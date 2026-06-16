"""
Resource Context Builder — deterministic resource granularity layer.

Parses opportunity resource_id (Azure ARM, AWS ARN, GCP paths, AKS composite)
and model fields into a normalized ResourceContext payload.

Design principles:
- Pure function, no DB access, no side effects
- Never invent data — null when unknown
- Provider-aware parsing with graceful fallback
- Transparent data_sources tracking
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.decision_engine.models import OptimizationOpportunity
    from app.domains.decision_engine.schemas import ResourceContext


# ── Azure ARM resource ID regex ────────────────────────────────────────────────
# Supports:
# - Full resource: /subscriptions/{sub}/resourceGroups/{rg}/providers/{type}/{name}
# - Child resources: /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type1}/{name1}/{type2}/{name2}
# - Subscription-only: /subscriptions/{sub}


def is_subscription_level_resource_id(resource_id: str | None) -> bool:
    """
    Check if resource_id is subscription-only (no resourceGroups).

    Azure Savings Plans and Reserved Instances are scoped to subscriptions,
    not individual resources, so their resource_id is just /subscriptions/{id}.
    """
    if not resource_id:
        return False
    rid_lower = resource_id.lower()
    return (
        rid_lower.startswith("/subscriptions/")
        and "resourcegroups" not in rid_lower
    )


def build_portal_url(resource_id: str | None) -> str | None:
    """
    Build Azure Portal URL for a resource.

    Handles both resource-level and subscription-level IDs.

    Args:
        resource_id: Azure ARM resource ID

    Returns:
        Azure Portal URL or None if not a valid Azure resource ID
    """
    if not resource_id:
        return None

    rid_lower = resource_id.lower()

    # Subscription-level URL (e.g., /subscriptions/{id} for Savings Plans)
    if rid_lower.startswith("/subscriptions/") and "resourcegroups" not in rid_lower:
        return f"https://portal.azure.com/#resource{resource_id}"

    # Resource-level URL (requires /subscriptions/ AND resourceGroups AND providers)
    if not rid_lower.startswith("/subscriptions/"):
        return None

    has_resource_groups = "resourcegroups" in rid_lower
    has_providers = "providers" in rid_lower

    if not (has_resource_groups and has_providers):
        return None

    return f"https://portal.azure.com/#resource{resource_id}"


def parse_arm_resource_id(resource_id: str | None) -> dict | None:
    """
    Parse Azure ARM resource ID into components.

    Supports:
    - Full resource: /subscriptions/{sub}/resourceGroups/{rg}/providers/{type}/{name}
    - Child resources: /subscriptions/{sub}/resourceGroups/{rg}/providers/{ns}/{type1}/{name1}/{type2}/{name2}
    - Subscription-only: /subscriptions/{sub}

    Args:
        resource_id: Azure ARM resource ID

    Returns:
        Dict with subscription_id, resource_group, resource_type, resource_name
        or None if parsing fails
    """
    if not resource_id:
        return None

    # Normalize to lowercase for case-insensitive key matching
    rid_lower = resource_id.lower()
    parts = resource_id.split("/")

    # Must start with /subscriptions/
    if len(parts) < 2 or parts[1].lower() != "subscriptions":
        return None

    subscription_id = parts[2]

    # Check if this is subscription-only (no resourceGroups means subscription-level)
    has_resource_groups = "resourcegroups" in rid_lower

    if not has_resource_groups:
        # Subscription-only ID
        return {
            "provider": "azure",
            "subscription_id": subscription_id,
            "resource_group": None,
            "resource_type": None,
            "resource_name": None,
        }

    # Find indices (case-insensitive)
    resource_groups_idx = None
    providers_idx = None

    for i, part in enumerate(parts):
        if part.lower() == "resourcegroups":
            resource_groups_idx = i
        elif part.lower() == "providers":
            providers_idx = i

    if resource_groups_idx is None or providers_idx is None:
        return {
            "provider": "azure",
            "subscription_id": subscription_id,
            "resource_group": None,
            "resource_type": None,
            "resource_name": None,
        }

    # Extract resource_group (preserve original case)
    resource_group = parts[resource_groups_idx + 1] if len(parts) > resource_groups_idx + 1 else None

    # Extract resource_type and resource_name from segments after providers
    # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{namespace}/{type1}/{name1}/{type2}/{name2}/...
    # Last segment is always resource_name
    # Everything between providers and last segment forms the resource_type

    after_providers = parts[providers_idx + 1:]

    if len(after_providers) == 0:
        return {
            "provider": "azure",
            "subscription_id": subscription_id,
            "resource_group": resource_group,
            "resource_type": None,
            "resource_name": None,
        }

    # Last segment is resource_name
    resource_name = after_providers[-1]

    # Build resource_type from namespace and type segments
    # After_providers format: [namespace, type1, name1, type2, name2, ...]
    # Types are at even indices (1, 3, 5, ...)
    # Names are at odd indices (2, 4, 6, ...)
    if len(after_providers) >= 2:
        namespace = after_providers[0]
        type_segments = []
        # Start from index 1, step by 2 to get types only
        for i in range(1, len(after_providers) - 1, 2):
            if i < len(after_providers) - 1:
                type_segments.append(after_providers[i])
        if type_segments:
            resource_type = f"{namespace}/{'/'.join(type_segments)}"
        else:
            resource_type = namespace
    else:
        resource_type = after_providers[0]

    return {
        "provider": "azure",
        "subscription_id": subscription_id,
        "resource_group": resource_group,
        "resource_type": resource_type,
        "resource_name": resource_name,
    }


# AKS composite resource_id: aks:{cluster_arm_path}:{node_pool_name}
_AKS_COMPOSITE_PATTERN = re.compile(
    r"^aks:(?P<cluster_path>.+):(?P<pool>[^:]+)$",
    re.IGNORECASE,
)

# AWS ARN pattern: arn:aws:{service}:{region}:{account}:{resource_type}/{resource_name}
_ARN_PATTERN = re.compile(
    r"^arn:aws:(?P<service>[^:]+):(?P<region>[^:]*):(?P<account>[^:]+):(?P<resource>.+)$",
    re.IGNORECASE,
)

# GCP resource path: projects/{project}/zones/{zone}/{type}/{name}
_GCP_PATTERN = re.compile(
    r"^projects/(?P<project>[^/]+)/"
    r"(?:zones|regions)/(?P<location>[^/]+)/"
    r"(?P<type>[^/]+)/(?P<name>[^/]+)$",
    re.IGNORECASE,
)

# Values that indicate "no owner" — treat as null
_EMPTY_OWNER_VALUES = frozenset({"", "untagged", "unknown", "none", "n/a"})


def build_resource_context(opportunity: "OptimizationOpportunity") -> "ResourceContext":
    """
    Build a normalized ResourceContext from an opportunity's existing fields.

    Always returns a ResourceContext (never None) — worst case is
    granularity_tier="unknown" with nulls.

    For subscription-level recommendations (Savings Plans, Reserved Instances),
    resource_id is just /subscriptions/{id} and we provide appropriate defaults.
    """
    from app.domains.decision_engine.schemas import ResourceContext

    resource_id = (opportunity.resource_id or "").strip()
    data_sources: list[str] = []

    # Detect subscription-level recommendations
    is_subscription_level = is_subscription_level_resource_id(resource_id)

    # Try provider-specific parsing
    parsed = parse_arm_resource_id(resource_id)
    if parsed:
        data_sources.append("resource_id_arm_parse")
    else:
        parsed = _try_parse_aks_composite(resource_id)
        if parsed:
            data_sources.append("resource_id_aks_composite_parse")
        else:
            parsed = _try_parse_arn(resource_id)
            if parsed:
                data_sources.append("resource_id_arn_parse")
            else:
                parsed = _try_parse_gcp(resource_id)
                if parsed:
                    data_sources.append("resource_id_gcp_parse")

    if not parsed:
        parsed = {}

    # Enrich from model fields (fallback / supplement)
    model_fields = _extract_model_fields(opportunity)
    if model_fields:
        data_sources.append("model_fields")

    # Merge: parsed takes priority, model_fields fills gaps
    provider = parsed.get("provider") or model_fields.get("provider")
    subscription_id = parsed.get("subscription_id") or model_fields.get("subscription_id")
    resource_group = parsed.get("resource_group")
    resource_type = parsed.get("resource_type")
    resource_name = parsed.get("resource_name")

    # For subscription-level recommendations, provide sensible defaults
    if is_subscription_level:
        if not resource_type:
            resource_type = "Azure Subscription"
        # Check if opportunity has a valid resource_name
        existing_name = (opportunity.resource_name or "").strip()
        if existing_name and existing_name not in _EMPTY_OWNER_VALUES:
            resource_name = existing_name
        elif not resource_name:
            # Use short subscription ID as resource name
            sub_short = subscription_id[:8] if subscription_id else "unknown"
            resource_name = f"Subscription {sub_short}"
        # resource_group stays null for subscription-level

    # Priority for resource_name (non-subscription):
    # 1. Existing resource_name from model (if valid)
    # 2. Parsed from ARM resource_id
    # 3. None (avoid showing subscription_id as resource name)
    else:
        existing_name = (opportunity.resource_name or "").strip()
        if existing_name and existing_name not in _EMPTY_OWNER_VALUES:
            # Only use if it's not a subscription_id
            if existing_name != subscription_id:
                resource_name = existing_name
            # else: keep parsed resource_name or None
        # If parsed has a valid resource_name, it's already set above

    sku = model_fields.get("sku")
    sku_tier = model_fields.get("sku_tier")
    region = parsed.get("region") or model_fields.get("region")
    environment = model_fields.get("environment")
    owner = model_fields.get("owner")  # Will be None if no inventory
    workload = parsed.get("workload") or model_fields.get("workload")
    tags_summary = _extract_tags(opportunity)  # Will be None if no inventory

    # Generate portal URL (handles both resource and subscription level)
    portal_url = build_portal_url(resource_id)

    # Determine granularity tier
    granularity_tier = _determine_tier(
        resource_id=resource_id,
        resource_type=resource_type,
        resource_name=resource_name,
        service=opportunity.service,
        region=region,
        subscription_id=subscription_id,
        is_subscription_level=is_subscription_level,
    )

    return ResourceContext(
        provider=provider,
        subscription_id=subscription_id,
        subscription_name=None,  # Not available without lookup
        resource_group=resource_group,
        resource_type=resource_type,
        resource_name=resource_name,
        sku=sku,
        sku_tier=sku_tier,
        region=region,
        environment=environment,
        owner=owner,
        workload=workload,
        tags_summary=tags_summary if tags_summary else None,
        granularity_tier=granularity_tier,
        data_sources=data_sources if data_sources else ["none"],
        portal_url=portal_url,
    )


# ── Parsers ────────────────────────────────────────────────────────────────────


def _try_parse_aks_composite(resource_id: str) -> dict | None:
    """Parse AKS composite format: aks:{cluster_arm_path}:{pool_name}."""
    match = _AKS_COMPOSITE_PATTERN.match(resource_id)
    if not match:
        return None

    cluster_path = match.group("cluster_path")
    pool_name = match.group("pool")

    # Try to parse the inner cluster ARM path
    result: dict = {
        "provider": "azure",
        "resource_type": "Microsoft.ContainerService/managedClusters",
        "resource_name": f"{_extract_cluster_name(cluster_path)}/{pool_name}",
        "workload": f"aks-nodepool:{pool_name}",
    }

    # Extract subscription and resource group from cluster path
    arm_match = re.match(
        r"(?i)/subscriptions/(?P<sub>[^/]+)/resourceGroups/(?P<rg>[^/]+)",
        cluster_path,
    )
    if arm_match:
        result["subscription_id"] = arm_match.group("sub")
        result["resource_group"] = arm_match.group("rg")

    return result


def _try_parse_arn(resource_id: str) -> dict | None:
    """Parse AWS ARN."""
    match = _ARN_PATTERN.match(resource_id)
    if not match:
        return None

    resource_part = match.group("resource")
    # resource can be "type/name" or "type:name"
    if "/" in resource_part:
        rtype, rname = resource_part.split("/", 1)
    elif ":" in resource_part:
        rtype, rname = resource_part.split(":", 1)
    else:
        rtype = resource_part
        rname = None

    return {
        "provider": "aws",
        "subscription_id": match.group("account"),  # AWS account ID
        "region": match.group("region") or None,
        "resource_type": f"{match.group('service')}/{rtype}",
        "resource_name": rname,
    }


def _try_parse_gcp(resource_id: str) -> dict | None:
    """Parse GCP resource path."""
    match = _GCP_PATTERN.match(resource_id)
    if not match:
        return None
    return {
        "provider": "gcp",
        "subscription_id": match.group("project"),  # GCP project
        "region": match.group("location"),
        "resource_type": match.group("type"),
        "resource_name": match.group("name"),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────


def _extract_cluster_name(cluster_path: str) -> str:
    """Extract cluster name from ARM path or raw string."""
    # Try to find managedClusters/{name}
    match = re.search(r"(?i)/managedClusters/([^/]+)", cluster_path)
    if match:
        return match.group(1)
    # Fallback: last segment
    parts = cluster_path.strip("/").split("/")
    return parts[-1] if parts else "unknown"


def _extract_model_fields(opportunity: "OptimizationOpportunity") -> dict:
    """Extract normalized context from opportunity model fields."""
    result: dict = {}

    # Region
    region = (opportunity.region or "").strip()
    if region:
        result["region"] = region

    # Environment
    env = (opportunity.environment or "").strip().lower()
    if env and env not in ("unknown", ""):
        result["environment"] = env

    # Owner - only if valid (not empty, not untagged, etc.)
    owner = (opportunity.owner_team or "").strip().lower()
    if owner and owner not in _EMPTY_OWNER_VALUES:
        result["owner"] = opportunity.owner_team.strip()

    # SKU
    sku = (opportunity.sku_name or "").strip()
    if sku:
        result["sku"] = sku

    # Resource name - keep original, let caller decide priority
    rname = (opportunity.resource_name or "").strip()
    if rname and rname not in _EMPTY_OWNER_VALUES:
        result["resource_name"] = rname

    # Service → workload hint
    service = (opportunity.service or "").strip()
    if service:
        result["workload"] = service

    # Infer provider from service name or decision_evidence
    provider = _infer_provider(opportunity)
    if provider:
        result["provider"] = provider

    return result


def _infer_provider(opportunity: "OptimizationOpportunity") -> str | None:
    """Infer cloud provider from available context."""
    resource_id = (opportunity.resource_id or "").lower()
    service = (opportunity.service or "").lower()

    # Azure indicators
    if resource_id.startswith("/subscriptions/") or resource_id.startswith("aks:"):
        return "azure"
    if any(k in service for k in ("azure", "microsoft", "aks")):
        return "azure"

    # AWS indicators
    if resource_id.startswith("arn:aws:"):
        return "aws"
    if any(k in service for k in ("aws", "amazon", "ec2", "s3", "rds")):
        return "aws"

    # GCP indicators
    if resource_id.startswith("projects/"):
        return "gcp"
    if any(k in service for k in ("gcp", "google", "gke", "bigquery")):
        return "gcp"

    return None


def _extract_tags(opportunity: "OptimizationOpportunity") -> dict[str, str] | None:
    """Extract tags from decision_evidence if available."""
    evidence = opportunity.decision_evidence or {}

    # Some evidence payloads include tags
    tags = evidence.get("tags")
    if isinstance(tags, dict) and tags:
        # Limit to first 10 tags for summary
        return dict(list(tags.items())[:10])

    # Build minimal tags from known fields
    synthetic: dict[str, str] = {}
    env = (opportunity.environment or "").strip()
    if env and env.lower() not in ("unknown", ""):
        synthetic["environment"] = env
    owner = (opportunity.owner_team or "").strip()
    if owner and owner.lower() not in _EMPTY_OWNER_VALUES:
        synthetic["owner_team"] = owner

    return synthetic if synthetic else None


def _determine_tier(
    *,
    resource_id: str,
    resource_type: str | None,
    resource_name: str | None,
    service: str | None,
    region: str | None,
    subscription_id: str | None,
    is_subscription_level: bool = False,
) -> str:
    """Determine the granularity tier based on available context."""
    # Subscription-level recommendations (Savings Plans, Reserved Instances)
    if is_subscription_level:
        return "subscription"

    # Resource tier: we have a specific, identifiable resource
    if resource_type and resource_name:
        return "resource"

    # If we have resource_id but no resource_type/resource_name, check if it's subscription-only
    # or if it's a resource-level ID that couldn't be parsed
    if resource_id and resource_type is None and resource_name is None:
        # Subscription-only level (e.g., /subscriptions/{id} for Savings Plans)
        if subscription_id and resource_id == f"/subscriptions/{subscription_id}":
            return "subscription"
        # Otherwise it's an unparseable resource_id
        return "resource"

    if resource_id and len(resource_id) > 10:
        # Has a meaningful resource_id even if not fully parsed
        return "resource"

    # Service tier: we know the service and region
    if service and region:
        return "service"

    # Subscription tier: only subscription-level
    if subscription_id:
        return "subscription"

    return "unknown"
