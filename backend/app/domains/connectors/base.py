from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class CanonicalCostRecord:
    date: date
    provider: str
    subscription_id: str
    service: str
    resource_id: str
    resource_name: str
    region: str
    environment: str
    owner_team: str
    cost_usd: float
    usage_quantity: float
    usage_unit: str
    currency: str
    tags: dict[str, str]
    charge_type: str = ""
    pricing_model: str = ""
    benefit_id: str = ""
    benefit_name: str = ""
    frequency: str = ""
    publisher_type: str = ""
    cost_type: str = "actual"


@dataclass
class CanonicalEventRecord:
    timestamp: Any  # datetime
    provider: str
    subscription_id: str
    event_type: str
    resource_id: str
    resource_name: str
    region: str
    severity: str
    description: str
    caller: str
    correlation_id: str
    raw_data: str


@dataclass
class CanonicalCarbonRecord:
    year_month: str  # YYYY-MM
    provider: str
    subscription_id: str
    service: str
    resource_group: str
    kg_co2e: float


@dataclass
class CanonicalRecommendationRecord:
    recommendation_id: str
    provider: str
    subscription_id: str
    category: str           # Cost | Security | Performance | HighAvailability | OperationalExcellence
    impact: str             # High | Medium | Low
    resource_id: str
    resource_name: str
    resource_group: str
    service: str
    short_description: str
    recommendation_type_id: str
    estimated_savings_usd: float | None
    fetched_at: Any         # datetime


@dataclass
class CanonicalResourceRecord:
    resource_id: str
    provider: str
    subscription_id: str
    name: str
    resource_type: str
    resource_group: str
    location: str
    environment: str
    owner_team: str
    sku_name: str
    sku_tier: str
    provisioning_state: str
    tags: dict[str, str]
    fetched_at: Any         # datetime


@dataclass
class CanonicalUsageRecord:
    date: date
    provider: str
    subscription_id: str
    service: str
    resource_id: str
    metric_name: str
    metric_value: float
    metric_unit: str
    region: str
    environment: str


class BaseConnector(ABC):
    @abstractmethod
    async def validate_connection(self) -> None:
        """Raise if connection fails."""

    @abstractmethod
    async def validate_cost_management_scope(self, subscription_id: str) -> None:
        """Raise PermissionError if the SP lacks Cost Management Reader or higher."""

    @abstractmethod
    async def fetch_costs(self, subscription_id: str, start: date, end: date) -> list[CanonicalCostRecord]:
        """Fetch daily cost records for the given date range."""

    @abstractmethod
    async def fetch_events(self, subscription_id: str, start: date, end: date) -> list[CanonicalEventRecord]:
        """Fetch activity log events."""

    @abstractmethod
    async def fetch_carbon_emissions(self, subscription_id: str, start: date, end: date) -> list[CanonicalCarbonRecord]:
        """Fetch monthly carbon emissions for the given period."""
