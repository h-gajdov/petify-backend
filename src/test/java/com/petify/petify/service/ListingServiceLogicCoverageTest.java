package com.petify.petify.service;

import com.petify.petify.domain.Listing;
import com.petify.petify.repo.ListingRepository;
import com.petify.petify.repo.OwnerRepository;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;

import java.math.BigDecimal;
import java.util.stream.Stream;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;


@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class ListingServiceLogicCoverageTest {

    private static final Pageable PAGEABLE = PageRequest.of(0, 20);

    @Mock private ListingRepository listingRepository;
    @Mock private OwnerRepository ownerRepository;

    @InjectMocks private ListingService listingService;

    private static Stream<Arguments> allEightRows() {
        BigDecimal ten = new BigDecimal("10");
        BigDecimal hundred = new BigDecimal("100");
        return Stream.of(
            // row, status, minPrice, maxPrice, branch
            Arguments.of(1, null, null, null, "findAll"),                         // T T T
            Arguments.of(2, null, null, hundred, "findAdminListings"),            // T T F
            Arguments.of(3, null, ten, null, "findAdminListings"),                // T F T
            Arguments.of(4, null, ten, hundred, "findAdminListings"),             // T F F
            Arguments.of(5, "ACTIVE", null, null, "findByStatusIgnoreCase"),      // F T T
            Arguments.of(6, "ACTIVE", null, hundred, "findAdminListings"),        // F T F
            Arguments.of(7, "ACTIVE", ten, null, "findAdminListings"),            // F F T
            Arguments.of(8, "ACTIVE", ten, hundred, "findAdminListings")          // F F F
        );
    }

    @ParameterizedTest(name = "CoC row {0} routes to {4}")
    @MethodSource("allEightRows")
    void adminListingCombinatorialCoverage(int row, String status, BigDecimal minPrice, BigDecimal maxPrice, String branch) {
        Page<Listing> empty = Page.empty(PAGEABLE);
        when(listingRepository.findAll(PAGEABLE)).thenReturn(empty);
        when(listingRepository.findByStatusIgnoreCase(any(), eq(PAGEABLE))).thenReturn(empty);
        when(listingRepository.findAdminListings(any(), any(), any(), eq(PAGEABLE))).thenReturn(empty);

        listingService.getAdminListings(status, minPrice, maxPrice, PAGEABLE);

        switch (branch) {
            case "findAll" -> {
                verify(listingRepository).findAll(PAGEABLE);
                verify(listingRepository, never()).findByStatusIgnoreCase(any(), any());
                verify(listingRepository, never()).findAdminListings(any(), any(), any(), any());
            }
            case "findByStatusIgnoreCase" -> {
                verify(listingRepository).findByStatusIgnoreCase(status, PAGEABLE);
                verify(listingRepository, never()).findAll(PAGEABLE);
                verify(listingRepository, never()).findAdminListings(any(), any(), any(), any());
            }
            default -> {
                verify(listingRepository).findAdminListings(status, minPrice, maxPrice, PAGEABLE);
                verify(listingRepository, never()).findAll(PAGEABLE);
                verify(listingRepository, never()).findByStatusIgnoreCase(any(), any());
            }
        }
    }

    @ParameterizedTest(name = "blank status {0} is treated as null")
    @MethodSource("blankStatuses")
    void blankStatusIsNormalisedToNull(String status) {
        when(listingRepository.findAll(PAGEABLE)).thenReturn(Page.empty(PAGEABLE));

        listingService.getAdminListings(status, null, null, PAGEABLE);

        verify(listingRepository).findAll(PAGEABLE);
    }

    private static Stream<Arguments> blankStatuses() {
        return Stream.of(Arguments.of(""), Arguments.of("   "));
    }
}
