// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import java.time.Instant;
import java.util.UUID;

/**
 * Read-only projection of the jobs table for callers that don't need the
 * full {@link io.filternarrange.gateway.domain.job.Job} aggregate (e.g. the
 * jobs list view). Plan D §3.
 */
public record JobRow(
    UUID id,
    UUID userId,
    String kind,
    String status,
    int priority,
    Instant createdAt,
    Instant startedAt,
    Instant finishedAt,
    String resultRef
) {}
