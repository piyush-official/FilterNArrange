# Incident — Keycloak unreachable

Plan G §T23.

## Symptoms

- 401 on every authenticated request after Keycloak restart
- Frontend login redirect loops to `/login` → `/auth/keycloak` → `/login`
- Gateway logs show `JwtDecoder` failure: cannot fetch JWKS from issuer URL

## Immediate failback to spring-jwt

If Keycloak is down for > 5 minutes and we have customer impact:

```bash
AUTH_PROVIDER=spring-jwt docker compose up -d --no-deps gateway
```

Existing spring-jwt sessions keep working. Keycloak-only users won't be able
to log in until Keycloak is back.

## Diagnose Keycloak

- `docker compose logs keycloak | tail -50`
- `curl http://keycloak:8080/realms/filternarrange/.well-known/openid-configuration`
- If Postgres-backed: check the `keycloak` database is reachable

## Restore

- `docker compose restart keycloak`
- Wait for `/health/ready` to return 200
- Verify the JWKS endpoint returns keys

## Switch back

```bash
AUTH_PROVIDER=keycloak docker compose up -d --no-deps gateway
```

## When to use

This runbook applies to Plan G PR-1's dual-mode auth. If the deployment only
has Keycloak (post-spring-jwt removal in Plan H), the failback step doesn't
apply — restoration is the only path.
