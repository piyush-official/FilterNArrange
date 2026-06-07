// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;
public record ColumnFilterSpecDto(@NotNull String kind, @NotEmpty List<String> keep) {}
