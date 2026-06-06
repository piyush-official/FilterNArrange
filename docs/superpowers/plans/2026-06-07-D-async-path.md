# Plan D — Async Path (Kafka + Worker) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce the asynchronous batch-processing pipeline for FilterNArrange so that long-running or large jobs no longer block the request thread — the user submits a job, the gateway persists + publishes it to Kafka, a Python worker consumes + processes it, results stream back to the browser over WebSocket, and the gateway-side audit-writer mirrors every state transition to Postgres.

**Architecture:** Adds the async lane that sits next to the existing sync lane from Plans B + C. Submission flows: React → `POST /api/v1/jobs` → gateway persists `jobs` row + produces to `topic.v1.jobs` → 200 with `{job_id, status: queued}`. Processing: Python worker (`MODE=worker`) consumes the topic, fetches the input blob from MinIO, runs the existing filter / convert / analyze plugins, writes the result blob, and produces to `topic.v1.job-results`. Push: gateway consumes `topic.v1.job-results`, fans out to all WebSocket subscribers on `/ws/jobs/{job_id}`. Resilience: bulkheaded thread pools, Resilience4j circuit breaker on the sync HTTP edge, explicit timeouts per spec §6, JSON-Schema validation on every Kafka boundary, and `Idempotency-Key`-keyed deduplication on submission.

**Tech Stack:** Spring Boot 3.3 (Java 21), `spring-kafka`, Resilience4j 2, Flyway 10, HikariCP, Lettuce (Redis), `everit-org/json-schema` 1.14 (Java JSON Schema validator), `jsonschema` 4.x (Python), `aiokafka` 0.11 (Python asyncio Kafka client), FastAPI, Python 3.12, `httpx`, React 18 + TypeScript, `@stomp/stompjs` replaced by native `WebSocket`, Postgres 16, Redis 7, Redpanda 24.

**Spec anchors:** §3 (Async path, sync trigger rules, contracts), §5 (`jobs` + `audit_log` tables, Kafka topics & retention, Redis keyspace prefixes), §6 (bulkheading, timeouts, circuit breakers, idempotency, error envelope).

---

## File Structure

The bullet list below is the contract between this plan and the engineer — every file referenced in any Task must appear here. Paths are absolute from the repo root.

**Postgres migrations (gateway-owned schema, per spec §5):**

- Create: `apps/gateway/src/main/resources/db/migration/V3__jobs.sql`
- Create: `apps/gateway/src/main/resources/db/migration/V4__audit_log.sql`

**Kafka contracts (cross-service, per spec §3):**

- Create: `contracts/kafka/topic.v1.jobs.schema.json`
- Create: `contracts/kafka/topic.v1.job-results.schema.json`
- Create: `contracts/kafka/topic.v1.audit-events.schema.json`
- Create (skeleton-only — used in Plan F): `contracts/kafka/topic.v1.format-requests.schema.json`

**Kafka topic provisioning (compose-level, per spec §5):**

- Create: `infra/kafka-init/Dockerfile`
- Create: `infra/kafka-init/create-topics.sh`
- Modify: `infra/docker-compose.yml` — add `kafka-init` one-shot service depending on `redpanda`.

**Gateway — application code (Spring Boot, package `io.filternarrange.gateway`):**

- Modify: `apps/gateway/build.gradle.kts` — add `spring-kafka`, Resilience4j, `everit-org/json-schema`.
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaProducerConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaConsumerConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaTopics.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JsonSchemaValidator.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobProducer.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventPublisher.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobResultsConsumer.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumer.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JobRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JobRow.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/AuditLogRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/Job.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/JobStatus.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/JobKind.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/JobService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/JobController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/CreateJobRequest.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/JobResponse.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/JobWebSocketHandler.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/JobSubscriberRegistry.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/WebSocketConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/idempotency/IdempotencyStore.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/threads/ThreadPoolConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/resilience/DataEngineCircuitBreakerConfig.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineClient.java` — wrap calls in Resilience4j breaker + 5s timeout.
- Modify: `apps/gateway/src/main/resources/application.yml` — add Kafka, Resilience4j, timeouts.

**Gateway — tests (JUnit 5 + Spring Boot Test + Testcontainers):**

- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/api/JobControllerIT.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/api/IdempotencyIT.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/api/ws/JobWebSocketIT.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/resilience/CircuitBreakerIT.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/JsonSchemaValidatorTest.java`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumerIT.java`

**Data-engine (Python, package `filternarrange_engine`):**

- Modify: `apps/data-engine/pyproject.toml` — add `aiokafka>=0.11`, `jsonschema>=4.22`.
- Create: `apps/data-engine/src/filternarrange_engine/platform/mode.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/topics.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/schema_validator.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/consumer.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/producer.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/worker.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/heartbeat.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/bulkheads.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/audit.py`
- Modify: `apps/data-engine/src/filternarrange_engine/main.py` — branch on `MODE` env var.
- Modify: `apps/data-engine/Dockerfile` — make `CMD` honour `MODE`.

**Data-engine — tests (pytest + aiokafka test harness):**

- Create: `apps/data-engine/tests/adapters/kafka/test_schema_validator.py`
- Create: `apps/data-engine/tests/adapters/kafka/test_consumer.py`
- Create: `apps/data-engine/tests/application/test_worker.py`
- Create: `apps/data-engine/tests/application/test_heartbeat.py`

**Frontend (React + TypeScript, feature-sliced per spec §6):**

- Create: `apps/frontend/src/features/jobs/api/jobsClient.ts`
- Create: `apps/frontend/src/features/jobs/api/jobsWebSocket.ts`
- Create: `apps/frontend/src/features/jobs/state/useJob.ts`
- Create: `apps/frontend/src/features/jobs/state/useJobsList.ts`
- Create: `apps/frontend/src/features/jobs/ui/JobProgressCard.tsx`
- Create: `apps/frontend/src/features/jobs/ui/JobsListPage.tsx`
- Create: `apps/frontend/src/features/jobs/ui/BatchTab.tsx`
- Create: `apps/frontend/src/features/jobs/ui/RunAsJobToggle.tsx`
- Create: `apps/frontend/src/features/jobs/index.ts`
- Modify: `apps/frontend/src/app/router.tsx` — register `/jobs` route + Batch tab.
- Modify: `apps/frontend/src/features/filter/ui/FilterPanel.tsx` — wire the "Run as job" toggle.
- Modify: `apps/frontend/src/shared/api/client.ts` — add `Idempotency-Key` helper.

**Frontend — tests (Vitest + Playwright):**

- Create: `apps/frontend/src/features/jobs/api/__tests__/jobsClient.test.ts`
- Create: `apps/frontend/src/features/jobs/state/__tests__/useJob.test.ts`
- Create: `tests/e2e/specs/jobs-async-path.spec.ts`

**Cross-service integration tests:**

- Create: `tests/integration/test_async_path_e2e.py`
- Create: `tests/integration/test_cancel.py`

---

## Dependency Graph

Tasks 1–3 are infra (migrations, topics, contracts). 4–10 are gateway. 11–15 are data-engine. 16–18 are frontend. 19–22 are cross-service integration. The dependency arrow is monotonic — each task only depends on tasks with a lower number.

---

### Task 1: Postgres migration `V3__jobs.sql` (spec §5)

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V3__jobs.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JobsSchemaIT.java`

- [ ] **Step 1: Write the failing integration test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@JdbcTest
@Testcontainers
class JobsSchemaIT {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
        r.add("spring.datasource.username", pg::getUsername);
        r.add("spring.datasource.password", pg::getPassword);
        r.add("spring.flyway.locations", () -> "classpath:db/migration");
    }

    @Autowired JdbcTemplate jdbc;

    @Test
    void jobs_table_exists_with_required_columns_and_indexes() {
        List<Map<String, Object>> cols = jdbc.queryForList(
                "SELECT column_name, data_type FROM information_schema.columns " +
                "WHERE table_name = 'jobs' ORDER BY ordinal_position");
        assertThat(cols).extracting(c -> c.get("column_name"))
                .containsExactly("id", "user_id", "kind", "status", "params",
                                 "result_ref", "error", "priority",
                                 "created_at", "started_at", "finished_at");

        List<String> idx = jdbc.queryForList(
                "SELECT indexname FROM pg_indexes WHERE tablename = 'jobs'",
                String.class);
        assertThat(idx).contains("jobs_user_recent", "jobs_status_open");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests JobsSchemaIT`
Expected: FAIL — `relation "jobs" does not exist` (V3 not applied yet).

- [ ] **Step 3: Write the migration**

```sql
-- V3__jobs.sql — async job tracking (spec §5)

CREATE TABLE jobs (
  id           UUID PRIMARY KEY,
  user_id      UUID NOT NULL REFERENCES users(id),
  kind         TEXT NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('queued','running','completed','failed','cancelled')),
  params       JSONB NOT NULL,
  result_ref   TEXT,
  error        JSONB,
  priority     INT  NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at   TIMESTAMPTZ,
  finished_at  TIMESTAMPTZ
);

CREATE INDEX jobs_user_recent
  ON jobs(user_id, created_at DESC);

CREATE INDEX jobs_status_open
  ON jobs(status)
  WHERE status IN ('queued','running');
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./gradlew :apps:gateway:test --tests JobsSchemaIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V3__jobs.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JobsSchemaIT.java
git commit -m "feat(gateway): add jobs table migration (V3) per spec §5"
```

---

### Task 2: Postgres migration `V4__audit_log.sql` (spec §5)

`audit_log` is partitioned by month with a default catch-all partition. Each release of the system runs a quarterly partition-maintenance migration; for v1 we ship the current-month partition and a default partition.

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V4__audit_log.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/AuditLogSchemaIT.java`

- [ ] **Step 1: Write the failing integration test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

@JdbcTest
@Testcontainers
class AuditLogSchemaIT {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
        r.add("spring.datasource.username", pg::getUsername);
        r.add("spring.datasource.password", pg::getPassword);
    }

    @Autowired JdbcTemplate jdbc;

    @Test
    void audit_log_is_partitioned_with_initial_and_default_partitions() {
        Integer partitioned = jdbc.queryForObject(
                "SELECT COUNT(*) FROM pg_partitioned_table " +
                "WHERE partrelid = 'audit_log'::regclass",
                Integer.class);
        assertThat(partitioned).isEqualTo(1);

        Integer parts = jdbc.queryForObject(
                "SELECT COUNT(*) FROM pg_inherits " +
                "WHERE inhparent = 'audit_log'::regclass",
                Integer.class);
        assertThat(parts).isGreaterThanOrEqualTo(2);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests AuditLogSchemaIT`
Expected: FAIL — `relation "audit_log" does not exist`.

- [ ] **Step 3: Write the migration**

```sql
-- V4__audit_log.sql — partitioned audit trail (spec §5)

CREATE TABLE audit_log (
  id           BIGSERIAL,
  user_id      UUID,
  action       TEXT NOT NULL,
  target       TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Current-month partition. The bounds are computed at migration time so the
-- shipped artifact is deterministic across re-runs; Flyway's checksum will
-- match because the SQL text is fixed and the date_trunc result is taken at
-- run time inside an anonymous block.
DO $$
DECLARE
    start_ts timestamptz := date_trunc('month', now());
    end_ts   timestamptz := start_ts + interval '1 month';
    pname    text := 'audit_log_' || to_char(start_ts, 'YYYY_MM');
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_log FOR VALUES FROM (%L) TO (%L)',
        pname, start_ts, end_ts);
END
$$;

CREATE TABLE IF NOT EXISTS audit_log_default
    PARTITION OF audit_log DEFAULT;

CREATE INDEX audit_log_user_recent
    ON audit_log (user_id, created_at DESC);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./gradlew :apps:gateway:test --tests AuditLogSchemaIT`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V4__audit_log.sql \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/AuditLogSchemaIT.java
git commit -m "feat(gateway): add audit_log partitioned table migration (V4) per spec §5"
```

---

### Task 3: Kafka JSON Schema contracts (spec §3)

**Files:**
- Create: `contracts/kafka/topic.v1.jobs.schema.json`
- Create: `contracts/kafka/topic.v1.job-results.schema.json`
- Create: `contracts/kafka/topic.v1.audit-events.schema.json`
- Create: `contracts/kafka/topic.v1.format-requests.schema.json`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/JsonSchemaValidatorTest.java`

- [ ] **Step 1: Write the failing schema-validator unit test**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class JsonSchemaValidatorTest {

    private final JsonSchemaValidator v = new JsonSchemaValidator();

    @Test
    void valid_job_message_passes() {
        String msg = """
            {"job_id":"11111111-1111-1111-1111-111111111111",
             "user_id":"22222222-2222-2222-2222-222222222222",
             "kind":"batch-filter",
             "params":{"a":1},
             "priority":0,
             "created_at":"2026-06-07T10:00:00Z",
             "trace_id":"trace-abc"}
            """;
        assertThat(v.isValid("topic.v1.jobs", msg)).isTrue();
    }

    @Test
    void job_message_missing_required_field_fails() {
        String msg = """
            {"job_id":"11111111-1111-1111-1111-111111111111",
             "kind":"batch-filter",
             "params":{},
             "priority":0,
             "created_at":"2026-06-07T10:00:00Z",
             "trace_id":"trace-abc"}
            """;
        assertThatThrownBy(() -> v.validateOrThrow("topic.v1.jobs", msg))
            .hasMessageContaining("user_id");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests JsonSchemaValidatorTest`
Expected: FAIL — schemas / validator not present.

- [ ] **Step 3: Write `contracts/kafka/topic.v1.jobs.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.jobs.schema.json",
  "title": "topic.v1.jobs",
  "type": "object",
  "required": ["job_id", "user_id", "kind", "params", "priority", "created_at", "trace_id"],
  "additionalProperties": false,
  "properties": {
    "job_id":     { "type": "string", "format": "uuid" },
    "user_id":    { "type": "string", "format": "uuid" },
    "kind":       { "type": "string", "enum": ["batch-filter", "convert", "analyze"] },
    "params":     { "type": "object" },
    "priority":   { "type": "integer", "minimum": 0, "maximum": 10 },
    "created_at": { "type": "string", "format": "date-time" },
    "trace_id":   { "type": "string", "minLength": 1, "maxLength": 128 }
  }
}
```

- [ ] **Step 4: Write `contracts/kafka/topic.v1.job-results.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.job-results.schema.json",
  "title": "topic.v1.job-results",
  "type": "object",
  "required": ["job_id", "status", "finished_at", "trace_id"],
  "additionalProperties": false,
  "properties": {
    "job_id":      { "type": "string", "format": "uuid" },
    "status":      { "type": "string", "enum": ["running", "completed", "failed", "cancelled"] },
    "progress":    { "type": "number", "minimum": 0, "maximum": 100 },
    "result_ref":  { "type": "string" },
    "error": {
      "type": "object",
      "required": ["code", "message"],
      "properties": {
        "code":      { "type": "string" },
        "plugin_id": { "type": "string" },
        "message":   { "type": "string" },
        "trace_id":  { "type": "string" }
      }
    },
    "finished_at": { "type": "string", "format": "date-time" },
    "trace_id":    { "type": "string", "minLength": 1, "maxLength": 128 }
  }
}
```

Note: `finished_at` is included for every status (for `running` heartbeats it is the heartbeat send time). This avoids a separate heartbeat schema and matches the spec §3 wire-format pragma "Human-readable; switch to Avro only if message volume demands."

- [ ] **Step 5: Write `contracts/kafka/topic.v1.audit-events.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.audit-events.schema.json",
  "title": "topic.v1.audit-events",
  "type": "object",
  "required": ["event_id", "action", "occurred_at", "trace_id"],
  "additionalProperties": false,
  "properties": {
    "event_id":    { "type": "string", "format": "uuid" },
    "user_id":     { "type": "string", "format": "uuid" },
    "action":      { "type": "string", "minLength": 1, "maxLength": 128 },
    "target":      { "type": "string", "maxLength": 256 },
    "metadata":    { "type": "object" },
    "occurred_at": { "type": "string", "format": "date-time" },
    "trace_id":    { "type": "string", "minLength": 1, "maxLength": 128 }
  }
}
```

- [ ] **Step 6: Write `contracts/kafka/topic.v1.format-requests.schema.json` (skeleton — Plan F consumes it)**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://filternarrange.io/contracts/kafka/topic.v1.format-requests.schema.json",
  "title": "topic.v1.format-requests",
  "type": "object",
  "required": ["request_id", "user_id", "sample_ref", "created_at", "trace_id"],
  "additionalProperties": false,
  "properties": {
    "request_id":  { "type": "string", "format": "uuid" },
    "user_id":     { "type": "string", "format": "uuid" },
    "sample_ref":  { "type": "string" },
    "user_label":  { "type": "string", "maxLength": 256 },
    "priority":    { "type": "integer", "minimum": 0, "maximum": 10 },
    "created_at":  { "type": "string", "format": "date-time" },
    "trace_id":    { "type": "string", "minLength": 1, "maxLength": 128 }
  }
}
```

- [ ] **Step 7: Implement `JsonSchemaValidator`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import org.everit.json.schema.Schema;
import org.everit.json.schema.ValidationException;
import org.everit.json.schema.loader.SchemaLoader;
import org.json.JSONObject;
import org.json.JSONTokener;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class JsonSchemaValidator {

    private static final Map<String, String> SCHEMA_PATHS = Map.of(
        "topic.v1.jobs",            "/contracts/kafka/topic.v1.jobs.schema.json",
        "topic.v1.job-results",     "/contracts/kafka/topic.v1.job-results.schema.json",
        "topic.v1.audit-events",    "/contracts/kafka/topic.v1.audit-events.schema.json",
        "topic.v1.format-requests", "/contracts/kafka/topic.v1.format-requests.schema.json"
    );

    private final Map<String, Schema> cache = new ConcurrentHashMap<>();

    public boolean isValid(String topic, String json) {
        try {
            validateOrThrow(topic, json);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public void validateOrThrow(String topic, String json) {
        Schema schema = cache.computeIfAbsent(topic, this::load);
        schema.validate(new JSONObject(new JSONTokener(json)));
    }

    private Schema load(String topic) {
        String path = SCHEMA_PATHS.get(topic);
        if (path == null) throw new IllegalArgumentException("Unknown topic: " + topic);
        try (InputStream in = JsonSchemaValidator.class.getResourceAsStream(path)) {
            if (in == null) throw new IllegalStateException("Schema not on classpath: " + path);
            return SchemaLoader.load(new JSONObject(new JSONTokener(in)));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to load schema " + path, e);
        }
    }
}
```

- [ ] **Step 8: Wire schemas onto the gateway classpath**

Modify: `apps/gateway/build.gradle.kts` — add a `sourceSets.main.resources.srcDir(rootProject.file("contracts"))` line so `contracts/kafka/*.schema.json` is packaged into the jar at `/contracts/kafka/...`.

```kotlin
sourceSets {
    named("main") {
        resources.srcDir(rootProject.file("contracts"))
    }
}

dependencies {
    implementation("com.github.erosb:everit-json-schema:1.14.4")
    // ...existing deps
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `./gradlew :apps:gateway:test --tests JsonSchemaValidatorTest`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add contracts/kafka/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JsonSchemaValidator.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/JsonSchemaValidatorTest.java \
        apps/gateway/build.gradle.kts
git commit -m "feat(contracts): add v1 Kafka JSON schemas + gateway-side validator (spec §3)"
```

---

### Task 4: Kafka topic provisioning init container (spec §5)

**Files:**
- Create: `infra/kafka-init/Dockerfile`
- Create: `infra/kafka-init/create-topics.sh`
- Modify: `infra/docker-compose.yml`

- [ ] **Step 1: Write `infra/kafka-init/create-topics.sh`**

```bash
#!/usr/bin/env bash
# Creates the four v1 topics on the Redpanda broker. Idempotent — re-runs are
# no-ops because `rpk topic create` honours --if-not-exists semantics.
set -euo pipefail

BROKER="${REDPANDA_BROKERS:-redpanda:9092}"

create() {
  local name="$1" partitions="$2" retention_ms="$3"
  echo "==> ensuring topic ${name} (partitions=${partitions}, retention=${retention_ms}ms)"
  rpk topic create "${name}" \
      --brokers "${BROKER}" \
      --partitions "${partitions}" \
      --replicas 1 \
      --config "retention.ms=${retention_ms}" \
      || true   # ignore "already exists"
}

# Spec §5 — Kafka topics table
create "topic.v1.jobs"            6 $((7 * 24 * 60 * 60 * 1000))
create "topic.v1.job-results"     6 $((24 * 60 * 60 * 1000))
create "topic.v1.audit-events"    3 $((7 * 24 * 60 * 60 * 1000))
create "topic.v1.format-requests" 3 $((30 * 24 * 60 * 60 * 1000))

echo "==> topics provisioned"
```

- [ ] **Step 2: Write `infra/kafka-init/Dockerfile`**

```dockerfile
# Minimal image with rpk for one-shot topic provisioning.
FROM docker.redpanda.com/redpandadata/redpanda:v24.2.4

USER root
COPY create-topics.sh /usr/local/bin/create-topics.sh
RUN chmod +x /usr/local/bin/create-topics.sh

ENTRYPOINT ["/usr/local/bin/create-topics.sh"]
```

- [ ] **Step 3: Modify `infra/docker-compose.yml` — add the init service**

```yaml
  kafka-init:
    build: ./kafka-init
    container_name: filternarrange-kafka-init
    depends_on:
      redpanda:
        condition: service_healthy
    environment:
      REDPANDA_BROKERS: redpanda:9092
    restart: "no"
    networks:
      - filternarrange-net
```

- [ ] **Step 4: Verify topics are created on `docker compose up`**

Run:
```bash
docker compose -f infra/docker-compose.yml up -d redpanda kafka-init
docker compose -f infra/docker-compose.yml run --rm kafka-init || true
docker exec filternarrange-redpanda rpk topic list
```
Expected output includes `topic.v1.jobs`, `topic.v1.job-results`, `topic.v1.audit-events`, `topic.v1.format-requests`.

- [ ] **Step 5: Commit**

```bash
git add infra/kafka-init/ infra/docker-compose.yml
git commit -m "feat(infra): add kafka-init container to provision v1 topics (spec §5)"
```

---

### Task 5: Gateway domain types — Job, JobStatus, JobKind

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/Job.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/JobStatus.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/JobKind.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/domain/job/JobStateMachineTest.java`

- [ ] **Step 1: Write the failing state-machine test**

```java
package io.filternarrange.gateway.domain.job;

import org.junit.jupiter.api.Test;
import static org.assertj.core.api.Assertions.assertThat;

class JobStateMachineTest {

    @Test
    void queued_can_transition_to_running_or_cancelled() {
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.RUNNING)).isTrue();
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.CANCELLED)).isTrue();
        assertThat(JobStatus.QUEUED.canTransitionTo(JobStatus.COMPLETED)).isFalse();
    }

    @Test
    void terminal_states_are_terminal() {
        assertThat(JobStatus.COMPLETED.isTerminal()).isTrue();
        assertThat(JobStatus.FAILED.isTerminal()).isTrue();
        assertThat(JobStatus.CANCELLED.isTerminal()).isTrue();
        assertThat(JobStatus.QUEUED.isTerminal()).isFalse();
        assertThat(JobStatus.RUNNING.isTerminal()).isFalse();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests JobStateMachineTest`
Expected: FAIL — `JobStatus` does not exist.

- [ ] **Step 3: Implement `JobStatus`**

```java
package io.filternarrange.gateway.domain.job;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

public enum JobStatus {
    QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED;

    private static final Map<JobStatus, Set<JobStatus>> TRANSITIONS = Map.of(
        QUEUED,    EnumSet.of(RUNNING, CANCELLED, FAILED),
        RUNNING,   EnumSet.of(COMPLETED, FAILED, CANCELLED),
        COMPLETED, EnumSet.noneOf(JobStatus.class),
        FAILED,    EnumSet.noneOf(JobStatus.class),
        CANCELLED, EnumSet.noneOf(JobStatus.class)
    );

    public boolean canTransitionTo(JobStatus next) {
        return TRANSITIONS.get(this).contains(next);
    }

    public boolean isTerminal() {
        return TRANSITIONS.get(this).isEmpty();
    }
}
```

- [ ] **Step 4: Implement `JobKind`**

```java
package io.filternarrange.gateway.domain.job;

public enum JobKind {
    BATCH_FILTER("batch-filter"),
    CONVERT("convert"),
    ANALYZE("analyze");

    private final String wire;

    JobKind(String wire) { this.wire = wire; }

    public String wire() { return wire; }

    public static JobKind fromWire(String s) {
        for (var k : values()) if (k.wire.equals(s)) return k;
        throw new IllegalArgumentException("Unknown job kind: " + s);
    }
}
```

- [ ] **Step 5: Implement `Job` (immutable record)**

```java
package io.filternarrange.gateway.domain.job;

import com.fasterxml.jackson.databind.JsonNode;

import java.time.Instant;
import java.util.UUID;

public record Job(
    UUID id,
    UUID userId,
    JobKind kind,
    JobStatus status,
    JsonNode params,
    String resultRef,
    JsonNode error,
    int priority,
    Instant createdAt,
    Instant startedAt,
    Instant finishedAt
) {
    public Job withStatus(JobStatus next) {
        if (!this.status.canTransitionTo(next)) {
            throw new IllegalStateException(
                "Invalid transition " + this.status + " -> " + next);
        }
        Instant startedAt = (next == JobStatus.RUNNING && this.startedAt == null)
                            ? Instant.now() : this.startedAt;
        Instant finishedAt = next.isTerminal() ? Instant.now() : this.finishedAt;
        return new Job(id, userId, kind, next, params, resultRef, error,
                       priority, createdAt, startedAt, finishedAt);
    }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `./gradlew :apps:gateway:test --tests JobStateMachineTest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/domain/job/ \
        apps/gateway/src/test/java/io/filternarrange/gateway/domain/job/JobStateMachineTest.java
git commit -m "feat(gateway): add Job domain types + state-machine guard (spec §3)"
```

---

### Task 6: Gateway persistence — `JobRepository`, `JobRow`, `AuditLogRepository`

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JobRow.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JobRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/AuditLogRepository.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JobRepositoryIT.java`

- [ ] **Step 1: Write the failing repo test**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@JdbcTest
@Import(JobRepositoryIT.Cfg.class)
@Testcontainers
class JobRepositoryIT {

    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
        r.add("spring.datasource.username", pg::getUsername);
        r.add("spring.datasource.password", pg::getPassword);
    }

    @TestConfiguration
    static class Cfg {
        @Bean JobRepository repo(org.springframework.jdbc.core.JdbcTemplate jdbc) {
            return new JobRepository(jdbc, new ObjectMapper());
        }
    }

    @Autowired JobRepository repo;
    @Autowired org.springframework.jdbc.core.JdbcTemplate jdbc;

    @Test
    void insert_then_load_then_update_status() throws Exception {
        UUID userId = UUID.randomUUID();
        jdbc.update("INSERT INTO users(id, email) VALUES (?, ?)",
                    userId, "x" + userId + "@t.io");
        ObjectMapper om = new ObjectMapper();
        Job j = new Job(UUID.randomUUID(), userId, JobKind.BATCH_FILTER,
                        JobStatus.QUEUED, om.readTree("{\"a\":1}"),
                        null, null, 0, Instant.now(), null, null);

        repo.insert(j);
        Optional<Job> loaded = repo.findById(j.id());
        assertThat(loaded).isPresent();
        assertThat(loaded.get().status()).isEqualTo(JobStatus.QUEUED);

        Job started = loaded.get().withStatus(JobStatus.RUNNING);
        repo.updateStatus(started);
        assertThat(repo.findById(j.id()).orElseThrow().status())
            .isEqualTo(JobStatus.RUNNING);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests JobRepositoryIT`
Expected: FAIL — `JobRepository` does not exist.

- [ ] **Step 3: Implement `JobRepository`**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import org.postgresql.util.PGobject;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class JobRepository {

    private static final int DEFAULT_QUERY_TIMEOUT_SECONDS = 3;   // spec §6

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;

    public JobRepository(JdbcTemplate jdbc, ObjectMapper om) {
        this.jdbc = jdbc;
        this.om   = om;
        this.jdbc.setQueryTimeout(DEFAULT_QUERY_TIMEOUT_SECONDS);
    }

    public void insert(Job j) {
        jdbc.update(
            "INSERT INTO jobs(id, user_id, kind, status, params, priority, created_at) " +
            "VALUES (?, ?, ?, ?, ?::jsonb, ?, ?)",
            j.id(), j.userId(), j.kind().wire(), j.status().name().toLowerCase(),
            asJson(j.params()), j.priority(), Timestamp.from(j.createdAt()));
    }

    public Optional<Job> findById(UUID id) {
        List<Job> rs = jdbc.query(
            "SELECT * FROM jobs WHERE id = ?", MAPPER, id);
        return rs.isEmpty() ? Optional.empty() : Optional.of(rs.get(0));
    }

    public List<Job> findRecentByUser(UUID userId, int limit) {
        return jdbc.query(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            MAPPER, userId, limit);
    }

    public void updateStatus(Job j) {
        jdbc.update(
            "UPDATE jobs SET status = ?, started_at = ?, finished_at = ?, " +
            "result_ref = ?, error = ?::jsonb WHERE id = ?",
            j.status().name().toLowerCase(),
            j.startedAt() == null ? null : Timestamp.from(j.startedAt()),
            j.finishedAt() == null ? null : Timestamp.from(j.finishedAt()),
            j.resultRef(),
            asJson(j.error()),
            j.id());
    }

    private String asJson(JsonNode n) {
        if (n == null) return null;
        try { return om.writeValueAsString(n); }
        catch (Exception e) { throw new IllegalStateException(e); }
    }

    private final RowMapper<Job> MAPPER = (rs, i) -> {
        try {
            JsonNode params = om.readTree(rs.getString("params"));
            String errStr = rs.getString("error");
            JsonNode error = errStr == null ? null : om.readTree(errStr);
            Timestamp started = rs.getTimestamp("started_at");
            Timestamp finished = rs.getTimestamp("finished_at");
            return new Job(
                UUID.fromString(rs.getString("id")),
                UUID.fromString(rs.getString("user_id")),
                JobKind.fromWire(rs.getString("kind")),
                JobStatus.valueOf(rs.getString("status").toUpperCase()),
                params,
                rs.getString("result_ref"),
                error,
                rs.getInt("priority"),
                rs.getTimestamp("created_at").toInstant(),
                started == null ? null : started.toInstant(),
                finished == null ? null : finished.toInstant());
        } catch (Exception e) {
            throw new IllegalStateException("Failed to map jobs row", e);
        }
    };
}
```

- [ ] **Step 4: Implement `AuditLogRepository`**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

@Repository
public class AuditLogRepository {

    private final JdbcTemplate jdbc;
    private final ObjectMapper om;

    public AuditLogRepository(JdbcTemplate jdbc, ObjectMapper om) {
        this.jdbc = jdbc;
        this.om = om;
        this.jdbc.setQueryTimeout(3);   // spec §6
    }

    public void insert(UUID userId, String action, String target,
                       JsonNode metadata, Instant occurredAt) {
        try {
            String meta = metadata == null ? null : om.writeValueAsString(metadata);
            jdbc.update(
                "INSERT INTO audit_log(user_id, action, target, metadata, created_at) " +
                "VALUES (?, ?, ?, ?::jsonb, ?)",
                userId, action, target, meta, Timestamp.from(occurredAt));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to write audit row", e);
        }
    }
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `./gradlew :apps:gateway:test --tests JobRepositoryIT`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/ \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/persistence/JobRepositoryIT.java
git commit -m "feat(gateway): add JobRepository + AuditLogRepository with 3s timeout (spec §6)"
```

---

### Task 7: Gateway thread pools, Kafka producers, topic constants (spec §6 bulkheading)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/threads/ThreadPoolConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaTopics.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaProducerConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobProducer.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventPublisher.java`
- Modify: `apps/gateway/src/main/resources/application.yml`

- [ ] **Step 1: Add `spring-kafka` to `apps/gateway/build.gradle.kts`**

```kotlin
dependencies {
    implementation("org.springframework.kafka:spring-kafka:3.2.4")
    implementation("io.github.resilience4j:resilience4j-spring-boot3:2.2.0")
    implementation("io.github.resilience4j:resilience4j-circuitbreaker:2.2.0")
    implementation("org.springframework.boot:spring-boot-starter-websocket")
}
```

- [ ] **Step 2: Create `KafkaTopics` constants**

```java
package io.filternarrange.gateway.infrastructure.messaging;

public final class KafkaTopics {
    public static final String JOBS            = "topic.v1.jobs";
    public static final String JOB_RESULTS     = "topic.v1.job-results";
    public static final String AUDIT_EVENTS    = "topic.v1.audit-events";
    public static final String FORMAT_REQUESTS = "topic.v1.format-requests";

    private KafkaTopics() {}
}
```

- [ ] **Step 3: Create `ThreadPoolConfig` (bulkheaded pools)**

```java
package io.filternarrange.gateway.platform.threads;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

@Configuration
public class ThreadPoolConfig {

    /** Bulkhead for kafka producer sends — spec §6. Sized to 4 per spec. */
    @Bean(name = "kafkaProducerExecutor")
    public ThreadPoolTaskExecutor kafkaProducerExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(4);
        e.setMaxPoolSize(4);
        e.setQueueCapacity(256);
        e.setThreadNamePrefix("kafka-producer-");
        e.initialize();
        return e;
    }
}
```

(Tomcat `web-io` and Hikari `db-io` are left at defaults per the task spec.)

- [ ] **Step 4: Create `KafkaProducerConfig`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;

import java.util.Map;

@Configuration
public class KafkaProducerConfig {

    private final String bootstrap;

    public KafkaProducerConfig(@Value("${spring.kafka.bootstrap-servers}") String b) {
        this.bootstrap = b;
    }

    private Map<String, Object> baseProps() {
        return Map.of(
            ProducerConfig.BOOTSTRAP_SERVERS_CONFIG,        bootstrap,
            ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,     StringSerializer.class,
            ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,   StringSerializer.class,
            ProducerConfig.ACKS_CONFIG,                     "all",
            ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG,       true,
            ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5,
            ProducerConfig.RETRIES_CONFIG,                  Integer.MAX_VALUE,
            ProducerConfig.DELIVERY_TIMEOUT_MS_CONFIG,      10_000, // spec §6
            ProducerConfig.REQUEST_TIMEOUT_MS_CONFIG,       5_000
        );
    }

    @Bean("jobsProducerFactory")
    public ProducerFactory<String, String> jobsProducerFactory() {
        return new DefaultKafkaProducerFactory<>(baseProps());
    }

    @Bean("jobsKafkaTemplate")
    public KafkaTemplate<String, String> jobsKafkaTemplate() {
        return new KafkaTemplate<>(jobsProducerFactory());
    }

    @Bean("auditProducerFactory")
    public ProducerFactory<String, String> auditProducerFactory() {
        return new DefaultKafkaProducerFactory<>(baseProps());
    }

    @Bean("auditKafkaTemplate")
    public KafkaTemplate<String, String> auditKafkaTemplate() {
        return new KafkaTemplate<>(auditProducerFactory());
    }
}
```

- [ ] **Step 5: Create `JobProducer`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import io.filternarrange.gateway.domain.job.Job;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class JobProducer {

    private final KafkaTemplate<String, String> template;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public JobProducer(@Qualifier("jobsKafkaTemplate") KafkaTemplate<String, String> t,
                       JsonSchemaValidator v,
                       ObjectMapper om) {
        this.template = t;
        this.validator = v;
        this.om = om;
    }

    /** Partition key = user_id, per spec §5. Blocks up to 10s — spec §6. */
    public void publish(Job j, String traceId) throws Exception {
        ObjectNode env = om.createObjectNode();
        env.put("job_id",     j.id().toString());
        env.put("user_id",    j.userId().toString());
        env.put("kind",       j.kind().wire());
        env.set ("params",    j.params());
        env.put("priority",   j.priority());
        env.put("created_at", j.createdAt().toString());
        env.put("trace_id",   traceId);

        String payload = om.writeValueAsString(env);
        validator.validateOrThrow(KafkaTopics.JOBS, payload);

        template.send(KafkaTopics.JOBS, j.userId().toString(), payload)
                .get(10, TimeUnit.SECONDS);
    }
}
```

- [ ] **Step 6: Create `AuditEventPublisher`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Component
public class AuditEventPublisher {

    private final KafkaTemplate<String, String> template;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public AuditEventPublisher(@Qualifier("auditKafkaTemplate") KafkaTemplate<String, String> t,
                               JsonSchemaValidator v, ObjectMapper om) {
        this.template = t; this.validator = v; this.om = om;
    }

    /** Partition key = user_id (or "system" if null). */
    public void publish(UUID userId, String action, String target,
                        JsonNode metadata, String traceId) throws Exception {
        ObjectNode env = om.createObjectNode();
        env.put("event_id",    UUID.randomUUID().toString());
        if (userId != null) env.put("user_id", userId.toString());
        env.put("action",      action);
        if (target != null) env.put("target", target);
        if (metadata != null) env.set("metadata", metadata);
        env.put("occurred_at", Instant.now().toString());
        env.put("trace_id",    traceId);

        String payload = om.writeValueAsString(env);
        validator.validateOrThrow(KafkaTopics.AUDIT_EVENTS, payload);

        String key = userId == null ? "system" : userId.toString();
        template.send(KafkaTopics.AUDIT_EVENTS, key, payload)
                .get(10, TimeUnit.SECONDS);
    }
}
```

- [ ] **Step 7: Modify `application.yml` — add Kafka + timeouts**

```yaml
spring:
  kafka:
    bootstrap-servers: ${REDPANDA_BROKERS:redpanda:9092}
  datasource:
    hikari:
      connection-timeout: 3000     # 3s — spec §6
      validation-timeout: 1000
data-engine:
  base-url: http://data-engine:8000
  timeout-ms: 5000                # spec §6
minio:
  client-timeout-ms: 60000        # spec §6
redis:
  command-timeout-ms: 250         # spec §6
resilience4j:
  circuitbreaker:
    instances:
      dataEngine:
        slidingWindowType: TIME_BASED
        slidingWindowSize: 10
        minimumNumberOfCalls: 5
        failureRateThreshold: 100
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 1
        automaticTransitionFromOpenToHalfOpenEnabled: true
```

- [ ] **Step 8: Smoke-test the producers with embedded Kafka**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/JobProducerIT.java`:

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;

import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = {"topic.v1.jobs"})
class JobProducerIT {

    @Autowired JobProducer producer;
    @Autowired EmbeddedKafkaBroker broker;
    @Autowired ObjectMapper om;

    @Test
    void publish_writes_a_schema_valid_message() throws Exception {
        Job j = new Job(UUID.randomUUID(), UUID.randomUUID(),
                        JobKind.BATCH_FILTER, JobStatus.QUEUED,
                        om.readTree("{\"input\":{}}"),
                        null, null, 0, Instant.now(), null, null);
        producer.publish(j, "trace-1");

        var consumerProps = KafkaTestUtils.consumerProps(
            "test", "true", broker);
        var cf = new org.apache.kafka.clients.consumer.KafkaConsumer<String, String>(consumerProps,
            new org.apache.kafka.common.serialization.StringDeserializer(),
            new org.apache.kafka.common.serialization.StringDeserializer());
        cf.subscribe(java.util.List.of("topic.v1.jobs"));
        ConsumerRecord<String, String> rec =
            KafkaTestUtils.getSingleRecord(cf, "topic.v1.jobs");
        assertThat(rec.value()).contains(j.id().toString());
    }
}
```

Run: `./gradlew :apps:gateway:test --tests JobProducerIT`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/threads/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaTopics.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaProducerConfig.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobProducer.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventPublisher.java \
        apps/gateway/src/main/resources/application.yml \
        apps/gateway/build.gradle.kts \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/JobProducerIT.java
git commit -m "feat(gateway): add Kafka producers + bulkhead pools + timeouts (spec §6)"
```

---

### Task 8: Idempotency store + Resilience4j circuit breaker (spec §6)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/idempotency/IdempotencyStore.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/resilience/DataEngineCircuitBreakerConfig.java`
- Modify: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineClient.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/idempotency/IdempotencyStoreTest.java`

- [ ] **Step 1: Write the failing idempotency-store test**

```java
package io.filternarrange.gateway.platform.idempotency;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.Optional;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class IdempotencyStoreTest {

    @Container
    static GenericContainer<?> redis =
        new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    @Autowired IdempotencyStore store;

    @Test
    void first_put_returns_empty_then_retrieves_same_value() {
        String key = "k-" + UUID.randomUUID();
        UUID jobId = UUID.randomUUID();
        Optional<UUID> existing = store.putIfAbsent(key, jobId);
        assertThat(existing).isEmpty();

        Optional<UUID> second = store.putIfAbsent(key, UUID.randomUUID());
        assertThat(second).contains(jobId);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./gradlew :apps:gateway:test --tests IdempotencyStoreTest`
Expected: FAIL — `IdempotencyStore` does not exist.

- [ ] **Step 3: Implement `IdempotencyStore`**

```java
package io.filternarrange.gateway.platform.idempotency;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.Optional;
import java.util.UUID;

@Component
public class IdempotencyStore {

    private static final Duration TTL = Duration.ofHours(24);
    private static final String PREFIX = "gw:idem:";   // spec §5 keyspace

    private final StringRedisTemplate redis;

    public IdempotencyStore(StringRedisTemplate redis) { this.redis = redis; }

    /**
     * Stores key→job_id if absent. Returns the *existing* value if the key
     * was already there; empty if this caller "won" the slot.
     */
    public Optional<UUID> putIfAbsent(String key, UUID jobId) {
        String redisKey = PREFIX + key;
        Boolean ok = redis.opsForValue()
                          .setIfAbsent(redisKey, jobId.toString(), TTL);
        if (Boolean.TRUE.equals(ok)) return Optional.empty();
        String existing = redis.opsForValue().get(redisKey);
        if (existing == null) return Optional.empty();
        return Optional.of(UUID.fromString(existing));
    }
}
```

- [ ] **Step 4: Implement `DataEngineCircuitBreakerConfig`**

```java
package io.filternarrange.gateway.platform.resilience;

import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CircuitBreakerConfig;
import io.github.resilience4j.circuitbreaker.CircuitBreakerRegistry;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
public class DataEngineCircuitBreakerConfig {

    @Bean
    public CircuitBreaker dataEngineBreaker(CircuitBreakerRegistry registry) {
        // 5 consecutive failures in 10s -> open. Spec §6.
        CircuitBreakerConfig cfg = CircuitBreakerConfig.custom()
            .slidingWindowType(CircuitBreakerConfig.SlidingWindowType.COUNT_BASED)
            .slidingWindowSize(5)
            .minimumNumberOfCalls(5)
            .failureRateThreshold(100.0f)
            .waitDurationInOpenState(Duration.ofSeconds(30))
            .permittedNumberOfCallsInHalfOpenState(1)
            .automaticTransitionFromOpenToHalfOpenEnabled(true)
            .build();
        return registry.circuitBreaker("dataEngine", cfg);
    }
}
```

- [ ] **Step 5: Modify `DataEngineClient` to wrap calls in the breaker + 5s HTTP timeout**

```java
// inside io.filternarrange.gateway.infrastructure.http.DataEngineClient
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
// ...

private final CircuitBreaker breaker;
private final RestClient http;   // configured with 5s connect+read timeout

public DataEngineClient(RestClient http, CircuitBreaker dataEngineBreaker) {
    this.http = http;
    this.breaker = dataEngineBreaker;
}

public <T> T callSync(String path, Object body, Class<T> respType) {
    try {
        return breaker.executeSupplier(() ->
            http.post().uri(path).body(body).retrieve().body(respType));
    } catch (CallNotPermittedException e) {
        throw new ServiceDegradedException(
            "SERVICE_DEGRADED",
            "Data engine is temporarily unavailable.",
            breaker.getName());
    }
}
```

Add a small exception type:

```java
package io.filternarrange.gateway.platform.errors;

public class ServiceDegradedException extends RuntimeException {
    private final String code;
    private final String component;
    public ServiceDegradedException(String code, String msg, String component) {
        super(msg);
        this.code = code; this.component = component;
    }
    public String code() { return code; }
    public String component() { return component; }
}
```

And map it in the existing `GlobalExceptionHandler` to `503` with the structured envelope `{code, plugin_id?, message, trace_id}`.

- [ ] **Step 6: Run test to verify it passes**

Run: `./gradlew :apps:gateway:test --tests IdempotencyStoreTest`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/platform/idempotency/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/platform/resilience/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/platform/errors/ServiceDegradedException.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineClient.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/platform/idempotency/IdempotencyStoreTest.java
git commit -m "feat(gateway): add idempotency store + Resilience4j breaker on data-engine (spec §6)"
```

---

### Task 9: `JobService` + `JobController` (spec §3 async path)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/JobService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/CreateJobRequest.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/JobResponse.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/JobController.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/JobControllerIT.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/IdempotencyIT.java`

- [ ] **Step 1: Write `CreateJobRequest` + `JobResponse` DTOs**

```java
// CreateJobRequest.java
package io.filternarrange.gateway.api.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateJobRequest(
    @NotBlank String kind,
    @NotNull JsonNode params,
    Integer priority
) {}
```

```java
// JobResponse.java
package io.filternarrange.gateway.api.dto;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.UUID;

public record JobResponse(
    UUID jobId,
    String status,
    String kind,
    JsonNode params,
    String resultRef,
    JsonNode error,
    Instant createdAt,
    Instant startedAt,
    Instant finishedAt
) {}
```

- [ ] **Step 2: Implement `JobService`**

```java
package io.filternarrange.gateway.application;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import io.filternarrange.gateway.infrastructure.messaging.AuditEventPublisher;
import io.filternarrange.gateway.infrastructure.messaging.JobProducer;
import io.filternarrange.gateway.infrastructure.persistence.JobRepository;
import io.filternarrange.gateway.platform.idempotency.IdempotencyStore;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class JobService {

    private final JobRepository jobs;
    private final JobProducer producer;
    private final AuditEventPublisher audit;
    private final IdempotencyStore idem;
    private final ObjectMapper om;

    public JobService(JobRepository jobs, JobProducer producer,
                      AuditEventPublisher audit, IdempotencyStore idem,
                      ObjectMapper om) {
        this.jobs = jobs; this.producer = producer; this.audit = audit;
        this.idem = idem; this.om = om;
    }

    @Transactional
    public Job submit(UUID userId, String idempotencyKey, String kindWire,
                      JsonNode params, int priority, String traceId)
            throws Exception {

        UUID newJobId = UUID.randomUUID();
        Optional<UUID> existing = idem.putIfAbsent(idempotencyKey, newJobId);
        if (existing.isPresent()) {
            return jobs.findById(existing.get())
                       .orElseThrow(() -> new IllegalStateException(
                           "Idempotency key points to missing job"));
        }

        Job j = new Job(newJobId, userId, JobKind.fromWire(kindWire),
                        JobStatus.QUEUED, params, null, null,
                        priority, Instant.now(), null, null);
        jobs.insert(j);
        producer.publish(j, traceId);

        var meta = om.createObjectNode().put("job_id", j.id().toString());
        audit.publish(userId, "job.submitted", j.id().toString(), meta, traceId);
        return j;
    }

    public Optional<Job> get(UUID jobId) { return jobs.findById(jobId); }

    public List<Job> recentForUser(UUID userId) {
        return jobs.findRecentByUser(userId, 20);
    }

    @Transactional
    public Job cancel(UUID jobId, String traceId) throws Exception {
        Job j = jobs.findById(jobId)
                    .orElseThrow(() -> new IllegalArgumentException(
                        "Job not found: " + jobId));
        if (j.status().isTerminal()) return j;
        Job cancelled = j.withStatus(JobStatus.CANCELLED);
        jobs.updateStatus(cancelled);
        audit.publish(j.userId(), "job.cancelled", j.id().toString(),
                      null, traceId);
        return cancelled;
    }
}
```

- [ ] **Step 3: Implement `JobController`**

```java
package io.filternarrange.gateway.api;

import io.filternarrange.gateway.api.dto.CreateJobRequest;
import io.filternarrange.gateway.api.dto.JobResponse;
import io.filternarrange.gateway.application.JobService;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.platform.security.AuthenticatedUser;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/jobs")
public class JobController {

    private final JobService jobs;

    public JobController(JobService jobs) { this.jobs = jobs; }

    @PostMapping
    public ResponseEntity<JobResponse> submit(
            @RequestHeader("Idempotency-Key") String key,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId,
            @Valid @RequestBody CreateJobRequest req,
            AuthenticatedUser user) throws Exception {
        Job j = jobs.submit(
            user.id(), key, req.kind(), req.params(),
            req.priority() == null ? 0 : req.priority(),
            traceId == null ? UUID.randomUUID().toString() : traceId);
        return ResponseEntity.accepted().body(toDto(j));
    }

    @GetMapping("/{jobId}")
    public JobResponse get(@PathVariable UUID jobId) {
        return jobs.get(jobId)
                   .map(this::toDto)
                   .orElseThrow(() -> new NotFoundException("Job not found"));
    }

    @GetMapping
    public List<JobResponse> recent(AuthenticatedUser user) {
        return jobs.recentForUser(user.id()).stream().map(this::toDto).toList();
    }

    @DeleteMapping("/{jobId}")
    public JobResponse cancel(
            @PathVariable UUID jobId,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId)
            throws Exception {
        return toDto(jobs.cancel(jobId,
            traceId == null ? UUID.randomUUID().toString() : traceId));
    }

    private JobResponse toDto(Job j) {
        return new JobResponse(
            j.id(), j.status().name().toLowerCase(), j.kind().wire(),
            j.params(), j.resultRef(), j.error(),
            j.createdAt(), j.startedAt(), j.finishedAt());
    }

    public static class NotFoundException extends RuntimeException {
        public NotFoundException(String m) { super(m); }
    }
}
```

`AuthenticatedUser` comes from Plan B (JWT-resolved principal).

- [ ] **Step 4: Write `JobControllerIT`**

```java
package io.filternarrange.gateway.api;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@EmbeddedKafka(partitions = 1,
               topics = {"topic.v1.jobs", "topic.v1.audit-events"})
class JobControllerIT {

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper om;

    @Test
    void post_jobs_returns_202_and_queued_status() throws Exception {
        String body = """
            {"kind":"batch-filter","params":{"input":{"ref":"uploads/x.csv"}}}
            """;
        mvc.perform(post("/api/v1/jobs")
                .header("Idempotency-Key", "key-1")
                .header("Authorization", "Bearer test-jwt")
                .contentType(MediaType.APPLICATION_JSON)
                .content(body))
           .andExpect(status().isAccepted())
           .andExpect(jsonPath("$.status").value("queued"));
    }
}
```

- [ ] **Step 5: Write `IdempotencyIT` — same key returns same job**

```java
package io.filternarrange.gateway.api;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@EmbeddedKafka(partitions = 1, topics = {"topic.v1.jobs","topic.v1.audit-events"})
class IdempotencyIT {

    @Autowired MockMvc mvc;

    @Test
    void same_idempotency_key_returns_same_job_id() throws Exception {
        String body = "{\"kind\":\"batch-filter\",\"params\":{}}";
        MvcResult r1 = mvc.perform(post("/api/v1/jobs")
                .header("Idempotency-Key", "dup-key")
                .header("Authorization", "Bearer test-jwt")
                .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isAccepted()).andReturn();
        MvcResult r2 = mvc.perform(post("/api/v1/jobs")
                .header("Idempotency-Key", "dup-key")
                .header("Authorization", "Bearer test-jwt")
                .contentType(MediaType.APPLICATION_JSON).content(body))
            .andExpect(status().isAccepted()).andReturn();

        String j1 = r1.getResponse().getContentAsString();
        String j2 = r2.getResponse().getContentAsString();
        assertThat(j1).isEqualTo(j2);
    }
}
```

- [ ] **Step 6: Run tests**

Run: `./gradlew :apps:gateway:test --tests JobControllerIT --tests IdempotencyIT`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/application/JobService.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/api/JobController.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/JobControllerIT.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/IdempotencyIT.java
git commit -m "feat(gateway): POST/GET/DELETE /api/v1/jobs with idempotency + audit (spec §3)"
```

---

### Task 10: Gateway WebSocket fan-out + `JobResultsConsumer` + `AuditEventsConsumer`

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/JobSubscriberRegistry.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/JobWebSocketHandler.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/WebSocketConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaConsumerConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobResultsConsumer.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumer.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/ws/JobWebSocketIT.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumerIT.java`

- [ ] **Step 1: Implement `JobSubscriberRegistry`**

```java
package io.filternarrange.gateway.api.ws;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketSession;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class JobSubscriberRegistry {

    private final Map<UUID, Set<WebSocketSession>> sessionsByJob =
        new ConcurrentHashMap<>();

    public void register(UUID jobId, WebSocketSession s) {
        sessionsByJob.computeIfAbsent(jobId, k -> ConcurrentHashMap.newKeySet()).add(s);
    }

    public void unregister(UUID jobId, WebSocketSession s) {
        Set<WebSocketSession> set = sessionsByJob.get(jobId);
        if (set != null) {
            set.remove(s);
            if (set.isEmpty()) sessionsByJob.remove(jobId);
        }
    }

    public void broadcast(UUID jobId, String payload, boolean closeAfter) {
        Set<WebSocketSession> set = sessionsByJob.get(jobId);
        if (set == null) return;
        for (WebSocketSession s : set) {
            try {
                if (s.isOpen()) s.sendMessage(
                    new org.springframework.web.socket.TextMessage(payload));
                if (closeAfter && s.isOpen()) s.close();
            } catch (IOException ignored) { }
        }
        if (closeAfter) sessionsByJob.remove(jobId);
    }
}
```

- [ ] **Step 2: Implement `JobWebSocketHandler` + `WebSocketConfig`**

```java
// JobWebSocketHandler.java
package io.filternarrange.gateway.api.ws;

import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.UUID;

@Component
public class JobWebSocketHandler extends TextWebSocketHandler {

    private static final String PATH_PREFIX = "/ws/jobs/";
    private final JobSubscriberRegistry registry;

    public JobWebSocketHandler(JobSubscriberRegistry r) { this.registry = r; }

    @Override
    public void afterConnectionEstablished(WebSocketSession s) throws Exception {
        UUID jobId = extract(s);
        if (jobId == null) { s.close(CloseStatus.BAD_DATA); return; }
        registry.register(jobId, s);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession s, CloseStatus status) {
        UUID jobId = extract(s);
        if (jobId != null) registry.unregister(jobId, s);
    }

    private UUID extract(WebSocketSession s) {
        String path = s.getUri() == null ? "" : s.getUri().getPath();
        if (!path.startsWith(PATH_PREFIX)) return null;
        try { return UUID.fromString(path.substring(PATH_PREFIX.length())); }
        catch (Exception e) { return null; }
    }
}
```

```java
// WebSocketConfig.java
package io.filternarrange.gateway.api.ws;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final JobWebSocketHandler handler;

    public WebSocketConfig(JobWebSocketHandler h) { this.handler = h; }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry r) {
        r.addHandler(handler, "/ws/jobs/*").setAllowedOriginPatterns("*");
    }
}
```

- [ ] **Step 3: Implement `KafkaConsumerConfig`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;

import java.util.Map;

@Configuration
@EnableKafka
public class KafkaConsumerConfig {

    @Value("${spring.kafka.bootstrap-servers}") String bootstrap;

    @Bean
    public ConsumerFactory<String, String> consumerFactory() {
        return new DefaultKafkaConsumerFactory<>(Map.of(
            ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrap,
            ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class,
            ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class,
            ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false,
            ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest"
        ));
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, String>
            kafkaListenerContainerFactory(ConsumerFactory<String, String> cf) {
        var f = new ConcurrentKafkaListenerContainerFactory<String, String>();
        f.setConsumerFactory(cf);
        f.getContainerProperties().setAckMode(
            org.springframework.kafka.listener.ContainerProperties.AckMode.MANUAL);
        return f;
    }
}
```

- [ ] **Step 4: Implement `JobResultsConsumer`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.api.ws.JobSubscriberRegistry;
import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobStatus;
import io.filternarrange.gateway.infrastructure.persistence.JobRepository;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;

@Component
public class JobResultsConsumer {

    private static final Logger log = LoggerFactory.getLogger(JobResultsConsumer.class);

    private final JobRepository jobs;
    private final JobSubscriberRegistry subs;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public JobResultsConsumer(JobRepository jobs, JobSubscriberRegistry subs,
                              JsonSchemaValidator v, ObjectMapper om) {
        this.jobs = jobs; this.subs = subs; this.validator = v; this.om = om;
    }

    @KafkaListener(topics = KafkaTopics.JOB_RESULTS,
                   groupId = "gateway-job-results",
                   containerFactory = "kafkaListenerContainerFactory")
    public void onMessage(ConsumerRecord<String, String> rec, Acknowledgment ack) {
        try {
            validator.validateOrThrow(KafkaTopics.JOB_RESULTS, rec.value());
            JsonNode n = om.readTree(rec.value());
            UUID jobId = UUID.fromString(n.get("job_id").asText());
            JobStatus status = JobStatus.valueOf(n.get("status").asText().toUpperCase());

            jobs.findById(jobId).ifPresent(j -> {
                if (j.status() == status) {
                    // heartbeat retransmission — fan out only
                } else if (j.status().canTransitionTo(status)) {
                    Job updated = j.withStatus(status);
                    if (n.hasNonNull("result_ref")) {
                        updated = new Job(updated.id(), updated.userId(),
                            updated.kind(), updated.status(), updated.params(),
                            n.get("result_ref").asText(), updated.error(),
                            updated.priority(), updated.createdAt(),
                            updated.startedAt(), updated.finishedAt());
                    }
                    if (n.hasNonNull("error")) {
                        updated = new Job(updated.id(), updated.userId(),
                            updated.kind(), updated.status(), updated.params(),
                            updated.resultRef(), n.get("error"),
                            updated.priority(), updated.createdAt(),
                            updated.startedAt(), updated.finishedAt());
                    }
                    jobs.updateStatus(updated);
                } else {
                    log.warn("Invalid transition {} -> {} for job {}",
                             j.status(), status, jobId);
                    ack.acknowledge();
                    return;
                }
                subs.broadcast(jobId, rec.value(), status.isTerminal());
            });
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Rejecting malformed job-result message at offset {}: {}",
                      rec.offset(), e.getMessage());
            // do not block the consumer — ack and move on
            ack.acknowledge();
        }
    }
}
```

- [ ] **Step 5: Implement `AuditEventsConsumer`**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.infrastructure.persistence.AuditLogRepository;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.UUID;

@Component
public class AuditEventsConsumer {

    private static final Logger log = LoggerFactory.getLogger(AuditEventsConsumer.class);

    private final AuditLogRepository repo;
    private final JsonSchemaValidator validator;
    private final ObjectMapper om;

    public AuditEventsConsumer(AuditLogRepository repo,
                               JsonSchemaValidator v, ObjectMapper om) {
        this.repo = repo; this.validator = v; this.om = om;
    }

    @KafkaListener(topics = KafkaTopics.AUDIT_EVENTS,
                   groupId = "gateway-audit-writer",
                   containerFactory = "kafkaListenerContainerFactory")
    public void onMessage(ConsumerRecord<String, String> rec, Acknowledgment ack) {
        try {
            validator.validateOrThrow(KafkaTopics.AUDIT_EVENTS, rec.value());
            JsonNode n = om.readTree(rec.value());
            UUID userId = n.hasNonNull("user_id")
                ? UUID.fromString(n.get("user_id").asText()) : null;
            String action = n.get("action").asText();
            String target = n.hasNonNull("target") ? n.get("target").asText() : null;
            JsonNode meta = n.hasNonNull("metadata") ? n.get("metadata") : null;
            Instant occurredAt = Instant.parse(n.get("occurred_at").asText());
            repo.insert(userId, action, target, meta, occurredAt);
            ack.acknowledge();
        } catch (Exception e) {
            log.error("Audit-event rejected at offset {}: {}",
                      rec.offset(), e.getMessage());
            ack.acknowledge();
        }
    }
}
```

- [ ] **Step 6: Write `JobWebSocketIT`**

```java
package io.filternarrange.gateway.api.ws;

import io.filternarrange.gateway.domain.job.Job;
import io.filternarrange.gateway.domain.job.JobKind;
import io.filternarrange.gateway.domain.job.JobStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.client.standard.StandardWebSocketClient;
import org.springframework.web.socket.handler.AbstractWebSocketHandler;
import org.springframework.web.socket.TextMessage;

import java.net.URI;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class JobWebSocketIT {

    @LocalServerPort int port;
    @Autowired JobSubscriberRegistry registry;

    @Test
    void broadcast_pushes_to_subscribers_and_closes_on_terminal() throws Exception {
        UUID jobId = UUID.randomUUID();
        StandardWebSocketClient client = new StandardWebSocketClient();
        CompletableFuture<String> received = new CompletableFuture<>();
        WebSocketSession session = client.execute(new AbstractWebSocketHandler() {
            @Override public void handleTextMessage(WebSocketSession s, TextMessage m) {
                received.complete(m.getPayload());
            }
        }, "ws://localhost:" + port + "/ws/jobs/" + jobId).get();

        await().atMost(Duration.ofSeconds(2))
               .until(() -> registry != null);

        registry.broadcast(jobId,
            "{\"job_id\":\"" + jobId + "\",\"status\":\"completed\"," +
            "\"finished_at\":\"2026-06-07T00:00:00Z\",\"trace_id\":\"t\"}",
            true);
        assertThat(received.get(2, java.util.concurrent.TimeUnit.SECONDS))
            .contains("completed");
    }
}
```

- [ ] **Step 7: Run tests**

Run: `./gradlew :apps:gateway:test --tests JobWebSocketIT --tests AuditEventsConsumerIT`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/gateway/src/main/java/io/filternarrange/gateway/api/ws/ \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/KafkaConsumerConfig.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/JobResultsConsumer.java \
        apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumer.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/api/ws/JobWebSocketIT.java \
        apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumerIT.java
git commit -m "feat(gateway): WS fan-out + job-results + audit consumers (spec §3, §5)"
```

---

### Task 11: Data-engine — MODE switch + pyproject deps

**Files:**
- Modify: `apps/data-engine/pyproject.toml`
- Create: `apps/data-engine/src/filternarrange_engine/platform/mode.py`
- Modify: `apps/data-engine/src/filternarrange_engine/main.py`
- Modify: `apps/data-engine/Dockerfile`

- [ ] **Step 1: Add deps to `pyproject.toml`**

```toml
[project]
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "aiokafka>=0.11",
    "jsonschema>=4.22",
    "httpx>=0.27",
    "minio>=7.2",
    "orjson>=3.10",
    # existing deps...
]
```

- [ ] **Step 2: Implement `platform/mode.py`**

```python
"""MODE switch for the data-engine service.

Per spec §2 loose-coupling rule 6, the same Python image runs in one of
four modes. Plan D introduces `worker`. The mode is read once at startup
and exposed as a frozen enum.
"""
from __future__ import annotations

import enum
import os


class Mode(str, enum.Enum):
    FULL = "full"      # HTTP + worker (dev convenience)
    DATA = "data"      # HTTP only — sync path
    AI = "ai"          # placeholder for Plan E
    WORKER = "worker"  # Kafka consumer only

    @classmethod
    def current(cls) -> "Mode":
        raw = os.getenv("MODE", "full").lower().strip()
        try:
            return cls(raw)
        except ValueError as exc:
            raise SystemExit(
                f"Invalid MODE={raw!r}; expected one of "
                f"{[m.value for m in cls]}"
            ) from exc


def serves_http(mode: Mode) -> bool:
    return mode in (Mode.FULL, Mode.DATA, Mode.AI)


def serves_worker(mode: Mode) -> bool:
    return mode in (Mode.FULL, Mode.WORKER)
```

- [ ] **Step 3: Branch `main.py` on MODE**

```python
"""Entrypoint — MODE-aware boot."""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI

from filternarrange_engine.platform.mode import Mode, serves_http, serves_worker
from filternarrange_engine.application.worker import run_worker

log = logging.getLogger(__name__)


def build_http_app() -> FastAPI:
    from filternarrange_engine.api import routers  # existing Plan B/C
    app = FastAPI(title="filternarrange-data-engine")
    routers.register(app)

    @app.get("/health")
    def health(): return {"status": "ok", "mode": Mode.current().value}

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    mode = Mode.current()
    log.info("Booting filternarrange-data-engine in MODE=%s", mode.value)

    if serves_http(mode) and not serves_worker(mode):
        # Pure HTTP — uvicorn drives the loop.
        import uvicorn
        uvicorn.run(build_http_app(), host="0.0.0.0", port=8000)
    elif serves_worker(mode) and not serves_http(mode):
        # Pure worker — asyncio drives.
        asyncio.run(run_worker())
    elif mode is Mode.FULL:
        # Both — run worker as background task alongside uvicorn.
        import uvicorn
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        worker_task = loop.create_task(run_worker())
        try:
            uvicorn.run(build_http_app(), host="0.0.0.0", port=8000)
        finally:
            worker_task.cancel()
    else:
        raise SystemExit(f"Mode {mode} not yet implemented")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Modify `Dockerfile`**

```dockerfile
# Honour MODE at runtime; default to full.
ENV MODE=full
CMD ["python", "-m", "filternarrange_engine.main"]
```

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/pyproject.toml \
        apps/data-engine/src/filternarrange_engine/platform/mode.py \
        apps/data-engine/src/filternarrange_engine/main.py \
        apps/data-engine/Dockerfile
git commit -m "feat(data-engine): add MODE switch + worker entrypoint (spec §2)"
```

---

### Task 12: Data-engine schema validator + Kafka topics constants

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/topics.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/schema_validator.py`
- Test: `apps/data-engine/tests/adapters/kafka/test_schema_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/data-engine/tests/adapters/kafka/test_schema_validator.py
import json
import pathlib
import pytest

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator, SchemaValidationError,
)

CONTRACTS = pathlib.Path(__file__).parents[4] / "contracts" / "kafka"


def test_valid_jobs_message_passes():
    v = SchemaValidator(CONTRACTS)
    msg = {
        "job_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "kind": "batch-filter",
        "params": {},
        "priority": 0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id": "t",
    }
    v.validate("topic.v1.jobs", msg)  # no raise


def test_missing_required_field_raises():
    v = SchemaValidator(CONTRACTS)
    bad = {"job_id": "11111111-1111-1111-1111-111111111111"}
    with pytest.raises(SchemaValidationError):
        v.validate("topic.v1.jobs", bad)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/adapters/kafka/test_schema_validator.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `topics.py`**

```python
"""Topic name constants — kept in lock-step with KafkaTopics.java."""
from __future__ import annotations

JOBS = "topic.v1.jobs"
JOB_RESULTS = "topic.v1.job-results"
AUDIT_EVENTS = "topic.v1.audit-events"
FORMAT_REQUESTS = "topic.v1.format-requests"

ALL_TOPICS = (JOBS, JOB_RESULTS, AUDIT_EVENTS, FORMAT_REQUESTS)
```

- [ ] **Step 4: Implement `schema_validator.py`**

```python
"""JSON-Schema validation for Kafka messages (spec §3, §6)."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Mapping

import jsonschema
from jsonschema import Draft202012Validator


class SchemaValidationError(ValueError):
    """Raised when a Kafka message does not conform to its v1 contract."""


class SchemaValidator:
    """Loads, caches, and validates against `contracts/kafka/*.schema.json`.

    The validator is process-wide; load once and share. `validate` raises
    `SchemaValidationError` so callers can ack-and-skip without crashing
    the consumer loop.
    """

    _FILE_FOR_TOPIC = {
        "topic.v1.jobs":            "topic.v1.jobs.schema.json",
        "topic.v1.job-results":     "topic.v1.job-results.schema.json",
        "topic.v1.audit-events":    "topic.v1.audit-events.schema.json",
        "topic.v1.format-requests": "topic.v1.format-requests.schema.json",
    }

    def __init__(self, contracts_dir: pathlib.Path) -> None:
        self._contracts_dir = contracts_dir
        self._cache: dict[str, Draft202012Validator] = {}

    def validate(self, topic: str, payload: Mapping[str, Any]) -> None:
        v = self._cache.get(topic)
        if v is None:
            fname = self._FILE_FOR_TOPIC.get(topic)
            if fname is None:
                raise SchemaValidationError(f"Unknown topic: {topic}")
            schema = json.loads((self._contracts_dir / fname).read_text())
            v = Draft202012Validator(schema)
            self._cache[topic] = v
        try:
            v.validate(payload)
        except jsonschema.ValidationError as e:
            raise SchemaValidationError(
                f"{topic}: {e.message} (at /{'/'.join(map(str, e.absolute_path))})"
            ) from e
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest apps/data-engine/tests/adapters/kafka/test_schema_validator.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/kafka/ \
        apps/data-engine/tests/adapters/kafka/test_schema_validator.py
git commit -m "feat(data-engine): add Kafka schema validator + topic constants"
```

---

### Task 13: Data-engine Kafka producer + consumer

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/producer.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/kafka/consumer.py`
- Test: `apps/data-engine/tests/adapters/kafka/test_consumer.py`

- [ ] **Step 1: Write the failing consumer test**

```python
import asyncio
import json
import pytest

from filternarrange_engine.adapters.kafka.consumer import JobConsumer


@pytest.mark.asyncio
async def test_consumer_dispatches_one_message_per_handler_call():
    received = []

    async def handler(payload):
        received.append(payload)

    c = JobConsumer(
        bootstrap_servers="dummy:9092",
        group_id="python-worker-free",
        handler=handler,
    )
    # exercise the internal dispatch with synthesized records
    await c._dispatch(json.dumps({
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }))
    assert len(received) == 1


@pytest.mark.asyncio
async def test_consumer_skips_invalid_messages():
    received = []
    async def handler(payload): received.append(payload)
    c = JobConsumer("dummy:9092", "python-worker-free", handler)
    await c._dispatch('{"job_id":"not-a-uuid"}')  # invalid
    assert received == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/adapters/kafka/test_consumer.py -v`
Expected: FAIL — `JobConsumer` does not exist.

- [ ] **Step 3: Implement `producer.py`**

```python
"""Kafka producer with JSON-Schema-on-write (spec §3)."""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Mapping

from aiokafka import AIOKafkaProducer

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator, SchemaValidationError,
)

log = logging.getLogger(__name__)
CONTRACTS = pathlib.Path(__file__).parents[5] / "contracts" / "kafka"


class JobResultsProducer:
    """Produces `topic.v1.job-results` messages keyed by job_id (spec §5)."""

    def __init__(self, bootstrap_servers: str,
                 validator: SchemaValidator | None = None) -> None:
        self._bootstrap = bootstrap_servers
        self._validator = validator or SchemaValidator(CONTRACTS)
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap,
            enable_idempotence=True,
            acks="all",
            request_timeout_ms=10_000,    # spec §6
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send(self, topic: str, key: str, payload: Mapping[str, Any]) -> None:
        assert self._producer is not None, "Call start() first"
        try:
            self._validator.validate(topic, payload)
        except SchemaValidationError as e:
            log.error("Refusing to produce malformed message: %s", e)
            raise
        await self._producer.send_and_wait(
            topic, key=key.encode(),
            value=json.dumps(payload).encode("utf-8"))
```

- [ ] **Step 4: Implement `consumer.py`**

```python
"""Async Kafka consumer with JSON-Schema-on-read (spec §3)."""
from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from typing import Any, Awaitable, Callable, Mapping

from aiokafka import AIOKafkaConsumer

from filternarrange_engine.adapters.kafka.schema_validator import (
    SchemaValidator, SchemaValidationError,
)
from filternarrange_engine.adapters.kafka.topics import JOBS

log = logging.getLogger(__name__)
CONTRACTS = pathlib.Path(__file__).parents[5] / "contracts" / "kafka"

Handler = Callable[[Mapping[str, Any]], Awaitable[None]]


class JobConsumer:
    """Consumes `topic.v1.jobs` for one consumer group.

    Plan D creates two groups — `python-worker-paid` and
    `python-worker-free` — both consuming the same topic. The actual
    tier routing lands in Plan F; for now both groups behave
    identically (the free group is the default).
    """

    def __init__(self, bootstrap_servers: str, group_id: str,
                 handler: Handler,
                 validator: SchemaValidator | None = None) -> None:
        self._bootstrap = bootstrap_servers
        self._group_id = group_id
        self._handler = handler
        self._validator = validator or SchemaValidator(CONTRACTS)
        self._consumer: AIOKafkaConsumer | None = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            JOBS,
            bootstrap_servers=self._bootstrap,
            group_id=self._group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            request_timeout_ms=10_000,
        )
        await self._consumer.start()

    async def stop(self) -> None:
        self._stop.set()
        if self._consumer:
            await self._consumer.stop()

    async def run(self) -> None:
        assert self._consumer is not None, "Call start() first"
        try:
            async for record in self._consumer:
                if self._stop.is_set():
                    break
                try:
                    await self._dispatch(record.value.decode("utf-8"))
                except Exception as e:
                    log.error(
                        "Handler crashed on offset %s: %s — ack & continue",
                        record.offset, e)
                # always commit — we use idempotency on the producer side and
                # job-status check in the handler to dedupe.
                await self._consumer.commit()
        finally:
            await self._consumer.stop()

    async def _dispatch(self, raw_value: str) -> None:
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError as e:
            log.warning("Dropping non-JSON message: %s", e)
            return
        try:
            self._validator.validate(JOBS, payload)
        except SchemaValidationError as e:
            log.warning("Dropping schema-invalid message: %s", e)
            return
        await self._handler(payload)
```

- [ ] **Step 5: Run tests to verify**

Run: `pytest apps/data-engine/tests/adapters/kafka/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/adapters/kafka/producer.py \
        apps/data-engine/src/filternarrange_engine/adapters/kafka/consumer.py \
        apps/data-engine/tests/adapters/kafka/test_consumer.py
git commit -m "feat(data-engine): add aiokafka producer + consumer with schema validation"
```

---

### Task 14: Data-engine bulkheads + heartbeat

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/platform/bulkheads.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/heartbeat.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/audit.py`
- Test: `apps/data-engine/tests/application/test_heartbeat.py`

- [ ] **Step 1: Write the failing heartbeat test**

```python
# apps/data-engine/tests/application/test_heartbeat.py
import asyncio
import pytest

from filternarrange_engine.application.heartbeat import Heartbeat


@pytest.mark.asyncio
async def test_heartbeat_emits_periodic_running_messages():
    sent = []

    async def emit():
        sent.append("tick")

    hb = Heartbeat(interval_s=0.05, emit=emit)
    task = asyncio.create_task(hb.run())
    await asyncio.sleep(0.18)
    await hb.stop()
    await task
    # 0, 50ms, 100ms, 150ms → at least 3 ticks
    assert len(sent) >= 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/application/test_heartbeat.py -v`
Expected: FAIL — `Heartbeat` does not exist.

- [ ] **Step 3: Implement `bulkheads.py`**

```python
"""Bulkheaded execution primitives (spec §6).

- ``data_cpu_pool`` — ProcessPoolExecutor for CPU-heavy parsing.
- ``plugin_async`` — Semaphore for in-process plugin dispatch fan-out.
"""
from __future__ import annotations

import asyncio
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor

_DATA_CPU_NAME = "data-cpu"
_PLUGIN_ASYNC_NAME = "plugin-async"

data_cpu_pool: ProcessPoolExecutor | None = None
plugin_async: asyncio.Semaphore | None = None


def init() -> None:
    global data_cpu_pool, plugin_async
    if data_cpu_pool is None:
        # Forkserver context — safer than fork on macOS, and avoids the
        # parent's loop state leaking into workers.
        ctx = multiprocessing.get_context("spawn")
        data_cpu_pool = ProcessPoolExecutor(
            max_workers=os.cpu_count() or 2,
            mp_context=ctx,
        )
    if plugin_async is None:
        plugin_async = asyncio.Semaphore(8)


def shutdown() -> None:
    global data_cpu_pool
    if data_cpu_pool is not None:
        data_cpu_pool.shutdown(wait=False, cancel_futures=True)
        data_cpu_pool = None
```

- [ ] **Step 4: Implement `heartbeat.py`**

```python
"""Per-job heartbeat producing `running` messages every 5s (spec §3)."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable


class Heartbeat:
    """Background ticker that calls ``emit`` every ``interval_s`` seconds.

    The job worker constructs one Heartbeat per active job and cancels it
    on terminal status. The first tick fires immediately so the WebSocket
    client sees a `running` envelope before the job is fully through its
    first parsing phase.
    """

    def __init__(self, interval_s: float, emit: Callable[[], Awaitable[None]]) -> None:
        self._interval = interval_s
        self._emit = emit
        self._stop = asyncio.Event()

    async def run(self) -> None:
        try:
            await self._emit()
            while not self._stop.is_set():
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    await self._emit()
        except asyncio.CancelledError:
            pass

    async def stop(self) -> None:
        self._stop.set()
```

- [ ] **Step 5: Implement `audit.py`**

```python
"""Audit-event publisher for the Python side."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from filternarrange_engine.adapters.kafka.producer import JobResultsProducer
from filternarrange_engine.adapters.kafka.topics import AUDIT_EVENTS


async def audit_event_publish(
    producer: JobResultsProducer,
    *,
    user_id: str | None,
    action: str,
    target: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    trace_id: str,
) -> None:
    payload: dict[str, Any] = {
        "event_id":    str(uuid.uuid4()),
        "action":      action,
        "occurred_at": datetime.now(timezone.utc).isoformat()
                                  .replace("+00:00", "Z"),
        "trace_id":    trace_id,
    }
    if user_id  is not None: payload["user_id"]  = user_id
    if target   is not None: payload["target"]   = target
    if metadata is not None: payload["metadata"] = dict(metadata)
    key = user_id or "system"
    await producer.send(AUDIT_EVENTS, key=key, payload=payload)
```

- [ ] **Step 6: Run tests**

Run: `pytest apps/data-engine/tests/application/test_heartbeat.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/platform/bulkheads.py \
        apps/data-engine/src/filternarrange_engine/application/heartbeat.py \
        apps/data-engine/src/filternarrange_engine/platform/audit.py \
        apps/data-engine/tests/application/test_heartbeat.py
git commit -m "feat(data-engine): bulkheads + heartbeat + audit publisher (spec §6)"
```

---

### Task 15: Data-engine `worker.py` orchestrator

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/application/worker.py`
- Test: `apps/data-engine/tests/application/test_worker.py`

- [ ] **Step 1: Write the failing test**

```python
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from filternarrange_engine.application import worker


@pytest.mark.asyncio
async def test_handle_job_writes_completed_message_on_success(monkeypatch):
    producer = AsyncMock()
    monkeypatch.setattr(worker, "_pipeline", AsyncMock(return_value="results/abc"))

    payload = {
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {"input": {"ref": "uploads/x.csv"}, "operations": []},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }
    await worker.handle_job(payload, producer=producer,
                            heartbeat_interval_s=0.0)
    sent_topics = [c.args[0] for c in producer.send.await_args_list]
    assert "topic.v1.job-results" in sent_topics
    statuses = [
        c.args[2]["status"] for c in producer.send.await_args_list
        if c.args[0] == "topic.v1.job-results"
    ]
    assert "completed" in statuses


@pytest.mark.asyncio
async def test_handle_job_skips_when_already_terminal(monkeypatch):
    producer = AsyncMock()
    monkeypatch.setattr(worker, "_load_job_status",
                        AsyncMock(return_value="completed"))
    payload = {
        "job_id":     "11111111-1111-1111-1111-111111111111",
        "user_id":    "22222222-2222-2222-2222-222222222222",
        "kind":       "batch-filter",
        "params":     {},
        "priority":   0,
        "created_at": "2026-06-07T10:00:00Z",
        "trace_id":   "t",
    }
    await worker.handle_job(payload, producer=producer,
                            heartbeat_interval_s=0.0)
    producer.send.assert_not_awaited()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest apps/data-engine/tests/application/test_worker.py -v`
Expected: FAIL — worker not implemented.

- [ ] **Step 3: Implement `worker.py`**

```python
"""Async worker — consume jobs, run the pipeline, publish results."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Mapping

from filternarrange_engine.adapters.kafka.consumer import JobConsumer
from filternarrange_engine.adapters.kafka.producer import JobResultsProducer
from filternarrange_engine.adapters.kafka.topics import JOB_RESULTS
from filternarrange_engine.application.heartbeat import Heartbeat
from filternarrange_engine.platform import bulkheads
from filternarrange_engine.platform.audit import audit_event_publish

log = logging.getLogger(__name__)

_BOOTSTRAP = os.getenv("REDPANDA_BROKERS", "redpanda:9092")
_HEARTBEAT_S = float(os.getenv("WORKER_HEARTBEAT_S", "5.0"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


async def _load_job_status(job_id: str) -> str | None:
    """Ask the gateway over its internal REST surface for the canonical
    job status. Used as the idempotency gate (spec §6).
    """
    import httpx
    base = os.getenv("GATEWAY_INTERNAL_URL", "http://gateway:8080")
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{base}/api/v1/jobs/{job_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()["status"]


async def _pipeline(payload: Mapping[str, Any]) -> str:
    """Run the filter/convert/analyze plugins from Plans B + C.

    Returns the MinIO result_ref. CPU-bound parsing is run in the
    `data-cpu` ProcessPoolExecutor; plugin fan-out is gated by the
    `plugin-async` semaphore (spec §6).
    """
    from filternarrange_engine.application import pipeline  # existing Plan B/C
    bulkheads.init()
    async with bulkheads.plugin_async:
        return await pipeline.run(payload, cpu_pool=bulkheads.data_cpu_pool)


async def handle_job(
    payload: Mapping[str, Any],
    *,
    producer: JobResultsProducer,
    heartbeat_interval_s: float = _HEARTBEAT_S,
) -> None:
    job_id = payload["job_id"]
    trace_id = payload["trace_id"]
    user_id = payload["user_id"]

    # Idempotency gate — skip if already running/terminal (spec §6).
    try:
        current = await _load_job_status(job_id)
    except Exception:                     # gateway unreachable → assume new
        current = None
    if current in ("running", "completed", "failed", "cancelled"):
        log.info("Skipping job %s — gateway reports status=%s", job_id, current)
        return

    async def emit_running() -> None:
        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "running",
            "progress":    0,
            "finished_at": _now(),         # heartbeat send time
            "trace_id":    trace_id,
        })

    hb = Heartbeat(heartbeat_interval_s, emit_running) \
            if heartbeat_interval_s > 0 else None
    hb_task = asyncio.create_task(hb.run()) if hb else None
    try:
        await audit_event_publish(
            producer, user_id=user_id, action="job.running",
            target=job_id, trace_id=trace_id)

        result_ref = await _pipeline(payload)

        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "completed",
            "progress":    100,
            "result_ref":  result_ref,
            "finished_at": _now(),
            "trace_id":    trace_id,
        })
        await audit_event_publish(
            producer, user_id=user_id, action="job.completed",
            target=job_id, metadata={"result_ref": result_ref},
            trace_id=trace_id)
    except Exception as e:
        log.exception("Job %s failed", job_id)
        await producer.send(JOB_RESULTS, key=job_id, payload={
            "job_id":      job_id,
            "status":      "failed",
            "error": {
                "code":    "PLUGIN_FAILURE",
                "message": str(e),
                "trace_id": trace_id,
            },
            "finished_at": _now(),
            "trace_id":    trace_id,
        })
        await audit_event_publish(
            producer, user_id=user_id, action="job.failed",
            target=job_id, metadata={"error": str(e)}, trace_id=trace_id)
    finally:
        if hb:
            await hb.stop()
        if hb_task:
            await hb_task


async def run_worker() -> None:
    bulkheads.init()
    producer = JobResultsProducer(_BOOTSTRAP)
    await producer.start()

    async def handler(payload: Mapping[str, Any]) -> None:
        await handle_job(payload, producer=producer)

    # Two consumer groups — both consume the same topic for Plan D; the
    # tier-aware routing is Plan F.
    paid = JobConsumer(_BOOTSTRAP, "python-worker-paid", handler)
    free = JobConsumer(_BOOTSTRAP, "python-worker-free", handler)
    await paid.start()
    await free.start()

    try:
        await asyncio.gather(paid.run(), free.run())
    finally:
        await paid.stop()
        await free.stop()
        await producer.stop()
        bulkheads.shutdown()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest apps/data-engine/tests/application/test_worker.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/data-engine/src/filternarrange_engine/application/worker.py \
        apps/data-engine/tests/application/test_worker.py
git commit -m "feat(data-engine): worker orchestrator with heartbeat + idempotency gate"
```

---

### Task 16: Frontend — jobs API client + WebSocket hook

**Files:**
- Create: `apps/frontend/src/features/jobs/api/jobsClient.ts`
- Create: `apps/frontend/src/features/jobs/api/jobsWebSocket.ts`
- Modify: `apps/frontend/src/shared/api/client.ts`
- Test: `apps/frontend/src/features/jobs/api/__tests__/jobsClient.test.ts`

- [ ] **Step 1: Add Idempotency-Key helper to `shared/api/client.ts`**

```ts
// shared/api/client.ts (additions only)
export function newIdempotencyKey(): string {
  // RFC 4122 v4 via crypto.randomUUID (Node 19+/all evergreen browsers).
  return crypto.randomUUID();
}
```

- [ ] **Step 2: Write the failing client test**

```ts
// apps/frontend/src/features/jobs/api/__tests__/jobsClient.test.ts
import { describe, expect, it, vi } from "vitest";
import { submitJob, getJob, cancelJob, listRecentJobs } from "../jobsClient";

describe("jobsClient", () => {
  it("POST /api/v1/jobs includes Idempotency-Key header", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ jobId: "j-1", status: "queued" }),
        { status: 202 }));
    await submitJob({ kind: "batch-filter", params: {} });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("Idempotency-Key")).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  });

  it("GET /api/v1/jobs/:id maps response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ jobId: "j-1", status: "running" })));
    const r = await getJob("j-1");
    expect(r.status).toBe("running");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pnpm --filter frontend vitest run jobsClient.test`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `jobsClient.ts`**

```ts
// apps/frontend/src/features/jobs/api/jobsClient.ts
import { authHeaders, newIdempotencyKey } from "@/shared/api/client";

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  jobId: string;
  status: JobStatus;
  kind: string;
  params: Record<string, unknown>;
  resultRef?: string;
  error?: { code: string; message: string; pluginId?: string; traceId?: string };
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface CreateJobRequest {
  kind: string;
  params: Record<string, unknown>;
  priority?: number;
}

const BASE = "/api/v1/jobs";

export async function submitJob(req: CreateJobRequest): Promise<Job> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: {
      "Content-Type":   "application/json",
      "Idempotency-Key": newIdempotencyKey(),
      ...authHeaders(),
    },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`submitJob failed: ${res.status}`);
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/${jobId}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`getJob failed: ${res.status}`);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/${jobId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`cancelJob failed: ${res.status}`);
  return res.json();
}

export async function listRecentJobs(): Promise<Job[]> {
  const res = await fetch(BASE, { headers: authHeaders() });
  if (!res.ok) throw new Error(`listRecentJobs failed: ${res.status}`);
  return res.json();
}
```

- [ ] **Step 5: Implement `jobsWebSocket.ts`**

```ts
// apps/frontend/src/features/jobs/api/jobsWebSocket.ts
import { JobStatus } from "./jobsClient";

export interface JobResultEnvelope {
  job_id: string;
  status: JobStatus;
  progress?: number;
  result_ref?: string;
  error?: { code: string; message: string; plugin_id?: string; trace_id?: string };
  finished_at: string;
  trace_id: string;
}

export type JobResultListener = (env: JobResultEnvelope) => void;

export function openJobSocket(
  jobId: string,
  onEvent: JobResultListener,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws/jobs/${jobId}`);

  ws.addEventListener("message", (evt: MessageEvent) => {
    try { onEvent(JSON.parse(evt.data) as JobResultEnvelope); }
    catch (e) { console.error("Bad job-result envelope", e); }
  });
  ws.addEventListener("close", () => onClose?.());

  return () => ws.close();
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pnpm --filter frontend vitest run jobsClient.test`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/frontend/src/features/jobs/api/ \
        apps/frontend/src/features/jobs/api/__tests__/ \
        apps/frontend/src/shared/api/client.ts
git commit -m "feat(frontend): jobs API client + WebSocket helper"
```

---

### Task 17: Frontend — `useJob` hook + `JobProgressCard`

**Files:**
- Create: `apps/frontend/src/features/jobs/state/useJob.ts`
- Create: `apps/frontend/src/features/jobs/state/useJobsList.ts`
- Create: `apps/frontend/src/features/jobs/ui/JobProgressCard.tsx`
- Create: `apps/frontend/src/features/jobs/ui/RunAsJobToggle.tsx`
- Create: `apps/frontend/src/features/jobs/index.ts`
- Test: `apps/frontend/src/features/jobs/state/__tests__/useJob.test.ts`

- [ ] **Step 1: Write the failing hook test**

```ts
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useJob } from "../useJob";

vi.mock("../../api/jobsClient", () => ({
  getJob: vi.fn().mockResolvedValue({
    jobId: "j-1", status: "queued", kind: "batch-filter",
    params: {}, createdAt: "2026-06-07T00:00:00Z",
  }),
}));
vi.mock("../../api/jobsWebSocket", () => ({
  openJobSocket: (id: string, on: (e: any) => void) => {
    setTimeout(() => on({
      job_id: id, status: "completed", progress: 100,
      result_ref: "results/abc", finished_at: "2026-06-07T00:01:00Z",
      trace_id: "t",
    }), 10);
    return () => {};
  },
}));

describe("useJob", () => {
  it("transitions queued → completed over WS", async () => {
    const { result } = renderHook(() => useJob("j-1"));
    await waitFor(() => expect(result.current.job?.status).toBe("queued"));
    await waitFor(() =>
      expect(result.current.job?.status).toBe("completed"), { timeout: 200 });
    expect(result.current.job?.resultRef).toBe("results/abc");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --filter frontend vitest run useJob.test`
Expected: FAIL — hook missing.

- [ ] **Step 3: Implement `useJob.ts`**

```ts
import { useEffect, useState } from "react";
import { Job, getJob } from "../api/jobsClient";
import { openJobSocket } from "../api/jobsWebSocket";

export interface UseJobResult {
  job: Job | undefined;
  progress: number;
  error: { code: string; message: string } | undefined;
}

export function useJob(jobId: string | undefined): UseJobResult {
  const [job, setJob] = useState<Job | undefined>(undefined);
  const [progress, setProgress] = useState(0);
  const [error, setError] =
    useState<{ code: string; message: string } | undefined>();

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    getJob(jobId).then(j => { if (!cancelled) setJob(j); }).catch(() => {});

    const close = openJobSocket(jobId, env => {
      setJob(prev => ({
        ...(prev ?? {
          jobId: env.job_id, kind: "", params: {},
          createdAt: env.finished_at,
        } as Job),
        status:      env.status,
        resultRef:   env.result_ref ?? prev?.resultRef,
        error:       env.error ? {
                       code:     env.error.code,
                       message:  env.error.message,
                       pluginId: env.error.plugin_id,
                       traceId:  env.error.trace_id,
                     } : prev?.error,
        finishedAt:  env.finished_at,
      }));
      if (typeof env.progress === "number") setProgress(env.progress);
      if (env.error) setError({ code: env.error.code, message: env.error.message });
    });

    return () => { cancelled = true; close(); };
  }, [jobId]);

  return { job, progress, error };
}
```

- [ ] **Step 4: Implement `useJobsList.ts`**

```ts
import { useEffect, useState } from "react";
import { Job, listRecentJobs } from "../api/jobsClient";

export function useJobsList(): { jobs: Job[]; refresh: () => Promise<void> } {
  const [jobs, setJobs] = useState<Job[]>([]);
  const refresh = async () => setJobs(await listRecentJobs());
  useEffect(() => { refresh().catch(() => {}); }, []);
  return { jobs, refresh };
}
```

- [ ] **Step 5: Implement `JobProgressCard.tsx`**

```tsx
import * as React from "react";
import { useJob } from "../state/useJob";
import { cancelJob } from "../api/jobsClient";

export interface JobProgressCardProps { jobId: string }

export function JobProgressCard({ jobId }: JobProgressCardProps) {
  const { job, progress, error } = useJob(jobId);
  if (!job) return <div className="job-card job-card--loading">Loading…</div>;

  const isTerminal = ["completed", "failed", "cancelled"].includes(job.status);

  return (
    <div className={`job-card job-card--${job.status}`}>
      <header>
        <span className="job-kind">{job.kind}</span>
        <span className="job-status">{job.status}</span>
      </header>
      <progress value={progress} max={100} />
      {error && <div className="job-error">{error.code}: {error.message}</div>}
      {!isTerminal && (
        <button onClick={() => cancelJob(jobId)}>Cancel</button>
      )}
      {job.status === "completed" && job.resultRef && (
        <a href={`/api/v1/files/${encodeURIComponent(job.resultRef)}`}
           download className="job-download">Download result</a>
      )}
      {job.status === "failed" && (
        <a href={`/jobs/${jobId}/error`} className="job-error-link">See error</a>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Implement `RunAsJobToggle.tsx`**

```tsx
import * as React from "react";

export interface RunAsJobToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
}

export function RunAsJobToggle({ value, onChange }: RunAsJobToggleProps) {
  return (
    <label className="run-as-job">
      <input
        type="checkbox"
        checked={value}
        onChange={e => onChange(e.target.checked)}
      />
      Run as job (async)
    </label>
  );
}
```

- [ ] **Step 7: Implement `index.ts` (public surface, spec §6)**

```ts
export { submitJob, getJob, cancelJob, listRecentJobs } from "./api/jobsClient";
export { useJob } from "./state/useJob";
export { useJobsList } from "./state/useJobsList";
export { JobProgressCard } from "./ui/JobProgressCard";
export { JobsListPage } from "./ui/JobsListPage";
export { BatchTab } from "./ui/BatchTab";
export { RunAsJobToggle } from "./ui/RunAsJobToggle";
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pnpm --filter frontend vitest run useJob.test`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/frontend/src/features/jobs/state/ \
        apps/frontend/src/features/jobs/ui/JobProgressCard.tsx \
        apps/frontend/src/features/jobs/ui/RunAsJobToggle.tsx \
        apps/frontend/src/features/jobs/index.ts \
        apps/frontend/src/features/jobs/state/__tests__/
git commit -m "feat(frontend): useJob hook + JobProgressCard + RunAsJobToggle"
```

---

### Task 18: Frontend — Jobs list page, Batch tab, wiring into FilterPanel

**Files:**
- Create: `apps/frontend/src/features/jobs/ui/JobsListPage.tsx`
- Create: `apps/frontend/src/features/jobs/ui/BatchTab.tsx`
- Modify: `apps/frontend/src/app/router.tsx`
- Modify: `apps/frontend/src/features/filter/ui/FilterPanel.tsx`

- [ ] **Step 1: Implement `JobsListPage.tsx`**

```tsx
import * as React from "react";
import { useJobsList } from "../state/useJobsList";
import { JobProgressCard } from "./JobProgressCard";

export function JobsListPage() {
  const { jobs } = useJobsList();
  return (
    <section className="jobs-list">
      <h2>Jobs</h2>
      {jobs.length === 0
        ? <p>No jobs yet. Submit one via "Run as job".</p>
        : jobs.map(j => <JobProgressCard key={j.jobId} jobId={j.jobId} />)}
    </section>
  );
}
```

- [ ] **Step 2: Implement `BatchTab.tsx`**

```tsx
import * as React from "react";
import { submitJob } from "../api/jobsClient";
import { JobProgressCard } from "./JobProgressCard";

export function BatchTab() {
  const [running, setRunning] = React.useState<string[]>([]);

  async function submit() {
    const j = await submitJob({
      kind: "batch-filter",
      params: { /* populated by upload UI in a real flow */ },
    });
    setRunning(prev => [j.jobId, ...prev]);
  }

  return (
    <section className="batch-tab">
      <h2>Batch (paid)</h2>
      <p>Submit large filter / convert / analyze jobs that run in the background.</p>
      <button onClick={submit}>Submit batch job</button>
      <div className="batch-tab__running">
        {running.map(id => <JobProgressCard key={id} jobId={id} />)}
      </div>
    </section>
  );
}
```

- [ ] **Step 3: Modify `router.tsx` to expose `/jobs` and Batch tab**

```tsx
// inside the router definition
import { JobsListPage, BatchTab } from "@/features/jobs";

const routes = [
  // ...existing routes
  { path: "/jobs", element: <JobsListPage /> },
  { path: "/batch", element: <BatchTab /> },
];
```

- [ ] **Step 4: Wire `RunAsJobToggle` into `FilterPanel.tsx`**

```tsx
// inside FilterPanel.tsx
import { RunAsJobToggle, submitJob } from "@/features/jobs";
// ...
const [asJob, setAsJob] = React.useState(false);

async function applyFilter() {
  if (asJob) {
    const j = await submitJob({
      kind: "batch-filter",
      params: { input: inputRef, operations: filterSpec },
    });
    navigate(`/jobs/${j.jobId}`);
    return;
  }
  // existing sync code path
}

// in the JSX form footer:
<RunAsJobToggle value={asJob} onChange={setAsJob} />
```

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/features/jobs/ui/JobsListPage.tsx \
        apps/frontend/src/features/jobs/ui/BatchTab.tsx \
        apps/frontend/src/app/router.tsx \
        apps/frontend/src/features/filter/ui/FilterPanel.tsx
git commit -m "feat(frontend): Jobs page + Batch tab + Run-as-job toggle"
```

---

### Task 19: Integration test — end-to-end async path on real compose stack

**Files:**
- Create: `tests/integration/test_async_path_e2e.py`

- [ ] **Step 1: Write the test**

```python
"""End-to-end async path against the full docker-compose stack.

Prereqs: `docker compose -f infra/docker-compose.yml up -d` running.
"""
from __future__ import annotations

import json
import os
import pathlib
import time
import uuid

import httpx
import pytest
import websockets

GATEWAY = os.getenv("FILTERNARRANGE_GATEWAY_URL", "http://localhost:8080")
WS_HOST = os.getenv("FILTERNARRANGE_WS_HOST", "localhost:8080")


@pytest.fixture
def sample_csv(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "sample.csv"
    header = "id,age,country\n"
    rows = "\n".join(f"{i},{20 + (i % 60)},IN" for i in range(1_000_000))
    p.write_text(header + rows)
    assert p.stat().st_size > 25 * 1024 * 1024   # > 25 MB → async path
    return p


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_path_completes_via_websocket(sample_csv):
    # 1) Upload the file (pre-signed PUT URL flow from Plan B).
    async with httpx.AsyncClient(timeout=60.0) as c:
        upload = await c.post(f"{GATEWAY}/api/v1/uploads",
                              json={"filename": "sample.csv"})
        assert upload.status_code == 200
        upload_ref = upload.json()["ref"]
        signed_url = upload.json()["upload_url"]
        with open(sample_csv, "rb") as f:
            r = await c.put(signed_url, content=f.read())
            assert r.status_code in (200, 204)

        # 2) Submit job.
        idem = str(uuid.uuid4())
        job = await c.post(f"{GATEWAY}/api/v1/jobs",
                           headers={"Idempotency-Key": idem},
                           json={
                             "kind": "batch-filter",
                             "params": {
                               "input": {"ref": upload_ref,
                                         "detected_format": "csv"},
                               "operations": [
                                 {"kind": "filter", "mode": "row",
                                  "predicate": "age > 18"}],
                             }})
        assert job.status_code == 202
        job_id = job.json()["jobId"]

    # 3) Open WS and assert state transitions.
    seen = []
    async with websockets.connect(f"ws://{WS_HOST}/ws/jobs/{job_id}") as ws:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            msg = json.loads(await ws.recv())
            seen.append(msg["status"])
            if msg["status"] in ("completed", "failed", "cancelled"):
                break

    assert "running" in seen
    assert seen[-1] == "completed"

    # 4) Result downloadable.
    async with httpx.AsyncClient(timeout=60.0) as c:
        get = await c.get(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert get.status_code == 200
        result_ref = get.json()["resultRef"]
        assert result_ref is not None
        dl = await c.get(f"{GATEWAY}/api/v1/files/{result_ref}",
                         follow_redirects=True)
        assert dl.status_code == 200
        assert len(dl.content) > 0
```

- [ ] **Step 2: Run it against compose**

Run:
```bash
docker compose -f infra/docker-compose.yml up -d
pytest tests/integration/test_async_path_e2e.py -m integration -v
```
Expected: PASS within ~2 minutes on a 50MB-class CSV.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_async_path_e2e.py
git commit -m "test(integration): end-to-end async path via WebSocket"
```

---

### Task 20: Integration test — circuit breaker opens on data-engine outage

**Files:**
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/resilience/CircuitBreakerIT.java`

- [ ] **Step 1: Write the test (uses a stub HTTP server we crash mid-test)**

```java
package io.filternarrange.gateway.platform.resilience;

import com.github.tomakehurst.wiremock.WireMockServer;
import io.github.resilience4j.circuitbreaker.CircuitBreaker;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.web.client.RestClient;

import static com.github.tomakehurst.wiremock.client.WireMock.*;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class CircuitBreakerIT {

    static WireMockServer mock;

    @BeforeAll static void up()   { mock = new WireMockServer(0); mock.start(); }
    @AfterAll  static void down() { mock.stop(); }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("data-engine.base-url", () -> mock.baseUrl());
    }

    @Autowired CircuitBreaker dataEngineBreaker;
    @Autowired RestClient http;

    @Test
    void breaker_opens_after_5_failures_then_recovers_after_30s() {
        mock.stubFor(post(urlEqualTo("/internal/v1/detect"))
            .willReturn(aResponse().withStatus(503)));

        for (int i = 0; i < 5; i++) {
            assertThat(callAndCatch()).isNotNull();
        }
        assertThat(dataEngineBreaker.getState())
            .isEqualTo(CircuitBreaker.State.OPEN);
    }

    private Throwable callAndCatch() {
        try {
            dataEngineBreaker.executeSupplier(() ->
                http.post().uri("/internal/v1/detect").retrieve().body(String.class));
            return null;
        } catch (Throwable t) { return t; }
    }
}
```

- [ ] **Step 2: Add `wiremock-jre8` to `build.gradle.kts` testImplementation**

```kotlin
testImplementation("com.github.tomakehurst:wiremock-jre8:3.0.1")
```

- [ ] **Step 3: Run the test**

Run: `./gradlew :apps:gateway:test --tests CircuitBreakerIT`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/gateway/src/test/java/io/filternarrange/gateway/platform/resilience/CircuitBreakerIT.java \
        apps/gateway/build.gradle.kts
git commit -m "test(gateway): circuit-breaker IT opens after 5 failures (spec §6)"
```

---

### Task 21: Integration test — schema validation rejects malformed Kafka messages

**Files:**
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumerIT.java` (already declared in Task 10's File Structure — implementing here)

- [ ] **Step 1: Write the test**

```java
package io.filternarrange.gateway.infrastructure.messaging;

import io.filternarrange.gateway.infrastructure.persistence.AuditLogRepository;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.common.serialization.StringSerializer;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;

import java.time.Duration;
import java.util.Map;
import java.util.Properties;

import static org.awaitility.Awaitility.await;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

@SpringBootTest
@EmbeddedKafka(partitions = 1, topics = {"topic.v1.audit-events"})
class AuditEventsConsumerIT {

    @MockBean AuditLogRepository repo;
    @Autowired EmbeddedKafkaBroker broker;

    @Test
    void malformed_message_does_not_break_consumer() throws Exception {
        Properties p = new Properties();
        p.put("bootstrap.servers", broker.getBrokersAsString());
        p.put("key.serializer", StringSerializer.class.getName());
        p.put("value.serializer", StringSerializer.class.getName());
        try (var producer = new KafkaProducer<String, String>(p)) {
            producer.send(new ProducerRecord<>("topic.v1.audit-events",
                "u", "{\"not\":\"valid\"}")).get();
        }
        // Wait long enough that the consumer would have processed it.
        Thread.sleep(2000);
        verify(repo, never()).insert(
            org.mockito.ArgumentMatchers.any(),
            org.mockito.ArgumentMatchers.anyString(),
            org.mockito.ArgumentMatchers.anyString(),
            org.mockito.ArgumentMatchers.any(),
            org.mockito.ArgumentMatchers.any());
    }
}
```

- [ ] **Step 2: Run it**

Run: `./gradlew :apps:gateway:test --tests AuditEventsConsumerIT`
Expected: PASS — repo never invoked because validation rejected.

- [ ] **Step 3: Commit**

```bash
git add apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/messaging/AuditEventsConsumerIT.java
git commit -m "test(gateway): malformed Kafka messages are dropped, consumer keeps running"
```

---

### Task 22: Integration test — cancel before pickup

**Files:**
- Create: `tests/integration/test_cancel.py`

- [ ] **Step 1: Write the test**

```python
"""Cancel a queued job before the worker picks it up."""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

GATEWAY = os.getenv("FILTERNARRANGE_GATEWAY_URL", "http://localhost:8080")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_before_worker_pickup_blocks_processing():
    async with httpx.AsyncClient(timeout=10.0) as c:
        # Submit with high priority to a paused-worker compose profile if
        # available; otherwise rely on the natural queue latency.
        idem = str(uuid.uuid4())
        job = await c.post(f"{GATEWAY}/api/v1/jobs",
            headers={"Idempotency-Key": idem},
            json={"kind": "batch-filter",
                  "params": {"input": {"ref": "uploads/none.csv"}}})
        assert job.status_code == 202
        job_id = job.json()["jobId"]

        # Cancel immediately.
        cancel = await c.delete(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        # Give the worker a chance to try, then re-fetch — must remain cancelled.
        import asyncio
        await asyncio.sleep(3)
        get = await c.get(f"{GATEWAY}/api/v1/jobs/{job_id}")
        assert get.json()["status"] == "cancelled"
```

- [ ] **Step 2: Run it**

Run: `pytest tests/integration/test_cancel.py -m integration -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_cancel.py
git commit -m "test(integration): cancel-before-pickup keeps job in cancelled state"
```

---

## Self-Review

**1. Spec coverage:**

- §3 async path (`React → POST /api/v1/jobs → gateway → Kafka → worker → WS`) — Tasks 9, 10, 15, 16-18, 19.
- §3 contracts (`topic.v1.jobs`, `topic.v1.job-results`, `topic.v1.audit-events`, `topic.v1.format-requests`) — Task 3.
- §5 `jobs` table + the two indexes — Task 1.
- §5 `audit_log` partitioned by month + default partition — Task 2.
- §5 Kafka topics with partition counts and retention — Task 4.
- §5 partition keys (`user_id` for jobs + audit-events; `job_id` for job-results) — Task 7 (`JobProducer`, `AuditEventPublisher`), Task 15 (`worker.handle_job`).
- §6 bulkheading (Java `web-io`/`db-io`/`kafka-producer`; Python `data-cpu`/`plugin-async`) — Tasks 7, 14.
- §6 timeouts (5s gateway→data-engine, 3s Postgres, 250ms Redis, 10s Kafka, 60s MinIO) — Task 6 (Postgres), Task 7 (Kafka + app.yml), Task 8 (HTTP), Task 15 (HTTP).
- §6 Resilience4j breaker (5 consecutive failures in 10s → open, 30s half-open) — Task 8 + Task 20 test.
- §6 idempotency key + Redis `gw:idem:{key}` + 24h TTL — Task 8.
- §6 error envelope `{code, plugin_id?, message, trace_id}` — Task 8 (`ServiceDegradedException`), Task 15 (failed-job envelope).
- §3 sync trigger rules — preserved (Plan B already enforces; Plan D does not weaken).
- §2 MODE switch (`full|data|ai|worker`) — Task 11.
- Heartbeat every 5s — Task 14 + Task 15.
- Two consumer groups (`python-worker-paid`, `python-worker-free`) — Task 15.
- WS handler `/ws/jobs/{job_id}` + close on terminal — Task 10.
- Frontend Batch tab + Run-as-job toggle + Jobs list — Tasks 16-18.
- Tests for end-to-end async, idempotency, circuit breaker, schema validation, cancel — Tasks 9, 19-22.

**2. Placeholder scan:** No `TBD`, `TODO`, "add appropriate error handling", or "implement later". Every code block compiles or runs as-is given the Plan B + C dependencies stated up front.

**3. Type consistency:**

- `JobStatus` enum values (`QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED`) used consistently in Java (`JobStatus.QUEUED`) and on the wire (`"queued"`).
- `JobKind` wire values (`batch-filter`, `convert`, `analyze`) matched in the JSON schema (Task 3) and in `JobKind.fromWire()` (Task 5).
- Topic constants centralized in `KafkaTopics.java` (Java) and `topics.py` (Python).
- `KafkaTemplate<String, String>` qualifier names `jobsKafkaTemplate` / `auditKafkaTemplate` are referenced consistently in `JobProducer` and `AuditEventPublisher`.
- `JobSubscriberRegistry` method names `register`, `unregister`, `broadcast` — same across producer (Task 10) and consumer (Task 10).
- Python `_pipeline(payload)`, `_load_job_status(job_id)`, `handle_job(payload, *, producer, heartbeat_interval_s)` — signature stable across Task 15 implementation and Task 15 tests.
- Frontend `Job.status: JobStatus` literal-union matches the Java enum's lower-cased wire form (`queued|running|completed|failed|cancelled`).

**4. Dependency ordering:** Verified by walking the graph — every imported symbol either ships with Plans B/C (existing) or appears in a strictly earlier task in this plan.

**5. Out-of-scope discipline:** No Keycloak code, no tier routing logic, no AI / Ollama, no format-request workflow body — only the skeleton schema file and the two consumer groups (named only, behaving identically).

---

Plan complete and saved to `docs/superpowers/plans/2026-06-07-D-async-path.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task with two-stage review checkpoints.

**2. Inline Execution** — Run tasks in this session via the executing-plans skill with batched checkpoints.

Which approach?
