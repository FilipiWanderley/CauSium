from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Iterable


@dataclass(frozen=True)
class VmRightsizingDecision:
    recommend: bool
    reason: str
    risk_level: str
    confidence: float
    evidence: dict[str, float | int | str | None]


def _metric_kind(metric_name: str) -> str | None:
    name = (metric_name or "").strip().lower()
    if not name:
        return None
    if "cpu" in name:
        return "cpu"
    if "memory" in name or "mem" in name:
        return "memory"
    return None


def _parse_azure_like_sku(sku_name: str) -> tuple[str, str, int, str, str] | None:
    """
    Parse SKU like Standard_D4s_v5.
    Returns tuple: (prefix, family, size, flavor, version_suffix).
    """
    raw = (sku_name or "").strip()
    if not raw:
        return None

    match = re.match(
        r"^(?P<prefix>Standard[_-])(?P<family>[A-Za-z]+)(?P<size>\d+)(?P<flavor>[A-Za-z0-9]*?)_(?P<version>v\d+)$",
        raw,
    )
    if not match:
        return None

    return (
        match.group("prefix"),
        match.group("family"),
        int(match.group("size")),
        match.group("flavor"),
        match.group("version"),
    )


def _smaller_compatible_sku(current_sku: str) -> str | None:
    parsed = _parse_azure_like_sku(current_sku)
    if not parsed:
        return None
    prefix, family, size, flavor, version = parsed
    if size <= 1:
        return None
    target_size = max(1, size // 2)
    if target_size == size:
        return None
    return f"{prefix}{family}{target_size}{flavor}_{version}"


def _size_ratio(current_sku: str, target_sku: str) -> float | None:
    cur = _parse_azure_like_sku(current_sku)
    tgt = _parse_azure_like_sku(target_sku)
    if not cur or not tgt:
        return None
    _, cur_family, cur_size, cur_flavor, cur_ver = cur
    _, tgt_family, tgt_size, tgt_flavor, tgt_ver = tgt
    if cur_family != tgt_family or cur_flavor != tgt_flavor or cur_ver != tgt_ver:
        return None
    if cur_size <= 0:
        return None
    return float(tgt_size) / float(cur_size)


def _compute_window_p95(
    *,
    observations: Iterable[dict],
    now_utc: datetime,
    window_days: int,
) -> tuple[float | None, float | None, int]:
    start = now_utc - timedelta(days=window_days)
    cpu_values: list[float] = []
    mem_values: list[float] = []
    distinct_dates: set[str] = set()

    for item in observations:
        window_start = item.get("window_start")
        if not isinstance(window_start, datetime):
            continue
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)
        if window_start < start:
            continue

        metric_kind = _metric_kind(str(item.get("metric_name") or ""))
        if metric_kind is None:
            continue

        p95 = item.get("p95_value")
        if p95 is None:
            continue
        try:
            p95_f = float(p95)
        except Exception:
            continue

        distinct_dates.add(window_start.date().isoformat())
        if metric_kind == "cpu":
            cpu_values.append(p95_f)
        elif metric_kind == "memory":
            mem_values.append(p95_f)

    cpu_p95 = max(cpu_values) if cpu_values else None
    mem_p95 = max(mem_values) if mem_values else None
    return cpu_p95, mem_p95, len(distinct_dates)


def decide_vm_rightsizing(
    *,
    current_sku: str | None,
    current_monthly_cost: float,
    observations: Iterable[dict],
) -> VmRightsizingDecision:
    now_utc = datetime.now(timezone.utc)
    windows = [30, 14, 7]
    all_window_stats: dict[int, tuple[float | None, float | None, int]] = {}
    for w in windows:
        all_window_stats[w] = _compute_window_p95(
            observations=observations,
            now_utc=now_utc,
            window_days=w,
        )

    selected_days: int | None = None
    cpu_p95: float | None = None
    mem_p95: float | None = None
    history_days: int = 0
    for w in windows:
        w_cpu, w_mem, w_history = all_window_stats[w]
        # Prefer 30 -> 14 -> 7 only when that full window is actually available.
        if w_history >= w and w_cpu is not None and w_mem is not None:
            selected_days = w
            cpu_p95 = w_cpu
            mem_p95 = w_mem
            history_days = w_history
            break
    if selected_days is None:
        # Partial fallback: still allow 7-day decision if at least 7 valid daily points exist.
        for w in windows:
            w_cpu, w_mem, w_history = all_window_stats[w]
            if w_history >= 7 and w_cpu is not None and w_mem is not None:
                selected_days = min(w, w_history)
                cpu_p95 = w_cpu
                mem_p95 = w_mem
                history_days = w_history
                break

    if selected_days is None:
        evidence = {
            "cpu_p95": cpu_p95,
            "memory_p95": mem_p95,
            "window_days": 0,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": None,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": None,
            "estimated_savings": 0.0,
            "estimated_savings_pct": 0.0,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "Dados insuficientes: histórico mínimo de 7 dias com CPU e memória p95.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="Dados insuficientes: histórico mínimo de 7 dias com CPU e memória p95.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    target_sku = _smaller_compatible_sku(current_sku or "")
    if not target_sku:
        evidence = {
            "cpu_p95": round(float(cpu_p95 or 0.0), 2),
            "memory_p95": round(float(mem_p95 or 0.0), 2),
            "window_days": selected_days,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": None,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": None,
            "estimated_savings": 0.0,
            "estimated_savings_pct": 0.0,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "SKU alvo não encontrado: sem SKU menor compatível para esta família.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="SKU alvo não encontrado: sem SKU menor compatível para esta família.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if cpu_p95 > 60.0:
        evidence = {
            "cpu_p95": round(float(cpu_p95), 2),
            "memory_p95": round(float(mem_p95 or 0.0), 2),
            "window_days": selected_days,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": target_sku,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": None,
            "estimated_savings": 0.0,
            "estimated_savings_pct": 0.0,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "Bloqueado por segurança: CPU p95 acima de 60%.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="Bloqueado por segurança: CPU p95 acima de 60%.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    if mem_p95 > 70.0:
        evidence = {
            "cpu_p95": round(float(cpu_p95 or 0.0), 2),
            "memory_p95": round(float(mem_p95), 2),
            "window_days": selected_days,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": target_sku,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": None,
            "estimated_savings": 0.0,
            "estimated_savings_pct": 0.0,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "Bloqueado por segurança: memória p95 acima de 70%.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="Bloqueado por segurança: memória p95 acima de 70%.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    ratio = _size_ratio(current_sku or "", target_sku)
    if ratio is None:
        evidence = {
            "cpu_p95": round(float(cpu_p95 or 0.0), 2),
            "memory_p95": round(float(mem_p95 or 0.0), 2),
            "window_days": selected_days,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": target_sku,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": None,
            "estimated_savings": 0.0,
            "estimated_savings_pct": 0.0,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "Não foi possível estimar custo do SKU alvo.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="Não foi possível estimar custo do SKU alvo.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    estimated_monthly_cost = round(float(current_monthly_cost) * ratio, 2)
    estimated_savings = round(float(current_monthly_cost) - estimated_monthly_cost, 2)
    estimated_savings_pct = round(
        (estimated_savings / float(current_monthly_cost) * 100.0) if current_monthly_cost > 0 else 0.0,
        2,
    )
    if estimated_savings <= 0:
        evidence = {
            "cpu_p95": round(float(cpu_p95 or 0.0), 2),
            "memory_p95": round(float(mem_p95 or 0.0), 2),
            "window_days": selected_days,
            "history_days": history_days,
            "current_sku": current_sku,
            "recommended_sku": target_sku,
            "current_monthly_cost": round(float(current_monthly_cost), 2),
            "estimated_monthly_cost": estimated_monthly_cost,
            "estimated_savings": estimated_savings,
            "estimated_savings_pct": estimated_savings_pct,
            "confidence": 0.0,
            "risk_level": "high",
            "reason": "Economia estimada não positiva.",
        }
        return VmRightsizingDecision(
            recommend=False,
            reason="Economia estimada não positiva.",
            risk_level="high",
            confidence=0.0,
            evidence=evidence,
        )

    risk_level = "low"
    if cpu_p95 > 50.0 or mem_p95 > 60.0:
        risk_level = "medium"

    confidence = 0.55
    if selected_days >= 30:
        confidence += 0.2
    elif selected_days >= 14:
        confidence += 0.12
    if cpu_p95 <= 35.0 and mem_p95 <= 50.0:
        confidence += 0.1
    if risk_level == "medium":
        confidence -= 0.08
    confidence = max(0.0, min(1.0, confidence))
    confidence = math.floor(confidence * 100) / 100.0

    evidence = {
        "cpu_p95": round(float(cpu_p95), 2),
        "memory_p95": round(float(mem_p95), 2),
        "window_days": selected_days,
        "history_days": history_days,
        "current_sku": current_sku,
        "recommended_sku": target_sku,
        "current_monthly_cost": round(float(current_monthly_cost), 2),
        "estimated_monthly_cost": estimated_monthly_cost,
        "estimated_savings": estimated_savings,
        "estimated_savings_pct": estimated_savings_pct,
        "confidence": confidence,
        "risk_level": risk_level,
        "reason": (
            f"CPU p95 {cpu_p95:.1f}% e memória p95 {mem_p95:.1f}% abaixo dos limites "
            f"em janela de {selected_days} dias."
        ),
    }
    return VmRightsizingDecision(
        recommend=True,
        reason=(
            f"CPU p95 {cpu_p95:.1f}% e memória p95 {mem_p95:.1f}% abaixo dos limites "
            f"em janela de {selected_days} dias."
        ),
        risk_level=risk_level,
        confidence=confidence,
        evidence=evidence,
    )
