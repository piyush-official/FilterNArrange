# Incident — job pipeline stalled

Plan G §T23.

## Symptoms

- `DetectionP95High` or `FilterPreviewP95High` firing
- Customers report submitted jobs sitting in `queued` for minutes
- `/api/v1/jobs/{id}` returns `status=queued` past expected wait

## Diagnose

- `kubectl logs -n filternarrange deployment/data-engine -c worker` or `docker compose logs data-engine`
- Check Kafka consumer lag: `rpk topic consumer-groups list` then `rpk group describe python-worker-free`
- Look for stuck idempotency keys: `redis-cli KEYS 'gw:idem:*' | wc -l`

## Decide

- Lag growing + worker logs show errors → **worker bug**, roll back or hotfix
- Lag growing + worker logs show no traffic → **worker offline**, restart
- Lag flat at 0 + jobs queued in DB → **gateway producer not emitting**, check `jobsKafkaTemplate` errors and breaker state

## Recover

- Restart worker: `docker compose restart data-engine`
- If a poison message is jamming a consumer, advance the offset:
  `rpk group seek python-worker-free --to end --topics topic.v1.jobs.free`

## Postmortem

Log decision + 24-hour follow-up in `docs/postmortems/YYYY-MM-DD-job-pipeline.md`.
