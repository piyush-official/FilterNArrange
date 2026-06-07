// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.api.recipe;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.recipe.RecipeService;
import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Plan F §T16 — recipes CRUD. ``FeatureGateFilter`` enforces paid-tier access
 * (the path ``/api/v1/recipes`` maps to the ``recipe-crud`` registry entry).
 */
@RestController
@RequestMapping("/api/v1/recipes")
public class RecipeController {

    private final RecipeService svc;
    private final ObjectMapper json;

    public RecipeController(RecipeService svc, ObjectMapper json) {
        this.svc = svc;
        this.json = json;
    }

    public record RecipeDto(
        String id,
        String name,
        JsonNode recipe,
        String createdAt,
        String updatedAt
    ) {
        static RecipeDto of(Recipe r, ObjectMapper m) {
            try {
                return new RecipeDto(
                    r.id().toString(),
                    r.name(),
                    m.readTree(r.recipeJson()),
                    r.createdAt().toString(),
                    r.updatedAt().toString()
                );
            } catch (Exception e) {
                throw new IllegalStateException("Recipe blob is not valid JSON", e);
            }
        }
    }

    public record CreateBody(String name, JsonNode recipe) {}

    @GetMapping
    public List<RecipeDto> list() {
        return svc.list(CurrentUser.id()).stream()
            .map(r -> RecipeDto.of(r, json)).toList();
    }

    @PostMapping
    public ResponseEntity<RecipeDto> create(@RequestBody CreateBody body) {
        Recipe r = svc.create(
            CurrentUser.id(), body.name(), body.recipe().toString()
        );
        return ResponseEntity.status(201).body(RecipeDto.of(r, json));
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable UUID id) {
        return svc.get(CurrentUser.id(), id)
            .<ResponseEntity<?>>map(r -> ResponseEntity.ok(RecipeDto.of(r, json)))
            .orElseGet(() -> ResponseEntity.status(404).body(notFound(id)));
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> update(
        @PathVariable UUID id, @RequestBody CreateBody body
    ) {
        return svc.update(
                CurrentUser.id(), id, body.name(), body.recipe().toString()
            )
            .<ResponseEntity<?>>map(r -> ResponseEntity.ok(RecipeDto.of(r, json)))
            .orElseGet(() -> ResponseEntity.status(404).body(notFound(id)));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable UUID id) {
        return svc.delete(CurrentUser.id(), id)
            ? ResponseEntity.noContent().build()
            : ResponseEntity.status(404).body(notFound(id));
    }

    private static Map<String, String> notFound(UUID id) {
        return Map.of(
            "code", "RECIPE_NOT_FOUND",
            "message", "Recipe " + id + " not found."
        );
    }
}
