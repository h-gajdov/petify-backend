package com.petify.petify.api;

import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import org.springframework.transaction.annotation.Transactional;

import com.petify.petify.repo.UserRepository;

@SpringBootTest(properties = "spring.config.import=")
@AutoConfigureMockMvc
@ActiveProfiles("mvc-test")
@Transactional
class ApiMvcTest {
    @Autowired private MockMvc mvc;
    @Autowired private UserRepository users;

    @Test
    void signupReturnsCreatedClient() throws Exception {
        String username = username();
        signup(username, username + "@example.com")
                .andExpect(status().isCreated())
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.userId").isNumber())
                .andExpect(jsonPath("$.username").value(username))
                .andExpect(jsonPath("$.email").value(username + "@example.com"))
                .andExpect(jsonPath("$.userType").value("CLIENT"))
                .andExpect(jsonPath("$.password").doesNotExist());
    }

    @Test
    void registeredUserCanLoginByUsernameAndEmail() throws Exception {
        String username = register();
        for (String identifier : new String[]{username, username + "@example.com"}) {
            login(identifier, "test-password")
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.username").value(username))
                    .andExpect(jsonPath("$.userType").value("CLIENT"))
                    .andExpect(jsonPath("$.password").doesNotExist());
        }
    }

    @Test
    void duplicateUsernameIsRejected() throws Exception {
        String username = register();
        signup(username, "other-" + username + "@example.com")
                .andExpect(status().isBadRequest());
    }

    @Test
    void duplicateEmailIsRejected() throws Exception {
        String username = register();
        signup(username(), username + "@example.com")
                .andExpect(status().isBadRequest());
    }

    @Test
    void wrongPasswordIsRejectedByRealAuthenticationService() throws Exception {
        login(register(), "wrong-password")
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("Invalid username or password"));
    }

    @Test
    void unknownUserCannotLogin() throws Exception {
        login(username(), "test-password")
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.message").value("Invalid username or password"));
    }

    @Test
    void malformedJsonIsRejected() throws Exception {
        mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content("{broken"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void newClientHasNoFavorites() throws Exception {
        mvc.perform(get("/api/favorites").header("X-User-Id", registeredUserId()))
                .andExpect(status().isOk()).andExpect(content().json("[]"));
    }

    @Test
    void addingMissingListingToFavoritesIsRejected() throws Exception {
        mvc.perform(post("/api/favorites/-1").header("X-User-Id", registeredUserId()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("Listing not found"));
    }

    @Test
    void clientCannotAccessAdminUsers() throws Exception {
        mvc.perform(get("/api/users/admin/all").header("X-User-Id", registeredUserId()))
                .andExpect(status().isForbidden());
    }

    @Test
    void clientWithoutClinicReceivesError() throws Exception {
        mvc.perform(get("/api/clinics/my").header("X-User-Id", registeredUserId()))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error").value("User is not linked to a clinic"));
    }

    @Test
    void clinicLookupRequiresUserHeader() throws Exception {
        mvc.perform(get("/api/clinics/my")).andExpect(status().isBadRequest());
    }

    @Test
    void appointmentSlotsRequireValidDate() throws Exception {
        mvc.perform(get("/api/appointments/clinics/1/available-slots").param("date", "not-a-date"))
                .andExpect(status().isBadRequest());
    }

    private String register() throws Exception {
        String username = username();
        signup(username, username + "@example.com").andExpect(status().isCreated());
        return username;
    }

    private long registeredUserId() throws Exception {
        // Real repository lookup for the ID generated by the signup request.
        return users.findByUsername(register()).orElseThrow().getUserId();
    }

    private ResultActions signup(String username, String email) throws Exception {
        return mvc.perform(post("/api/auth/signup").contentType(MediaType.APPLICATION_JSON).content("""
                {"username":"%s","email":"%s","password":"test-password",
                 "firstName":"MVC","lastName":"Test"}
                """.formatted(username, email)));
    }

    private ResultActions login(String username, String password) throws Exception {
        return mvc.perform(post("/api/auth/login").contentType(MediaType.APPLICATION_JSON).content("""
                {"username":"%s","password":"%s"}
                """.formatted(username, password)));
    }

    private String username() {
        return "mvc_" + UUID.randomUUID().toString().replace("-", "").substring(0, 24);
    }
}
