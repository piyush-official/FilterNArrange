# Incident — dataEngine circuit breaker open

Plan G §T23.

## Symptoms

- `CircuitBreakerOpen` alert firing
- Customers see 503 `SERVICE_DEGRADED` on `/api/v1/detect`, `/filter/preview`, etc.
- `/actuator/metrics/resilience4j.circuitbreaker.state{name="dataEngine"}` shows state=OPEN

## Diagnose

- `docker compose logs data-engine` — is the service responding at all?
- `curl http://data-engine:8000/health` from gateway container — what status?
- Check Ollama: AI endpoints may be timing out → upstream timeouts → breaker trip

## Recover

- If data-engine is dead, restart: `docker compose restart data-engine`
- Force the breaker closed once data-engine is healthy:
  `curl -XPOST http://gateway:8080/actuator/circuitbreakers/dataEngine -d 'state=CLOSED'`
- If Ollama timeouts caused the trip, raise `AI_TIMEOUT_SECONDS` env or disable the offending AI capability via `FILTERNARRANGE_DISABLED_AI`

## Prevent

- Capacity-plan Ollama: pin a smaller default model if the host can't handle 8B-parameter llama under load
- Bump `data-engine.read-timeout-ms` if user-traffic shape changed
