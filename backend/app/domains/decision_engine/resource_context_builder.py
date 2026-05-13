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
# Example: /subscriptions/abc-123/resourceGroups/rg-platform/providers/Microsoft.Compute/virtualMachines/vm-01
_ARM_PATTERN = re.compile(
    r"^/subscriptions/(?P<sub>[^/]+)"
    r"/resourceGroups/(?P<rg>[^/]+)"
    r"/providers/(?P<type>[^/]+/[^/]+)"
    r"/(?P<name>.+)$",
    re.IGNORECASE,
)

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
    """
    from app.domains.decision_engine.schemas import ResourceContext

    resource_id = (opportunity.resource_id or "").strip()
    data_sources: list[str] = []

    # Try provider-specific parsing
    parsed = _try_parse_arm(resource_id)
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
    resource_name = parsed.get("resource_name") or model_fields.get("resource_name")
    sku = model_fields.get("sku")
    sku_tier = model_fields.get("sku_tier")
    region = parsed.get("region") or model_fields.get("region")
    environment = model_fields.get("environment")
    owner = model_fields.get("owner")
    workload = parsed.get("workload") or model_fields.get("workload")
    tags_summary = _extract_tags(opportunity)

    # Determine granularity tier
    granularity_tier = _determine_tier(
        resource_id=resource_id,
        resource_type=resource_type,
        resource_name=resource_name,
        service=opportunity.service,
        region=region,
        subscription_id=subscription_id,
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
    )


# ── Parsers ────────────────────────────────────────────────────────────────────


def _try_parse_arm(resource_id: str) -> dict | None:
    """Parse Azure ARM resource ID."""
    match = _ARM_PATTERN.match(resource_id)
    if not match:
        return None
    return {
        "provider": "azure",
        "subscription_id": match.group("sub"),
        "resource_group": match.group("rg"),
        "resource_type": match.group("type"),
        "resource_name": match.group("name"),
    }


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

    # Owner
    owner = (opportunity.owner_team or "").strip().lower()
    if owner and owner not in _EMPTY_OWNER_VALUES:
        result["owner"] = opportunity.owner_team.strip()

    # SKU
    sku = (opportunity.sku_name or "").strip()
    if sku:
        result["sku"] = sku

    # Resource name
    rname = (opportunity.resource_name or "").strip()
    if rname:
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
) -> str:
    """Determine the granularity tier based on available context."""
    # Resource tier: we have a specific, identifiable resource
    if resource_type and resource_name:
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
