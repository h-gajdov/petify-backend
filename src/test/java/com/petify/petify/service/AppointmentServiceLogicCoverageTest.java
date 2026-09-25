package com.petify.petify.service;

import com.petify.petify.domain.Appointment;
import com.petify.petify.domain.Owner;
import com.petify.petify.domain.Pet;
import com.petify.petify.domain.User;
import com.petify.petify.dto.CreateAppointmentRequest;
import com.petify.petify.repo.AppointmentRepository;
import com.petify.petify.repo.ClinicUnavailableSlotRepository;
import com.petify.petify.repo.NotificationRepository;
import com.petify.petify.repo.OwnerRepository;
import com.petify.petify.repo.PetRepository;
import com.petify.petify.repo.UserRepository;
import com.petify.petify.repo.VetClinicRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Optional;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;


@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class AppointmentServiceLogicCoverageTest {

    private static final Long USER_ID = 7L;
    private static final Long OTHER_OWNER_ID = 99L;
    private static final Long PET_ID = 21L;
    private static final Long CLINIC_ID = 1L;

    private static final DateTimeFormatter ISO = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSSSSSSSS");

    @Mock private AppointmentRepository appointmentRepository;
    @Mock private ClinicUnavailableSlotRepository unavailableSlotRepository;
    @Mock private NotificationRepository notificationRepository;
    @Mock private OwnerRepository ownerRepository;
    @Mock private PetRepository petRepository;
    @Mock private UserRepository userRepository;
    @Mock private VetClinicRepository vetClinicRepository;

    @InjectMocks private AppointmentService appointmentService;

    private static LocalDateTime base(int daysFromNow) {
        return LocalDateTime.now()
            .plusDays(daysFromNow)
            .withHour(10).withMinute(0).withSecond(0).withNano(0);
    }

    private static String iso(LocalDateTime dateTime) {
        return dateTime.format(ISO);
    }

    private static Owner ownerWith(Long userId) {
        if (userId == null) {
            return new Owner();
        }
        User user = new User();
        user.setUserId(userId);
        Owner owner = new Owner(user);
        owner.setUserId(userId);
        return owner;
    }

    @Test
    void requiredFieldsGuard_predicateTrue() {
        CreateAppointmentRequest request =
            new CreateAppointmentRequest(null, PET_ID, iso(base(7)), "PC: predicate true");

        assertThatThrownBy(() -> appointmentService.createAppointment(USER_ID, request))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("Clinic, pet, and date/time are required");

        verify(ownerRepository, never()).findByUserId(anyLong());
    }

    @Test
    void requiredFieldsGuard_predicateFalse() {
        CreateAppointmentRequest request =
            new CreateAppointmentRequest(CLINIC_ID, PET_ID, iso(base(7)), "PC: predicate false");
        when(ownerRepository.findByUserId(USER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> appointmentService.createAppointment(USER_ID, request))
            .hasMessageNotContaining("required");

        verify(ownerRepository).findByUserId(USER_ID);
    }

    private static Stream<Arguments> petOwnershipRows() {
        return Stream.of(
            Arguments.of(4, (Owner) null, true),               // T F F : no owner at all
            Arguments.of(6, ownerWith(null), true),             // F T F : owner row with no user id
            Arguments.of(7, ownerWith(OTHER_OWNER_ID), true)    // F F T : belongs to someone else
        );
    }

    @ParameterizedTest(name = "CC row {0}: pet ownership guard rejects = {2}")
    @MethodSource("petOwnershipRows")
    void petOwnershipGuardClauseCoverage(int row, Owner petOwner, boolean predicateHolds) {
        Owner callerOwner = ownerWith(USER_ID);
        Pet pet = new Pet();
        pet.setOwner(petOwner);

        when(ownerRepository.findByUserId(USER_ID)).thenReturn(Optional.of(callerOwner));
        when(petRepository.findById(PET_ID)).thenReturn(Optional.of(pet));

        CreateAppointmentRequest request =
            new CreateAppointmentRequest(CLINIC_ID, PET_ID, iso(base(7)), "CC row " + row);

        assertThatThrownBy(() -> appointmentService.createAppointment(USER_ID, request))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("You can only create appointments for your own pets");
    }

    @BeforeEach
    void reachTheSlotChecks() {
        Owner owner = ownerWith(USER_ID);
        Pet pet = new Pet();
        pet.setOwner(owner);

        when(ownerRepository.findByUserId(USER_ID)).thenReturn(Optional.of(owner));
        when(petRepository.findById(PET_ID)).thenReturn(Optional.of(pet));
        when(vetClinicRepository.existsById(CLINIC_ID)).thenReturn(true);
        when(appointmentRepository.save(any(Appointment.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));
    }

    private static Stream<Arguments> clinicSlotAvailabilityRows() {
        return Stream.of(
            Arguments.of(1, iso(base(7)), false, false, true),                        // T T T
            Arguments.of(2, iso(base(7).withMinute(15)), false, false, false),        // F T T : off-grid, a false
            Arguments.of(3, iso(base(7)), true, false, false),                        // T F T
            Arguments.of(4, iso(base(7)), false, true, false)                         // T T F
        );
    }

    @ParameterizedTest(name = "GACC row {0}: clinic slot available = {4}")
    @MethodSource("clinicSlotAvailabilityRows")
    void clinicSlotAvailabilityGeneralActiveClauseCoverage(int row, String dateTime, boolean appointmentExists, boolean slotUnavailable, boolean predicateHolds) {
        when(appointmentRepository.existsByClinicIdAndDateTimeAndStatusNotIn(anyLong(), any(), anyList()))
            .thenReturn(appointmentExists);
        when(unavailableSlotRepository.existsByClinicIdAndDateTime(anyLong(), any()))
            .thenReturn(slotUnavailable);

        CreateAppointmentRequest request =
            new CreateAppointmentRequest(CLINIC_ID, PET_ID, dateTime, "GACC row " + row);

        if (predicateHolds) {
            assertThat(appointmentService.createAppointment(USER_ID, request)).isNotNull();
        } else {
            assertThatThrownBy(() -> appointmentService.createAppointment(USER_ID, request))
                .hasMessageContaining("no longer available");
        }
    }


    private static Stream<Arguments> slotRows() {
        return Stream.of(
            Arguments.of(1, iso(base(7)), true),                                       // T T T T T T -> true
            Arguments.of(2, iso(base(-7)), false),                                     // F T T T T T : in the past
            Arguments.of(3, iso(base(7).withHour(8).withMinute(30)), false),           // T F T T T T : before opening
            Arguments.of(4, iso(base(7).withHour(17).withMinute(30)), false),          // T T F T T T : after closing
            Arguments.of(5, iso(base(7).withMinute(15)), false),                       // T T T F T T : off the grid
            Arguments.of(6, iso(base(7).withSecond(30)), false),                       // T T T T F T : seconds set
            Arguments.of(7, iso(base(7).withNano(500)), false)                         // T T T T T F : nanos set
        );
    }

    @ParameterizedTest(name = "CACC row {0} expects predicate = {2}")
    @MethodSource("slotRows")
    void isValidWorkingSlotCorrelatedActiveClauseCoverage(int row, String dateTime, boolean predicateHolds) {
        when(appointmentRepository.existsByClinicIdAndDateTimeAndStatusNotIn(anyLong(), any(), anyList()))
            .thenReturn(false);
        when(unavailableSlotRepository.existsByClinicIdAndDateTime(anyLong(), any()))
            .thenReturn(false);

        CreateAppointmentRequest request =
            new CreateAppointmentRequest(CLINIC_ID, PET_ID, dateTime, "CACC row " + row);

        if (predicateHolds) {
            assertThat(appointmentService.createAppointment(USER_ID, request)).isNotNull();
            verify(appointmentRepository).save(any(Appointment.class));
        } else {
            assertThatThrownBy(() -> appointmentService.createAppointment(USER_ID, request))
                .hasMessageContaining("no longer available");
            verify(appointmentRepository, never()).save(any(Appointment.class));
        }
    }
}
