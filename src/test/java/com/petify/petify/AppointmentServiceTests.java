package com.petify.petify;

import com.petify.petify.domain.Appointment;
import com.petify.petify.domain.ClinicUnavailableSlot;
import com.petify.petify.domain.Owner;
import com.petify.petify.domain.User;
import com.petify.petify.domain.VetClinic;
import com.petify.petify.dto.CreateUnavailableSlotRequest;
import com.petify.petify.repo.AppointmentRepository;
import com.petify.petify.repo.ClinicUnavailableSlotRepository;
import com.petify.petify.repo.NotificationRepository;
import com.petify.petify.repo.VetClinicRepository;
import com.petify.petify.repo.UserRepository;
import com.petify.petify.service.AppointmentService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class AppointmentServiceTests {

    @Mock AppointmentRepository appointmentRepository;
    @Mock VetClinicRepository vetClinicRepository;
    @Mock UserRepository userRepository;
    @Mock NotificationRepository notificationRepository;
    @Mock ClinicUnavailableSlotRepository unavailableSlotRepository;

    @InjectMocks
    AppointmentService appointmentService;

    @BeforeEach
    void setUp() {
        org.mockito.Mockito.lenient().when(appointmentRepository.save(any())).thenAnswer(i -> i.getArguments()[0]);

        org.mockito.Mockito.lenient().when(unavailableSlotRepository.save(any())).thenAnswer(i -> {
            ClinicUnavailableSlot slot = i.getArgument(0);
            slot.setSlotId(999L);
            return slot;
        });

        VetClinic clinic = new VetClinic();
        clinic.setClinicId(10L);
        org.mockito.Mockito.lenient().when(vetClinicRepository.findByUserId(1L)).thenReturn(Optional.of(clinic));
    }

    // ==========================================
    // TESTS FOR cancelAppointmentForOwner
    // ==========================================

    @ParameterizedTest
    @MethodSource("cancelAppointmentValues")
    public void cancelAppointmentTest(Long userId, Long appointmentId, Appointment mockAppointment, String expectedOutput) {
        if (mockAppointment != null) {
            when(appointmentRepository.findById(appointmentId)).thenReturn(Optional.of(mockAppointment));
        } else if (appointmentId != null) {
            when(appointmentRepository.findById(appointmentId)).thenReturn(Optional.empty());
        }

        if ("SUCCESS".equals(expectedOutput)) {
            var result = appointmentService.cancelAppointmentForOwner(userId, appointmentId);
            assertEquals("CANCELLED", result.getStatus());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    appointmentService.cancelAppointmentForOwner(userId, appointmentId)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> cancelAppointmentValues() {
        return Stream.of(
                Arguments.of(null, null, null, "User and appointment are required"),
                Arguments.of(1L, 100L, null, "Appointment not found"),
                Arguments.of(1L, 100L, createMockOwnerAppointment(2L, LocalDateTime.now().plusDays(1), "CONFIRMED"), "You can only cancel your own appointments"),
                Arguments.of(1L, 100L, createMockOwnerAppointment(1L, LocalDateTime.now().minusDays(1), "CONFIRMED"), "Only future appointments can be cancelled"),
                Arguments.of(1L, 100L, createMockOwnerAppointment(1L, LocalDateTime.now().plusDays(1), "CANCELLED"), "Appointment is already cancelled"),
                Arguments.of(1L, 100L, createMockOwnerAppointment(1L, LocalDateTime.now().plusDays(1), "DONE"), "This appointment can no longer be cancelled"),
                Arguments.of(1L, 100L, createMockOwnerAppointment(1L, LocalDateTime.now().plusDays(1), "CONFIRMED"), "SUCCESS")
        );
    }

    private static Appointment createMockOwnerAppointment(Long ownerUserId, LocalDateTime dateTime, String status) {
        Appointment appointment = new Appointment();
        Owner owner = new Owner();
        owner.setUserId(ownerUserId);
        User user = new User();
        user.setUserId(ownerUserId);
        owner.setUser(user);
        appointment.setResponsibleOwner(owner);
        appointment.setDateTime(dateTime);
        appointment.setStatus(status);
        appointment.setClinicId(1L);
        return appointment;
    }

    // ==========================================
    // TESTS FOR markAppointmentNoShowForClinicUser
    // ==========================================

    @ParameterizedTest
    @MethodSource("markNoShowValues")
    public void markNoShowTest(Long userId, Long appointmentId, Appointment mockAppointment, String expectedOutput) {
        if (mockAppointment != null) {
            when(appointmentRepository.findById(appointmentId)).thenReturn(Optional.of(mockAppointment));
        } else if (appointmentId != null) {
            when(appointmentRepository.findById(appointmentId)).thenReturn(Optional.empty());
        }

        if ("SUCCESS".equals(expectedOutput)) {
            var result = appointmentService.markAppointmentNoShowForClinicUser(userId, appointmentId);
            assertEquals("NO_SHOW", result.getStatus());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    appointmentService.markAppointmentNoShowForClinicUser(userId, appointmentId)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> markNoShowValues() {
        return Stream.of(
                Arguments.of(1L, 100L, null, "Appointment not found"),
                Arguments.of(1L, 100L, createMockClinicAppointment(99L, "CONFIRMED", LocalDateTime.now().minusDays(1)), "You can only update appointments for your own clinic"),
                Arguments.of(1L, 100L, createMockClinicAppointment(10L, "CANCELLED", LocalDateTime.now().minusDays(1)), "Only confirmed or done appointments can be marked as no-show"),
                Arguments.of(1L, 100L, createMockClinicAppointment(10L, "CONFIRMED", LocalDateTime.now().plusDays(1)), "An appointment can be marked as no-show only after its scheduled time"),
                Arguments.of(1L, 100L, createMockClinicAppointment(10L, "CONFIRMED", LocalDateTime.now().minusDays(1)), "SUCCESS")
        );
    }

    private static Appointment createMockClinicAppointment(Long clinicId, String status, LocalDateTime dateTime) {
        Appointment appointment = new Appointment();
        appointment.setClinicId(clinicId);
        appointment.setStatus(status);
        appointment.setDateTime(dateTime);
        return appointment;
    }

    // ==========================================
    // TESTS FOR createUnavailableSlot (All-DU-Paths)
    // ==========================================

    @ParameterizedTest
    @MethodSource("createUnavailableSlotValues")
    public void createUnavailableSlotTest(Long clinicId, String requestDateTime, boolean clinicExists, boolean appointmentExists, boolean slotExists, String expectedOutput) {
        CreateUnavailableSlotRequest request = new CreateUnavailableSlotRequest();
        request.setDateTime(requestDateTime);
        request.setReason("Doctor unavailable");

        if (clinicId != null && requestDateTime != null) {
            when(vetClinicRepository.existsById(clinicId)).thenReturn(clinicExists);

            if (clinicExists) {
                LocalDateTime slotTime = LocalDateTime.parse(requestDateTime);

                org.mockito.Mockito.lenient()
                        .when(appointmentRepository.existsByClinicIdAndDateTimeAndStatusNotIn(
                                eq(clinicId), eq(slotTime), any(List.class)))
                        .thenReturn(appointmentExists);

                org.mockito.Mockito.lenient()
                        .when(unavailableSlotRepository.existsByClinicIdAndDateTime(clinicId, slotTime))
                        .thenReturn(slotExists);
            }
        }

        if ("SUCCESS".equals(expectedOutput)) {
            var result = appointmentService.createUnavailableSlot(clinicId, request);
            assertNotNull(result);
            assertEquals(clinicId, result.getClinicId());
        } else {
            RuntimeException ex = assertThrows(RuntimeException.class, () ->
                    appointmentService.createUnavailableSlot(clinicId, request)
            );
            assertEquals(expectedOutput, ex.getMessage());
        }
    }

    public static Stream<Arguments> createUnavailableSlotValues() {
        // Valid slot (Future, lands on a 30-min boundary between 09:00 and 17:00)
        String validFutureTime = LocalDateTime.now().plusDays(1).withHour(10).withMinute(30).withSecond(0).withNano(0).toString();

        // Invalid slot (Past time) to purposefully fail the isValidWorkingSlot constraint
        String invalidPastTime = LocalDateTime.now().minusDays(1).withHour(10).withMinute(30).withSecond(0).withNano(0).toString();

        return Stream.of(
                // Path [1, 2]: Missing clinic ID
                Arguments.of(null, validFutureTime, false, false, false, "Clinic and date/time are required"),

                // Path [1, 3, 4]: Vet clinic does not exist
                Arguments.of(1L, validFutureTime, false, false, false, "Vet clinic not found"),

                // Path [1, 3, 5, 6]: Invalid working slot
                Arguments.of(1L, invalidPastTime, true, false, false, "Unavailable slot must be a future 30-minute slot between 09:00 and 17:00"),

                // Path [1, 3, 5, 7, 8]: Overlaps with existing appointment
                Arguments.of(1L, validFutureTime, true, true, false, "Cannot block a slot that already has an appointment"),

                // Path [1, 3, 5, 7, 9, 10]: Slot already marked unavailable
                Arguments.of(1L, validFutureTime, true, false, true, "This slot is already marked unavailable"),

                // Path [1, 3, 5, 7, 9, 11]: SUCCESS
                Arguments.of(1L, validFutureTime, true, false, false, "SUCCESS")
        );
    }
}