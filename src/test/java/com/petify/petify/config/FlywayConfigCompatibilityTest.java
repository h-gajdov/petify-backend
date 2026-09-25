package com.petify.petify.config;

import java.sql.DriverManager;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@Testcontainers
class FlywayConfigCompatibilityTest {
    @Container
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:15-alpine");

    @Test
    void repairsOnlyTheKnownLegacySeedHistory() throws Exception {
        Flyway.configure()
                .dataSource(postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword())
                .locations("classpath:db/migration", "classpath:db/test-seed")
                .load()
                .migrate();

        // Represent a database migrated before seeds moved to test resources.
        try (var connection = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
             var statement = connection.createStatement()) {
            statement.executeUpdate("DELETE FROM flyway_schema_history WHERE version = '10.1'");
            statement.executeUpdate("UPDATE flyway_schema_history SET checksum = 659034310 WHERE version = '10'");
        }

        var dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        Flyway applicationFlyway = new FlywayConfig().flyway(
                dataSource, new String[]{"classpath:db/migration"}, false, "1");
        applicationFlyway.migrate();
        assertThat(applicationFlyway.validateWithResult().validationSuccessful).isTrue();

        // An unrelated checksum change must still be reported to the operator.
        try (var connection = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
             var statement = connection.createStatement()) {
            statement.executeUpdate("UPDATE flyway_schema_history SET checksum = 1 WHERE version = '10'");
        }
        Flyway unchanged = new FlywayConfig().flyway(
                dataSource, new String[]{"classpath:db/migration"}, false, "1");
        assertThat(applicationFlyway.validateWithResult().validationSuccessful).isFalse();
        assertThatThrownBy(unchanged::migrate).hasMessageContaining("checksum mismatch");
    }
}
