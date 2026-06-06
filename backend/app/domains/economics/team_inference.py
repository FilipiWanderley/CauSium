"""
Team inference from Resource Group patterns.

This module provides fallback logic to infer team labels when Azure Cost Management
API does not return team tags. It only applies to records where owner_team = 'untagged'.

Rules:
------
- Only applies when owner_team = 'untagged' or empty
- Does NOT overwrite owner_team values from real tags
- Uses resource_group/resource_name prefix patterns to infer team

Mapping (approved):
-------------------
csc       -> CSC
cqg       -> CQG
engetec   -> Engetec
vital     -> Vital
qgi       -> QGI
qggn      -> QGGN
qgsa      -> QGSA
frontis   -> Frontis
projeto   -> Datalake (for projeto-datalake)

Not classified (no fallback):
-------------------------------
- Empty resource_name
- networkwatcherrg
- azurebackuprg_*
- $system
- defaultresourcegroup
- cloud-shell
- veeam-linux-helper
- causiumcost
"""

from dataclasses import dataclass
from enum import Enum


class TeamClassificationSource(Enum):
    """Source of the team classification."""
    TAG_AZURE = "Tag Azure"
    RESOURCE_GROUP_INFERRED = "Resource Group inferido"
    SEM_EQUIPE_IDENTIFICADA = "Sem equipe identificada"


# Mapping of prefixes to team labels
_TEAM_PREFIX_MAP = {
    "csc": "CSC",
    "cqg": "CQG",
    "engetec": "Engetec",
    "vital": "Vital",
    "qgi": "QGI",
    "qggn": "QGGN",
    "qgsa": "QGSA",
    "frontis": "Frontis",
    "projeto": "Datalake",  # Special case for projeto-datalake
}

# Prefixes that should NOT be classified (Azure system or generic)
_EXCLUDED_PREFIXES = {
    "networkwatcherrg",
    "azurebackuprg",
    "$system",
    "defaultresourcegroup",
    "cloud",
    "veeam-linux-helper",
    "causiumcost",
}


@dataclass
class TeamInferenceResult:
    """Result of team inference from resource name."""
    team_label: str
    source: TeamClassificationSource
    original_owner_team: str
    resource_name: str


def infer_team_from_resource(
    resource_name: str,
    owner_team: str,
) -> TeamInferenceResult:
    """
    Infer team label from resource_group/resource_name pattern.

    Rules:
    - If owner_team is NOT 'untagged' or empty, preserve original value
    - Only apply fallback when owner_team = 'untagged' or empty
    - Use resource_name prefix to infer team label

    Args:
        resource_name: The resource_group or resource_name from Azure
        owner_team: The owner_team value from the database (may be 'untagged')

    Returns:
        TeamInferenceResult with team_label and classification source
    """
    # Preserve original if it's a real tag (not 'untagged' or empty)
    if owner_team and owner_team.lower() not in ("", "untagged"):
        return TeamInferenceResult(
            team_label=owner_team,
            source=TeamClassificationSource.TAG_AZURE,
            original_owner_team=owner_team,
            resource_name=resource_name or "",
        )

    # Empty resource_name -> no inference possible
    if not resource_name or not resource_name.strip():
        return TeamInferenceResult(
            team_label="Sem equipe identificada",
            source=TeamClassificationSource.SEM_EQUIPE_IDENTIFICADA,
            original_owner_team=owner_team or "",
            resource_name="",
        )

    # Extract prefix (first segment of resource_group name)
    resource_name_clean = resource_name.strip().lower()

    # Check for excluded prefixes first
    for excluded in _EXCLUDED_PREFIXES:
        if resource_name_clean.startswith(excluded):
            return TeamInferenceResult(
                team_label="Sem equipe identificada",
                source=TeamClassificationSource.SEM_EQUIPE_IDENTIFICADA,
                original_owner_team=owner_team or "",
                resource_name=resource_name,
            )

    # Get first prefix (segment before first '-')
    parts = resource_name_clean.split("-")
    if not parts:
        return TeamInferenceResult(
            team_label="Sem equipe identificada",
            source=TeamClassificationSource.SEM_EQUIPE_IDENTIFICADA,
            original_owner_team=owner_team or "",
            resource_name=resource_name,
        )

    prefix = parts[0]

    # Check for matching prefix in map
    if prefix in _TEAM_PREFIX_MAP:
        inferred_label = _TEAM_PREFIX_MAP[prefix]
        return TeamInferenceResult(
            team_label=inferred_label,
            source=TeamClassificationSource.RESOURCE_GROUP_INFERRED,
            original_owner_team=owner_team or "",
            resource_name=resource_name,
        )

    # No pattern match -> keep as "Sem equipe identificada"
    return TeamInferenceResult(
        team_label="Sem equipe identificada",
        source=TeamClassificationSource.SEM_EQUIPE_IDENTIFICADA,
        original_owner_team=owner_team or "",
        resource_name=resource_name,
    )


def format_team_label(owner_team: str) -> str:
    """
    Format owner_team for display with fallback inference.

    This is a convenience function that returns only the team label
    without the source classification.

    Args:
        owner_team: The owner_team value from database

    Returns:
        Formatted team label string
    """
    if not owner_team or owner_team.lower() in ("", "untagged"):
        return "Sem equipe identificada"
    return owner_team


def format_team_label_with_resource(owner_team: str, resource_name: str) -> str:
    """
    Format owner_team for display with fallback from resource_name.

    Args:
        owner_team: The owner_team value from database
        resource_name: The resource_group/resource_name for inference

    Returns:
        Formatted team label string
    """
    result = infer_team_from_resource(resource_name, owner_team)
    return result.team_label