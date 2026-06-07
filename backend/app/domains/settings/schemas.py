from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

# Allowed tag keys: alphanumeric, underscore, hyphen, max 64 chars
TAG_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Predefined tag options
TAG_OPTIONS = [
    "team",
    "owner",
    "squad",
    "application",
    "business_unit",
    "costcenter",
    "product",
    "project",
]


class FinOpsSettingsOut(BaseModel):
    monitored_tag_key: Annotated[str, Field(description="Tag key used for compliance visibility")]

    model_config = {"from_attributes": True}


class FinOpsSettingsUpdate(BaseModel):
    monitored_tag_key: Annotated[str, Field(min_length=1, max_length=64)]

    @field_validator("monitored_tag_key")
    @classmethod
    def validate_tag_key(cls, v: str) -> str:
        v = v.strip()
        if not TAG_KEY_PATTERN.match(v):
            raise ValueError(
                "Must be 1-64 chars: letters, numbers, underscore, or hyphen. "
                f"Got: {v!r}"
            )
        return v

    model_config = {"from_attributes": True}


class FinOpsSettingsPatch(BaseModel):
    """Partial update — only include fields to change."""

    monitored_tag_key: str | None = None

    @field_validator("monitored_tag_key")
    @classmethod
    def validate_tag_key(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not TAG_KEY_PATTERN.match(v):
            raise ValueError(
                "Must be 1-64 chars: letters, numbers, underscore, or hyphen. "
                f"Got: {v!r}"
            )
        return v