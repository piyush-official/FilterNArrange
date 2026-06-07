// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.domain.recipe.RecipeRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcRecipeRepository implements RecipeRepository {

    private final JdbcTemplate jdbc;

    public JdbcRecipeRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<Recipe> MAPPER = (rs, i) -> new Recipe(
        UUID.fromString(rs.getString("id")),
        UUID.fromString(rs.getString("user_id")),
        rs.getString("name"),
        rs.getString("recipe"),
        rs.getBoolean("is_shared"),
        rs.getTimestamp("created_at").toInstant(),
        rs.getTimestamp("updated_at").toInstant()
    );

    @Override
    public Recipe save(Recipe r) {
        jdbc.update(
            "INSERT INTO recipes(id, user_id, name, recipe, is_shared, created_at, updated_at) "
                + "VALUES (?, ?, ?, ?::jsonb, ?, ?, ?)",
            r.id(),
            r.userId(),
            r.name(),
            r.recipeJson(),
            r.isShared(),
            Timestamp.from(r.createdAt()),
            Timestamp.from(r.updatedAt())
        );
        return r;
    }

    @Override
    public Optional<Recipe> findByIdForUser(UUID id, UUID userId) {
        var rows = jdbc.query(
            "SELECT id, user_id, name, recipe, is_shared, created_at, updated_at "
                + "FROM recipes WHERE id = ? AND user_id = ?",
            MAPPER, id, userId
        );
        return rows.stream().findFirst();
    }

    @Override
    public List<Recipe> listForUser(UUID userId) {
        return jdbc.query(
            "SELECT id, user_id, name, recipe, is_shared, created_at, updated_at "
                + "FROM recipes WHERE user_id = ? ORDER BY updated_at DESC",
            MAPPER, userId
        );
    }

    @Override
    public boolean deleteForUser(UUID id, UUID userId) {
        return jdbc.update(
            "DELETE FROM recipes WHERE id = ? AND user_id = ?", id, userId
        ) > 0;
    }

    @Override
    public Optional<Recipe> update(
        UUID id, UUID userId, String newName, String newJson
    ) {
        int n = jdbc.update(
            "UPDATE recipes SET name = ?, recipe = ?::jsonb "
                + "WHERE id = ? AND user_id = ?",
            newName, newJson, id, userId
        );
        return n > 0 ? findByIdForUser(id, userId) : Optional.empty();
    }
}
