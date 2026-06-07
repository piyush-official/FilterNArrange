// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.dto;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.Instant;
import java.util.UUID;

public record JobResponse(
    UUID jobId,
    String status,
    String kind,
    JsonNode params,
    String resultRef,
    JsonNode error,
    Instant createdAt,
    Instant startedAt,
    Instant finishedAt
) {}
