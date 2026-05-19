# Backup & Restore Runbook

## Overview

CauSium relies on three persistent datastores that require backup coverage:

| Datastore | Purpose | Data Criticality |
|-----------|---------|-----------------|
| PostgreSQL | Auth, orgs, workflow, audit chain, config | **Critical** — loss means total platform state loss |
| ClickHouse | Cost facts, usage metrics, time-series analytics | **High** — loss means re-ingestion required (recoverable but slow) |
| Redis | Queues, rate-limit counters, idempotency cache | **Low** — ephemeral by design; loss causes temporary disruption only |

## Quick Reference

```bash
# Take a full backup
make backup
# or: ./scripts/backup.sh

# Restore from a specific backup
make restore BACKUP=backups/2026-01-15_143022
# or: ./scripts/restore.sh backups/2026-01-15_143022

# Full DR drill (backup + restore + RTO/RPO measurement)
make dr-drill
# or: ./scripts/rto_rpo_test.sh

# Dry-run (backup only, no restore)
make dr-drill-dry
# or: DRY_RUN=true ./scripts/rto_rpo_test.sh

# Verify backup structure
make verify-backup BACKUP=backups/2026-01-15_143022
```

## Current Strategy

### Managed Deployments (Azure / Production)

| Datastore | Backup Method | RPO | RTO |
|-----------|--------------|-----|-----|
| PostgreSQL (Azure Database for PostgreSQL Flexible Server) | Azure automated backups (point-in-time restore, geo-redundant) | 5 min | < 1 hour |
| ClickHouse (self-managed on VM or Azure Container) | Scheduled `scripts/backup.sh` to Azure Blob Storage | 24 hours | 2–4 hours |
| Redis (Azure Cache for Redis) | Azure automated persistence (AOF/RDB) | Minutes | < 30 min |

### Self-Managed / Docker Compose

| Datastore | Backup Method | RPO | RTO |
|-----------|--------------|-----|-----|
| PostgreSQL | `scripts/backup.sh` → `pg_dump --format=custom` | Depends on schedule | < 5 min |
| ClickHouse | `scripts/backup.sh` → Native binary per table | Depends on schedule | < 10 min |
| Redis | `scripts/backup.sh` → BGSAVE + RDB copy | Depends on schedule | < 1 min |

### Recommended Backup Schedule

| Environment | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| Production | Every 6 hours | 30 days | Azure Blob / S3 / NAS |
| Staging | Daily | 7 days | Local disk |
| Development | Manual (before risky changes) | 3 days | Local `backups/` |

## Backup Procedure

### Automated (scripts/backup.sh)

The backup script handles all three datastores in sequence:

```bash
# Default: writes to ./backups/<timestamp>/
./scripts/backup.sh

# Custom backup location
BACKUP_ROOT=/mnt/nas/causium-backups ./scripts/backup.sh

# Override credentials (if not in .env)
POSTGRES_USER=myuser POSTGRES_PASSWORD=mypass ./scripts/backup.sh
```

**What it produces:**
```
backups/2026-01-15_143022/
├── postgres/
│   └── causium.dump          # pg_dump custom format (compressed, parallel-restoreable)
├── clickhouse/
│   ├── cost_facts.bin        # Native binary per table
│   ├── usage_metrics.bin
│   └── ...
├── redis/
│   └── dump.rdb              # Redis RDB snapshot
├── backup.log                # Full execution log
└── backup_report.json        # Timing, sizes, success/failure
```

### Manual PostgreSQL Backup (without script)

```bash
# From Docker Compose
docker compose exec -T postgres \
  pg_dump --username=causium --format=custom --compress=9 causium \
  > backup_$(date +%Y%m%d_%H%M%S).dump

# From Azure (using pg_dump against managed instance)
PGPASSWORD=$AZURE_PG_PASSWORD pg_dump \
  --host=$AZURE_PG_HOST --port=5432 --username=$AZURE_PG_USER \
  --format=custom --compress=9 causium \
  > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Manual ClickHouse Backup (without script)

```bash
# Export a single table
docker compose exec -T clickhouse \
  clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="SELECT * FROM causium.cost_facts FORMAT Native" \
  > cost_facts_$(date +%Y%m%d).bin

# Export all tables
for table in $(docker compose exec -T clickhouse \
  clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="SHOW TABLES FROM causium"); do
  docker compose exec -T clickhouse \
    clickhouse-client --user=causium --password=$CH_PASSWORD \
    --query="SELECT * FROM causium.$table FORMAT Native" \
    > "${table}_$(date +%Y%m%d).bin"
done
```

## Restore Procedures

### Automated (scripts/restore.sh)

```bash
# Full restore from a backup directory
./scripts/restore.sh backups/2026-01-15_143022

# Skip specific datastores
SKIP_REDIS=true ./scripts/restore.sh backups/2026-01-15_143022
SKIP_CLICKHOUSE=true ./scripts/restore.sh backups/2026-01-15_143022

# Custom health check timeout (default: 120s)
HEALTH_TIMEOUT=300 ./scripts/restore.sh backups/2026-01-15_143022
```

**What it does:**
1. Validates backup directory structure
2. Drops and recreates PostgreSQL database, then `pg_restore`
3. Truncates ClickHouse tables, then streams Native binary back
4. Copies RDB into Redis container and restarts it
5. Waits for all services to pass health checks
6. Measures RTO (wall-clock time from start to all-healthy)
7. Writes `restore_report.json` with timing and health status

### PostgreSQL — Point-in-Time Restore (Azure Managed)

1. Navigate to Azure Portal → PostgreSQL Flexible Server → Backups
2. Select restore point (timestamp)
3. Create new server from restore point
4. Update `DATABASE_URL` in App Service configuration to point to restored server
5. Restart the application
6. Verify: `GET /health/detailed` returns `postgres: ok`

### PostgreSQL — Manual Restore (Docker / Self-Managed)

```bash
# Stop the application
docker compose stop backend worker

# Drop and recreate
docker compose exec -T postgres \
  psql --username=causium --dbname=postgres \
  --command="DROP DATABASE IF EXISTS causium"
docker compose exec -T postgres \
  psql --username=causium --dbname=postgres \
  --command="CREATE DATABASE causium OWNER causium"

# Restore from dump
docker compose exec -T postgres \
  pg_restore --username=causium --dbname=causium --single-transaction \
  - < backups/2026-01-15_143022/postgres/causium.dump

# Run pending migrations (in case backup predates latest schema)
docker compose exec backend alembic upgrade head

# Restart
docker compose up -d backend worker
```

### ClickHouse — Manual Restore

```bash
# Restore a single table
docker compose exec -T clickhouse \
  clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="TRUNCATE TABLE causium.cost_facts"

docker compose exec -T clickhouse \
  clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="INSERT INTO causium.cost_facts FORMAT Native" \
  < backups/2026-01-15_143022/clickhouse/cost_facts.bin
```

### Redis — Recovery

Redis data is ephemeral. On total loss:
- Rate-limit counters reset (brief window of elevated limits)
- Idempotency cache clears (safe — worst case is duplicate processing)
- Ingestion queue empties (next scheduled sync re-enqueues all accounts)

No manual restore action required. The system self-heals within one ingestion cycle.

To restore from RDB (if needed for queue state):
```bash
docker compose cp backups/2026-01-15_143022/redis/dump.rdb redis:/data/dump.rdb
docker compose restart redis
```

## Backup Verification

### Automated Verification

```bash
# Structural check (files exist, report is valid)
make verify-backup BACKUP=backups/2026-01-15_143022
```

### Full Verification (Restore to Staging)

This is the gold standard — restore a backup into a clean environment and verify data integrity:

```bash
# 1. Start a clean staging environment
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# 2. Restore the backup
./scripts/restore.sh backups/2026-01-15_143022

# 3. Verify application health
curl -sf http://localhost:8000/health/detailed | python3 -m json.tool

# 4. Verify data integrity
# - Check row counts match expectations
docker compose exec -T postgres \
  psql --username=causium --dbname=causium \
  --command="SELECT schemaname, relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 20"

# - Verify audit chain integrity
curl -sf http://localhost:8000/api/v1/audit-chain/verify \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 5. Tear down staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml down -v
```

### Verification Checklist (Post-Restore)

- [ ] `GET /health/detailed` — all checks return `ok`
- [ ] `GET /metrics/slo` — no error spike, SLO targets met
- [ ] Audit chain integrity: `GET /api/v1/audit-chain/verify` (per org) — `is_valid: true`
- [ ] Latest data timestamps in ClickHouse match expected restore point
- [ ] Users can log in and access their workspaces
- [ ] Worker heartbeat file is being updated (`/tmp/worker_heartbeat` < 60s old)
- [ ] No unexpected entries in DLQ after restore

## Disaster Recovery Drill Checklist

> **Purpose:** Validate that the team can restore CauSium from backup within RTO/RPO targets.
> **Frequency:** Quarterly (minimum), or after any significant infrastructure change.
> **Environment:** Staging only. Never run destructive DR drills against production.

### Pre-Drill Preparation

- [ ] Schedule a maintenance window (even for staging)
- [ ] Notify the team that a DR drill is in progress
- [ ] Ensure a recent backup exists (< 24 hours old)
- [ ] Verify staging environment is isolated from production
- [ ] Have the runbook open (this document)
- [ ] Designate a drill lead and an observer/note-taker

### Drill Scenario: Complete Data Loss Recovery

**Simulated failure:** All three datastores lose their data simultaneously.

#### Step 1 — Take a fresh backup (baseline)
```bash
make backup
# Record the backup directory: _______________
```

#### Step 2 — Simulate data loss
```bash
# Stop all services
docker compose stop backend worker

# Destroy PostgreSQL data
docker compose exec -T postgres psql --username=causium --dbname=postgres \
  --command="DROP DATABASE IF EXISTS causium"
docker compose exec -T postgres psql --username=causium --dbname=postgres \
  --command="CREATE DATABASE causium OWNER causium"

# Flush Redis
docker compose exec -T redis redis-cli FLUSHALL

# Truncate ClickHouse (if accessible)
docker compose exec -T clickhouse clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="SELECT name FROM system.tables WHERE database='causium'" | \
  xargs -I{} docker compose exec -T clickhouse clickhouse-client --user=causium --password=$CH_PASSWORD \
  --query="TRUNCATE TABLE causium.{}"
```

#### Step 3 — Start the clock (RTO measurement begins)
```bash
echo "RESTORE START: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

#### Step 4 — Execute restore
```bash
make restore BACKUP=backups/<timestamp-from-step-1>
# or: ./scripts/rto_rpo_test.sh (automated measurement)
```

#### Step 5 — Verify recovery
Run the verification checklist above. Record results:

| Check | Result | Notes |
|-------|--------|-------|
| /health/detailed | ☐ Pass / ☐ Fail | |
| /metrics/slo | ☐ Pass / ☐ Fail | |
| Audit chain integrity | ☐ Pass / ☐ Fail | |
| User login works | ☐ Pass / ☐ Fail | |
| Worker heartbeat active | ☐ Pass / ☐ Fail | |
| ClickHouse data present | ☐ Pass / ☐ Fail | |

#### Step 6 — Stop the clock
```bash
echo "RESTORE END: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

### Success Criteria

| Metric | Target | Actual | Pass? |
|--------|--------|--------|-------|
| RTO (time to full recovery) | ≤ 5 minutes (self-managed) / ≤ 1 hour (Azure) | ___ | ☐ |
| RPO (data age at restore) | ≤ 24 hours (ClickHouse) / ≤ 5 min (PostgreSQL managed) | ___ | ☐ |
| All health checks pass | Yes | ___ | ☐ |
| Audit chain intact | Yes | ___ | ☐ |
| No data corruption detected | Yes | ___ | ☐ |

### Post-Drill Actions

- [ ] Record drill results in `backups/<timestamp>/rto_rpo_report.json`
- [ ] File any issues discovered during the drill
- [ ] Update this runbook if procedures were unclear or incorrect
- [ ] Schedule next drill (quarterly)
- [ ] If targets were missed: create action items to improve RTO/RPO

### Automated DR Drill (scripts/rto_rpo_test.sh)

For routine validation, use the automated drill script:

```bash
# Full automated drill with RTO/RPO measurement
./scripts/rto_rpo_test.sh

# Adjust targets
RTO_TARGET_S=600 RPO_TARGET_S=86400 ./scripts/rto_rpo_test.sh
```

The script:
1. Runs `backup.sh` to take a fresh backup
2. Runs `restore.sh` to restore from that backup
3. Measures wall-clock RTO and RPO window
4. Emits a JSON report with pass/fail against targets
5. Exit code 0 = all targets met, 1 = one or more missed

## Alerting on Backup Failures

Prometheus alerting rules are configured in `monitoring/rules.yml`:

- **CauSiumBackupOverdue** — fires if no successful backup in 25 hours
- Requires pushing a timestamp metric after each successful backup

To push the metric after `backup.sh` succeeds:
```bash
# Example: push to Prometheus Pushgateway
echo "causium_last_backup_success_timestamp_seconds $(date +%s)" | \
  curl --data-binary @- http://pushgateway:9091/metrics/job/causium_backup
```

## Contacts

| Role | Responsibility |
|------|---------------|
| Platform Admin | Trigger restore, verify integrity |
| Infrastructure Lead | Azure resource management, backup configuration |
| On-Call Engineer | First responder for data loss incidents |

---

*Last updated: 2025-01-01*
*Status: Operational — scripts tested, DR drill checklist ready for quarterly execution.*
