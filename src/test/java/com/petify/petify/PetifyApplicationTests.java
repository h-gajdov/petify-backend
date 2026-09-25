package com.petify.petify;

import com.petify.petify.repo.PublicListingCardView;
import com.petify.petify.repo.PublicListingRepository;
import com.petify.petify.repo.RecommendationRepository;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class PetifyApplicationTests {

    @Container
    @ServiceConnection
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:15-alpine");

    @Autowired
    private Flyway flyway;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private PublicListingRepository publicListingRepository;

    @Autowired
    private RecommendationRepository recommendationRepository;

    @Test
    void migrationsRunAgainstPostgres() {
        assertThat(flyway.info().current()).isNotNull();
        assertThat(flyway.info().pending()).isEmpty();
    }

    @Test
    void publicListingRepositoryReadsMigratedView() {
        PublicListingCardView beagle = publicListingRepository.findActiveListingCards().stream()
            .filter(listing -> "UiBeagle".equals(listing.getAnimalName()))
            .findFirst()
            .orElseThrow();

        assertThat(beagle.getStatus()).isEqualTo("ACTIVE");
        assertThat(beagle.getOwnerUsername()).isEqualTo("ui.owner");
        assertThat(beagle.getOwnerId()).isNotNull();
    }

    @Test
    void recommendationsUsePostgresFunctionAndExcludeAlreadyLikedListing() {
        Long userId = jdbcTemplate.queryForObject(
            "select user_id from users where username = 'ui.recs'", Long.class
        );

        var recommendations = recommendationRepository.getRecommendedListings(userId);

        assertThat(recommendations).extracting(r -> r.getTitle()).contains("UiCorgi")
            .doesNotContain("UiBeagle");
    }

    @Test
    @Transactional
    void listingTriggerRejectsInvalidStatusTransition() {
        Long listingId = jdbcTemplate.queryForObject("""
            select l.listing_id from listings l
            join animals a on a.animal_id = l.animal_id
            where a.name = 'UiBeagle'
            """, Long.class);

        assertThatThrownBy(() -> jdbcTemplate.update(
            "update listings set status = 'DRAFT' where listing_id = ?", listingId
        )).isInstanceOf(DataAccessException.class)
          .hasMessageContaining("Invalid listing status transition: ACTIVE -> DRAFT");
    }
}
