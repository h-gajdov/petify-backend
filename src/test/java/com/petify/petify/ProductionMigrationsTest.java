package com.petify.petify;

import java.sql.DriverManager;

import com.petify.petify.config.FlywayConfig;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;

import static org.assertj.core.api.Assertions.assertThat;

@Testcontainers
class ProductionMigrationsTest {
    @Container
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:15-alpine");

    @Test
    void applicationMigrationsCreateSchemaWithoutSampleData() throws Exception {
        var dataSource = new DriverManagerDataSource(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
        new FlywayConfig().flyway(
                dataSource, new String[]{"classpath:db/migration"}, false, "1").migrate();

        try (var connection = DriverManager.getConnection(
                postgres.getJdbcUrl(), postgres.getUsername(), postgres.getPassword());
             var statement = connection.createStatement()) {
            for (String table : new String[]{"users", "vet_clinics", "animals", "listings"}) {
                try (var rows = statement.executeQuery("SELECT COUNT(*) FROM " + table)) {
                    assertThat(rows.next()).isTrue();
                    assertThat(rows.getLong(1)).as(table).isZero();
                }
            }
        }
    }
}
