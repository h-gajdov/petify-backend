package com.petify.petify.e2e;

import com.petify.petify.PetifyApplication;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testng.annotations.AfterClass;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.testng.Assert.*;


public class PetifyE2EIT {
    private final PostgreSQLContainer database = new PostgreSQLContainer("postgres:15-alpine");
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    private final JsonMapper json = JsonMapper.builder().build();
    private ConfigurableApplicationContext application;
    private String baseUrl;
    private static final String PASSWORD = "E2e-password-123!";

    @BeforeClass(alwaysRun = true)
    public void startApplication() {
        database.start();
        application = new SpringApplicationBuilder(PetifyApplication.class).run(new String[]{
            "--spring.profiles.active=e2e", "--spring.config.import=", "--server.port=0",
                "--spring.datasource.url=" + database.getJdbcUrl(),
                "--spring.datasource.username=" + database.getUsername(),
                "--spring.datasource.password=" + database.getPassword(),
                "--spring.flyway.enabled=true", "--spring.flyway.baseline-on-migrate=false",
                "--spring.jpa.hibernate.ddl-auto=none", "--spring.jpa.show-sql=false",
                "--logging.level.root=WARN", "--logging.level.org.hibernate.SQL=WARN",
                "--logging.level.com.zaxxer.hikari=WARN", "--logging.level.com.zaxxer.hikari.HikariConfig=WARN",
                "--logging.level.com.zaxxer.hikari.HikariDataSource=WARN", "--logging.level.org.flywaydb=WARN"});
        baseUrl = "http://localhost:" + ((WebServerApplicationContext) application).getWebServer().getPort();
    }

    @AfterClass(alwaysRun = true)
    public void stopApplication() {
        try {
            if (application != null) application.close();
        } finally {
            database.stop();
        }
    }

    @Test
    public void registrationCanLoginWithUsernameAndEmail() throws Exception {
        JsonNode user = register();
        assertTrue(user.path("userId").asLong() > 0);
        assertEquals(user.path("userType").asString(), "CLIENT");
        assertEquals(user.path("firstName").asString(), "End");
        assertEquals(user.path("lastName").asString(), "ToEnd");
        assertFalse(user.has("password"));
        for (String identifier : new String[]{user.path("username").asString(), user.path("email").asString()}) {
            JsonNode loggedIn = login(identifier, PASSWORD, 200);
            assertEquals(loggedIn.path("userId").asLong(), user.path("userId").asLong());
            assertEquals(loggedIn.path("userType").asString(), "CLIENT");
        }
    }

    @DataProvider
    public Object[][] duplicateFields() {
        return new Object[][]{{"username"}, {"email"}};
    }

    @Test(dataProvider = "duplicateFields")
    public void duplicateRegistrationIsRejected(String field) throws Exception {
        JsonNode user = register();
        Map<String, Object> duplicate = signupBody();
        duplicate.put(field, user.path(field).asString());
        request("POST", "/api/auth/signup", duplicate, null, 400);
        assertEquals(login(user.path("username").asString(), PASSWORD, 200).path("userId").asLong(),
                user.path("userId").asLong());
        login(duplicate.get(field.equals("username") ? "email" : "username").toString(), PASSWORD, 401);
    }

    @Test
    public void incorrectPasswordAndUnknownUserAreRejected() throws Exception {
        JsonNode user = register();
        assertEquals(login(user.path("username").asString(), "incorrect", 401).path("message").asString(),
                "Invalid username or password");
        assertEquals(login("missing-" + UUID.randomUUID(), PASSWORD, 401).path("message").asString(),
                "Invalid username or password");
    }

    @Test
    public void creatingPetPersistsDetailsAndPromotesClientToOwner() throws Exception {
        JsonNode user = register();
        long userId = user.path("userId").asLong();
        JsonNode created = request("POST", "/api/users/" + userId + "/pets", petBody(), userId, 201);
        long petId = created.path("animalId").asLong();
        assertTrue(petId > 0);
        JsonNode fetched = request("GET", "/api/pets/" + petId, null, null, 200);
        assertEquals(fetched.path("ownerUserId").asLong(), userId);
        petBody().forEach((key, value) -> assertEquals(fetched.path(key).asString(), value.toString(), key));
        assertEquals(login(user.path("username").asString(), PASSWORD, 200).path("userType").asString(), "OWNER");
    }

    @DataProvider
    public Object[][] requiredPetFields() {
        return new Object[][]{{"name", "Pet name is required"}, {"sex", "Pet sex is required"},
                {"type", "Pet type is required"}, {"species", "Pet species is required"}};
    }

    @Test(dataProvider = "requiredPetFields")
    public void invalidPetDoesNotPromoteClient(String field, String error) throws Exception {
        JsonNode user = register();
        long userId = user.path("userId").asLong();
        Map<String, Object> body = new HashMap<>(petBody());
        body.remove(field);
        assertEquals(request("POST", "/api/users/" + userId + "/pets", body, userId, 400)
                .path("error").asString(), error);
        assertEquals(login(user.path("username").asString(), PASSWORD, 200).path("userType").asString(), "CLIENT");
        assertEquals(request("GET", "/api/users/" + userId + "/pets", null, null, 200).size(), 0);
    }

    @Test
    public void cannotCreatePetForAnotherUser() throws Exception {
        JsonNode user = register();
        long otherId = register().path("userId").asLong();
        assertEquals(request("POST", "/api/users/" + otherId + "/pets", petBody(),
                user.path("userId").asLong(), 403).path("error").asString(), "You can only create pets for yourself");
        assertEquals(request("GET", "/api/users/" + otherId + "/pets", null, null, 200).size(), 0);
    }

    @Test
    public void missingPetReturnsNotFound() throws Exception {
        assertEquals(request("GET", "/api/pets/9223372036854775807", null, null, 404)
                .path("error").asString(), "Pet not found");
    }

    private JsonNode register() throws Exception {
        return request("POST", "/api/auth/signup", signupBody(), null, 201);
    }

    private Map<String, Object> signupBody() {
        String username = "e2e_" + UUID.randomUUID().toString().replace("-", "").substring(0, 20);
        return new HashMap<>(Map.of("username", username, "email", username + "@example.test",
                "password", PASSWORD, "firstName", "End", "lastName", "ToEnd"));
    }

    private Map<String, Object> petBody() {
        return Map.of("name", "Luna E2E", "sex", "FEMALE", "type", "DOG", "species", "Dog",
                "breed", "Labrador", "dateOfBirth", "2023-01-15", "locatedName", "Skopje");
    }

    private JsonNode login(String identifier, String password, int status) throws Exception {
        return request("POST", "/api/auth/login", Map.of("username", identifier, "password", password), null, status);
    }

    private JsonNode request(String method, String path, Object body, Long userId, int expectedStatus) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder(URI.create(baseUrl + path))
                .timeout(Duration.ofSeconds(20)).header("Accept", "application/json");
        if (userId != null) builder.header("X-User-Id", userId.toString());
        if (body != null) builder.header("Content-Type", "application/json");
        builder.method(method, body == null ? HttpRequest.BodyPublishers.noBody()
                : HttpRequest.BodyPublishers.ofString(json.writeValueAsString(body)));
        HttpResponse<String> response = http.send(builder.build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(response.statusCode(), expectedStatus, method + " " + path + ": " + response.body());
        assertTrue(response.headers().firstValue("Content-Type").orElse("").contains("application/json"));
        return json.readTree(response.body());
    }
}
