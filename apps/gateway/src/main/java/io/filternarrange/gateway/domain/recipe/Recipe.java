// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.recipe;

import java.time.Instant;
import java.util.UUID;

public record Recipe(
    UUID id,
    UUID userId,
    String name,
    String recipeJson,
    boolean isShared,
    Instant createdAt,
    Instant updatedAt
) {}
