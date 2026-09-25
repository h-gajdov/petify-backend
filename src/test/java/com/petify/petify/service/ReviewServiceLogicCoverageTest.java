package com.petify.petify.service;

import com.petify.petify.dto.CreateReviewRequest;
import com.petify.petify.repo.AppointmentRepository;
import com.petify.petify.repo.ClinicReviewRepository;
import com.petify.petify.repo.ReviewRepository;
import com.petify.petify.repo.UserRepository;
import com.petify.petify.repo.UserReviewRepository;
import com.petify.petify.repo.VetClinicRepository;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Optional;
import java.util.stream.Stream;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ReviewServiceLogicCoverageTest {

    private static final Long REVIEWER_ID = 40L;
    private static final Long TARGET_ID = 39L;

    @Mock private ReviewRepository reviewRepository;
    @Mock private UserReviewRepository userReviewRepository;
    @Mock private ClinicReviewRepository clinicReviewRepository;
    @Mock private UserRepository userRepository;
    @Mock private VetClinicRepository vetClinicRepository;
    @Mock private AppointmentRepository appointmentRepository;

    @InjectMocks private ReviewService reviewService;

    private static CreateReviewRequest request(Integer rating) {
        CreateReviewRequest request = new CreateReviewRequest();
        request.setRating(rating);
        request.setComment("Logic coverage");
        return request;
    }

    private static Stream<Arguments> raccTrueRows() {
        return Stream.of(
            Arguments.of(4, (Integer) null),   // T F F : a=T, minors b=F c=F
            Arguments.of(6, 0),                // F T F : b=T, minors a=F c=F
            Arguments.of(7, 6)                 // F F T : c=T, minors a=F b=F
        );
    }

    @ParameterizedTest(name = "RACC row {0}: rating = {1} is rejected")
    @MethodSource("raccTrueRows")
    void invalidRatingIsRejected(int row, Integer rating) {
        assertThatThrownBy(() -> reviewService.createReview(REVIEWER_ID, TARGET_ID, request(rating)))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("Rating must be between 1 and 5");

        verify(userRepository, never()).findById(anyLong());
    }


    @ParameterizedTest(name = "RACC row 8: rating = {0} passes validation")
    @MethodSource("raccFalseRow")
    void validRatingPassesValidation(int rating) {
        when(userRepository.findById(REVIEWER_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> reviewService.createReview(REVIEWER_ID, TARGET_ID, request(rating)))
            .isInstanceOf(RuntimeException.class)
            .hasMessage("Reviewer not found");

        verify(userRepository).findById(REVIEWER_ID);
    }

    private static Stream<Arguments> raccFalseRow() {
        return Stream.of(
            Arguments.of(3),  // F F F : middle of the range
            Arguments.of(1),  // F F F : lower boundary
            Arguments.of(5)   // F F F : upper boundary
        );
    }
}
