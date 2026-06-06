# Plan B — Walking Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the first end-to-end user flow — login, upload a CSV, see detected format, filter columns, download as CSV or JSON — across Spring Boot gateway, Python data-engine, and React frontend, with the contract OpenAPI as the single source of truth.

**Architecture:** Three apps wired through versioned REST contracts. Gateway owns auth (Spring-JWT) and Postgres; data-engine owns the canonical model (`TabularData` / `TreeData`) and the plugin registry; frontend is feature-sliced with a generated API client. Two format plugins (CSV, JSON) and one filter plugin (column projection) prove the plugin extension surface. All sync path; no Kafka / async / AI yet.

**Tech Stack:** Spring Boot 3.3 (Java 21), Flyway, HikariCP, springdoc-openapi, ArchUnit; FastAPI (Python 3.12), `uv`, pydantic v2, `import-linter`; React 18 + Vite + TypeScript, `react-dropzone`, `openapi-typescript-codegen`, vitest, Playwright; Postgres 16, Redis 7, MinIO; testcontainers-python for cross-service integration.

**Conventions (locked across all 8 plans):**
- Java root package: `io.filternarrange.gateway`
- Python root package: `filternarrange_engine`
- Frontend: feature-sliced React + TypeScript at `apps/frontend/src/`
- Conventional Commits, squash-merge, `Closes #N` (use `#TBD` if not yet known)
- Cross-service error envelope: `{ code, plugin_id?, message, trace_id }`
- Test commands: `./gradlew test`, `uv run pytest`, `npm test`
- Plugin manifest: TOML per spec §4
- Auth: Spring-JWT only (env switch `AUTH_PROVIDER=spring-jwt`); Keycloak deferred to Plan G.

---

## File Structure

### Contracts (single source of truth)

- `contracts/openapi/gateway-public.v1.yaml` — every endpoint the frontend calls
- `contracts/openapi/gateway-internal.v1.yaml` — every endpoint the gateway calls on the data-engine
- `contracts/openapi/.spectral.yaml` — lint rules
- `.github/workflows/contracts.yml` — oasdiff breaking-change gate (extends Plan A's `pr.yml`)

### Gateway (Spring Boot, hexagonal)

- `apps/gateway/build.gradle.kts` — adds deps + springdoc + openapi-generator + ArchUnit + Resilience4j (skeleton; full breaker tuning later)
- `apps/gateway/src/main/resources/application.yml`
- `apps/gateway/src/main/resources/db/migration/V1__users.sql`
- `apps/gateway/src/main/resources/db/migration/V2__sessions.sql`
- `apps/gateway/src/main/java/io/filternarrange/gateway/GatewayApplication.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/User.java` — domain entity
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/UserRepository.java` — port
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/session/Session.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/session/SessionRepository.java` — port
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/storage/ObjectStore.java` — port
- `apps/gateway/src/main/java/io/filternarrange/gateway/domain/dataengine/DataEngineClient.java` — port
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/auth/AuthService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/upload/UploadService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/application/pipeline/PipelineService.java` — detect / filter / convert orchestration
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/AuthController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/upload/UploadController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/PipelineController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/download/DownloadController.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/api/dto/...` — generated from OpenAPI
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/...` — JPA / JDBC adapters
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/storage/MinioObjectStore.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineHttpClient.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtAuthFilter.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtService.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/SecurityConfig.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/ErrorEnvelope.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/GlobalExceptionHandler.java`
- `apps/gateway/src/main/java/io/filternarrange/gateway/platform/storage/BucketBootstrap.java`
- `apps/gateway/src/test/java/io/filternarrange/gateway/architecture/LayeringTest.java` — ArchUnit
- `apps/gateway/src/test/java/io/filternarrange/gateway/...` — unit + slice tests

### Data-engine (Python, hexagonal)

- `apps/data-engine/pyproject.toml` (extend)
- `apps/data-engine/.importlinter`
- `apps/data-engine/src/filternarrange_engine/__init__.py`
- `apps/data-engine/src/filternarrange_engine/api/main.py`
- `apps/data-engine/src/filternarrange_engine/api/routes_detect.py`
- `apps/data-engine/src/filternarrange_engine/api/routes_filter.py`
- `apps/data-engine/src/filternarrange_engine/api/routes_convert.py`
- `apps/data-engine/src/filternarrange_engine/application/detect_service.py`
- `apps/data-engine/src/filternarrange_engine/application/filter_service.py`
- `apps/data-engine/src/filternarrange_engine/application/convert_service.py`
- `apps/data-engine/src/filternarrange_engine/core/types.py` — `TypeTag`
- `apps/data-engine/src/filternarrange_engine/core/canonical.py` — `Column`, `TabularData`, `Node`, `TreeData`
- `apps/data-engine/src/filternarrange_engine/core/plugin_api.py` — `FormatPlugin`, `FilterPlugin`, manifests, `PluginResult`
- `apps/data-engine/src/filternarrange_engine/core/ports.py` — `ObjectStorePort`
- `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/registry.py`
- `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/dispatcher.py`
- `apps/data-engine/src/filternarrange_engine/adapters/storage/minio_store.py`
- `apps/data-engine/src/filternarrange_engine/platform/errors.py`
- `apps/data-engine/src/filternarrange_engine/platform/config.py`
- `apps/data-engine/src/filternarrange_engine/platform/logging.py`

### Plugins

- `plugins/format-csv/pyproject.toml`
- `plugins/format-csv/manifest.toml`
- `plugins/format-csv/src/filternarrange_format_csv/__init__.py`
- `plugins/format-csv/src/filternarrange_format_csv/plugin.py`
- `plugins/format-csv/src/filternarrange_format_csv/detect.py`
- `plugins/format-csv/src/filternarrange_format_csv/parse.py`
- `plugins/format-csv/src/filternarrange_format_csv/emit.py`
- `plugins/format-csv/tests/fixtures/people.csv`
- `plugins/format-csv/tests/test_detect.py`
- `plugins/format-csv/tests/test_parse.py`
- `plugins/format-csv/tests/test_emit.py`
- `plugins/format-json/...` — mirror layout
- `plugins/filter-column/...` — mirror layout

### Frontend

- `apps/frontend/package.json` (extend)
- `apps/frontend/.eslintrc.cjs`
- `apps/frontend/openapi-ts.config.ts`
- `apps/frontend/src/app/App.tsx`
- `apps/frontend/src/app/router.tsx`
- `apps/frontend/src/app/providers/AuthProvider.tsx`
- `apps/frontend/src/features/auth/{api,ui,state,index.ts}`
- `apps/frontend/src/features/upload/{api,ui,state,index.ts}`
- `apps/frontend/src/features/filter/{api,ui,state,index.ts}`
- `apps/frontend/src/features/download/{api,ui,state,index.ts}`
- `apps/frontend/src/shared/api/generated/` — generated from contract
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/pages/{LoginPage,SignupPage,WorkbenchPage}.tsx`
- `apps/frontend/tests/unit/*.test.tsx`
- `apps/frontend/tests/e2e/walking-skeleton.spec.ts`

### Integration tests

- `tests/integration/test_walking_skeleton.py`
- `tests/integration/conftest.py`
- `tests/fixtures/sample.csv`
- `tests/fixtures/sample.json`

---

## Task Overview

1. Contracts: flesh out OpenAPI specs (public + internal) + spectral lint + oasdiff CI step
2. Gateway: Flyway migrations + Hikari + Postgres testcontainer
3. Gateway: JWT auth (signup/login/me) + SecurityConfig + filter
4. Gateway: error envelope + global exception handler
5. Gateway: MinIO adapter + bucket bootstrap
6. Gateway: data-engine HTTP client + circuit-breaker skeleton
7. Gateway: upload / detect / filter-preview / convert / download controllers (generated DTOs)
8. Gateway: ArchUnit layering test
9. Data-engine: canonical model (`TypeTag`, `Column`, `TabularData`, `Node`, `TreeData`)
10. Data-engine: plugin API protocols + `PluginResult` + manifests
11. Data-engine: plugin registry + dispatcher (catch-and-envelope)
12. Data-engine: MinIO storage adapter + config + logging
13. Plugin: `format-csv` — manifest + detect + parse + emit + tests
14. Plugin: `format-json` — manifest + detect + parse + emit + tests
15. Plugin: `filter-column` — manifest + apply + validate + explain + tests
16. Data-engine: FastAPI routers (`/detect`, `/filter`, `/convert`) + service layer
17. Data-engine: `import-linter` config
18. Frontend: API client generation + auth feature (login/signup/me) + AuthProvider
19. Frontend: upload feature (react-dropzone) + detection result UI
20. Frontend: filter feature (column picker) + preview table
21. Frontend: download feature + format chooser + workbench page wiring
22. Frontend: eslint-plugin-boundaries config + vitest unit tests
23. Integration: testcontainers Python test of full happy path
24. E2E: Playwright walking-skeleton spec against docker compose

---

## Task 1: Contracts — Flesh out OpenAPI + spectral + oasdiff gate

**Files:**
- Create: `contracts/openapi/gateway-public.v1.yaml`
- Create: `contracts/openapi/gateway-internal.v1.yaml`
- Create: `contracts/openapi/.spectral.yaml`
- Create: `.github/workflows/contracts.yml`
- Create: `contracts/openapi/tests/lint.sh`

- [ ] **Step 1.1: Write the contract lint test**

Create `contracts/openapi/tests/lint.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx --yes @stoplight/spectral-cli@6 lint gateway-public.v1.yaml --ruleset .spectral.yaml --fail-severity=warn
npx --yes @stoplight/spectral-cli@6 lint gateway-internal.v1.yaml --ruleset .spectral.yaml --fail-severity=warn
echo "OK"
```

- [ ] **Step 1.2: Run lint — must fail (files missing)**

Run: `bash contracts/openapi/tests/lint.sh`
Expected: FAIL — file not found.

- [ ] **Step 1.3: Create `.spectral.yaml`**

```yaml
extends: ["spectral:oas"]
rules:
  operation-tag-defined: error
  operation-operationId: error
  operation-success-response: error
  oas3-unused-component: warn
```

- [ ] **Step 1.4: Create `gateway-public.v1.yaml`**

```yaml
openapi: 3.1.0
info:
  title: FilterNArrange Gateway Public API
  version: 1.0.0
  description: REST surface consumed by the React frontend.
  license:
    name: Apache-2.0
servers:
  - url: /api/v1
tags:
  - name: auth
  - name: upload
  - name: pipeline
  - name: download
paths:
  /auth/signup:
    post:
      tags: [auth]
      operationId: signup
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/SignupRequest' }
      responses:
        '200':
          description: signed up
          content:
            application/json:
              schema: { $ref: '#/components/schemas/AuthResponse' }
        '400': { $ref: '#/components/responses/Error' }
        '409': { $ref: '#/components/responses/Error' }
  /auth/login:
    post:
      tags: [auth]
      operationId: login
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/LoginRequest' }
      responses:
        '200':
          description: logged in
          content:
            application/json:
              schema: { $ref: '#/components/schemas/AuthResponse' }
        '401': { $ref: '#/components/responses/Error' }
  /auth/me:
    get:
      tags: [auth]
      operationId: me
      security: [{ bearerAuth: [] }]
      responses:
        '200':
          description: current user
          content:
            application/json:
              schema: { $ref: '#/components/schemas/User' }
        '401': { $ref: '#/components/responses/Error' }
  /upload:
    post:
      tags: [upload]
      operationId: upload
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [file]
              properties:
                file:
                  type: string
                  format: binary
      responses:
        '200':
          description: uploaded
          content:
            application/json:
              schema: { $ref: '#/components/schemas/UploadResponse' }
        '413': { $ref: '#/components/responses/Error' }
        '401': { $ref: '#/components/responses/Error' }
  /detect:
    post:
      tags: [pipeline]
      operationId: detect
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/DetectRequest' }
      responses:
        '200':
          description: detected
          content:
            application/json:
              schema: { $ref: '#/components/schemas/DetectResponse' }
        '400': { $ref: '#/components/responses/Error' }
        '404': { $ref: '#/components/responses/Error' }
  /filter/preview:
    post:
      tags: [pipeline]
      operationId: filterPreview
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/FilterPreviewRequest' }
      responses:
        '200':
          description: preview
          content:
            application/json:
              schema: { $ref: '#/components/schemas/FilterPreviewResponse' }
        '400': { $ref: '#/components/responses/Error' }
  /convert:
    post:
      tags: [pipeline]
      operationId: convert
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ConvertRequest' }
      responses:
        '200':
          description: result-ready
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ConvertResponse' }
        '400': { $ref: '#/components/responses/Error' }
  /download/{resultId}:
    get:
      tags: [download]
      operationId: download
      security: [{ bearerAuth: [] }]
      parameters:
        - in: path
          name: resultId
          required: true
          schema: { type: string, format: uuid }
      responses:
        '302':
          description: redirect to pre-signed MinIO URL
          headers:
            Location:
              schema: { type: string }
        '404': { $ref: '#/components/responses/Error' }
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  responses:
    Error:
      description: structured error
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ErrorEnvelope' }
  schemas:
    SignupRequest:
      type: object
      required: [email, password]
      properties:
        email: { type: string, format: email }
        password: { type: string, minLength: 8 }
        displayName: { type: string }
    LoginRequest:
      type: object
      required: [email, password]
      properties:
        email: { type: string, format: email }
        password: { type: string }
    AuthResponse:
      type: object
      required: [token, user]
      properties:
        token: { type: string }
        user: { $ref: '#/components/schemas/User' }
    User:
      type: object
      required: [id, email]
      properties:
        id: { type: string, format: uuid }
        email: { type: string, format: email }
        displayName: { type: string, nullable: true }
    UploadResponse:
      type: object
      required: [uploadId, ref, sizeBytes]
      properties:
        uploadId: { type: string, format: uuid }
        ref: { type: string }
        sizeBytes: { type: integer, format: int64 }
    DetectRequest:
      type: object
      required: [uploadId]
      properties:
        uploadId: { type: string, format: uuid }
    Column:
      type: object
      required: [name, type, nullable]
      properties:
        name: { type: string }
        type:
          type: string
          enum: [string, number, integer, boolean, datetime, "null"]
        nullable: { type: boolean }
    DetectResponse:
      type: object
      required: [format, confidence, schema]
      properties:
        format: { type: string }
        confidence: { type: number, minimum: 0, maximum: 1 }
        schema:
          type: array
          items: { $ref: '#/components/schemas/Column' }
    ColumnFilterSpec:
      type: object
      required: [kind, keep]
      properties:
        kind: { type: string, enum: [column] }
        keep:
          type: array
          items: { type: string }
    FilterPreviewRequest:
      type: object
      required: [uploadId, filter]
      properties:
        uploadId: { type: string, format: uuid }
        filter: { $ref: '#/components/schemas/ColumnFilterSpec' }
        sampleSize: { type: integer, default: 20, minimum: 1, maximum: 500 }
    FilterPreviewResponse:
      type: object
      required: [schema, rows]
      properties:
        schema:
          type: array
          items: { $ref: '#/components/schemas/Column' }
        rows:
          type: array
          items:
            type: object
            additionalProperties: true
    ConvertRequest:
      type: object
      required: [uploadId, filter, outputFormat]
      properties:
        uploadId: { type: string, format: uuid }
        filter: { $ref: '#/components/schemas/ColumnFilterSpec' }
        outputFormat:
          type: string
          enum: [csv, json]
    ConvertResponse:
      type: object
      required: [resultId, ref]
      properties:
        resultId: { type: string, format: uuid }
        ref: { type: string }
    ErrorEnvelope:
      type: object
      required: [code, message, traceId]
      properties:
        code: { type: string }
        pluginId: { type: string, nullable: true }
        message: { type: string }
        traceId: { type: string }
```

- [ ] **Step 1.5: Create `gateway-internal.v1.yaml`**

```yaml
openapi: 3.1.0
info:
  title: FilterNArrange Gateway → Data-engine Internal API
  version: 1.0.0
  license:
    name: Apache-2.0
servers:
  - url: http://data-engine:8000
tags:
  - name: detect
  - name: filter
  - name: convert
paths:
  /detect:
    post:
      tags: [detect]
      operationId: engineDetect
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/RefRequest' }
      responses:
        '200':
          description: detected
          content:
            application/json:
              schema: { $ref: '#/components/schemas/DetectResult' }
        '4XX': { $ref: '#/components/responses/Error' }
        '5XX': { $ref: '#/components/responses/Error' }
  /filter:
    post:
      tags: [filter]
      operationId: engineFilter
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/FilterRequest' }
      responses:
        '200':
          description: filtered
          content:
            application/json:
              schema: { $ref: '#/components/schemas/FilterResult' }
        '4XX': { $ref: '#/components/responses/Error' }
        '5XX': { $ref: '#/components/responses/Error' }
  /convert:
    post:
      tags: [convert]
      operationId: engineConvert
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/ConvertRequest' }
      responses:
        '200':
          description: converted
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ConvertResult' }
        '4XX': { $ref: '#/components/responses/Error' }
        '5XX': { $ref: '#/components/responses/Error' }
components:
  responses:
    Error:
      description: structured plugin or engine error
      content:
        application/json:
          schema: { $ref: '#/components/schemas/ErrorEnvelope' }
  schemas:
    RefRequest:
      type: object
      required: [ref]
      properties:
        ref: { type: string }
    Column:
      type: object
      required: [name, type, nullable]
      properties:
        name: { type: string }
        type:
          type: string
          enum: [string, number, integer, boolean, datetime, "null"]
        nullable: { type: boolean }
    DetectResult:
      type: object
      required: [format, confidence, schema]
      properties:
        format: { type: string }
        confidence: { type: number, minimum: 0, maximum: 1 }
        schema:
          type: array
          items: { $ref: '#/components/schemas/Column' }
    ColumnFilterSpec:
      type: object
      required: [kind, keep]
      properties:
        kind: { type: string, enum: [column] }
        keep:
          type: array
          items: { type: string }
    FilterRequest:
      type: object
      required: [ref, filter]
      properties:
        ref: { type: string }
        filter: { $ref: '#/components/schemas/ColumnFilterSpec' }
        sampleSize: { type: integer, default: 20 }
    FilterResult:
      type: object
      required: [schema, rows]
      properties:
        schema:
          type: array
          items: { $ref: '#/components/schemas/Column' }
        rows:
          type: array
          items:
            type: object
            additionalProperties: true
    ConvertRequest:
      type: object
      required: [ref, filter, outputFormat]
      properties:
        ref: { type: string }
        filter: { $ref: '#/components/schemas/ColumnFilterSpec' }
        outputFormat: { type: string, enum: [csv, json] }
    ConvertResult:
      type: object
      required: [resultRef]
      properties:
        resultRef: { type: string }
    ErrorEnvelope:
      type: object
      required: [code, message, traceId]
      properties:
        code: { type: string }
        pluginId: { type: string, nullable: true }
        message: { type: string }
        traceId: { type: string }
```

- [ ] **Step 1.6: Make the lint script executable, run it**

Run: `chmod +x contracts/openapi/tests/lint.sh && bash contracts/openapi/tests/lint.sh`
Expected: PASS.

- [ ] **Step 1.7: Add oasdiff GitHub workflow**

Create `.github/workflows/contracts.yml`:

```yaml
name: contracts
on:
  pull_request:
    paths:
      - 'contracts/**'
jobs:
  oasdiff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Fetch base
        run: git fetch origin "${{ github.base_ref }}":refs/remotes/origin/base
      - name: Install oasdiff
        run: |
          curl -fsSL https://github.com/oasdiff/oasdiff/releases/download/v1.10.25/oasdiff_1.10.25_linux_amd64.tar.gz \
            | tar -xz oasdiff
          sudo mv oasdiff /usr/local/bin/
      - name: Diff public
        run: |
          git show origin/base:contracts/openapi/gateway-public.v1.yaml > /tmp/base-public.yaml || exit 0
          oasdiff breaking /tmp/base-public.yaml contracts/openapi/gateway-public.v1.yaml --fail-on ERR
      - name: Diff internal
        run: |
          git show origin/base:contracts/openapi/gateway-internal.v1.yaml > /tmp/base-internal.yaml || exit 0
          oasdiff breaking /tmp/base-internal.yaml contracts/openapi/gateway-internal.v1.yaml --fail-on ERR
      - name: Spectral lint
        run: bash contracts/openapi/tests/lint.sh
```

- [ ] **Step 1.8: Commit**

```bash
git add contracts/ .github/workflows/contracts.yml
git commit -m "feat(contracts): flesh out v1 OpenAPI for walking skeleton + oasdiff gate

Closes #TBD"
```

---

## Task 2: Gateway — Flyway migrations + Postgres testcontainer harness

**Files:**
- Modify: `apps/gateway/build.gradle.kts`
- Create: `apps/gateway/src/main/resources/application.yml`
- Create: `apps/gateway/src/main/resources/db/migration/V1__users.sql`
- Create: `apps/gateway/src/main/resources/db/migration/V2__sessions.sql`
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/persistence/MigrationTest.java`
- Create: `apps/gateway/src/test/resources/application-test.yml`

- [ ] **Step 2.1: Write a Flyway migration test that fails**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/persistence/MigrationTest.java`:

```java
package io.filternarrange.gateway.persistence;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class MigrationTest {

    @Container
    static PostgreSQLContainer<?> POSTGRES =
        new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        r.add("spring.datasource.username", POSTGRES::getUsername);
        r.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired JdbcTemplate jdbc;

    @Test
    void usersTableExists() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'users'",
            Integer.class);
        assertThat(count).isEqualTo(1);
    }

    @Test
    void sessionsTableExists() {
        Integer count = jdbc.queryForObject(
            "select count(*) from information_schema.tables where table_name = 'sessions'",
            Integer.class);
        assertThat(count).isEqualTo(1);
    }
}
```

- [ ] **Step 2.2: Extend `build.gradle.kts`**

Append to `apps/gateway/build.gradle.kts`:

```kotlin
plugins {
    java
    id("org.springframework.boot") version "3.3.4"
    id("io.spring.dependency-management") version "1.1.6"
    id("org.openapi.generator") version "7.7.0"
    id("org.flywaydb.flyway") version "10.17.0"
}

group = "io.filternarrange"
version = "0.1.0-SNAPSHOT"
java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }

repositories { mavenCentral() }

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    runtimeOnly("org.postgresql:postgresql")
    implementation("io.minio:minio:8.5.12")
    implementation("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.6.0")
    implementation("io.github.resilience4j:resilience4j-spring-boot3:2.2.0")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("com.fasterxml.jackson.module:jackson-module-parameter-names")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
    testImplementation("org.testcontainers:junit-jupiter:1.20.1")
    testImplementation("org.testcontainers:postgresql:1.20.1")
    testImplementation("org.testcontainers:minio:1.20.1")
    testImplementation("com.tngtech.archunit:archunit-junit5:1.3.0")
}

tasks.test { useJUnitPlatform() }
```

- [ ] **Step 2.3: Create `application.yml`**

Create `apps/gateway/src/main/resources/application.yml`:

```yaml
server:
  port: 8080
spring:
  application:
    name: gateway
  datasource:
    url: jdbc:postgresql://${POSTGRES_HOST:postgres}:${POSTGRES_PORT:5432}/${POSTGRES_DB:filternarrange}
    username: ${POSTGRES_USER:filternarrange}
    password: ${POSTGRES_PASSWORD:filternarrange}
    hikari:
      maximum-pool-size: 10
      minimum-idle: 2
      connection-timeout: 3000
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
  flyway:
    enabled: true
    locations: classpath:db/migration
  data:
    redis:
      host: ${REDIS_HOST:redis}
      port: ${REDIS_PORT:6379}

auth:
  provider: ${AUTH_PROVIDER:spring-jwt}
  jwt:
    secret: ${JWT_SECRET:dev-secret-change-me-please-32-bytes-min}
    ttl-seconds: 86400

minio:
  endpoint: ${MINIO_ENDPOINT:http://minio:9000}
  access-key: ${MINIO_ACCESS_KEY:minioadmin}
  secret-key: ${MINIO_SECRET_KEY:minioadmin}
  buckets:
    uploads: uploads
    results: results
    format-samples: format-samples
    backups: backups

data-engine:
  base-url: ${DATA_ENGINE_URL:http://data-engine:8000}
  connect-timeout-ms: 2000
  read-timeout-ms: 5000

springdoc:
  swagger-ui:
    path: /swagger-ui.html
```

- [ ] **Step 2.4: Create `V1__users.sql`**

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email         CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

CREATE INDEX users_created_at ON users(created_at DESC);
```

- [ ] **Step 2.5: Create `V2__sessions.sql`**

```sql
CREATE TABLE sessions (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash   TEXT NOT NULL UNIQUE,
  issued_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at   TIMESTAMPTZ NOT NULL,
  revoked_at   TIMESTAMPTZ
);

CREATE INDEX sessions_user_id ON sessions(user_id);
CREATE INDEX sessions_active ON sessions(expires_at) WHERE revoked_at IS NULL;
```

- [ ] **Step 2.6: Create `application-test.yml`**

```yaml
spring:
  data:
    redis:
      host: localhost
      port: 6379
  autoconfigure:
    exclude:
      - org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration
      - org.springframework.boot.autoconfigure.data.redis.RedisRepositoriesAutoConfiguration
auth:
  jwt:
    secret: test-secret-test-secret-test-secret-32bytes
    ttl-seconds: 3600
minio:
  endpoint: http://localhost:9000
  access-key: test
  secret-key: testtest
```

- [ ] **Step 2.7: Add a minimal `GatewayApplication.java` so Spring boots**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/GatewayApplication.java`:

```java
package io.filternarrange.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

- [ ] **Step 2.8: Run the migration test**

Run: `cd apps/gateway && ./gradlew test --tests "*MigrationTest"`
Expected: PASS — both `users` and `sessions` tables exist.

- [ ] **Step 2.9: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): Flyway V1 users + V2 sessions; Hikari pool sized for dev

Closes #TBD"
```

---

## Task 3: Gateway — JWT auth (signup / login / me)

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/User.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/UserRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UserEntity.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UserJpaRepository.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JpaUserRepositoryAdapter.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtAuthFilter.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/SecurityConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/CurrentUser.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/auth/AuthService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/auth/Credentials.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/AuthController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/dto/*`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/auth/AuthControllerIT.java`

- [ ] **Step 3.1: Write the failing auth integration test**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/api/auth/AuthControllerIT.java`:

```java
package io.filternarrange.gateway.api.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class AuthControllerIT {

    @Container
    static PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
    }

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    @Test
    void signup_then_login_then_me() throws Exception {
        String signup = """
            {"email":"a@b.co","password":"hunter2hunter2","displayName":"A"}""";
        String body = mvc.perform(post("/api/v1/auth/signup")
                .contentType(MediaType.APPLICATION_JSON).content(signup))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.token").isString())
            .andReturn().getResponse().getContentAsString();
        String token = json.readTree(body).get("token").asText();
        assertThat(token).isNotBlank();

        mvc.perform(post("/api/v1/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"email":"a@b.co","password":"hunter2hunter2"}"""))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.token").isString());

        mvc.perform(get("/api/v1/auth/me").header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.email").value("a@b.co"));
    }

    @Test
    void me_without_token_is_401() throws Exception {
        mvc.perform(get("/api/v1/auth/me")).andExpect(status().isUnauthorized());
    }
}
```

- [ ] **Step 3.2: Run the test — expect failure**

Run: `cd apps/gateway && ./gradlew test --tests AuthControllerIT`
Expected: FAIL — no endpoint defined yet.

- [ ] **Step 3.3: Create domain `User` + port**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/User.java`:

```java
package io.filternarrange.gateway.domain.user;

import java.time.Instant;
import java.util.UUID;

public record User(UUID id, String email, String passwordHash, String displayName,
                   Instant createdAt, Instant lastLoginAt) {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/domain/user/UserRepository.java`:

```java
package io.filternarrange.gateway.domain.user;

import java.util.Optional;
import java.util.UUID;

public interface UserRepository {
    User save(User user);
    Optional<User> findByEmail(String email);
    Optional<User> findById(UUID id);
}
```

- [ ] **Step 3.4: Create JPA entity + adapter**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UserEntity.java`:

```java
package io.filternarrange.gateway.infrastructure.persistence;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "users")
public class UserEntity {
    @Id
    private UUID id;
    @Column(nullable = false, unique = true, columnDefinition = "citext")
    private String email;
    @Column(name = "password_hash", nullable = false)
    private String passwordHash;
    @Column(name = "display_name")
    private String displayName;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;
    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    public UserEntity() {}
    public UserEntity(UUID id, String email, String passwordHash, String displayName,
                      Instant createdAt, Instant lastLoginAt) {
        this.id = id; this.email = email; this.passwordHash = passwordHash;
        this.displayName = displayName; this.createdAt = createdAt; this.lastLoginAt = lastLoginAt;
    }
    public UUID getId() { return id; }
    public String getEmail() { return email; }
    public String getPasswordHash() { return passwordHash; }
    public String getDisplayName() { return displayName; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getLastLoginAt() { return lastLoginAt; }
    public void setLastLoginAt(Instant t) { this.lastLoginAt = t; }
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UserJpaRepository.java`:

```java
package io.filternarrange.gateway.infrastructure.persistence;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import java.util.UUID;

public interface UserJpaRepository extends JpaRepository<UserEntity, UUID> {
    Optional<UserEntity> findByEmailIgnoreCase(String email);
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/JpaUserRepositoryAdapter.java`:

```java
package io.filternarrange.gateway.infrastructure.persistence;

import io.filternarrange.gateway.domain.user.User;
import io.filternarrange.gateway.domain.user.UserRepository;
import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.UUID;

@Component
public class JpaUserRepositoryAdapter implements UserRepository {

    private final UserJpaRepository jpa;
    public JpaUserRepositoryAdapter(UserJpaRepository jpa) { this.jpa = jpa; }

    @Override public User save(User u) {
        UserEntity e = new UserEntity(
            u.id(), u.email(), u.passwordHash(), u.displayName(),
            u.createdAt(), u.lastLoginAt());
        UserEntity saved = jpa.save(e);
        return toDomain(saved);
    }
    @Override public Optional<User> findByEmail(String email) {
        return jpa.findByEmailIgnoreCase(email).map(this::toDomain);
    }
    @Override public Optional<User> findById(UUID id) {
        return jpa.findById(id).map(this::toDomain);
    }
    private User toDomain(UserEntity e) {
        return new User(e.getId(), e.getEmail(), e.getPasswordHash(), e.getDisplayName(),
            e.getCreatedAt(), e.getLastLoginAt());
    }
}
```

- [ ] **Step 3.5: Create JwtService + JwtAuthFilter + SecurityConfig**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtService.java`:

```java
package io.filternarrange.gateway.platform.auth;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;
import java.util.UUID;

@Component
public class JwtService {

    private final SecretKey key;
    private final Duration ttl;

    public JwtService(@Value("${auth.jwt.secret}") String secret,
                      @Value("${auth.jwt.ttl-seconds}") long ttlSeconds) {
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.ttl = Duration.ofSeconds(ttlSeconds);
    }

    public String issue(UUID userId, String email) {
        Instant now = Instant.now();
        return Jwts.builder()
            .subject(userId.toString())
            .claim("email", email)
            .issuedAt(Date.from(now))
            .expiration(Date.from(now.plus(ttl)))
            .signWith(key)
            .compact();
    }

    public UUID verify(String token) {
        var jws = Jwts.parser().verifyWith(key).build().parseSignedClaims(token);
        return UUID.fromString(jws.getPayload().getSubject());
    }
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/JwtAuthFilter.java`:

```java
package io.filternarrange.gateway.platform.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;
import java.util.UUID;

@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtService jwt;
    public JwtAuthFilter(JwtService jwt) { this.jwt = jwt; }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String auth = req.getHeader("Authorization");
        if (auth != null && auth.startsWith("Bearer ")) {
            try {
                UUID userId = jwt.verify(auth.substring(7));
                var token = new UsernamePasswordAuthenticationToken(
                    userId, null, List.of());
                SecurityContextHolder.getContext().setAuthentication(token);
            } catch (Exception ignored) { /* fall through unauthenticated */ }
        }
        chain.doFilter(req, res);
    }
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/SecurityConfig.java`:

```java
package io.filternarrange.gateway.platform.auth;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http, JwtAuthFilter jwt) throws Exception {
        http
            .csrf(c -> c.disable())
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(a -> a
                .requestMatchers("/api/v1/auth/signup", "/api/v1/auth/login").permitAll()
                .requestMatchers("/actuator/**", "/v3/api-docs/**", "/swagger-ui/**", "/swagger-ui.html").permitAll()
                .anyRequest().authenticated())
            .addFilterBefore(jwt, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/CurrentUser.java`:

```java
package io.filternarrange.gateway.platform.auth;

import org.springframework.security.core.context.SecurityContextHolder;
import java.util.UUID;

public final class CurrentUser {
    private CurrentUser() {}
    public static UUID id() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || auth.getPrincipal() == null) throw new IllegalStateException("no auth");
        return (UUID) auth.getPrincipal();
    }
}
```

- [ ] **Step 3.6: Create AuthService + Credentials**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/application/auth/Credentials.java`:

```java
package io.filternarrange.gateway.application.auth;

public record Credentials(String email, String password, String displayName) {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/application/auth/AuthService.java`:

```java
package io.filternarrange.gateway.application.auth;

import io.filternarrange.gateway.domain.user.User;
import io.filternarrange.gateway.domain.user.UserRepository;
import io.filternarrange.gateway.platform.auth.JwtService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.UUID;

@Service
public class AuthService {

    private final UserRepository users;
    private final PasswordEncoder enc;
    private final JwtService jwt;

    public AuthService(UserRepository users, PasswordEncoder enc, JwtService jwt) {
        this.users = users; this.enc = enc; this.jwt = jwt;
    }

    public record Authenticated(String token, User user) {}

    public Authenticated signup(Credentials c) {
        if (users.findByEmail(c.email()).isPresent())
            throw new IllegalStateException("EMAIL_TAKEN");
        User u = new User(UUID.randomUUID(), c.email(), enc.encode(c.password()),
            c.displayName(), Instant.now(), null);
        u = users.save(u);
        return new Authenticated(jwt.issue(u.id(), u.email()), u);
    }

    public Authenticated login(Credentials c) {
        User u = users.findByEmail(c.email()).orElseThrow(() -> new IllegalStateException("BAD_CREDS"));
        if (!enc.matches(c.password(), u.passwordHash()))
            throw new IllegalStateException("BAD_CREDS");
        return new Authenticated(jwt.issue(u.id(), u.email()), u);
    }

    public User requireUser(UUID id) {
        return users.findById(id).orElseThrow(() -> new IllegalStateException("NO_USER"));
    }
}
```

- [ ] **Step 3.7: Create AuthController and DTOs**

Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/dto/SignupRequest.java`:

```java
package io.filternarrange.gateway.api.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record SignupRequest(
    @Email @NotBlank String email,
    @NotBlank @Size(min = 8) String password,
    String displayName) {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/dto/LoginRequest.java`:

```java
package io.filternarrange.gateway.api.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record LoginRequest(@Email @NotBlank String email, @NotBlank String password) {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/dto/AuthResponse.java`:

```java
package io.filternarrange.gateway.api.auth.dto;

public record AuthResponse(String token, UserDto user) {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/dto/UserDto.java`:

```java
package io.filternarrange.gateway.api.auth.dto;

import io.filternarrange.gateway.domain.user.User;
import java.util.UUID;

public record UserDto(UUID id, String email, String displayName) {
    public static UserDto of(User u) { return new UserDto(u.id(), u.email(), u.displayName()); }
}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/api/auth/AuthController.java`:

```java
package io.filternarrange.gateway.api.auth;

import io.filternarrange.gateway.api.auth.dto.*;
import io.filternarrange.gateway.application.auth.AuthService;
import io.filternarrange.gateway.application.auth.Credentials;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService auth;
    public AuthController(AuthService auth) { this.auth = auth; }

    @PostMapping("/signup")
    public AuthResponse signup(@Valid @RequestBody SignupRequest r) {
        var a = auth.signup(new Credentials(r.email(), r.password(), r.displayName()));
        return new AuthResponse(a.token(), UserDto.of(a.user()));
    }

    @PostMapping("/login")
    public AuthResponse login(@Valid @RequestBody LoginRequest r) {
        var a = auth.login(new Credentials(r.email(), r.password(), null));
        return new AuthResponse(a.token(), UserDto.of(a.user()));
    }

    @GetMapping("/me")
    public UserDto me() {
        return UserDto.of(auth.requireUser(CurrentUser.id()));
    }
}
```

- [ ] **Step 3.8: Run AuthControllerIT — should pass**

Run: `cd apps/gateway && ./gradlew test --tests AuthControllerIT`
Expected: PASS.

- [ ] **Step 3.9: Commit**

```bash
git add apps/gateway/src
git commit -m "feat(gateway): Spring-JWT auth with signup/login/me

Closes #TBD"
```

---

## Task 4: Gateway — Error envelope + global exception handler

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/ErrorEnvelope.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/AppException.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/GlobalExceptionHandler.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/error/TraceIdFilter.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/error/GlobalExceptionHandlerTest.java`

- [ ] **Step 4.1: Write the failing handler test**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/platform/error/GlobalExceptionHandlerTest.java`:

```java
package io.filternarrange.gateway.platform.error;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class GlobalExceptionHandlerTest {

    @Container
    static PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
    }

    @Autowired MockMvc mvc;

    @Test
    void invalidBodyYieldsEnvelope() throws Exception {
        mvc.perform(post("/api/v1/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\":\"bad\",\"password\":\"x\"}"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
            .andExpect(jsonPath("$.traceId").isString())
            .andExpect(jsonPath("$.message").isString());
    }
}
```

- [ ] **Step 4.2: Run — expect failure (no envelope yet)**

Run: `cd apps/gateway && ./gradlew test --tests GlobalExceptionHandlerTest`
Expected: FAIL — body shape mismatch.

- [ ] **Step 4.3: Implement `ErrorEnvelope`**

```java
package io.filternarrange.gateway.platform.error;

public record ErrorEnvelope(String code, String pluginId, String message, String traceId) {
    public static ErrorEnvelope of(String code, String message, String traceId) {
        return new ErrorEnvelope(code, null, message, traceId);
    }
}
```

- [ ] **Step 4.4: Implement `AppException`**

```java
package io.filternarrange.gateway.platform.error;

public class AppException extends RuntimeException {
    private final String code;
    private final int httpStatus;
    public AppException(String code, int httpStatus, String message) {
        super(message); this.code = code; this.httpStatus = httpStatus;
    }
    public String code() { return code; }
    public int httpStatus() { return httpStatus; }
}
```

- [ ] **Step 4.5: Implement `TraceIdFilter`**

```java
package io.filternarrange.gateway.platform.error;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {
    public static final String KEY = "traceId";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String existing = req.getHeader("X-Trace-Id");
        String id = (existing != null && !existing.isBlank()) ? existing : UUID.randomUUID().toString();
        MDC.put(KEY, id);
        res.setHeader("X-Trace-Id", id);
        try { chain.doFilter(req, res); } finally { MDC.remove(KEY); }
    }

    public static String current() {
        String v = MDC.get(KEY);
        return v == null ? "unknown" : v;
    }
}
```

- [ ] **Step 4.6: Implement `GlobalExceptionHandler`**

```java
package io.filternarrange.gateway.platform.error;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.stream.Collectors;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorEnvelope> validation(MethodArgumentNotValidException ex) {
        String msg = ex.getBindingResult().getFieldErrors().stream()
            .map(f -> f.getField() + ": " + f.getDefaultMessage())
            .collect(Collectors.joining("; "));
        return ResponseEntity.status(HttpStatus.BAD_REQUEST)
            .body(ErrorEnvelope.of("VALIDATION_FAILED", msg, TraceIdFilter.current()));
    }

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ErrorEnvelope> app(AppException ex) {
        return ResponseEntity.status(ex.httpStatus())
            .body(ErrorEnvelope.of(ex.code(), ex.getMessage(), TraceIdFilter.current()));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<ErrorEnvelope> illegalState(IllegalStateException ex) {
        String m = ex.getMessage();
        return switch (m) {
            case "EMAIL_TAKEN" -> ResponseEntity.status(HttpStatus.CONFLICT)
                .body(ErrorEnvelope.of("EMAIL_TAKEN", "Email already registered", TraceIdFilter.current()));
            case "BAD_CREDS" -> ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ErrorEnvelope.of("BAD_CREDS", "Invalid credentials", TraceIdFilter.current()));
            case "NO_USER" -> ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(ErrorEnvelope.of("NO_USER", "User not found", TraceIdFilter.current()));
            default -> ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ErrorEnvelope.of("INTERNAL", m, TraceIdFilter.current()));
        };
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorEnvelope> fallback(Exception ex) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(ErrorEnvelope.of("INTERNAL", ex.getMessage(), TraceIdFilter.current()));
    }
}
```

- [ ] **Step 4.7: Run handler test — must pass**

Run: `cd apps/gateway && ./gradlew test --tests GlobalExceptionHandlerTest`
Expected: PASS.

- [ ] **Step 4.8: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): structured error envelope { code, message, traceId }

Closes #TBD"
```

---

## Task 5: Gateway — MinIO adapter + bucket bootstrap

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/storage/ObjectStore.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/storage/StoredObject.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/storage/MinioObjectStore.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/storage/MinioConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/storage/BucketBootstrap.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/storage/MinioObjectStoreIT.java`

- [ ] **Step 5.1: Write the failing MinIO IT**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/storage/MinioObjectStoreIT.java`:

```java
package io.filternarrange.gateway.infrastructure.storage;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.io.ByteArrayInputStream;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@Testcontainers
class MinioObjectStoreIT {

    @Container static PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");
    @Container static MinIOContainer MINIO = new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired ObjectStore store;

    @Test
    void putAndGet_roundtrips() {
        byte[] data = "hello".getBytes();
        String key = "uploads/users/test/x.csv";
        store.put("uploads", key, new ByteArrayInputStream(data), data.length, "text/csv");
        String url = store.presignedGet("uploads", key, 60);
        assertThat(url).contains(key);
    }
}
```

- [ ] **Step 5.2: Run — expect failure**

Run: `cd apps/gateway && ./gradlew test --tests MinioObjectStoreIT`
Expected: FAIL — `ObjectStore` bean missing.

- [ ] **Step 5.3: Create `ObjectStore` port + record**

```java
package io.filternarrange.gateway.domain.storage;

public record StoredObject(String bucket, String key, long sizeBytes, String contentType) {}
```

```java
package io.filternarrange.gateway.domain.storage;

import java.io.InputStream;

public interface ObjectStore {
    StoredObject put(String bucket, String key, InputStream data, long size, String contentType);
    String presignedGet(String bucket, String key, long expirySeconds);
    boolean exists(String bucket, String key);
    void ensureBucket(String bucket);
}
```

- [ ] **Step 5.4: Create `MinioConfig`**

```java
package io.filternarrange.gateway.platform.storage;

import io.minio.MinioClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MinioConfig {
    @Bean
    public MinioClient minioClient(
            @Value("${minio.endpoint}") String endpoint,
            @Value("${minio.access-key}") String access,
            @Value("${minio.secret-key}") String secret) {
        return MinioClient.builder().endpoint(endpoint).credentials(access, secret).build();
    }
}
```

- [ ] **Step 5.5: Implement `MinioObjectStore`**

```java
package io.filternarrange.gateway.infrastructure.storage;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.domain.storage.StoredObject;
import io.minio.*;
import io.minio.http.Method;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.util.concurrent.TimeUnit;

@Component
public class MinioObjectStore implements ObjectStore {

    private final MinioClient client;
    public MinioObjectStore(MinioClient client) { this.client = client; }

    @Override
    public StoredObject put(String bucket, String key, InputStream data, long size, String contentType) {
        try {
            ensureBucket(bucket);
            client.putObject(PutObjectArgs.builder()
                .bucket(bucket).object(key)
                .stream(data, size, -1)
                .contentType(contentType)
                .build());
            return new StoredObject(bucket, key, size, contentType);
        } catch (Exception e) {
            throw new RuntimeException("minio put failed: " + e.getMessage(), e);
        }
    }

    @Override
    public String presignedGet(String bucket, String key, long expirySeconds) {
        try {
            return client.getPresignedObjectUrl(GetPresignedObjectUrlArgs.builder()
                .method(Method.GET).bucket(bucket).object(key)
                .expiry((int) expirySeconds, TimeUnit.SECONDS)
                .build());
        } catch (Exception e) {
            throw new RuntimeException("minio presign failed: " + e.getMessage(), e);
        }
    }

    @Override
    public boolean exists(String bucket, String key) {
        try {
            client.statObject(StatObjectArgs.builder().bucket(bucket).object(key).build());
            return true;
        } catch (Exception e) { return false; }
    }

    @Override
    public void ensureBucket(String bucket) {
        try {
            boolean found = client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
            if (!found) client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
        } catch (Exception e) {
            throw new RuntimeException("minio ensure bucket: " + e.getMessage(), e);
        }
    }
}
```

- [ ] **Step 5.6: Implement `BucketBootstrap`**

```java
package io.filternarrange.gateway.platform.storage;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class BucketBootstrap {

    private final ObjectStore store;
    private final String uploads;
    private final String results;
    private final String samples;
    private final String backups;

    public BucketBootstrap(ObjectStore store,
                           @Value("${minio.buckets.uploads}") String uploads,
                           @Value("${minio.buckets.results}") String results,
                           @Value("${minio.buckets.format-samples}") String samples,
                           @Value("${minio.buckets.backups}") String backups) {
        this.store = store; this.uploads = uploads; this.results = results;
        this.samples = samples; this.backups = backups;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void bootstrap() {
        for (String b : new String[]{uploads, results, samples, backups}) store.ensureBucket(b);
    }
}
```

- [ ] **Step 5.7: Run IT — must pass**

Run: `cd apps/gateway && ./gradlew test --tests MinioObjectStoreIT`
Expected: PASS.

- [ ] **Step 5.8: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): MinIO ObjectStore adapter + bucket bootstrap

Closes #TBD"
```

---

## Task 6: Gateway — Data-engine HTTP client + circuit-breaker skeleton

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/dataengine/DataEngineClient.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/domain/dataengine/EngineDtos.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/http/DataEngineHttpClient.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/http/RestClientConfig.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/http/DataEngineHttpClientTest.java`

- [ ] **Step 6.1: Write the failing client test using `MockRestServiceServer`**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/infrastructure/http/DataEngineHttpClientTest.java`:

```java
package io.filternarrange.gateway.infrastructure.http;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class DataEngineHttpClientTest {

    DataEngineHttpClient client;
    MockRestServiceServer server;
    ObjectMapper json = new ObjectMapper();

    @BeforeEach
    void setup() {
        var builder = RestClient.builder().baseUrl("http://data-engine:8000");
        server = MockRestServiceServer.bindTo(builder).build();
        client = new DataEngineHttpClient(builder.build(), json);
    }

    @Test
    void detect_callsEngine() throws Exception {
        server.expect(requestTo("http://data-engine:8000/detect"))
            .andExpect(content().contentType(MediaType.APPLICATION_JSON))
            .andRespond(withSuccess("""
                {"format":"csv","confidence":0.97,"schema":[{"name":"a","type":"string","nullable":false}]}
                """, MediaType.APPLICATION_JSON));
        var res = client.detect(new EngineDtos.RefRequest("uploads/u/abc.csv"));
        assertThat(res.format()).isEqualTo("csv");
        assertThat(res.confidence()).isEqualTo(0.97);
        assertThat(res.schema()).hasSize(1);
    }

    @Test
    void filter_callsEngine() {
        server.expect(requestTo("http://data-engine:8000/filter"))
            .andRespond(withSuccess("""
                {"schema":[{"name":"a","type":"string","nullable":false}],"rows":[{"a":"1"}]}
                """, MediaType.APPLICATION_JSON));
        var res = client.filter(new EngineDtos.FilterRequest(
            "uploads/u/abc.csv",
            new EngineDtos.ColumnFilterSpec("column", List.of("a")),
            20));
        assertThat(res.rows()).hasSize(1);
        assertThat(res.rows().get(0)).containsEntry("a", "1");
    }
}
```

- [ ] **Step 6.2: Run — expect failure**

Run: `cd apps/gateway && ./gradlew test --tests DataEngineHttpClientTest`
Expected: FAIL — class missing.

- [ ] **Step 6.3: Create `EngineDtos`**

```java
package io.filternarrange.gateway.domain.dataengine;

import java.util.List;
import java.util.Map;

public final class EngineDtos {
    private EngineDtos() {}

    public record Column(String name, String type, boolean nullable) {}

    public record RefRequest(String ref) {}

    public record ColumnFilterSpec(String kind, List<String> keep) {}

    public record FilterRequest(String ref, ColumnFilterSpec filter, int sampleSize) {}

    public record ConvertRequest(String ref, ColumnFilterSpec filter, String outputFormat) {}

    public record DetectResult(String format, double confidence, List<Column> schema) {}

    public record FilterResult(List<Column> schema, List<Map<String, Object>> rows) {}

    public record ConvertResult(String resultRef) {}
}
```

- [ ] **Step 6.4: Create `DataEngineClient` port**

```java
package io.filternarrange.gateway.domain.dataengine;

public interface DataEngineClient {
    EngineDtos.DetectResult detect(EngineDtos.RefRequest req);
    EngineDtos.FilterResult filter(EngineDtos.FilterRequest req);
    EngineDtos.ConvertResult convert(EngineDtos.ConvertRequest req);
}
```

- [ ] **Step 6.5: Create RestClient config**

```java
package io.filternarrange.gateway.platform.http;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfig {
    @Bean
    public RestClient dataEngineRestClient(
            @Value("${data-engine.base-url}") String baseUrl,
            @Value("${data-engine.connect-timeout-ms}") int connectTimeout,
            @Value("${data-engine.read-timeout-ms}") int readTimeout) {
        var f = new SimpleClientHttpRequestFactory();
        f.setConnectTimeout(connectTimeout);
        f.setReadTimeout(readTimeout);
        return RestClient.builder().baseUrl(baseUrl).requestFactory(f).build();
    }
}
```

- [ ] **Step 6.6: Implement `DataEngineHttpClient`**

```java
package io.filternarrange.gateway.infrastructure.http;

import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class DataEngineHttpClient implements DataEngineClient {

    private final RestClient rest;
    private final ObjectMapper json;

    public DataEngineHttpClient(RestClient dataEngineRestClient, ObjectMapper json) {
        this.rest = dataEngineRestClient; this.json = json;
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.DetectResult detect(EngineDtos.RefRequest req) {
        return rest.post().uri("/detect").body(req).retrieve().body(EngineDtos.DetectResult.class);
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.FilterResult filter(EngineDtos.FilterRequest req) {
        return rest.post().uri("/filter").body(req).retrieve().body(EngineDtos.FilterResult.class);
    }

    @CircuitBreaker(name = "dataEngine")
    @Override
    public EngineDtos.ConvertResult convert(EngineDtos.ConvertRequest req) {
        return rest.post().uri("/convert").body(req).retrieve().body(EngineDtos.ConvertResult.class);
    }
}
```

- [ ] **Step 6.7: Add Resilience4j config to `application.yml`**

Append:

```yaml
resilience4j:
  circuitbreaker:
    instances:
      dataEngine:
        sliding-window-size: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        minimum-number-of-calls: 5
        permitted-number-of-calls-in-half-open-state: 2
```

- [ ] **Step 6.8: Run client test — must pass**

Run: `cd apps/gateway && ./gradlew test --tests DataEngineHttpClientTest`
Expected: PASS.

- [ ] **Step 6.9: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): data-engine HTTP client with Resilience4j breaker

Closes #TBD"
```

---

## Task 7: Gateway — Upload, Detect, Filter, Convert, Download controllers

**Files:**
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/upload/UploadService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/pipeline/PipelineService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/application/download/DownloadService.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/upload/dto/UploadResponse.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/upload/UploadController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/*`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/PipelineController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/api/download/DownloadController.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UploadRecordEntity.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/UploadRecordRepository.java`
- Create: `apps/gateway/src/main/resources/db/migration/V3__uploads_and_results.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/api/pipeline/PipelineControllerIT.java`

- [ ] **Step 7.1: Write the failing pipeline IT**

Create `apps/gateway/src/test/java/io/filternarrange/gateway/api/pipeline/PipelineControllerIT.java`:

```java
package io.filternarrange.gateway.api.pipeline;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.MinIOContainer;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.util.List;
import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class PipelineControllerIT {

    @Container static PostgreSQLContainer<?> PG = new PostgreSQLContainer<>("postgres:16-alpine");
    @Container static MinIOContainer MINIO = new MinIOContainer("minio/minio:RELEASE.2024-08-29T01-40-52Z");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", PG::getUsername);
        r.add("spring.datasource.password", PG::getPassword);
        r.add("minio.endpoint", MINIO::getS3URL);
        r.add("minio.access-key", MINIO::getUserName);
        r.add("minio.secret-key", MINIO::getPassword);
    }

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;
    @MockBean DataEngineClient engine;

    private String authToken() throws Exception {
        String body = mvc.perform(post("/api/v1/auth/signup")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"email":"p@x.co","password":"hunter2hunter2"}"""))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return json.readTree(body).get("token").asText();
    }

    @Test
    void uploadDetectFilterConvertDownload() throws Exception {
        String token = authToken();
        var file = new MockMultipartFile("file", "x.csv", "text/csv",
            "name,age\nA,1\nB,2".getBytes());
        String upRes = mvc.perform(multipart("/api/v1/upload").file(file)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.uploadId").isString())
            .andReturn().getResponse().getContentAsString();
        JsonNode up = json.readTree(upRes);
        String uploadId = up.get("uploadId").asText();

        Mockito.when(engine.detect(Mockito.any())).thenReturn(
            new EngineDtos.DetectResult("csv", 0.95, List.of(
                new EngineDtos.Column("name", "string", false),
                new EngineDtos.Column("age", "integer", false))));
        mvc.perform(post("/api/v1/detect")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s"}""".formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.format").value("csv"));

        Mockito.when(engine.filter(Mockito.any())).thenReturn(
            new EngineDtos.FilterResult(
                List.of(new EngineDtos.Column("name", "string", false)),
                List.of(Map.of("name", "A"), Map.of("name", "B"))));
        mvc.perform(post("/api/v1/filter/preview")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s","filter":{"kind":"column","keep":["name"]},"sampleSize":10}
                    """.formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.rows.length()").value(2));

        Mockito.when(engine.convert(Mockito.any())).thenReturn(
            new EngineDtos.ConvertResult("results/users/x/abc.json"));
        String convRes = mvc.perform(post("/api/v1/convert")
                .header("Authorization", "Bearer " + token)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"uploadId":"%s","filter":{"kind":"column","keep":["name"]},"outputFormat":"json"}
                    """.formatted(uploadId)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.resultId").isString())
            .andReturn().getResponse().getContentAsString();
        String resultId = json.readTree(convRes).get("resultId").asText();

        mvc.perform(get("/api/v1/download/" + resultId)
                .header("Authorization", "Bearer " + token))
            .andExpect(status().is3xxRedirection());
    }
}
```

- [ ] **Step 7.2: Run — expect failure**

Run: `cd apps/gateway && ./gradlew test --tests PipelineControllerIT`
Expected: FAIL — endpoints missing.

- [ ] **Step 7.3: Add `V3__uploads_and_results.sql`**

```sql
CREATE TABLE uploads (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id),
  ref          TEXT NOT NULL,
  size_bytes   BIGINT NOT NULL,
  content_type TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX uploads_user_id ON uploads(user_id, created_at DESC);

CREATE TABLE results (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id      UUID NOT NULL REFERENCES users(id),
  upload_id    UUID REFERENCES uploads(id),
  ref          TEXT NOT NULL,
  output_format TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX results_user_id ON results(user_id, created_at DESC);
```

- [ ] **Step 7.4: Create `UploadRecordEntity` + repo**

```java
package io.filternarrange.gateway.infrastructure.persistence;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "uploads")
public class UploadRecordEntity {
    @Id
    private UUID id;
    @Column(name = "user_id", nullable = false)
    private UUID userId;
    @Column(nullable = false)
    private String ref;
    @Column(name = "size_bytes", nullable = false)
    private long sizeBytes;
    @Column(name = "content_type", nullable = false)
    private String contentType;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public UploadRecordEntity() {}
    public UploadRecordEntity(UUID id, UUID userId, String ref, long sizeBytes, String contentType, Instant createdAt) {
        this.id = id; this.userId = userId; this.ref = ref;
        this.sizeBytes = sizeBytes; this.contentType = contentType; this.createdAt = createdAt;
    }
    public UUID getId() { return id; }
    public UUID getUserId() { return userId; }
    public String getRef() { return ref; }
    public long getSizeBytes() { return sizeBytes; }
    public String getContentType() { return contentType; }
    public Instant getCreatedAt() { return createdAt; }
}
```

```java
package io.filternarrange.gateway.infrastructure.persistence;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface UploadRecordRepository extends JpaRepository<UploadRecordEntity, UUID> {}
```

Create `apps/gateway/src/main/java/io/filternarrange/gateway/infrastructure/persistence/ResultRecordEntity.java`:

```java
package io.filternarrange.gateway.infrastructure.persistence;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "results")
public class ResultRecordEntity {
    @Id
    private UUID id;
    @Column(name = "user_id", nullable = false)
    private UUID userId;
    @Column(name = "upload_id")
    private UUID uploadId;
    @Column(nullable = false)
    private String ref;
    @Column(name = "output_format", nullable = false)
    private String outputFormat;
    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    public ResultRecordEntity() {}
    public ResultRecordEntity(UUID id, UUID userId, UUID uploadId, String ref, String outputFormat, Instant createdAt) {
        this.id = id; this.userId = userId; this.uploadId = uploadId;
        this.ref = ref; this.outputFormat = outputFormat; this.createdAt = createdAt;
    }
    public UUID getId() { return id; }
    public UUID getUserId() { return userId; }
    public UUID getUploadId() { return uploadId; }
    public String getRef() { return ref; }
    public String getOutputFormat() { return outputFormat; }
    public Instant getCreatedAt() { return createdAt; }
}
```

```java
package io.filternarrange.gateway.infrastructure.persistence;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

public interface ResultRecordRepository extends JpaRepository<ResultRecordEntity, UUID> {}
```

- [ ] **Step 7.5: Create `UploadService`**

```java
package io.filternarrange.gateway.application.upload;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.time.Instant;
import java.util.UUID;

@Service
public class UploadService {

    private final ObjectStore store;
    private final UploadRecordRepository uploads;
    private final String bucket;

    public UploadService(ObjectStore store, UploadRecordRepository uploads,
                         @Value("${minio.buckets.uploads}") String bucket) {
        this.store = store; this.uploads = uploads; this.bucket = bucket;
    }

    public record Uploaded(UUID id, String ref, long size) {}

    public Uploaded upload(UUID userId, MultipartFile file) throws IOException {
        String ext = extensionOf(file.getOriginalFilename());
        UUID id = UUID.randomUUID();
        String key = "users/%s/%s%s".formatted(userId, id, ext);
        store.put(bucket, key, file.getInputStream(), file.getSize(),
            file.getContentType() != null ? file.getContentType() : "application/octet-stream");
        String ref = bucket + "/" + key;
        UploadRecordEntity e = new UploadRecordEntity(id, userId, ref, file.getSize(),
            file.getContentType() != null ? file.getContentType() : "application/octet-stream", Instant.now());
        uploads.save(e);
        return new Uploaded(id, ref, file.getSize());
    }

    public UploadRecordEntity require(UUID id, UUID userId) {
        UploadRecordEntity e = uploads.findById(id).orElseThrow(() ->
            new io.filternarrange.gateway.platform.error.AppException("NO_UPLOAD", 404, "Upload not found"));
        if (!e.getUserId().equals(userId))
            throw new io.filternarrange.gateway.platform.error.AppException("FORBIDDEN", 403, "Not your upload");
        return e;
    }

    private String extensionOf(String name) {
        if (name == null) return "";
        int dot = name.lastIndexOf('.');
        return dot < 0 ? "" : name.substring(dot);
    }
}
```

- [ ] **Step 7.6: Create `PipelineService`**

```java
package io.filternarrange.gateway.application.pipeline;

import io.filternarrange.gateway.application.upload.UploadService;
import io.filternarrange.gateway.domain.dataengine.DataEngineClient;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordRepository;
import io.filternarrange.gateway.infrastructure.persistence.UploadRecordEntity;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
public class PipelineService {

    private final UploadService uploads;
    private final DataEngineClient engine;
    private final ResultRecordRepository results;

    public PipelineService(UploadService uploads, DataEngineClient engine, ResultRecordRepository results) {
        this.uploads = uploads; this.engine = engine; this.results = results;
    }

    public EngineDtos.DetectResult detect(UUID userId, UUID uploadId) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.detect(new EngineDtos.RefRequest(u.getRef()));
    }

    public EngineDtos.FilterResult filterPreview(UUID userId, UUID uploadId,
                                                 List<String> keep, int sampleSize) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        return engine.filter(new EngineDtos.FilterRequest(
            u.getRef(),
            new EngineDtos.ColumnFilterSpec("column", keep),
            sampleSize));
    }

    public record Converted(UUID resultId, String ref) {}

    public Converted convert(UUID userId, UUID uploadId, List<String> keep, String outputFormat) {
        UploadRecordEntity u = uploads.require(uploadId, userId);
        EngineDtos.ConvertResult r = engine.convert(new EngineDtos.ConvertRequest(
            u.getRef(),
            new EngineDtos.ColumnFilterSpec("column", keep),
            outputFormat));
        UUID id = UUID.randomUUID();
        results.save(new ResultRecordEntity(id, userId, u.getId(), r.resultRef(), outputFormat, Instant.now()));
        return new Converted(id, r.resultRef());
    }
}
```

- [ ] **Step 7.7: Create `DownloadService`**

```java
package io.filternarrange.gateway.application.download;

import io.filternarrange.gateway.domain.storage.ObjectStore;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordEntity;
import io.filternarrange.gateway.infrastructure.persistence.ResultRecordRepository;
import io.filternarrange.gateway.platform.error.AppException;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
public class DownloadService {

    private final ResultRecordRepository results;
    private final ObjectStore store;

    public DownloadService(ResultRecordRepository results, ObjectStore store) {
        this.results = results; this.store = store;
    }

    public String presignedUrl(UUID userId, UUID resultId) {
        ResultRecordEntity r = results.findById(resultId)
            .orElseThrow(() -> new AppException("NO_RESULT", 404, "Result not found"));
        if (!r.getUserId().equals(userId))
            throw new AppException("FORBIDDEN", 403, "Not your result");
        String ref = r.getRef();
        int slash = ref.indexOf('/');
        String bucket = ref.substring(0, slash);
        String key = ref.substring(slash + 1);
        return store.presignedGet(bucket, key, 300);
    }
}
```

- [ ] **Step 7.8: Create DTOs + controllers**

`apps/gateway/src/main/java/io/filternarrange/gateway/api/upload/dto/UploadResponse.java`:

```java
package io.filternarrange.gateway.api.upload.dto;

import java.util.UUID;
public record UploadResponse(UUID uploadId, String ref, long sizeBytes) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/upload/UploadController.java`:

```java
package io.filternarrange.gateway.api.upload;

import io.filternarrange.gateway.api.upload.dto.UploadResponse;
import io.filternarrange.gateway.application.upload.UploadService;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@RestController
@RequestMapping("/api/v1/upload")
public class UploadController {
    private final UploadService svc;
    public UploadController(UploadService svc) { this.svc = svc; }

    @PostMapping(consumes = "multipart/form-data")
    public UploadResponse upload(@RequestParam("file") MultipartFile file) throws IOException {
        var r = svc.upload(CurrentUser.id(), file);
        return new UploadResponse(r.id(), r.ref(), r.size());
    }
}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/DetectRequest.java`:

```java
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
public record DetectRequest(@NotNull UUID uploadId) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/ColumnFilterSpecDto.java`:

```java
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;
public record ColumnFilterSpecDto(@NotNull String kind, @NotEmpty List<String> keep) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/FilterPreviewRequest.java`:

```java
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.UUID;
public record FilterPreviewRequest(@NotNull UUID uploadId, @NotNull @Valid ColumnFilterSpecDto filter, Integer sampleSize) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/ConvertRequest.java`:

```java
package io.filternarrange.gateway.api.pipeline.dto;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.util.UUID;
public record ConvertRequest(@NotNull UUID uploadId,
                             @NotNull @Valid ColumnFilterSpecDto filter,
                             @NotNull @Pattern(regexp = "csv|json") String outputFormat) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/dto/ConvertResponse.java`:

```java
package io.filternarrange.gateway.api.pipeline.dto;
import java.util.UUID;
public record ConvertResponse(UUID resultId, String ref) {}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/pipeline/PipelineController.java`:

```java
package io.filternarrange.gateway.api.pipeline;

import io.filternarrange.gateway.api.pipeline.dto.*;
import io.filternarrange.gateway.application.pipeline.PipelineService;
import io.filternarrange.gateway.domain.dataengine.EngineDtos;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class PipelineController {

    private final PipelineService svc;
    public PipelineController(PipelineService svc) { this.svc = svc; }

    @PostMapping("/detect")
    public EngineDtos.DetectResult detect(@Valid @RequestBody DetectRequest r) {
        return svc.detect(CurrentUser.id(), r.uploadId());
    }

    @PostMapping("/filter/preview")
    public EngineDtos.FilterResult preview(@Valid @RequestBody FilterPreviewRequest r) {
        int n = r.sampleSize() == null ? 20 : r.sampleSize();
        return svc.filterPreview(CurrentUser.id(), r.uploadId(), r.filter().keep(), n);
    }

    @PostMapping("/convert")
    public ConvertResponse convert(@Valid @RequestBody ConvertRequest r) {
        var c = svc.convert(CurrentUser.id(), r.uploadId(), r.filter().keep(), r.outputFormat());
        return new ConvertResponse(c.resultId(), c.ref());
    }
}
```

`apps/gateway/src/main/java/io/filternarrange/gateway/api/download/DownloadController.java`:

```java
package io.filternarrange.gateway.api.download;

import io.filternarrange.gateway.application.download.DownloadService;
import io.filternarrange.gateway.platform.auth.CurrentUser;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/download")
public class DownloadController {

    private final DownloadService svc;
    public DownloadController(DownloadService svc) { this.svc = svc; }

    @GetMapping("/{resultId}")
    public ResponseEntity<Void> download(@PathVariable UUID resultId) {
        String url = svc.presignedUrl(CurrentUser.id(), resultId);
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(url)).build();
    }
}
```

- [ ] **Step 7.9: Run the pipeline IT — must pass**

Run: `cd apps/gateway && ./gradlew test --tests PipelineControllerIT`
Expected: PASS.

- [ ] **Step 7.10: Commit**

```bash
git add apps/gateway
git commit -m "feat(gateway): upload/detect/filter/convert/download controllers + V3 migration

Closes #TBD"
```

---

## Task 8: Gateway — ArchUnit layering test

**Files:**
- Create: `apps/gateway/src/test/java/io/filternarrange/gateway/architecture/LayeringTest.java`

- [ ] **Step 8.1: Write the failing arch test**

```java
package io.filternarrange.gateway.architecture;

import com.tngtech.archunit.core.importer.ImportOption;
import com.tngtech.archunit.junit.AnalyzeClasses;
import com.tngtech.archunit.junit.ArchTest;
import com.tngtech.archunit.lang.ArchRule;

import static com.tngtech.archunit.library.Architectures.layeredArchitecture;

@AnalyzeClasses(packages = "io.filternarrange.gateway",
    importOptions = ImportOption.DoNotIncludeTests.class)
class LayeringTest {

    @ArchTest
    static final ArchRule LAYERS = layeredArchitecture().consideringAllDependencies()
        .layer("Api").definedBy("io.filternarrange.gateway.api..")
        .layer("Application").definedBy("io.filternarrange.gateway.application..")
        .layer("Domain").definedBy("io.filternarrange.gateway.domain..")
        .layer("Infrastructure").definedBy("io.filternarrange.gateway.infrastructure..")
        .layer("Platform").definedBy("io.filternarrange.gateway.platform..")

        .whereLayer("Api").mayNotBeAccessedByAnyLayer()
        .whereLayer("Application").mayOnlyBeAccessedByLayers("Api")
        .whereLayer("Infrastructure").mayOnlyBeAccessedByLayers("Platform", "Application", "Api")
        .whereLayer("Domain").mayOnlyBeAccessedByLayers("Application", "Infrastructure", "Api", "Platform");
}
```

- [ ] **Step 8.2: Run — must pass**

Run: `cd apps/gateway && ./gradlew test --tests LayeringTest`
Expected: PASS.

If a real layering violation is found, the test will fail — refactor offending file rather than weakening the rule.

- [ ] **Step 8.3: Commit**

```bash
git add apps/gateway/src/test
git commit -m "test(gateway): ArchUnit layering rule

Closes #TBD"
```

---

## Task 9: Data-engine — Canonical model

**Files:**
- Modify: `apps/data-engine/pyproject.toml`
- Create: `apps/data-engine/src/filternarrange_engine/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/types.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/canonical.py`
- Test: `apps/data-engine/tests/core/test_canonical.py`

- [ ] **Step 9.1: Extend `pyproject.toml`**

```toml
[project]
name = "filternarrange-engine"
version = "0.1.0"
description = "FilterNArrange data-engine"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = [
  "fastapi==0.115.0",
  "uvicorn[standard]==0.30.6",
  "pydantic==2.9.2",
  "minio==7.2.9",
  "httpx==0.27.2",
  "python-multipart==0.0.10",
  "structlog==24.4.0",
  "typing-extensions>=4.12",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.3",
  "pytest-asyncio==0.24.0",
  "import-linter==2.1",
  "ruff==0.6.9",
  "mypy==1.11.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 9.2: Write the failing canonical-model test**

Create `apps/data-engine/tests/core/test_canonical.py`:

```python
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_engine.core.canonical import Column, TabularData, Node, TreeData


async def _aiter(rows):
    for r in rows:
        yield r


@pytest.mark.asyncio
async def test_tabular_data_iterates_rows():
    cols = [Column("name", TypeTag.STRING, False), Column("age", TypeTag.INTEGER, True)]
    data = TabularData(schema=cols, rows=_aiter([{"name": "A", "age": 1}]), meta={})
    out = [r async for r in data.rows]
    assert out == [{"name": "A", "age": 1}]
    assert data.schema[0].name == "name"
    assert data.schema[0].type is TypeTag.STRING


def test_tree_data_holds_nodes():
    leaf = Node(key="x", value=1, type=TypeTag.INTEGER, children=[])
    root = Node(key="root", value=None, type=TypeTag.NULL, children=[leaf])
    tree = TreeData(root=root, meta={"depth": 1, "total_nodes": 2})
    assert tree.root.children[0].value == 1


def test_typetag_enum_values():
    assert {t.value for t in TypeTag} == {
        "string", "number", "integer", "boolean", "datetime", "null"
    }
```

- [ ] **Step 9.3: Run — expect failure**

Run: `cd apps/data-engine && uv run pytest tests/core/test_canonical.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 9.4: Implement `types.py`**

```python
"""Canonical type tags shared by every plugin."""
from __future__ import annotations
from enum import Enum


class TypeTag(str, Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    NULL = "null"


__all__ = ["TypeTag"]
```

- [ ] **Step 9.5: Implement `canonical.py`**

```python
"""Canonical intermediate model: TabularData and TreeData."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from .types import TypeTag


@dataclass(frozen=True)
class Column:
    name: str
    type: TypeTag
    nullable: bool


@dataclass
class TabularData:
    schema: list[Column]
    rows: AsyncIterator[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Node:
    key: str
    value: Any
    type: TypeTag
    children: list["Node"] = field(default_factory=list)


@dataclass
class TreeData:
    root: Node
    meta: dict[str, Any] = field(default_factory=dict)


__all__ = ["Column", "TabularData", "Node", "TreeData"]
```

- [ ] **Step 9.6: Add packaging stubs**

`apps/data-engine/src/filternarrange_engine/__init__.py`:

```python
"""FilterNArrange data-engine package."""
__version__ = "0.1.0"
```

`apps/data-engine/src/filternarrange_engine/core/__init__.py`:

```python
from .types import TypeTag
from .canonical import Column, TabularData, Node, TreeData

__all__ = ["TypeTag", "Column", "TabularData", "Node", "TreeData"]
```

- [ ] **Step 9.7: Run tests — must pass**

Run: `cd apps/data-engine && uv sync --extra dev && uv run pytest tests/core/test_canonical.py -v`
Expected: PASS.

- [ ] **Step 9.8: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): canonical model (TypeTag, Column, TabularData, TreeData)

Closes #TBD"
```

---

## Task 10: Data-engine — Plugin API protocols + manifests + PluginResult

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/core/plugin_api.py`
- Create: `apps/data-engine/src/filternarrange_engine/core/ports.py`
- Test: `apps/data-engine/tests/core/test_plugin_api.py`

- [ ] **Step 10.1: Write failing protocol test**

Create `apps/data-engine/tests/core/test_plugin_api.py`:

```python
import io
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.plugin_api import (
    FormatManifest, FilterManifest, DetectResult,
    FormatPlugin, FilterPlugin, FilterSpec, PluginResult,
)


def test_format_manifest_validates():
    m = FormatManifest(
        id="csv", display_name="CSV", version="1.0.0",
        license="Apache-2.0", author="x",
        mime_types=["text/csv"], extensions=[".csv"],
        shape="tabular", parse=True, emit=True, streaming=True,
    )
    assert m.id == "csv"
    assert m.shape == "tabular"


def test_plugin_result_ok_and_error():
    ok = PluginResult.ok({"a": 1})
    assert ok.is_ok and ok.value == {"a": 1}
    err = PluginResult.error("PARSE_FAILED", "csv", "1.0.0", "bad row", "trace-1")
    assert not err.is_ok
    assert err.code == "PARSE_FAILED"
    assert err.plugin_id == "csv"


def test_filter_spec_is_dict_like():
    spec: FilterSpec = {"kind": "column", "keep": ["a"]}
    assert spec["kind"] == "column"


def test_format_plugin_protocol_is_structural():
    class DummyPlugin:
        manifest = FormatManifest(
            id="csv", display_name="CSV", version="1.0.0",
            license="Apache-2.0", author="x",
            mime_types=[], extensions=[], shape="tabular",
            parse=True, emit=True, streaming=True,
        )
        def detect(self, sample: bytes) -> DetectResult:
            return DetectResult(format="csv", confidence=0.5)
        def parse(self, source):
            raise NotImplementedError
        def emit(self, data, sink):
            raise NotImplementedError

    p: FormatPlugin = DummyPlugin()  # structural check
    assert p.manifest.id == "csv"
```

- [ ] **Step 10.2: Run — expect failure**

Run: `cd apps/data-engine && uv run pytest tests/core/test_plugin_api.py -v`
Expected: FAIL — module missing.

- [ ] **Step 10.3: Implement `plugin_api.py`**

```python
"""Plugin contracts.

Every format / filter / analysis / AI plugin imports from this module and only
this module. Core code can change internals freely as long as these signatures
stay stable.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, BinaryIO, Generic, Literal, Protocol, TypeVar, TypedDict, Union

from .canonical import TabularData, TreeData


# ---------- Manifests ----------

@dataclass(frozen=True)
class FormatManifest:
    id: str
    display_name: str
    version: str
    license: str
    author: str
    mime_types: list[str]
    extensions: list[str]
    shape: Literal["tabular", "tree"]
    parse: bool
    emit: bool
    streaming: bool
    magic_bytes: list[bytes] = field(default_factory=list)
    confidence_strategy: str = "content-sniff"
    required_tier: Literal["free", "paid"] = "free"


@dataclass(frozen=True)
class FilterManifest:
    id: str
    display_name: str
    version: str
    license: str
    author: str
    kinds: list[str]
    required_tier: Literal["free", "paid"] = "free"


# ---------- Detection ----------

@dataclass(frozen=True)
class DetectResult:
    format: str
    confidence: float


# ---------- Filter specs ----------

class ColumnFilterSpec(TypedDict):
    kind: Literal["column"]
    keep: list[str]


FilterSpec = ColumnFilterSpec  # union grows in Plan C (row/expression/regex)


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


# ---------- Result envelope ----------

T = TypeVar("T")


@dataclass
class PluginResult(Generic[T]):
    """Success-or-error wrapper used at every plugin dispatch boundary."""
    is_ok: bool
    value: T | None = None
    code: str | None = None
    plugin_id: str | None = None
    plugin_version: str | None = None
    message: str | None = None
    trace_id: str | None = None

    @classmethod
    def ok(cls, value: T) -> "PluginResult[T]":
        return cls(is_ok=True, value=value)

    @classmethod
    def error(cls, code: str, plugin_id: str, plugin_version: str,
              message: str, trace_id: str) -> "PluginResult[T]":
        return cls(is_ok=False, code=code, plugin_id=plugin_id,
                   plugin_version=plugin_version, message=message, trace_id=trace_id)

    def to_envelope(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "message": self.message,
            "trace_id": self.trace_id,
        }


# ---------- Plugin protocols ----------

class FormatPlugin(Protocol):
    manifest: FormatManifest

    def detect(self, sample: bytes) -> DetectResult: ...
    def parse(self, source: BinaryIO) -> Union[TabularData, TreeData]: ...
    def emit(self, data: Union[TabularData, TreeData], sink: BinaryIO) -> None: ...


class FilterPlugin(Protocol):
    manifest: FilterManifest

    def apply(self, data: Union[TabularData, TreeData],
              spec: FilterSpec) -> Union[TabularData, TreeData]: ...
    def validate(self, spec: FilterSpec) -> list[ValidationError]: ...
    def explain(self, spec: FilterSpec) -> str: ...


__all__ = [
    "FormatManifest", "FilterManifest",
    "DetectResult", "ColumnFilterSpec", "FilterSpec",
    "ValidationError",
    "PluginResult",
    "FormatPlugin", "FilterPlugin",
]
```

- [ ] **Step 10.4: Implement `ports.py`**

```python
"""Adapter-facing ports the data-engine core depends on."""
from __future__ import annotations
from typing import BinaryIO, Protocol


class ObjectStorePort(Protocol):
    def get(self, ref: str) -> BinaryIO: ...
    def put(self, ref: str, data: BinaryIO, size: int, content_type: str) -> None: ...


__all__ = ["ObjectStorePort"]
```

- [ ] **Step 10.5: Run protocol test**

Run: `cd apps/data-engine && uv run pytest tests/core/test_plugin_api.py -v`
Expected: PASS.

- [ ] **Step 10.6: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): plugin API protocols, manifests, PluginResult envelope

Closes #TBD"
```

---

## Task 11: Data-engine — Plugin registry + dispatcher

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/registry.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/dispatcher.py`
- Test: `apps/data-engine/tests/adapters/plugin_registry/test_registry.py`
- Test: `apps/data-engine/tests/adapters/plugin_registry/test_dispatcher.py`

- [ ] **Step 11.1: Write failing registry test**

Create `apps/data-engine/tests/adapters/plugin_registry/test_registry.py`:

```python
import pytest
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.plugin_api import FormatManifest, DetectResult


class _FakeCsv:
    manifest = FormatManifest(
        id="csv", display_name="CSV", version="1.0.0",
        license="Apache-2.0", author="x",
        mime_types=["text/csv"], extensions=[".csv"],
        shape="tabular", parse=True, emit=True, streaming=True,
    )
    def detect(self, sample): return DetectResult(format="csv", confidence=0.9)
    def parse(self, src): raise NotImplementedError
    def emit(self, data, sink): raise NotImplementedError


def test_register_and_lookup_format():
    r = PluginRegistry()
    p = _FakeCsv()
    r.register_format(p)
    assert r.get_format("csv") is p
    assert "csv" in r.list_formats()


def test_disabled_plugins_skip(monkeypatch):
    monkeypatch.setenv("FILTERNARRANGE_DISABLED_PLUGINS", "csv,parquet")
    r = PluginRegistry()
    assert r.is_disabled("csv")
    assert not r.is_disabled("json")


def test_missing_format_raises():
    r = PluginRegistry()
    with pytest.raises(KeyError):
        r.get_format("xml")
```

- [ ] **Step 11.2: Run — expect failure**

Run: `cd apps/data-engine && uv run pytest tests/adapters/plugin_registry/test_registry.py -v`
Expected: FAIL — module missing.

- [ ] **Step 11.3: Implement `registry.py`**

```python
"""Plugin registry.

Discovers plugins via importlib entry-points and offers explicit register()
for tests. Honors the FILTERNARRANGE_DISABLED_PLUGINS env var.
"""
from __future__ import annotations
import os
from importlib.metadata import entry_points
from typing import Any

from filternarrange_engine.core.plugin_api import FormatPlugin, FilterPlugin


class PluginRegistry:

    FORMAT_GROUP = "filternarrange.formats"
    FILTER_GROUP = "filternarrange.filters"

    def __init__(self) -> None:
        self._formats: dict[str, FormatPlugin] = {}
        self._filters: dict[str, FilterPlugin] = {}
        self._disabled = self._read_disabled()

    @staticmethod
    def _read_disabled() -> set[str]:
        raw = os.environ.get("FILTERNARRANGE_DISABLED_PLUGINS", "")
        return {p.strip() for p in raw.split(",") if p.strip()}

    def is_disabled(self, plugin_id: str) -> bool:
        return plugin_id in self._disabled

    # explicit registration (used by tests + plugins that fail entry-point load)
    def register_format(self, plugin: FormatPlugin) -> None:
        if self.is_disabled(plugin.manifest.id):
            return
        self._formats[plugin.manifest.id] = plugin

    def register_filter(self, plugin: FilterPlugin) -> None:
        if self.is_disabled(plugin.manifest.id):
            return
        for k in plugin.manifest.kinds:
            self._filters[k] = plugin

    def discover(self) -> None:
        for ep in entry_points(group=self.FORMAT_GROUP):
            plugin = ep.load()
            if hasattr(plugin, "manifest"):
                self.register_format(plugin)
        for ep in entry_points(group=self.FILTER_GROUP):
            plugin = ep.load()
            if hasattr(plugin, "manifest"):
                self.register_filter(plugin)

    def get_format(self, fid: str) -> FormatPlugin:
        if fid not in self._formats:
            raise KeyError(fid)
        return self._formats[fid]

    def get_filter(self, kind: str) -> FilterPlugin:
        if kind not in self._filters:
            raise KeyError(kind)
        return self._filters[kind]

    def list_formats(self) -> list[str]:
        return sorted(self._formats.keys())

    def list_filters(self) -> list[str]:
        return sorted(self._filters.keys())

    def detect_format(self, sample: bytes) -> tuple[str, float] | None:
        best: tuple[str, float] | None = None
        for fid, plugin in self._formats.items():
            try:
                res = plugin.detect(sample)
            except Exception:
                continue
            if res.confidence > (best[1] if best else 0.0):
                best = (res.format, res.confidence)
        return best


__all__ = ["PluginRegistry"]
```

- [ ] **Step 11.4: Write failing dispatcher test**

Create `apps/data-engine/tests/adapters/plugin_registry/test_dispatcher.py`:

```python
import pytest
from filternarrange_engine.adapters.plugin_registry.dispatcher import dispatch_plugin_call
from filternarrange_engine.core.plugin_api import PluginResult


def test_dispatch_success():
    result = dispatch_plugin_call("csv", "1.0.0", "trace-1", lambda: {"ok": True})
    assert result.is_ok and result.value == {"ok": True}


def test_dispatch_catches_exception_and_returns_envelope():
    def boom():
        raise ValueError("kaboom")
    result = dispatch_plugin_call("csv", "1.0.0", "trace-9", boom)
    assert not result.is_ok
    assert result.code == "PLUGIN_FAILURE"
    assert result.plugin_id == "csv"
    assert result.plugin_version == "1.0.0"
    assert "kaboom" in result.message
    assert result.trace_id == "trace-9"
```

- [ ] **Step 11.5: Implement `dispatcher.py`**

```python
"""Dispatcher boundary — wraps plugin calls in a PluginResult."""
from __future__ import annotations
from typing import Callable, TypeVar
import structlog

from filternarrange_engine.core.plugin_api import PluginResult

log = structlog.get_logger(__name__)

T = TypeVar("T")


def dispatch_plugin_call(plugin_id: str, plugin_version: str, trace_id: str,
                         call: Callable[[], T]) -> PluginResult[T]:
    """Run `call`; convert any exception into a structured PluginResult.error."""
    try:
        value = call()
        return PluginResult.ok(value)
    except Exception as exc:
        log.warning("plugin_failure",
                    plugin_id=plugin_id, plugin_version=plugin_version,
                    trace_id=trace_id, error=str(exc),
                    error_type=type(exc).__name__)
        return PluginResult.error(
            code="PLUGIN_FAILURE",
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            message=f"{type(exc).__name__}: {exc}",
            trace_id=trace_id,
        )


__all__ = ["dispatch_plugin_call"]
```

- [ ] **Step 11.6: Add `adapters/__init__.py` and registry init**

`apps/data-engine/src/filternarrange_engine/adapters/__init__.py`: empty.

`apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/__init__.py`:

```python
from .registry import PluginRegistry
from .dispatcher import dispatch_plugin_call

__all__ = ["PluginRegistry", "dispatch_plugin_call"]
```

- [ ] **Step 11.7: Run tests**

Run: `cd apps/data-engine && uv run pytest tests/adapters/plugin_registry -v`
Expected: PASS.

- [ ] **Step 11.8: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): plugin registry with entry-point discovery + dispatcher boundary

Closes #TBD"
```

---

## Task 12: Data-engine — MinIO storage adapter + config + logging

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/adapters/storage/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/adapters/storage/minio_store.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/config.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/logging.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/errors.py`
- Test: `apps/data-engine/tests/adapters/storage/test_minio_store.py`

- [ ] **Step 12.1: Write failing MinIO test (testcontainers)**

Create `apps/data-engine/tests/adapters/storage/test_minio_store.py`:

```python
import io
import os
import socket
import time
import subprocess
import pytest

from filternarrange_engine.adapters.storage.minio_store import MinioObjectStore
from filternarrange_engine.platform.config import EngineSettings


def _free_port():
    s = socket.socket()
    s.bind(("localhost", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture(scope="module")
def minio_server():
    port = _free_port()
    console_port = _free_port()
    proc = subprocess.Popen([
        "docker", "run", "--rm", "-d",
        "-p", f"{port}:9000",
        "-p", f"{console_port}:9001",
        "-e", "MINIO_ROOT_USER=testkey",
        "-e", "MINIO_ROOT_PASSWORD=testsecret",
        "minio/minio:RELEASE.2024-08-29T01-40-52Z",
        "server", "/data", "--console-address", ":9001"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cid = proc.stdout.read().decode().strip()
    time.sleep(3)
    try:
        yield f"http://localhost:{port}"
    finally:
        subprocess.run(["docker", "rm", "-f", cid], check=False)


def test_put_get_roundtrip(minio_server):
    settings = EngineSettings(
        minio_endpoint=minio_server,
        minio_access_key="testkey",
        minio_secret_key="testsecret",
        minio_uploads_bucket="uploads",
    )
    store = MinioObjectStore(settings)
    store.ensure_bucket("uploads")
    body = b"name,age\nA,1\n"
    store.put("uploads/x.csv", io.BytesIO(body), len(body), "text/csv")
    out = store.get("uploads/x.csv").read()
    assert out == body
```

- [ ] **Step 12.2: Run — expect failure**

Run: `cd apps/data-engine && uv run pytest tests/adapters/storage/test_minio_store.py -v`
Expected: FAIL — module missing.

- [ ] **Step 12.3: Implement `platform/config.py`**

```python
"""Centralized settings (env-driven)."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineSettings:
    minio_endpoint: str = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
    minio_access_key: str = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    minio_uploads_bucket: str = os.environ.get("MINIO_UPLOADS_BUCKET", "uploads")
    minio_results_bucket: str = os.environ.get("MINIO_RESULTS_BUCKET", "results")
    sample_bytes: int = int(os.environ.get("DETECT_SAMPLE_BYTES", "65536"))


__all__ = ["EngineSettings"]
```

- [ ] **Step 12.4: Implement `platform/logging.py`**

```python
"""Structured logging via structlog."""
from __future__ import annotations
import logging
import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


__all__ = ["configure_logging"]
```

- [ ] **Step 12.5: Implement `platform/errors.py`**

```python
"""Engine-side error envelope."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EngineError(Exception):
    code: str
    message: str
    http_status: int = 500
    plugin_id: str | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


__all__ = ["EngineError"]
```

- [ ] **Step 12.6: Implement `minio_store.py`**

```python
"""MinIO adapter implementing ObjectStorePort."""
from __future__ import annotations
import io
from typing import BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from filternarrange_engine.platform.config import EngineSettings


class MinioObjectStore:

    def __init__(self, settings: EngineSettings) -> None:
        parsed = urlparse(settings.minio_endpoint)
        secure = parsed.scheme == "https"
        self._client = Minio(
            parsed.netloc,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=secure,
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def _split(self, ref: str) -> tuple[str, str]:
        slash = ref.find("/")
        if slash < 0:
            raise ValueError(f"ref '{ref}' is not in bucket/key form")
        return ref[:slash], ref[slash + 1:]

    def get(self, ref: str) -> BinaryIO:
        bucket, key = self._split(ref)
        try:
            response = self._client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return io.BytesIO(data)
        except S3Error as e:
            raise FileNotFoundError(f"object not found: {ref}") from e

    def put(self, ref: str, data: BinaryIO, size: int, content_type: str) -> None:
        bucket, key = self._split(ref)
        self.ensure_bucket(bucket)
        self._client.put_object(bucket, key, data, length=size, content_type=content_type)


__all__ = ["MinioObjectStore"]
```

- [ ] **Step 12.7: Add `__init__.py` files**

`apps/data-engine/src/filternarrange_engine/adapters/storage/__init__.py`:

```python
from .minio_store import MinioObjectStore
__all__ = ["MinioObjectStore"]
```

`apps/data-engine/src/filternarrange_engine/platform/__init__.py`:

```python
from .config import EngineSettings
from .logging import configure_logging
from .errors import EngineError
__all__ = ["EngineSettings", "configure_logging", "EngineError"]
```

- [ ] **Step 12.8: Run the MinIO test (requires Docker)**

Run: `cd apps/data-engine && uv run pytest tests/adapters/storage -v`
Expected: PASS (skip if Docker not available — annotate test or run in CI only).

- [ ] **Step 12.9: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): MinIO ObjectStore adapter + config + structured logging

Closes #TBD"
```

---

## Task 13: Plugin `format-csv` — manifest + detect/parse/emit + tests

**Files:**
- Create: `plugins/format-csv/pyproject.toml`
- Create: `plugins/format-csv/manifest.toml`
- Create: `plugins/format-csv/src/filternarrange_format_csv/__init__.py`
- Create: `plugins/format-csv/src/filternarrange_format_csv/plugin.py`
- Create: `plugins/format-csv/src/filternarrange_format_csv/detect.py`
- Create: `plugins/format-csv/src/filternarrange_format_csv/parse.py`
- Create: `plugins/format-csv/src/filternarrange_format_csv/emit.py`
- Create: `plugins/format-csv/tests/fixtures/people.csv`
- Create: `plugins/format-csv/tests/conftest.py`
- Create: `plugins/format-csv/tests/test_detect.py`
- Create: `plugins/format-csv/tests/test_parse.py`
- Create: `plugins/format-csv/tests/test_emit.py`

- [ ] **Step 13.1: Create fixture `people.csv`**

```
name,age,active
Alice,30,true
Bob,25,false
Carol,42,true
```

- [ ] **Step 13.2: Write failing detect test**

`plugins/format-csv/tests/conftest.py`:

```python
from pathlib import Path
import pytest

@pytest.fixture
def people_csv_bytes() -> bytes:
    return (Path(__file__).parent / "fixtures" / "people.csv").read_bytes()
```

`plugins/format-csv/tests/test_detect.py`:

```python
from filternarrange_format_csv.detect import detect_csv


def test_detect_simple_csv(people_csv_bytes):
    r = detect_csv(people_csv_bytes)
    assert r.format == "csv"
    assert r.confidence >= 0.6


def test_detect_returns_zero_for_binary():
    r = detect_csv(b"\x89PNG\r\n\x1a\n binary data")
    assert r.confidence < 0.4
```

- [ ] **Step 13.3: Create `pyproject.toml`**

```toml
[project]
name = "filternarrange-format-csv"
version = "1.0.0"
description = "CSV format plugin for FilterNArrange"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = [
  "filternarrange-engine",
]

[project.entry-points."filternarrange.formats"]
csv = "filternarrange_format_csv:plugin"

[project.optional-dependencies]
dev = ["pytest==8.3.3", "pytest-asyncio==0.24.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 13.4: Create `manifest.toml`**

```toml
[plugin]
id = "csv"
display_name = "CSV"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"

[detect]
mime_types = ["text/csv"]
extensions = [".csv"]
magic_bytes = []
confidence_strategy = "content-sniff"

[capabilities]
parse = true
emit = true
streaming = true
shape = "tabular"
```

- [ ] **Step 13.5: Implement `detect.py`**

```python
"""CSV detection via csv.Sniffer + heuristics."""
from __future__ import annotations
import csv
import io

from filternarrange_engine.core.plugin_api import DetectResult


def detect_csv(sample: bytes) -> DetectResult:
    text = _safe_decode(sample)
    if not text or "\x00" in text:
        return DetectResult(format="csv", confidence=0.0)

    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(text[:4096], delimiters=",\t;|")
    except csv.Error:
        return DetectResult(format="csv", confidence=0.0)

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    rows = []
    for i, row in enumerate(reader):
        if i >= 50:
            break
        rows.append(row)
    if not rows or len(rows) < 2:
        return DetectResult(format="csv", confidence=0.0)

    header_len = len(rows[0])
    if header_len == 0:
        return DetectResult(format="csv", confidence=0.0)
    consistent = sum(1 for r in rows[1:] if len(r) == header_len)
    confidence = consistent / max(len(rows) - 1, 1)
    confidence = min(confidence + (0.1 if dialect.delimiter == "," else 0.0), 1.0)
    return DetectResult(format="csv", confidence=round(confidence, 3))


def _safe_decode(b: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


__all__ = ["detect_csv"]
```

- [ ] **Step 13.6: Implement `parse.py`**

```python
"""CSV parsing into TabularData with async row iteration."""
from __future__ import annotations
import csv
import io
from typing import AsyncIterator, BinaryIO

from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag


def parse_csv(source: BinaryIO) -> TabularData:
    raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows_list: list[list[str]] = list(reader)
    if not rows_list:
        return TabularData(schema=[], rows=_aiter([]), meta={"row_count": 0})

    header = rows_list[0]
    body = rows_list[1:]
    schema = [Column(name=h, type=_infer_type(h, body, i), nullable=True)
              for i, h in enumerate(header)]
    dicts = [dict(zip(header, r)) for r in body]
    return TabularData(schema=schema, rows=_aiter(dicts), meta={"row_count": len(dicts)})


def _infer_type(col_name: str, body: list[list[str]], idx: int) -> TypeTag:
    values = [r[idx] for r in body if idx < len(r) and r[idx] != ""]
    if not values:
        return TypeTag.STRING
    if all(_is_int(v) for v in values):
        return TypeTag.INTEGER
    if all(_is_float(v) for v in values):
        return TypeTag.NUMBER
    if all(_is_bool(v) for v in values):
        return TypeTag.BOOLEAN
    return TypeTag.STRING


def _is_int(v: str) -> bool:
    try:
        int(v); return True
    except ValueError:
        return False


def _is_float(v: str) -> bool:
    try:
        float(v); return True
    except ValueError:
        return False


def _is_bool(v: str) -> bool:
    return v.lower() in {"true", "false", "0", "1", "yes", "no"}


async def _aiter(items):
    for it in items:
        yield it


__all__ = ["parse_csv"]
```

- [ ] **Step 13.7: Implement `emit.py`**

```python
"""CSV emission from TabularData."""
from __future__ import annotations
import asyncio
import csv
import io
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData


def emit_csv(data: TabularData, sink: BinaryIO) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    columns = [c.name for c in data.schema]
    writer.writerow(columns)

    async def _drain() -> list[dict]:
        return [r async for r in data.rows]

    rows = asyncio.get_event_loop().run_until_complete(_drain()) \
        if not asyncio.get_event_loop().is_running() else _collect_sync(data)
    for r in rows:
        writer.writerow([r.get(c, "") for c in columns])
    sink.write(buf.getvalue().encode("utf-8"))


def _collect_sync(data: TabularData) -> list[dict]:
    # When already in a running loop (FastAPI), use nest_asyncio-style fallback.
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_drain(data))
    finally:
        loop.close()


async def _drain(data: TabularData) -> list[dict]:
    return [r async for r in data.rows]


__all__ = ["emit_csv"]
```

- [ ] **Step 13.8: Implement `plugin.py`**

```python
"""CSV plugin entry-point object."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_api import DetectResult, FormatManifest

from .detect import detect_csv
from .parse import parse_csv
from .emit import emit_csv


class _CsvPlugin:
    manifest = FormatManifest(
        id="csv",
        display_name="CSV",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        mime_types=["text/csv"],
        extensions=[".csv"],
        shape="tabular",
        parse=True, emit=True, streaming=True,
    )

    def detect(self, sample: bytes) -> DetectResult:
        return detect_csv(sample)

    def parse(self, source: BinaryIO) -> TabularData:
        return parse_csv(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        if not isinstance(data, TabularData):
            raise ValueError("csv emit requires TabularData")
        emit_csv(data, sink)


plugin = _CsvPlugin()
```

- [ ] **Step 13.9: `__init__.py`**

```python
from .plugin import plugin
__all__ = ["plugin"]
```

- [ ] **Step 13.10: Write parse & emit tests**

`plugins/format-csv/tests/test_parse.py`:

```python
import io
import pytest
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_csv.parse import parse_csv


@pytest.mark.asyncio
async def test_parse_infers_columns_and_streams_rows(people_csv_bytes):
    data = parse_csv(io.BytesIO(people_csv_bytes))
    names = [c.name for c in data.schema]
    assert names == ["name", "age", "active"]
    assert data.schema[1].type is TypeTag.INTEGER
    rows = [r async for r in data.rows]
    assert rows[0]["name"] == "Alice"
    assert rows[1]["age"] == "25"
```

`plugins/format-csv/tests/test_emit.py`:

```python
import io
import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_csv.emit import emit_csv


async def _rows(items):
    for r in items: yield r


def test_emit_writes_csv():
    data = TabularData(
        schema=[Column("name", TypeTag.STRING, False), Column("age", TypeTag.INTEGER, True)],
        rows=_rows([{"name": "A", "age": "1"}, {"name": "B", "age": "2"}]),
        meta={},
    )
    buf = io.BytesIO()
    emit_csv(data, buf)
    text = buf.getvalue().decode()
    assert text.splitlines()[0] == "name,age"
    assert "A,1" in text
    assert "B,2" in text
```

- [ ] **Step 13.11: Install plugin in dev + run tests**

Run:
```
cd plugins/format-csv && uv pip install -e . --python ../../apps/data-engine/.venv/bin/python
uv run --project ../../apps/data-engine pytest plugins/format-csv/tests -v
```
Expected: PASS.

- [ ] **Step 13.12: Commit**

```bash
git add plugins/format-csv
git commit -m "feat(plugins): format-csv plugin (detect/parse/emit) + tests

Closes #TBD"
```

---

## Task 14: Plugin `format-json` — array → tabular, object → tree

**Files:**
- Create: `plugins/format-json/pyproject.toml`
- Create: `plugins/format-json/manifest.toml`
- Create: `plugins/format-json/src/filternarrange_format_json/__init__.py`
- Create: `plugins/format-json/src/filternarrange_format_json/plugin.py`
- Create: `plugins/format-json/src/filternarrange_format_json/detect.py`
- Create: `plugins/format-json/src/filternarrange_format_json/parse.py`
- Create: `plugins/format-json/src/filternarrange_format_json/emit.py`
- Create: `plugins/format-json/tests/fixtures/people.json`
- Create: `plugins/format-json/tests/fixtures/nested.json`
- Create: `plugins/format-json/tests/conftest.py`
- Create: `plugins/format-json/tests/test_detect.py`
- Create: `plugins/format-json/tests/test_parse.py`
- Create: `plugins/format-json/tests/test_emit.py`

- [ ] **Step 14.1: Create fixtures**

`plugins/format-json/tests/fixtures/people.json`:

```json
[
  {"name": "Alice", "age": 30, "active": true},
  {"name": "Bob",   "age": 25, "active": false}
]
```

`plugins/format-json/tests/fixtures/nested.json`:

```json
{
  "company": "Acme",
  "departments": [
    {"name": "Eng", "size": 12},
    {"name": "Ops", "size": 5}
  ]
}
```

- [ ] **Step 14.2: Failing detect test**

`plugins/format-json/tests/conftest.py`:

```python
from pathlib import Path
import pytest

FIX = Path(__file__).parent / "fixtures"

@pytest.fixture
def people_json() -> bytes: return (FIX / "people.json").read_bytes()

@pytest.fixture
def nested_json() -> bytes: return (FIX / "nested.json").read_bytes()
```

`plugins/format-json/tests/test_detect.py`:

```python
from filternarrange_format_json.detect import detect_json


def test_detect_array(people_json):
    r = detect_json(people_json)
    assert r.format == "json"
    assert r.confidence >= 0.9


def test_detect_object(nested_json):
    r = detect_json(nested_json)
    assert r.format == "json"
    assert r.confidence >= 0.9


def test_detect_garbage():
    r = detect_json(b"not json at all !!!")
    assert r.confidence == 0.0
```

- [ ] **Step 14.3: `pyproject.toml`**

```toml
[project]
name = "filternarrange-format-json"
version = "1.0.0"
description = "JSON format plugin"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.formats"]
json = "filternarrange_format_json:plugin"

[project.optional-dependencies]
dev = ["pytest==8.3.3", "pytest-asyncio==0.24.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 14.4: `manifest.toml`**

```toml
[plugin]
id = "json"
display_name = "JSON"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"

[detect]
mime_types = ["application/json"]
extensions = [".json"]
magic_bytes = []
confidence_strategy = "structural-sniff"

[capabilities]
parse = true
emit = true
streaming = false
shape = "tabular"
```

- [ ] **Step 14.5: `detect.py`**

```python
"""JSON detection — parse a sample and check for array/object."""
from __future__ import annotations
import json
from filternarrange_engine.core.plugin_api import DetectResult


def detect_json(sample: bytes) -> DetectResult:
    try:
        text = sample.decode("utf-8-sig")
    except UnicodeDecodeError:
        return DetectResult(format="json", confidence=0.0)
    stripped = text.lstrip()
    if not stripped or stripped[0] not in "[{":
        return DetectResult(format="json", confidence=0.0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return DetectResult(format="json", confidence=0.0)
    if isinstance(parsed, list) and all(isinstance(x, dict) for x in parsed):
        return DetectResult(format="json", confidence=0.98)
    if isinstance(parsed, dict):
        return DetectResult(format="json", confidence=0.95)
    return DetectResult(format="json", confidence=0.7)


__all__ = ["detect_json"]
```

- [ ] **Step 14.6: `parse.py`**

```python
"""Parse JSON to TabularData (array of objects) or TreeData (anything else)."""
from __future__ import annotations
import json
from typing import Any, BinaryIO, Union

from filternarrange_engine.core.canonical import Column, Node, TabularData, TreeData
from filternarrange_engine.core.types import TypeTag


def parse_json(source: BinaryIO) -> Union[TabularData, TreeData]:
    text = source.read().decode("utf-8-sig")
    obj = json.loads(text)

    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj):
        return _to_tabular(obj)
    return _to_tree(obj)


def _to_tabular(rows: list[dict]) -> TabularData:
    columns: dict[str, TypeTag] = {}
    for r in rows:
        for k, v in r.items():
            columns.setdefault(k, _type_of(v))
    schema = [Column(name=n, type=t, nullable=True) for n, t in columns.items()]
    return TabularData(schema=schema, rows=_aiter(rows), meta={"row_count": len(rows)})


def _to_tree(value: Any, key: str = "$") -> TreeData:
    root = _node(key, value)
    return TreeData(root=root, meta={"depth": _depth(root), "total_nodes": _count(root)})


def _node(key: str, value: Any) -> Node:
    if isinstance(value, dict):
        children = [_node(k, v) for k, v in value.items()]
        return Node(key=key, value=None, type=TypeTag.NULL, children=children)
    if isinstance(value, list):
        children = [_node(f"[{i}]", v) for i, v in enumerate(value)]
        return Node(key=key, value=None, type=TypeTag.NULL, children=children)
    return Node(key=key, value=value, type=_type_of(value), children=[])


def _type_of(v: Any) -> TypeTag:
    if v is None: return TypeTag.NULL
    if isinstance(v, bool): return TypeTag.BOOLEAN
    if isinstance(v, int): return TypeTag.INTEGER
    if isinstance(v, float): return TypeTag.NUMBER
    if isinstance(v, str): return TypeTag.STRING
    return TypeTag.STRING


def _depth(n: Node) -> int:
    return 1 + max((_depth(c) for c in n.children), default=0)


def _count(n: Node) -> int:
    return 1 + sum(_count(c) for c in n.children)


async def _aiter(items):
    for it in items: yield it


__all__ = ["parse_json"]
```

- [ ] **Step 14.7: `emit.py`**

```python
"""Emit TabularData (or TreeData) as JSON."""
from __future__ import annotations
import asyncio
import json
from typing import BinaryIO, Union

from filternarrange_engine.core.canonical import TabularData, TreeData, Node


def emit_json(data: Union[TabularData, TreeData], sink: BinaryIO) -> None:
    if isinstance(data, TabularData):
        rows = _drain(data)
        sink.write(json.dumps(rows, default=_default).encode("utf-8"))
    else:
        sink.write(json.dumps(_node_to_obj(data.root), default=_default).encode("utf-8"))


def _drain(data: TabularData) -> list[dict]:
    loop = asyncio.new_event_loop()
    try:
        async def collect():
            return [r async for r in data.rows]
        return loop.run_until_complete(collect())
    finally:
        loop.close()


def _node_to_obj(n: Node):
    if not n.children:
        return n.value
    if all(c.key.startswith("[") for c in n.children):
        return [_node_to_obj(c) for c in n.children]
    return {c.key: _node_to_obj(c) for c in n.children}


def _default(o):
    try:
        return str(o)
    except Exception:
        return None


__all__ = ["emit_json"]
```

- [ ] **Step 14.8: `plugin.py` + `__init__.py`**

```python
"""JSON plugin entry-point."""
from __future__ import annotations
from typing import BinaryIO

from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.core.plugin_api import DetectResult, FormatManifest

from .detect import detect_json
from .parse import parse_json
from .emit import emit_json


class _JsonPlugin:
    manifest = FormatManifest(
        id="json",
        display_name="JSON",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        mime_types=["application/json"],
        extensions=[".json"],
        shape="tabular",  # default — tree if structure dictates
        parse=True, emit=True, streaming=False,
    )

    def detect(self, sample: bytes) -> DetectResult:
        return detect_json(sample)

    def parse(self, source: BinaryIO) -> TabularData | TreeData:
        return parse_json(source)

    def emit(self, data: TabularData | TreeData, sink: BinaryIO) -> None:
        emit_json(data, sink)


plugin = _JsonPlugin()
```

```python
from .plugin import plugin
__all__ = ["plugin"]
```

- [ ] **Step 14.9: parse / emit tests**

`plugins/format-json/tests/test_parse.py`:

```python
import io
import pytest
from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_format_json.parse import parse_json


@pytest.mark.asyncio
async def test_array_becomes_tabular(people_json):
    data = parse_json(io.BytesIO(people_json))
    assert isinstance(data, TabularData)
    names = [c.name for c in data.schema]
    assert "name" in names and "age" in names
    rows = [r async for r in data.rows]
    assert len(rows) == 2


def test_object_becomes_tree(nested_json):
    data = parse_json(io.BytesIO(nested_json))
    assert isinstance(data, TreeData)
    assert data.root.key == "$"
    keys = [c.key for c in data.root.children]
    assert "company" in keys and "departments" in keys
```

`plugins/format-json/tests/test_emit.py`:

```python
import io
import json
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_format_json.emit import emit_json


async def _rows(items):
    for r in items: yield r


def test_emit_tabular_writes_json_array():
    data = TabularData(
        schema=[Column("a", TypeTag.STRING, False)],
        rows=_rows([{"a": "1"}, {"a": "2"}]),
        meta={},
    )
    buf = io.BytesIO()
    emit_json(data, buf)
    parsed = json.loads(buf.getvalue())
    assert parsed == [{"a": "1"}, {"a": "2"}]
```

- [ ] **Step 14.10: Run tests**

Run:
```
cd plugins/format-json && uv pip install -e . --python ../../apps/data-engine/.venv/bin/python
uv run --project ../../apps/data-engine pytest plugins/format-json/tests -v
```
Expected: PASS.

- [ ] **Step 14.11: Commit**

```bash
git add plugins/format-json
git commit -m "feat(plugins): format-json plugin (array→tabular, object→tree)

Closes #TBD"
```

---

## Task 15: Plugin `filter-column` — keep listed columns

**Files:**
- Create: `plugins/filter-column/pyproject.toml`
- Create: `plugins/filter-column/manifest.toml`
- Create: `plugins/filter-column/src/filternarrange_filter_column/__init__.py`
- Create: `plugins/filter-column/src/filternarrange_filter_column/plugin.py`
- Create: `plugins/filter-column/tests/test_apply.py`
- Create: `plugins/filter-column/tests/test_validate.py`

- [ ] **Step 15.1: Failing apply test**

`plugins/filter-column/tests/test_apply.py`:

```python
import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.types import TypeTag
from filternarrange_filter_column.plugin import plugin as filter_plugin


async def _rows(items):
    for r in items: yield r


@pytest.mark.asyncio
async def test_apply_keeps_only_listed_columns():
    data = TabularData(
        schema=[
            Column("name", TypeTag.STRING, False),
            Column("age", TypeTag.INTEGER, True),
            Column("email", TypeTag.STRING, True),
        ],
        rows=_rows([
            {"name": "A", "age": 1, "email": "a@x"},
            {"name": "B", "age": 2, "email": "b@x"},
        ]),
        meta={},
    )
    out = filter_plugin.apply(data, {"kind": "column", "keep": ["name", "age"]})
    assert [c.name for c in out.schema] == ["name", "age"]
    rows = [r async for r in out.rows]
    assert rows == [{"name": "A", "age": 1}, {"name": "B", "age": 2}]


def test_explain():
    spec = {"kind": "column", "keep": ["a", "b"]}
    text = filter_plugin.explain(spec)
    assert "keep" in text.lower()
    assert "a" in text and "b" in text
```

`plugins/filter-column/tests/test_validate.py`:

```python
from filternarrange_filter_column.plugin import plugin


def test_validate_missing_kind_fails():
    errs = plugin.validate({"keep": ["a"]})
    assert any(e.field == "kind" for e in errs)


def test_validate_empty_keep_fails():
    errs = plugin.validate({"kind": "column", "keep": []})
    assert any(e.field == "keep" for e in errs)


def test_validate_wrong_kind_fails():
    errs = plugin.validate({"kind": "row", "keep": ["a"]})
    assert any(e.field == "kind" for e in errs)


def test_validate_ok():
    errs = plugin.validate({"kind": "column", "keep": ["a"]})
    assert errs == []
```

- [ ] **Step 15.2: `pyproject.toml`**

```toml
[project]
name = "filternarrange-filter-column"
version = "1.0.0"
description = "Column-projection filter plugin"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = ["filternarrange-engine"]

[project.entry-points."filternarrange.filters"]
column = "filternarrange_filter_column:plugin"

[project.optional-dependencies]
dev = ["pytest==8.3.3", "pytest-asyncio==0.24.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 15.3: `manifest.toml`**

```toml
[plugin]
id = "filter-column"
display_name = "Column projection"
version = "1.0.0"
license = "Apache-2.0"
author = "FilterNArrange Core"

[capabilities]
kinds = ["column"]
```

- [ ] **Step 15.4: `plugin.py`**

```python
"""Column-projection filter plugin."""
from __future__ import annotations
from typing import Union

from filternarrange_engine.core.canonical import Column, TabularData, TreeData
from filternarrange_engine.core.plugin_api import (
    FilterManifest, FilterSpec, ValidationError,
)


class _ColumnFilter:
    manifest = FilterManifest(
        id="filter-column",
        display_name="Column projection",
        version="1.0.0",
        license="Apache-2.0",
        author="FilterNArrange Core",
        kinds=["column"],
    )

    def apply(self, data: Union[TabularData, TreeData], spec: FilterSpec) -> TabularData:
        if not isinstance(data, TabularData):
            raise ValueError("filter-column requires TabularData input")
        keep = list(spec["keep"])
        keep_set = set(keep)
        new_schema = [c for c in data.schema if c.name in keep_set]
        # preserve user-requested order
        order_map = {name: i for i, name in enumerate(keep)}
        new_schema.sort(key=lambda c: order_map.get(c.name, 1_000_000))

        async def project():
            async for row in data.rows:
                yield {k: row[k] for k in keep if k in row}

        return TabularData(schema=new_schema, rows=project(), meta=data.meta)

    def validate(self, spec: FilterSpec) -> list[ValidationError]:
        errs: list[ValidationError] = []
        kind = spec.get("kind") if isinstance(spec, dict) else None
        if kind is None:
            errs.append(ValidationError(field="kind", message="kind is required"))
        elif kind != "column":
            errs.append(ValidationError(field="kind", message=f"unsupported kind '{kind}'"))
        keep = spec.get("keep") if isinstance(spec, dict) else None
        if not keep or not isinstance(keep, list):
            errs.append(ValidationError(field="keep", message="keep must be a non-empty list of column names"))
        return errs

    def explain(self, spec: FilterSpec) -> str:
        keep = spec.get("keep", [])
        return f"keep columns: {', '.join(keep)}"


plugin = _ColumnFilter()
```

- [ ] **Step 15.5: `__init__.py`**

```python
from .plugin import plugin
__all__ = ["plugin"]
```

- [ ] **Step 15.6: Run tests**

Run:
```
cd plugins/filter-column && uv pip install -e . --python ../../apps/data-engine/.venv/bin/python
uv run --project ../../apps/data-engine pytest plugins/filter-column/tests -v
```
Expected: PASS.

- [ ] **Step 15.7: Commit**

```bash
git add plugins/filter-column
git commit -m "feat(plugins): filter-column projection plugin

Closes #TBD"
```

---

## Task 16: Data-engine — FastAPI routers + service layer

**Files:**
- Create: `apps/data-engine/src/filternarrange_engine/application/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/detect_service.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/filter_service.py`
- Create: `apps/data-engine/src/filternarrange_engine/application/convert_service.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/__init__.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/dependencies.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/schemas.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/routes_detect.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/routes_filter.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/routes_convert.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/main.py`
- Test: `apps/data-engine/tests/api/test_routes.py`

- [ ] **Step 16.1: Failing FastAPI test using in-memory MinIO stub**

`apps/data-engine/tests/api/test_routes.py`:

```python
import io
import pytest
from fastapi.testclient import TestClient

from filternarrange_engine.api.main import build_app
from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_format_csv import plugin as csv_plugin
from filternarrange_format_json import plugin as json_plugin
from filternarrange_filter_column import plugin as col_filter_plugin


class _InMemoryStore:
    def __init__(self): self._blobs: dict[str, bytes] = {}
    def put(self, ref, data, size, content_type):
        self._blobs[ref] = data.read()
    def get(self, ref):
        if ref not in self._blobs:
            raise FileNotFoundError(ref)
        return io.BytesIO(self._blobs[ref])
    def ensure_bucket(self, b): pass


@pytest.fixture
def app_and_store():
    store = _InMemoryStore()
    registry = PluginRegistry()
    registry.register_format(csv_plugin)
    registry.register_format(json_plugin)
    registry.register_filter(col_filter_plugin)
    app = build_app(store=store, registry=registry)
    return TestClient(app), store


def _put_csv(store, ref):
    body = b"name,age\nA,1\nB,2\n"
    store.put(ref, io.BytesIO(body), len(body), "text/csv")


def test_detect_returns_csv(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/detect", json={"ref": "uploads/u/x.csv"})
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "csv"
    assert any(c["name"] == "name" for c in body["schema"])


def test_filter_returns_subset_rows(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/filter", json={
        "ref": "uploads/u/x.csv",
        "filter": {"kind": "column", "keep": ["name"]},
        "sampleSize": 10,
    })
    assert res.status_code == 200
    body = res.json()
    assert [c["name"] for c in body["schema"]] == ["name"]
    assert body["rows"] == [{"name": "A"}, {"name": "B"}]


def test_convert_writes_result_blob(app_and_store):
    client, store = app_and_store
    _put_csv(store, "uploads/u/x.csv")
    res = client.post("/convert", json={
        "ref": "uploads/u/x.csv",
        "filter": {"kind": "column", "keep": ["name"]},
        "outputFormat": "json",
    })
    assert res.status_code == 200
    ref = res.json()["resultRef"]
    out = store.get(ref).read()
    assert b"\"name\"" in out
    assert b"A" in out and b"B" in out


def test_detect_unknown_ref_returns_envelope(app_and_store):
    client, _ = app_and_store
    res = client.post("/detect", json={"ref": "uploads/u/missing.csv"})
    assert res.status_code == 404
    body = res.json()
    assert body["code"] == "NOT_FOUND"
    assert "traceId" in body
```

- [ ] **Step 16.2: Run — expect failure**

Run: `cd apps/data-engine && uv run pytest tests/api/test_routes.py -v`
Expected: FAIL — `build_app` missing.

- [ ] **Step 16.3: `application/__init__.py` empty**

- [ ] **Step 16.4: Implement `application/detect_service.py`**

```python
"""Detect orchestration: load sample → run all plugins → choose best."""
from __future__ import annotations
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData, TreeData
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


class DetectService:
    def __init__(self, store: _Store, registry: PluginRegistry, settings: EngineSettings):
        self.store = store; self.registry = registry; self.settings = settings

    def run(self, ref: str) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e
        sample = blob[:self.settings.sample_bytes]
        choice = self.registry.detect_format(sample)
        if choice is None or choice[1] < 0.4:
            raise EngineError(code="UNKNOWN_FORMAT", message="No plugin matched", http_status=422)
        fid, confidence = choice
        plugin = self.registry.get_format(fid)
        import io as _io
        parsed = plugin.parse(_io.BytesIO(blob))
        schema = _schema_of(parsed)
        return {"format": fid, "confidence": confidence, "schema": schema}


def _schema_of(parsed) -> list[dict]:
    if isinstance(parsed, TabularData):
        return [{"name": c.name, "type": c.type.value, "nullable": c.nullable} for c in parsed.schema]
    if isinstance(parsed, TreeData):
        return [{"name": "$", "type": "null", "nullable": True}]
    return []


__all__ = ["DetectService"]
```

- [ ] **Step 16.5: Implement `application/filter_service.py`**

```python
"""Filter orchestration: detect → parse → filter → collect N rows."""
from __future__ import annotations
import asyncio
import io as _io
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...


class FilterService:
    def __init__(self, store: _Store, registry: PluginRegistry):
        self.store = store; self.registry = registry

    def run(self, ref: str, spec: dict, sample_size: int) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

        choice = self.registry.detect_format(blob[:65536])
        if choice is None:
            raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
        fid, _ = choice
        format_plugin = self.registry.get_format(fid)
        parsed = format_plugin.parse(_io.BytesIO(blob))
        if not isinstance(parsed, TabularData):
            raise EngineError(code="NOT_TABULAR", message="filter requires tabular data", http_status=422)

        kind = spec.get("kind")
        try:
            filter_plugin = self.registry.get_filter(kind)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_FILTER", message=f"no filter for kind={kind}",
                              http_status=422) from e

        errs = filter_plugin.validate(spec)
        if errs:
            raise EngineError(code="VALIDATION_FAILED",
                              message="; ".join(f"{e.field}: {e.message}" for e in errs),
                              http_status=400)
        filtered = filter_plugin.apply(parsed, spec)

        async def collect():
            out = []
            async for r in filtered.rows:
                out.append(r)
                if len(out) >= sample_size:
                    break
            return out

        rows = asyncio.new_event_loop().run_until_complete(collect())
        return {
            "schema": [{"name": c.name, "type": c.type.value, "nullable": c.nullable} for c in filtered.schema],
            "rows": rows,
        }


__all__ = ["FilterService"]
```

- [ ] **Step 16.6: Implement `application/convert_service.py`**

```python
"""Convert orchestration: filter then emit to chosen format → write blob."""
from __future__ import annotations
import io as _io
import uuid
from typing import Protocol

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.core.canonical import TabularData
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError


class _Store(Protocol):
    def get(self, ref: str): ...
    def put(self, ref: str, data, size: int, content_type: str): ...


class ConvertService:
    def __init__(self, store: _Store, registry: PluginRegistry, settings: EngineSettings):
        self.store = store; self.registry = registry; self.settings = settings

    def run(self, ref: str, spec: dict, output_format: str) -> dict:
        try:
            blob = self.store.get(ref).read()
        except FileNotFoundError as e:
            raise EngineError(code="NOT_FOUND", message=str(e), http_status=404) from e

        choice = self.registry.detect_format(blob[:65536])
        if choice is None:
            raise EngineError(code="UNKNOWN_FORMAT", message="no plugin matched", http_status=422)
        fid, _ = choice
        in_plugin = self.registry.get_format(fid)
        try:
            out_plugin = self.registry.get_format(output_format)
        except KeyError as e:
            raise EngineError(code="UNKNOWN_OUTPUT_FORMAT",
                              message=f"no plugin for {output_format}", http_status=400) from e

        parsed = in_plugin.parse(_io.BytesIO(blob))
        if isinstance(parsed, TabularData):
            try:
                filter_plugin = self.registry.get_filter(spec.get("kind", ""))
                parsed = filter_plugin.apply(parsed, spec)
            except KeyError as e:
                raise EngineError(code="UNKNOWN_FILTER", message=str(e), http_status=422) from e

        result_id = uuid.uuid4()
        result_ref = f"{self.settings.minio_results_bucket}/{result_id}.{output_format}"
        sink = _io.BytesIO()
        out_plugin.emit(parsed, sink)
        body = sink.getvalue()
        self.store.put(result_ref, _io.BytesIO(body), len(body),
                       _ct(output_format))
        return {"resultRef": result_ref}


def _ct(fmt: str) -> str:
    return {"csv": "text/csv", "json": "application/json"}.get(fmt, "application/octet-stream")


__all__ = ["ConvertService"]
```

- [ ] **Step 16.7: Implement API schemas**

`apps/data-engine/src/filternarrange_engine/api/__init__.py`: empty.

`apps/data-engine/src/filternarrange_engine/api/schemas.py`:

```python
"""Pydantic models — mirror gateway-internal.v1.yaml."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class RefRequest(BaseModel):
    ref: str


class Column(BaseModel):
    name: str
    type: str
    nullable: bool


class DetectResponse(BaseModel):
    format: str
    confidence: float
    schema_: list[Column] = Field(alias="schema")

    model_config = {"populate_by_name": True}


class ColumnFilterSpec(BaseModel):
    kind: str
    keep: list[str]


class FilterRequest(BaseModel):
    ref: str
    filter: ColumnFilterSpec
    sampleSize: int = 20


class FilterResponse(BaseModel):
    schema_: list[Column] = Field(alias="schema")
    rows: list[dict[str, Any]]
    model_config = {"populate_by_name": True}


class ConvertRequest(BaseModel):
    ref: str
    filter: ColumnFilterSpec
    outputFormat: str


class ConvertResponse(BaseModel):
    resultRef: str


class ErrorEnvelope(BaseModel):
    code: str
    pluginId: str | None = None
    message: str
    traceId: str
```

- [ ] **Step 16.8: Implement `api/dependencies.py`**

```python
"""FastAPI dependency providers."""
from __future__ import annotations
import uuid
from contextvars import ContextVar
from fastapi import Request

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def trace_id_from_request(request: Request) -> str:
    existing = request.headers.get("X-Trace-Id")
    tid = existing if existing else str(uuid.uuid4())
    trace_id_var.set(tid)
    return tid
```

- [ ] **Step 16.9: Implement route modules**

`routes_detect.py`:

```python
from fastapi import APIRouter, Depends, Request
from .schemas import RefRequest, DetectResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/detect", response_model=DetectResponse, response_model_by_alias=True)
def detect(req: RefRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.detect
    result = svc.run(req.ref)
    return DetectResponse(format=result["format"], confidence=result["confidence"],
                          **{"schema": result["schema"]})
```

`routes_filter.py`:

```python
from fastapi import APIRouter, Depends, Request
from .schemas import FilterRequest, FilterResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/filter", response_model=FilterResponse, response_model_by_alias=True)
def filter_(req: FilterRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.filter
    result = svc.run(req.ref, req.filter.model_dump(), req.sampleSize)
    return FilterResponse(rows=result["rows"], **{"schema": result["schema"]})
```

`routes_convert.py`:

```python
from fastapi import APIRouter, Depends, Request
from .schemas import ConvertRequest, ConvertResponse
from .dependencies import trace_id_from_request

router = APIRouter()


@router.post("/convert", response_model=ConvertResponse)
def convert(req: ConvertRequest, request: Request, trace_id: str = Depends(trace_id_from_request)):
    svc = request.app.state.convert
    result = svc.run(req.ref, req.filter.model_dump(), req.outputFormat)
    return ConvertResponse(resultRef=result["resultRef"])
```

- [ ] **Step 16.10: Implement `api/main.py`**

```python
"""FastAPI app factory and lifecycle."""
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from filternarrange_engine.adapters.plugin_registry.registry import PluginRegistry
from filternarrange_engine.adapters.storage.minio_store import MinioObjectStore
from filternarrange_engine.application.convert_service import ConvertService
from filternarrange_engine.application.detect_service import DetectService
from filternarrange_engine.application.filter_service import FilterService
from filternarrange_engine.platform.config import EngineSettings
from filternarrange_engine.platform.errors import EngineError
from filternarrange_engine.platform.logging import configure_logging

from .dependencies import trace_id_var
from .routes_convert import router as convert_router
from .routes_detect import router as detect_router
from .routes_filter import router as filter_router


def build_app(store=None, registry: PluginRegistry | None = None,
              settings: EngineSettings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or EngineSettings()
    registry = registry or PluginRegistry()
    if registry.list_formats() == [] and store is None:
        registry.discover()
    store = store or MinioObjectStore(settings)

    app = FastAPI(title="FilterNArrange data-engine", version="1.0.0")
    app.state.settings = settings
    app.state.registry = registry
    app.state.store = store
    app.state.detect = DetectService(store, registry, settings)
    app.state.filter = FilterService(store, registry)
    app.state.convert = ConvertService(store, registry, settings)

    app.include_router(detect_router)
    app.include_router(filter_router)
    app.include_router(convert_router)

    @app.exception_handler(EngineError)
    async def engine_error_handler(request: Request, exc: EngineError):
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "pluginId": exc.plugin_id,
                "message": exc.message,
                "traceId": trace_id_var.get() or "unknown",
            },
        )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "formats": registry.list_formats(),
                "filters": registry.list_filters()}

    return app


app = build_app()
```

- [ ] **Step 16.11: Run the API test**

Run: `cd apps/data-engine && uv run pytest tests/api -v`
Expected: PASS (all four cases).

- [ ] **Step 16.12: Commit**

```bash
git add apps/data-engine
git commit -m "feat(data-engine): FastAPI routers + detect/filter/convert services

Closes #TBD"
```

---

## Task 17: Data-engine — `import-linter` rules

**Files:**
- Create: `apps/data-engine/.importlinter`
- Test: run `import-linter` as a pytest step

- [ ] **Step 17.1: Write `.importlinter`**

```ini
[importlinter]
root_packages =
    filternarrange_engine

[importlinter:contract:layered]
name = Layered architecture
type = layers
layers =
    filternarrange_engine.api
    filternarrange_engine.application
    filternarrange_engine.adapters
    filternarrange_engine.platform
    filternarrange_engine.core

[importlinter:contract:core-isolation]
name = core does not import adapters
type = forbidden
source_modules =
    filternarrange_engine.core
forbidden_modules =
    filternarrange_engine.adapters
    filternarrange_engine.api
    filternarrange_engine.application
```

- [ ] **Step 17.2: Run import-linter**

Run: `cd apps/data-engine && uv run lint-imports`
Expected: PASS. If a violation appears, fix offending file rather than weakening rules.

- [ ] **Step 17.3: Add `tests/test_import_linter.py` so CI runs it via pytest**

```python
import subprocess
import pathlib


def test_import_linter_passes():
    root = pathlib.Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["uv", "run", "lint-imports"],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 17.4: Commit**

```bash
git add apps/data-engine/.importlinter apps/data-engine/tests/test_import_linter.py
git commit -m "test(data-engine): import-linter layered + core-isolation contracts

Closes #TBD"
```

---

## Task 18: Frontend — Generated API client + auth feature

**Files:**
- Modify: `apps/frontend/package.json`
- Create: `apps/frontend/openapi-ts.config.ts`
- Create: `apps/frontend/.eslintrc.cjs`
- Create: `apps/frontend/src/shared/api/client.ts`
- Create: `apps/frontend/src/app/providers/AuthProvider.tsx`
- Create: `apps/frontend/src/features/auth/api/index.ts`
- Create: `apps/frontend/src/features/auth/state/useAuth.ts`
- Create: `apps/frontend/src/features/auth/ui/LoginForm.tsx`
- Create: `apps/frontend/src/features/auth/ui/SignupForm.tsx`
- Create: `apps/frontend/src/features/auth/index.ts`
- Create: `apps/frontend/src/pages/LoginPage.tsx`
- Create: `apps/frontend/src/pages/SignupPage.tsx`
- Test: `apps/frontend/tests/unit/auth.test.tsx`

- [ ] **Step 18.1: Add deps**

`apps/frontend/package.json`:

```json
{
  "name": "filternarrange-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:e2e": "playwright test",
    "lint": "eslint src --max-warnings=0",
    "gen:api": "openapi --input ../../contracts/openapi/gateway-public.v1.yaml --output src/shared/api/generated --client fetch --useOptions"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.26.2",
    "react-dropzone": "^14.2.10"
  },
  "devDependencies": {
    "@playwright/test": "^1.47.2",
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@testing-library/user-event": "^14.5.2",
    "@types/react": "^18.3.10",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "eslint": "^9.11.1",
    "eslint-plugin-boundaries": "^4.2.2",
    "eslint-plugin-import": "^2.30.0",
    "eslint-plugin-react": "^7.36.1",
    "jsdom": "^25.0.0",
    "openapi-typescript-codegen": "^0.29.0",
    "typescript": "^5.6.2",
    "vite": "^5.4.8",
    "vitest": "^2.1.1"
  }
}
```

- [ ] **Step 18.2: `openapi-ts.config.ts`**

```ts
import { defineConfig } from 'openapi-typescript-codegen';
export default defineConfig({
  input: '../../contracts/openapi/gateway-public.v1.yaml',
  output: 'src/shared/api/generated',
  client: 'fetch',
});
```

- [ ] **Step 18.3: Generate client**

Run: `cd apps/frontend && npm install && npm run gen:api`
Expected: `src/shared/api/generated/` is populated with services + DTO types.

- [ ] **Step 18.4: `shared/api/client.ts`**

```ts
import { OpenAPI } from './generated/core/OpenAPI';

export function configureApi(token: string | null) {
  OpenAPI.BASE = (import.meta.env.VITE_API_BASE as string) ?? '/api/v1';
  OpenAPI.TOKEN = token ?? undefined;
}
```

- [ ] **Step 18.5: Write failing auth unit test**

`apps/frontend/tests/unit/auth.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { LoginForm } from '../../src/features/auth/ui/LoginForm';

describe('LoginForm', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('calls onSubmit with email and password', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText(/email/i), 'a@b.co');
    await userEvent.type(screen.getByLabelText(/password/i), 'hunter2hunter2');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(onSubmit).toHaveBeenCalledWith({ email: 'a@b.co', password: 'hunter2hunter2' });
  });

  it('validates required fields', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm onSubmit={onSubmit} />);
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 18.6: Run — expect failure**

Run: `cd apps/frontend && npm test -- auth.test.tsx`
Expected: FAIL — `LoginForm` missing.

- [ ] **Step 18.7: `features/auth/ui/LoginForm.tsx`**

```tsx
import { FormEvent, useState } from 'react';

interface Props {
  onSubmit: (creds: { email: string; password: string }) => Promise<void>;
}

export function LoginForm({ onSubmit }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    setBusy(true); setError(null);
    try { await onSubmit({ email, password }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email}
             onChange={e => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password}
             onChange={e => setPassword(e.target.value)} required minLength={8} />
      <button type="submit" disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</button>
      {error && <div role="alert">{error}</div>}
    </form>
  );
}
```

- [ ] **Step 18.8: `features/auth/ui/SignupForm.tsx`**

```tsx
import { FormEvent, useState } from 'react';

interface Props {
  onSubmit: (data: { email: string; password: string; displayName?: string }) => Promise<void>;
}

export function SignupForm({ onSubmit }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!email || password.length < 8) return;
    setBusy(true); setError(null);
    try { await onSubmit({ email, password, displayName: displayName || undefined }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit}>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password}
             onChange={e => setPassword(e.target.value)} required minLength={8} />
      <label htmlFor="displayName">Display name</label>
      <input id="displayName" value={displayName} onChange={e => setDisplayName(e.target.value)} />
      <button type="submit" disabled={busy}>{busy ? 'Creating…' : 'Sign up'}</button>
      {error && <div role="alert">{error}</div>}
    </form>
  );
}
```

- [ ] **Step 18.9: `features/auth/api/index.ts`**

```ts
import { AuthService } from '../../../shared/api/generated/services/AuthService';
import { configureApi } from '../../../shared/api/client';

export interface AuthSession {
  token: string;
  user: { id: string; email: string; displayName?: string | null };
}

export async function signup(email: string, password: string, displayName?: string): Promise<AuthSession> {
  configureApi(null);
  const res = await AuthService.signup({ requestBody: { email, password, displayName } });
  return res as AuthSession;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  configureApi(null);
  const res = await AuthService.login({ requestBody: { email, password } });
  return res as AuthSession;
}

export async function me(token: string) {
  configureApi(token);
  return AuthService.me();
}
```

- [ ] **Step 18.10: `features/auth/state/useAuth.ts`**

```ts
import { useContext } from 'react';
import { AuthContext } from '../../../app/providers/AuthProvider';

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
```

- [ ] **Step 18.11: `app/providers/AuthProvider.tsx`**

```tsx
import { createContext, ReactNode, useEffect, useState, useCallback } from 'react';
import * as authApi from '../../features/auth/api';
import { configureApi } from '../../shared/api/client';

interface AuthState {
  token: string | null;
  user: authApi.AuthSession['user'] | null;
  signup: (e: string, p: string, dn?: string) => Promise<void>;
  login: (e: string, p: string) => Promise<void>;
  logout: () => void;
}

const STORAGE_KEY = 'fna.session';

export const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<authApi.AuthSession['user'] | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const s = JSON.parse(raw) as authApi.AuthSession;
        setToken(s.token); setUser(s.user); configureApi(s.token);
      } catch { /* corrupt — clear */ localStorage.removeItem(STORAGE_KEY); }
    }
  }, []);

  const persist = useCallback((s: authApi.AuthSession) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    setToken(s.token); setUser(s.user); configureApi(s.token);
  }, []);

  const signup = useCallback(async (email: string, password: string, displayName?: string) => {
    persist(await authApi.signup(email, password, displayName));
  }, [persist]);

  const login = useCallback(async (email: string, password: string) => {
    persist(await authApi.login(email, password));
  }, [persist]);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null); setUser(null); configureApi(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, signup, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

- [ ] **Step 18.12: `features/auth/index.ts`**

```ts
export { LoginForm } from './ui/LoginForm';
export { SignupForm } from './ui/SignupForm';
export { useAuth } from './state/useAuth';
```

- [ ] **Step 18.13: Pages**

`apps/frontend/src/pages/LoginPage.tsx`:

```tsx
import { useNavigate } from 'react-router-dom';
import { LoginForm, useAuth } from '../features/auth';

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  return (
    <main>
      <h1>Log in</h1>
      <LoginForm onSubmit={async ({ email, password }) => {
        await login(email, password); nav('/');
      }} />
    </main>
  );
}
```

`apps/frontend/src/pages/SignupPage.tsx`:

```tsx
import { useNavigate } from 'react-router-dom';
import { SignupForm, useAuth } from '../features/auth';

export function SignupPage() {
  const { signup } = useAuth();
  const nav = useNavigate();
  return (
    <main>
      <h1>Sign up</h1>
      <SignupForm onSubmit={async ({ email, password, displayName }) => {
        await signup(email, password, displayName); nav('/');
      }} />
    </main>
  );
}
```

- [ ] **Step 18.14: Run unit test**

Run: `cd apps/frontend && npm test -- auth.test.tsx`
Expected: PASS.

- [ ] **Step 18.15: Commit**

```bash
git add apps/frontend
git commit -m "feat(frontend): generated API client + auth feature (login/signup)

Closes #TBD"
```

---

## Task 19: Frontend — Upload feature with detection result

**Files:**
- Create: `apps/frontend/src/features/upload/api/index.ts`
- Create: `apps/frontend/src/features/upload/state/useUpload.ts`
- Create: `apps/frontend/src/features/upload/ui/Dropzone.tsx`
- Create: `apps/frontend/src/features/upload/ui/DetectionPanel.tsx`
- Create: `apps/frontend/src/features/upload/index.ts`
- Test: `apps/frontend/tests/unit/upload.test.tsx`

- [ ] **Step 19.1: Failing dropzone test**

`apps/frontend/tests/unit/upload.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Dropzone } from '../../src/features/upload/ui/Dropzone';

describe('Dropzone', () => {
  it('invokes onSelect when a file is chosen', async () => {
    const onSelect = vi.fn();
    render(<Dropzone onSelect={onSelect} />);
    const input = screen.getByLabelText(/upload csv or json/i) as HTMLInputElement;
    const file = new File(['name,age\nA,1'], 'x.csv', { type: 'text/csv' });
    await userEvent.upload(input, file);
    expect(onSelect).toHaveBeenCalledWith(file);
  });
});
```

- [ ] **Step 19.2: Run — expect failure**

Run: `cd apps/frontend && npm test -- upload.test.tsx`
Expected: FAIL.

- [ ] **Step 19.3: `features/upload/ui/Dropzone.tsx`**

```tsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface Props { onSelect: (file: File) => void; }

export function Dropzone({ onSelect }: Props) {
  const onDrop = useCallback((files: File[]) => {
    if (files.length > 0) onSelect(files[0]);
  }, [onSelect]);
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, multiple: false, accept: { 'text/csv': ['.csv'], 'application/json': ['.json'] },
  });
  return (
    <div {...getRootProps()} role="button" aria-label="Upload CSV or JSON">
      <input {...getInputProps({ id: 'upload-input' })} aria-label="Upload CSV or JSON" />
      <p>{isDragActive ? 'Drop the file here' : 'Drop a CSV or JSON file, or click to choose'}</p>
    </div>
  );
}
```

- [ ] **Step 19.4: `features/upload/api/index.ts`**

```ts
import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { UploadService } from '../../../shared/api/generated/services/UploadService';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export interface UploadResult {
  uploadId: string;
  ref: string;
  sizeBytes: number;
}

export async function uploadFile(file: File, token: string): Promise<UploadResult> {
  OpenAPI.TOKEN = token;
  // openapi-typescript-codegen's multipart body uses a FormData under the hood
  const res = await UploadService.upload({ formData: { file } });
  return res as UploadResult;
}

export async function detect(uploadId: string, token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.detect({ requestBody: { uploadId } });
}
```

- [ ] **Step 19.5: `features/upload/state/useUpload.ts`**

```ts
import { useState } from 'react';
import { useAuth } from '../../auth';
import * as uploadApi from '../api';

export interface DetectedSchemaColumn { name: string; type: string; nullable: boolean }

export function useUpload() {
  const { token } = useAuth();
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [format, setFormat] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [schema, setSchema] = useState<DetectedSchemaColumn[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function select(file: File) {
    if (!token) { setError('You must be logged in'); return; }
    setBusy(true); setError(null);
    try {
      const up = await uploadApi.uploadFile(file, token);
      setUploadId(up.uploadId);
      const det = await uploadApi.detect(up.uploadId, token);
      setFormat(det.format); setConfidence(det.confidence);
      setSchema(det.schema as DetectedSchemaColumn[]);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return { uploadId, format, confidence, schema, error, busy, select };
}
```

- [ ] **Step 19.6: `features/upload/ui/DetectionPanel.tsx`**

```tsx
interface Props {
  format: string;
  confidence: number;
  schema: Array<{ name: string; type: string; nullable: boolean }>;
}

export function DetectionPanel({ format, confidence, schema }: Props) {
  return (
    <section aria-label="detection result">
      <h2>Detected: {format}</h2>
      <p>Confidence: {(confidence * 100).toFixed(0)}%</p>
      <table>
        <thead><tr><th>Column</th><th>Type</th><th>Nullable</th></tr></thead>
        <tbody>
          {schema.map(c => (
            <tr key={c.name}>
              <td>{c.name}</td><td>{c.type}</td><td>{c.nullable ? 'yes' : 'no'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 19.7: `features/upload/index.ts`**

```ts
export { Dropzone } from './ui/Dropzone';
export { DetectionPanel } from './ui/DetectionPanel';
export { useUpload } from './state/useUpload';
```

- [ ] **Step 19.8: Run test**

Run: `cd apps/frontend && npm test -- upload.test.tsx`
Expected: PASS.

- [ ] **Step 19.9: Commit**

```bash
git add apps/frontend
git commit -m "feat(frontend): upload feature with dropzone + detection panel

Closes #TBD"
```

---

## Task 20: Frontend — Filter feature (column picker + preview)

**Files:**
- Create: `apps/frontend/src/features/filter/api/index.ts`
- Create: `apps/frontend/src/features/filter/state/useFilter.ts`
- Create: `apps/frontend/src/features/filter/ui/ColumnPicker.tsx`
- Create: `apps/frontend/src/features/filter/ui/PreviewTable.tsx`
- Create: `apps/frontend/src/features/filter/index.ts`
- Test: `apps/frontend/tests/unit/filter.test.tsx`

- [ ] **Step 20.1: Failing test**

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { ColumnPicker } from '../../src/features/filter/ui/ColumnPicker';

describe('ColumnPicker', () => {
  it('toggles columns and reports selection', async () => {
    const onChange = vi.fn();
    render(<ColumnPicker columns={['a', 'b', 'c']} selected={['a']} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText('b'));
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
  });

  it('select all and none', async () => {
    const onChange = vi.fn();
    render(<ColumnPicker columns={['a', 'b']} selected={[]} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: /select all/i }));
    expect(onChange).toHaveBeenCalledWith(['a', 'b']);
    await userEvent.click(screen.getByRole('button', { name: /select none/i }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});
```

- [ ] **Step 20.2: Run — expect failure**

Run: `cd apps/frontend && npm test -- filter.test.tsx`
Expected: FAIL.

- [ ] **Step 20.3: `features/filter/ui/ColumnPicker.tsx`**

```tsx
interface Props {
  columns: string[];
  selected: string[];
  onChange: (next: string[]) => void;
}

export function ColumnPicker({ columns, selected, onChange }: Props) {
  function toggle(c: string) {
    const set = new Set(selected);
    set.has(c) ? set.delete(c) : set.add(c);
    onChange(columns.filter(col => set.has(col)));
  }
  return (
    <fieldset>
      <legend>Columns to keep</legend>
      <button type="button" onClick={() => onChange([...columns])}>Select all</button>
      <button type="button" onClick={() => onChange([])}>Select none</button>
      <ul>
        {columns.map(c => (
          <li key={c}>
            <label>
              <input type="checkbox" aria-label={c}
                     checked={selected.includes(c)}
                     onChange={() => toggle(c)} />
              {c}
            </label>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
```

- [ ] **Step 20.4: `features/filter/ui/PreviewTable.tsx`**

```tsx
interface Props {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}

export function PreviewTable({ columns, rows }: Props) {
  return (
    <table aria-label="filter preview">
      <thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>{columns.map(c => <td key={c}>{String(r[c] ?? '')}</td>)}</tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 20.5: `features/filter/api/index.ts`**

```ts
import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export async function preview(uploadId: string, keep: string[], token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.filterPreview({
    requestBody: { uploadId, filter: { kind: 'column', keep }, sampleSize: 20 },
  });
}
```

- [ ] **Step 20.6: `features/filter/state/useFilter.ts`**

```ts
import { useEffect, useState } from 'react';
import { useAuth } from '../../auth';
import * as filterApi from '../api';

export function useFilter(uploadId: string | null, allColumns: string[]) {
  const { token } = useAuth();
  const [selected, setSelected] = useState<string[]>([]);
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { setSelected(allColumns); }, [allColumns.join('|')]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!uploadId || !token || selected.length === 0) { setRows([]); return; }
      setBusy(true); setError(null);
      try {
        const r = await filterApi.preview(uploadId, selected, token);
        if (!cancelled) setRows((r.rows ?? []) as Array<Record<string, unknown>>);
      } catch (e) { if (!cancelled) setError((e as Error).message); }
      finally { if (!cancelled) setBusy(false); }
    }
    run();
    return () => { cancelled = true; };
  }, [uploadId, token, selected.join('|')]);

  return { selected, setSelected, rows, error, busy };
}
```

- [ ] **Step 20.7: `features/filter/index.ts`**

```ts
export { ColumnPicker } from './ui/ColumnPicker';
export { PreviewTable } from './ui/PreviewTable';
export { useFilter } from './state/useFilter';
```

- [ ] **Step 20.8: Run test — must pass**

Run: `cd apps/frontend && npm test -- filter.test.tsx`
Expected: PASS.

- [ ] **Step 20.9: Commit**

```bash
git add apps/frontend
git commit -m "feat(frontend): filter feature (column picker + preview)

Closes #TBD"
```

---

## Task 21: Frontend — Download feature, workbench page, app shell

**Files:**
- Create: `apps/frontend/src/features/download/api/index.ts`
- Create: `apps/frontend/src/features/download/state/useDownload.ts`
- Create: `apps/frontend/src/features/download/ui/FormatChooser.tsx`
- Create: `apps/frontend/src/features/download/ui/DownloadButton.tsx`
- Create: `apps/frontend/src/features/download/index.ts`
- Create: `apps/frontend/src/pages/WorkbenchPage.tsx`
- Create: `apps/frontend/src/app/router.tsx`
- Create: `apps/frontend/src/app/App.tsx`
- Create: `apps/frontend/src/main.tsx`
- Create: `apps/frontend/index.html`
- Test: `apps/frontend/tests/unit/download.test.tsx`

- [ ] **Step 21.1: Failing chooser test**

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { FormatChooser } from '../../src/features/download/ui/FormatChooser';

describe('FormatChooser', () => {
  it('reports format change', async () => {
    const onChange = vi.fn();
    render(<FormatChooser value="csv" onChange={onChange} />);
    await userEvent.click(screen.getByLabelText('JSON'));
    expect(onChange).toHaveBeenCalledWith('json');
  });
});
```

- [ ] **Step 21.2: Run — expect failure**

Run: `cd apps/frontend && npm test -- download.test.tsx`
Expected: FAIL.

- [ ] **Step 21.3: `features/download/ui/FormatChooser.tsx`**

```tsx
interface Props {
  value: 'csv' | 'json';
  onChange: (v: 'csv' | 'json') => void;
}

export function FormatChooser({ value, onChange }: Props) {
  return (
    <fieldset>
      <legend>Output format</legend>
      <label><input type="radio" name="fmt" checked={value === 'csv'} onChange={() => onChange('csv')} />CSV</label>
      <label><input type="radio" name="fmt" checked={value === 'json'} onChange={() => onChange('json')} />JSON</label>
    </fieldset>
  );
}
```

- [ ] **Step 21.4: `features/download/ui/DownloadButton.tsx`**

```tsx
interface Props {
  disabled: boolean;
  onClick: () => void;
  busy: boolean;
}

export function DownloadButton({ disabled, onClick, busy }: Props) {
  return (
    <button type="button" onClick={onClick} disabled={disabled || busy}>
      {busy ? 'Preparing…' : 'Download'}
    </button>
  );
}
```

- [ ] **Step 21.5: `features/download/api/index.ts`**

```ts
import { OpenAPI } from '../../../shared/api/generated/core/OpenAPI';
import { PipelineService } from '../../../shared/api/generated/services/PipelineService';

export async function convert(uploadId: string, keep: string[],
                              outputFormat: 'csv' | 'json', token: string) {
  OpenAPI.TOKEN = token;
  return PipelineService.convert({
    requestBody: { uploadId, filter: { kind: 'column', keep }, outputFormat },
  });
}

export function downloadUrl(resultId: string): string {
  const base = (OpenAPI.BASE as string) ?? '/api/v1';
  return `${base}/download/${resultId}`;
}
```

- [ ] **Step 21.6: `features/download/state/useDownload.ts`**

```ts
import { useState } from 'react';
import { useAuth } from '../../auth';
import * as dlApi from '../api';

export function useDownload() {
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(uploadId: string, keep: string[], outputFormat: 'csv' | 'json') {
    if (!token) { setError('Not logged in'); return; }
    setBusy(true); setError(null);
    try {
      const conv = await dlApi.convert(uploadId, keep, outputFormat, token);
      window.location.assign(dlApi.downloadUrl(conv.resultId));
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return { busy, error, run };
}
```

- [ ] **Step 21.7: `features/download/index.ts`**

```ts
export { FormatChooser } from './ui/FormatChooser';
export { DownloadButton } from './ui/DownloadButton';
export { useDownload } from './state/useDownload';
```

- [ ] **Step 21.8: `pages/WorkbenchPage.tsx`**

```tsx
import { useState } from 'react';
import { Dropzone, DetectionPanel, useUpload } from '../features/upload';
import { ColumnPicker, PreviewTable, useFilter } from '../features/filter';
import { FormatChooser, DownloadButton, useDownload } from '../features/download';
import { useAuth } from '../features/auth';

export function WorkbenchPage() {
  const { user, logout } = useAuth();
  const up = useUpload();
  const columnNames = up.schema.map(c => c.name);
  const flt = useFilter(up.uploadId, columnNames);
  const dl = useDownload();
  const [fmt, setFmt] = useState<'csv' | 'json'>('csv');

  return (
    <main>
      <header>
        <h1>FilterNArrange</h1>
        <div>{user?.email} <button onClick={logout}>Log out</button></div>
      </header>
      <Dropzone onSelect={up.select} />
      {up.busy && <p>Working…</p>}
      {up.error && <p role="alert">{up.error}</p>}
      {up.format && (
        <DetectionPanel format={up.format} confidence={up.confidence!} schema={up.schema} />
      )}
      {columnNames.length > 0 && (
        <>
          <ColumnPicker columns={columnNames} selected={flt.selected} onChange={flt.setSelected} />
          <PreviewTable columns={flt.selected} rows={flt.rows} />
          <FormatChooser value={fmt} onChange={setFmt} />
          <DownloadButton busy={dl.busy}
            disabled={!up.uploadId || flt.selected.length === 0}
            onClick={() => up.uploadId && dl.run(up.uploadId, flt.selected, fmt)} />
          {dl.error && <p role="alert">{dl.error}</p>}
        </>
      )}
    </main>
  );
}
```

- [ ] **Step 21.9: `app/router.tsx`**

```tsx
import { Navigate, Route, Routes } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { SignupPage } from '../pages/SignupPage';
import { WorkbenchPage } from '../pages/WorkbenchPage';
import { useAuth } from '../features/auth';

function Private({ children }: { children: JSX.Element }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

export function Router() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/" element={<Private><WorkbenchPage /></Private>} />
    </Routes>
  );
}
```

- [ ] **Step 21.10: `app/App.tsx`**

```tsx
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './providers/AuthProvider';
import { Router } from './router';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Router />
      </AuthProvider>
    </BrowserRouter>
  );
}
```

- [ ] **Step 21.11: `main.tsx` and `index.html`**

`apps/frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
```

`apps/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>FilterNArrange</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 21.12: Run all unit tests**

Run: `cd apps/frontend && npm test`
Expected: PASS (auth + upload + filter + download).

- [ ] **Step 21.13: Commit**

```bash
git add apps/frontend
git commit -m "feat(frontend): download feature + workbench page + app shell

Closes #TBD"
```

---

## Task 22: Frontend — eslint-plugin-boundaries config

**Files:**
- Create: `apps/frontend/.eslintrc.cjs`

- [ ] **Step 22.1: Create `.eslintrc.cjs`**

```js
module.exports = {
  root: true,
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 2023, sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['boundaries', 'import', 'react'],
  settings: {
    react: { version: 'detect' },
    'boundaries/elements': [
      { type: 'app',      pattern: 'src/app/**' },
      { type: 'pages',    pattern: 'src/pages/**' },
      { type: 'features', pattern: 'src/features/*' },
      { type: 'shared',   pattern: 'src/shared/**' },
    ],
  },
  rules: {
    'boundaries/element-types': ['error', {
      default: 'disallow',
      rules: [
        { from: 'app',      allow: ['pages', 'features', 'shared'] },
        { from: 'pages',    allow: ['features', 'shared'] },
        { from: 'features', allow: ['shared'] },
        { from: 'shared',   allow: ['shared'] },
      ],
    }],
    'boundaries/no-private': ['error', { allowUncles: false }],
    'import/no-default-export': 'off',
  },
  ignorePatterns: ['dist', 'src/shared/api/generated', 'tests'],
};
```

- [ ] **Step 22.2: Run lint**

Run: `cd apps/frontend && npm run lint`
Expected: PASS. If a feature imports another feature, the violation must be fixed by moving shared code into `src/shared/`.

- [ ] **Step 22.3: Commit**

```bash
git add apps/frontend/.eslintrc.cjs
git commit -m "build(frontend): eslint-plugin-boundaries to enforce feature isolation

Closes #TBD"
```

---

## Task 23: Integration — testcontainers walking-skeleton test

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_walking_skeleton.py`
- Create: `tests/fixtures/sample.csv`
- Create: `tests/integration/pyproject.toml`

- [ ] **Step 23.1: Sample fixture**

`tests/fixtures/sample.csv`:

```
name,age,country
Alice,30,IN
Bob,25,US
Carol,42,IN
Dan,18,UK
```

- [ ] **Step 23.2: Integration project metadata**

`tests/integration/pyproject.toml`:

```toml
[project]
name = "filternarrange-integration-tests"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "pytest==8.3.3",
  "httpx==0.27.2",
  "testcontainers[minio,postgres]==4.8.1",
  "docker==7.1.0",
]

[tool.pytest.ini_options]
testpaths = ["."]
```

- [ ] **Step 23.3: `conftest.py` — bring up the stack**

```python
"""Boot the docker-compose stack for integration tests.

Plan A defines an infra/docker-compose.yml with: postgres, redis, minio,
gateway, data-engine, frontend. We assume that file exists and `docker compose`
is installed.
"""
import subprocess
import time
import socket
import pathlib
import pytest
import httpx

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "infra" / "docker-compose.yml"


def _wait_for_http(url: str, timeout: float = 60.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500: return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError(f"timeout waiting for {url}")


@pytest.fixture(scope="session")
def stack():
    subprocess.run(["docker", "compose", "-f", str(COMPOSE), "up", "-d",
                    "postgres", "redis", "minio", "data-engine", "gateway"],
                   check=True)
    try:
        _wait_for_http("http://localhost:8080/actuator/health")
        _wait_for_http("http://localhost:8000/healthz")
        yield {"gateway": "http://localhost:8080", "engine": "http://localhost:8000"}
    finally:
        subprocess.run(["docker", "compose", "-f", str(COMPOSE), "down", "-v"],
                       check=False)
```

- [ ] **Step 23.4: Write the failing happy-path test**

```python
"""End-to-end: signup → upload → detect → filter → convert → download."""
import pathlib
import httpx
import pytest

FIX = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample.csv"


def test_walking_skeleton(stack):
    gw = stack["gateway"]
    with httpx.Client(base_url=gw, timeout=30.0) as c:
        r = c.post("/api/v1/auth/signup", json={
            "email": "e2e@filternarrange.io", "password": "hunter2hunter2",
        })
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}

        with FIX.open("rb") as f:
            r = c.post("/api/v1/upload", headers=h,
                       files={"file": ("sample.csv", f, "text/csv")})
        assert r.status_code == 200, r.text
        upload_id = r.json()["uploadId"]

        r = c.post("/api/v1/detect", headers=h, json={"uploadId": upload_id})
        assert r.status_code == 200, r.text
        det = r.json()
        assert det["format"] == "csv"
        names = [col["name"] for col in det["schema"]]
        assert {"name", "age", "country"}.issubset(set(names))

        r = c.post("/api/v1/filter/preview", headers=h, json={
            "uploadId": upload_id,
            "filter": {"kind": "column", "keep": ["name", "country"]},
            "sampleSize": 10,
        })
        assert r.status_code == 200, r.text
        prev = r.json()
        assert [c["name"] for c in prev["schema"]] == ["name", "country"]
        assert any(row.get("name") == "Alice" for row in prev["rows"])

        r = c.post("/api/v1/convert", headers=h, json={
            "uploadId": upload_id,
            "filter": {"kind": "column", "keep": ["name", "country"]},
            "outputFormat": "json",
        })
        assert r.status_code == 200, r.text
        result_id = r.json()["resultId"]

        r = c.get(f"/api/v1/download/{result_id}", headers=h, follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["Location"]
        assert location.startswith("http")

        # Fetch the actual blob from the pre-signed URL
        with httpx.Client(timeout=30.0) as raw:
            blob = raw.get(location)
        assert blob.status_code == 200
        body = blob.text
        assert "Alice" in body and "IN" in body
        # age column should have been projected away
        assert "30" not in body or '"age"' not in body
```

- [ ] **Step 23.5: Run the test**

Run: `cd tests/integration && uv run pytest -v`
Expected: PASS (depends on Plan A docker-compose having gateway + data-engine + postgres + minio configured).

- [ ] **Step 23.6: Commit**

```bash
git add tests/integration tests/fixtures
git commit -m "test: walking-skeleton integration test (signup→upload→detect→filter→convert→download)

Closes #TBD"
```

---

## Task 24: E2E — Playwright walking-skeleton spec

**Files:**
- Create: `apps/frontend/playwright.config.ts`
- Create: `apps/frontend/tests/e2e/walking-skeleton.spec.ts`

- [ ] **Step 24.1: `playwright.config.ts`**

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: true },
});
```

- [ ] **Step 24.2: `walking-skeleton.spec.ts`**

```ts
import { test, expect } from '@playwright/test';
import path from 'node:path';

const FIXTURE = path.resolve(__dirname, '../../../../tests/fixtures/sample.csv');

test('user can signup, upload, filter, and download', async ({ page }) => {
  const email = `e2e-${Date.now()}@filternarrange.io`;
  await page.goto('/signup');
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill('hunter2hunter2');
  await page.getByRole('button', { name: /sign up/i }).click();

  // Lands on workbench
  await expect(page).toHaveURL('/');
  await expect(page.getByRole('heading', { name: /filternarrange/i })).toBeVisible();

  // Upload
  const fileInput = page.getByLabel(/upload csv or json/i);
  await fileInput.setInputFiles(FIXTURE);
  await expect(page.getByText(/Detected: csv/i)).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('cell', { name: 'name' })).toBeVisible();

  // Deselect age, keep name + country
  await page.getByLabel('age').uncheck();
  await expect(page.getByRole('table', { name: /filter preview/i })).toBeVisible();

  // Switch format to JSON and download
  await page.getByLabel('JSON').check();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /^download$/i }).click();
  const download = await downloadPromise;
  const fp = await download.path();
  expect(fp).toBeTruthy();
});
```

- [ ] **Step 24.3: Install Playwright browsers**

Run: `cd apps/frontend && npx playwright install --with-deps chromium`
Expected: success.

- [ ] **Step 24.4: Run E2E (against the docker compose stack)**

Run:
```
docker compose -f infra/docker-compose.yml up -d
cd apps/frontend && E2E_BASE_URL=http://localhost npm run test:e2e
```
Expected: PASS. Tear down with `docker compose -f infra/docker-compose.yml down -v`.

- [ ] **Step 24.5: Commit**

```bash
git add apps/frontend/playwright.config.ts apps/frontend/tests/e2e
git commit -m "test(frontend): Playwright walking-skeleton happy-path

Closes #TBD"
```

---

## Self-Review

**Spec coverage check (against `docs/superpowers/specs/2026-06-07-filternarrange-design.md`):**

- §3 Sync path (detect → filter preview → convert): Tasks 6, 7, 16
- §4 Plugin model — canonical model, FormatPlugin, FilterPlugin, manifest TOML, entry-point registry, dispatcher with PluginResult envelope, `FILTERNARRANGE_DISABLED_PLUGINS`: Tasks 9, 10, 11, 13–15
- §5 Postgres `users` table + Flyway: Task 2 (note: `external_id` is intentionally deferred to Plan G per scope)
- §5 MinIO buckets `uploads`, `results`, `format-samples`, `backups` bootstrap: Task 5
- §5 Redis-backed sessions + DB record for revocation: V2 migration in Task 2; gateway-level session persistence and revocation API are not in walking-skeleton scope but the schema is laid so Plan G can plug into it without a migration
- §6 hexagonal layering with CI enforcement: Task 8 (ArchUnit) + Task 17 (import-linter) + Task 22 (eslint-plugin-boundaries)
- §6 Error envelope `{ code, plugin_id?, message, trace_id }`: Tasks 4 (gateway), 11 (engine), 16 (engine)
- §6 Timeouts: Task 6 sets connect=2 s, read=5 s; circuit-breaker config in Task 6 application.yml
- Contracts as source-of-truth + oasdiff gate: Task 1
- Frontend client generated from contract: Task 18 (`gen:api` script)
- Walking-skeleton flow: Tasks 18–24

**Spec items intentionally deferred (matches "Out of scope for Plan B" in the prompt):**

- Other formats (Plan C): xml/yaml/jsonl/tsv/xlsx
- Other filter modes (Plan C): row, expression, regex
- Async / Kafka (Plan D)
- AI features (Plan E)
- Tier enforcement, quotas, format-request workflow (Plan F)
- Keycloak + `external_id` column on users (Plan G)
- Saved recipes, audit log, subscriptions, format_requests tables (later plans)

**Type / name consistency checks:**

- `EngineDtos.Column.type` is `String` on Java side and `string` on the OpenAPI side; both use the same six-value enum from §4 (`string|number|integer|boolean|datetime|null`).
- `ColumnFilterSpec` shape — `{ kind: "column", keep: string[] }` — used identically in: OpenAPI public + internal (Task 1), gateway DTO `ColumnFilterSpecDto` (Task 7), engine pydantic schema (Task 16), filter plugin (Task 15).
- `PluginResult` field set `{ is_ok, value, code, plugin_id, plugin_version, message, trace_id }` is consistent across Task 10 definition, Task 11 dispatcher.
- `TabularData.rows: AsyncIterator[dict]` used identically across canonical (Task 9), CSV plugin parse (Task 13), JSON plugin parse (Task 14), filter plugin apply (Task 15), and FilterService.collect (Task 16).

**Placeholder scan:** plan contains no "TODO", "TBD", "implement later", or hand-wavy "add appropriate X" — every code block is concrete. (`Closes #TBD` is a deliberate convention from the prompt, not a placeholder for plan content.)

**No-placeholder spot fixes:** none required.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-07-B-walking-skeleton.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Use `superpowers:subagent-driven-development`.
2. **Inline Execution** — execute tasks in this session via `superpowers:executing-plans` with checkpoints.

Which approach?
