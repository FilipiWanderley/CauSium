from __future__ import annotations

import hashlib

from app.domains.auth.models import User

ANONYMIZED_FULL_NAME = "Deleted User"
ANONYMIZED_EMAIL_DOMAIN = "deleted.invalid"


def anonymize_user_identity(user: User, *, secret_key: str) -> bool:
    """Apply irreversible identity anonymization to a user row.

    Returns True when at least one field changed.
    """
    changed = False

    if not user.email.endswith(f"@{ANONYMIZED_EMAIL_DOMAIN}"):
        digest = hashlib.sha256(f"{user.email}|{user.id}|{secret_key}".encode("utf-8")).hexdigest()
        user.email = f"deleted_{digest[:40]}@{ANONYMIZED_EMAIL_DOMAIN}"
        changed = True

    if user.full_name != ANONYMIZED_FULL_NAME:
        user.full_name = ANONYMIZED_FULL_NAME
        changed = True

    return changed
