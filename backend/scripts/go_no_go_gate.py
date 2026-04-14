#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    smoke: dict[str, Any],
    perf: dict[str, Any],
    *,
    max_p95_ms: float,
    required_success_status: int,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    smoke_failed = int(smoke.get("failed", 9999))
    checks.append(
        {
            "name": "release_smoke_failed_zero",
            "ok": smoke_failed == 0,
            "detail": f"failed={smoke_failed}",
        }
    )

    dry_run = bool(perf.get("dry_run", False))
    p95 = float(perf.get("p95_ms", 1e9))
    checks.append(
        {
            "name": "perf_p95_within_target",
            "ok": p95 <= max_p95_ms,
            "detail": f"p95_ms={p95} target={max_p95_ms}",
        }
    )

    status_counts_raw = perf.get("status_counts", {})
    status_counts: dict[int, int] = {}
    for k, v in status_counts_raw.items():
        status_counts[int(k)] = int(v)

    total = sum(status_counts.values())
    success = status_counts.get(required_success_status, 0)
    non_success = total - success

    checks.append(
        {
            "name": "perf_all_requests_success",
            "ok": non_success == 0 and total > 0,
            "detail": f"total={total} success={success} non_success={non_success}",
        }
    )

    decision = all(c["ok"] for c in checks)
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": "GO" if decision else "NO_GO",
        "dry_run": dry_run,
        "checks": checks,
        "inputs": {
            "max_p95_ms": max_p95_ms,
            "required_success_status": required_success_status,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Go/No-Go based on release artifacts")
    parser.add_argument(
        "--smoke-json",
        default="benchmark_artifacts/release_smoke.json",
        help="Path to release smoke artifact JSON",
    )
    parser.add_argument(
        "--perf-json",
        default="benchmark_artifacts/ledger_costs_benchmark.json",
        help="Path to performance benchmark artifact JSON",
    )
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--required-success-status", type=int, default=200)
    parser.add_argument(
        "--output-json",
        default="benchmark_artifacts/go_no_go.json",
        help="Path to write go/no-go decision artifact",
    )
    args = parser.parse_args()

    smoke = _load_json(args.smoke_json)
    perf = _load_json(args.perf_json)

    result = evaluate(
        smoke,
        perf,
        max_p95_ms=args.max_p95_ms,
        required_success_status=args.required_success_status,
    )

    out = Path(args.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result, indent=2))
    return 0 if result["decision"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
