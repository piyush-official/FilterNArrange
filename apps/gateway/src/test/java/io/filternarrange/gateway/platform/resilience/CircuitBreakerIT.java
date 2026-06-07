// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.resilience;

import com.github.tomakehurst.wiremock.WireMockServer;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.infrastructure.http.DataEngineHttpClient;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Plan D §6 — verify the dataEngine circuit-breaker opens after the configured
 * failure threshold and subsequent calls short-circuit with
 * {@link CallNotPermittedException}. WireMock impersonates a flapping data-engine.
 */
@SpringBootTest
@Testcontainers
class CircuitBreakerIT {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    static MinIOContainer MINIO =
        new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    private static WireMockServer mock;

    @BeforeAll
    static void up() {
        mock = new WireMockServer(0);
        mock.start();
    }

    @AfterAll
    static void down() {
        if (mock != null) {
            mock.stop();
        }
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
        r.add("data-engine.base-url", () -> mock.baseUrl());
    }

    @Autowired
    private CircuitBreakerRegistry registry;
    @Autowired
    private DataEngineHttpClient client;

    @BeforeEach
    void resetBreaker() {
        registry.circuitBreaker("dataEngine").reset();
        mock.resetAll();
    }

    @Test
    void breaker_opens_after_minimum_failures_threshold() {
        mock.stubFor(post(urlEqualTo("/detect"))
            .willReturn(aResponse().withStatus(503)));

        CircuitBreaker cb = registry.circuitBreaker("dataEngine");
        EngineDtos.RefRequest req = new EngineDtos.RefRequest("uploads/x.csv");

        for (int i = 0; i < 10; i++) {
            try {
                client.detect(req);
            } catch (Throwable ignored) {
                // Expected — keep driving the breaker until it trips.
            }
            if (cb.getState() == CircuitBreaker.State.OPEN) {
                break;
            }
        }

        assertThat(cb.getState()).isEqualTo(CircuitBreaker.State.OPEN);
    }

    @Test
    void open_breaker_short_circuits_subsequent_calls() {
        CircuitBreaker cb = registry.circuitBreaker("dataEngine");
        cb.transitionToOpenState();
        assertThatThrownBy(() -> client.detect(new EngineDtos.RefRequest("uploads/y.csv")))
            .isInstanceOf(CallNotPermittedException.class);
    }
}
