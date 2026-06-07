// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcFormatRequestRepository implements FormatRequestRepository {

    private final JdbcTemplate jdbc;

    public JdbcFormatRequestRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<FormatRequest> MAPPER = (rs, i) -> new FormatRequest(
        UUID.fromString(rs.getString("id")),
        UUID.fromString(rs.getString("user_id")),
        rs.getString("sample_ref"),
        rs.getString("user_label"),
        FormatRequest.Status.fromWire(rs.getString("status")),
        rs.getInt("priority"),
        (Integer) rs.getObject("github_issue"),
        rs.getTimestamp("created_at").toInstant(),
        rs.getTimestamp("resolved_at") == null
            ? null : rs.getTimestamp("resolved_at").toInstant()
    );

    @Override
    public FormatRequest save(FormatRequest fr) {
        jdbc.update(
            "INSERT INTO format_requests"
                + "(id, user_id, sample_ref, user_label, status, priority, github_issue, created_at, resolved_at) "
                + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            fr.id(),
            fr.userId(),
            fr.sampleRef(),
            fr.userLabel(),
            fr.status().wire(),
            fr.priority(),
            fr.githubIssue(),
            Timestamp.from(fr.createdAt()),
            fr.resolvedAt() == null ? null : Timestamp.from(fr.resolvedAt())
        );
        return fr;
    }

    @Override
    public Optional<FormatRequest> findById(UUID id) {
        var rows = jdbc.query(
            "SELECT id, user_id, sample_ref, user_label, status, priority, "
                + "github_issue, created_at, resolved_at "
                + "FROM format_requests WHERE id = ?",
            MAPPER, id
        );
        return rows.stream().findFirst();
    }

    @Override
    public List<FormatRequest> listOpen() {
        return jdbc.query(
            "SELECT id, user_id, sample_ref, user_label, status, priority, "
                + "github_issue, created_at, resolved_at "
                + "FROM format_requests "
                + "WHERE status IN ('open','triaged','in-progress') "
                + "ORDER BY priority DESC, created_at ASC",
            MAPPER
        );
    }

    @Override
    public boolean updateStatus(UUID id, FormatRequest.Status next, Integer githubIssue) {
        boolean terminal = next == FormatRequest.Status.SHIPPED
            || next == FormatRequest.Status.REJECTED;
        int n = jdbc.update(
            "UPDATE format_requests "
                + "SET status = ?, github_issue = COALESCE(?, github_issue), "
                + "    resolved_at = CASE WHEN ? THEN now() ELSE resolved_at END "
                + "WHERE id = ?",
            next.wire(), githubIssue, terminal, id
        );
        return n > 0;
    }
}
