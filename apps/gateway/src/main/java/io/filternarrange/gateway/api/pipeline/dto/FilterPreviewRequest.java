// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
public record FilterPreviewRequest(@NotNull UUID uploadId, @NotNull @Valid ColumnFilterSpecDto filter, Integer sampleSize) {}
