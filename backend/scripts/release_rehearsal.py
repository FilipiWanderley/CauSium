#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing expected artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full release rehearsal pipeline")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", default="", help="Bearer token for real benchmark calls")
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--warmup", type=int, default=15)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-dir", default="benchmark_artifacts")
    parser.add_argument("--output-json", default="benchmark_artifacts/release_rehearsal.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = _script_dir()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    perf_json = out_dir / "ledger_costs_benchmark.rehearsal.json"
    smoke_json = out_dir / "release_smoke.rehearsal.json"
    gate_json = out_dir / "go_no_go.rehearsal.json"

    python_exec = sys.executable

    perf_cmd = [
        python_exec,
        str(script_dir / "benchmark_ledger_costs.py"),
        "--base-url",
        args.base_url,
        "--requests",
        str(args.requests),
        "--warmup",
        str(args.warmup),
        "--output-json",
        str(perf_json),
    ]
    if args.dry_run:
        perf_cmd.append("--dry-run")
    else:
        if not args.token.strip():
            raise SystemExit("--token is required when --dry-run is not enabled")
        perf_cmd.extend(["--token", args.token.strip()])

    smoke_cmd = [
        python_exec,
        str(script_dir / "release_smoke.py"),
        "--base-url",
        args.base_url,
        "--output-json",
        str(smoke_json),
    ]
    if args.dry_run:
        smoke_cmd.append("--dry-run")

    gate_cmd = [
        python_exec,
        str(script_dir / "go_no_go_gate.py"),
        "--smoke-json",
        str(smoke_json),
        "--perf-json",
        str(perf_json),
        "--max-p95-ms",
        str(args.max_p95_ms),
        "--output-json",
        str(gate_json),
    ]

    steps: list[dict[str, Any]] = []

    perf_rc, perf_out, perf_err = _run(perf_cmd)
    steps.append(
        {
            "name": "benchmark",
            "command": perf_cmd,
            "exit_code": perf_rc,
            "stdout": perf_out,
            "stderr": perf_err,
        }
    )

    smoke_rc, smoke_out, smoke_err = _run(smoke_cmd)
    steps.append(
        {
            "name": "release_smoke",
            "command": smoke_cmd,
            "exit_code": smoke_rc,
            "stdout": smoke_out,
            "stderr": smoke_err,
        }
    )

    gate_rc, gate_out, gate_err = _run(gate_cmd)
    steps.append(
        {
            "name": "go_no_go",
            "command": gate_cmd,
            "exit_code": gate_rc,
            "stdout": gate_out,
            "stderr": gate_err,
        }
    )

    result: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "base_url": args.base_url,
        "steps": steps,
        "artifacts": {
            "benchmark": str(perf_json),
            "release_smoke": str(smoke_json),
            "go_no_go": str(gate_json),
        },
    }

    try:
        result["benchmark"] = _load_json(perf_json)
    except Exception as exc:
        result["benchmark_error"] = str(exc)

    try:
        result["release_smoke"] = _load_json(smoke_json)
    except Exception as exc:
        result["release_smoke_error"] = str(exc)

    try:
        result["go_no_go"] = _load_json(gate_json)
    except Exception as exc:
        result["go_no_go_error"] = str(exc)

    decision = result.get("go_no_go", {}).get("decision")
    result["decision"] = decision or "NO_GO"

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps({
        "decision": result["decision"],
        "output_json": str(out_json),
        "benchmark_artifact": str(perf_json),
        "smoke_artifact": str(smoke_json),
        "gate_artifact": str(gate_json),
    }, indent=2))

    if perf_rc != 0 or smoke_rc != 0 or gate_rc != 0:
        return 1
    return 0 if result["decision"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
