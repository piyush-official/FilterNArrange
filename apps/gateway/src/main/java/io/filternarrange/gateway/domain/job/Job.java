// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.job;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.Instant;
import java.util.UUID;

public record Job(
    UUID id,
    UUID userId,
    JobKind kind,
    JobStatus status,
    JsonNode params,
    String resultRef,
    JsonNode error,
    int priority,
    Instant createdAt,
    Instant startedAt,
    Instant finishedAt
) {
    public Job withStatus(JobStatus next) {
        if (!this.status.canTransitionTo(next)) {
            throw new IllegalStateException(
                "Invalid transition " + this.status + " -> " + next);
        }
        Instant startedAt = (next == JobStatus.RUNNING && this.startedAt == null)
                            ? Instant.now() : this.startedAt;
        Instant finishedAt = next.isTerminal() ? Instant.now() : this.finishedAt;
        return new Job(id, userId, kind, next, params, resultRef, error,
                       priority, createdAt, startedAt, finishedAt);
    }

    public Job withResult(String resultRef, JsonNode error) {
        return new Job(id, userId, kind, status, params, resultRef, error,
                       priority, createdAt, startedAt, finishedAt);
    }
}
