// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.util.UUID;
public record ConvertRequest(@NotNull UUID uploadId,
                             @NotNull @Valid ColumnFilterSpecDto filter,
                             @NotNull @Pattern(regexp = "csv|json") String outputFormat) {}
