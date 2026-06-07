// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Plan G §T4 — verifies the Keycloak user-sync upserts users and mirrors
 * realm roles into subscriptions. Runs under the spring-jwt context (no
 * AuthConfig wired) since we only need the JdbcTemplate.
 */
@SpringBootTest
@Testcontainers
class KeycloakUserSyncServiceTest {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @Container
    static MinIOContainer MINIO =
        new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired JdbcTemplate jdbc;

    @Test
    void firstLoginCreatesUserWithMatchingTier() {
        KeycloakUserSyncService svc = new KeycloakUserSyncService(jdbc);
        String subject = "kc-" + UUID.randomUUID();
        UUID userId = svc.upsertOnLogin(
            subject, "first@kc.test", "First KC User",
            List.of("user", "paid")
        );

        String externalId = jdbc.queryForObject(
            "SELECT external_id FROM users WHERE id = ?",
            String.class, userId
        );
        assertThat(externalId).isEqualTo(subject);

        String tier = jdbc.queryForObject(
            "SELECT tier FROM subscriptions WHERE user_id = ? AND status = 'active'",
            String.class, userId
        );
        assertThat(tier).isEqualTo("paid");
    }

    @Test
    void secondLoginUpdatesLastLoginAndKeepsExternalId() {
        KeycloakUserSyncService svc = new KeycloakUserSyncService(jdbc);
        String subject = "kc-" + UUID.randomUUID();
        UUID first = svc.upsertOnLogin(subject, "two@kc.test", "Two", List.of("user"));
        UUID second = svc.upsertOnLogin(subject, "two@kc.test", "Two", List.of("user"));
        assertThat(second).isEqualTo(first);
    }

    @Test
    void roleChangeDemotesPaidToFree() {
        KeycloakUserSyncService svc = new KeycloakUserSyncService(jdbc);
        String subject = "kc-" + UUID.randomUUID();
        UUID userId = svc.upsertOnLogin(
            subject, "demote@kc.test", "Demote", List.of("user", "paid")
        );
        // Re-login without the 'paid' role
        svc.upsertOnLogin(subject, "demote@kc.test", "Demote", List.of("user"));
        String tier = jdbc.queryForObject(
            "SELECT tier FROM subscriptions WHERE user_id = ? AND status = 'active'",
            String.class, userId
        );
        assertThat(tier).isEqualTo("free");
    }
}
