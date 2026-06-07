// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.analyze.dto;

import jakarta.validation.constraints.NotNull;
import java.util.Map;
import java.util.UUID;

public record AnalyzeRequest(@NotNull UUID uploadId,
                             @NotNull Map<String, Object> analysis,
                             Map<String, Object> filter) {}
