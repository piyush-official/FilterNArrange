# Plan F — Tiers, Quotas & Format-Request Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Realize the tier system (free vs paid) with all four open-core levers (file-size cap, daily-op quota, saved recipes + retention, advanced-feature gating) plus the format-request workflow (community-PR path always visible + maintainer-handled prioritized path for paid users).

**Architecture:** Spring Boot gateway gains a `TierResolver` + `QuotaFilter` chain that reads/writes Redis counters and consults Postgres `subscriptions` / `plugin_registry`. Kafka splits `topic.v1.jobs` into `.paid` / `.free` topics for genuine priority via separate consumer groups. A new `retention-worker` container (same Python image, `MODE=worker --retention`) purges aged blobs/rows. Frontend gains a billing pane, recipe CRUD, and a tier-gated format-request submission UI with a paired admin panel.

**Tech Stack:** Spring Boot 3 (Java 21) + Spring Security; Flyway; Postgres 16 + JSONB; Redis 7; Redpanda (Kafka API); Python 3.12 + FastAPI + APScheduler + aiokafka + minio-py + Octokit (`PyGithub`); React 18 + TypeScript + TanStack Query; Vitest / JUnit 5 / pytest / Playwright; Testcontainers.

**Spec reading (preamble — adjust-as-implied):** Spec §1 lists "advanced-feature gating (charts, SQL-mode filtering, schema inference, batch processing, API access — all paid-only)". The user message overrides for two items (`analysis-chart-suggest` and `analysis-schema-infer` stay free; `analysis-group-by` and `filter-expression` stay free). This plan follows the **user-message override** exactly and seeds `plugin_registry.required_tier = 'paid'` for: `job-kind:batch-filter`, `recipe:*` endpoints, `format-request:submit`, `ai:nl_to_filter`, `ai:auto_summary`, `ai:chart_suggest`, `ai:anomaly_detect`. Everything else stays `required_tier = 'free'` (NULL semantically means "free"). The preamble is captured inside `V8__plugin_registry.sql` as a SQL comment so the reading is auditable from the schema.

---

## File Structure

**Gateway (Java) — created:**
- `apps/gateway/src/main/resources/db/migration/V5__subscriptions.sql`
- `apps/gateway/src/main/resources/db/migration/V6__format_requests.sql`
- `apps/gateway/src/main/resources/db/migration/V7__recipes.sql`
- `apps/gateway/src/main/resources/db/migration/V8__plugin_registry.sql`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/Tier.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/TierConfig.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/Subscription.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/SubscriptionRepository.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcSubscriptionRepository.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/tier/TierResolver.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/QuotaFilter.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/IpRateLimitFilter.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/SizeLimitFilter.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/FeatureGateFilter.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/plugin/PluginRegistryService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/recipe/RecipeController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/recipe/RecipeService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/recipe/Recipe.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcRecipeRepository.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/formatrequest/FormatRequestController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/formatrequest/FormatRequestService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestKafkaProducer.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestConsumer.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/github/GithubIssueClient.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/admin/AdminFormatRequestController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/billing/BillingController.java`
- Tests under `apps/gateway/src/test/java/io/filternarrange/gateway/…` mirroring the above.

**Gateway (Java) — modified:**
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/job/JobController.java` — route producer to `topic.v1.jobs.paid|free`.
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/security/SecurityConfig.java` — wire filters, admin role.
- `apps/gateway/src/main/resources/application.yaml` — tier env-var bindings.

**Data-engine / worker (Python) — created:**
- `apps/data-engine/src/filternarrange_engine/retention/__init__.py`
- `apps/data-engine/src/filternarrange_engine/retention/sweeper.py`
- `apps/data-engine/src/filternarrange_engine/retention/cli.py`
- `apps/data-engine/src/filternarrange_engine/retention/config.py`
- Tests under `apps/data-engine/tests/retention/`.

**Data-engine — modified:**
- `apps/data-engine/src/filternarrange_engine/__main__.py` — add `--retention` flag.
- `apps/data-engine/pyproject.toml` — add `apscheduler`, `asyncpg` (if not already), `minio` deps.

**Contracts — modified:**
- `contracts/kafka/topic.v1.jobs.schema.json` — header note that schema is shared by `.paid` and `.free` topics.
- `contracts/kafka/topic.v1.format-requests.schema.json` — already exists from Plan D; add `github_issue` lifecycle field.
- `contracts/openapi/gateway-public.v1.yaml` — add `/billing`, `/recipes`, `/format-requests`, `/admin/format-requests` paths.

**Infra — modified:**
- `infra/docker-compose.yml` — add `retention-worker` service; add `python-worker-paid` and `python-worker-free` services with their respective topic subscriptions; add `GITHUB_TOKEN`, `GITHUB_REPO`, tier env vars.

**Frontend (TypeScript) — created:**
- `apps/frontend/src/features/billing/api/billingApi.ts`
- `apps/frontend/src/features/billing/ui/BillingPanel.tsx`
- `apps/frontend/src/features/billing/ui/TierBadge.tsx`
- `apps/frontend/src/features/billing/ui/QuotaMeter.tsx`
- `apps/frontend/src/features/recipes/api/recipesApi.ts`
- `apps/frontend/src/features/recipes/ui/RecipeList.tsx`
- `apps/frontend/src/features/recipes/ui/SaveRecipeButton.tsx`
- `apps/frontend/src/features/recipes/ui/RunRecipeButton.tsx`
- `apps/frontend/src/features/recipes/state/useRecipes.ts`
- `apps/frontend/src/features/format-request/api/formatRequestApi.ts`
- `apps/frontend/src/features/format-request/ui/FormatRequestBanner.tsx`
- `apps/frontend/src/features/format-request/ui/FormatRequestButton.tsx`
- `apps/frontend/src/features/admin/ui/AdminFormatRequestList.tsx`
- `apps/frontend/src/shared/ui/PaidGate.tsx`
- `apps/frontend/src/shared/lib/tier.ts`
- Vitest tests next to each component.

**Frontend — modified:**
- `apps/frontend/src/app/router.tsx` — `/account/billing`, `/recipes`, `/admin/format-requests`.

---

## Conventions Reminder

- Java package: `io.filternarrange.gateway`
- Python package: `filternarrange_engine`
- Conventional Commits everywhere.
- Error envelope: `{ code, plugin_id, message, trace_id }`. Stable `code` values introduced this plan: `TIER_QUOTA_EXCEEDED`, `PAYLOAD_TOO_LARGE`, `FEATURE_REQUIRES_PAID_TIER`, `IP_RATE_LIMITED`, `RECIPE_NOT_FOUND`, `FORMAT_REQUEST_NOT_FOUND`, `ADMIN_REQUIRED`.
- Plugin manifest TOML + entry-point discovery is **read** in this plan via `PluginRegistryService` (Plan C wrote it; Plan F adds the `required_tier` column).

---

## Task 1: Flyway migration V5 — `subscriptions`

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V5__subscriptions.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/migration/V5SubscriptionsMigrationTest.java`

- [ ] **Step 1: Write the failing migration test**

```java
package io.filternarrange.gateway.migration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
@Testcontainers
class V5SubscriptionsMigrationTest {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");

    @Autowired JdbcTemplate jdbc;

    @Test
    void subscriptionsTableExistsWithExpectedColumns() {
        List<Map<String, Object>> cols = jdbc.queryForList(
            "SELECT column_name, data_type FROM information_schema.columns " +
            "WHERE table_name = 'subscriptions' ORDER BY column_name");
        assertThat(cols).extracting(c -> c.get("column_name"))
            .contains("id", "user_id", "tier", "status", "started_at",
                      "expires_at", "external_ref", "created_at");
    }

    @Test
    void onlyOneActiveSubscriptionPerUser() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "u@test");
        jdbc.update("INSERT INTO subscriptions(id, user_id, tier, status, started_at) " +
                    "VALUES (?, ?, 'paid', 'active', now())", UUID.randomUUID(), userId);
        assertThatThrownBy(() ->
            jdbc.update("INSERT INTO subscriptions(id, user_id, tier, status, started_at) " +
                        "VALUES (?, ?, 'paid', 'active', now())", UUID.randomUUID(), userId)
        ).hasMessageContaining("one_active_sub_per_user");
    }

    @Test
    void tierCheckConstraintRejectsUnknown() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "u2@test");
        assertThatThrownBy(() ->
            jdbc.update("INSERT INTO subscriptions(id, user_id, tier, status, started_at) " +
                        "VALUES (?, ?, 'enterprise', 'active', now())",
                        UUID.randomUUID(), userId)
        ).hasMessageContaining("subscriptions_tier_check");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=V5SubscriptionsMigrationTest`
Expected: FAIL — relation `subscriptions` does not exist.

- [ ] **Step 3: Write the migration SQL**

```sql
-- V5__subscriptions.sql
-- Realizes spec §5 `subscriptions` table with one-active-sub-per-user invariant.

CREATE TABLE subscriptions (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tier         TEXT NOT NULL CHECK (tier IN ('free', 'paid')),
  status       TEXT NOT NULL CHECK (status IN ('active', 'cancelled', 'expired')),
  started_at   TIMESTAMPTZ NOT NULL,
  expires_at   TIMESTAMPTZ,
  external_ref TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX one_active_sub_per_user
  ON subscriptions(user_id) WHERE status = 'active';

CREATE INDEX subscriptions_user_recent
  ON subscriptions(user_id, created_at DESC);

-- Backfill: every existing user gets a free active subscription.
INSERT INTO subscriptions (id, user_id, tier, status, started_at)
SELECT gen_random_uuid(), id, 'free', 'active', now()
FROM users
WHERE NOT EXISTS (
  SELECT 1 FROM subscriptions s WHERE s.user_id = users.id AND s.status = 'active'
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=V5SubscriptionsMigrationTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V5__subscriptions.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/migration/V5SubscriptionsMigrationTest.java
git commit -m "feat(gateway): add subscriptions table with active-uniqueness invariant"
```

---

## Task 2: Flyway migration V6 — `format_requests`

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V6__format_requests.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/migration/V6FormatRequestsMigrationTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.migration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
class V6FormatRequestsMigrationTest {

    @Autowired JdbcTemplate jdbc;

    @Test
    void formatRequestsHasExpectedColumns() {
        List<Map<String, Object>> cols = jdbc.queryForList(
            "SELECT column_name FROM information_schema.columns " +
            "WHERE table_name = 'format_requests' ORDER BY column_name");
        assertThat(cols).extracting(c -> c.get("column_name"))
            .contains("id", "user_id", "sample_ref", "user_label", "status",
                      "priority", "github_issue", "created_at", "resolved_at");
    }

    @Test
    void statusCheckRejectsUnknown() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "fr@test");
        assertThatThrownBy(() ->
            jdbc.update("INSERT INTO format_requests(id, user_id, sample_ref, status) " +
                        "VALUES (?, ?, ?, 'invented')",
                        UUID.randomUUID(), userId, "format-samples/foo")
        ).hasMessageContaining("format_requests_status_check");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=V6FormatRequestsMigrationTest`
Expected: FAIL — relation does not exist.

- [ ] **Step 3: Write the migration**

```sql
-- V6__format_requests.sql
CREATE TABLE format_requests (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  sample_ref   TEXT NOT NULL,
  user_label   TEXT,
  status       TEXT NOT NULL DEFAULT 'open'
               CHECK (status IN ('open','triaged','in-progress','shipped','rejected')),
  priority     INT NOT NULL DEFAULT 0,
  github_issue INT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at  TIMESTAMPTZ
);

CREATE INDEX format_requests_status_open
  ON format_requests(status) WHERE status IN ('open', 'triaged', 'in-progress');

CREATE INDEX format_requests_user_recent
  ON format_requests(user_id, created_at DESC);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=V6FormatRequestsMigrationTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V6__format_requests.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/migration/V6FormatRequestsMigrationTest.java
git commit -m "feat(gateway): add format_requests table with status lifecycle constraint"
```

---

## Task 3: Flyway migration V7 — `recipes`

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V7__recipes.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/migration/V7RecipesMigrationTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.migration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThatThrownBy;

@SpringBootTest
class V7RecipesMigrationTest {

    @Autowired JdbcTemplate jdbc;

    @Test
    void recipeNameUniquePerUser() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "r@test");
        jdbc.update("INSERT INTO recipes(id, user_id, name, recipe) " +
                    "VALUES (?, ?, 'my-recipe', '{}'::jsonb)",
                    UUID.randomUUID(), userId);
        assertThatThrownBy(() ->
            jdbc.update("INSERT INTO recipes(id, user_id, name, recipe) " +
                        "VALUES (?, ?, 'my-recipe', '{}'::jsonb)",
                        UUID.randomUUID(), userId)
        ).hasMessageContaining("recipes_user_id_name_key");
    }

    @Test
    void recipeJsonbStored() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "r2@test");
        jdbc.update("INSERT INTO recipes(id, user_id, name, recipe) " +
                    "VALUES (?, ?, ?, ?::jsonb)",
                    UUID.randomUUID(), userId, "x", "{\"output\":\"json\"}");
        String stored = jdbc.queryForObject(
            "SELECT recipe->>'output' FROM recipes WHERE name = 'x'", String.class);
        org.assertj.core.api.Assertions.assertThat(stored).isEqualTo("json");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=V7RecipesMigrationTest`
Expected: FAIL — relation `recipes` does not exist.

- [ ] **Step 3: Write the migration**

```sql
-- V7__recipes.sql
CREATE TABLE recipes (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,
  recipe       JSONB NOT NULL,
  is_shared    BOOLEAN NOT NULL DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, name)
);

CREATE INDEX recipes_user_updated
  ON recipes(user_id, updated_at DESC);

-- Touch updated_at on UPDATE.
CREATE OR REPLACE FUNCTION recipes_touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER recipes_touch_updated_at_trg
  BEFORE UPDATE ON recipes
  FOR EACH ROW EXECUTE FUNCTION recipes_touch_updated_at();
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=V7RecipesMigrationTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V7__recipes.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/migration/V7RecipesMigrationTest.java
git commit -m "feat(gateway): add recipes table with per-user name uniqueness and touch trigger"
```

---

## Task 4: Flyway migration V8 — `plugin_registry`

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V8__plugin_registry.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/migration/V8PluginRegistryMigrationTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.migration;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class V8PluginRegistryMigrationTest {

    @Autowired JdbcTemplate jdbc;

    @Test
    void registrySeededWithExpectedPaidPlugins() {
        var paidIds = jdbc.queryForList(
            "SELECT plugin_id FROM plugin_registry WHERE required_tier = 'paid' ORDER BY plugin_id",
            String.class);
        assertThat(paidIds).containsExactlyInAnyOrder(
            "ai-anomaly-detect",
            "ai-auto-summary",
            "ai-chart-suggest",
            "ai-nl-to-filter",
            "format-request-submit",
            "job-batch-filter",
            "recipe-crud"
        );
    }

    @Test
    void registryContainsFreePlugins() {
        var freeCount = jdbc.queryForObject(
            "SELECT count(*) FROM plugin_registry WHERE required_tier = 'free'", Integer.class);
        assertThat(freeCount).isGreaterThanOrEqualTo(1);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=V8PluginRegistryMigrationTest`
Expected: FAIL.

- [ ] **Step 3: Write the migration**

```sql
-- V8__plugin_registry.sql
--
-- Spec reading (per Plan F preamble):
--   Spec §1 says "advanced-feature gating (charts, SQL-mode filtering, schema
--   inference, batch processing, API access — all paid-only)".
--   User-message override (authoritative for this plan):
--     - analysis-chart-suggest      = free
--     - analysis-schema-infer       = free
--     - analysis-group-by           = free
--     - filter-expression           = free
--     - recipe-*                    = paid
--     - job kind batch-filter       = paid
--     - format-request-submit       = paid
--     - all ai/*                    = paid
--
-- 'free' means: any authenticated user may invoke.
-- 'paid' means: only an active subscription with tier='paid' may invoke.

CREATE TABLE plugin_registry (
  plugin_id     TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('format','filter','analysis','ai-provider','feature')),
  version       TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('enabled','disabled','deprecated')),
  required_tier TEXT CHECK (required_tier IN ('free','paid')),
  installed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (plugin_id, version)
);

CREATE INDEX plugin_registry_required_tier
  ON plugin_registry(required_tier) WHERE status = 'enabled';

-- Seed: free format plugins
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('format-csv',   'format', '1.0.0', 'enabled', 'free'),
  ('format-tsv',   'format', '1.0.0', 'enabled', 'free'),
  ('format-json',  'format', '1.0.0', 'enabled', 'free'),
  ('format-jsonl', 'format', '1.0.0', 'enabled', 'free'),
  ('format-xml',   'format', '1.0.0', 'enabled', 'free'),
  ('format-yaml',  'format', '1.0.0', 'enabled', 'free'),
  ('format-xlsx',  'format', '1.0.0', 'enabled', 'free');

-- Seed: filter plugins (all free per user-message override)
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('filter-column',     'filter', '1.0.0', 'enabled', 'free'),
  ('filter-row',        'filter', '1.0.0', 'enabled', 'free'),
  ('filter-expression', 'filter', '1.0.0', 'enabled', 'free'),
  ('filter-regex',      'filter', '1.0.0', 'enabled', 'free');

-- Seed: analysis plugins (all free per user-message override)
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('analysis-summary-stats',  'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-group-by',       'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-chart-suggest',  'analysis', '1.0.0', 'enabled', 'free'),
  ('analysis-schema-infer',   'analysis', '1.0.0', 'enabled', 'free');

-- Seed: AI provider plugins (paid)
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('ai-nl-to-filter',   'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-auto-summary',   'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-chart-suggest',  'ai-provider', '1.0.0', 'enabled', 'paid'),
  ('ai-anomaly-detect', 'ai-provider', '1.0.0', 'enabled', 'paid');

-- Seed: feature gates (synthetic entries — not real plugins, but the
--       gateway feature-gate filter reads from the same table).
INSERT INTO plugin_registry (plugin_id, kind, version, status, required_tier) VALUES
  ('recipe-crud',           'feature', '1.0.0', 'enabled', 'paid'),
  ('job-batch-filter',      'feature', '1.0.0', 'enabled', 'paid'),
  ('format-request-submit', 'feature', '1.0.0', 'enabled', 'paid');
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=V8PluginRegistryMigrationTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V8__plugin_registry.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/migration/V8PluginRegistryMigrationTest.java
git commit -m "feat(gateway): seed plugin_registry with tier requirements (open-core)"
```

---

## Task 5: Domain types — `Tier`, `Subscription`, `TierConfig`

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/Tier.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/Subscription.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/TierConfig.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/domain/tier/TierConfigTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.domain.tier;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class TierConfigTest {

    @Test
    void freeTierLimitsFromConfig() {
        TierConfig cfg = new TierConfig(5, 100, 50, 0);
        assertThat(cfg.maxUploadMb(Tier.FREE)).isEqualTo(5);
        assertThat(cfg.dailyOps(Tier.FREE)).isEqualTo(100);
    }

    @Test
    void paidTierZeroMeansUnlimited() {
        TierConfig cfg = new TierConfig(5, 100, 50, 0);
        assertThat(cfg.dailyOps(Tier.PAID)).isZero();
        assertThat(cfg.isUnlimitedOps(Tier.PAID)).isTrue();
    }

    @Test
    void tierFromStringIsCaseInsensitive() {
        assertThat(Tier.fromString("FREE")).isEqualTo(Tier.FREE);
        assertThat(Tier.fromString("paid")).isEqualTo(Tier.PAID);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=TierConfigTest`
Expected: FAIL — `Tier` does not exist.

- [ ] **Step 3: Write `Tier.java`**

```java
package io.filternarrange.gateway.domain.tier;

import java.util.Locale;

public enum Tier {
    FREE, PAID;

    public static Tier fromString(String raw) {
        if (raw == null) return FREE;
        return switch (raw.toLowerCase(Locale.ROOT)) {
            case "paid" -> PAID;
            case "free" -> FREE;
            default -> throw new IllegalArgumentException("Unknown tier: " + raw);
        };
    }

    public String wireValue() {
        return name().toLowerCase(Locale.ROOT);
    }
}
```

- [ ] **Step 4: Write `Subscription.java`**

```java
package io.filternarrange.gateway.domain.tier;

import java.time.Instant;
import java.util.UUID;

public record Subscription(
        UUID id,
        UUID userId,
        Tier tier,
        Status status,
        Instant startedAt,
        Instant expiresAt,
        String externalRef
) {
    public enum Status { ACTIVE, CANCELLED, EXPIRED }

    public boolean isActiveNow() {
        return status == Status.ACTIVE && (expiresAt == null || expiresAt.isAfter(Instant.now()));
    }
}
```

- [ ] **Step 5: Write `TierConfig.java`**

```java
package io.filternarrange.gateway.domain.tier;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "filternarrange.tier")
public record TierConfig(
        int freeTierMaxUploadMb,
        int freeTierDailyOps,
        int paidTierMaxUploadMb,
        int paidTierDailyOps
) {
    public int maxUploadMb(Tier t) {
        return t == Tier.PAID ? paidTierMaxUploadMb : freeTierMaxUploadMb;
    }

    public int dailyOps(Tier t) {
        return t == Tier.PAID ? paidTierDailyOps : freeTierDailyOps;
    }

    public boolean isUnlimitedOps(Tier t) {
        return dailyOps(t) == 0;
    }

    public boolean isUnlimitedUpload(Tier t) {
        return maxUploadMb(t) == 0;
    }
}
```

- [ ] **Step 6: Wire into `application.yaml`**

```yaml
filternarrange:
  tier:
    free-tier-max-upload-mb: ${FREE_TIER_MAX_UPLOAD_MB:5}
    free-tier-daily-ops:     ${FREE_TIER_DAILY_OPS:100}
    paid-tier-max-upload-mb: ${PAID_TIER_MAX_UPLOAD_MB:500}
    paid-tier-daily-ops:     ${PAID_TIER_DAILY_OPS:0}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=TierConfigTest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier \
        apps/gateway/src/test/java/io/filternarrange/gateway/domain/tier/TierConfigTest.java \
        apps/gateway/src/main/resources/application.yaml
git commit -m "feat(gateway): introduce Tier enum, Subscription record, and TierConfig binding"
```

---

## Task 6: `SubscriptionRepository` + JDBC adapter

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/SubscriptionRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcSubscriptionRepository.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcSubscriptionRepositoryTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class JdbcSubscriptionRepositoryTest {

    @Autowired SubscriptionRepository repo;
    @Autowired JdbcTemplate jdbc;

    @Test
    void findActiveByUserReturnsLatestActive() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "sub@test");
        UUID subId = UUID.randomUUID();
        jdbc.update("INSERT INTO subscriptions(id, user_id, tier, status, started_at) " +
                    "VALUES (?, ?, 'paid', 'active', now())", subId, userId);

        Optional<Subscription> found = repo.findActiveByUserId(userId);
        assertThat(found).isPresent();
        assertThat(found.get().tier()).isEqualTo(Tier.PAID);
        assertThat(found.get().userId()).isEqualTo(userId);
    }

    @Test
    void findActiveByUserReturnsEmptyWhenNone() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "noemu@test");
        // V5 backfill triggered only at migration time; an inserted-after user has none.
        assertThat(repo.findActiveByUserId(userId)).isEmpty();
    }

    @Test
    void saveAndLookupCancelledIsExcluded() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "x@test");
        Subscription s = new Subscription(
            UUID.randomUUID(), userId, Tier.PAID,
            Subscription.Status.CANCELLED, Instant.now(), null, null);
        repo.save(s);
        assertThat(repo.findActiveByUserId(userId)).isEmpty();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcSubscriptionRepositoryTest`
Expected: FAIL — `SubscriptionRepository` does not exist.

- [ ] **Step 3: Write the port interface**

```java
package io.filternarrange.gateway.domain.tier;

import java.util.Optional;
import java.util.UUID;

public interface SubscriptionRepository {
    Optional<Subscription> findActiveByUserId(UUID userId);
    Subscription save(Subscription sub);
}
```

- [ ] **Step 4: Write the JDBC adapter**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcSubscriptionRepository implements SubscriptionRepository {

    private final JdbcTemplate jdbc;

    public JdbcSubscriptionRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static final RowMapper<Subscription> MAPPER = (rs, i) -> new Subscription(
        UUID.fromString(rs.getString("id")),
        UUID.fromString(rs.getString("user_id")),
        Tier.fromString(rs.getString("tier")),
        Subscription.Status.valueOf(rs.getString("status").toUpperCase()),
        rs.getTimestamp("started_at").toInstant(),
        rs.getTimestamp("expires_at") == null ? null : rs.getTimestamp("expires_at").toInstant(),
        rs.getString("external_ref")
    );

    @Override
    public Optional<Subscription> findActiveByUserId(UUID userId) {
        List<Subscription> rows = jdbc.query(
            "SELECT id, user_id, tier, status, started_at, expires_at, external_ref " +
            "FROM subscriptions WHERE user_id = ? AND status = 'active' " +
            "ORDER BY started_at DESC LIMIT 1",
            MAPPER, userId);
        return rows.stream().findFirst();
    }

    @Override
    public Subscription save(Subscription s) {
        jdbc.update(
            "INSERT INTO subscriptions(id, user_id, tier, status, started_at, expires_at, external_ref) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            s.id(), s.userId(), s.tier().wireValue(),
            s.status().name().toLowerCase(),
            Timestamp.from(s.startedAt()),
            s.expiresAt() == null ? null : Timestamp.from(s.expiresAt()),
            s.externalRef());
        return s;
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcSubscriptionRepositoryTest`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/domain/tier/SubscriptionRepository.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcSubscriptionRepository.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcSubscriptionRepositoryTest.java
git commit -m "feat(gateway): JDBC SubscriptionRepository with active-row lookup"
```

---

## Task 7: `TierResolver` with Redis caching

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/tier/TierResolver.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/application/tier/TierResolverTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.application.tier;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class TierResolverTest {

    @Test
    void cacheHitSkipsDb() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get("gw:tier:" + userId)).thenReturn("paid");
        SubscriptionRepository repo = mock(SubscriptionRepository.class);

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.PAID);
        verifyNoInteractions(repo);
    }

    @Test
    void cacheMissReadsDbAndPopulates() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get("gw:tier:" + userId)).thenReturn(null);
        SubscriptionRepository repo = mock(SubscriptionRepository.class);
        when(repo.findActiveByUserId(userId)).thenReturn(Optional.of(
            new Subscription(UUID.randomUUID(), userId, Tier.PAID,
                Subscription.Status.ACTIVE, Instant.now(), null, null)));

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.PAID);
        verify(ops).set(eq("gw:tier:" + userId), eq("paid"), any(Duration.class));
    }

    @Test
    void noSubscriptionDefaultsToFree() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        UUID userId = UUID.randomUUID();
        when(ops.get(anyString())).thenReturn(null);
        SubscriptionRepository repo = mock(SubscriptionRepository.class);
        when(repo.findActiveByUserId(userId)).thenReturn(Optional.empty());

        TierResolver r = new TierResolver(redis, repo);
        assertThat(r.resolve(userId)).isEqualTo(Tier.FREE);
    }

    @Test
    void invalidateClearsCacheEntry() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        UUID userId = UUID.randomUUID();
        TierResolver r = new TierResolver(redis, mock(SubscriptionRepository.class));
        r.invalidate(userId);
        verify(redis).delete("gw:tier:" + userId);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=TierResolverTest`
Expected: FAIL — class missing.

- [ ] **Step 3: Write the resolver**

```java
package io.filternarrange.gateway.application.tier;

import io.filternarrange.gateway.domain.tier.Subscription;
import io.filternarrange.gateway.domain.tier.SubscriptionRepository;
import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.UUID;

/**
 * Resolves the current effective tier for a user.
 * Cache: Redis `gw:tier:{user_id}` 60s TTL. Default Tier.FREE if no active sub.
 */
@Service
public class TierResolver {
    private static final Duration CACHE_TTL = Duration.ofSeconds(60);
    private static final String KEY_PREFIX = "gw:tier:";

    private final StringRedisTemplate redis;
    private final SubscriptionRepository subs;

    public TierResolver(StringRedisTemplate redis, SubscriptionRepository subs) {
        this.redis = redis;
        this.subs = subs;
    }

    public Tier resolve(UUID userId) {
        String key = KEY_PREFIX + userId;
        String cached = redis.opsForValue().get(key);
        if (cached != null) {
            return Tier.fromString(cached);
        }
        Tier tier = subs.findActiveByUserId(userId)
            .filter(Subscription::isActiveNow)
            .map(Subscription::tier)
            .orElse(Tier.FREE);
        redis.opsForValue().set(key, tier.wireValue(), CACHE_TTL);
        return tier;
    }

    public void invalidate(UUID userId) {
        redis.delete(KEY_PREFIX + userId);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=TierResolverTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/tier/TierResolver.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/application/tier/TierResolverTest.java
git commit -m "feat(gateway): TierResolver with Redis-cached active-subscription lookup"
```

---

## Task 8: `QuotaFilter` — daily op counter + 429

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/QuotaFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/QuotaFilterTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.platform.web;

import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

class QuotaFilterTest {

    @Test
    void underQuotaPassesThrough() throws Exception {
        UUID userId = UUID.randomUUID();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(5L);
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        QuotaFilter f = new QuotaFilter(redis, tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);

        verify(chain).doFilter(req, res);
        assertThat(res.getStatus()).isEqualTo(200);
    }

    @Test
    void overQuotaReturns429WithRetryAfter() throws Exception {
        UUID userId = UUID.randomUUID();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(101L);
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        QuotaFilter f = new QuotaFilter(redis, tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);

        verifyNoInteractions(chain);
        assertThat(res.getStatus()).isEqualTo(429);
        assertThat(res.getHeader("Retry-After")).isNotNull();
        assertThat(res.getContentAsString()).contains("TIER_QUOTA_EXCEEDED");
    }

    @Test
    void paidUnlimitedNeverBlocked() throws Exception {
        UUID userId = UUID.randomUUID();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(999_999L);
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.PAID);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        QuotaFilter f = new QuotaFilter(redis, tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }

    @Test
    void counterKeyIsTodaysDateInUtc() throws Exception {
        UUID userId = UUID.randomUUID();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(1L);
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        QuotaFilter f = new QuotaFilter(redis, tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        f.doFilter(req, new MockHttpServletResponse(), mock(FilterChain.class));

        verify(ops).increment(argThat(k ->
            k.startsWith("gw:rate:user:" + userId + ":ops:") && k.length() >= "gw:rate:user::ops:2026-06-07".length()));
        verify(redis).expire(anyString(), any(Duration.class));
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=QuotaFilterTest`
Expected: FAIL.

- [ ] **Step 3: Write the filter**

```java
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Per-user daily op counter enforced before any business endpoint.
 * Excludes /api/v1/auth/**, /api/v1/billing/me, /actuator/** (handled elsewhere).
 */
@Component
public class QuotaFilter extends OncePerRequestFilter {

    private static final Set<String> EXEMPT_PREFIXES = Set.of(
        "/api/v1/auth/",
        "/api/v1/billing/me",
        "/actuator/",
        "/api/v1/admin/"
    );

    private static final ObjectMapper JSON = new ObjectMapper();
    private final StringRedisTemplate redis;
    private final TierResolver tierResolver;
    private final TierConfig cfg;

    public QuotaFilter(StringRedisTemplate redis, TierResolver tierResolver, TierConfig cfg) {
        this.redis = redis;
        this.tierResolver = tierResolver;
        this.cfg = cfg;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String path = req.getRequestURI();
        if (EXEMPT_PREFIXES.stream().anyMatch(path::startsWith)) {
            chain.doFilter(req, res);
            return;
        }
        AuthenticatedUser user = (AuthenticatedUser) req.getAttribute("auth.user");
        if (user == null) {
            chain.doFilter(req, res); // auth filter will reject earlier
            return;
        }
        Tier tier = tierResolver.resolve(user.id());
        if (cfg.isUnlimitedOps(tier)) {
            chain.doFilter(req, res);
            return;
        }
        String today = LocalDate.now(ZoneOffset.UTC).toString();
        String key = "gw:rate:user:" + user.id() + ":ops:" + today;
        Long count = redis.opsForValue().increment(key);
        redis.expire(key, secondsUntilEndOfDayUtc());
        if (count != null && count > cfg.dailyOps(tier)) {
            writeQuotaExceeded(res, tier);
            return;
        }
        chain.doFilter(req, res);
    }

    private Duration secondsUntilEndOfDayUtc() {
        LocalDateTime now = LocalDateTime.now(ZoneOffset.UTC);
        LocalDateTime midnight = now.toLocalDate().plusDays(1).atStartOfDay();
        return Duration.between(now, midnight);
    }

    private void writeQuotaExceeded(HttpServletResponse res, Tier tier) throws IOException {
        res.setStatus(429);
        res.setHeader("Retry-After", String.valueOf(secondsUntilEndOfDayUtc().toSeconds()));
        res.setContentType("application/json");
        JSON.writeValue(res.getWriter(), Map.of(
            "code", "TIER_QUOTA_EXCEEDED",
            "message", "Daily operation quota exceeded for tier '" + tier.wireValue() + "'.",
            "tier", tier.wireValue(),
            "upgrade_hint", tier == Tier.FREE ? "/account/billing" : null
        ));
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=QuotaFilterTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/QuotaFilter.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/QuotaFilterTest.java
git commit -m "feat(gateway): QuotaFilter with Redis daily counter and 429 + Retry-After"
```

---

## Task 9: `SizeLimitFilter` — 413 on oversize multipart

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/SizeLimitFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/SizeLimitFilterTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.platform.web;

import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class SizeLimitFilterTest {

    @Test
    void underLimitPassesThrough() throws Exception {
        UUID userId = UUID.randomUUID();
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        SizeLimitFilter f = new SizeLimitFilter(tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/uploads");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        req.setContent(new byte[4 * 1024 * 1024]); // 4 MB
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }

    @Test
    void overLimitReturns413WithUpgradeHint() throws Exception {
        UUID userId = UUID.randomUUID();
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        SizeLimitFilter f = new SizeLimitFilter(tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/uploads");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        req.setContent(new byte[6 * 1024 * 1024]); // 6 MB > 5 MB free
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verifyNoInteractions(chain);
        assertThat(res.getStatus()).isEqualTo(413);
        assertThat(res.getContentAsString()).contains("PAYLOAD_TOO_LARGE");
        assertThat(res.getContentAsString()).contains("upgrade_hint");
    }

    @Test
    void paidUnlimitedZeroPassesAnySize() throws Exception {
        UUID userId = UUID.randomUUID();
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.PAID);
        TierConfig cfg = new TierConfig(5, 100, 0, 0); // paid unlimited

        SizeLimitFilter f = new SizeLimitFilter(tr, cfg);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/uploads");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        req.setContent(new byte[600 * 1024 * 1024]);
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);
        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=SizeLimitFilterTest`
Expected: FAIL.

- [ ] **Step 3: Write the filter**

```java
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.Set;

/**
 * Enforces tier-specific max-upload-MB on multipart and POST bodies for endpoints
 * that ingest user content. Pure body-size check; does not consume the body stream.
 */
@Component
public class SizeLimitFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> GUARDED_PATHS = Set.of(
        "/api/v1/uploads",
        "/api/v1/detect",
        "/api/v1/paste",
        "/api/v1/jobs"
    );

    private final TierResolver tierResolver;
    private final TierConfig cfg;

    public SizeLimitFilter(TierResolver tierResolver, TierConfig cfg) {
        this.tierResolver = tierResolver;
        this.cfg = cfg;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String path = req.getRequestURI();
        if (GUARDED_PATHS.stream().noneMatch(path::startsWith)) {
            chain.doFilter(req, res);
            return;
        }
        AuthenticatedUser user = (AuthenticatedUser) req.getAttribute("auth.user");
        if (user == null) {
            chain.doFilter(req, res);
            return;
        }
        Tier tier = tierResolver.resolve(user.id());
        if (cfg.isUnlimitedUpload(tier)) {
            chain.doFilter(req, res);
            return;
        }
        long maxBytes = cfg.maxUploadMb(tier) * 1024L * 1024L;
        long len = req.getContentLengthLong();
        if (len > maxBytes) {
            res.setStatus(413);
            res.setContentType("application/json");
            JSON.writeValue(res.getWriter(), Map.of(
                "code", "PAYLOAD_TOO_LARGE",
                "message", "File exceeds tier limit of " + cfg.maxUploadMb(tier) + " MB.",
                "tier", tier.wireValue(),
                "max_upload_mb", cfg.maxUploadMb(tier),
                "upgrade_hint", tier == Tier.FREE ? "/account/billing" : null
            ));
            return;
        }
        chain.doFilter(req, res);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=SizeLimitFilterTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/SizeLimitFilter.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/SizeLimitFilterTest.java
git commit -m "feat(gateway): SizeLimitFilter enforcing tier upload caps with 413"
```

---

## Task 10: `IpRateLimitFilter` for unauthenticated endpoints

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/IpRateLimitFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/IpRateLimitFilterTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.platform.web;

import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

class IpRateLimitFilterTest {

    @Test
    void underLimitPassesThrough() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(10L);

        IpRateLimitFilter f = new IpRateLimitFilter(redis, 60);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/auth/signup");
        req.setRemoteAddr("1.2.3.4");
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }

    @Test
    void overLimitReturns429() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(61L);

        IpRateLimitFilter f = new IpRateLimitFilter(redis, 60);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/auth/signup");
        req.setRemoteAddr("1.2.3.4");
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verifyNoInteractions(chain);
        assertThat(res.getStatus()).isEqualTo(429);
        assertThat(res.getContentAsString()).contains("IP_RATE_LIMITED");
    }

    @Test
    void onlyAppliesToUnauthenticatedPaths() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        IpRateLimitFilter f = new IpRateLimitFilter(redis, 60);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setRemoteAddr("1.2.3.4");
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
        verifyNoInteractions(redis);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=IpRateLimitFilterTest`
Expected: FAIL.

- [ ] **Step 3: Write the filter**

```java
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Set;

/** Rate-limits unauthenticated endpoints (signup, login) by client IP. */
@Component
public class IpRateLimitFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> UNAUTH_PATHS = Set.of(
        "/api/v1/auth/signup",
        "/api/v1/auth/login"
    );

    private final StringRedisTemplate redis;
    private final int perMinuteLimit;

    public IpRateLimitFilter(StringRedisTemplate redis,
                             @Value("${filternarrange.ip-rate-limit-per-minute:60}") int limit) {
        this.redis = redis;
        this.perMinuteLimit = limit;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        if (!UNAUTH_PATHS.contains(req.getRequestURI())) {
            chain.doFilter(req, res);
            return;
        }
        String ip = clientIp(req);
        long windowSeconds = 60;
        long windowStart = Instant.now().getEpochSecond() / windowSeconds;
        String key = "gw:rate:ip:" + ip + ":" + windowStart;
        Long count = redis.opsForValue().increment(key);
        redis.expire(key, Duration.ofSeconds(windowSeconds));
        if (count != null && count > perMinuteLimit) {
            res.setStatus(429);
            res.setHeader("Retry-After", String.valueOf(windowSeconds));
            res.setContentType("application/json");
            JSON.writeValue(res.getWriter(), Map.of(
                "code", "IP_RATE_LIMITED",
                "message", "Too many requests from " + ip + "."));
            return;
        }
        chain.doFilter(req, res);
    }

    private String clientIp(HttpServletRequest req) {
        String fwd = req.getHeader("X-Forwarded-For");
        return fwd != null && !fwd.isBlank() ? fwd.split(",")[0].trim() : req.getRemoteAddr();
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=IpRateLimitFilterTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/IpRateLimitFilter.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/IpRateLimitFilterTest.java
git commit -m "feat(gateway): IpRateLimitFilter for signup/login endpoints"
```

---

## Task 11: `PluginRegistryService` — tier lookup with Redis cache

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/plugin/PluginRegistryService.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/application/plugin/PluginRegistryServiceTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.application.plugin;

import io.filternarrange.gateway.domain.tier.Tier;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class PluginRegistryServiceTest {

    @Autowired PluginRegistryService svc;

    @Test
    void aiNlToFilterRequiresPaid() {
        assertThat(svc.requiredTier("ai-nl-to-filter")).contains(Tier.PAID);
    }

    @Test
    void filterRegexRequiresFree() {
        assertThat(svc.requiredTier("filter-regex")).contains(Tier.FREE);
    }

    @Test
    void unknownPluginReturnsEmpty() {
        assertThat(svc.requiredTier("nope")).isEqualTo(Optional.empty());
    }

    @Test
    void recipeCrudFeatureIsPaid() {
        assertThat(svc.requiredTier("recipe-crud")).contains(Tier.PAID);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=PluginRegistryServiceTest`
Expected: FAIL.

- [ ] **Step 3: Write the service**

```java
package io.filternarrange.gateway.application.plugin;

import io.filternarrange.gateway.domain.tier.Tier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;

@Service
public class PluginRegistryService {

    private static final Duration CACHE_TTL = Duration.ofMinutes(5);
    private final JdbcTemplate jdbc;
    private final StringRedisTemplate redis;

    public PluginRegistryService(JdbcTemplate jdbc, StringRedisTemplate redis) {
        this.jdbc = jdbc;
        this.redis = redis;
    }

    public Optional<Tier> requiredTier(String pluginId) {
        String key = "gw:plugin-tier:" + pluginId;
        String cached = redis.opsForValue().get(key);
        if ("__none__".equals(cached)) {
            return Optional.empty();
        }
        if (cached != null) {
            return Optional.of(Tier.fromString(cached));
        }
        Optional<String> dbVal = jdbc.query(
            "SELECT required_tier FROM plugin_registry " +
            "WHERE plugin_id = ? AND status = 'enabled' " +
            "ORDER BY version DESC LIMIT 1",
            rs -> rs.next() ? Optional.ofNullable(rs.getString(1)) : Optional.<String>empty(),
            pluginId);
        if (dbVal == null || dbVal.isEmpty()) {
            redis.opsForValue().set(key, "__none__", CACHE_TTL);
            return Optional.empty();
        }
        Tier t = Tier.fromString(dbVal.get());
        redis.opsForValue().set(key, t.wireValue(), CACHE_TTL);
        return Optional.of(t);
    }

    public void invalidateAll() {
        redis.keys("gw:plugin-tier:*").forEach(redis::delete);
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=PluginRegistryServiceTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/plugin/PluginRegistryService.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/application/plugin/PluginRegistryServiceTest.java
git commit -m "feat(gateway): PluginRegistryService with cached required-tier lookup"
```

---

## Task 12: `FeatureGateFilter` — 403 FEATURE_REQUIRES_PAID_TIER

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/FeatureGateFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/FeatureGateFilterTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.platform.web;

import io.filternarrange.gateway.application.plugin.PluginRegistryService;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class FeatureGateFilterTest {

    @Test
    void freeUserCannotCallPaidAiEndpoint() throws Exception {
        UUID userId = UUID.randomUUID();
        PluginRegistryService prs = mock(PluginRegistryService.class);
        when(prs.requiredTier("ai-nl-to-filter")).thenReturn(Optional.of(Tier.PAID));
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);

        FeatureGateFilter f = new FeatureGateFilter(prs, tr);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/ai/nl-to-filter");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verifyNoInteractions(chain);
        assertThat(res.getStatus()).isEqualTo(403);
        assertThat(res.getContentAsString()).contains("FEATURE_REQUIRES_PAID_TIER");
    }

    @Test
    void paidUserCanCallPaidEndpoint() throws Exception {
        UUID userId = UUID.randomUUID();
        PluginRegistryService prs = mock(PluginRegistryService.class);
        when(prs.requiredTier("ai-nl-to-filter")).thenReturn(Optional.of(Tier.PAID));
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.PAID);

        FeatureGateFilter f = new FeatureGateFilter(prs, tr);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/ai/nl-to-filter");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }

    @Test
    void freeUserCanCallFreeEndpoint() throws Exception {
        UUID userId = UUID.randomUUID();
        PluginRegistryService prs = mock(PluginRegistryService.class);
        when(prs.requiredTier("filter-regex")).thenReturn(Optional.of(Tier.FREE));
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);

        FeatureGateFilter f = new FeatureGateFilter(prs, tr);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/filter");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        req.setAttribute("plugin.id", "filter-regex");
        MockHttpServletResponse res = new MockHttpServletResponse();
        FilterChain chain = mock(FilterChain.class);

        f.doFilter(req, res, chain);
        verify(chain).doFilter(req, res);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=FeatureGateFilterTest`
Expected: FAIL.

- [ ] **Step 3: Write the filter**

```java
package io.filternarrange.gateway.platform.web;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.plugin.PluginRegistryService;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.Optional;

/**
 * Maps `/api/v1/...` URLs to plugin_id keys, looks up the required tier, and
 * rejects requests whose user's tier is insufficient.
 */
@Component
public class FeatureGateFilter extends OncePerRequestFilter {

    private static final ObjectMapper JSON = new ObjectMapper();
    private final PluginRegistryService plugins;
    private final TierResolver tierResolver;

    public FeatureGateFilter(PluginRegistryService plugins, TierResolver tierResolver) {
        this.plugins = plugins;
        this.tierResolver = tierResolver;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String pluginId = resolvePluginId(req);
        if (pluginId == null) { chain.doFilter(req, res); return; }
        Optional<Tier> required = plugins.requiredTier(pluginId);
        if (required.isEmpty() || required.get() == Tier.FREE) {
            chain.doFilter(req, res);
            return;
        }
        AuthenticatedUser user = (AuthenticatedUser) req.getAttribute("auth.user");
        if (user == null) { chain.doFilter(req, res); return; }
        Tier actual = tierResolver.resolve(user.id());
        if (actual == Tier.PAID) { chain.doFilter(req, res); return; }
        res.setStatus(403);
        res.setContentType("application/json");
        JSON.writeValue(res.getWriter(), Map.of(
            "code", "FEATURE_REQUIRES_PAID_TIER",
            "message", "This feature requires a paid subscription.",
            "plugin_id", pluginId,
            "upgrade_hint", "/account/billing"));
    }

    /** Map URL → plugin_id key in the registry. */
    private String resolvePluginId(HttpServletRequest req) {
        String path = req.getRequestURI();
        // Explicit attribute set by controllers that already know their plugin id.
        Object attr = req.getAttribute("plugin.id");
        if (attr instanceof String s) return s;
        if (path.startsWith("/api/v1/ai/nl-to-filter"))   return "ai-nl-to-filter";
        if (path.startsWith("/api/v1/ai/auto-summary"))   return "ai-auto-summary";
        if (path.startsWith("/api/v1/ai/chart-suggest"))  return "ai-chart-suggest";
        if (path.startsWith("/api/v1/ai/anomaly-detect")) return "ai-anomaly-detect";
        if (path.startsWith("/api/v1/recipes"))           return "recipe-crud";
        if (path.equals("/api/v1/format-requests") && "POST".equals(req.getMethod()))
            return "format-request-submit";
        // job-batch-filter handled inside JobController via plugin.id attribute.
        return null;
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=FeatureGateFilterTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/FeatureGateFilter.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/FeatureGateFilterTest.java
git commit -m "feat(gateway): FeatureGateFilter rejecting free users from paid-only endpoints"
```

---

## Task 13: Wire all filters into `SecurityConfig`

**Files:**
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/security/SecurityConfig.java`

- [ ] **Step 1: Update SecurityConfig**

```java
package io.filternarrange.gateway.platform.security;

import io.filternarrange.gateway.platform.web.FeatureGateFilter;
import io.filternarrange.gateway.platform.web.IpRateLimitFilter;
import io.filternarrange.gateway.platform.web.QuotaFilter;
import io.filternarrange.gateway.platform.web.SizeLimitFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.AuthorizationFilter;

@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain filterChain(HttpSecurity http,
                                    IpRateLimitFilter ipRateLimit,
                                    SizeLimitFilter sizeLimit,
                                    QuotaFilter quota,
                                    FeatureGateFilter featureGate) throws Exception {
        return http
            .csrf(c -> c.disable())
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/api/v1/admin/**").hasAuthority("ROLE_ADMIN")
                .anyRequest().authenticated())
            .addFilterBefore(ipRateLimit, AuthorizationFilter.class)
            .addFilterAfter(sizeLimit, AuthorizationFilter.class)
            .addFilterAfter(quota, SizeLimitFilter.class)
            .addFilterAfter(featureGate, QuotaFilter.class)
            .build();
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/security/SecurityConfig.java
git commit -m "feat(gateway): wire tier filter chain (ip-rate → size → quota → feature-gate)"
```

---

## Task 14: Recipe domain + repository

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/recipe/Recipe.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/recipe/RecipeRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcRecipeRepository.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcRecipeRepositoryTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.domain.recipe.RecipeRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class JdbcRecipeRepositoryTest {

    @Autowired RecipeRepository repo;
    @Autowired JdbcTemplate jdbc;

    UUID seedUser() {
        UUID u = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", u, "r-" + u + "@t");
        return u;
    }

    @Test
    void saveAndFindById() {
        UUID userId = seedUser();
        Recipe r = new Recipe(UUID.randomUUID(), userId, "my-r", "{\"k\":\"v\"}",
            false, Instant.now(), Instant.now());
        repo.save(r);
        assertThat(repo.findByIdForUser(r.id(), userId)).isPresent();
    }

    @Test
    void listForUserOrderedByUpdatedDesc() {
        UUID userId = seedUser();
        repo.save(new Recipe(UUID.randomUUID(), userId, "a", "{}", false,
            Instant.now().minusSeconds(60), Instant.now().minusSeconds(60)));
        repo.save(new Recipe(UUID.randomUUID(), userId, "b", "{}", false,
            Instant.now(), Instant.now()));
        List<Recipe> got = repo.listForUser(userId);
        assertThat(got).hasSize(2);
        assertThat(got.get(0).name()).isEqualTo("b");
    }

    @Test
    void deleteRemovesRow() {
        UUID userId = seedUser();
        Recipe r = new Recipe(UUID.randomUUID(), userId, "to-del", "{}", false,
            Instant.now(), Instant.now());
        repo.save(r);
        assertThat(repo.deleteForUser(r.id(), userId)).isTrue();
        assertThat(repo.findByIdForUser(r.id(), userId)).isEmpty();
    }

    @Test
    void updateChangesRecipeBlob() {
        UUID userId = seedUser();
        UUID rid = UUID.randomUUID();
        repo.save(new Recipe(rid, userId, "upd", "{\"v\":1}", false,
            Instant.now(), Instant.now()));
        repo.update(rid, userId, "upd-renamed", "{\"v\":2}");
        Recipe got = repo.findByIdForUser(rid, userId).orElseThrow();
        assertThat(got.name()).isEqualTo("upd-renamed");
        assertThat(got.recipeJson()).contains("\"v\": 2", "\"v\":2");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcRecipeRepositoryTest`
Expected: FAIL.

- [ ] **Step 3: Write the domain types**

```java
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
```

```java
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
```

- [ ] **Step 4: Write the JDBC adapter**

```java
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

    public JdbcRecipeRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

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
            "INSERT INTO recipes(id, user_id, name, recipe, is_shared, created_at, updated_at) " +
            "VALUES (?, ?, ?, ?::jsonb, ?, ?, ?)",
            r.id(), r.userId(), r.name(), r.recipeJson(), r.isShared(),
            Timestamp.from(r.createdAt()), Timestamp.from(r.updatedAt()));
        return r;
    }

    @Override
    public Optional<Recipe> findByIdForUser(UUID id, UUID userId) {
        var rows = jdbc.query(
            "SELECT id, user_id, name, recipe, is_shared, created_at, updated_at " +
            "FROM recipes WHERE id = ? AND user_id = ?",
            MAPPER, id, userId);
        return rows.stream().findFirst();
    }

    @Override
    public List<Recipe> listForUser(UUID userId) {
        return jdbc.query(
            "SELECT id, user_id, name, recipe, is_shared, created_at, updated_at " +
            "FROM recipes WHERE user_id = ? ORDER BY updated_at DESC",
            MAPPER, userId);
    }

    @Override
    public boolean deleteForUser(UUID id, UUID userId) {
        return jdbc.update("DELETE FROM recipes WHERE id = ? AND user_id = ?", id, userId) > 0;
    }

    @Override
    public Optional<Recipe> update(UUID id, UUID userId, String newName, String newJson) {
        int n = jdbc.update(
            "UPDATE recipes SET name = ?, recipe = ?::jsonb WHERE id = ? AND user_id = ?",
            newName, newJson, id, userId);
        return n > 0 ? findByIdForUser(id, userId) : Optional.empty();
    }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcRecipeRepositoryTest`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/domain/recipe \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcRecipeRepository.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcRecipeRepositoryTest.java
git commit -m "feat(gateway): Recipe domain and JDBC repository"
```

---

## Task 15: `RecipeService` with audit emission

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/recipe/RecipeService.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/application/recipe/RecipeServiceTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.application.recipe;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.domain.recipe.RecipeRepository;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class RecipeServiceTest {

    @Test
    void createPersistsAndEmitsAudit() {
        RecipeRepository repo = mock(RecipeRepository.class);
        when(repo.save(any())).thenAnswer(inv -> inv.getArgument(0));
        AuditEmitter audit = mock(AuditEmitter.class);
        RecipeService svc = new RecipeService(repo, audit);

        UUID userId = UUID.randomUUID();
        Recipe out = svc.create(userId, "name", "{\"k\":\"v\"}");

        assertThat(out.name()).isEqualTo("name");
        verify(audit).emit(eq(userId), eq("recipe.create"), eq(out.id().toString()), any());
    }

    @Test
    void deleteEmitsAuditOnSuccess() {
        RecipeRepository repo = mock(RecipeRepository.class);
        AuditEmitter audit = mock(AuditEmitter.class);
        when(repo.deleteForUser(any(), any())).thenReturn(true);

        RecipeService svc = new RecipeService(repo, audit);
        UUID userId = UUID.randomUUID();
        UUID rid = UUID.randomUUID();
        assertThat(svc.delete(userId, rid)).isTrue();
        verify(audit).emit(eq(userId), eq("recipe.delete"), eq(rid.toString()), any());
    }

    @Test
    void deleteDoesNotEmitWhenNoRow() {
        RecipeRepository repo = mock(RecipeRepository.class);
        AuditEmitter audit = mock(AuditEmitter.class);
        when(repo.deleteForUser(any(), any())).thenReturn(false);

        RecipeService svc = new RecipeService(repo, audit);
        assertThat(svc.delete(UUID.randomUUID(), UUID.randomUUID())).isFalse();
        verifyNoInteractions(audit);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=RecipeServiceTest`
Expected: FAIL.

- [ ] **Step 3: Write the service**

```java
package io.filternarrange.gateway.application.recipe;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.domain.recipe.RecipeRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@Service
public class RecipeService {

    private final RecipeRepository repo;
    private final AuditEmitter audit;

    public RecipeService(RecipeRepository repo, AuditEmitter audit) {
        this.repo = repo;
        this.audit = audit;
    }

    public Recipe create(UUID userId, String name, String json) {
        Recipe r = new Recipe(UUID.randomUUID(), userId, name, json, false,
            Instant.now(), Instant.now());
        Recipe saved = repo.save(r);
        audit.emit(userId, "recipe.create", saved.id().toString(),
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
        out.ifPresent(r ->
            audit.emit(userId, "recipe.update", id.toString(), Map.of("name", newName)));
        return out;
    }

    public boolean delete(UUID userId, UUID id) {
        boolean removed = repo.deleteForUser(id, userId);
        if (removed) {
            audit.emit(userId, "recipe.delete", id.toString(), Map.of());
        }
        return removed;
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=RecipeServiceTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/recipe/RecipeService.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/application/recipe/RecipeServiceTest.java
git commit -m "feat(gateway): RecipeService with audit emission on every mutation"
```

---

## Task 16: `RecipeController` (REST API, paid-gated)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/recipe/RecipeController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/recipe/RecipeControllerIT.java`

- [ ] **Step 1: Write the failing integration test**

```java
package io.filternarrange.gateway.api.recipe;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class RecipeControllerIT {

    @Autowired MockMvc mvc;

    @Test
    void freeUser403OnRecipesGet() throws Exception {
        mvc.perform(get("/api/v1/recipes")
                .header("Authorization", "Bearer " + TestTokens.freeUser()))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("FEATURE_REQUIRES_PAID_TIER"));
    }

    @Test
    void paidUserCanCreateGetListUpdateDelete() throws Exception {
        String token = TestTokens.paidUser();
        var create = mvc.perform(post("/api/v1/recipes")
                .header("Authorization", "Bearer " + token)
                .contentType("application/json")
                .content("{\"name\":\"r1\",\"recipe\":{\"out\":\"json\"}}"))
            .andExpect(status().isCreated())
            .andReturn();
        String id = JsonPath.read(create.getResponse().getContentAsString(), "$.id");

        mvc.perform(get("/api/v1/recipes/" + id)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("r1"));

        mvc.perform(get("/api/v1/recipes")
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.length()").value(1));

        mvc.perform(put("/api/v1/recipes/" + id)
                .header("Authorization", "Bearer " + token)
                .contentType("application/json")
                .content("{\"name\":\"r1b\",\"recipe\":{\"out\":\"yaml\"}}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("r1b"));

        mvc.perform(delete("/api/v1/recipes/" + id)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isNoContent());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=RecipeControllerIT`
Expected: FAIL.

- [ ] **Step 3: Write the controller**

```java
package io.filternarrange.gateway.api.recipe;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.recipe.RecipeService;
import io.filternarrange.gateway.domain.recipe.Recipe;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import io.filternarrange.gateway.platform.security.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/recipes")
public class RecipeController {

    private final RecipeService svc;
    private final ObjectMapper json;

    public RecipeController(RecipeService svc, ObjectMapper json) {
        this.svc = svc;
        this.json = json;
    }

    public record RecipeDto(String id, String name, JsonNode recipe,
                            String createdAt, String updatedAt) {
        static RecipeDto of(Recipe r, ObjectMapper m) {
            try {
                return new RecipeDto(r.id().toString(), r.name(),
                    m.readTree(r.recipeJson()),
                    r.createdAt().toString(), r.updatedAt().toString());
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
    }

    public record CreateBody(String name, JsonNode recipe) {}

    @GetMapping
    public Object list(@CurrentUser AuthenticatedUser user) {
        return svc.list(user.id()).stream().map(r -> RecipeDto.of(r, json)).toList();
    }

    @PostMapping
    public ResponseEntity<RecipeDto> create(@CurrentUser AuthenticatedUser user,
                                            @RequestBody CreateBody body) {
        Recipe r = svc.create(user.id(), body.name(), body.recipe().toString());
        return ResponseEntity.status(201).body(RecipeDto.of(r, json));
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@CurrentUser AuthenticatedUser user, @PathVariable UUID id) {
        return svc.get(user.id(), id)
            .<ResponseEntity<?>>map(r -> ResponseEntity.ok(RecipeDto.of(r, json)))
            .orElseGet(() -> ResponseEntity.status(404).body(Map.of(
                "code", "RECIPE_NOT_FOUND",
                "message", "Recipe " + id + " not found.")));
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> update(@CurrentUser AuthenticatedUser user,
                                    @PathVariable UUID id,
                                    @RequestBody CreateBody body) {
        return svc.update(user.id(), id, body.name(), body.recipe().toString())
            .<ResponseEntity<?>>map(r -> ResponseEntity.ok(RecipeDto.of(r, json)))
            .orElseGet(() -> ResponseEntity.status(404).body(Map.of(
                "code", "RECIPE_NOT_FOUND",
                "message", "Recipe " + id + " not found.")));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@CurrentUser AuthenticatedUser user, @PathVariable UUID id) {
        return svc.delete(user.id(), id)
            ? ResponseEntity.noContent().build()
            : ResponseEntity.status(404).body(Map.of(
                "code", "RECIPE_NOT_FOUND",
                "message", "Recipe " + id + " not found."));
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=RecipeControllerIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/recipe \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/recipe/RecipeControllerIT.java
git commit -m "feat(gateway): RecipeController CRUD endpoints (paid-tier gated)"
```

---

## Task 17: Split Kafka jobs topic — `topic.v1.jobs.paid` / `topic.v1.jobs.free`

**Files:**
- Modify: `contracts/kafka/topic.v1.jobs.schema.json`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/api/job/JobController.java`
- Modify: `infra/docker-compose.yml` (worker services + topics)
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/job/JobTopicRoutingTest.java`

- [ ] **Step 1: Write the failing routing test**

```java
package io.filternarrange.gateway.api.job;

import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.kafka.core.KafkaTemplate;

import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class JobTopicRoutingTest {

    @Test
    void paidUserRoutesToPaidTopic() {
        KafkaTemplate<String, String> tmpl = mock(KafkaTemplate.class);
        TierResolver tr = mock(TierResolver.class);
        UUID userId = UUID.randomUUID();
        when(tr.resolve(userId)).thenReturn(Tier.PAID);

        JobController c = new JobController(tmpl, tr, /* jobRepo */ mock(JobRepository.class),
            new com.fasterxml.jackson.databind.ObjectMapper());
        c.submit(new AuthenticatedUser(userId, "u@t", false),
            new JobController.JobSubmissionBody("convert", Map.of()));

        ArgumentCaptor<ProducerRecord<String, String>> cap = ArgumentCaptor.forClass(ProducerRecord.class);
        verify(tmpl).send(cap.capture());
        assertThat(cap.getValue().topic()).isEqualTo("topic.v1.jobs.paid");
        assertThat(cap.getValue().key()).isEqualTo(userId.toString());
    }

    @Test
    void freeUserRoutesToFreeTopic() {
        KafkaTemplate<String, String> tmpl = mock(KafkaTemplate.class);
        TierResolver tr = mock(TierResolver.class);
        UUID userId = UUID.randomUUID();
        when(tr.resolve(userId)).thenReturn(Tier.FREE);

        JobController c = new JobController(tmpl, tr, mock(JobRepository.class),
            new com.fasterxml.jackson.databind.ObjectMapper());
        c.submit(new AuthenticatedUser(userId, "u@t", false),
            new JobController.JobSubmissionBody("convert", Map.of()));

        ArgumentCaptor<ProducerRecord<String, String>> cap = ArgumentCaptor.forClass(ProducerRecord.class);
        verify(tmpl).send(cap.capture());
        assertThat(cap.getValue().topic()).isEqualTo("topic.v1.jobs.free");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=JobTopicRoutingTest`
Expected: FAIL — JobController still produces to one topic.

- [ ] **Step 3: Update `JobController.submit`**

```java
// inside JobController.java
private static final String TOPIC_PAID = "topic.v1.jobs.paid";
private static final String TOPIC_FREE = "topic.v1.jobs.free";

@PostMapping
public ResponseEntity<?> submit(@CurrentUser AuthenticatedUser user,
                                @RequestBody JobSubmissionBody body) {
    UUID jobId = UUID.randomUUID();
    Tier tier = tierResolver.resolve(user.id());
    // batch-filter is paid only; let the feature-gate handle the actual 403,
    // but we set the plugin.id attribute upstream via interceptor.
    String topic = tier == Tier.PAID ? TOPIC_PAID : TOPIC_FREE;

    // Persist queued job
    jobRepo.save(new Job(jobId, user.id(), body.kind(), "queued",
        json.valueToTree(body.params()), null, null, 0, Instant.now(), null, null));

    // Produce — payload schema unchanged; topic differentiates tier.
    String payload = JobPayload.serialize(jobId, user.id(), body.kind(), body.params(), json);
    template.send(new ProducerRecord<>(topic, user.id().toString(), payload));
    return ResponseEntity.accepted().body(Map.of("job_id", jobId.toString(), "status", "queued"));
}
```

- [ ] **Step 4: Update the schema header**

Edit `contracts/kafka/topic.v1.jobs.schema.json`, add at top:

```json
{
  "$id": "topic.v1.jobs",
  "$comment": "This schema is SHARED by topic.v1.jobs.paid and topic.v1.jobs.free. The tier differentiator is the topic name; payload is identical.",
  "type": "object",
  "required": ["job_id", "user_id", "kind", "params"],
  "properties": {
    "job_id":  { "type": "string", "format": "uuid" },
    "user_id": { "type": "string", "format": "uuid" },
    "kind":    { "type": "string" },
    "params":  { "type": "object" }
  }
}
```

- [ ] **Step 5: Update `infra/docker-compose.yml`**

```yaml
  python-worker-paid:
    image: filternarrange/data-engine:latest
    environment:
      MODE: worker
      WORKER_TOPICS: topic.v1.jobs.paid
      KAFKA_GROUP: python-worker-paid
      KAFKA_BROKERS: redpanda:9092
      WORKER_CONCURRENCY: 8
    depends_on: [redpanda, postgres, minio]

  python-worker-free:
    image: filternarrange/data-engine:latest
    environment:
      MODE: worker
      WORKER_TOPICS: topic.v1.jobs.free
      KAFKA_GROUP: python-worker-free
      KAFKA_BROKERS: redpanda:9092
      WORKER_CONCURRENCY: 2
    depends_on: [redpanda, postgres, minio]

  topic-init:
    image: docker.redpanda.com/redpandadata/redpanda:latest
    entrypoint: ["/bin/sh", "-c"]
    command: >
      rpk -X brokers=redpanda:9092 topic create topic.v1.jobs.paid -p 6 -r 1 &&
      rpk -X brokers=redpanda:9092 topic create topic.v1.jobs.free -p 6 -r 1
    depends_on: [redpanda]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=JobTopicRoutingTest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/job/JobController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/job/JobTopicRoutingTest.java \
        contracts/kafka/topic.v1.jobs.schema.json \
        infra/docker-compose.yml
git commit -m "feat: split jobs topic into .paid/.free for true tier prioritization"
```

---

## Task 18: Format-request domain + repository

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/formatrequest/FormatRequest.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/formatrequest/FormatRequestRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcFormatRequestRepository.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcFormatRequestRepositoryTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class JdbcFormatRequestRepositoryTest {

    @Autowired FormatRequestRepository repo;
    @Autowired JdbcTemplate jdbc;

    @Test
    void saveListByStatusUpdateGithubIssue() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "fr@test");
        UUID id = UUID.randomUUID();
        repo.save(new FormatRequest(id, userId, "format-samples/abc", "fixed-width-cobol",
            FormatRequest.Status.OPEN, 0, null, Instant.now(), null));

        var open = repo.listByStatus(FormatRequest.Status.OPEN);
        assertThat(open).anyMatch(fr -> fr.id().equals(id));

        repo.updateGithubIssue(id, 42);
        assertThat(repo.findById(id).orElseThrow().githubIssue()).isEqualTo(42);
    }

    @Test
    void transitionToShipped() {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)", userId, "fr2@test");
        UUID id = UUID.randomUUID();
        repo.save(new FormatRequest(id, userId, "format-samples/xyz", "x",
            FormatRequest.Status.OPEN, 0, null, Instant.now(), null));
        repo.transition(id, FormatRequest.Status.SHIPPED);
        FormatRequest after = repo.findById(id).orElseThrow();
        assertThat(after.status()).isEqualTo(FormatRequest.Status.SHIPPED);
        assertThat(after.resolvedAt()).isNotNull();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcFormatRequestRepositoryTest`
Expected: FAIL.

- [ ] **Step 3: Write domain + repository**

```java
package io.filternarrange.gateway.domain.formatrequest;

import java.time.Instant;
import java.util.UUID;

public record FormatRequest(
        UUID id,
        UUID userId,
        String sampleRef,
        String userLabel,
        Status status,
        int priority,
        Integer githubIssue,
        Instant createdAt,
        Instant resolvedAt
) {
    public enum Status {
        OPEN, TRIAGED, IN_PROGRESS, SHIPPED, REJECTED;
        public String wire() {
            return switch (this) {
                case IN_PROGRESS -> "in-progress";
                default -> name().toLowerCase();
            };
        }
        public static Status fromWire(String s) {
            return switch (s) {
                case "in-progress" -> IN_PROGRESS;
                default -> Status.valueOf(s.toUpperCase());
            };
        }
    }
}
```

```java
package io.filternarrange.gateway.domain.formatrequest;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FormatRequestRepository {
    FormatRequest save(FormatRequest f);
    Optional<FormatRequest> findById(UUID id);
    List<FormatRequest> listByStatus(FormatRequest.Status status);
    List<FormatRequest> listAllRecent(int limit);
    void updateGithubIssue(UUID id, int issueNumber);
    void transition(UUID id, FormatRequest.Status next);
}
```

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JdbcFormatRequestRepository implements FormatRequestRepository {

    private final JdbcTemplate jdbc;

    public JdbcFormatRequestRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    private static final RowMapper<FormatRequest> MAPPER = (rs, i) -> new FormatRequest(
        UUID.fromString(rs.getString("id")),
        UUID.fromString(rs.getString("user_id")),
        rs.getString("sample_ref"),
        rs.getString("user_label"),
        FormatRequest.Status.fromWire(rs.getString("status")),
        rs.getInt("priority"),
        rs.getObject("github_issue") == null ? null : rs.getInt("github_issue"),
        rs.getTimestamp("created_at").toInstant(),
        rs.getTimestamp("resolved_at") == null ? null : rs.getTimestamp("resolved_at").toInstant()
    );

    @Override
    public FormatRequest save(FormatRequest f) {
        jdbc.update(
            "INSERT INTO format_requests(id, user_id, sample_ref, user_label, status, priority) " +
            "VALUES (?, ?, ?, ?, ?, ?)",
            f.id(), f.userId(), f.sampleRef(), f.userLabel(), f.status().wire(), f.priority());
        return f;
    }

    @Override
    public Optional<FormatRequest> findById(UUID id) {
        var rows = jdbc.query(
            "SELECT * FROM format_requests WHERE id = ?", MAPPER, id);
        return rows.stream().findFirst();
    }

    @Override
    public List<FormatRequest> listByStatus(FormatRequest.Status s) {
        return jdbc.query(
            "SELECT * FROM format_requests WHERE status = ? ORDER BY created_at DESC",
            MAPPER, s.wire());
    }

    @Override
    public List<FormatRequest> listAllRecent(int limit) {
        return jdbc.query(
            "SELECT * FROM format_requests ORDER BY created_at DESC LIMIT ?",
            MAPPER, limit);
    }

    @Override
    public void updateGithubIssue(UUID id, int issueNumber) {
        jdbc.update("UPDATE format_requests SET github_issue = ?, status = 'triaged' WHERE id = ?",
            issueNumber, id);
    }

    @Override
    public void transition(UUID id, FormatRequest.Status next) {
        boolean terminal = next == FormatRequest.Status.SHIPPED || next == FormatRequest.Status.REJECTED;
        jdbc.update(
            "UPDATE format_requests SET status = ?, resolved_at = " +
                (terminal ? "?" : "resolved_at") + " WHERE id = ?",
            terminal
                ? new Object[] { next.wire(), Timestamp.from(Instant.now()), id }
                : new Object[] { next.wire(), id });
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=JdbcFormatRequestRepositoryTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/domain/formatrequest \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JdbcFormatRequestRepository.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JdbcFormatRequestRepositoryTest.java
git commit -m "feat(gateway): FormatRequest domain and JDBC repository with status transitions"
```

---

## Task 19: `FormatRequestService` + Kafka producer

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/formatrequest/FormatRequestService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestKafkaProducer.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/application/formatrequest/FormatRequestServiceTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.application.formatrequest;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.messaging.FormatRequestKafkaProducer;
import io.filternarrange.gateway.infrastructure.storage.SampleStore;
import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

class FormatRequestServiceTest {

    @Test
    void submitStoresSampleSavesRowProducesAndAudits() {
        SampleStore store = mock(SampleStore.class);
        when(store.storeFirstNKb(any(), any(), eq(64))).thenReturn("format-samples/abc.bin");
        FormatRequestRepository repo = mock(FormatRequestRepository.class);
        when(repo.save(any())).thenAnswer(i -> i.getArgument(0));
        FormatRequestKafkaProducer producer = mock(FormatRequestKafkaProducer.class);
        AuditEmitter audit = mock(AuditEmitter.class);

        FormatRequestService svc = new FormatRequestService(store, repo, producer, audit, 64);
        UUID userId = UUID.randomUUID();
        FormatRequest out = svc.submit(userId, UUID.randomUUID(), "fixed-width-cobol");

        assertThat(out.status()).isEqualTo(FormatRequest.Status.OPEN);
        verify(producer).publish(out);
        verify(audit).emit(eq(userId), eq("format-request.submit"), eq(out.id().toString()), any());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestServiceTest`
Expected: FAIL.

- [ ] **Step 3: Write the service + producer**

```java
package io.filternarrange.gateway.application.formatrequest;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.messaging.FormatRequestKafkaProducer;
import io.filternarrange.gateway.infrastructure.storage.SampleStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@Service
public class FormatRequestService {

    private final SampleStore store;
    private final FormatRequestRepository repo;
    private final FormatRequestKafkaProducer producer;
    private final AuditEmitter audit;
    private final int sampleKb;

    public FormatRequestService(SampleStore store,
                                FormatRequestRepository repo,
                                FormatRequestKafkaProducer producer,
                                AuditEmitter audit,
                                @Value("${filternarrange.format-request.sample-kb:64}") int sampleKb) {
        this.store = store;
        this.repo = repo;
        this.producer = producer;
        this.audit = audit;
        this.sampleKb = sampleKb;
    }

    public FormatRequest submit(UUID userId, UUID uploadId, String userLabel) {
        String sampleRef = store.storeFirstNKb(userId, uploadId, sampleKb);
        FormatRequest f = new FormatRequest(
            UUID.randomUUID(), userId, sampleRef, userLabel,
            FormatRequest.Status.OPEN, 0, null, Instant.now(), null);
        FormatRequest saved = repo.save(f);
        producer.publish(saved);
        audit.emit(userId, "format-request.submit", saved.id().toString(),
            Map.of("user_label", userLabel == null ? "" : userLabel));
        return saved;
    }
}
```

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

@Component
public class FormatRequestKafkaProducer {
    private static final String TOPIC = "topic.v1.format-requests";

    private final KafkaTemplate<String, String> tmpl;
    private final ObjectMapper json;

    public FormatRequestKafkaProducer(KafkaTemplate<String, String> tmpl, ObjectMapper json) {
        this.tmpl = tmpl;
        this.json = json;
    }

    public void publish(FormatRequest f) {
        try {
            String payload = json.writeValueAsString(Map.of(
                "id", f.id().toString(),
                "user_id", f.userId().toString(),
                "sample_ref", f.sampleRef(),
                "user_label", f.userLabel() == null ? "" : f.userLabel(),
                "status", f.status().wire(),
                "created_at", f.createdAt().toString()
            ));
            tmpl.send(new ProducerRecord<>(TOPIC, f.userId().toString(), payload));
        } catch (Exception e) {
            throw new RuntimeException("Failed to publish format-request", e);
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestServiceTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/formatrequest \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestKafkaProducer.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/application/formatrequest/FormatRequestServiceTest.java
git commit -m "feat(gateway): FormatRequestService stores sample, persists row, and publishes to Kafka"
```

---

## Task 20: `FormatRequestController` (paid-only POST)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/formatrequest/FormatRequestController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/formatrequest/FormatRequestControllerIT.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.api.formatrequest;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class FormatRequestControllerIT {

    @Autowired MockMvc mvc;

    @Test
    void freeUserCannotSubmit() throws Exception {
        mvc.perform(post("/api/v1/format-requests")
                .header("Authorization", "Bearer " + TestTokens.freeUser())
                .contentType("application/json")
                .content("{\"upload_id\":\"00000000-0000-0000-0000-000000000001\"}"))
            .andExpect(status().isForbidden())
            .andExpect(jsonPath("$.code").value("FEATURE_REQUIRES_PAID_TIER"));
    }

    @Test
    void paidUserCanSubmitAndRowIsPersisted() throws Exception {
        MvcResult res = mvc.perform(post("/api/v1/format-requests")
                .header("Authorization", "Bearer " + TestTokens.paidUser())
                .contentType("application/json")
                .content("{\"upload_id\":\"00000000-0000-0000-0000-000000000002\"," +
                         "\"user_label\":\"fixed-width-cobol\"}"))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.status").value("open"))
            .andReturn();
        String id = JsonPath.read(res.getResponse().getContentAsString(), "$.id");
        assert !id.isEmpty();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestControllerIT`
Expected: FAIL.

- [ ] **Step 3: Write the controller**

```java
package io.filternarrange.gateway.api.formatrequest;

import io.filternarrange.gateway.application.formatrequest.FormatRequestService;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import io.filternarrange.gateway.platform.security.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/format-requests")
public class FormatRequestController {

    private final FormatRequestService svc;

    public FormatRequestController(FormatRequestService svc) { this.svc = svc; }

    public record SubmitBody(UUID upload_id, String user_label) {}

    @PostMapping
    public ResponseEntity<Map<String, Object>> submit(@CurrentUser AuthenticatedUser user,
                                                       @RequestBody SubmitBody body) {
        FormatRequest f = svc.submit(user.id(), body.upload_id(), body.user_label());
        return ResponseEntity.status(201).body(Map.of(
            "id", f.id().toString(),
            "status", f.status().wire(),
            "created_at", f.createdAt().toString()
        ));
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestControllerIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/formatrequest/FormatRequestController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/formatrequest/FormatRequestControllerIT.java
git commit -m "feat(gateway): POST /api/v1/format-requests (paid-only, gated by feature-filter)"
```

---

## Task 21: `GithubIssueClient` adapter

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/github/GithubIssueClient.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/github/GithubIssueClientTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.infrastructure.github;

import okhttp3.mockwebserver.MockResponse;
import okhttp3.mockwebserver.MockWebServer;
import okhttp3.mockwebserver.RecordedRequest;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GithubIssueClientTest {

    MockWebServer server;

    @BeforeEach void setUp() throws Exception {
        server = new MockWebServer();
        server.start();
    }
    @AfterEach void tearDown() throws Exception { server.shutdown(); }

    @Test
    void createsIssueAndReturnsNumber() throws Exception {
        server.enqueue(new MockResponse()
            .setResponseCode(201)
            .setBody("{\"number\":1234}")
            .setHeader("Content-Type", "application/json"));

        GithubIssueClient c = new GithubIssueClient(
            "token-xyz",
            "piyush-official/FilterNArrange",
            server.url("/").toString().replaceAll("/$", ""));
        int n = c.createIssue("New format request: fixed-width-cobol",
                              "Anonymized sample stored at format-samples/abc.bin");

        assertThat(n).isEqualTo(1234);
        RecordedRequest sent = server.takeRequest();
        assertThat(sent.getPath()).isEqualTo("/repos/piyush-official/FilterNArrange/issues");
        assertThat(sent.getHeader("Authorization")).isEqualTo("Bearer token-xyz");
        assertThat(sent.getBody().readUtf8()).contains("fixed-width-cobol");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=GithubIssueClientTest`
Expected: FAIL.

- [ ] **Step 3: Write the adapter**

```java
package io.filternarrange.gateway.infrastructure.github;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

@Component
public class GithubIssueClient {
    private static final ObjectMapper JSON = new ObjectMapper();

    private final String token;
    private final String repo;
    private final String apiBase;
    private final HttpClient http = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(5))
        .build();

    public GithubIssueClient(@Value("${filternarrange.github.token:}") String token,
                             @Value("${filternarrange.github.repo:piyush-official/FilterNArrange}") String repo,
                             @Value("${filternarrange.github.api-base:https://api.github.com}") String apiBase) {
        this.token = token;
        this.repo = repo;
        this.apiBase = apiBase;
    }

    /**
     * @return the newly-created issue number
     */
    public int createIssue(String title, String body) {
        try {
            String payload = JSON.writeValueAsString(Map.of(
                "title", title,
                "body", body,
                "labels", java.util.List.of("format-request", "triaged")
            ));
            HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(apiBase + "/repos/" + repo + "/issues"))
                .header("Authorization", "Bearer " + token)
                .header("Accept", "application/vnd.github+json")
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(payload))
                .timeout(Duration.ofSeconds(10))
                .build();
            HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
            if (res.statusCode() / 100 != 2) {
                throw new RuntimeException("GitHub API " + res.statusCode() + ": " + res.body());
            }
            Map<?, ?> parsed = JSON.readValue(res.body(), Map.class);
            return ((Number) parsed.get("number")).intValue();
        } catch (Exception e) {
            throw new RuntimeException("Failed to create GitHub issue", e);
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=GithubIssueClientTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/github/GithubIssueClient.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/github/GithubIssueClientTest.java
git commit -m "feat(gateway): GithubIssueClient using Java 21 HttpClient (no extra dep)"
```

---

## Task 22: `FormatRequestConsumer` — Kafka → GitHub mirror

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestConsumer.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestConsumerTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.github.GithubIssueClient;
import io.filternarrange.gateway.infrastructure.storage.SampleStore;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class FormatRequestConsumerTest {

    @Test
    void onMessageCreatesGithubIssueAndUpdatesRow() throws Exception {
        ObjectMapper json = new ObjectMapper();
        UUID id = UUID.randomUUID();
        UUID userId = UUID.randomUUID();

        FormatRequestRepository repo = mock(FormatRequestRepository.class);
        when(repo.findById(id)).thenReturn(Optional.of(new FormatRequest(
            id, userId, "format-samples/abc.bin", "fixed-width-cobol",
            FormatRequest.Status.OPEN, 0, null, Instant.now(), null)));

        GithubIssueClient gh = mock(GithubIssueClient.class);
        when(gh.createIssue(anyString(), anyString())).thenReturn(7777);
        SampleStore store = mock(SampleStore.class);
        when(store.readFirstKb("format-samples/abc.bin", 1)).thenReturn("col1,col2,col3");
        AuditEmitter audit = mock(AuditEmitter.class);

        FormatRequestConsumer c = new FormatRequestConsumer(repo, gh, store, audit, json);

        String msg = json.writeValueAsString(Map.of(
            "id", id.toString(),
            "user_id", userId.toString(),
            "sample_ref", "format-samples/abc.bin",
            "user_label", "fixed-width-cobol",
            "status", "open",
            "created_at", Instant.now().toString()));
        c.onMessage(msg);

        verify(gh).createIssue(contains("fixed-width-cobol"), contains("format-samples/abc.bin"));
        verify(repo).updateGithubIssue(id, 7777);
        verify(audit).emit(eq(userId), eq("format-request.triaged"), eq(id.toString()), any());
    }

    @Test
    void onMessageSkipsIfRowAlreadyTriaged() throws Exception {
        ObjectMapper json = new ObjectMapper();
        UUID id = UUID.randomUUID();
        FormatRequestRepository repo = mock(FormatRequestRepository.class);
        when(repo.findById(id)).thenReturn(Optional.of(new FormatRequest(
            id, UUID.randomUUID(), "x", "y", FormatRequest.Status.TRIAGED, 0,
            42, Instant.now(), null)));
        GithubIssueClient gh = mock(GithubIssueClient.class);

        FormatRequestConsumer c = new FormatRequestConsumer(
            repo, gh, mock(SampleStore.class), mock(AuditEmitter.class), json);
        c.onMessage(json.writeValueAsString(Map.of(
            "id", id.toString(),
            "user_id", UUID.randomUUID().toString(),
            "sample_ref", "x",
            "user_label", "y",
            "status", "triaged",
            "created_at", Instant.now().toString())));

        verifyNoInteractions(gh);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestConsumerTest`
Expected: FAIL.

- [ ] **Step 3: Write the consumer**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.infrastructure.github.GithubIssueClient;
import io.filternarrange.gateway.infrastructure.storage.SampleStore;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.UUID;

@Component
public class FormatRequestConsumer {

    private final FormatRequestRepository repo;
    private final GithubIssueClient github;
    private final SampleStore store;
    private final AuditEmitter audit;
    private final ObjectMapper json;

    public FormatRequestConsumer(FormatRequestRepository repo,
                                 GithubIssueClient github,
                                 SampleStore store,
                                 AuditEmitter audit,
                                 ObjectMapper json) {
        this.repo = repo;
        this.github = github;
        this.store = store;
        this.audit = audit;
        this.json = json;
    }

    @KafkaListener(topics = "topic.v1.format-requests", groupId = "gateway-format-request-mirror")
    public void onMessage(String payload) {
        try {
            JsonNode n = json.readTree(payload);
            UUID id = UUID.fromString(n.get("id").asText());
            FormatRequest fr = repo.findById(id).orElse(null);
            if (fr == null || fr.githubIssue() != null
                || fr.status() != FormatRequest.Status.OPEN) {
                return;
            }
            String label = n.get("user_label").asText();
            String sampleRef = n.get("sample_ref").asText();
            String snippet = store.readFirstKb(sampleRef, 1);
            String title = "Format request: " + (label.isEmpty() ? "(unlabelled)" : label);
            String body = String.format(
                "## New format request\n\n" +
                "- Ticket: `%s`\n" +
                "- User label: `%s`\n" +
                "- Sample MinIO key: `%s`\n\n" +
                "### Anonymized first-1KB sample\n\n```\n%s\n```\n",
                id, label, sampleRef, snippet);
            int issueNumber = github.createIssue(title, body);
            repo.updateGithubIssue(id, issueNumber);
            UUID userId = UUID.fromString(n.get("user_id").asText());
            audit.emit(userId, "format-request.triaged", id.toString(),
                Map.of("github_issue", issueNumber));
        } catch (Exception e) {
            throw new RuntimeException("Failed to mirror format-request to GitHub", e);
        }
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=FormatRequestConsumerTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestConsumer.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/FormatRequestConsumerTest.java
git commit -m "feat(gateway): consume format-requests topic and mirror to GitHub issue"
```

---

## Task 23: Admin endpoint — list/transition format-requests

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/admin/AdminFormatRequestController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/admin/AdminFormatRequestControllerIT.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.api.admin;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class AdminFormatRequestControllerIT {

    @Autowired MockMvc mvc;

    @Test
    void nonAdmin403() throws Exception {
        mvc.perform(get("/api/v1/admin/format-requests")
                .header("Authorization", "Bearer " + TestTokens.paidUser()))
            .andExpect(status().isForbidden());
    }

    @Test
    void adminListsAndShips() throws Exception {
        String token = TestTokens.adminUser();
        mvc.perform(get("/api/v1/admin/format-requests")
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$").isArray());

        mvc.perform(post("/api/v1/admin/format-requests/seeded-id/ship")
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=AdminFormatRequestControllerIT`
Expected: FAIL.

- [ ] **Step 3: Write the controller**

```java
package io.filternarrange.gateway.api.admin;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.domain.formatrequest.FormatRequest;
import io.filternarrange.gateway.domain.formatrequest.FormatRequestRepository;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import io.filternarrange.gateway.platform.security.CurrentUser;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/admin/format-requests")
@PreAuthorize("hasAuthority('ROLE_ADMIN')")
public class AdminFormatRequestController {

    private final FormatRequestRepository repo;
    private final AuditEmitter audit;

    public AdminFormatRequestController(FormatRequestRepository repo, AuditEmitter audit) {
        this.repo = repo;
        this.audit = audit;
    }

    public record Dto(String id, String userId, String userLabel, String status,
                      Integer githubIssue, String createdAt, String resolvedAt) {
        static Dto of(FormatRequest f) {
            return new Dto(f.id().toString(), f.userId().toString(),
                f.userLabel(), f.status().wire(), f.githubIssue(),
                f.createdAt().toString(),
                f.resolvedAt() == null ? null : f.resolvedAt().toString());
        }
    }

    @GetMapping
    public List<Dto> list(@RequestParam(required = false) String status) {
        List<FormatRequest> rows;
        if (status == null) {
            rows = repo.listAllRecent(200);
        } else {
            rows = repo.listByStatus(FormatRequest.Status.fromWire(status));
        }
        return rows.stream().map(Dto::of).toList();
    }

    @PostMapping("/{id}/ship")
    public ResponseEntity<?> ship(@CurrentUser AuthenticatedUser admin, @PathVariable UUID id) {
        Optional<FormatRequest> existing = repo.findById(id);
        if (existing.isEmpty()) {
            return ResponseEntity.status(404).body(Map.of(
                "code", "FORMAT_REQUEST_NOT_FOUND",
                "message", "Format request " + id + " not found."));
        }
        repo.transition(id, FormatRequest.Status.SHIPPED);
        audit.emit(admin.id(), "format-request.shipped", id.toString(), Map.of());
        return ResponseEntity.ok(Map.of("status", "shipped"));
    }

    @PostMapping("/{id}/reject")
    public ResponseEntity<?> reject(@CurrentUser AuthenticatedUser admin, @PathVariable UUID id) {
        Optional<FormatRequest> existing = repo.findById(id);
        if (existing.isEmpty()) {
            return ResponseEntity.status(404).body(Map.of(
                "code", "FORMAT_REQUEST_NOT_FOUND",
                "message", "Format request " + id + " not found."));
        }
        repo.transition(id, FormatRequest.Status.REJECTED);
        audit.emit(admin.id(), "format-request.rejected", id.toString(), Map.of());
        return ResponseEntity.ok(Map.of("status", "rejected"));
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=AdminFormatRequestControllerIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/admin/AdminFormatRequestController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/admin/AdminFormatRequestControllerIT.java
git commit -m "feat(gateway): admin endpoints to list/ship/reject format-requests"
```

---

## Task 24: `BillingController` — current tier + today's quota usage

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/billing/BillingController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/billing/BillingControllerIT.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.api.billing;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
class BillingControllerIT {

    @Autowired MockMvc mvc;

    @Test
    void freeUserSeesFreeTierAndZeroOps() throws Exception {
        mvc.perform(get("/api/v1/billing/me")
                .header("Authorization", "Bearer " + TestTokens.freeUser()))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.tier").value("free"))
            .andExpect(jsonPath("$.ops_today").value(0))
            .andExpect(jsonPath("$.daily_ops_limit").isNumber())
            .andExpect(jsonPath("$.max_upload_mb").isNumber())
            .andExpect(jsonPath("$.upgrade_url").value("/account/billing"));
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=BillingControllerIT`
Expected: FAIL.

- [ ] **Step 3: Write the controller**

```java
package io.filternarrange.gateway.api.billing;

import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import io.filternarrange.gateway.platform.security.CurrentUser;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/billing")
public class BillingController {

    private final TierResolver tierResolver;
    private final TierConfig cfg;
    private final StringRedisTemplate redis;

    public BillingController(TierResolver tierResolver, TierConfig cfg, StringRedisTemplate redis) {
        this.tierResolver = tierResolver;
        this.cfg = cfg;
        this.redis = redis;
    }

    @GetMapping("/me")
    public Map<String, Object> me(@CurrentUser AuthenticatedUser user) {
        Tier tier = tierResolver.resolve(user.id());
        String key = "gw:rate:user:" + user.id() + ":ops:" + LocalDate.now(ZoneOffset.UTC);
        String raw = redis.opsForValue().get(key);
        int opsToday = raw == null ? 0 : Integer.parseInt(raw);
        return Map.of(
            "tier", tier.wireValue(),
            "ops_today", opsToday,
            "daily_ops_limit", cfg.dailyOps(tier),
            "max_upload_mb", cfg.maxUploadMb(tier),
            "unlimited_ops", cfg.isUnlimitedOps(tier),
            "unlimited_upload", cfg.isUnlimitedUpload(tier),
            "upgrade_url", tier == Tier.FREE ? "/account/billing" : null
        );
    }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=BillingControllerIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/billing/BillingController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/billing/BillingControllerIT.java
git commit -m "feat(gateway): GET /api/v1/billing/me reporting tier + quota usage"
```

---

## Task 25: Audit-on-reject hook

**Files:**
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/QuotaFilter.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/FeatureGateFilter.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/web/SizeLimitFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/AuditOnRejectTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.platform.web;

import io.filternarrange.gateway.application.audit.AuditEmitter;
import io.filternarrange.gateway.application.tier.TierResolver;
import io.filternarrange.gateway.domain.tier.Tier;
import io.filternarrange.gateway.domain.tier.TierConfig;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.UUID;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class AuditOnRejectTest {

    @Test
    void quotaRejectEmitsAuditTierReject() throws Exception {
        UUID userId = UUID.randomUUID();
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        when(redis.opsForValue()).thenReturn(ops);
        when(ops.increment(anyString())).thenReturn(101L);
        TierResolver tr = mock(TierResolver.class);
        when(tr.resolve(userId)).thenReturn(Tier.FREE);
        AuditEmitter audit = mock(AuditEmitter.class);
        TierConfig cfg = new TierConfig(5, 100, 500, 0);

        QuotaFilter f = new QuotaFilter(redis, tr, cfg, audit);
        MockHttpServletRequest req = new MockHttpServletRequest("POST", "/api/v1/detect");
        req.setAttribute("auth.user", new AuthenticatedUser(userId, "u@t", false));
        f.doFilter(req, new MockHttpServletResponse(), mock(FilterChain.class));

        verify(audit).emit(eq(userId), eq("tier-reject"), eq("POST /api/v1/detect"), any());
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=AuditOnRejectTest`
Expected: FAIL.

- [ ] **Step 3: Add AuditEmitter dep + emit on rejection**

In `QuotaFilter.java`, change constructor to accept `AuditEmitter audit` and add to `writeQuotaExceeded`:

```java
private final AuditEmitter audit;
public QuotaFilter(StringRedisTemplate redis, TierResolver tierResolver,
                   TierConfig cfg, AuditEmitter audit) {
    this.redis = redis; this.tierResolver = tierResolver;
    this.cfg = cfg; this.audit = audit;
}

private void writeQuotaExceeded(HttpServletRequest req, HttpServletResponse res, Tier tier,
                                UUID userId) throws IOException {
    res.setStatus(429);
    res.setHeader("Retry-After", String.valueOf(secondsUntilEndOfDayUtc().toSeconds()));
    res.setContentType("application/json");
    JSON.writeValue(res.getWriter(), Map.of(
        "code", "TIER_QUOTA_EXCEEDED",
        "message", "Daily operation quota exceeded for tier '" + tier.wireValue() + "'.",
        "tier", tier.wireValue(),
        "upgrade_hint", tier == Tier.FREE ? "/account/billing" : null
    ));
    audit.emit(userId, "tier-reject",
        req.getMethod() + " " + req.getRequestURI(),
        Map.of("reason", "TIER_QUOTA_EXCEEDED", "tier", tier.wireValue()));
}
```

Apply the same shape — accept and call `audit.emit(...)` on rejection — to `FeatureGateFilter` (`reason: "FEATURE_REQUIRES_PAID_TIER"`) and `SizeLimitFilter` (`reason: "PAYLOAD_TOO_LARGE"`).

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=AuditOnRejectTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/web \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/web/AuditOnRejectTest.java
git commit -m "feat(gateway): emit tier-reject audit event from quota/size/feature filters"
```

---

## Task 26: Retention sweeper config + types (Python)

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/retention/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/retention/config.py`
- Test: `apps/data-engine/tests/retention/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/retention/test_config.py
from filternarrange_engine.retention.config import RetentionConfig
import os, datetime

def test_defaults_match_spec(monkeypatch):
    for k in [
        "UPLOAD_RETENTION_FREE_HOURS",
        "UPLOAD_RETENTION_PAID_DAYS",
        "RESULT_RETENTION_FREE_HOURS",
        "RESULT_RETENTION_PAID_DAYS",
    ]:
        monkeypatch.delenv(k, raising=False)
    cfg = RetentionConfig.from_env()
    assert cfg.upload_free_hours == 24
    assert cfg.upload_paid_days == 30
    assert cfg.result_free_hours == 24
    assert cfg.result_paid_days == 30

def test_thresholds(monkeypatch):
    cfg = RetentionConfig.from_env()
    now = datetime.datetime(2026, 6, 7, 12, 0, tzinfo=datetime.timezone.utc)
    free_cutoff = cfg.upload_cutoff(tier="free", now=now)
    paid_cutoff = cfg.upload_cutoff(tier="paid", now=now)
    assert free_cutoff == now - datetime.timedelta(hours=24)
    assert paid_cutoff == now - datetime.timedelta(days=30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/retention/test_config.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the config**

```python
# src/filternarrange_engine/retention/__init__.py
"""Retention worker — periodically purges aged MinIO blobs per tier rules."""
```

```python
# src/filternarrange_engine/retention/config.py
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class RetentionConfig:
    upload_free_hours: int = 24
    upload_paid_days: int = 30
    result_free_hours: int = 24
    result_paid_days: int = 30
    interval_minutes: int = 60

    @classmethod
    def from_env(cls) -> "RetentionConfig":
        return cls(
            upload_free_hours=int(os.environ.get("UPLOAD_RETENTION_FREE_HOURS", "24")),
            upload_paid_days=int(os.environ.get("UPLOAD_RETENTION_PAID_DAYS", "30")),
            result_free_hours=int(os.environ.get("RESULT_RETENTION_FREE_HOURS", "24")),
            result_paid_days=int(os.environ.get("RESULT_RETENTION_PAID_DAYS", "30")),
            interval_minutes=int(os.environ.get("RETENTION_INTERVAL_MINUTES", "60")),
        )

    def upload_cutoff(self, *, tier: str, now: _dt.datetime) -> _dt.datetime:
        if tier == "paid":
            return now - _dt.timedelta(days=self.upload_paid_days)
        return now - _dt.timedelta(hours=self.upload_free_hours)

    def result_cutoff(self, *, tier: str, now: _dt.datetime) -> _dt.datetime:
        if tier == "paid":
            return now - _dt.timedelta(days=self.result_paid_days)
        return now - _dt.timedelta(hours=self.result_free_hours)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/data-engine/tests/retention/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/retention/__init__.py \
        apps/data-engine/src/filternarrange_engine/retention/config.py \
        apps/data-engine/tests/retention/test_config.py
git commit -m "feat(data-engine): RetentionConfig with per-tier upload/result cutoffs"
```

---

## Task 27: Retention `Sweeper` core logic

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/retention/sweeper.py`
- Test: `apps/data-engine/tests/retention/test_sweeper.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/retention/test_sweeper.py
import datetime as dt
from unittest.mock import AsyncMock, MagicMock, call
import pytest

from filternarrange_engine.retention.config import RetentionConfig
from filternarrange_engine.retention.sweeper import RetentionSweeper, JobRow

UTC = dt.timezone.utc

def _job(job_id, tier, hours_old, bucket="uploads", key=None):
    return JobRow(
        job_id=job_id,
        user_id="u-1",
        tier=tier,
        bucket=bucket,
        object_key=key or f"{bucket}/u-1/{job_id}.bin",
        created_at=dt.datetime.now(UTC) - dt.timedelta(hours=hours_old),
    )

@pytest.mark.asyncio
async def test_purges_25h_old_free_upload():
    db = AsyncMock()
    db.iter_jobs_with_blobs.return_value = _async_iter([
        _job("j1", "free", hours_old=25)
    ])
    minio = MagicMock()
    audit = AsyncMock()
    sweeper = RetentionSweeper(db, minio, audit, RetentionConfig())
    purged = await sweeper.run_once(now=dt.datetime.now(UTC))
    assert purged == 1
    minio.remove_object.assert_called_once_with("uploads", "uploads/u-1/j1.bin")
    audit.emit.assert_awaited_once()

@pytest.mark.asyncio
async def test_retains_5d_old_paid_upload():
    db = AsyncMock()
    db.iter_jobs_with_blobs.return_value = _async_iter([
        _job("j2", "paid", hours_old=120)
    ])
    minio = MagicMock()
    audit = AsyncMock()
    sweeper = RetentionSweeper(db, minio, audit, RetentionConfig())
    purged = await sweeper.run_once(now=dt.datetime.now(UTC))
    assert purged == 0
    minio.remove_object.assert_not_called()
    audit.emit.assert_not_called()

@pytest.mark.asyncio
async def test_recipe_attached_extends_to_90_days():
    db = AsyncMock()
    db.iter_jobs_with_blobs.return_value = _async_iter([
        JobRow(job_id="j3", user_id="u-1", tier="paid",
               bucket="uploads", object_key="uploads/u-1/j3.bin",
               created_at=dt.datetime.now(UTC) - dt.timedelta(days=45),
               recipe_attached=True)
    ])
    minio = MagicMock()
    audit = AsyncMock()
    sweeper = RetentionSweeper(db, minio, audit, RetentionConfig())
    purged = await sweeper.run_once(now=dt.datetime.now(UTC))
    assert purged == 0  # recipe-attached → 90 days; 45d < 90d

@pytest.mark.asyncio
async def test_continues_after_minio_failure():
    db = AsyncMock()
    db.iter_jobs_with_blobs.return_value = _async_iter([
        _job("j4", "free", hours_old=25, key="uploads/u-1/j4.bin"),
        _job("j5", "free", hours_old=25, key="uploads/u-1/j5.bin"),
    ])
    minio = MagicMock()
    minio.remove_object.side_effect = [RuntimeError("boom"), None]
    audit = AsyncMock()
    sweeper = RetentionSweeper(db, minio, audit, RetentionConfig())
    purged = await sweeper.run_once(now=dt.datetime.now(UTC))
    # Second one still purged after first failed.
    assert purged == 1

async def _async_iter(items):
    for x in items:
        yield x
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/retention/test_sweeper.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the sweeper**

```python
# src/filternarrange_engine/retention/sweeper.py
from __future__ import annotations

import dataclasses as _dc
import datetime as _dt
import logging
from typing import AsyncIterator, Protocol

from filternarrange_engine.retention.config import RetentionConfig

log = logging.getLogger(__name__)
UTC = _dt.timezone.utc

@_dc.dataclass(frozen=True)
class JobRow:
    job_id: str
    user_id: str
    tier: str               # 'free' | 'paid'
    bucket: str             # 'uploads' | 'results'
    object_key: str
    created_at: _dt.datetime
    recipe_attached: bool = False

class DbPort(Protocol):
    def iter_jobs_with_blobs(self) -> AsyncIterator[JobRow]: ...
    async def mark_blob_deleted(self, job_id: str, bucket: str) -> None: ...

class MinioPort(Protocol):
    def remove_object(self, bucket: str, key: str) -> None: ...

class AuditPort(Protocol):
    async def emit(self, *, user_id: str, action: str, target: str, metadata: dict) -> None: ...

class RetentionSweeper:
    def __init__(self, db: DbPort, minio: MinioPort, audit: AuditPort, cfg: RetentionConfig):
        self.db = db
        self.minio = minio
        self.audit = audit
        self.cfg = cfg

    async def run_once(self, *, now: _dt.datetime | None = None) -> int:
        now = now or _dt.datetime.now(UTC)
        purged = 0
        async for row in self.db.iter_jobs_with_blobs():
            cutoff = self._cutoff(row, now=now)
            if row.created_at >= cutoff:
                continue
            try:
                self.minio.remove_object(row.bucket, row.object_key)
                await self.db.mark_blob_deleted(row.job_id, row.bucket)
                await self.audit.emit(
                    user_id=row.user_id,
                    action="retention.purge",
                    target=f"{row.bucket}/{row.object_key}",
                    metadata={
                        "job_id": row.job_id,
                        "tier": row.tier,
                        "age_seconds": int((now - row.created_at).total_seconds()),
                    },
                )
                purged += 1
            except Exception as e:
                log.warning("retention: failed to purge %s/%s: %s",
                            row.bucket, row.object_key, e)
        return purged

    def _cutoff(self, row: JobRow, *, now: _dt.datetime) -> _dt.datetime:
        if row.recipe_attached and row.tier == "paid":
            return now - _dt.timedelta(days=90)
        if row.bucket == "uploads":
            return self.cfg.upload_cutoff(tier=row.tier, now=now)
        return self.cfg.result_cutoff(tier=row.tier, now=now)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest apps/data-engine/tests/retention/test_sweeper.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/retention/sweeper.py \
        apps/data-engine/tests/retention/test_sweeper.py
git commit -m "feat(data-engine): RetentionSweeper purges aged blobs per tier with audit"
```

---

## Task 28: Retention CLI + scheduler

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/retention/cli.py`
- Modify: `apps/data-engine/src/filternarrange_engine/__main__.py`
- Modify: `apps/data-engine/pyproject.toml` (add `apscheduler`)
- Test: `apps/data-engine/tests/retention/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/retention/test_cli.py
from unittest.mock import AsyncMock, patch
import pytest

@pytest.mark.asyncio
async def test_run_once_invokes_sweeper(monkeypatch):
    from filternarrange_engine.retention.cli import run_once
    sweeper = AsyncMock()
    sweeper.run_once.return_value = 3
    with patch("filternarrange_engine.retention.cli.build_sweeper",
               return_value=sweeper):
        purged = await run_once()
    assert purged == 3
    sweeper.run_once.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/retention/test_cli.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the CLI**

```python
# src/filternarrange_engine/retention/cli.py
from __future__ import annotations

import argparse
import asyncio
import logging

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from minio import Minio

from filternarrange_engine.adapters.audit_kafka import KafkaAuditEmitter
from filternarrange_engine.platform.config import load_engine_config
from filternarrange_engine.retention.config import RetentionConfig
from filternarrange_engine.retention.sweeper import JobRow, RetentionSweeper

log = logging.getLogger("retention")

class _DbAdapter:
    def __init__(self, pool):
        self.pool = pool

    async def iter_jobs_with_blobs(self):
        async with self.pool.acquire() as conn:
            async for row in conn.cursor(
                """
                SELECT j.id, j.user_id, COALESCE(s.tier, 'free') AS tier,
                       j.created_at,
                       (j.params->'input'->>'ref') AS upload_ref,
                       j.result_ref,
                       EXISTS (
                           SELECT 1 FROM recipes r WHERE r.user_id = j.user_id
                       ) AS recipe_attached
                FROM jobs j
                LEFT JOIN LATERAL (
                    SELECT tier FROM subscriptions
                    WHERE user_id = j.user_id AND status='active' LIMIT 1
                ) s ON true
                WHERE j.created_at < now() - interval '6 hours'
                """
            ):
                # Yield once per blob present (uploads + results).
                if row["upload_ref"]:
                    yield JobRow(
                        job_id=str(row["id"]), user_id=str(row["user_id"]),
                        tier=row["tier"], bucket="uploads",
                        object_key=row["upload_ref"],
                        created_at=row["created_at"],
                        recipe_attached=row["recipe_attached"],
                    )
                if row["result_ref"]:
                    yield JobRow(
                        job_id=str(row["id"]), user_id=str(row["user_id"]),
                        tier=row["tier"], bucket="results",
                        object_key=row["result_ref"],
                        created_at=row["created_at"],
                        recipe_attached=row["recipe_attached"],
                    )

    async def mark_blob_deleted(self, job_id, bucket):
        col = "params" if bucket == "uploads" else "result_ref"
        async with self.pool.acquire() as conn:
            if bucket == "uploads":
                await conn.execute(
                    "UPDATE jobs SET params = params || '{\"input_purged\": true}'::jsonb "
                    "WHERE id = $1",
                    job_id)
            else:
                await conn.execute(
                    "UPDATE jobs SET result_ref = NULL WHERE id = $1", job_id)

async def build_sweeper() -> RetentionSweeper:
    cfg = load_engine_config()
    pool = await asyncpg.create_pool(cfg.postgres_dsn)
    minio = Minio(cfg.minio_endpoint, access_key=cfg.minio_access,
                  secret_key=cfg.minio_secret, secure=False)
    audit = KafkaAuditEmitter(cfg.kafka_brokers)
    await audit.start()
    return RetentionSweeper(_DbAdapter(pool), minio, audit, RetentionConfig.from_env())

async def run_once() -> int:
    sweeper = await build_sweeper()
    return await sweeper.run_once()

async def run_scheduler() -> None:
    sweeper = await build_sweeper()
    sched = AsyncIOScheduler()
    sched.add_job(sweeper.run_once,
                  "interval",
                  minutes=sweeper.cfg.interval_minutes,
                  next_run_time=None)
    sched.start()
    log.info("retention scheduler started; interval=%s min",
             sweeper.cfg.interval_minutes)
    # Initial run, then sleep forever.
    await sweeper.run_once()
    while True:
        await asyncio.sleep(3600)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true",
                   help="Run sweeper once and exit (for tests / cron).")
    args = p.parse_args()
    if args.once:
        asyncio.run(run_once())
    else:
        asyncio.run(run_scheduler())
```

- [ ] **Step 4: Wire `__main__.py`**

```python
# src/filternarrange_engine/__main__.py
import argparse, os, sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retention", action="store_true",
                        help="Run as the retention worker.")
    args, rest = parser.parse_known_args()
    if args.retention:
        from filternarrange_engine.retention.cli import main as retention_main
        retention_main()
        return
    mode = os.environ.get("MODE", "full")
    if mode == "worker":
        from filternarrange_engine.workers.jobs import main as worker_main
        worker_main()
    else:
        from filternarrange_engine.api.app import main as api_main
        api_main()

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Add `apscheduler` to `pyproject.toml` dependencies**

```toml
[project]
# ... existing fields ...
dependencies = [
    # ... existing deps ...
    "apscheduler>=3.10",
    "asyncpg>=0.29",
    "minio>=7.2",
]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest apps/data-engine/tests/retention/test_cli.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/retention/cli.py \
        apps/data-engine/src/filternarrange_engine/__main__.py \
        apps/data-engine/pyproject.toml \
        apps/data-engine/tests/retention/test_cli.py
git commit -m "feat(data-engine): retention CLI with --once and apscheduler loop"
```

---

## Task 29: docker-compose `retention-worker` service

**Files:**
- Modify: `infra/docker-compose.yml`

- [ ] **Step 1: Append retention-worker block**

```yaml
  retention-worker:
    image: filternarrange/data-engine:latest
    command: ["python", "-m", "filternarrange_engine", "--retention"]
    environment:
      POSTGRES_DSN: postgresql://gateway:gateway@postgres:5432/filternarrange
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ROOT_USER}
      MINIO_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
      KAFKA_BROKERS: redpanda:9092
      UPLOAD_RETENTION_FREE_HOURS: ${UPLOAD_RETENTION_FREE_HOURS:-24}
      UPLOAD_RETENTION_PAID_DAYS:  ${UPLOAD_RETENTION_PAID_DAYS:-30}
      RESULT_RETENTION_FREE_HOURS: ${RESULT_RETENTION_FREE_HOURS:-24}
      RESULT_RETENTION_PAID_DAYS:  ${RESULT_RETENTION_PAID_DAYS:-30}
      RETENTION_INTERVAL_MINUTES:  ${RETENTION_INTERVAL_MINUTES:-60}
    depends_on:
      - postgres
      - minio
      - redpanda
    restart: unless-stopped
```

- [ ] **Step 2: Commit**

```bash
git add infra/docker-compose.yml
git commit -m "feat(infra): retention-worker container running --retention loop"
```

---

## Task 30: Frontend — `tier.ts` shared helper

**Files:**
- Create: `apps/frontend/src/shared/lib/tier.ts`
- Test: `apps/frontend/src/shared/lib/tier.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from "vitest";
import { isPaid, percentUsed, formatQuotaMessage } from "./tier";

describe("tier helpers", () => {
  it("isPaid returns true for paid", () => {
    expect(isPaid({ tier: "paid" } as any)).toBe(true);
    expect(isPaid({ tier: "free" } as any)).toBe(false);
  });

  it("percentUsed clamps to 100", () => {
    expect(percentUsed({ ops_today: 150, daily_ops_limit: 100 } as any)).toBe(100);
    expect(percentUsed({ ops_today: 50,  daily_ops_limit: 100 } as any)).toBe(50);
    expect(percentUsed({ ops_today: 0,   daily_ops_limit: 0 }   as any)).toBe(0);
  });

  it("formatQuotaMessage explains free limit", () => {
    expect(formatQuotaMessage({ tier: "free", ops_today: 100, daily_ops_limit: 100 } as any))
      .toMatch(/free tier/i);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run apps/frontend/src/shared/lib/tier.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write the helper**

```ts
// apps/frontend/src/shared/lib/tier.ts
export type Tier = "free" | "paid";

export interface BillingInfo {
  tier: Tier;
  ops_today: number;
  daily_ops_limit: number;
  max_upload_mb: number;
  unlimited_ops: boolean;
  unlimited_upload: boolean;
  upgrade_url: string | null;
}

export const isPaid = (b: Pick<BillingInfo, "tier">) => b.tier === "paid";

export function percentUsed(b: Pick<BillingInfo, "ops_today" | "daily_ops_limit">): number {
  if (!b.daily_ops_limit) return 0;
  return Math.min(100, Math.round((b.ops_today / b.daily_ops_limit) * 100));
}

export function formatQuotaMessage(b: BillingInfo): string {
  if (b.unlimited_ops) return "Unlimited daily operations.";
  return `${b.ops_today} / ${b.daily_ops_limit} operations used today (${b.tier} tier).`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run apps/frontend/src/shared/lib/tier.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/shared/lib/tier.ts apps/frontend/src/shared/lib/tier.test.ts
git commit -m "feat(frontend): shared tier helpers and BillingInfo type"
```

---

## Task 31: Frontend — `PaidGate` component

**Files:**
- Create: `apps/frontend/src/shared/ui/PaidGate.tsx`
- Test: `apps/frontend/src/shared/ui/PaidGate.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PaidGate } from "./PaidGate";

describe("PaidGate", () => {
  it("renders children when user is paid", () => {
    render(
      <PaidGate tier="paid" mode="disabled">
        <button>Pro thing</button>
      </PaidGate>
    );
    expect(screen.getByText("Pro thing")).toBeInTheDocument();
    expect(screen.getByText("Pro thing")).not.toBeDisabled();
  });

  it("disables children when free + mode=disabled", () => {
    render(
      <PaidGate tier="free" mode="disabled">
        <button>Pro thing</button>
      </PaidGate>
    );
    expect(screen.getByText("Pro thing")).toBeDisabled();
    expect(screen.getByRole("tooltip")).toHaveTextContent(/paid feature/i);
  });

  it("hides children when free + mode=hidden", () => {
    render(
      <PaidGate tier="free" mode="hidden">
        <button>Pro thing</button>
      </PaidGate>
    );
    expect(screen.queryByText("Pro thing")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run apps/frontend/src/shared/ui/PaidGate.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Write the component**

```tsx
// apps/frontend/src/shared/ui/PaidGate.tsx
import React from "react";
import type { Tier } from "../lib/tier";

type Mode = "disabled" | "hidden";

interface Props {
  tier: Tier;
  mode?: Mode;
  upgradeHref?: string;
  children: React.ReactElement;
}

export const PaidGate: React.FC<Props> = ({
  tier,
  mode = "disabled",
  upgradeHref = "/account/billing",
  children,
}) => {
  if (tier === "paid") return children;
  if (mode === "hidden") return null;
  return (
    <span style={{ position: "relative" }}>
      {React.cloneElement(children, { disabled: true })}
      <span role="tooltip" style={{ marginLeft: 8, fontSize: 12, color: "#888" }}>
        Paid feature — <a href={upgradeHref}>upgrade</a>
      </span>
    </span>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run apps/frontend/src/shared/ui/PaidGate.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/shared/ui/PaidGate.tsx \
        apps/frontend/src/shared/ui/PaidGate.test.tsx
git commit -m "feat(frontend): PaidGate component with disabled/hidden modes"
```

---

## Task 32: Frontend — billing API + `BillingPanel`

**Files:**
- Create: `apps/frontend/src/features/billing/api/billingApi.ts`
- Create: `apps/frontend/src/features/billing/ui/BillingPanel.tsx`
- Create: `apps/frontend/src/features/billing/ui/TierBadge.tsx`
- Create: `apps/frontend/src/features/billing/ui/QuotaMeter.tsx`
- Test: `apps/frontend/src/features/billing/ui/BillingPanel.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BillingPanel } from "./BillingPanel";
import * as api from "../api/billingApi";

describe("BillingPanel", () => {
  it("renders free tier badge + quota usage + upgrade CTA", async () => {
    vi.spyOn(api, "fetchBilling").mockResolvedValue({
      tier: "free", ops_today: 75, daily_ops_limit: 100,
      max_upload_mb: 5, unlimited_ops: false, unlimited_upload: false,
      upgrade_url: "/account/billing",
    });
    const qc = new QueryClient();
    render(<QueryClientProvider client={qc}><BillingPanel /></QueryClientProvider>);
    await waitFor(() => expect(screen.getByText(/free/i)).toBeInTheDocument());
    expect(screen.getByText(/75/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /upgrade/i })).toBeInTheDocument();
  });

  it("hides upgrade CTA for paid tier", async () => {
    vi.spyOn(api, "fetchBilling").mockResolvedValue({
      tier: "paid", ops_today: 0, daily_ops_limit: 0,
      max_upload_mb: 500, unlimited_ops: true, unlimited_upload: false,
      upgrade_url: null,
    });
    const qc = new QueryClient();
    render(<QueryClientProvider client={qc}><BillingPanel /></QueryClientProvider>);
    await waitFor(() => expect(screen.getByText(/paid/i)).toBeInTheDocument());
    expect(screen.queryByRole("link", { name: /upgrade/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run apps/frontend/src/features/billing/ui/BillingPanel.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Write the API + components**

```ts
// apps/frontend/src/features/billing/api/billingApi.ts
import { httpClient } from "@/shared/api/client";
import type { BillingInfo } from "@/shared/lib/tier";

export const fetchBilling = async (): Promise<BillingInfo> =>
  (await httpClient.get<BillingInfo>("/api/v1/billing/me")).data;
```

```tsx
// apps/frontend/src/features/billing/ui/TierBadge.tsx
import React from "react";
import type { Tier } from "@/shared/lib/tier";

export const TierBadge: React.FC<{ tier: Tier }> = ({ tier }) => (
  <span style={{
    padding: "2px 8px", borderRadius: 4,
    background: tier === "paid" ? "#0a7" : "#888",
    color: "white", fontSize: 12,
  }}>{tier.toUpperCase()}</span>
);
```

```tsx
// apps/frontend/src/features/billing/ui/QuotaMeter.tsx
import React from "react";
import { percentUsed, type BillingInfo } from "@/shared/lib/tier";

export const QuotaMeter: React.FC<{ billing: BillingInfo }> = ({ billing }) => {
  const pct = percentUsed(billing);
  return (
    <div>
      <div style={{ height: 8, background: "#eee", borderRadius: 4 }}>
        <div style={{ height: 8, width: `${pct}%`,
                      background: pct >= 100 ? "#c33" : "#0a7",
                      borderRadius: 4 }} />
      </div>
      <small>
        {billing.unlimited_ops
          ? "Unlimited operations"
          : `${billing.ops_today} / ${billing.daily_ops_limit} ops today`}
      </small>
    </div>
  );
};
```

```tsx
// apps/frontend/src/features/billing/ui/BillingPanel.tsx
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchBilling } from "../api/billingApi";
import { TierBadge } from "./TierBadge";
import { QuotaMeter } from "./QuotaMeter";

export const BillingPanel: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["billing", "me"],
    queryFn: fetchBilling,
    staleTime: 30_000,
  });
  if (isLoading) return <div>Loading…</div>;
  if (error || !data) return <div>Could not load billing info.</div>;

  return (
    <section>
      <h2>Account & billing</h2>
      <p>Current tier: <TierBadge tier={data.tier} /></p>
      <QuotaMeter billing={data} />
      <p>Max upload size: {data.unlimited_upload ? "Unlimited" : `${data.max_upload_mb} MB`}</p>
      {data.upgrade_url && (
        <p><a href={data.upgrade_url}>Upgrade to paid</a></p>
      )}
    </section>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run apps/frontend/src/features/billing/ui/BillingPanel.test.tsx`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/billing
git commit -m "feat(frontend): BillingPanel with TierBadge, QuotaMeter, upgrade CTA"
```

---

## Task 33: Frontend — recipes feature

**Files:**
- Create: `apps/frontend/src/features/recipes/api/recipesApi.ts`
- Create: `apps/frontend/src/features/recipes/state/useRecipes.ts`
- Create: `apps/frontend/src/features/recipes/ui/RecipeList.tsx`
- Create: `apps/frontend/src/features/recipes/ui/SaveRecipeButton.tsx`
- Create: `apps/frontend/src/features/recipes/ui/RunRecipeButton.tsx`
- Test: `apps/frontend/src/features/recipes/ui/RecipeList.test.tsx`
- Test: `apps/frontend/src/features/recipes/ui/SaveRecipeButton.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// RecipeList.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RecipeList } from "./RecipeList";
import * as api from "../api/recipesApi";

describe("RecipeList", () => {
  it("renders recipes for paid users", async () => {
    vi.spyOn(api, "listRecipes").mockResolvedValue([
      { id: "r-1", name: "weekly-csv-to-json", recipe: {},
        createdAt: "2026-06-01", updatedAt: "2026-06-06" },
    ]);
    const qc = new QueryClient();
    render(<QueryClientProvider client={qc}><RecipeList tier="paid" /></QueryClientProvider>);
    await waitFor(() => expect(screen.getByText("weekly-csv-to-json")).toBeInTheDocument());
  });

  it("shows upsell for free users", () => {
    const qc = new QueryClient();
    render(<QueryClientProvider client={qc}><RecipeList tier="free" /></QueryClientProvider>);
    expect(screen.getByText(/paid feature/i)).toBeInTheDocument();
  });
});
```

```tsx
// SaveRecipeButton.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SaveRecipeButton } from "./SaveRecipeButton";
import * as api from "../api/recipesApi";

describe("SaveRecipeButton", () => {
  it("posts create on click for paid user", async () => {
    const spy = vi.spyOn(api, "createRecipe")
      .mockResolvedValue({ id: "r-99", name: "x", recipe: {},
                           createdAt: "n", updatedAt: "n" });
    const qc = new QueryClient();
    render(<QueryClientProvider client={qc}>
      <SaveRecipeButton tier="paid" name="x" body={{ output: "json" }} />
    </QueryClientProvider>);
    fireEvent.click(screen.getByRole("button"));
    expect(spy).toHaveBeenCalledWith("x", { output: "json" });
  });

  it("is disabled for free users", () => {
    render(<QueryClientProvider client={new QueryClient()}>
      <SaveRecipeButton tier="free" name="x" body={{}} />
    </QueryClientProvider>);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run apps/frontend/src/features/recipes`
Expected: FAIL.

- [ ] **Step 3: Write the API**

```ts
// apps/frontend/src/features/recipes/api/recipesApi.ts
import { httpClient } from "@/shared/api/client";

export interface Recipe {
  id: string;
  name: string;
  recipe: any;
  createdAt: string;
  updatedAt: string;
}

export const listRecipes = async (): Promise<Recipe[]> =>
  (await httpClient.get<Recipe[]>("/api/v1/recipes")).data;

export const createRecipe = async (name: string, body: any): Promise<Recipe> =>
  (await httpClient.post<Recipe>("/api/v1/recipes", { name, recipe: body })).data;

export const updateRecipe = async (id: string, name: string, body: any): Promise<Recipe> =>
  (await httpClient.put<Recipe>(`/api/v1/recipes/${id}`, { name, recipe: body })).data;

export const deleteRecipe = async (id: string): Promise<void> => {
  await httpClient.delete(`/api/v1/recipes/${id}`);
};

export const getRecipe = async (id: string): Promise<Recipe> =>
  (await httpClient.get<Recipe>(`/api/v1/recipes/${id}`)).data;
```

- [ ] **Step 4: Write the hook**

```ts
// apps/frontend/src/features/recipes/state/useRecipes.ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as api from "../api/recipesApi";

export const useRecipes = () =>
  useQuery({ queryKey: ["recipes"], queryFn: api.listRecipes, staleTime: 60_000 });

export const useCreateRecipe = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: any }) =>
      api.createRecipe(name, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recipes"] }),
  });
};

export const useDeleteRecipe = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteRecipe(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["recipes"] }),
  });
};
```

- [ ] **Step 5: Write the UI components**

```tsx
// apps/frontend/src/features/recipes/ui/RecipeList.tsx
import React from "react";
import { useRecipes, useDeleteRecipe } from "../state/useRecipes";
import type { Tier } from "@/shared/lib/tier";

export const RecipeList: React.FC<{ tier: Tier }> = ({ tier }) => {
  if (tier !== "paid") {
    return (
      <p>Saved recipes are a paid feature. <a href="/account/billing">Upgrade.</a></p>
    );
  }
  const { data, isLoading } = useRecipes();
  const del = useDeleteRecipe();
  if (isLoading) return <div>Loading…</div>;
  return (
    <ul>
      {(data ?? []).map(r => (
        <li key={r.id}>
          <strong>{r.name}</strong> · updated {r.updatedAt}
          <button onClick={() => del.mutate(r.id)} aria-label={`Delete ${r.name}`}>Delete</button>
        </li>
      ))}
    </ul>
  );
};
```

```tsx
// apps/frontend/src/features/recipes/ui/SaveRecipeButton.tsx
import React from "react";
import { useCreateRecipe } from "../state/useRecipes";
import type { Tier } from "@/shared/lib/tier";

interface Props {
  tier: Tier;
  name: string;
  body: any;
}

export const SaveRecipeButton: React.FC<Props> = ({ tier, name, body }) => {
  const create = useCreateRecipe();
  const disabled = tier !== "paid";
  return (
    <button
      type="button"
      disabled={disabled}
      title={disabled ? "Paid feature — upgrade to save recipes" : undefined}
      onClick={() => create.mutate({ name, body })}>
      Save as recipe
    </button>
  );
};
```

```tsx
// apps/frontend/src/features/recipes/ui/RunRecipeButton.tsx
import React from "react";
import { useNavigate } from "react-router-dom";
import type { Recipe } from "../api/recipesApi";

export const RunRecipeButton: React.FC<{ recipe: Recipe }> = ({ recipe }) => {
  const nav = useNavigate();
  return (
    <button onClick={() => nav(`/?recipe=${recipe.id}`)}>Run on new data</button>
  );
};
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run apps/frontend/src/features/recipes`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/recipes
git commit -m "feat(frontend): recipe CRUD UI with tier-gated controls"
```

---

## Task 34: Frontend — format-request banner + button

**Files:**
- Create: `apps/frontend/src/features/format-request/api/formatRequestApi.ts`
- Create: `apps/frontend/src/features/format-request/ui/FormatRequestBanner.tsx`
- Create: `apps/frontend/src/features/format-request/ui/FormatRequestButton.tsx`
- Test: `apps/frontend/src/features/format-request/ui/FormatRequestBanner.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FormatRequestBanner } from "./FormatRequestBanner";
import * as api from "../api/formatRequestApi";

describe("FormatRequestBanner", () => {
  it("always shows the community PR link", () => {
    render(<QueryClientProvider client={new QueryClient()}>
      <FormatRequestBanner tier="free" uploadId="u-1" />
    </QueryClientProvider>);
    expect(screen.getByRole("link", { name: /contribute a format/i }))
      .toHaveAttribute("href",
        "https://github.com/piyush-official/FilterNArrange/blob/main/CONTRIBUTING.md#contributing-a-format");
  });

  it("does NOT show request button for free users", () => {
    render(<QueryClientProvider client={new QueryClient()}>
      <FormatRequestBanner tier="free" uploadId="u-1" />
    </QueryClientProvider>);
    expect(screen.queryByRole("button", { name: /request format/i })).toBeNull();
  });

  it("shows AND fires submit for paid users", async () => {
    const spy = vi.spyOn(api, "submitFormatRequest")
      .mockResolvedValue({ id: "fr-1", status: "open", created_at: "n" });
    render(<QueryClientProvider client={new QueryClient()}>
      <FormatRequestBanner tier="paid" uploadId="u-1" />
    </QueryClientProvider>);
    const btn = screen.getByRole("button", { name: /request format/i });
    fireEvent.click(btn);
    expect(spy).toHaveBeenCalledWith({ upload_id: "u-1", user_label: undefined });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run apps/frontend/src/features/format-request`
Expected: FAIL.

- [ ] **Step 3: Write the API + UI**

```ts
// apps/frontend/src/features/format-request/api/formatRequestApi.ts
import { httpClient } from "@/shared/api/client";

export interface FormatRequestRow {
  id: string;
  status: string;
  created_at: string;
}

export const submitFormatRequest = async (
  body: { upload_id: string; user_label?: string }
): Promise<FormatRequestRow> =>
  (await httpClient.post<FormatRequestRow>("/api/v1/format-requests", body)).data;
```

```tsx
// apps/frontend/src/features/format-request/ui/FormatRequestBanner.tsx
import React from "react";
import { FormatRequestButton } from "./FormatRequestButton";
import type { Tier } from "@/shared/lib/tier";

const COMMUNITY_LINK =
  "https://github.com/piyush-official/FilterNArrange/blob/main/CONTRIBUTING.md#contributing-a-format";

interface Props {
  tier: Tier;
  uploadId: string;
}

export const FormatRequestBanner: React.FC<Props> = ({ tier, uploadId }) => (
  <div role="alert" style={{ padding: 12, border: "1px solid #f1c40f", borderRadius: 6 }}>
    <p>We couldn't auto-detect this format.</p>
    <p>
      <a href={COMMUNITY_LINK} target="_blank" rel="noreferrer">
        Contribute a format (OSS PR)
      </a>
      {" "}— anyone can add a new format adapter.
    </p>
    {tier === "paid" && (
      <p>
        Or, as a paid user, request maintainer-handled support:
        <FormatRequestButton uploadId={uploadId} />
      </p>
    )}
  </div>
);
```

```tsx
// apps/frontend/src/features/format-request/ui/FormatRequestButton.tsx
import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { submitFormatRequest } from "../api/formatRequestApi";

interface Props { uploadId: string; }

export const FormatRequestButton: React.FC<Props> = ({ uploadId }) => {
  const [label, setLabel] = useState<string>("");
  const m = useMutation({
    mutationFn: () => submitFormatRequest({
      upload_id: uploadId,
      user_label: label || undefined,
    }),
  });
  if (m.isSuccess) {
    return <span>Request received — ticket {m.data!.id.slice(0, 8)}.</span>;
  }
  return (
    <span>
      <input
        type="text"
        value={label}
        placeholder="Optional label (e.g. 'fixed-width-cobol')"
        onChange={e => setLabel(e.target.value)}
      />
      <button type="button" onClick={() => m.mutate()}>Request format</button>
    </span>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run apps/frontend/src/features/format-request`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/format-request
git commit -m "feat(frontend): format-request banner with always-visible OSS link + paid-only submit"
```

---

## Task 35: Frontend — admin format-request list

**Files:**
- Create: `apps/frontend/src/features/admin/ui/AdminFormatRequestList.tsx`
- Test: `apps/frontend/src/features/admin/ui/AdminFormatRequestList.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AdminFormatRequestList } from "./AdminFormatRequestList";
import * as api from "../api/adminApi";

describe("AdminFormatRequestList", () => {
  it("lists rows and ships on click", async () => {
    vi.spyOn(api, "listFormatRequests").mockResolvedValue([
      { id: "id-1", userId: "u-1", userLabel: "x", status: "triaged",
        githubIssue: 42, createdAt: "n", resolvedAt: null },
    ]);
    const ship = vi.spyOn(api, "shipFormatRequest").mockResolvedValue();
    render(<QueryClientProvider client={new QueryClient()}>
      <AdminFormatRequestList />
    </QueryClientProvider>);
    await waitFor(() => expect(screen.getByText("id-1")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /mark shipped/i }));
    expect(ship).toHaveBeenCalledWith("id-1");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run apps/frontend/src/features/admin`
Expected: FAIL.

- [ ] **Step 3: Write API + component**

```ts
// apps/frontend/src/features/admin/api/adminApi.ts
import { httpClient } from "@/shared/api/client";

export interface AdminFormatRequest {
  id: string;
  userId: string;
  userLabel: string;
  status: string;
  githubIssue: number | null;
  createdAt: string;
  resolvedAt: string | null;
}

export const listFormatRequests = async (status?: string): Promise<AdminFormatRequest[]> =>
  (await httpClient.get<AdminFormatRequest[]>("/api/v1/admin/format-requests",
    { params: status ? { status } : {} })).data;

export const shipFormatRequest = async (id: string): Promise<void> => {
  await httpClient.post(`/api/v1/admin/format-requests/${id}/ship`);
};

export const rejectFormatRequest = async (id: string): Promise<void> => {
  await httpClient.post(`/api/v1/admin/format-requests/${id}/reject`);
};
```

```tsx
// apps/frontend/src/features/admin/ui/AdminFormatRequestList.tsx
import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listFormatRequests, shipFormatRequest, rejectFormatRequest } from "../api/adminApi";

export const AdminFormatRequestList: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "format-requests", statusFilter],
    queryFn: () => listFormatRequests(statusFilter || undefined),
  });
  const ship = useMutation({
    mutationFn: shipFormatRequest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "format-requests"] }),
  });
  const reject = useMutation({
    mutationFn: rejectFormatRequest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "format-requests"] }),
  });
  return (
    <section>
      <h2>Format requests</h2>
      <label>
        Status:
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="triaged">Triaged</option>
          <option value="in-progress">In progress</option>
          <option value="shipped">Shipped</option>
          <option value="rejected">Rejected</option>
        </select>
      </label>
      {isLoading ? <div>Loading…</div> : (
        <table>
          <thead>
            <tr><th>ID</th><th>Label</th><th>Status</th>
                <th>Issue</th><th>Created</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {(data ?? []).map(r => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.userLabel}</td>
                <td>{r.status}</td>
                <td>{r.githubIssue ?? "—"}</td>
                <td>{r.createdAt}</td>
                <td>
                  <button onClick={() => ship.mutate(r.id)}>Mark shipped</button>
                  <button onClick={() => reject.mutate(r.id)}>Reject</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
};
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run apps/frontend/src/features/admin`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/admin
git commit -m "feat(frontend): admin UI for listing and transitioning format-requests"
```

---

## Task 36: Frontend — router additions

**Files:**
- Modify: `apps/frontend/src/app/router.tsx`

- [ ] **Step 1: Add routes**

```tsx
// apps/frontend/src/app/router.tsx
import { createBrowserRouter } from "react-router-dom";
import { BillingPanel } from "@/features/billing/ui/BillingPanel";
import { RecipeList } from "@/features/recipes/ui/RecipeList";
import { AdminFormatRequestList } from "@/features/admin/ui/AdminFormatRequestList";
// ... existing imports ...

export const router = createBrowserRouter([
  // ... existing routes ...
  { path: "/account/billing",       element: <BillingPanel /> },
  { path: "/recipes",               element: <RecipeListGuarded /> },
  { path: "/admin/format-requests", element: <AdminFormatRequestList /> },
]);

// Tier-aware wrapper that reads billing info from the auth context.
function RecipeListGuarded() {
  const { tier } = useTierFromAuth();
  return <RecipeList tier={tier} />;
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/app/router.tsx
git commit -m "feat(frontend): register /account/billing, /recipes, /admin/format-requests routes"
```

---

## Task 37: End-to-end test — quota 429 path

**Files:**
- Create: `tests/integration/quota_test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/quota_test.py
import os, pytest, requests

BASE = os.environ.get("GATEWAY_BASE", "http://localhost:8080")

@pytest.fixture
def free_token():
    r = requests.post(f"{BASE}/api/v1/auth/signup",
        json={"email": "qtest@e.com", "password": "qpasswd!23"})
    assert r.status_code in (200, 201)
    return r.json()["token"]

def test_free_user_429_after_quota(free_token, monkeypatch):
    # Compose-injected FREE_TIER_DAILY_OPS=3 for this test profile.
    headers = {"Authorization": f"Bearer {free_token}"}
    for i in range(3):
        r = requests.post(f"{BASE}/api/v1/detect", headers=headers,
                          files={"file": ("x.csv", b"a,b\n1,2\n")})
        assert r.status_code == 200, f"op {i} unexpectedly {r.status_code}: {r.text}"
    r = requests.post(f"{BASE}/api/v1/detect", headers=headers,
                      files={"file": ("x.csv", b"a,b\n1,2\n")})
    assert r.status_code == 429
    assert r.json()["code"] == "TIER_QUOTA_EXCEEDED"
    assert "Retry-After" in r.headers
```

- [ ] **Step 2: Run test to verify it fails (until stack up with quota=3)**

Run: `FREE_TIER_DAILY_OPS=3 docker compose up -d && pytest tests/integration/quota_test.py -v`
Expected: FAIL initially, PASS after compose with override is running.

- [ ] **Step 3: Add a CI override compose file** at `infra/docker-compose.test.yml`:

```yaml
services:
  gateway:
    environment:
      FREE_TIER_DAILY_OPS: 3
      FREE_TIER_MAX_UPLOAD_MB: 5
```

- [ ] **Step 4: Verify**

Run: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.test.yml up -d && pytest tests/integration/quota_test.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/quota_test.py infra/docker-compose.test.yml
git commit -m "test(integration): free user hits 429 after FREE_TIER_DAILY_OPS"
```

---

## Task 38: End-to-end test — 413 size, 403 feature gate

**Files:**
- Create: `tests/integration/tier_filters_test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/tier_filters_test.py
import os, pytest, requests

BASE = os.environ.get("GATEWAY_BASE", "http://localhost:8080")

@pytest.fixture
def free_token():
    r = requests.post(f"{BASE}/api/v1/auth/signup",
        json={"email": "size@e.com", "password": "qpasswd!23"})
    return r.json()["token"]

def test_413_oversize_upload(free_token):
    headers = {"Authorization": f"Bearer {free_token}"}
    big = b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB free
    r = requests.post(f"{BASE}/api/v1/detect", headers=headers,
                      files={"file": ("big.csv", big)})
    assert r.status_code == 413
    body = r.json()
    assert body["code"] == "PAYLOAD_TOO_LARGE"
    assert body["upgrade_hint"] == "/account/billing"

def test_403_paid_feature(free_token):
    headers = {"Authorization": f"Bearer {free_token}"}
    r = requests.post(f"{BASE}/api/v1/ai/nl-to-filter", headers=headers,
                      json={"prompt": "show rows where age > 18"})
    assert r.status_code == 403
    assert r.json()["code"] == "FEATURE_REQUIRES_PAID_TIER"
```

- [ ] **Step 2: Run test to verify it fails / passes against stack**

Run: `pytest tests/integration/tier_filters_test.py -v`
Expected: PASS against running stack.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/tier_filters_test.py
git commit -m "test(integration): 413 oversize and 403 paid-feature gating"
```

---

## Task 39: End-to-end test — retention purges 25h-old free, retains 5d paid

**Files:**
- Create: `tests/integration/retention_test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/retention_test.py
import asyncio, datetime as dt
import asyncpg, pytest
from minio import Minio
import io, os, subprocess

UTC = dt.timezone.utc
DSN = os.environ.get("POSTGRES_DSN",
    "postgresql://gateway:gateway@localhost:5432/filternarrange")

@pytest.mark.asyncio
async def test_retention_free_25h_purged_and_paid_5d_retained():
    pool = await asyncpg.create_pool(DSN)
    minio = Minio("localhost:9000", access_key="minio", secret_key="minio12345",
                  secure=False)
    for bkt in ["uploads", "results"]:
        if not minio.bucket_exists(bkt):
            minio.make_bucket(bkt)

    # Seed free user with 25h-old upload
    async with pool.acquire() as c:
        free_id = await c.fetchval(
            "INSERT INTO users(id, email) VALUES (gen_random_uuid(), $1) RETURNING id",
            "ret-free@e.com")
        await c.execute(
            "INSERT INTO subscriptions(id, user_id, tier, status, started_at) "
            "VALUES (gen_random_uuid(), $1, 'free', 'active', now())", free_id)
        free_job = await c.fetchval(
            "INSERT INTO jobs(id, user_id, kind, status, params, created_at) "
            "VALUES (gen_random_uuid(), $1, 'convert', 'completed', "
            "  jsonb_build_object('input', jsonb_build_object('ref', $2)), $3) "
            "RETURNING id",
            free_id, "uploads/free/" + str(free_id) + ".bin",
            dt.datetime.now(UTC) - dt.timedelta(hours=25))
        minio.put_object("uploads", f"free/{free_id}.bin",
                         io.BytesIO(b"x"), 1)

        # Paid user with 5d-old upload
        paid_id = await c.fetchval(
            "INSERT INTO users(id, email) VALUES (gen_random_uuid(), $1) RETURNING id",
            "ret-paid@e.com")
        await c.execute(
            "INSERT INTO subscriptions(id, user_id, tier, status, started_at) "
            "VALUES (gen_random_uuid(), $1, 'paid', 'active', now())", paid_id)
        await c.execute(
            "INSERT INTO jobs(id, user_id, kind, status, params, created_at) "
            "VALUES (gen_random_uuid(), $1, 'convert', 'completed', "
            "  jsonb_build_object('input', jsonb_build_object('ref', $2)), $3)",
            paid_id, "uploads/paid/" + str(paid_id) + ".bin",
            dt.datetime.now(UTC) - dt.timedelta(days=5))
        minio.put_object("uploads", f"paid/{paid_id}.bin",
                         io.BytesIO(b"y"), 1)

    # Trigger retention --once via docker compose exec
    subprocess.run(
        ["docker", "compose", "exec", "-T", "retention-worker",
         "python", "-m", "filternarrange_engine.retention.cli", "--once"],
        check=True,
        env=dict(os.environ),
    )

    # Verify
    objs = [o.object_name for o in minio.list_objects("uploads", recursive=True)]
    assert f"free/{free_id}.bin" not in objs, "Free 25h upload should be purged"
    assert f"paid/{paid_id}.bin" in objs,     "Paid 5d upload should be retained"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/retention_test.py -v`
Expected: FAIL until stack + retention-worker is up.

- [ ] **Step 3: Bring up stack and re-run**

Run: `docker compose up -d && pytest tests/integration/retention_test.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/retention_test.py
git commit -m "test(integration): retention purges 25h-old free, retains 5d-old paid"
```

---

## Task 40: End-to-end test — format-request lifecycle with mock Octokit

**Files:**
- Create: `tests/integration/format_request_test.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/format_request_test.py
import os, time, pytest, requests, asyncpg, asyncio

BASE = os.environ.get("GATEWAY_BASE", "http://localhost:8080")
DSN = os.environ.get("POSTGRES_DSN",
    "postgresql://gateway:gateway@localhost:5432/filternarrange")

@pytest.fixture
def paid_token():
    r = requests.post(f"{BASE}/api/v1/auth/signup",
        json={"email": "fr-paid@e.com", "password": "frpass!23"})
    assert r.status_code in (200, 201)
    # Promote to paid via test-only admin endpoint or direct DB.
    requests.post(f"{BASE}/api/v1/test/_promote_paid",
        json={"email": "fr-paid@e.com"})
    r2 = requests.post(f"{BASE}/api/v1/auth/login",
        json={"email": "fr-paid@e.com", "password": "frpass!23"})
    return r2.json()["token"]

def test_free_cannot_submit():
    r = requests.post(f"{BASE}/api/v1/auth/signup",
        json={"email": "fr-free@e.com", "password": "frpass!23"})
    tok = r.json()["token"]
    s = requests.post(f"{BASE}/api/v1/format-requests",
        headers={"Authorization": f"Bearer {tok}"},
        json={"upload_id": "00000000-0000-0000-0000-000000000001"})
    assert s.status_code == 403
    assert s.json()["code"] == "FEATURE_REQUIRES_PAID_TIER"

@pytest.mark.asyncio
async def test_paid_submit_persists_publishes_and_mirrors(paid_token):
    # Mock GitHub server already pointed-at via FILTERNARRANGE_GITHUB_API_BASE
    # env var in docker-compose.test.yml; it returns {"number": 9001}.
    r = requests.post(f"{BASE}/api/v1/format-requests",
        headers={"Authorization": f"Bearer {paid_token}"},
        json={"upload_id": "00000000-0000-0000-0000-000000000002",
              "user_label": "fixed-width-cobol"})
    assert r.status_code == 201
    ticket_id = r.json()["id"]

    # Wait up to 10s for consumer to mirror.
    deadline = time.time() + 10
    pool = await asyncpg.create_pool(DSN)
    issue = None
    while time.time() < deadline:
        async with pool.acquire() as c:
            row = await c.fetchrow(
                "SELECT github_issue, status FROM format_requests WHERE id = $1",
                ticket_id)
            if row and row["github_issue"]:
                issue = row["github_issue"]
                assert row["status"] == "triaged"
                break
        await asyncio.sleep(0.5)
    assert issue == 9001
```

- [ ] **Step 2: Add the mock GitHub server to compose**

In `infra/docker-compose.test.yml`:

```yaml
services:
  mock-github:
    image: mockoon/cli:latest
    command: ["--data", "/data/mock-github.json", "--port", "3001"]
    volumes:
      - ./mock-github.json:/data/mock-github.json:ro
    ports: ["3001:3001"]
  gateway:
    environment:
      FILTERNARRANGE_GITHUB_API_BASE: http://mock-github:3001
      FILTERNARRANGE_GITHUB_TOKEN: test-token
      FILTERNARRANGE_GITHUB_REPO: piyush-official/FilterNArrange
```

and `infra/mock-github.json`:

```json
{
  "routes": [
    {
      "method": "post",
      "endpoint": "repos/piyush-official/FilterNArrange/issues",
      "responses": [{
        "status": 201,
        "headers": [{ "key": "Content-Type", "value": "application/json" }],
        "body": "{\"number\":9001}"
      }]
    }
  ]
}
```

- [ ] **Step 3: Run tests**

Run: `docker compose -f infra/docker-compose.yml -f infra/docker-compose.test.yml up -d && pytest tests/integration/format_request_test.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/format_request_test.py \
        infra/docker-compose.test.yml \
        infra/mock-github.json
git commit -m "test(integration): format-request lifecycle through mock GitHub Octokit"
```

---

## Task 41: End-to-end test — recipe CRUD across both tiers

**Files:**
- Create: `tests/integration/recipe_crud_test.py`

- [ ] **Step 1: Write the test**

```python
# tests/integration/recipe_crud_test.py
import os, pytest, requests

BASE = os.environ.get("GATEWAY_BASE", "http://localhost:8080")

def _signup(email):
    r = requests.post(f"{BASE}/api/v1/auth/signup",
        json={"email": email, "password": "rpass!23"})
    return r.json()["token"]

def _promote_paid(email):
    requests.post(f"{BASE}/api/v1/test/_promote_paid", json={"email": email})

def _login(email):
    r = requests.post(f"{BASE}/api/v1/auth/login",
        json={"email": email, "password": "rpass!23"})
    return r.json()["token"]

def test_free_user_recipes_403():
    tok = _signup("r-free@e.com")
    r = requests.get(f"{BASE}/api/v1/recipes",
        headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403
    assert r.json()["code"] == "FEATURE_REQUIRES_PAID_TIER"

def test_paid_full_lifecycle():
    _signup("r-paid@e.com")
    _promote_paid("r-paid@e.com")
    tok = _login("r-paid@e.com")
    h = {"Authorization": f"Bearer {tok}"}

    # Create
    c = requests.post(f"{BASE}/api/v1/recipes", headers=h,
        json={"name": "r1", "recipe": {"out": "json"}})
    assert c.status_code == 201
    rid = c.json()["id"]

    # Get
    g = requests.get(f"{BASE}/api/v1/recipes/{rid}", headers=h)
    assert g.status_code == 200
    assert g.json()["name"] == "r1"

    # List
    l = requests.get(f"{BASE}/api/v1/recipes", headers=h)
    assert l.status_code == 200
    assert any(r["id"] == rid for r in l.json())

    # Update
    u = requests.put(f"{BASE}/api/v1/recipes/{rid}", headers=h,
        json={"name": "r1b", "recipe": {"out": "yaml"}})
    assert u.status_code == 200
    assert u.json()["name"] == "r1b"

    # Delete
    d = requests.delete(f"{BASE}/api/v1/recipes/{rid}", headers=h)
    assert d.status_code == 204

    # Confirm gone
    g2 = requests.get(f"{BASE}/api/v1/recipes/{rid}", headers=h)
    assert g2.status_code == 404
    assert g2.json()["code"] == "RECIPE_NOT_FOUND"
```

- [ ] **Step 2: Run test**

Run: `pytest tests/integration/recipe_crud_test.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/recipe_crud_test.py
git commit -m "test(integration): recipe CRUD passes paid, blocks free with 403"
```

---

## Task 42: OpenAPI contract additions

**Files:**
- Modify: `contracts/openapi/gateway-public.v1.yaml`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/contract/OpenApiSchemaTest.java`

- [ ] **Step 1: Write the failing test**

```java
package io.filternarrange.gateway.contract;

import org.junit.jupiter.api.Test;
import org.yaml.snakeyaml.Yaml;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class OpenApiSchemaTest {

    @Test
    void publicSchemaIncludesAllPlanFPaths() throws Exception {
        String yaml = Files.readString(
            Path.of("contracts/openapi/gateway-public.v1.yaml"));
        Map<String, Object> doc = new Yaml().load(yaml);
        Map<String, Object> paths = (Map<String, Object>) doc.get("paths");
        assertThat(paths).containsKeys(
            "/api/v1/billing/me",
            "/api/v1/recipes",
            "/api/v1/recipes/{id}",
            "/api/v1/format-requests",
            "/api/v1/admin/format-requests",
            "/api/v1/admin/format-requests/{id}/ship",
            "/api/v1/admin/format-requests/{id}/reject"
        );
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./mvnw -pl apps/gateway test -Dtest=OpenApiSchemaTest`
Expected: FAIL.

- [ ] **Step 3: Append paths to OpenAPI**

```yaml
# contracts/openapi/gateway-public.v1.yaml (additions)
paths:
  /api/v1/billing/me:
    get:
      summary: Current tier + today's quota usage
      security: [bearer: []]
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                type: object
                required: [tier, ops_today, daily_ops_limit, max_upload_mb]
                properties:
                  tier:             { type: string, enum: [free, paid] }
                  ops_today:        { type: integer }
                  daily_ops_limit:  { type: integer }
                  max_upload_mb:    { type: integer }
                  unlimited_ops:    { type: boolean }
                  unlimited_upload: { type: boolean }
                  upgrade_url:      { type: string, nullable: true }

  /api/v1/recipes:
    get:
      summary: List recipes (paid only)
      security: [bearer: []]
      responses:
        "200": { description: OK }
        "403":
          description: FEATURE_REQUIRES_PAID_TIER
          content: { application/json: { schema: { $ref: '#/components/schemas/ErrorEnvelope' } } }
    post:
      summary: Create recipe (paid only)
      security: [bearer: []]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name, recipe]
              properties:
                name:   { type: string }
                recipe: { type: object }
      responses:
        "201": { description: Created }
        "403": { $ref: '#/components/responses/PaidOnly' }

  /api/v1/recipes/{id}:
    parameters:
      - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
    get:    { security: [bearer: []], responses: { "200": { description: OK }, "404": { description: RECIPE_NOT_FOUND } } }
    put:    { security: [bearer: []], responses: { "200": { description: OK } } }
    delete: { security: [bearer: []], responses: { "204": { description: No Content } } }

  /api/v1/format-requests:
    post:
      summary: Submit a format request (paid only)
      security: [bearer: []]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [upload_id]
              properties:
                upload_id:  { type: string, format: uuid }
                user_label: { type: string }
      responses:
        "201": { description: Created }
        "403": { $ref: '#/components/responses/PaidOnly' }

  /api/v1/admin/format-requests:
    get:
      summary: Admin list of format requests
      security: [bearer: []]
      parameters:
        - { name: status, in: query, schema: { type: string,
            enum: [open, triaged, in-progress, shipped, rejected] } }
      responses:
        "200": { description: OK }
        "403": { description: ADMIN_REQUIRED }

  /api/v1/admin/format-requests/{id}/ship:
    post:
      security: [bearer: []]
      parameters:
        - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
      responses: { "200": { description: OK }, "404": { description: FORMAT_REQUEST_NOT_FOUND } }

  /api/v1/admin/format-requests/{id}/reject:
    post:
      security: [bearer: []]
      parameters:
        - { name: id, in: path, required: true, schema: { type: string, format: uuid } }
      responses: { "200": { description: OK }, "404": { description: FORMAT_REQUEST_NOT_FOUND } }

components:
  responses:
    PaidOnly:
      description: FEATURE_REQUIRES_PAID_TIER
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ErrorEnvelope' }
  schemas:
    ErrorEnvelope:
      type: object
      required: [code, message]
      properties:
        code:         { type: string }
        plugin_id:    { type: string }
        message:      { type: string }
        trace_id:     { type: string }
        upgrade_hint: { type: string, nullable: true }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./mvnw -pl apps/gateway test -Dtest=OpenApiSchemaTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add contracts/openapi/gateway-public.v1.yaml \
        apps/gateway/src/test/java/io/filternarrange/gateway/contract/OpenApiSchemaTest.java
git commit -m "feat(contracts): OpenAPI paths for billing, recipes, format-requests, admin"
```

---

## Task 43: ADR documenting the tier-config + plugin-registry lever choices

**Files:**
- Create: `docs/decisions/ADR-0005-tier-and-format-request-model.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-0005 — Tier system & format-request workflow

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-06-07 |
| **Deciders** | piyush-official |
| **Related** | ADR-0001 (stack), spec §1/§5 |

## Context

Spec §1 calls for an open-core model with four tier levers (file-size, daily-op
quota, recipes + retention, advanced-feature gating) plus a format-request
workflow with both a free OSS-PR path and a paid maintainer-handled path.

## Decision

1. Per-tier limits are env-driven via `TierConfig` (`FREE_TIER_MAX_UPLOAD_MB`,
   `FREE_TIER_DAILY_OPS`, `PAID_TIER_MAX_UPLOAD_MB=500`,
   `PAID_TIER_DAILY_OPS=0` (unlimited)) — production thresholds finalized by
   the open question §10/2.
2. Tier is sourced from Postgres `subscriptions` (one active row per user,
   enforced by `one_active_sub_per_user` partial unique index) and cached in
   Redis at `gw:tier:{user_id}` for 60s.
3. Quota counter lives at `gw:rate:user:{user_id}:ops:{date-UTC}`, TTL =
   end-of-day-UTC. 429 + `Retry-After` returned on overflow.
4. Feature gating reads `plugin_registry.required_tier` (cached). Free-tier
   features in v1: format/filter/analysis plugins **except** AI; recipe/batch/
   format-request endpoints are paid.
5. Kafka jobs topic splits into `topic.v1.jobs.paid` and `topic.v1.jobs.free`,
   each partitioned by `user_id`. Two consumer groups; paid runs higher
   `WORKER_CONCURRENCY` for genuine priority.
6. Format-request workflow: OSS PR link always visible. POST endpoint is paid-
   only; gateway consumes the topic and mirrors to GitHub issues via the
   `GithubIssueClient` (Java 21 `HttpClient`, no extra dep).
7. Retention purges run in a dedicated `retention-worker` container
   (same image, `--retention` flag, apscheduler interval loop). Per-tier
   cutoffs from spec §5.

## Consequences

- Free users have a hard upper bound on cost without losing the OSS story.
- Paid signals can be raised/lowered solely via env variables.
- Adding a new paid-only feature is a single `plugin_registry` row.
- Stripe wiring is deferred — `subscriptions.external_ref` already exists.

## Follow-ups

- ADR-0006 once Stripe is wired (post-v1).
- Tune `FREE_TIER_DAILY_OPS` once first month of usage data is in.
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/ADR-0005-tier-and-format-request-model.md
git commit -m "docs(adr): ADR-0005 — tier system and format-request workflow"
```

---

## Self-Review Notes

**Spec coverage check:**
- §1 four tier levers: file-size (Task 9), daily-ops (Task 8), recipes + retention (Tasks 3, 14-16, 26-29), advanced-feature gating (Tasks 4, 11, 12). ✓
- §1 format-request workflow with community link + paid path: Tasks 18-23, 34. ✓
- §5 `subscriptions` (Task 1), `format_requests` (Task 2), `recipes` (Task 3), `plugin_registry` (Task 4). ✓
- §3 backpressure & quotas — per-tier consumer groups via split topic (Task 17). ✓
- §5 retention windows (Tasks 26-29, 39). ✓
- §3 priority via separate consumer groups (Task 17 + compose). ✓
- §6 hexagonal layout (domain → app → infra → api) followed in every Java task. ✓

**Placeholder scan:** none. All steps contain full code.

**Type consistency:**
- `Tier` enum spelled identically across Java (Task 5) and TS (Task 30) using lowercase wire value.
- `AuthenticatedUser` referenced from Plan B; signature `(UUID id, String email, boolean admin)` consistent in Tasks 8, 9, 10, 12, 16, 20.
- `AuditEmitter` from Plan D; method signature `emit(UUID, String, String, Map)` consistent in Tasks 15, 19, 22, 23, 25.
- `SampleStore` referenced from Plan D as `storeFirstNKb(userId, uploadId, kb)` / `readFirstKb(ref, kb)` — consistent in Tasks 19, 22.
- `FormatRequest.Status` enum maps `IN_PROGRESS ↔ "in-progress"` everywhere it's used.
- Kafka topics: `topic.v1.jobs.paid|free`, `topic.v1.format-requests`, `topic.v1.audit-events`. Plan D published `topic.v1.audit-events`; this plan does not change it.
- Plugin IDs in `plugin_registry` (Task 4) match the gate lookups (Task 12) and tests (Task 11).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-07-F-tiers-and-format-requests.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?
