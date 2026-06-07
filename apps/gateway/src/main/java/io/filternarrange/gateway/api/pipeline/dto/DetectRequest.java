// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
public record DetectRequest(@NotNull UUID uploadId) {}
