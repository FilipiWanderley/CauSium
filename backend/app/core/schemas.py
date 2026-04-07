from __future__ import annotations

from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """FastAPI dependency for page-based pagination query params."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
        page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    ) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page(BaseModel, Generic[T]):
    """Standardised paginated response envelope used across all list endpoints."""

    items: list[T]
    page: int
    page_size: int
    total: int
    has_next: bool

    @classmethod
    def of(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        return cls(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
            has_next=(params.offset + len(items)) < total,
        )
