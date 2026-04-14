#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

REQUIRED_FILES = [
    "docs/operations/Release_Runbook.md",
    "docs/operations/Rollback_Runbook.md",
    "docs/operations/E2E_Critical_Flows.md",
    "docs/operations/Go_No_Go_Checklist.md",
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def check_required_files() -> list[dict[str, Any]]:
    root = _repo_root()
    checks: list[dict[str, Any]] = []
    for rel in REQUIRED_FILES:
        path = root / rel
        checks.append(
            {
                "name": f"file_exists:{rel}",
                "ok": path.exists(),
                "detail": "found" if path.exists() else "missing",
            }
        )
    return checks


def check_http(base_url: str, timeout: float) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout) as client:
        for endpoint in ("/health", "/health/detailed", "/metrics"):
            url = f"{base_url.rstrip('/')}{endpoint}"
            try:
                resp = client.get(url)
                ok = resp.status_code == 200
                checks.append(
                    {
                        "name": f"http:{endpoint}",
                        "ok": ok,
                        "detail": f"status={resp.status_code}",
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "name": f"http:{endpoint}",
                        "ok": False,
                        "detail": str(exc),
                    }
                )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Release smoke validation")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", default="benchmark_artifacts/release_smoke.json")
    args = parser.parse_args()

    checks = check_required_files()

    if not args.dry_run:
        checks.extend(check_http(args.base_url, args.timeout))

    passed = sum(1 for c in checks if c["ok"])
    failed = len(checks) - passed

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "base_url": args.base_url,
        "passed": passed,
        "failed": failed,
        "checks": checks,
    }

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
