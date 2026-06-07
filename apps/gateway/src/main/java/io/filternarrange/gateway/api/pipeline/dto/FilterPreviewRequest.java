// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline.dto;

import jakarta.validation.constraints.NotNull;

import java.util.Map;
import java.util.UUID;

/**
 * Plan C: filter shape is a passthrough Map so column / row / expression /
 * regex specs all flow through the same endpoint. The data-engine validates.
 */
public record FilterPreviewRequest(@NotNull UUID uploadId,
                                   @NotNull Map<String, Object> filter,
                                   Integer sampleSize) {}
