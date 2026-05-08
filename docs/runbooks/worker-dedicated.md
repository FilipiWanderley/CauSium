# Dedicated Ingestion Worker Runbook (Phase 1A)

## Objective

Prepare a dedicated ingestion worker process that runs outside the API process.
This phase only prepares support files and operating guidance. No infrastructure
or production changes are performed here.

## Current Architecture

- API remains the production entrypoint.
- API must keep `INGESTION_WORKER_ENABLED=false`.
- Dedicated runner exists at `backend/app/workers/ingestion_runner.py`.
- Worker is intended to run separately with:
  - `python -m app.workers.ingestion_runner`

## Startup Command

Use the worker startup script:

```bash
bash startup-worker.sh
```

The script executes:

```bash
python -m app.workers.ingestion_runner
```

## Mandatory Environment Variables (Worker)

- `APP_ENV`
- `DATABASE_URL`
- `ENCRYPTION_KEY`
- `CLICKHOUSE_HOST`
- `CLICKHOUSE_PORT`
- `CLICKHOUSE_USER`
- `CLICKHOUSE_PASSWORD`
- `CLICKHOUSE_DB`
- `CLICKHOUSE_SECURE`
- `CLICKHOUSE_VERIFY`
- `CLICKHOUSE_SSL_MIN_VERSION`
- `REDIS_SSL_VERIFY`
- `REDIS_SSL_CA_FILE` (if certificate pinning is used)
- `REDIS_SSL_MIN_VERSION`
- `INGESTION_INTERVAL_HOURS`

## Variables That Must NOT Be Activated Yet (Phase 1A)

- `REDIS_URL` must not be configured in this phase.
- Any backfill/sync trigger setting must not be introduced.
- Keep API-side `INGESTION_WORKER_ENABLED=false`.

## Validation (When Preparing a Future Controlled Activation)

- Confirm worker startup command only launches ingestion runner.
- Confirm no gunicorn/uvicorn startup in worker process.
- Confirm no API import path usage for worker startup.
- Confirm no migrations executed by worker startup script.
- Confirm no manual sync execution.
- Confirm no 90-day backfill execution.

## Rollback

- Stop dedicated worker process/app.
- Remove `REDIS_URL` from worker environment (when it is eventually enabled).
- Keep API app untouched and stable with `INGESTION_WORKER_ENABLED=false`.

## Stop Criteria

Stop immediately if any of the following occurs:

- API health degrades.
- Worker shows recurring startup failures.
- Redis/TLS errors repeat after controlled activation.
- DLQ growth indicates systemic ingestion failure.

## Explicit Prohibitions For This Phase

- Do not execute backfill 90 days.
- Do not execute manual sync.
- Do not change Azure infrastructure.
- Do not deploy.
- Do not commit automatically without approval.
