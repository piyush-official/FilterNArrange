# apps/gateway

Spring Boot 3.x API gateway (Java 21). Owns auth, tier/quota enforcement, routing to the data-engine, WebSocket push for async results, and the Postgres datastore (per spec §2 service map).

## Layout (hexagonal — see spec §6)

- `src/main/java/io/filternarrange/gateway/api` — REST controllers
- `src/main/java/io/filternarrange/gateway/application` — use-case services
- `src/main/java/io/filternarrange/gateway/domain` — entities + ports (pure, zero outside deps)
- `src/main/java/io/filternarrange/gateway/infrastructure` — adapters (persistence, messaging, storage, http)
- `src/main/java/io/filternarrange/gateway/platform` — auth, errors, observability

## Local run

```bash
./gradlew bootRun
```

## Tests

```bash
./gradlew test
```
