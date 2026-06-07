// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JobRepository {

    /** Spec §6 — 3s default JDBC query timeout. */
    private static final int DEFAULT_QUERY_TIMEOUT_SECONDS = 3;

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;
    private final RowMapper<Job> mapper;

    public JobRepository(JdbcTemplate jdbc, ObjectMapper om) {
        this.jdbc = jdbc;
        this.om = om;
        this.jdbc.setQueryTimeout(DEFAULT_QUERY_TIMEOUT_SECONDS);
        this.mapper = (rs, i) -> {
            try {
                JsonNode params = om.readTree(rs.getString("params"));
                String errStr = rs.getString("error");
                JsonNode error = errStr == null ? null : om.readTree(errStr);
                Timestamp started = rs.getTimestamp("started_at");
                Timestamp finished = rs.getTimestamp("finished_at");
                return new Job(
                    UUID.fromString(rs.getString("id")),
                    UUID.fromString(rs.getString("user_id")),
                    JobKind.fromWire(rs.getString("kind")),
                    JobStatus.valueOf(rs.getString("status").toUpperCase()),
                    params,
                    rs.getString("result_ref"),
                    error,
                    rs.getInt("priority"),
                    rs.getTimestamp("created_at").toInstant(),
                    started == null ? null : started.toInstant(),
                    finished == null ? null : finished.toInstant());
            } catch (Exception e) {
                throw new IllegalStateException("Failed to map jobs row", e);
            }
        };
    }

    public void insert(Job j) {
        jdbc.update(
            "INSERT INTO jobs(id, user_id, kind, status, params, priority, created_at) "
                + "VALUES (?, ?, ?, ?, ?::jsonb, ?, ?)",
            j.id(), j.userId(), j.kind().wire(), j.status().name().toLowerCase(),
            asJson(j.params()), j.priority(), Timestamp.from(j.createdAt()));
    }

    public Optional<Job> findById(UUID id) {
        List<Job> rs = jdbc.query("SELECT * FROM jobs WHERE id = ?", mapper, id);
        return rs.isEmpty() ? Optional.empty() : Optional.of(rs.get(0));
    }

    public List<Job> findRecentByUser(UUID userId, int limit) {
        return jdbc.query(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            mapper, userId, limit);
    }

    public void updateStatus(Job j) {
        jdbc.update(
            "UPDATE jobs SET status = ?, started_at = ?, finished_at = ?, "
                + "result_ref = ?, error = ?::jsonb WHERE id = ?",
            j.status().name().toLowerCase(),
            j.startedAt() == null ? null : Timestamp.from(j.startedAt()),
            j.finishedAt() == null ? null : Timestamp.from(j.finishedAt()),
            j.resultRef(),
            asJson(j.error()),
            j.id());
    }

    private String asJson(JsonNode n) {
        if (n == null) return null;
        try { return om.writeValueAsString(n); }
        catch (Exception e) { throw new IllegalStateException(e); }
    }
}
