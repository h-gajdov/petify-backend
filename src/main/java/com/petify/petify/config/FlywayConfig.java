package com.petify.petify.config;

import javax.sql.DataSource;

import org.flywaydb.core.Flyway;
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

    @Bean(initMethod = "migrate")
    public Flyway flyway(DataSource dataSource,
                         @Value("${spring.flyway.locations:classpath:db/migration}") String[] locations,
                         @Value("${spring.flyway.baseline-on-migrate:false}") boolean baselineOnMigrate,
                         @Value("${spring.flyway.baseline-version:1}") String baselineVersion) {
        return Flyway.configure()
                .dataSource(dataSource)
                .locations(locations)
                .baselineOnMigrate(baselineOnMigrate)
                .baselineVersion(baselineVersion)
                .load();
    }

    /** Makes the JPA EntityManagerFactory wait until the migrations have run. */
    @Bean
    public static EntityManagerFactoryDependsOnPostProcessor flywayDependsOnPostProcessor() {
        return new EntityManagerFactoryDependsOnPostProcessor("flyway");
    }
}
