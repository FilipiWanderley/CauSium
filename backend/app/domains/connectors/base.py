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


class BaseConnector(ABC):
    @abstractmethod
    async def validate_connection(self) -> None:
        """Raise if connection fails."""

    @abstractmethod
    async def fetch_costs(self, subscription_id: str, start: date, end: date) -> list[CanonicalCostRecord]:
        """Fetch daily cost records for the given date range."""

    @abstractmethod
    async def fetch_events(self, subscription_id: str, start: date, end: date) -> list[CanonicalEventRecord]:
        """Fetch activity log events."""
