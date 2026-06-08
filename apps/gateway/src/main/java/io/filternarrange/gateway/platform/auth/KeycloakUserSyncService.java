// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.platform.auth;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * Plan G §T3 — on first Keycloak login (or every login after a profile
 * change), upsert the user row and mirror the realm roles into the
 * subscriptions + admin columns.
 *
 * <p>Loaded only when {@code AUTH_PROVIDER=keycloak} so the spring-jwt
 * path keeps booting without a JwtDecoder.
 */
@Service
public class KeycloakUserSyncService {

    private final JdbcTemplate jdbc;

    public KeycloakUserSyncService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    public UUID upsertOnLogin(
        String subject, String email, String displayName, List<String> roles
    ) {
        boolean wantsPaid = roles.contains("paid");
        boolean isAdmin = roles.contains("admin");

        UUID existing = jdbc.query(
            "SELECT id FROM users WHERE external_id = ? "
                + "OR (external_id IS NULL AND email = ?) LIMIT 1",
            ps -> {
                ps.setString(1, subject);
                ps.setString(2, email);
            },
            rs -> rs.next() ? UUID.fromString(rs.getString("id")) : null
        );

        UUID userId = existing != null ? existing : UUID.randomUUID();

        if (existing == null) {
            jdbc.update(
                "INSERT INTO users (id, email, external_id, display_name, created_at, last_login_at) "
                    + "VALUES (?, ?, ?, ?, now(), now())",
                userId, email, subject, displayName
            );
        } else {
            jdbc.update(
                "UPDATE users SET external_id = ?, "
                    + "email = COALESCE(?, email), "
                    + "display_name = COALESCE(?, display_name), "
                    + "last_login_at = now() WHERE id = ?",
                subject, email, displayName, userId
            );
        }

        // Mirror Keycloak's 'paid' role into the active subscription. We can't
        // ON CONFLICT (user_id) WHERE status='active' directly — Postgres
        // doesn't accept WHERE on the ON CONFLICT target — so cancel any
        // existing active row first and insert fresh.
        String desiredTier = wantsPaid ? "paid" : "free";
        jdbc.update(
            "UPDATE subscriptions SET status = 'cancelled' "
                + "WHERE user_id = ? AND status = 'active' AND tier <> ?",
            userId, desiredTier
        );
        jdbc.update(
            "INSERT INTO subscriptions(id, user_id, tier, status, started_at) "
                + "SELECT ?, ?, ?, 'active', now() "
                + "WHERE NOT EXISTS ("
                + "  SELECT 1 FROM subscriptions WHERE user_id = ? AND status = 'active'"
                + ")",
            UUID.randomUUID(), userId, desiredTier, userId
        );

        // Mirror admin flag if the column exists. Plan B's V1__users.sql
        // doesn't ship an 'admin' column yet, so swallow the missing-column
        // error — Plan H follow-up adds the column via V11.
        try {
            jdbc.update("UPDATE users SET admin = ? WHERE id = ?", isAdmin, userId);
        } catch (Exception ignored) {
            // users.admin not present — skip
        }

        return userId;
    }
}
