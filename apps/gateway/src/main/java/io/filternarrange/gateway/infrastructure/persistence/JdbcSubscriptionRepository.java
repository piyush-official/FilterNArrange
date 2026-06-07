// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcSubscriptionRepository implements SubscriptionRepository {

    private final JdbcTemplate jdbc;

    public JdbcSubscriptionRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<Subscription> MAPPER = (rs, i) -> new Subscription(
        UUID.fromString(rs.getString("id")),
        UUID.fromString(rs.getString("user_id")),
        Tier.fromString(rs.getString("tier")),
        Subscription.Status.valueOf(
            rs.getString("status").toUpperCase(Locale.ROOT)
        ),
        rs.getTimestamp("started_at").toInstant(),
        rs.getTimestamp("expires_at") == null
            ? null : rs.getTimestamp("expires_at").toInstant(),
        rs.getString("external_ref")
    );

    @Override
    public Optional<Subscription> findActiveByUserId(UUID userId) {
        List<Subscription> rows = jdbc.query(
            "SELECT id, user_id, tier, status, started_at, expires_at, external_ref "
                + "FROM subscriptions WHERE user_id = ? AND status = 'active' "
                + "ORDER BY started_at DESC LIMIT 1",
            MAPPER, userId
        );
        return rows.stream().findFirst();
    }

    @Override
    public Subscription save(Subscription s) {
        jdbc.update(
            "INSERT INTO subscriptions"
                + "(id, user_id, tier, status, started_at, expires_at, external_ref) "
                + "VALUES (?, ?, ?, ?, ?, ?, ?)",
            s.id(),
            s.userId(),
            s.tier().wireValue(),
            s.status().name().toLowerCase(Locale.ROOT),
            Timestamp.from(s.startedAt()),
            s.expiresAt() == null ? null : Timestamp.from(s.expiresAt()),
            s.externalRef()
        );
        return s;
    }
}
