#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

VALID_TOOLS = {"bandit", "pip_audit", "npm_audit", "gitleaks"}


@dataclass
class BaselineEntry:
    id: str
    reason: str
    owner: str
    ticket: str
    expires_on: date


def load_baseline(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Baseline file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid baseline JSON: {exc}") from exc
    return data


def parse_entry(raw: dict[str, Any], tool: str, idx: int) -> BaselineEntry:
    required = {"id", "reason", "owner", "ticket", "expires_on"}
    missing = required - set(raw.keys())
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise SystemExit(f"{tool}[{idx}] missing required fields: {missing_list}")

    if not str(raw["id"]).strip():
        raise SystemExit(f"{tool}[{idx}] id cannot be empty")
    if not str(raw["reason"]).strip():
        raise SystemExit(f"{tool}[{idx}] reason cannot be empty")
    if not str(raw["owner"]).strip():
        raise SystemExit(f"{tool}[{idx}] owner cannot be empty")
    if not str(raw["ticket"]).strip():
        raise SystemExit(f"{tool}[{idx}] ticket cannot be empty")

    try:
        expires_on = date.fromisoformat(str(raw["expires_on"]))
    except ValueError as exc:
        raise SystemExit(
            f"{tool}[{idx}] expires_on must be YYYY-MM-DD; got {raw['expires_on']}"
        ) from exc

    return BaselineEntry(
        id=str(raw["id"]).strip(),
        reason=str(raw["reason"]).strip(),
        owner=str(raw["owner"]).strip(),
        ticket=str(raw["ticket"]).strip(),
        expires_on=expires_on,
    )


def read_entries(data: dict[str, Any], tool: str) -> list[BaselineEntry]:
    exceptions = data.get("exceptions")
    if not isinstance(exceptions, dict):
        raise SystemExit("Baseline must include an 'exceptions' object")

    rows = exceptions.get(tool, [])
    if not isinstance(rows, list):
        raise SystemExit(f"exceptions.{tool} must be a list")

    entries: list[BaselineEntry] = []
    for idx, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise SystemExit(f"{tool}[{idx}] must be an object")
        entries.append(parse_entry(raw, tool, idx))
    return entries


def validate_baseline(data: dict[str, Any]) -> None:
    version = data.get("version")
    if version != 1:
        raise SystemExit(f"Unsupported baseline version: {version}. Expected: 1")

    exceptions = data.get("exceptions")
    if not isinstance(exceptions, dict):
        raise SystemExit("Baseline must include an 'exceptions' object")

    unknown_tools = sorted(set(exceptions.keys()) - VALID_TOOLS)
    if unknown_tools:
        raise SystemExit(f"Unknown exception tool keys: {', '.join(unknown_tools)}")

    today = date.today()
    for tool in VALID_TOOLS:
        entries = read_entries(data, tool)
        for entry in entries:
            if entry.expires_on < today:
                raise SystemExit(
                    f"Expired baseline exception: tool={tool} id={entry.id} "
                    f"expires_on={entry.expires_on.isoformat()}"
                )


def emit_ids(entries: list[BaselineEntry]) -> str:
    return " ".join(entry.id for entry in entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and query security baseline exceptions")
    parser.add_argument("command", choices=["validate", "bandit-ids", "pip-audit-ids", "npm-audit-ids", "gitleaks-ids"])
    parser.add_argument("--file", default=".security/security_baseline.json")
    args = parser.parse_args()

    path = Path(args.file)
    data = load_baseline(path)

    if args.command == "validate":
        validate_baseline(data)
        print("baseline_valid")
        return 0

    validate_baseline(data)

    if args.command == "bandit-ids":
        print(emit_ids(read_entries(data, "bandit")))
        return 0
    if args.command == "pip-audit-ids":
        print(emit_ids(read_entries(data, "pip_audit")))
        return 0
    if args.command == "npm-audit-ids":
        print(emit_ids(read_entries(data, "npm_audit")))
        return 0

    print(emit_ids(read_entries(data, "gitleaks")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
