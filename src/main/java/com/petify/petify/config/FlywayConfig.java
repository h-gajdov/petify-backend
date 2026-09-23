package com.petify.petify.config;

import java.util.Arrays;
import java.util.Map;
import java.util.Objects;
import javax.sql.DataSource;

import org.flywaydb.core.Flyway;
import org.flywaydb.core.api.CoreErrorCode;
import org.flywaydb.core.api.MigrationInfo;
import org.flywaydb.core.api.output.ValidateOutput;
import org.flywaydb.core.api.output.ValidateResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.jpa.autoconfigure.EntityManagerFactoryDependsOnPostProcessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Spring Boot 4 moved the Flyway auto-configuration into the separate
 * {@code org.springframework.boot:spring-boot-flyway} module, so having only
 * {@code flyway-core} on the classpath no longer runs the migrations on startup.
 * This wires Flyway by hand from the same {@code spring.flyway.*} properties.
 */
@Configuration
@ConditionalOnProperty(name = "spring.flyway.enabled", havingValue = "true", matchIfMissing = true)
public class FlywayConfig {
    private static final Logger log = LoggerFactory.getLogger(FlywayConfig.class);
    private static final int OLD_V10_CHECKSUM = 659034310;
    private static final Map<String, String> MOVED_SEED_MIGRATIONS = Map.of(
            "2", "Insert initial data",
            "8", "Insert more vet clinics and applications",
            "11", "Insert clinic unavailable slots",
            "13", "Seed ui test accounts",
            "14", "Seed ui test listings",
            "15", "Seed ui test health records"
    );

    @Bean(initMethod = "migrate")
    public Flyway flyway(DataSource dataSource,
                         @Value("${spring.flyway.locations:classpath:db/migration}") String[] locations,
                         @Value("${spring.flyway.baseline-on-migrate:false}") boolean baselineOnMigrate,
                         @Value("${spring.flyway.baseline-version:1}") String baselineVersion) {
        Flyway flyway = Flyway.configure()
                .dataSource(dataSource)
                .locations(locations)
                .baselineOnMigrate(baselineOnMigrate)
                .baselineVersion(baselineVersion)
                .load();

        // Older releases applied sample data as normal migrations. Reconcile only
        // that known history when starting with application-only migrations.
        if (Arrays.equals(locations, new String[]{"classpath:db/migration"})) {
            repairMovedSeedHistory(flyway);
        }
        return flyway;
    }

    static void repairMovedSeedHistory(Flyway flyway) {
        ValidateResult validation = flyway.validateWithResult();
        if (validation.validationSuccessful || validation.invalidMigrations.isEmpty()) {
            return;
        }

        Integer appliedV10Checksum = Arrays.stream(flyway.info().all())
                .filter(migration -> migration.getVersion() != null
                        && "10".equals(migration.getVersion().getVersion()))
                .map(MigrationInfo::getAppliedChecksum)
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null);

        boolean knownHistoryOnly = validation.invalidMigrations.stream()
                .allMatch(migration -> isMovedSeedMigration(migration, appliedV10Checksum));
        if (knownHistoryOnly) {
            log.warn("Repairing Flyway history for seed migrations moved out of application resources");
            flyway.repair();
            flyway.validate();
        }
    }

    private static boolean isMovedSeedMigration(ValidateOutput migration, Integer appliedV10Checksum) {
        if (migration.errorDetails.errorCode == CoreErrorCode.APPLIED_VERSIONED_MIGRATION_NOT_RESOLVED) {
            return MOVED_SEED_MIGRATIONS.get(migration.version) != null
                    && MOVED_SEED_MIGRATIONS.get(migration.version).equals(migration.description);
        }
        return migration.errorDetails.errorCode == CoreErrorCode.CHECKSUM_MISMATCH
                && "10".equals(migration.version)
                && Integer.valueOf(OLD_V10_CHECKSUM).equals(appliedV10Checksum);
    }

    /** Makes the JPA EntityManagerFactory wait until the migrations have run. */
    @Bean
    public static EntityManagerFactoryDependsOnPostProcessor flywayDependsOnPostProcessor() {
        return new EntityManagerFactoryDependsOnPostProcessor("flyway");
    }
}
