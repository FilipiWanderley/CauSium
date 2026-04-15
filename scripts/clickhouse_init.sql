-- CauSium ClickHouse schema
-- Analytical tables for Cloud Ledger

CREATE TABLE IF NOT EXISTS cost_facts (
    date           Date,
    org_id         UUID,
    account_id     UUID,
    provider       LowCardinality(String),
    subscription_id String,
    service        LowCardinality(String),
    resource_id    String,
    resource_name  String,
    region         LowCardinality(String),
    environment    LowCardinality(String),
    owner_team     LowCardinality(String),
    cost_usd       Float64,
    usage_quantity Float64,
    usage_unit     LowCardinality(String),
    currency       LowCardinality(String) DEFAULT 'USD',
    tags           Map(String, String),
    ingested_at    DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(date)
ORDER BY (org_id, account_id, provider, service, resource_id, date)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS event_facts (
    timestamp      DateTime,
    org_id         UUID,
    account_id     UUID,
    provider       LowCardinality(String),
    subscription_id String,
    event_type     LowCardinality(String),
    resource_id    String,
    resource_name  String,
    region         LowCardinality(String),
    severity       LowCardinality(String),
    description    String,
    caller         String,
    correlation_id String,
    raw_data       String,
    ingested_at    DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (org_id, account_id, timestamp, event_type)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS usage_facts (
    date           Date,
    org_id         UUID,
    account_id     UUID,
    provider       LowCardinality(String),
    subscription_id String,
    service        LowCardinality(String),
    resource_id    String,
    metric_name    LowCardinality(String),
    metric_value   Float64,
    metric_unit    LowCardinality(String),
    region         LowCardinality(String),
    environment    LowCardinality(String),
    ingested_at    DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(date)
ORDER BY (org_id, account_id, provider, service, resource_id, metric_name, date)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS recommendation_facts (
    fetched_at             DateTime,
    org_id                 UUID,
    account_id             UUID,
    provider               LowCardinality(String),
    subscription_id        String,
    recommendation_id      String,
    category               LowCardinality(String),
    impact                 LowCardinality(String),
    resource_id            String,
    resource_name          String,
    resource_group         String,
    service                LowCardinality(String),
    short_description      String,
    recommendation_type_id String,
    estimated_savings_usd  Nullable(Float64),
    ingested_at            DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(fetched_at)
ORDER BY (org_id, account_id, subscription_id, recommendation_id, fetched_at)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS resource_inventory (
    fetched_at         DateTime,
    org_id             UUID,
    account_id         UUID,
    provider           LowCardinality(String),
    subscription_id    String,
    resource_id        String,
    name               String,
    resource_type      LowCardinality(String),
    resource_group     String,
    location           LowCardinality(String),
    environment        LowCardinality(String),
    owner_team         LowCardinality(String),
    sku_name           LowCardinality(String),
    sku_tier           LowCardinality(String),
    provisioning_state LowCardinality(String),
    tags               Map(String, String),
    ingested_at        DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(fetched_at)
ORDER BY (org_id, account_id, subscription_id, resource_id, fetched_at)
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS carbon_facts (
    year_month     String,
    org_id         UUID,
    account_id     UUID,
    provider       LowCardinality(String),
    subscription_id String,
    service        LowCardinality(String),
    resource_group String,
    kg_co2e        Float64,
    ingested_at    DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY year_month
ORDER BY (org_id, account_id, provider, subscription_id, service, resource_group, year_month)
SETTINGS index_granularity = 8192;
