from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScopeValidationResult:
    """Normalized response for provider-specific scope validation."""

    ok: bool
    validated_scopes: list[str]
    message: str
