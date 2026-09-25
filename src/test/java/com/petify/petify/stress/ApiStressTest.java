package com.petify.petify.stress;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

@Tag("stress")
class ApiStressTest {
    private final String baseUrl = System.getProperty("stress.baseUrl", "http://localhost:8081");
    private final int users = Integer.getInteger("stress.users", 20);
    private final int requestsPerUser = Integer.getInteger("stress.requests", 10);
    private final HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5)).build();
    private final JsonMapper json = JsonMapper.builder().build();

    @Test
    void publicListingsHandleConcurrentRequests() throws Exception {
        checkUnderLoad("/api/public/listings", null);
    }

    @Test
    void activeListingsHandleConcurrentRequests() throws Exception {
        checkUnderLoad("/api/listings/active", null);
    }

    @Test
    void clinicsHandleConcurrentRequests() throws Exception {
        checkUnderLoad("/api/clinics", null);
    }

    @Test
    void listingDetailsHandleConcurrentRequests() throws Exception {
        JsonNode listings = getJson("/api/public/listings");
        assertTrue(listings.isArray() && !listings.isEmpty(), "Create an active listing before running this test");
        long listingId = listings.get(0).path("listingId").asLong();
        assertTrue(listingId > 0, "Expected a positive listing ID");
        checkUnderLoad("/api/listings/" + listingId, listingId);
    }

    private void checkUnderLoad(String path, Long expectedListingId) throws Exception {
        assertTrue(users >= 1 && users <= 200, "stress.users must be between 1 and 200");
        assertTrue(requestsPerUser >= 1 && requestsPerUser <= 1000,
                "stress.requests must be between 1 and 1000");
        getJson(path); 

        var workers = Executors.newFixedThreadPool(users);
        var start = new CountDownLatch(1);
        var tasks = new ArrayList<Callable<Void>>();
        for (int user = 0; user < users; user++) {
            tasks.add(() -> {
                start.await();
                for (int request = 0; request < requestsPerUser; request++) {
                    JsonNode body = getJson(path);
                    if (expectedListingId == null) {
                        assertTrue(body.isArray(), path + " should return a JSON array");
                    } else {
                        assertEquals(expectedListingId.longValue(), body.path("listingId").asLong(),
                                "Response should contain the requested listing");
                    }
                }
                return null;
            });
        }

        long started = System.nanoTime();
        try {
            var results = new ArrayList<java.util.concurrent.Future<Void>>();
            for (var task : tasks) results.add(workers.submit(task));
            start.countDown();
            long deadline = System.nanoTime() + TimeUnit.MINUTES.toNanos(2);
            for (var result : results) {
                result.get(Math.max(1, deadline - System.nanoTime()), TimeUnit.NANOSECONDS);
            }
            long elapsed = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started);
            System.out.printf("%s: %d users, %d successful requests, %d ms total%n",
                    path, users, users * requestsPerUser, elapsed);
        } finally {
            workers.shutdownNow();
            assertTrue(workers.awaitTermination(15, TimeUnit.SECONDS), "Workers did not stop");
        }
    }

    private JsonNode getJson(String path) throws Exception {
        var request = HttpRequest.newBuilder(URI.create(baseUrl.replaceAll("/+$", "") + path))
                .timeout(Duration.ofSeconds(10)).GET().build();
        HttpResponse<String> response;
        try {
            response = client.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException e) {
            throw new AssertionError("Cannot complete request to " + baseUrl + path
                    + ". Make sure PostgreSQL and the backend are running.", e);
        }
        assertEquals(200, response.statusCode(), "Unexpected HTTP status for " + path);
        return json.readTree(response.body());
    }
}
