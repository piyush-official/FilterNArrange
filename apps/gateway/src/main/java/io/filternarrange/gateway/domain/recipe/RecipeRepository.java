// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.domain.recipe;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface RecipeRepository {
    Recipe save(Recipe r);

    Optional<Recipe> findByIdForUser(UUID id, UUID userId);

    List<Recipe> listForUser(UUID userId);

    boolean deleteForUser(UUID id, UUID userId);

    Optional<Recipe> update(UUID id, UUID userId, String newName, String newRecipeJson);
}
