// SPDX-License-Identifier: Apache-2.0
package io.filternarrange.gateway.application.recipe;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.domain.recipe.RecipeRepository;
import io.filternarrange.gateway.infrastructure.messaging.AuditEventPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * Plan F §T15 — recipe CRUD with audit emission on every mutation. Audit
 * failures are logged but do not roll back the write — the repository is the
 * source of truth; audit is a downstream concern.
 */
@Service
public class RecipeService {

    private static final Logger log = LoggerFactory.getLogger(RecipeService.class);

    private final RecipeRepository repo;
    private final AuditEventPublisher audit;
    private final ObjectMapper om;

    public RecipeService(RecipeRepository repo, AuditEventPublisher audit, ObjectMapper om) {
        this.repo = repo;
        this.audit = audit;
        this.om = om;
    }

    public Recipe create(UUID userId, String name, String json) {
        Recipe r = new Recipe(
            UUID.randomUUID(), userId, name, json, false,
            Instant.now(), Instant.now()
        );
        Recipe saved = repo.save(r);
        tryAudit(userId, "recipe.create", saved.id().toString(),
            Map.of("name", name));
        return saved;
    }

    public Optional<Recipe> get(UUID userId, UUID id) {
        return repo.findByIdForUser(id, userId);
    }

    public List<Recipe> list(UUID userId) {
        return repo.listForUser(userId);
    }

    public Optional<Recipe> update(UUID userId, UUID id, String newName, String newJson) {
        Optional<Recipe> out = repo.update(id, userId, newName, newJson);
        out.ifPresent(r -> tryAudit(userId, "recipe.update", id.toString(),
            Map.of("name", newName)));
        return out;
    }

    public boolean delete(UUID userId, UUID id) {
        boolean removed = repo.deleteForUser(id, userId);
        if (removed) {
            tryAudit(userId, "recipe.delete", id.toString(), Map.of());
        }
        return removed;
    }

    private void tryAudit(
        UUID userId, String action, String target, Map<String, ?> meta
    ) {
        try {
            audit.publish(
                userId, action, target, om.valueToTree(meta),
                UUID.randomUUID().toString()
            );
        } catch (Exception e) {
            log.warn("audit emit failed for {} {}: {}", action, target, e.toString());
        }
    }
}
