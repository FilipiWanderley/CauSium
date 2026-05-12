# Incident Report — Azure Cost Export Duplication

**Date:** 2026-05-12  
**Severity:** Medium (financial data accuracy)  
**Status:** Resolved  
**Affected Tenant:** Queiroz (`org_id: 1859c537-5f07-4923-9555-42817567c32d`)  
**Affected Subscription:** ALYA (`180203f3-3ae4-4a2b-8042-158841b99818`)

---

## Summary

The CauSium Dashboard displayed inflated "Current Month Cost" values (~16x the real Azure Portal value) due to duplicate ingestion of Azure Cost Management Export CSV files. The root cause was that Azure generates **cumulative month-to-date exports** and the pipeline performed raw INSERTs without clearing overlapping data.

---

## Timeline

| When | What |
|------|------|
| 2026-05-04 | Initial Azure ingest confirmed working (10k cost_facts rows) |
| 2026-05-12 | Financial reconciliation investigation started |
| 2026-05-12 | Root cause identified: cumulative exports causing 16x duplication |
| 2026-05-12 | Fix deployed: delete-before-insert for Azure provider |
| 2026-05-12 | Production validated: duplication_factor = 1, data converged |

---

## Root Cause Analysis

### How Azure Cost Exports Work

Azure Cost Management Exports generate CSV files on a schedule (typically daily). Each export is **cumulative month-to-date** — meaning:

- Export on May 1 → contains cost rows for May 1
- Export on May 2 → contains cost rows for May 1 + May 2
- Export on May 10 → contains cost rows for May 1 through May 10
- Export on May 16 → contains cost rows for May 1 through May 16

Each export is a **complete snapshot** of the month up to that point, not an incremental delta.

### What CauSium Was Doing Wrong

The ingestion pipeline:
1. Listed all CSV blobs in the Azure Storage container
2. For each new blob (not previously checkpointed): parsed all rows and INSERTed into ClickHouse
3. Saved a checkpoint (`blob_name::etag`) to prevent reprocessing the same file

The checkpoint prevented reprocessing the **same file**, but did NOT prevent the **same data** from being inserted multiple times across different files. Each new daily export re-delivered all previous days' data.

### Result

With 16 daily exports processed, each row from day 1 existed 16 times in `cost_facts`. The Dashboard's `get_month_cost()` query (`SELECT sum(cost_usd)`) summed all duplicates, showing ~16x the real cost.

### Contributing Factors

1. **No deduplication at INSERT time** — ClickHouse `MergeTree` (the engine used in production) does not deduplicate on INSERT
2. **Checkpoint granularity too coarse** — checkpoints tracked files, not data ranges
3. **No overlap detection** — the pipeline had no awareness that exports are cumulative
4. **Column naming ambiguity** — the field `cost_usd` stores values in BillingCurrency (BRL), not USD, adding confusion during investigation

---

## Impact

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| Duplication factor | ~16x | 1x |
| Dashboard "Current Month Cost" | ~16x inflated | Correct |
| Data integrity | Duplicated rows | Clean |
| Financial accuracy | Unreliable | Matches Azure Portal |

**No data loss occurred.** The issue was purely additive (extra rows), not destructive.

---

## Diagnosis Process

### Investigation Steps

1. Traced `get_month_cost()` → simple `SELECT sum(cost_usd)` with no dedup
2. Traced Azure connector → `_fetch_costs_from_blob_exports()` → raw INSERT
3. Identified fallback chain: `PreTaxCost > Cost > CostUSD > CostInBillingCurrency > ...`
4. Confirmed no currency conversion exists (BRL stored as `cost_usd`)
5. Confirmed ClickHouse engine is `MergeTree` (no native dedup)
6. Confirmed checkpoint logic only prevents same-file reprocessing

### Validation Queries Used

```sql
-- Duplication factor
SELECT
    count() AS total_rows,
    uniqExact(date, resource_id, service) AS distinct_combinations,
    round(count() / uniqExact(date, resource_id, service), 2) AS avg_duplication_factor
FROM cost_facts
WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d'
  AND subscription_id = '180203f3-3ae4-4a2b-8042-158841b99818'
  AND provider = 'azure'
  AND toYYYYMM(date) = 202605;

-- Top duplicates
SELECT date, resource_id, service, count() AS duplicates
FROM cost_facts
WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d'
  AND subscription_id = '180203f3-3ae4-4a2b-8042-158841b99818'
  AND provider = 'azure'
  AND toYYYYMM(date) = 202605
GROUP BY date, resource_id, service
HAVING duplicates > 1
ORDER BY duplicates DESC
LIMIT 10;
```

---

## Fix Applied

**Commit:** `a76d70c` — `fix: prevent duplicate azure cost export ingestion`  
**File:** `backend/app/domains/cloud_ledger/service.py`  
**Strategy:** Delete-before-insert for Azure provider

### How It Works

Before inserting a new Azure cost batch into ClickHouse:

1. Group incoming rows by `subscription_id`
2. For each subscription: determine `min_date` and `max_date` from the batch
3. Execute a scoped DELETE:
   ```sql
   DELETE FROM cost_facts
   WHERE org_id = {org_id}
     AND account_id = {account_id}
     AND provider = 'azure'
     AND subscription_id = {subscription_id}
     AND date >= {min_date}
     AND date <= {max_date}
   ```
4. INSERT the fresh snapshot

This makes ingestion **idempotent** — running it N times produces the same result as running it once.

### Safety Guards

| Guard | Implementation |
|-------|---------------|
| Only Azure | `if account.provider == CloudProvider.AZURE` + hardcoded `provider = 'azure'` in SQL |
| Requires subscription_id | Skips with warning if missing |
| Requires date range | Skips if no dates in batch |
| Scoped to org + account | Both in WHERE clause |
| Abort on delete failure | Exception propagates, INSERT never runs |
| Self-healing | If INSERT fails, next sync re-ingests (checkpoint not saved) |

---

## ClickHouse SharedMergeTree Behavior

The production ClickHouse instance uses **SharedMergeTree** (ClickHouse Cloud).

### DELETE Semantics

The fix uses `DELETE FROM` (Lightweight Delete, ClickHouse >= 22.8):
- Marks rows as deleted **immediately** (not eventual)
- Subsequent queries (including the INSERT that follows) do not see deleted rows
- No partition rewrite — lightweight and fast
- Fully supported on SharedMergeTree

### Why Not `ALTER TABLE ... DELETE`

| | Lightweight DELETE | ALTER TABLE DELETE |
|---|---|---|
| Visibility | Immediate | Eventual (mutation) |
| Performance | Fast | Heavy (rewrites parts) |
| Use case | Transactional cleanup | Bulk historical cleanup |

---

## Risks Considered

| Risk | Assessment | Mitigation |
|------|-----------|-----------|
| Window between DELETE and INSERT | Milliseconds, background worker only | Acceptable for analytics workload |
| INSERT fails after DELETE | Data temporarily absent | Self-heals on next sync cycle |
| Race condition (multiple workers) | Unlikely (checkpoint prevents) | Even if occurs, result is idempotent |
| Partial month delete | By design — only deletes the range covered by the batch | Correct for cumulative exports |
| ClickHouse version < 22.8 | DELETE fails, ingest aborts | No data corruption, clear error log |

---

## Post-Deploy Validation

### Results (2026-05-12)

| Metric | Value |
|--------|-------|
| `avg_duplication_factor` | **1** (no duplicates) |
| `total_rows` = `distinct_combinations` | Confirmed |
| Engine | SharedMergeTree |
| Currency | BRL |
| Total maio 2026 | ~27.9k BRL |
| Convergence | Automatic (worker re-sync applied fix) |

The fix resolved existing duplicates automatically — the next scheduled worker sync applied delete-before-insert, which cleared the 16x duplicated data and replaced it with a single clean snapshot.

---

## Operational Playbook

### Detecting Duplication Regression

Run periodically or after ingestion changes:

```sql
SELECT
    subscription_id,
    toYYYYMM(date) AS month,
    count() AS total_rows,
    uniqExact(date, resource_id, service) AS distinct_combos,
    round(count() / uniqExact(date, resource_id, service), 2) AS dup_factor
FROM cost_facts
WHERE org_id = '{ORG_ID}'
  AND provider = 'azure'
GROUP BY subscription_id, month
HAVING dup_factor > 1.1
ORDER BY dup_factor DESC;
```

**Alert threshold:** `dup_factor > 1.0` indicates duplication has returned.

### Verifying Ingestion Health

```sql
SELECT
    max(date) AS last_ingested_date,
    dateDiff('day', max(date), today()) AS days_behind,
    count() AS rows_current_month
FROM cost_facts
WHERE org_id = '{ORG_ID}'
  AND provider = 'azure'
  AND toYYYYMM(date) = toYYYYMM(today());
```

**Alert:** `days_behind > 2` indicates ingestion may be stalled.

### Reconciliation Check

```sql
SELECT
    sum(cost_usd) AS causium_total,
    currency
FROM cost_facts
WHERE org_id = '{ORG_ID}'
  AND subscription_id = '{SUBSCRIPTION_ID}'
  AND provider = 'azure'
  AND toYYYYMM(date) = toYYYYMM(today())
GROUP BY currency;
```

Compare with Azure Portal → Cost Management → Cost Analysis for the same subscription and period.

### Log Signals to Monitor

| Log Key | Meaning |
|---------|---------|
| `ledger.azure_dedup.deleted` | Normal: overlap cleared before insert |
| `ledger.azure_dedup.skipped` | Warning: batch had no subscription_id |
| `ledger.azure_dedup.skipped_sub` | Warning: sub-batch had no dates |
| `ledger.azure_dedup.abort` | Error: DELETE failed, ingest aborted |

---

## Lessons Learned

1. **Azure Cost Exports are cumulative, not incremental.** Any pipeline consuming them must handle overlap. File-level checkpoints are insufficient — data-level idempotency is required.

2. **Field naming matters.** The column `cost_usd` stores BillingCurrency (BRL in this case), not USD. This caused confusion during investigation and will cause confusion for users comparing with USD-denominated tools.

3. **ClickHouse MergeTree does not deduplicate.** Unlike `ReplacingMergeTree`, plain `MergeTree` accumulates all INSERTs. The Python `clickhouse_init.py` creates `MergeTree` while the SQL init script creates `ReplacingMergeTree` — whichever runs first wins. In production, `MergeTree` was active.

4. **Reconciliation tooling is essential.** Without the `/diagnostic/ingest` endpoint and direct ClickHouse access, this issue would have been much harder to diagnose. The `ReconciliationReport` API endpoint (already built) should be surfaced to users.

5. **Delete-before-insert is the standard pattern for cumulative exports.** This is how most data warehouses handle slowly-changing or snapshot-based source data. The pattern is well-understood and production-safe.

---

## Related Commits

| Hash | Description |
|------|-------------|
| `a76d70c` | fix: prevent duplicate azure cost export ingestion |
| `bc7b335` | debug: add detailed blob ingest logs for Azure cost_facts |
| `d26207f` | debug: add /diagnostic/sync-account endpoint |

---

## Open Items (Not Blocking)

| Item | Priority | Description |
|------|----------|-------------|
| Currency conversion | Medium | `cost_usd` stores BRL — needs conversion or field rename |
| Schema alignment | Low | Python init uses MergeTree, SQL init uses ReplacingMergeTree — should converge |
| Amortized vs Actual | Low | Blob CSV fallback chain may pick AmortizedCost if other columns are empty |

---

*Document created: 2026-05-12. Validated with production ClickHouse queries.*
