# Keycloak realm — `filternarrange`

Auto-imported from `realm-export.json` on first boot.

## Clients

- `filternarrange-frontend` — public, PKCE S256, redirect to `http://localhost:5173/*`
- `filternarrange-gateway` — confidential, bearer-only, secret `dev-only-gateway-secret` (override per environment)

## Realm roles

- `user`  — assigned by default on registration
- `paid`  — mirrored into `users.tier='paid'` by the gateway sync (Plan G §T3)
- `admin` — mirrored into `users.admin=true`

## Seeded users (dev only)

- `dev-user` / `dev-password`  — free tier
- `dev-paid` / `paid-password` — paid tier

> These credentials are for docker-compose only. **Never reuse them anywhere else.**

## Switching the gateway to Keycloak

```bash
AUTH_PROVIDER=keycloak \
KEYCLOAK_ISSUER=http://keycloak:8080/realms/filternarrange \
docker compose -f infra/docker-compose/docker-compose.yml up gateway
```

The gateway resolves JWKS from `${KEYCLOAK_ISSUER}/protocol/openid-connect/certs` automatically.
