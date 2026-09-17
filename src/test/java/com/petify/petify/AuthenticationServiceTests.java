package com.petify.petify;

import com.petify.petify.domain.Client;
import com.petify.petify.domain.User;
import com.petify.petify.domain.UserType;
import com.petify.petify.dto.LoginRequest;
import com.petify.petify.dto.UserDTO;
import com.petify.petify.dto.SignUpRequest;
import com.petify.petify.repo.AdminRepository;
import com.petify.petify.repo.AnalyticsRepository;
import com.petify.petify.repo.ClientRepository;
import com.petify.petify.repo.OwnerRepository;
import com.petify.petify.repo.UserRepository;
import com.petify.petify.repo.VetClinicRepository;
import com.petify.petify.service.AuthService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class AuthenticationServiceTests {

    @Mock UserRepository userRepository;
    @Mock ClientRepository clientRepository;
    @Mock OwnerRepository ownerRepository;
    @Mock AdminRepository adminRepository;
    @Mock PasswordEncoder passwordEncoder;
    @Mock AnalyticsRepository analyticsRepository;
    @Mock VetClinicRepository vetClinicRepository;

    @InjectMocks
    AuthService authService;

    @BeforeEach
    void setUp() {
        org.mockito.Mockito.lenient().when(passwordEncoder.encode(any())).thenReturn("$2a$10$encodedHash");

        org.mockito.Mockito.lenient().when(userRepository.save(any())).thenAnswer(i -> {
            User user = i.getArgument(0);
            user.setUserId(1L);
            return user;
        });

        org.mockito.Mockito.lenient()
                .when(analyticsRepository.getTopActiveUsers(any(), any()))
                .thenReturn(Collections.emptyList());
    }

    // ==========================================
    // TESTS FOR signUp (Prime Path Coverage)
    // ==========================================

    @ParameterizedTest
    @MethodSource("signUpValues")
    public void signUpTest(boolean usernameTaken, boolean emailTaken, boolean clientInsertFails, String expectedOutput) {
        SignUpRequest request = createSignUpRequest("petlover", "pet@lover.com", "Secret123");

        when(userRepository.findByUsername(request.getUsername()))
                .thenReturn(usernameTaken ? Optional.of(createMockUser("petlover", "other@lover.com")) : Optional.empty());

        if (!usernameTaken) {
            when(userRepository.findByEmail(request.getEmail()))
                    .thenReturn(emailTaken ? Optional.of(createMockUser("someoneelse", "pet@lover.com")) : Optional.empty());
        }

        if (!usernameTaken && !emailTaken) {
            if (clientInsertFails) {
                when(clientRepository.save(any())).thenThrow(new RuntimeException("clients insert failed"));
            } else {
                when(clientRepository.save(any())).thenAnswer(i -> i.getArguments()[0]);
            }
        }

        if ("SUCCESS".equals(expectedOutput)) {
            var result = authService.signUp(request);
            assertNotNull(result);
            assertEquals(1L, result.getUserId());
            assertEquals("petlover", result.getUsername());
            assertEquals("pet@lover.com", result.getEmail());
            assertEquals(UserType.CLIENT, result.getUserType());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    authService.signUp(request)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> signUpValues() {
        return Stream.of(

                // Path [1, 2]
                Arguments.of(true, false, false, "Username already exists"),

                // Path [1, 3, 4]
                Arguments.of(false, true, false, "Email already exists"),

                // Path [1, 3, 5, 6, 7]
                Arguments.of(false, false, true, "Failed to create client profile: clients insert failed"),

                // Path [1, 3, 5, 6, 8]
                Arguments.of(false, false, false, "SUCCESS")
        );
    }

    private static SignUpRequest createSignUpRequest(String username, String email, String password) {
        SignUpRequest request = new SignUpRequest();
        request.setUsername(username);
        request.setEmail(email);
        request.setPassword(password);
        request.setFirstName("Ana");
        request.setLastName("Ilieva");
        return request;
    }

    private static User createMockUser(String username, String email) {
        User user = new User();
        user.setUserId(99L);
        user.setUsername(username);
        user.setEmail(email);
        return user;
    }

    // ==========================================
    // TESTS FOR login (Edge Pair Coverage)
    // ==========================================

    @ParameterizedTest
    @MethodSource("loginValues")
    public void loginTest(boolean userExists, boolean encoderMatches, boolean legacyPlaintext,
                          boolean blocked, UserType role, String expectedOutput) {
        LoginRequest request = new LoginRequest("petlover", "Secret123");

        User foundUser = createMockLoginUser(legacyPlaintext ? "Secret123" : "$2a$10$storedHash");

        when(userRepository.findByUsernameOrEmail(request.getUsername(), request.getUsername()))
                .thenReturn(userExists ? Optional.of(foundUser) : Optional.empty());

        if (userExists) {
            when(passwordEncoder.matches(request.getPassword(), foundUser.getPassword()))
                    .thenReturn(encoderMatches);
        }

        boolean authenticated = userExists && (encoderMatches || legacyPlaintext);

        if (authenticated) {
            when(clientRepository.existsById(1L)).thenReturn(blocked);
            if (blocked) {
                when(clientRepository.findById(1L))
                        .thenReturn(Optional.of(createBlockedClient(foundUser, "Spam")));
            }
        }

        if (authenticated && !blocked) {
            when(adminRepository.existsById(1L)).thenReturn(role == UserType.ADMIN);
            if (role != UserType.ADMIN) {
                when(vetClinicRepository.existsByUserId(1L)).thenReturn(role == UserType.CLINIC);
            }
            if (role != UserType.ADMIN && role != UserType.CLINIC) {
                when(ownerRepository.existsById(1L)).thenReturn(role == UserType.OWNER);
            }
        }

        if ("SUCCESS".equals(expectedOutput)) {
            var result = authService.login(request);
            assertNotNull(result);
            assertEquals(1L, result.getUserId());
            assertEquals("petlover", result.getUsername());
            assertEquals(role, result.getUserType());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    authService.login(request)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> loginValues() {
        return Stream.of(
                // Path [1, 2, 3]
                Arguments.of(false, false, false, false, null, "Invalid username or password"),

                // Path [1, 2, 4, 5, 6, 8]
                Arguments.of(true, false, false, false, null, "Invalid username or password"),

                // Path [1, 2, 4, 5, 6, 7, 9, 10, 11]
                Arguments.of(true, false, true, true, null, "Your account has been blocked. Reason: Spam"),

                // Path [1, 2, 4, 5, 9, 10, 12, 14, 16, 18, 19, 20]
                Arguments.of(true, true, false, false, UserType.CLIENT, "SUCCESS"),

                // Path [1, 2, 4, 5, 6, 7, 9, 10, 12, 13, 19, 20]
                Arguments.of(true, false, true, false, UserType.ADMIN, "SUCCESS"),

                // Path [1, 2, 4, 5, 9, 10, 12, 14, 15, 19, 20]
                Arguments.of(true, true, false, false, UserType.CLINIC, "SUCCESS"),

                // Path [1, 2, 4, 5, 9, 10, 12, 14, 16, 17, 19, 20]
                Arguments.of(true, true, false, false, UserType.OWNER, "SUCCESS")
        );
    }

    private static User createMockLoginUser(String storedPassword) {
        User user = new User();
        user.setUserId(1L);
        user.setUsername("petlover");
        user.setEmail("pet@lover.com");
        user.setPassword(storedPassword);
        user.setFirstName("Ana");
        user.setLastName("Ilieva");
        return user;
    }

    private static Client createBlockedClient(User user, String reason) {
        Client client = new Client(user);
        client.setBlocked(true);
        client.setBlockedReason(reason);
        return client;
    }

    // ==========================================
    // TESTS FOR getUserById (All Combinations Coverage)
    // ==========================================

    @ParameterizedTest
    @MethodSource("getUserByIdValues")
    public void getUserByIdTest(Long userId, boolean userExists, String expectedOutput) {
        User foundUser = createMockLoginUser("$2a$10$storedHash");

        when(userRepository.findById(userId))
                .thenReturn(userExists ? Optional.of(foundUser) : Optional.empty());

        if (userExists) {
            stubPlainClientLookups();
        }

        if ("SUCCESS".equals(expectedOutput)) {
            UserDTO result = authService.getUserById(userId);
            assertNotNull(result);
            assertEquals(1L, result.getUserId());
            assertEquals("petlover", result.getUsername());
            assertEquals("CLIENT", result.getUserType());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    authService.getUserById(userId)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> getUserByIdValues() {
        return Stream.of(
                Arguments.of(7L, false, "User not found"),

                Arguments.of(null, false, "User not found"),

                Arguments.of(1L, true, "SUCCESS")
        );
    }

    // ==========================================
    // TESTS FOR getUserByUsername (All Combinations Coverage)
    // ==========================================

    @ParameterizedTest
    @MethodSource("getUserByUsernameValues")
    public void getUserByUsernameTest(String username, boolean userExists, String expectedOutput) {
        User foundUser = createMockLoginUser("$2a$10$storedHash");

        when(userRepository.findByUsername(username))
                .thenReturn(userExists ? Optional.of(foundUser) : Optional.empty());

        if (userExists) {
            stubPlainClientLookups();
        }

        if ("SUCCESS".equals(expectedOutput)) {
            UserDTO result = authService.getUserByUsername(username);
            assertNotNull(result);
            assertEquals(1L, result.getUserId());
            assertEquals("petlover", result.getUsername());
            assertEquals("CLIENT", result.getUserType());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    authService.getUserByUsername(username)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> getUserByUsernameValues() {
        return Stream.of(

                Arguments.of("ghost", false, "User not found"),

                Arguments.of(null, false, "User not found"),

                Arguments.of("petlover", true, "SUCCESS")
        );
    }

    private void stubPlainClientLookups() {
        when(adminRepository.existsById(1L)).thenReturn(false);
        when(vetClinicRepository.existsByUserId(1L)).thenReturn(false);
        when(ownerRepository.existsById(1L)).thenReturn(false);
        when(clientRepository.existsById(1L)).thenReturn(false);
    }

    // ==========================================
    // TESTS FOR getAllUsers (Prime Path Coverage)
    // ==========================================

    // Test path [1, 2, 4, 5]
    @org.junit.jupiter.api.Test
    public void getAllUsersEmptyRepositoryTest() {
        when(userRepository.findAll()).thenReturn(Collections.emptyList());

        List<UserDTO> result = authService.getAllUsers();

        assertNotNull(result);
        assertEquals(0, result.size());
    }

    // Test path [1, 2, 3, 2, 3, 2, 4, 5]
    @org.junit.jupiter.api.Test
    public void getAllUsersTwoIterationsTest() {
        User admin = createUser(1L, "adminka", "admin@petify.mk");
        User blockedClient = createUser(2L, "petlover", "pet@lover.com");

        when(userRepository.findAll()).thenReturn(List.of(admin, blockedClient));

        when(adminRepository.existsById(1L)).thenReturn(true);

        when(adminRepository.existsById(2L)).thenReturn(false);
        when(vetClinicRepository.existsByUserId(2L)).thenReturn(false);
        when(ownerRepository.existsById(2L)).thenReturn(false);
        when(clientRepository.existsById(2L)).thenReturn(true);
        when(clientRepository.findById(2L))
                .thenReturn(Optional.of(createBlockedClient(blockedClient, "Spam")));

        List<UserDTO> result = authService.getAllUsers();

        assertEquals(2, result.size());

        assertEquals("adminka", result.get(0).getUsername());
        assertEquals("ADMIN", result.get(0).getUserType());
        assertFalse(result.get(0).isBlocked());

        assertEquals("petlover", result.get(1).getUsername());
        assertEquals("CLIENT", result.get(1).getUserType());
        assertTrue(result.get(1).isBlocked());
        assertEquals("Spam", result.get(1).getBlockedReason());
    }

    private static User createUser(Long userId, String username, String email) {
        User user = new User();
        user.setUserId(userId);
        user.setUsername(username);
        user.setEmail(email);
        user.setFirstName("Ana");
        user.setLastName("Ilieva");
        return user;
    }

    // ==========================================
    // TESTS FOR mapToDTO (All-DU-Paths Coverage)
    // ==========================================

    @ParameterizedTest
    @MethodSource("mapToDTOValues")
    public void mapToDTOTest(String role, boolean clientRecordExists, boolean clientFound, boolean blocked,
                             String expectedUserType, boolean expectedBlocked, String expectedReason) {
        User user = createUser(1L, "petlover", "pet@lover.com");
        when(userRepository.findById(1L)).thenReturn(Optional.of(user));

        when(adminRepository.existsById(1L)).thenReturn("ADMIN".equals(role));

        if (!"ADMIN".equals(role)) {
            when(vetClinicRepository.existsByUserId(1L)).thenReturn("CLINIC".equals(role));
        }

        if (!"ADMIN".equals(role) && !"CLINIC".equals(role)) {
            when(ownerRepository.existsById(1L)).thenReturn("OWNER".equals(role));
            when(clientRepository.existsById(1L)).thenReturn(clientRecordExists);

            if (clientRecordExists) {
                when(clientRepository.findById(1L)).thenReturn(
                        clientFound
                                ? Optional.of(createClient(user, blocked, blocked ? "Spam" : null))
                                : Optional.empty());
            }
        }

        UserDTO result = authService.getUserById(1L);

        assertNotNull(result);
        assertEquals(1L, result.getUserId());
        assertEquals("petlover", result.getUsername());
        assertEquals(expectedUserType, result.getUserType());
        assertEquals(expectedBlocked, result.isBlocked());
        assertEquals(expectedReason, result.getBlockedReason());
        assertFalse(result.isVerified());

        verify(clientRepository, clientRecordExists ? times(1) : never()).findById(1L);
    }

    public static Stream<Arguments> mapToDTOValues() {
        return Stream.of(

                // Path [1, 2, 3, 12, 13]
                Arguments.of("ADMIN", false, false, false, "ADMIN", false, ""),

                // Path [1, 2, 4, 5, 12, 13]
                Arguments.of("CLINIC", false, false, false, "CLINIC", false, ""),

                // Path [1, 2, 4, 6, 7, 12, 13]
                Arguments.of("OWNER", false, false, false, "OWNER", false, ""),

                // Path [1, 2, 4, 6, 7, 8, 12, 13]
                Arguments.of("OWNER", true, false, false, "OWNER", false, ""),

                // Path [1, 2, 4, 6, 7, 8, 10, 12, 13]
                Arguments.of("OWNER", true, true, false, "OWNER", false, ""),

                // Path [1, 2, 4, 6, 7, 8, 10, 11, 12, 13]
                Arguments.of("OWNER", true, true, true, "OWNER", true, "Spam"),

                // Path [1, 2, 4, 6, 9, 12, 13]
                Arguments.of("CLIENT", false, false, false, "CLIENT", false, ""),

                // Path [1, 2, 4, 6, 9, 14, 12, 13]
                Arguments.of("CLIENT", true, false, false, "CLIENT", false, ""),

                // Path [1, 2, 4, 6, 9, 14, 15, 12, 13]
                Arguments.of("CLIENT", true, true, false, "CLIENT", false, ""),

                // Path [1, 2, 4, 6, 9, 14, 15, 16, 12, 13]
                Arguments.of("CLIENT", true, true, true, "CLIENT", true, "Spam")
        );
    }

    private static Client createClient(User user, boolean blocked, String reason) {
        Client client = new Client(user);
        client.setBlocked(blocked);
        client.setBlockedReason(reason);
        return client;
    }
}
