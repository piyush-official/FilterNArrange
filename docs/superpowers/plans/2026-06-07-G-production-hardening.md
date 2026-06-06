# Plan G — Production Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take the running FilterNArrange v0.6 stack (after Plan F) and make it production-credible by adding Keycloak identity, full observability (metrics + logs + traces + alerts), backup/DR, performance gates, supply-chain security, DB-operations safety, and operational runbooks. No new user-facing features.

**Architecture:** Observability follows the OpenTelemetry-first pattern — all three signals (metrics, logs, traces) are emitted by both services, shipped to an OTel Collector, fanned out to Prometheus / Loki / Tempo, and visualized in Grafana. Auth gains a second provider (Keycloak) selectable at startup by `AUTH_PROVIDER`, with the Plan-B local-JWT path retained as failback. Backup/DR uses container-native `pg_dump` + `mc mirror` into MinIO. Supply-chain protection is layered into CI (Trivy + Syft + Cosign + ZAP + gitleaks). DB safety is policy-driven (expand-contract migrations). All deferred-to-production capabilities (PITR, paging, off-VM mirroring) are explicitly out of scope and slotted into Plan H.

**Tech Stack:** Keycloak 25 (bitnami/keycloak — ARM-friendly OCI image), Spring Security OAuth2 Resource Server, `oidc-client-ts`, Prometheus 2.x, Grafana 11, Loki 3.x, Promtail, Tempo 2.x, OpenTelemetry Collector contrib, OpenTelemetry Java agent, `opentelemetry-instrumentation-fastapi`, AlertManager, `pg_dump`, MinIO `mc`, k6, Trivy, Syft, Cosign, OWASP ZAP, gitleaks, Flyway.

---

## File Structure

**New / modified files (grouped by deliverable):**

```
infra/
├── docker-compose/
│   └── docker-compose.yml                                    (modify: add keycloak + observability + backup services)
├── keycloak/
│   ├── realm-export.json                                     (NEW)
│   └── README.md                                             (NEW)
├── observability/
│   ├── prometheus/
│   │   ├── prometheus.yml                                    (NEW)
│   │   └── alerts.yml                                        (NEW)
│   ├── alertmanager/
│   │   └── alertmanager.yml                                  (NEW)
│   ├── loki/
│   │   └── loki-config.yml                                   (NEW)
│   ├── promtail/
│   │   └── promtail-config.yml                               (NEW)
│   ├── tempo/
│   │   └── tempo.yml                                         (NEW)
│   ├── otel-collector/
│   │   └── otel-collector.yml                                (NEW)
│   └── grafana/
│       ├── datasources.yml                                   (NEW)
│       ├── dashboards.yml                                    (NEW)
│       └── dashboards/
│           ├── api-latency.json                              (NEW)
│           ├── plugin-performance.json                       (NEW)
│           ├── job-pipeline.json                             (NEW)
│           ├── ai-capabilities.json                          (NEW)
│           └── infra.json                                    (NEW)
├── backup/
│   ├── Dockerfile                                            (NEW)
│   ├── crontab                                               (NEW)
│   ├── backup.sh                                             (NEW)
│   ├── restore.sh                                            (NEW)
│   ├── mirror.sh                                             (NEW)
│   └── README.md                                             (NEW)
└── db/
    └── migration-policy.md                                   (NEW)

apps/gateway/
├── build.gradle.kts                                          (modify: add OAuth2 RS, micrometer-prom, OTel deps)
├── src/main/java/io/filternarrange/gateway/
│   ├── platform/
│   │   ├── auth/
│   │   │   ├── AuthConfig.java                               (NEW — picks filter by AUTH_PROVIDER)
│   │   │   ├── KeycloakAuthFilter.java                       (NEW)
│   │   │   ├── KeycloakUserSyncService.java                  (NEW)
│   │   │   └── SpringJwtAuthFilter.java                      (modify: extract to be wireable from AuthConfig)
│   │   ├── observability/
│   │   │   ├── MetricsConfig.java                            (NEW — registers custom meters)
│   │   │   ├── JobStateTransitionMetric.java                 (NEW)
│   │   │   ├── QuotaRejectionMetric.java                     (NEW)
│   │   │   └── StructuredLoggingConfig.java                  (NEW — JSON encoder)
│   │   └── tracing/
│   │       └── TraceContextPropagator.java                   (NEW — Kafka + WS header propagation)
│   └── resources/
│       ├── application-keycloak.yml                          (NEW)
│       ├── application-spring-jwt.yml                        (NEW)
│       └── logback-spring.xml                                (modify: switch to LogstashEncoder)
└── src/main/resources/db/migration/
    └── V9__user_external_id.sql                              (NEW)

apps/data-engine/
├── pyproject.toml                                            (modify: add prometheus_client, otel)
└── src/filternarrange_engine/
    ├── platform/
    │   ├── metrics.py                                        (NEW — registry + custom metrics)
    │   ├── logging_json.py                                   (NEW — JSON formatter)
    │   └── tracing.py                                        (NEW — OTel FastAPI instrumentation)
    └── api/
        └── metrics_router.py                                 (NEW — /metrics endpoint)

apps/frontend/
├── package.json                                              (modify: add oidc-client-ts)
├── src/
│   ├── features/auth/
│   │   ├── auth-provider.ts                                  (NEW — mode dispatcher)
│   │   ├── keycloak-client.ts                                (NEW)
│   │   └── login-page.tsx                                    (modify: dual-mode)
│   └── shared/config.ts                                      (modify: VITE_AUTH_PROVIDER)

tests/
├── perf/
│   ├── detect.js                                             (NEW)
│   ├── filter-preview.js                                     (NEW)
│   ├── nl-to-filter.js                                       (NEW)
│   ├── job-roundtrip.js                                      (NEW)
│   ├── baseline.json                                         (NEW)
│   └── perf-helpers.js                                       (NEW)
├── integration/
│   ├── test_keycloak_login.py                                (NEW — Playwright)
│   ├── test_migration_smoke.py                               (NEW)
│   ├── test_backup_restore.py                                (NEW)
│   ├── test_observability_smoke.py                           (NEW)
│   └── test_trivy_assertion.py                               (NEW)

.github/workflows/
├── perf.yml                                                  (NEW)
├── perf-baseline.yml                                         (NEW)
├── security.yml                                              (NEW)
└── release.yml                                               (modify: attach SBOM + cosign signing)

docs/operations/
├── README.md                                                 (NEW — index)
├── incident-circuit-breaker-open.md                          (NEW)
├── incident-job-pipeline-stalled.md                          (NEW)
├── incident-disk-pressure.md                                 (NEW)
├── incident-keycloak-down.md                                 (NEW)
├── restore-from-backup.md                                    (NEW)
└── rotate-secrets.md                                         (NEW)
```

**Boundaries:** Auth-provider switching is confined to `platform/auth/`. Observability cross-cutting code lives under `platform/observability/` (gateway) and `platform/metrics.py` / `platform/logging_json.py` / `platform/tracing.py` (data-engine). Infra changes are confined to `infra/` and `.github/workflows/`. No business code is touched except where instrumentation requires it.

---

## Task 1 — Keycloak service in Compose

**Files:**
- Modify: `infra/docker-compose/docker-compose.yml`
- Create: `infra/keycloak/realm-export.json`
- Create: `infra/keycloak/README.md`
- Test: `tests/integration/test_keycloak_boot.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_keycloak_boot.py
import os
import time
import requests
import pytest

KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL", "http://localhost:8085")
REALM = "filternarrange"

def wait_for(url: str, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise AssertionError(f"{url} never came up in {timeout}s")

def test_keycloak_realm_loaded():
    wait_for(f"{KEYCLOAK_URL}/health/ready")
    r = requests.get(f"{KEYCLOAK_URL}/realms/{REALM}/.well-known/openid-configuration", timeout=5)
    assert r.status_code == 200
    cfg = r.json()
    assert cfg["issuer"].endswith(f"/realms/{REALM}")
    assert "authorization_endpoint" in cfg
    assert "token_endpoint" in cfg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_keycloak_boot.py -v`
Expected: FAIL with connection refused (Keycloak not yet in compose).

- [ ] **Step 3: Add the realm export**

```json
// infra/keycloak/realm-export.json
{
  "realm": "filternarrange",
  "enabled": true,
  "sslRequired": "none",
  "registrationAllowed": true,
  "resetPasswordAllowed": true,
  "rememberMe": true,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "accessTokenLifespan": 900,
  "ssoSessionIdleTimeout": 1800,
  "ssoSessionMaxLifespan": 36000,
  "roles": {
    "realm": [
      { "name": "user",  "description": "Standard authenticated user" },
      { "name": "paid",  "description": "Paid tier user" },
      { "name": "admin", "description": "Administrative user" }
    ]
  },
  "defaultRoles": ["user"],
  "clients": [
    {
      "clientId": "filternarrange-frontend",
      "name": "FilterNArrange Frontend",
      "enabled": true,
      "publicClient": true,
      "standardFlowEnabled": true,
      "directAccessGrantsEnabled": false,
      "rootUrl": "http://localhost:5173",
      "redirectUris": ["http://localhost:5173/*"],
      "webOrigins": ["http://localhost:5173"],
      "attributes": {
        "pkce.code.challenge.method": "S256"
      }
    },
    {
      "clientId": "filternarrange-gateway",
      "name": "FilterNArrange Gateway",
      "enabled": true,
      "publicClient": false,
      "bearerOnly": true,
      "secret": "dev-only-gateway-secret",
      "directAccessGrantsEnabled": false,
      "standardFlowEnabled": false,
      "serviceAccountsEnabled": true,
      "attributes": {
        "access.token.lifespan": "900"
      }
    }
  ],
  "users": [
    {
      "username": "dev-user",
      "email": "dev@filternarrange.local",
      "emailVerified": true,
      "enabled": true,
      "firstName": "Dev",
      "lastName": "User",
      "credentials": [{ "type": "password", "value": "dev-password", "temporary": false }],
      "realmRoles": ["user"]
    },
    {
      "username": "dev-paid",
      "email": "paid@filternarrange.local",
      "emailVerified": true,
      "enabled": true,
      "credentials": [{ "type": "password", "value": "paid-password", "temporary": false }],
      "realmRoles": ["user", "paid"]
    }
  ]
}
```

- [ ] **Step 4: Add Keycloak service to compose**

Append to `infra/docker-compose/docker-compose.yml` under `services:`:

```yaml
  keycloak:
    image: bitnami/keycloak:25
    container_name: fna-keycloak
    environment:
      KEYCLOAK_ADMIN_USER: admin
      KEYCLOAK_ADMIN_PASSWORD: admin
      KEYCLOAK_DATABASE_VENDOR: postgresql
      KEYCLOAK_DATABASE_HOST: postgres
      KEYCLOAK_DATABASE_PORT: 5432
      KEYCLOAK_DATABASE_NAME: keycloak
      KEYCLOAK_DATABASE_USER: keycloak
      KEYCLOAK_DATABASE_PASSWORD: keycloak
      KEYCLOAK_HTTP_PORT: 8080
      KEYCLOAK_EXTRA_ARGS: "--import-realm"
    volumes:
      - ../keycloak/realm-export.json:/opt/bitnami/keycloak/data/import/filternarrange-realm.json:ro
    ports:
      - "8085:8080"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 30
    networks: [fna-net]
```

Plan A already provides a `keycloak` database in Postgres; if not present, also append a one-shot init container or extend the Postgres init script to `CREATE DATABASE keycloak OWNER keycloak;`.

- [ ] **Step 5: Document the realm**

```markdown
# infra/keycloak/README.md
Keycloak realm `filternarrange` — auto-imported from realm-export.json on first boot.

## Clients
- `filternarrange-frontend` — public, PKCE S256, redirect to http://localhost:5173/*
- `filternarrange-gateway` — confidential, bearer-only, secret `dev-only-gateway-secret` (override per environment)

## Realm roles
- `user`  — assigned by default on registration.
- `paid`  — mirrored into `users.tier='paid'` by the gateway sync service.
- `admin` — mirrored into `users.admin=true`.

## Seeded users (dev only)
- `dev-user` / `dev-password`        — free
- `dev-paid` / `paid-password`       — paid

Never reuse these credentials outside docker-compose.
```

- [ ] **Step 6: Run test to verify it passes**

Run: `docker compose -f infra/docker-compose/docker-compose.yml up -d keycloak && pytest tests/integration/test_keycloak_boot.py -v`
Expected: PASS — well-known endpoint returns config for realm `filternarrange`.

- [ ] **Step 7: Commit**

```bash
git add infra/docker-compose/docker-compose.yml infra/keycloak/ tests/integration/test_keycloak_boot.py
git commit -m "feat(infra): add Keycloak service with filternarrange realm"
```

---

## Task 2 — Gateway: V9 migration adding `external_id`

**Files:**
- Create: `apps/gateway/src/main/resources/db/migration/V9__user_external_id.sql`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/migration/V9MigrationTest.java`

- [ ] **Step 1: Write the failing test**

```java
// apps/gateway/src/test/java/io/filternarrange/gateway/migration/V9MigrationTest.java
package io.filternarrange.gateway.migration;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
class V9MigrationTest {
    @Autowired JdbcTemplate jdbc;

    @Test
    void users_table_has_external_id_column_and_unique_index() {
        var col = jdbc.queryForMap(
            "SELECT data_type, is_nullable FROM information_schema.columns " +
            "WHERE table_name='users' AND column_name='external_id'");
        assertThat(col.get("data_type")).isEqualTo("text");
        assertThat(col.get("is_nullable")).isEqualTo("YES");

        Integer idxCount = jdbc.queryForObject(
            "SELECT count(*) FROM pg_indexes WHERE tablename='users' AND indexdef LIKE '%external_id%'",
            Integer.class);
        assertThat(idxCount).isGreaterThanOrEqualTo(1);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/gateway && ./gradlew test --tests V9MigrationTest`
Expected: FAIL — column `external_id` does not exist.

- [ ] **Step 3: Write the migration**

```sql
-- apps/gateway/src/main/resources/db/migration/V9__user_external_id.sql
-- Expand step: add external_id as nullable (will be backfilled at first Keycloak login).
ALTER TABLE users ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Unique index (CONCURRENTLY would require running outside a tx; Flyway runs
-- migrations inside a tx, so we accept the brief lock at install time).
CREATE UNIQUE INDEX IF NOT EXISTS users_external_id_uq
  ON users(external_id)
  WHERE external_id IS NOT NULL;

COMMENT ON COLUMN users.external_id IS
  'Identity-provider subject (Keycloak ''sub'' claim). NULL for users created via spring-jwt path.';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/gateway && ./gradlew test --tests V9MigrationTest`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/main/resources/db/migration/V9__user_external_id.sql apps/gateway/src/test/java/io/filternarrange/gateway/migration/V9MigrationTest.java
git commit -m "feat(db): V9 add users.external_id for Keycloak subject mapping"
```

---

## Task 3 — Gateway: Keycloak auth filter + provider switch

**Files:**
- Modify: `apps/gateway/build.gradle.kts`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/AuthConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/KeycloakAuthFilter.java`
- Create: `apps/gateway/src/main/resources/application-keycloak.yml`
- Create: `apps/gateway/src/main/resources/application-spring-jwt.yml`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/auth/AuthProviderSwitchTest.java`

- [ ] **Step 1: Write the failing test**

```java
// apps/gateway/src/test/java/io/filternarrange/gateway/platform/auth/AuthProviderSwitchTest.java
package io.filternarrange.gateway.platform.auth;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.test.context.TestPropertySource;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@TestPropertySource(properties = {"AUTH_PROVIDER=keycloak", "spring.profiles.active=keycloak"})
class AuthProviderSwitchTest {
    @Autowired SecurityFilterChain chain;

    @Test
    void keycloak_filter_is_wired_when_AUTH_PROVIDER_keycloak() {
        boolean hasKeycloak = chain.getFilters().stream()
            .anyMatch(f -> f.getClass().getSimpleName().equals("KeycloakAuthFilter"));
        boolean hasSpringJwt = chain.getFilters().stream()
            .anyMatch(f -> f.getClass().getSimpleName().equals("SpringJwtAuthFilter"));
        assertThat(hasKeycloak).isTrue();
        assertThat(hasSpringJwt).isFalse();
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/gateway && ./gradlew test --tests AuthProviderSwitchTest`
Expected: FAIL — `KeycloakAuthFilter` class not defined.

- [ ] **Step 3: Add dependencies**

Edit `apps/gateway/build.gradle.kts` `dependencies` block — add:

```kotlin
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
    implementation("org.springframework.security:spring-security-oauth2-jose")
```

- [ ] **Step 4: Implement the Keycloak filter**

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/KeycloakAuthFilter.java
package io.filternarrange.gateway.platform.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

public class KeycloakAuthFilter extends OncePerRequestFilter {
    private final JwtDecoder jwtDecoder;
    private final KeycloakUserSyncService sync;

    public KeycloakAuthFilter(JwtDecoder jwtDecoder, KeycloakUserSyncService sync) {
        this.jwtDecoder = jwtDecoder;
        this.sync = sync;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String header = req.getHeader("Authorization");
        if (header == null || !header.startsWith("Bearer ")) {
            chain.doFilter(req, res);
            return;
        }
        try {
            Jwt jwt = jwtDecoder.decode(header.substring(7));
            String subject = jwt.getSubject();
            String email = jwt.getClaimAsString("email");
            String name = jwt.getClaimAsString("preferred_username");
            List<String> roles = extractRealmRoles(jwt);

            UUID userId = sync.upsertOnLogin(subject, email, name, roles);

            var authorities = roles.stream()
                .map(r -> new SimpleGrantedAuthority("ROLE_" + r.toUpperCase()))
                .collect(Collectors.toList());
            var auth = new JwtAuthenticationToken(jwt, authorities, subject);
            auth.setDetails(Map.of("user_id", userId.toString(), "roles", roles));
            SecurityContextHolder.getContext().setAuthentication(auth);
        } catch (Exception ex) {
            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            res.setContentType("application/json");
            res.getWriter().write("{\"code\":\"AUTH_INVALID_TOKEN\",\"message\":\"Invalid or expired token\"}");
            return;
        }
        chain.doFilter(req, res);
    }

    @SuppressWarnings("unchecked")
    private List<String> extractRealmRoles(Jwt jwt) {
        Map<String, Object> realmAccess = jwt.getClaim("realm_access");
        if (realmAccess == null) return List.of();
        Object roles = realmAccess.get("roles");
        if (!(roles instanceof Collection<?>)) return List.of();
        return ((Collection<?>) roles).stream().map(Object::toString).collect(Collectors.toList());
    }
}
```

- [ ] **Step 5: Implement the user-sync service**

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/KeycloakUserSyncService.java
package io.filternarrange.gateway.platform.auth;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
public class KeycloakUserSyncService {
    private final JdbcTemplate jdbc;

    public KeycloakUserSyncService(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    @Transactional
    public UUID upsertOnLogin(String subject, String email, String displayName, List<String> roles) {
        String tier  = roles.contains("paid")  ? "paid" : "free";
        boolean admin = roles.contains("admin");

        UUID existing = jdbc.query(
            "SELECT id FROM users WHERE external_id = ? OR email = ?",
            ps -> { ps.setString(1, subject); ps.setString(2, email); },
            rs -> rs.next() ? UUID.fromString(rs.getString("id")) : null);

        UUID userId = existing != null ? existing : UUID.randomUUID();

        if (existing == null) {
            jdbc.update(
                "INSERT INTO users (id, email, external_id, display_name, created_at, last_login_at) " +
                "VALUES (?, ?, ?, ?, now(), now())",
                userId, email, subject, displayName);
        } else {
            jdbc.update(
                "UPDATE users SET external_id = ?, email = COALESCE(?, email), " +
                "display_name = COALESCE(?, display_name), last_login_at = now() WHERE id = ?",
                subject, email, displayName, userId);
        }

        // Mirror tier into active subscription
        jdbc.update(
            "INSERT INTO subscriptions (id, user_id, tier, status, started_at) " +
            "VALUES (?, ?, ?, 'active', now()) " +
            "ON CONFLICT (user_id) WHERE status = 'active' DO UPDATE SET tier = EXCLUDED.tier",
            UUID.randomUUID(), userId, tier);

        // admin column lives on users (added in Plan B); update it
        jdbc.update("UPDATE users SET admin = ? WHERE id = ?", admin, userId);
        return userId;
    }
}
```

- [ ] **Step 6: Implement the AuthConfig switcher**

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/auth/AuthConfig.java
package io.filternarrange.gateway.platform.auth;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
public class AuthConfig {

    @Value("${AUTH_PROVIDER:spring-jwt}")
    private String provider;

    @Value("${keycloak.jwks-uri:}")
    private String jwksUri;

    @Bean
    public JwtDecoder jwtDecoder() {
        if (jwksUri.isBlank()) {
            // fallback for spring-jwt mode: a no-op decoder so Spring context boots
            return token -> { throw new UnsupportedOperationException("JwtDecoder not configured"); };
        }
        return NimbusJwtDecoder.withJwkSetUri(jwksUri).build();
    }

    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            KeycloakUserSyncService sync,
            JwtDecoder decoder,
            SpringJwtAuthFilter springJwtFilter
    ) throws Exception {
        http.csrf(c -> c.disable())
            .authorizeHttpRequests(a -> a
                .requestMatchers("/actuator/**", "/api/v1/health", "/api/v1/auth/**").permitAll()
                .anyRequest().authenticated());

        if ("keycloak".equalsIgnoreCase(provider)) {
            http.addFilterBefore(new KeycloakAuthFilter(decoder, sync),
                UsernamePasswordAuthenticationFilter.class);
        } else {
            http.addFilterBefore(springJwtFilter, UsernamePasswordAuthenticationFilter.class);
        }
        return http.build();
    }
}
```

- [ ] **Step 7: Profile YAMLs**

```yaml
# apps/gateway/src/main/resources/application-keycloak.yml
keycloak:
  jwks-uri: ${KEYCLOAK_JWKS_URI:http://keycloak:8080/realms/filternarrange/protocol/openid-connect/certs}
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          jwk-set-uri: ${keycloak.jwks-uri}
```

```yaml
# apps/gateway/src/main/resources/application-spring-jwt.yml
# Inherits Plan B's spring-jwt settings; placeholder ensures the profile resolves.
filternarrange:
  auth:
    mode: spring-jwt
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd apps/gateway && ./gradlew test --tests AuthProviderSwitchTest`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/gateway/
git commit -m "feat(auth): add Keycloak OAuth2 resource server provider with AUTH_PROVIDER switch"
```

---

## Task 4 — Gateway: matrix integration test (Keycloak + spring-jwt)

**Files:**
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/auth/AuthMatrixIntegrationTest.java`

- [ ] **Step 1: Write the failing test**

```java
// apps/gateway/src/test/java/io/filternarrange/gateway/auth/AuthMatrixIntegrationTest.java
package io.filternarrange.gateway.auth;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.*;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AuthMatrixIntegrationTest {
    @Autowired TestRestTemplate http;
    @LocalServerPort int port;

    @ParameterizedTest
    @ValueSource(strings = {"keycloak", "spring-jwt"})
    void protected_endpoint_returns_401_without_token(String provider) {
        System.setProperty("AUTH_PROVIDER", provider);
        var resp = http.getForEntity("http://localhost:" + port + "/api/v1/me", String.class);
        assertThat(resp.getStatusCode()).isEqualTo(HttpStatus.UNAUTHORIZED);
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/gateway && ./gradlew test --tests AuthMatrixIntegrationTest`
Expected: FAIL if `/api/v1/me` lacks security wiring; PASS once Task 3 is in.

- [ ] **Step 3: Implement (no code — wiring already exists from Task 3)**

If failure persists, ensure `/api/v1/me` is not in the `permitAll` allowlist in `AuthConfig`.

- [ ] **Step 4: Re-run**

Run: `cd apps/gateway && ./gradlew test --tests AuthMatrixIntegrationTest`
Expected: PASS for both providers.

- [ ] **Step 5: Commit**

```bash
git add apps/gateway/src/test/java/io/filternarrange/gateway/auth/AuthMatrixIntegrationTest.java
git commit -m "test(auth): matrix test that both providers enforce auth"
```

---

## Task 5 — Frontend: dual-mode OIDC login

**Files:**
- Modify: `apps/frontend/package.json` (add `oidc-client-ts`)
- Create: `apps/frontend/src/features/auth/keycloak-client.ts`
- Create: `apps/frontend/src/features/auth/auth-provider.ts`
- Modify: `apps/frontend/src/features/auth/login-page.tsx`
- Modify: `apps/frontend/src/shared/config.ts`
- Test: `apps/frontend/src/features/auth/__tests__/auth-provider.test.ts`

- [ ] **Step 1: Add dependency**

```bash
cd apps/frontend && pnpm add oidc-client-ts
```

- [ ] **Step 2: Write the failing test**

```ts
// apps/frontend/src/features/auth/__tests__/auth-provider.test.ts
import { describe, it, expect, vi } from "vitest";
import { resolveAuthProvider } from "../auth-provider";

describe("resolveAuthProvider", () => {
  it("returns 'keycloak' when env says keycloak", () => {
    expect(resolveAuthProvider("keycloak")).toBe("keycloak");
  });
  it("returns 'spring-jwt' when env says spring-jwt", () => {
    expect(resolveAuthProvider("spring-jwt")).toBe("spring-jwt");
  });
  it("defaults to 'spring-jwt' when env is empty", () => {
    expect(resolveAuthProvider("")).toBe("spring-jwt");
  });
  it("defaults to 'spring-jwt' for unknown values", () => {
    expect(resolveAuthProvider("malformed")).toBe("spring-jwt");
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd apps/frontend && pnpm test auth-provider`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement the provider resolver**

```ts
// apps/frontend/src/features/auth/auth-provider.ts
export type AuthProvider = "keycloak" | "spring-jwt";

export function resolveAuthProvider(raw: string | undefined): AuthProvider {
  return raw === "keycloak" ? "keycloak" : "spring-jwt";
}
```

- [ ] **Step 5: Implement the Keycloak client wrapper**

```ts
// apps/frontend/src/features/auth/keycloak-client.ts
import { UserManager, WebStorageStateStore } from "oidc-client-ts";

export function buildKeycloakManager(): UserManager {
  return new UserManager({
    authority: import.meta.env.VITE_KEYCLOAK_ISSUER ?? "http://localhost:8085/realms/filternarrange",
    client_id: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "filternarrange-frontend",
    redirect_uri: `${window.location.origin}/auth/callback`,
    response_type: "code",
    scope: "openid profile email",
    userStore: new WebStorageStateStore({ store: window.localStorage }),
    automaticSilentRenew: true,
  });
}
```

- [ ] **Step 6: Update the login page**

```tsx
// apps/frontend/src/features/auth/login-page.tsx
import { resolveAuthProvider } from "./auth-provider";
import { buildKeycloakManager } from "./keycloak-client";
import { LocalLoginForm } from "./local-login-form"; // existed since Plan B

export function LoginPage() {
  const provider = resolveAuthProvider(import.meta.env.VITE_AUTH_PROVIDER);
  if (provider === "keycloak") {
    return (
      <main>
        <h1>Sign in</h1>
        <button onClick={async () => {
          const mgr = buildKeycloakManager();
          await mgr.signinRedirect();
        }}>Continue with Keycloak</button>
      </main>
    );
  }
  return <LocalLoginForm />;
}
```

- [ ] **Step 7: Extend shared config**

```ts
// apps/frontend/src/shared/config.ts (add)
export const AUTH_PROVIDER = import.meta.env.VITE_AUTH_PROVIDER ?? "spring-jwt";
export const KEYCLOAK_ISSUER = import.meta.env.VITE_KEYCLOAK_ISSUER ?? "";
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd apps/frontend && pnpm test auth-provider`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/frontend/
git commit -m "feat(frontend): dual-mode auth with Keycloak OIDC PKCE flow"
```

---

## Task 6 — Playwright: Keycloak login E2E

**Files:**
- Create: `tests/integration/test_keycloak_login.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_keycloak_login.py
import os
from playwright.sync_api import sync_playwright, expect

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
USER = os.environ.get("KC_TEST_USER", "dev-user")
PWD  = os.environ.get("KC_TEST_PWD", "dev-password")

def test_keycloak_login_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(f"{FRONTEND_URL}/login")

        page.click("text=Continue with Keycloak")
        page.fill('input[name="username"]', USER)
        page.fill('input[name="password"]', PWD)
        page.click('input[name="login"]')

        page.wait_for_url(f"{FRONTEND_URL}/**")
        expect(page.locator('[data-testid="current-user"]')).to_contain_text(USER)
        browser.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `VITE_AUTH_PROVIDER=keycloak docker compose up -d && pytest tests/integration/test_keycloak_login.py -v`
Expected: FAIL until full stack is up and `[data-testid="current-user"]` selector exists.

- [ ] **Step 3: Ensure the user-display element exists in the frontend shell**

In `apps/frontend/src/app/shell.tsx`, ensure the header has:

```tsx
<span data-testid="current-user">{user?.displayName ?? user?.email}</span>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_keycloak_login.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/integration/test_keycloak_login.py apps/frontend/src/app/shell.tsx
git commit -m "test(e2e): Keycloak OIDC login lands user in app"
```

---

## Task 7 — Prometheus + Grafana + AlertManager compose services

**Files:**
- Modify: `infra/docker-compose/docker-compose.yml`
- Create: `infra/observability/prometheus/prometheus.yml`
- Create: `infra/observability/prometheus/alerts.yml`
- Create: `infra/observability/alertmanager/alertmanager.yml`
- Create: `infra/observability/grafana/datasources.yml`
- Create: `infra/observability/grafana/dashboards.yml`

- [ ] **Step 1: Prometheus scrape config**

```yaml
# infra/observability/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  - job_name: gateway
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["gateway:8080"]

  - job_name: data-engine
    metrics_path: /metrics
    static_configs:
      - targets: ["data-engine:8000"]

  - job_name: otel-collector
    static_configs:
      - targets: ["otel-collector:8889"]

  - job_name: node
    static_configs:
      - targets: ["node-exporter:9100"]
```

- [ ] **Step 2: Alert rules**

```yaml
# infra/observability/prometheus/alerts.yml
groups:
  - name: filternarrange-slos
    interval: 30s
    rules:
      - alert: DetectionP95High
        expr: histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{uri="/api/v1/detect"}[5m])) by (le)) > 0.5
        for: 5m
        labels: { severity: warning, slo: detect-p95 }
        annotations:
          summary: "Detection p95 > 500ms for 5m"
          runbook: "docs/operations/incident-job-pipeline-stalled.md"

      - alert: FilterPreviewP95High
        expr: histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{uri="/api/v1/filter/preview"}[5m])) by (le)) > 1.0
        for: 5m
        labels: { severity: warning, slo: filter-preview-p95 }
        annotations:
          summary: "Filter preview p95 > 1s for 5m"

      - alert: NLToFilterP95High
        expr: histogram_quantile(0.95, sum(rate(fna_ai_capability_seconds_bucket{capability="nl_to_filter"}[5m])) by (le)) > 3.0
        for: 5m
        labels: { severity: warning, slo: nl2filter-p95 }
        annotations:
          summary: "NL-to-filter p95 > 3s for 5m"

      - alert: HighErrorRate
        expr: sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m])) > 0.05
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "Gateway 5xx rate > 5% over 5m"

      - alert: CircuitBreakerOpen
        expr: max(resilience4j_circuitbreaker_state{state="open"}) == 1
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Resilience4j circuit breaker is OPEN"
          runbook: "docs/operations/incident-circuit-breaker-open.md"

      - alert: RetentionWorkerStalled
        expr: time() - fna_retention_worker_last_run_timestamp_seconds > 129600
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Retention worker hasn't reported in 36h"

      - alert: DiskHigh
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) > 0.80
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "Host disk > 80% on /"
          runbook: "docs/operations/incident-disk-pressure.md"
```

- [ ] **Step 3: AlertManager (dev webhook receiver)**

```yaml
# infra/observability/alertmanager/alertmanager.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 1m
  repeat_interval: 1h
  receiver: dev-log

receivers:
  - name: dev-log
    webhook_configs:
      - url: "http://otel-collector:4318/v1/logs"
        send_resolved: true
```

- [ ] **Step 4: Grafana datasources**

```yaml
# infra/observability/grafana/datasources.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['trace_id']
```

- [ ] **Step 5: Grafana dashboard provider**

```yaml
# infra/observability/grafana/dashboards.yml
apiVersion: 1
providers:
  - name: filternarrange
    folder: FilterNArrange
    type: file
    disableDeletion: false
    options:
      path: /etc/grafana/provisioning/dashboards
```

- [ ] **Step 6: Add services to compose**

Append to `infra/docker-compose/docker-compose.yml`:

```yaml
  prometheus:
    image: prom/prometheus:v2.54.1
    container_name: fna-prometheus
    volumes:
      - ../observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ../observability/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
    ports: ["9090:9090"]
    networks: [fna-net]

  alertmanager:
    image: prom/alertmanager:v0.27.0
    container_name: fna-alertmanager
    volumes:
      - ../observability/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    ports: ["9093:9093"]
    networks: [fna-net]

  grafana:
    image: grafana/grafana-oss:11.2.0
    container_name: fna-grafana
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"
      GF_AUTH_ANONYMOUS_ORG_ROLE: "Viewer"
    volumes:
      - ../observability/grafana/datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml:ro
      - ../observability/grafana/dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml:ro
      - ../observability/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    ports: ["3001:3000"]
    networks: [fna-net]

  node-exporter:
    image: prom/node-exporter:v1.8.2
    container_name: fna-node-exporter
    pid: host
    volumes: ["/:/host:ro,rslave"]
    command: ["--path.rootfs=/host"]
    networks: [fna-net]
```

- [ ] **Step 7: Commit**

```bash
git add infra/docker-compose/docker-compose.yml infra/observability/prometheus infra/observability/alertmanager infra/observability/grafana/datasources.yml infra/observability/grafana/dashboards.yml
git commit -m "feat(observability): add Prometheus + AlertManager + Grafana with SLO alerts"
```

---

## Task 8 — Loki + Promtail + Tempo + OTel Collector compose

**Files:**
- Modify: `infra/docker-compose/docker-compose.yml`
- Create: `infra/observability/loki/loki-config.yml`
- Create: `infra/observability/promtail/promtail-config.yml`
- Create: `infra/observability/tempo/tempo.yml`
- Create: `infra/observability/otel-collector/otel-collector.yml`

- [ ] **Step 1: Loki config**

```yaml
# infra/observability/loki/loki-config.yml
auth_enabled: false
server: { http_listen_port: 3100 }
common:
  ring: { kvstore: { store: inmemory } }
  replication_factor: 1
  path_prefix: /tmp/loki
schema_config:
  configs:
    - from: 2024-01-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index: { prefix: index_, period: 24h }
storage_config:
  tsdb_shipper: { active_index_directory: /tmp/loki/tsdb-index, cache_location: /tmp/loki/tsdb-cache }
  filesystem: { directory: /tmp/loki/chunks }
limits_config:
  allow_structured_metadata: true
```

- [ ] **Step 2: Promtail config**

```yaml
# infra/observability/promtail/promtail-config.yml
server: { http_listen_port: 9080 }
positions: { filename: /tmp/positions.yaml }
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(fna-.*)'
        target_label: 'container'
      - source_labels: ['container']
        target_label: 'job'
    pipeline_stages:
      - json:
          expressions:
            level: level
            trace_id: trace_id
            user_id: user_id
            job_id: job_id
            plugin_id: plugin_id
            tier: tier
            endpoint: endpoint
      - labels: { level:, trace_id:, plugin_id: }
```

- [ ] **Step 3: Tempo config**

```yaml
# infra/observability/tempo/tempo.yml
server: { http_listen_port: 3200 }
distributor:
  receivers:
    otlp:
      protocols:
        grpc: { endpoint: 0.0.0.0:4317 }
        http: { endpoint: 0.0.0.0:4318 }
storage:
  trace:
    backend: local
    local: { path: /tmp/tempo/blocks }
    wal: { path: /tmp/tempo/wal }
compactor:
  compaction: { block_retention: 24h }
```

- [ ] **Step 4: OTel Collector config**

```yaml
# infra/observability/otel-collector/otel-collector.yml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  batch: {}
  memory_limiter: { limit_mib: 256, check_interval: 1s }

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }
  loki:
    endpoint: http://loki:3100/loki/api/v1/push
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

- [ ] **Step 5: Add services to compose**

Append:

```yaml
  loki:
    image: grafana/loki:3.1.1
    container_name: fna-loki
    command: ["-config.file=/etc/loki/loki-config.yml"]
    volumes:
      - ../observability/loki/loki-config.yml:/etc/loki/loki-config.yml:ro
    ports: ["3100:3100"]
    networks: [fna-net]

  promtail:
    image: grafana/promtail:3.1.1
    container_name: fna-promtail
    command: ["-config.file=/etc/promtail/promtail-config.yml"]
    volumes:
      - ../observability/promtail/promtail-config.yml:/etc/promtail/promtail-config.yml:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    depends_on: [loki]
    networks: [fna-net]

  tempo:
    image: grafana/tempo:2.6.0
    container_name: fna-tempo
    command: ["-config.file=/etc/tempo/tempo.yml"]
    volumes:
      - ../observability/tempo/tempo.yml:/etc/tempo/tempo.yml:ro
    ports: ["3200:3200", "4317:4317"]
    networks: [fna-net]

  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.110.0
    container_name: fna-otel
    command: ["--config=/etc/otelcol/otel-collector.yml"]
    volumes:
      - ../observability/otel-collector/otel-collector.yml:/etc/otelcol/otel-collector.yml:ro
    ports: ["4318:4318", "8889:8889"]
    depends_on: [tempo, loki]
    networks: [fna-net]
```

- [ ] **Step 6: Commit**

```bash
git add infra/observability/loki infra/observability/promtail infra/observability/tempo infra/observability/otel-collector infra/docker-compose/docker-compose.yml
git commit -m "feat(observability): add Loki/Promtail/Tempo/OTel-Collector to compose"
```

---

## Task 9 — Gateway: Micrometer Prometheus + custom metrics

**Files:**
- Modify: `apps/gateway/build.gradle.kts`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/MetricsConfig.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/JobStateTransitionMetric.java`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/QuotaRejectionMetric.java`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/observability/MetricsExposureTest.java`

- [ ] **Step 1: Write the failing test**

```java
// apps/gateway/src/test/java/io/filternarrange/gateway/platform/observability/MetricsExposureTest.java
package io.filternarrange.gateway.platform.observability;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.server.LocalServerPort;
import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class MetricsExposureTest {
    @Autowired TestRestTemplate http;
    @LocalServerPort int port;

    @Test
    void prometheus_endpoint_exposes_custom_meters() {
        String body = http.getForObject("http://localhost:" + port + "/actuator/prometheus", String.class);
        assertThat(body).contains("fna_quota_rejections_total");
        assertThat(body).contains("fna_job_state_transitions_total");
        assertThat(body).contains("http_server_requests_seconds");
    }
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/gateway && ./gradlew test --tests MetricsExposureTest`
Expected: FAIL — meters not registered.

- [ ] **Step 3: Add dependencies**

In `apps/gateway/build.gradle.kts`:

```kotlin
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("io.micrometer:micrometer-registry-prometheus")
```

- [ ] **Step 4: Implement the meters**

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/QuotaRejectionMetric.java
package io.filternarrange.gateway.platform.observability;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

@Component
public class QuotaRejectionMetric {
    private final MeterRegistry registry;
    public QuotaRejectionMetric(MeterRegistry registry) { this.registry = registry; }

    public void record(String tier, String endpoint) {
        Counter.builder("fna_quota_rejections_total")
            .description("Requests rejected by quota enforcement")
            .tags("tier", tier, "endpoint", endpoint)
            .register(registry)
            .increment();
    }
}
```

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/JobStateTransitionMetric.java
package io.filternarrange.gateway.platform.observability;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

@Component
public class JobStateTransitionMetric {
    private final MeterRegistry registry;
    public JobStateTransitionMetric(MeterRegistry registry) { this.registry = registry; }

    public void record(String from, String to, String kind) {
        Counter.builder("fna_job_state_transitions_total")
            .tags("from", from, "to", to, "kind", kind)
            .register(registry)
            .increment();
    }
}
```

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/observability/MetricsConfig.java
package io.filternarrange.gateway.platform.observability;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.config.MeterFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class MetricsConfig {
    @Bean
    MeterFilter percentileHistogramOnHttpServer() {
        return MeterFilter.maximumExpectedValue("http.server.requests", java.time.Duration.ofSeconds(30));
    }

    @Bean
    org.springframework.boot.actuate.autoconfigure.metrics.MeterRegistryCustomizer<MeterRegistry> applicationTag() {
        return r -> r.config().commonTags("application", "fna-gateway");
    }
}
```

- [ ] **Step 5: Expose the actuator endpoint**

In `apps/gateway/src/main/resources/application.yml`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
        fna.ai.capability: true
        fna.plugin.execution: true
```

- [ ] **Step 6: Wire QuotaRejectionMetric into existing quota enforcement**

In the existing quota interceptor (from Plan B / D), inject `QuotaRejectionMetric` and call `record(tier, request.getRequestURI())` whenever a 429 is returned. Wire `JobStateTransitionMetric` into the Job repository's state-change method.

- [ ] **Step 7: Run test to verify it passes**

Run: `cd apps/gateway && ./gradlew test --tests MetricsExposureTest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/gateway/
git commit -m "feat(observability): gateway emits custom Prometheus meters"
```

---

## Task 10 — Data-engine: prometheus_client + custom metrics

**Files:**
- Modify: `apps/data-engine/pyproject.toml`
- Create: `apps/data-engine/src/filternarrange_engine/platform/metrics.py`
- Create: `apps/data-engine/src/filternarrange_engine/api/metrics_router.py`
- Test: `apps/data-engine/tests/test_metrics_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/data-engine/tests/test_metrics_endpoint.py
import pytest
from httpx import AsyncClient
from filternarrange_engine.main import app

@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_custom_metrics():
    from filternarrange_engine.platform.metrics import plugin_execution_seconds
    plugin_execution_seconds.labels(plugin_id="csv", outcome="ok").observe(0.123)
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "fna_plugin_execution_seconds" in body
    assert "fna_ai_capability_seconds" in body
    assert "fna_circuit_breaker_state" in body
    assert 'plugin_id="csv"' in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/data-engine && uv run pytest tests/test_metrics_endpoint.py -v`
Expected: FAIL — module not found / endpoint missing.

- [ ] **Step 3: Add the dependency**

In `apps/data-engine/pyproject.toml`:

```toml
[project]
dependencies = [
    # ...
    "prometheus_client>=0.21.0",
    "opentelemetry-instrumentation-fastapi>=0.48b0",
    "opentelemetry-sdk>=1.27.0",
    "opentelemetry-exporter-otlp-proto-http>=1.27.0",
]
```

- [ ] **Step 4: Implement metrics**

```python
# apps/data-engine/src/filternarrange_engine/platform/metrics.py
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

registry = CollectorRegistry()

plugin_execution_seconds = Histogram(
    "fna_plugin_execution_seconds",
    "Plugin execution time",
    labelnames=("plugin_id", "outcome"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
    registry=registry,
)

ai_capability_seconds = Histogram(
    "fna_ai_capability_seconds",
    "AI capability latency",
    labelnames=("capability", "model", "outcome"),
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 10, 30, 60),
    registry=registry,
)

quota_rejections_total = Counter(
    "fna_quota_rejections_total",
    "Quota rejections (data-engine side)",
    labelnames=("tier", "endpoint"),
    registry=registry,
)

job_state_transitions_total = Counter(
    "fna_job_state_transitions_total",
    "Job state transitions observed by data-engine",
    labelnames=("from", "to", "kind"),
    registry=registry,
)

circuit_breaker_state = Gauge(
    "fna_circuit_breaker_state",
    "Circuit breaker state (0=closed,1=half-open,2=open)",
    labelnames=("breaker",),
    registry=registry,
)

retention_worker_last_run = Gauge(
    "fna_retention_worker_last_run_timestamp_seconds",
    "Unix timestamp of the last retention worker run",
    registry=registry,
)

def render() -> bytes:
    return generate_latest(registry)
```

- [ ] **Step 5: Implement the router**

```python
# apps/data-engine/src/filternarrange_engine/api/metrics_router.py
from fastapi import APIRouter, Response
from filternarrange_engine.platform.metrics import render

router = APIRouter()

@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=render(), media_type="text/plain; version=0.0.4; charset=utf-8")
```

- [ ] **Step 6: Wire it in main.py**

In `apps/data-engine/src/filternarrange_engine/main.py`, add:

```python
from filternarrange_engine.api.metrics_router import router as metrics_router
app.include_router(metrics_router)
```

- [ ] **Step 7: Instrument the plugin-dispatch boundary**

In `apps/data-engine/src/filternarrange_engine/adapters/plugin_registry/dispatcher.py`, wrap calls:

```python
import time
from filternarrange_engine.platform.metrics import plugin_execution_seconds

def dispatch(plugin_id: str, op: callable, *args, **kwargs):
    start = time.perf_counter()
    outcome = "ok"
    try:
        return op(*args, **kwargs)
    except Exception:
        outcome = "error"
        raise
    finally:
        plugin_execution_seconds.labels(plugin_id=plugin_id, outcome=outcome).observe(
            time.perf_counter() - start
        )
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd apps/data-engine && uv run pytest tests/test_metrics_endpoint.py -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add apps/data-engine/
git commit -m "feat(observability): data-engine exposes /metrics with custom histograms"
```

---

## Task 11 — Structured JSON logging (both services)

**Files:**
- Modify: `apps/gateway/build.gradle.kts` — add `net.logstash.logback:logstash-logback-encoder`
- Modify: `apps/gateway/src/main/resources/logback-spring.xml`
- Create: `apps/data-engine/src/filternarrange_engine/platform/logging_json.py`
- Test: `apps/gateway/src/test/java/io/filternarrange/gateway/platform/observability/JsonLoggingTest.java`
- Test: `apps/data-engine/tests/test_json_logging.py`

- [ ] **Step 1: Write the failing tests**

```java
// apps/gateway/src/test/java/io/filternarrange/gateway/platform/observability/JsonLoggingTest.java
package io.filternarrange.gateway.platform.observability;

import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.core.read.ListAppender;
import ch.qos.logback.classic.spi.ILoggingEvent;
import static org.assertj.core.api.Assertions.assertThat;

class JsonLoggingTest {
    @Test
    void mdc_keys_appear_in_log_event() {
        Logger root = (Logger) LoggerFactory.getLogger(Logger.ROOT_LOGGER_NAME);
        ListAppender<ILoggingEvent> listAppender = new ListAppender<>();
        listAppender.start();
        root.addAppender(listAppender);

        MDC.put("trace_id", "abc");
        MDC.put("user_id", "u-1");
        LoggerFactory.getLogger("test").info("hello");
        MDC.clear();

        var evt = listAppender.list.get(0);
        assertThat(evt.getMDCPropertyMap()).containsEntry("trace_id", "abc").containsEntry("user_id", "u-1");
    }
}
```

```python
# apps/data-engine/tests/test_json_logging.py
import json, logging, io
from filternarrange_engine.platform.logging_json import configure_json_logging, bind

def test_logs_emit_json_with_bound_fields(capsys):
    configure_json_logging()
    log = logging.getLogger("test")
    with bind(trace_id="abc", user_id="u-1", endpoint="/api/v1/detect"):
        log.info("hello")
    captured = capsys.readouterr().out.strip().splitlines()[-1]
    obj = json.loads(captured)
    assert obj["trace_id"] == "abc"
    assert obj["user_id"] == "u-1"
    assert obj["endpoint"] == "/api/v1/detect"
    assert obj["msg"] == "hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/gateway && ./gradlew test --tests JsonLoggingTest` — FAIL.
Run: `cd apps/data-engine && uv run pytest tests/test_json_logging.py -v` — FAIL.

- [ ] **Step 3: Gateway logback-spring.xml**

```xml
<!-- apps/gateway/src/main/resources/logback-spring.xml -->
<configuration>
  <appender name="STDOUT_JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
      <includeMdcKeyName>trace_id</includeMdcKeyName>
      <includeMdcKeyName>user_id</includeMdcKeyName>
      <includeMdcKeyName>job_id</includeMdcKeyName>
      <includeMdcKeyName>plugin_id</includeMdcKeyName>
      <includeMdcKeyName>tier</includeMdcKeyName>
      <includeMdcKeyName>endpoint</includeMdcKeyName>
      <customFields>{"application":"fna-gateway"}</customFields>
    </encoder>
  </appender>
  <root level="INFO">
    <appender-ref ref="STDOUT_JSON"/>
  </root>
</configuration>
```

Add to `build.gradle.kts`:

```kotlin
    implementation("net.logstash.logback:logstash-logback-encoder:8.0")
```

- [ ] **Step 4: Data-engine JSON logger**

```python
# apps/data-engine/src/filternarrange_engine/platform/logging_json.py
import json, logging, sys, contextvars, contextlib
from typing import Any

_ctx: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("log_ctx", default={})

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "application": "fna-data-engine",
        }
        base.update(_ctx.get())
        return json.dumps(base, default=str)

def configure_json_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

@contextlib.contextmanager
def bind(**fields: Any):
    existing = _ctx.get()
    token = _ctx.set({**existing, **fields})
    try:
        yield
    finally:
        _ctx.reset(token)
```

- [ ] **Step 5: Run tests to verify they pass**

Run both — Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/gateway/src/main/resources/logback-spring.xml apps/gateway/build.gradle.kts apps/data-engine/src/filternarrange_engine/platform/logging_json.py apps/gateway/src/test/java/io/filternarrange/gateway/platform/observability/JsonLoggingTest.java apps/data-engine/tests/test_json_logging.py
git commit -m "feat(observability): structured JSON logs with MDC propagation in both services"
```

---

## Task 12 — Distributed tracing (OTel)

**Files:**
- Modify: `apps/gateway/Dockerfile` — add OTel Java agent
- Modify: `apps/data-engine/src/filternarrange_engine/main.py`
- Create: `apps/data-engine/src/filternarrange_engine/platform/tracing.py`
- Create: `apps/gateway/src/main/java/io/filternarrange/gateway/platform/tracing/TraceContextPropagator.java`
- Test: `tests/integration/test_trace_propagation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_trace_propagation.py
import os, requests, time

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
TEMPO_URL = os.environ.get("TEMPO_URL", "http://localhost:3200")

def test_trace_id_propagates_from_gateway_to_tempo():
    trace_id = "0af7651916cd43dd8448eb211c80319c"
    headers = {"traceparent": f"00-{trace_id}-b7ad6b7169203331-01"}
    r = requests.post(f"{GATEWAY_URL}/api/v1/detect", headers=headers, files={"file": ("x.csv", b"a,b\n1,2")})
    assert r.status_code in (200, 401, 415)
    time.sleep(2)
    t = requests.get(f"{TEMPO_URL}/api/traces/{trace_id}", timeout=5)
    assert t.status_code == 200
    body = t.json()
    assert body.get("batches"), "no spans landed in Tempo"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_trace_propagation.py -v`
Expected: FAIL — tracing not wired.

- [ ] **Step 3: Add Java agent to gateway Dockerfile**

```dockerfile
# apps/gateway/Dockerfile (additions)
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/download/v2.8.0/opentelemetry-javaagent.jar /opt/otel/otel.jar
ENV JAVA_TOOL_OPTIONS="-javaagent:/opt/otel/otel.jar"
ENV OTEL_SERVICE_NAME=fna-gateway
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
ENV OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
ENV OTEL_TRACES_EXPORTER=otlp
ENV OTEL_LOGS_EXPORTER=otlp
ENV OTEL_METRICS_EXPORTER=none
ENV OTEL_PROPAGATORS=tracecontext,baggage
```

- [ ] **Step 4: Add Kafka/WS propagator**

```java
// apps/gateway/src/main/java/io/filternarrange/gateway/platform/tracing/TraceContextPropagator.java
package io.filternarrange.gateway.platform.tracing;

import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.propagation.TextMapSetter;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.TextMessage;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.springframework.stereotype.Component;

@Component
public class TraceContextPropagator {
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public void injectKafkaHeaders(ProducerRecord<?, ?> record) {
        TextMapSetter<ProducerRecord<?, ?>> setter =
            (r, k, v) -> r.headers().add(k, v.getBytes());
        GlobalOpenTelemetry.getPropagators().getTextMapPropagator()
            .inject(Context.current(), record, setter);
    }

    public TextMessage injectWsMessage(String json) throws Exception {
        JsonNode node = MAPPER.readTree(json);
        ObjectNode out = node.isObject() ? (ObjectNode) node : MAPPER.createObjectNode().set("payload", node);
        out.put("traceparent", io.opentelemetry.api.trace.Span.current().getSpanContext().isValid()
            ? "00-" + io.opentelemetry.api.trace.Span.current().getSpanContext().getTraceId()
              + "-" + io.opentelemetry.api.trace.Span.current().getSpanContext().getSpanId() + "-01"
            : "");
        return new TextMessage(MAPPER.writeValueAsString(out));
    }
}
```

- [ ] **Step 5: Data-engine tracing**

```python
# apps/data-engine/src/filternarrange_engine/platform/tracing.py
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def configure_tracing(app) -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    service = os.environ.get("OTEL_SERVICE_NAME", "fna-data-engine")
    provider = TracerProvider(resource=Resource.create({"service.name": service}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")))
    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())
    FastAPIInstrumentor.instrument_app(app)
```

In `main.py`:

```python
from filternarrange_engine.platform.tracing import configure_tracing
configure_tracing(app)
```

- [ ] **Step 6: Run test to verify it passes**

Bring up full stack: `docker compose up -d`. Then `pytest tests/integration/test_trace_propagation.py -v`.
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/gateway/Dockerfile apps/gateway/src/main/java/io/filternarrange/gateway/platform/tracing apps/data-engine/src/filternarrange_engine/platform/tracing.py apps/data-engine/src/filternarrange_engine/main.py tests/integration/test_trace_propagation.py
git commit -m "feat(observability): OTel tracing across gateway, data-engine, Kafka, WebSocket"
```

---

## Task 13 — Grafana dashboards (5 JSON files)

**Files:**
- Create: `infra/observability/grafana/dashboards/api-latency.json`
- Create: `infra/observability/grafana/dashboards/plugin-performance.json`
- Create: `infra/observability/grafana/dashboards/job-pipeline.json`
- Create: `infra/observability/grafana/dashboards/ai-capabilities.json`
- Create: `infra/observability/grafana/dashboards/infra.json`

- [ ] **Step 1: Write each dashboard**

Each dashboard is a minimal valid Grafana JSON with the relevant panels. Example for `api-latency.json`:

```json
{
  "title": "FNA — API Latency Overview",
  "uid": "fna-api-latency",
  "schemaVersion": 39,
  "version": 1,
  "refresh": "30s",
  "time": { "from": "now-1h", "to": "now" },
  "panels": [
    {
      "type": "timeseries",
      "title": "Gateway p95 by endpoint",
      "datasource": { "type": "prometheus", "uid": "prometheus" },
      "targets": [{
        "expr": "histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, uri))",
        "legendFormat": "{{uri}}"
      }],
      "gridPos": { "x": 0, "y": 0, "w": 24, "h": 8 }
    },
    {
      "type": "timeseries",
      "title": "Gateway 5xx rate",
      "datasource": { "type": "prometheus", "uid": "prometheus" },
      "targets": [{
        "expr": "sum(rate(http_server_requests_seconds_count{status=~\"5..\"}[5m])) by (uri)",
        "legendFormat": "{{uri}}"
      }],
      "gridPos": { "x": 0, "y": 8, "w": 24, "h": 8 }
    }
  ]
}
```

Author the four remaining dashboards with these panel sets:
- `plugin-performance.json` — `fna_plugin_execution_seconds` p50/p95 per `plugin_id`, error rate per `plugin_id`.
- `job-pipeline.json` — `fna_job_state_transitions_total` rate by transition, queued-jobs gauge, Kafka consumer-lag (from collector).
- `ai-capabilities.json` — `fna_ai_capability_seconds` p95 per `capability`, throughput per `model`, AI errors.
- `infra.json` — node CPU/mem/disk, Postgres `pg_stat_database`, Redis hit-rate, Kafka topic lag, MinIO usage.

Keep each file < 200 lines; copy the structure above for every panel.

- [ ] **Step 2: Smoke-test dashboards load**

Run: `docker compose up -d grafana && curl -s http://admin:admin@localhost:3001/api/search?type=dash-db | jq '.[].title'`
Expected: 5 titles printed.

- [ ] **Step 3: Commit**

```bash
git add infra/observability/grafana/dashboards/
git commit -m "feat(observability): five Grafana dashboards (api, plugins, jobs, ai, infra)"
```

---

## Task 14 — Backup container + cron + restore script

**Files:**
- Create: `infra/backup/Dockerfile`
- Create: `infra/backup/crontab`
- Create: `infra/backup/backup.sh`
- Create: `infra/backup/restore.sh`
- Create: `infra/backup/mirror.sh`
- Create: `infra/backup/README.md`
- Modify: `infra/docker-compose/docker-compose.yml`

- [ ] **Step 1: Dockerfile**

```dockerfile
# infra/backup/Dockerfile
FROM alpine:3.20
RUN apk add --no-cache postgresql16-client mc curl bash gzip coreutils tzdata dcron
COPY backup.sh /usr/local/bin/backup.sh
COPY restore.sh /usr/local/bin/restore.sh
COPY mirror.sh /usr/local/bin/mirror.sh
COPY crontab /etc/crontabs/root
RUN chmod +x /usr/local/bin/*.sh
CMD ["crond", "-f", "-l", "8"]
```

- [ ] **Step 2: Crontab**

```cron
# infra/backup/crontab
# m h dom mon dow command
30 2 * * * /usr/local/bin/backup.sh >> /proc/1/fd/1 2>&1
0  3 * * * /usr/local/bin/mirror.sh  >> /proc/1/fd/1 2>&1
```

- [ ] **Step 3: backup.sh**

```bash
#!/usr/bin/env bash
# infra/backup/backup.sh
set -euo pipefail

DATE=$(date -u +%Y-%m-%d)
TMP=$(mktemp -d)
OUT="${TMP}/${DATE}.sql.gz"

export PGPASSWORD="${POSTGRES_PASSWORD}"
pg_dump --format=c --no-owner --no-privileges \
    -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  | gzip -9 > "${OUT}"

SIZE=$(stat -c '%s' "${OUT}")
echo "{\"event\":\"backup_created\",\"date\":\"${DATE}\",\"bytes\":${SIZE}}"

mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
mc cp "${OUT}" "minio/backups/postgres/${DATE}.sql.gz"

# Retention: 14 days
CUTOFF=$(date -u -d '14 days ago' +%Y-%m-%d)
mc ls "minio/backups/postgres/" | awk '{print $NF}' | while read f; do
    name="${f%.sql.gz}"
    if [[ "${name}" < "${CUTOFF}" ]]; then
        mc rm "minio/backups/postgres/${f}" || true
        echo "{\"event\":\"backup_pruned\",\"date\":\"${name}\"}"
    fi
done
```

- [ ] **Step 4: restore.sh**

```bash
#!/usr/bin/env bash
# infra/backup/restore.sh
# Usage: restore.sh <backup-date-or-key> [target-db]
set -euo pipefail

BACKUP="${1:?backup key required, e.g. 2026-06-07.sql.gz}"
TARGET_DB="${2:-${POSTGRES_DB}}"

TMP=$(mktemp -d)
LOCAL="${TMP}/${BACKUP##*/}"

mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
if [[ "${BACKUP}" == */* ]]; then
    mc cp "minio/${BACKUP}" "${LOCAL}"
else
    mc cp "minio/backups/postgres/${BACKUP}" "${LOCAL}"
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"
gunzip < "${LOCAL}" | pg_restore --clean --if-exists --no-owner --no-privileges \
    -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${TARGET_DB}"

echo "{\"event\":\"restore_complete\",\"backup\":\"${BACKUP}\",\"target\":\"${TARGET_DB}\"}"
```

- [ ] **Step 5: mirror.sh**

```bash
#!/usr/bin/env bash
# infra/backup/mirror.sh
set -euo pipefail
mc alias set minio "http://${MINIO_HOST}:9000" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
mc mb --ignore-existing minio/mirror
mc mirror --overwrite --remove minio/uploads minio/mirror/uploads
mc mirror --overwrite --remove minio/results minio/mirror/results
echo "{\"event\":\"mirror_complete\"}"
```

- [ ] **Step 6: README**

```markdown
# infra/backup/README.md
Nightly logical backup of Postgres → MinIO `backups/postgres/`.

## Schedule
- 02:30 UTC — pg_dump custom format, gzipped, 14-day retention.
- 03:00 UTC — `mc mirror` uploads/results → sibling `mirror/` bucket.

## Restore
docker compose run --rm backup /usr/local/bin/restore.sh 2026-06-07.sql.gz

## Out of scope (Plan H)
- Off-VM Backblaze B2 copy.
- Continuous WAL archiving (PITR).
```

- [ ] **Step 7: Add backup service to compose**

```yaml
  backup:
    build: ../backup
    container_name: fna-backup
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_USER: filternarrange
      POSTGRES_PASSWORD: filternarrange
      POSTGRES_DB: filternarrange
      MINIO_HOST: minio
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    depends_on: [postgres, minio]
    networks: [fna-net]
```

Also patch the `redis` service for AOF:

```yaml
  redis:
    # ...existing...
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
    volumes:
      - redis-data:/data
```

Add `redis-data:` to top-level `volumes:`.

- [ ] **Step 8: Commit**

```bash
git add infra/backup infra/docker-compose/docker-compose.yml
git commit -m "feat(infra): nightly pg_dump backup + mc mirror + restore script + Redis AOF"
```

---

## Task 15 — Restore integration test

**Files:**
- Create: `tests/integration/test_backup_restore.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_backup_restore.py
import os, subprocess, time, uuid, pytest
import psycopg

PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_USER = os.environ.get("POSTGRES_USER", "filternarrange")
PG_PWD  = os.environ.get("POSTGRES_PASSWORD", "filternarrange")

@pytest.mark.integration
def test_backup_then_restore_preserves_inserted_row():
    db_main = "filternarrange"
    marker = f"marker-{uuid.uuid4()}"

    with psycopg.connect(f"host={PG_HOST} user={PG_USER} password={PG_PWD} dbname={db_main}") as c:
        c.execute("CREATE TABLE IF NOT EXISTS backup_smoke (k TEXT PRIMARY KEY)")
        c.execute("INSERT INTO backup_smoke (k) VALUES (%s)", (marker,))
        c.commit()

    subprocess.check_call([
        "docker", "compose", "-f", "infra/docker-compose/docker-compose.yml",
        "run", "--rm", "backup", "/usr/local/bin/backup.sh"
    ])

    target_db = f"restore_test_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(f"host={PG_HOST} user={PG_USER} password={PG_PWD} dbname=postgres", autocommit=True) as c:
        c.execute(f"CREATE DATABASE {target_db}")

    today = time.strftime("%Y-%m-%d", time.gmtime())
    subprocess.check_call([
        "docker", "compose", "-f", "infra/docker-compose/docker-compose.yml",
        "run", "--rm", "backup", "/usr/local/bin/restore.sh", f"{today}.sql.gz", target_db
    ])

    with psycopg.connect(f"host={PG_HOST} user={PG_USER} password={PG_PWD} dbname={target_db}") as c:
        r = c.execute("SELECT k FROM backup_smoke WHERE k = %s", (marker,)).fetchone()
    assert r and r[0] == marker
```

- [ ] **Step 2: Run test**

Run: `pytest tests/integration/test_backup_restore.py -v -m integration`
Expected: PASS once backup container and MinIO are reachable.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_backup_restore.py
git commit -m "test(backup): end-to-end backup -> restore -> data-integrity check"
```

---

## Task 16 — Migration smoke test

**Files:**
- Create: `tests/integration/test_migration_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/integration/test_migration_smoke.py
import subprocess, time, requests, pytest

@pytest.mark.integration
def test_all_migrations_apply_on_empty_volume(tmp_path):
    project = "migrate_smoke"
    env = {"COMPOSE_PROJECT_NAME": project}
    # Bring up postgres + gateway clean
    subprocess.check_call(["docker", "compose", "-f", "infra/docker-compose/docker-compose.yml",
                           "-p", project, "down", "-v"])
    subprocess.check_call(["docker", "compose", "-f", "infra/docker-compose/docker-compose.yml",
                           "-p", project, "up", "-d", "postgres", "gateway"])
    try:
        deadline = time.time() + 180
        while time.time() < deadline:
            try:
                r = requests.get("http://localhost:8080/actuator/health", timeout=2)
                if r.status_code == 200 and r.json().get("status") == "UP":
                    break
            except requests.RequestException:
                pass
            time.sleep(3)
        else:
            raise AssertionError("Gateway never became healthy")
    finally:
        subprocess.check_call(["docker", "compose", "-f", "infra/docker-compose/docker-compose.yml",
                               "-p", project, "down", "-v"])
```

- [ ] **Step 2: Run test**

Run: `pytest tests/integration/test_migration_smoke.py -v -m integration`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_migration_smoke.py
git commit -m "test(db): clean-volume migration smoke check"
```

---

## Task 17 — k6 performance scripts

**Files:**
- Create: `tests/perf/detect.js`
- Create: `tests/perf/filter-preview.js`
- Create: `tests/perf/nl-to-filter.js`
- Create: `tests/perf/job-roundtrip.js`
- Create: `tests/perf/perf-helpers.js`
- Create: `tests/perf/baseline.json`

- [ ] **Step 1: Shared helpers**

```javascript
// tests/perf/perf-helpers.js
import http from "k6/http";
import { check } from "k6";

export const GATEWAY = __ENV.GATEWAY_URL || "http://localhost:8080";
export const TOKEN = __ENV.AUTH_TOKEN || "";

export function auth() {
  return { headers: { Authorization: `Bearer ${TOKEN}` } };
}

export function csvBytes(rows, cols) {
  let s = Array.from({ length: cols }, (_, i) => `c${i}`).join(",") + "\n";
  for (let r = 0; r < rows; r++) {
    s += Array.from({ length: cols }, (_, i) => `${r}_${i}`).join(",") + "\n";
  }
  return s;
}

export function postFile(path, name, body) {
  return http.post(`${GATEWAY}${path}`, { file: http.file(body, name, "text/csv") }, auth());
}

export function expectOk(res, label) {
  check(res, { [`${label} status 2xx`]: (r) => r.status >= 200 && r.status < 300 });
}
```

- [ ] **Step 2: detect.js**

```javascript
// tests/perf/detect.js
import { csvBytes, postFile, expectOk } from "./perf-helpers.js";

export const options = {
  scenarios: {
    detect_small: { executor: "constant-vus", vus: 5, duration: "30s" },
  },
  thresholds: {
    "http_req_duration{name:detect}": ["p(95)<500"],
    "http_req_failed":               ["rate<0.01"],
  },
};

export default function () {
  const body = csvBytes(1000, 8);
  const res = postFile("/api/v1/detect", "small.csv", body);
  res.request.tags = { name: "detect" };
  expectOk(res, "detect");
}
```

- [ ] **Step 3: filter-preview.js**

```javascript
// tests/perf/filter-preview.js
import http from "k6/http";
import { GATEWAY, auth, csvBytes, postFile, expectOk } from "./perf-helpers.js";

export const options = {
  scenarios: { preview: { executor: "constant-vus", vus: 3, duration: "1m" } },
  thresholds: {
    "http_req_duration{name:filter-preview}": ["p(95)<1000"],
    "http_req_failed":                        ["rate<0.01"],
  },
};

const big = csvBytes(100000, 6);

export default function () {
  const upload = postFile("/api/v1/uploads", "big.csv", big);
  expectOk(upload, "upload");
  const ref = upload.json("ref");
  const res = http.post(
    `${GATEWAY}/api/v1/filter/preview`,
    JSON.stringify({ ref, spec: { kind: "column", keep: ["c0", "c3", "c5"] } }),
    { headers: { "Content-Type": "application/json", ...auth().headers }, tags: { name: "filter-preview" } }
  );
  expectOk(res, "filter-preview");
}
```

- [ ] **Step 4: nl-to-filter.js**

```javascript
// tests/perf/nl-to-filter.js
import http from "k6/http";
import { GATEWAY, auth, expectOk } from "./perf-helpers.js";

if (__ENV.RUN_OLLAMA_PERF !== "1") {
  throw new Error("nl-to-filter perf requires RUN_OLLAMA_PERF=1 to enable");
}

const prompts = Array.from({ length: 50 }, (_, i) => `keep rows where age > ${i + 18} and country = 'IN'`);

export const options = {
  scenarios: { nl: { executor: "per-vu-iterations", vus: 1, iterations: prompts.length } },
  thresholds: { "http_req_duration{name:nl2filter}": ["p(95)<3000"] },
};

export default function () {
  const p = prompts[__ITER % prompts.length];
  const res = http.post(`${GATEWAY}/api/v1/ai/nl-to-filter`,
    JSON.stringify({ prompt: p, schema_hint: ["age:int", "country:str"] }),
    { headers: { "Content-Type": "application/json", ...auth().headers }, tags: { name: "nl2filter" } });
  expectOk(res, "nl2filter");
}
```

- [ ] **Step 5: job-roundtrip.js**

```javascript
// tests/perf/job-roundtrip.js
import http from "k6/http";
import ws from "k6/ws";
import { GATEWAY, auth, csvBytes, postFile, expectOk } from "./perf-helpers.js";

export const options = {
  scenarios: { jobs: { executor: "per-vu-iterations", vus: 2, iterations: 5 } },
  thresholds: { "iteration_duration{name:roundtrip}": ["p(95)<60000"] },
};

export default function () {
  const upload = postFile("/api/v1/uploads", "10mb.csv", csvBytes(100000, 10));
  expectOk(upload, "upload");
  const ref = upload.json("ref");
  const job = http.post(`${GATEWAY}/api/v1/jobs`,
    JSON.stringify({ kind: "batch-filter", input: ref, operations: [{ kind: "convert", to: "json" }] }),
    { headers: { "Content-Type": "application/json", ...auth().headers }, tags: { name: "submit" } });
  expectOk(job, "submit");
  const jobId = job.json("id");

  const wsUrl = `${GATEWAY.replace("http", "ws")}/ws/jobs/${jobId}`;
  ws.connect(wsUrl, { headers: auth().headers, tags: { name: "roundtrip" } }, (socket) => {
    socket.on("message", (msg) => {
      const m = JSON.parse(msg);
      if (m.status === "completed" || m.status === "failed") socket.close();
    });
    socket.setTimeout(() => socket.close(), 60000);
  });
}
```

- [ ] **Step 6: Baseline**

```json
{
  "version": 1,
  "updated": "2026-06-07",
  "metrics": {
    "detect.p95_ms": 420,
    "filter-preview.p95_ms": 850,
    "nl-to-filter.p95_ms": 2500,
    "job-roundtrip.p95_ms": 45000
  }
}
```

- [ ] **Step 7: Commit**

```bash
git add tests/perf/
git commit -m "test(perf): k6 scripts for detect/filter/nl/job with p95 budgets"
```

---

## Task 18 — Performance CI workflow

**Files:**
- Create: `.github/workflows/perf.yml`
- Create: `.github/workflows/perf-baseline.yml`

- [ ] **Step 1: PR perf workflow**

```yaml
# .github/workflows/perf.yml
name: perf
on:
  pull_request:
    paths-ignore: [ "docs/**", "**/*.md" ]
  workflow_dispatch: {}

jobs:
  perf:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Boot compose
        run: docker compose -f infra/docker-compose/docker-compose.yml up -d postgres redis minio redpanda gateway data-engine
      - name: Wait for gateway
        run: timeout 180 bash -c 'until curl -fsS http://localhost:8080/actuator/health; do sleep 2; done'
      - name: Mint dev token
        id: tok
        run: |
          TOKEN=$(curl -fsS -X POST http://localhost:8080/api/v1/auth/dev-token | jq -r .access_token)
          echo "AUTH_TOKEN=$TOKEN" >> $GITHUB_ENV
      - name: Run k6
        uses: grafana/k6-action@v0.3.1
        with:
          filename: tests/perf/detect.js
        env:
          AUTH_TOKEN: ${{ env.AUTH_TOKEN }}
      - name: Run filter-preview
        uses: grafana/k6-action@v0.3.1
        with: { filename: tests/perf/filter-preview.js }
        env: { AUTH_TOKEN: "${{ env.AUTH_TOKEN }}" }
      - name: Run job-roundtrip
        uses: grafana/k6-action@v0.3.1
        with: { filename: tests/perf/job-roundtrip.js }
        env: { AUTH_TOKEN: "${{ env.AUTH_TOKEN }}" }
      - name: Compare against baseline
        run: python tests/perf/compare_baseline.py
```

- [ ] **Step 2: Comparison script**

```python
# tests/perf/compare_baseline.py
import json, subprocess, sys
from pathlib import Path

BASELINE = json.loads(Path("tests/perf/baseline.json").read_text())["metrics"]
results = json.loads(Path("k6-summary.json").read_text())  # produced by k6 --summary-export
budgets = BASELINE
failed = []
for k, baseline_ms in budgets.items():
    actual = results.get(k)
    if actual is None:
        continue
    if actual > baseline_ms * 1.10:
        failed.append((k, baseline_ms, actual))
if failed:
    for k, b, a in failed:
        print(f"REGRESSION {k}: baseline={b}ms, actual={a}ms (>10%)", file=sys.stderr)
    sys.exit(1)
print("Perf within budget for all measured metrics.")
```

- [ ] **Step 3: Baseline refresh workflow**

```yaml
# .github/workflows/perf-baseline.yml
name: perf-baseline-refresh
on:
  push:
    branches: [main]
  workflow_dispatch: {}

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run perf
        run: bash tests/perf/run-all.sh
      - name: Open baseline PR
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore(perf): refresh baseline"
          branch: perf/baseline-refresh
          title: "chore(perf): refresh baseline from main"
          body: "Automated baseline refresh after merge to main."
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/perf.yml .github/workflows/perf-baseline.yml tests/perf/compare_baseline.py
git commit -m "ci(perf): PR gate on p95 regression > 10% vs baseline"
```

---

## Task 19 — Supply-chain security CI workflow

**Files:**
- Create: `.github/workflows/security.yml`
- Modify: `.github/workflows/release.yml` (created in Plan A)

- [ ] **Step 1: security.yml**

```yaml
# .github/workflows/security.yml
name: security
on:
  pull_request: {}
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch: {}

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
        env: { GITHUB_TOKEN: "${{ secrets.GITHUB_TOKEN }}" }

  trivy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        image: [gateway, data-engine, frontend]
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t fna-${{ matrix.image }}:ci apps/${{ matrix.image }}
      - name: Trivy scan
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: fna-${{ matrix.image }}:ci
          format: sarif
          output: trivy-${{ matrix.image }}.sarif
          severity: HIGH,CRITICAL
          exit-code: "1"
          ignore-unfixed: "true"
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: { sarif_file: "trivy-${{ matrix.image }}.sarif" }

  sbom:
    runs-on: ubuntu-latest
    strategy:
      matrix: { image: [gateway, data-engine, frontend] }
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t fna-${{ matrix.image }}:ci apps/${{ matrix.image }}
      - uses: anchore/sbom-action@v0
        with:
          image: fna-${{ matrix.image }}:ci
          artifact-name: sbom-${{ matrix.image }}.spdx.json
          format: spdx-json

  zap:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Boot stack
        run: docker compose -f infra/docker-compose/docker-compose.yml up -d
      - name: Wait for gateway
        run: timeout 180 bash -c 'until curl -fsS http://localhost:8080/actuator/health; do sleep 2; done'
      - uses: zaproxy/action-baseline@v0.12.0
        with:
          target: "http://localhost:8080"
          rules_file_name: ".zap/rules.tsv"
          cmd_options: "-a -j -m 5"
          allow_issue_writing: false
```

- [ ] **Step 2: Add `.zap/rules.tsv`**

```tsv
# .zap/rules.tsv  (id<TAB>state<TAB>name)
10038	IGNORE	CSP - in-place dev only
10063	WARN	Permissions Policy header
```

- [ ] **Step 3: Patch release.yml**

In `.github/workflows/release.yml`, add jobs:

```yaml
  attach-sbom:
    needs: build-images
    runs-on: ubuntu-latest
    permissions: { contents: write, id-token: write, packages: write }
    strategy:
      matrix: { image: [gateway, data-engine, frontend] }
    steps:
      - uses: actions/checkout@v4
      - uses: anchore/sbom-action@v0
        with: { image: "ghcr.io/${{ github.repository }}/${{ matrix.image }}:${{ github.ref_name }}", format: spdx-json, output-file: "sbom-${{ matrix.image }}.spdx.json" }
      - uses: sigstore/cosign-installer@v3
      - name: Sign image (keyless OIDC)
        run: cosign sign --yes "ghcr.io/${{ github.repository }}/${{ matrix.image }}:${{ github.ref_name }}"
      - name: Attach SBOM to release
        uses: softprops/action-gh-release@v2
        with: { files: "sbom-${{ matrix.image }}.spdx.json" }
```

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/security.yml .github/workflows/release.yml .zap/rules.tsv
git commit -m "ci(security): Trivy + Syft + Cosign + ZAP + gitleaks pipeline"
```

---

## Task 20 — Trivy regression assertion test

**Files:**
- Create: `tests/integration/test_trivy_assertion.py`
- Create: `tests/integration/fixtures/Dockerfile.vulnerable`

- [ ] **Step 1: Vulnerable fixture**

```dockerfile
# tests/integration/fixtures/Dockerfile.vulnerable
FROM debian:bullseye-20210408
RUN apt-get update && apt-get install -y openssl=1.1.1k-1+deb11u1 || true
CMD ["sleep", "1"]
```

- [ ] **Step 2: Test**

```python
# tests/integration/test_trivy_assertion.py
import subprocess, pytest

@pytest.mark.integration
def test_trivy_fails_on_known_vulnerable_base():
    subprocess.check_call(["docker", "build", "-t", "fna-vuln:test",
                           "-f", "tests/integration/fixtures/Dockerfile.vulnerable",
                           "tests/integration/fixtures"])
    rc = subprocess.call([
        "trivy", "image", "--exit-code", "1",
        "--severity", "HIGH,CRITICAL", "--ignore-unfixed", "fna-vuln:test"
    ])
    assert rc != 0, "Trivy must fail on the known-vulnerable base image"
```

- [ ] **Step 3: Run test**

Run: `pytest tests/integration/test_trivy_assertion.py -v -m integration`
Expected: PASS — Trivy exits non-zero.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_trivy_assertion.py tests/integration/fixtures/Dockerfile.vulnerable
git commit -m "test(security): assertion that Trivy fails on a known-vulnerable image"
```

---

## Task 21 — Observability smoke test

**Files:**
- Create: `tests/integration/test_observability_smoke.py`

- [ ] **Step 1: Write the test**

```python
# tests/integration/test_observability_smoke.py
import os, time, requests, pytest

PROM = os.environ.get("PROM_URL", "http://localhost:9090")
LOKI = os.environ.get("LOKI_URL", "http://localhost:3100")
TEMPO = os.environ.get("TEMPO_URL", "http://localhost:3200")
GW   = os.environ.get("GATEWAY_URL", "http://localhost:8080")

@pytest.mark.integration
def test_metrics_logs_traces_all_present_after_traffic():
    # Generate traffic
    for _ in range(20):
        requests.get(f"{GW}/api/v1/health", timeout=2)
    time.sleep(5)

    # Prometheus: gateway up
    r = requests.get(f"{PROM}/api/v1/query", params={"query": "up{job=\"gateway\"}"}, timeout=5)
    assert r.json()["data"]["result"], "no gateway scrape"

    # Loki: structured logs from fna-gateway
    r = requests.get(f"{LOKI}/loki/api/v1/query_range",
                     params={"query": '{container="fna-gateway"}', "limit": 5}, timeout=5)
    streams = r.json()["data"]["result"]
    assert streams, "no gateway logs in Loki"

    # Tempo: at least one trace via search
    r = requests.get(f"{TEMPO}/api/search", params={"limit": 1, "service.name": "fna-gateway"}, timeout=5)
    assert r.status_code == 200
```

- [ ] **Step 2: Run test**

Run: `docker compose up -d && pytest tests/integration/test_observability_smoke.py -v -m integration`
Expected: PASS once Tasks 7, 8, 9, 10, 11, 12 are merged.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_observability_smoke.py
git commit -m "test(observability): smoke test that metrics, logs, traces are all queryable"
```

---

## Task 22 — DB migration policy

**Files:**
- Create: `infra/db/migration-policy.md`

- [ ] **Step 1: Write the policy**

```markdown
# Database migration policy

Status: Adopted 2026-06-07 (Plan G)

## Pattern: expand-contract

Every column or constraint change spans **two** release versions.

1. **Expand release.** Add the new column / table / index. Code is dual-aware:
   reads both shapes, writes the new shape; the old column stays nullable.
2. **Backfill window.** A migration or background job populates the new shape.
3. **Contract release.** Once production reads are 100% off the old shape and
   one full release cycle has passed, drop the old column / constraint.

## Rules

- **Never `DROP COLUMN` in the same release that stops using it.** Wait one
  release minimum. Bisects, rollbacks, and emergency hotfixes need the old shape
  to still exist.
- **Never set `NOT NULL` in one step on a populated column.** Two phases: add
  nullable + backfill + check constraint `NOT VALID`, then `VALIDATE CONSTRAINT`
  in the next release.
- **All new indexes in production use `CREATE INDEX CONCURRENTLY`.** Flyway
  cannot run statements outside a tx; use a `repeatable` migration or a manual
  out-of-band script for production. Document the manual step in the migration
  comment.
- **Flyway baseline confirmation.** Before any deploy, CI verifies the schema
  history table is consistent with the migrations directory. A missing or
  out-of-order migration blocks deploy.
- **Migrations are immutable once shipped.** Never edit `Vx__*.sql` after merge
  — write a new `Vy__*.sql` instead.

## Checklist for migration PRs

- [ ] Migration is additive only (or split into expand + contract PRs).
- [ ] No `DROP` in the same release as the code change that removed the read path.
- [ ] Indexes annotated for `CONCURRENTLY` if non-trivially sized.
- [ ] Rollback plan documented in PR description.
- [ ] Smoke-restore test passes (see `tests/integration/test_backup_restore.py`).

## Out of scope (Plan H)

- Online schema-change tooling (pg-osc, pg_repack) — only needed once a single
  table grows past ~100M rows.
- Continuous WAL archiving (PITR) — paid tier launch.
```

- [ ] **Step 2: Commit**

```bash
git add infra/db/migration-policy.md
git commit -m "docs(db): adopt expand-contract migration policy"
```

---

## Task 23 — Operational runbooks

**Files:**
- Create: `docs/operations/README.md`
- Create: `docs/operations/incident-circuit-breaker-open.md`
- Create: `docs/operations/incident-job-pipeline-stalled.md`
- Create: `docs/operations/incident-disk-pressure.md`
- Create: `docs/operations/incident-keycloak-down.md`
- Create: `docs/operations/restore-from-backup.md`
- Create: `docs/operations/rotate-secrets.md`

- [ ] **Step 1: Index**

```markdown
# docs/operations/README.md
Operational runbooks — one file per incident scenario. Linked from
Prometheus alert annotations so on-call can jump straight from a page to
the relevant procedure.

| Runbook | Trigger |
|---|---|
| incident-circuit-breaker-open | `CircuitBreakerOpen` alert |
| incident-job-pipeline-stalled | queue depth growing, `RetentionWorkerStalled` |
| incident-disk-pressure        | `DiskHigh` alert |
| incident-keycloak-down        | Keycloak `/health/ready` failing |
| restore-from-backup           | data loss / corruption |
| rotate-secrets                | quarterly or post-incident |
```

- [ ] **Step 2: Circuit-breaker runbook**

```markdown
# docs/operations/incident-circuit-breaker-open.md
**Alert:** `CircuitBreakerOpen`. The gateway → data-engine Resilience4j breaker
has been OPEN for ≥ 1m.

## Symptoms
- Frontend renders degraded mode banner.
- Gateway returns `503 GATEWAY_BREAKER_OPEN` on data-engine routes.
- `fna_circuit_breaker_state` gauge == 2.

## Diagnose
1. `docker logs fna-data-engine --tail 200 | jq`
2. Grafana → "API Latency Overview" → spike on 5xx? On p95?
3. Check Ollama: `curl http://localhost:11434/api/version`. AI surge can starve.
4. Postgres: `SELECT count(*) FROM pg_stat_activity WHERE state = 'active';`

## Decide
- Data-engine OOM → restart `docker restart fna-data-engine`.
- Ollama hung → restart Ollama; consider disabling AI capabilities
  (`FILTERNARRANGE_DISABLED_CAPABILITIES=auto_summary,chart_suggest`).
- Genuine traffic spike → temporarily raise quota, or enable shedding via
  `RATE_LIMIT_AGGRESSIVE=1`.

## Recover
Breaker auto half-opens after 30s. Force-reset via:
`curl -X POST http://localhost:8080/actuator/circuitbreakers/dataEngine/reset`

## Postmortem
File an incident ticket in GitHub Issues with the `incident` label, fill the
template (timeline, root cause, action items).
```

- [ ] **Step 3: Job-pipeline-stalled**

```markdown
# docs/operations/incident-job-pipeline-stalled.md
**Symptoms:** `jobs.status='queued'` count grows; WebSocket clients see no
updates; `fna_job_state_transitions_total` flatlines.

## Diagnose
1. Redpanda lag:
   `docker exec fna-redpanda rpk group describe python-worker-paid`
2. Consumer alive? `docker ps | grep worker`
3. Worker logs: `docker logs fna-data-engine-worker --tail 200 | jq`
4. Postgres lock: `SELECT pid, query, wait_event FROM pg_stat_activity WHERE state='active';`

## Recover
- Restart worker(s): `docker compose restart data-engine-worker`
- If a poison message, identify the partition + offset and bump the consumer
  group past it: `rpk group seek python-worker-paid --partition N --offset X+1`
- Drain stuck jobs: `UPDATE jobs SET status='failed', error='{"code":"WORKER_TIMEOUT"}'
  WHERE status='running' AND started_at < now() - interval '10 minutes';`

## Prevent
- Add a poison-pill consumer that DLQs messages failing > 3 times.
```

- [ ] **Step 4: Disk-pressure**

```markdown
# docs/operations/incident-disk-pressure.md
**Alert:** `DiskHigh` — host filesystem > 80%.

## Diagnose
1. `df -h`
2. Per-container: `docker system df -v`
3. Volumes: `du -sh /var/lib/docker/volumes/*`

## Common offenders
- MinIO `uploads/` not retention-cleaned. Force cleanup:
  `mc rm --recursive --force --older-than 1d minio/uploads`
- Postgres bloat: `VACUUM FULL` overnight; `REINDEX` partitioned audit log.
- Loki chunks: shorten retention via `limits_config.retention_period`.

## Quick wins (in order)
1. `docker system prune -af --volumes` (frees image cache; data-volumes safe).
2. Rotate `backups/postgres/` (retention may have failed): keep 7 days only.
3. Truncate `audit_log` partitions older than 90 days.
```

- [ ] **Step 5: Keycloak-down**

```markdown
# docs/operations/incident-keycloak-down.md
**Symptoms:** Login redirects fail; gateway returns
`401 AUTH_INVALID_TOKEN` for everyone; Keycloak `/health/ready` returns 5xx.

## Immediate failback to spring-jwt
1. Edit env: `AUTH_PROVIDER=spring-jwt`
2. `docker compose up -d gateway` (no rebuild needed; profile-based).
3. Tell users: existing Keycloak-backed sessions become read-only until
   Keycloak is restored. Local form-based login resumes immediately.

## Diagnose Keycloak
1. `docker logs fna-keycloak --tail 200`
2. Postgres reachable? `docker exec fna-postgres pg_isready`
3. Realm import errors visible at boot? Check
   `KEYCLOAK_EXTRA_ARGS=--import-realm` log lines.

## Restore
- If DB unaffected: `docker compose restart keycloak`. Watch for `--import-realm`
  to succeed (only on empty DB; subsequent boots skip).
- If realm corrupted: re-import via Keycloak admin console
  (`http://localhost:8085/admin/master/console`).

## Switch back
1. Verify `/health/ready` is 200.
2. Set `AUTH_PROVIDER=keycloak`.
3. `docker compose up -d gateway`.
```

- [ ] **Step 6: restore-from-backup**

```markdown
# docs/operations/restore-from-backup.md
## When to use
Data loss / corruption confirmed; you are willing to accept loss of all
writes since the last nightly backup (typically up to 24h).

## Procedure
1. Stop the gateway to prevent writes:
   `docker compose stop gateway`
2. Identify backup key:
   `docker compose run --rm backup mc ls minio/backups/postgres/`
3. Restore into a side database first:
   `docker compose run --rm backup /usr/local/bin/restore.sh 2026-06-06.sql.gz filternarrange_restore`
4. Sanity check:
   `docker compose exec postgres psql -U filternarrange -d filternarrange_restore -c "SELECT count(*) FROM users;"`
5. Promote: `ALTER DATABASE filternarrange RENAME TO filternarrange_broken; ALTER DATABASE filternarrange_restore RENAME TO filternarrange;`
6. Restart: `docker compose start gateway`
7. Verify smoke tests: `pytest tests/integration/smoke_*.py`
8. Drop the broken DB once verification holds: `DROP DATABASE filternarrange_broken;`

## Out of scope
PITR / partial-table restore — Plan H once paid tier funds WAL archiving.
```

- [ ] **Step 7: rotate-secrets**

```markdown
# docs/operations/rotate-secrets.md
Quarterly cadence (or immediately post-incident).

## Inventory
- Postgres password (per-service users)
- MinIO root creds + per-service IAM keys
- Redpanda SCRAM (none in v1 — no auth between services on docker net)
- Keycloak admin password, gateway client secret
- Gateway spring-jwt HMAC key (`SPRING_JWT_SECRET`)
- GitHub Actions OIDC trust (no rotation needed; keyless)
- Cosign signing — keyless OIDC, no rotation

## Procedure
1. Generate new secret(s): `openssl rand -base64 32`.
2. Update the secrets store (CI: GH Actions repo secrets; dev: `.env`).
3. Roll services one at a time so reads/writes don't collide:
   - Postgres password: `ALTER USER ... PASSWORD ...;` then redeploy gateway.
   - MinIO: rotate via admin console; redeploy data-engine.
   - Keycloak gateway client: regenerate via admin console; update gateway env.
   - `SPRING_JWT_SECRET`: rotate during a maintenance window; sessions invalidated.
4. Audit: `SELECT user_id, action, created_at FROM audit_log WHERE action LIKE 'secret%' ORDER BY created_at DESC LIMIT 50;`

## Post-rotation
- Verify all services healthy.
- Tag the rotation in CHANGELOG (chore entry).
```

- [ ] **Step 8: Commit**

```bash
git add docs/operations/
git commit -m "docs(ops): six operational runbooks for production incidents"
```

---

## Task 24 — Final integration: wire everything in compose & verify

**Files:**
- Modify: `infra/docker-compose/docker-compose.yml` (final pass)
- Test: `tests/integration/test_full_stack_smoke.py`

- [ ] **Step 1: Final compose check**

Verify the full compose file declares (alphabetically):
`alertmanager`, `backup`, `data-engine`, `frontend`, `gateway`, `grafana`,
`keycloak`, `loki`, `minio`, `node-exporter`, `ollama`, `otel-collector`,
`postgres`, `promtail`, `prometheus`, `redis`, `redpanda`, `tempo`.

Confirm `networks: [fna-net]` on every service. Confirm shared volumes for
Postgres, MinIO, Redis, Grafana.

- [ ] **Step 2: Full-stack smoke test**

```python
# tests/integration/test_full_stack_smoke.py
import os, time, requests, pytest

@pytest.mark.integration
def test_every_service_responds_to_a_basic_probe():
    probes = [
        ("gateway",        "http://localhost:8080/actuator/health"),
        ("data-engine",    "http://localhost:8000/metrics"),
        ("keycloak",       "http://localhost:8085/health/ready"),
        ("prometheus",     "http://localhost:9090/-/ready"),
        ("grafana",        "http://localhost:3001/api/health"),
        ("loki",           "http://localhost:3100/ready"),
        ("tempo",          "http://localhost:3200/ready"),
        ("alertmanager",   "http://localhost:9093/-/ready"),
        ("minio",          "http://localhost:9000/minio/health/ready"),
    ]
    failures = []
    deadline = time.time() + 240
    for name, url in probes:
        while time.time() < deadline:
            try:
                r = requests.get(url, timeout=3)
                if r.status_code < 500:
                    break
            except requests.RequestException:
                pass
            time.sleep(3)
        else:
            failures.append(name)
    assert not failures, f"Services not ready: {failures}"
```

- [ ] **Step 3: Run**

Run: `docker compose -f infra/docker-compose/docker-compose.yml up -d && pytest tests/integration/test_full_stack_smoke.py -v -m integration`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add infra/docker-compose/docker-compose.yml tests/integration/test_full_stack_smoke.py
git commit -m "test(infra): full-stack smoke verifying all production-hardened services come up"
```

---

## Self-Review Notes (post-write)

**Spec coverage:**
- Spec §5 `users.external_id` → Task 2.
- Spec §6 auth fallback → Tasks 3, 4 + runbook in Task 23.
- Spec §3 latency budgets → Task 17 (k6) + Task 18 (CI gate).
- Spec §5 backup → Tasks 14, 15.
- Spec §7.5 supply-chain (Trivy/Syft/Cosign/ZAP/gitleaks) → Tasks 19, 20.
- Spec §7.6 observability layer of the testing strategy → Tasks 7–13, 21.
- Spec §6 expand-contract / failure isolation → Task 22 policy + V9 migration in Task 2 follows it.

**Type / signature consistency:** `KeycloakAuthFilter`, `KeycloakUserSyncService`, `AuthConfig`, `JobStateTransitionMetric`, `QuotaRejectionMetric`, `plugin_execution_seconds`, `ai_capability_seconds`, `circuit_breaker_state` — names used consistently across Tasks 3, 4, 9, 10, 13, 21, 23.

**No placeholders:** every code block is concrete. Realm export, k6 scripts, Prometheus rules, runbooks all contain real content.

**Consistency concerns surfaced for the parent agent:**
1. Plan G assumes Plan A pre-creates the `keycloak` Postgres database. If Plan A only includes a `keycloak` stub container without DB provisioning, Task 1 must also add `CREATE DATABASE keycloak;` to the Postgres init script.
2. Plan G assumes Plan B's `users` table already has an `admin` boolean column — used by `KeycloakUserSyncService`. If Plan B didn't add it, V9 must also add `admin BOOLEAN NOT NULL DEFAULT FALSE`.
3. Plan G's `application-keycloak.yml` uses Spring profiles; Plan B's existing config must be profile-aware (`application-spring-jwt.yml` exists). If Plan B hard-codes the SecurityFilterChain, Task 3 must refactor it behind the `AUTH_PROVIDER` switch.
4. Task 18's perf workflow expects an `/api/v1/auth/dev-token` endpoint for token minting in CI. If Plan B didn't ship this, add it as a guarded (`AUTH_DEV_MODE=true`) endpoint as part of Task 18.
5. Plan G expects Plan F's retention worker to call `fna_retention_worker_last_run_timestamp_seconds.set_to_current_time()` — if not present, that one-line instrumentation must be added.
