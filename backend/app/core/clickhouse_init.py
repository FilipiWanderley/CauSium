from __future__ import annotations
from app.core.logging import get_logger

log = get_logger(__name__)

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS cost_facts (
        date Date,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        service String,
        resource_id String,
        resource_name String,
        region String,
        environment String,
        owner_team String,
        cost_usd Float64,
        usage_quantity Float64,
        usage_unit String,
        currency String,
        tags String
    ) ENGINE = MergeTree()
    ORDER BY (org_id, account_id, date, service)
    """,
    """
    CREATE TABLE IF NOT EXISTS event_facts (
        timestamp DateTime,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        event_type String,
        resource_id String,
        resource_name String,
        region String,
        severity String,
        description String,
        caller String,
        correlation_id String,
        raw_data String
    ) ENGINE = MergeTree()
    ORDER BY (org_id, account_id, timestamp, event_type)
    """,
    """
    CREATE TABLE IF NOT EXISTS recommendation_facts (
        date Date,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        resource_id String,
        resource_name String,
        service String,
        short_description String,
        recommendation_type_id String,
        category String,
        impact String,
        resource_type String,
        sku_name String,
        sku_tier String
    ) ENGINE = MergeTree()
    ORDER BY (org_id, account_id, date, category)
    """,
    """
    CREATE TABLE IF NOT EXISTS usage_facts (
        date Date,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        service String,
        resource_id String,
        metric_name String,
        metric_value Float64,
        metric_unit String,
        region String
    ) ENGINE = MergeTree()
    ORDER BY (org_id, account_id, date, metric_name)
    """,
    """
    CREATE TABLE IF NOT EXISTS resource_inventory (
        fetched_at DateTime,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        resource_id String,
        name String,
        resource_type String,
        resource_group String,
        location String,
        environment String,
        owner_team String,
        sku_name String,
        sku_tier String,
        provisioning_state String,
        tags String
    ) ENGINE = ReplacingMergeTree(fetched_at)
    ORDER BY (org_id, account_id, resource_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS carbon_facts (
        year_month String,
        org_id String,
        account_id String,
        provider String,
        subscription_id String,
        service String,
        resource_group String,
        kg_co2e Float64
    ) ENGINE = MergeTree()
    ORDER BY (org_id, account_id, year_month, service)
    """,
]


def ensure_clickhouse_schema() -> None:
    try:
        from app.core.clickhouse import execute_command
        for ddl in TABLES:
            execute_command(ddl.strip())
        log.info("clickhouse.schema.ok")
    except Exception as exc:
        log.warning("clickhouse.schema.failed", error=str(exc))
