// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

@Repository
public class AuditLogRepository {

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;

    public AuditLogRepository(JdbcTemplate jdbc, ObjectMapper om) {
        this.jdbc = jdbc;
        this.om = om;
        this.jdbc.setQueryTimeout(3);  // spec §6
    }

    public void insert(UUID userId, String action, String target,
                       JsonNode metadata, Instant occurredAt) {
        try {
            String meta = metadata == null ? null : om.writeValueAsString(metadata);
            jdbc.update(
                "INSERT INTO audit_log(user_id, action, target, metadata, created_at) "
                    + "VALUES (?, ?, ?, ?::jsonb, ?)",
                userId, action, target, meta, Timestamp.from(occurredAt));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to write audit row", e);
        }
    }
}
