#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import time
from dataclasses import dataclass

import httpx


@dataclass
class Sample:
    latency_ms: float
    status_code: int


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark /api/v1/ledger/costs endpoint and report p50/p95 latency.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--token", default="", help="Bearer token for authenticated calls")
    parser.add_argument("--requests", type=int, default=120, help="Number of requests to execute")
    parser.add_argument("--warmup", type=int, default=15, help="Warmup requests")
    parser.add_argument("--concurrency", type=int, default=1, help="Reserved for future async mode")
    parser.add_argument("--page-size", type=int, default=20, help="Page size for each request")
    parser.add_argument(
        "--output-json",
        default="benchmark_artifacts/ledger_costs_benchmark.json",
        help="Path to write benchmark metrics as JSON artifact",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate synthetic benchmark samples (for CI smoke) without calling the API",
    )
    return parser.parse_args()


def random_params(page_size: int) -> dict[str, object]:
    provider = random.choice(["", "azure", "aws", "gcp"])
    service = random.choice(["", "Compute", "Storage", "Networking"])
    owner_team = random.choice(["", "platform", "finops", "sre"])
    environment = random.choice(["", "prod", "staging", "dev"])

    params: dict[str, object] = {
        "days": random.choice([30, 60, 90]),
        "page": random.choice([1, 2, 3]),
        "page_size": page_size,
    }
    if provider:
        params["provider"] = provider
    if service:
        params["service"] = service
    if owner_team:
        params["owner_team"] = owner_team
    if environment:
        params["environment"] = environment
    return params


def request_once(client: httpx.Client, base_url: str, page_size: int) -> Sample:
    params = random_params(page_size)
    started = time.perf_counter()
    response = client.get(f"{base_url}/api/v1/ledger/costs", params=params)
    latency_ms = (time.perf_counter() - started) * 1000
    return Sample(latency_ms=latency_ms, status_code=response.status_code)


def dry_run_sample() -> Sample:
    # Deterministic synthetic latency envelope to smoke-test the pipeline path.
    latency_ms = random.uniform(35.0, 120.0)
    return Sample(latency_ms=latency_ms, status_code=200)


def build_report(samples: list[Sample], *, base_url: str, requests: int, warmup: int, dry_run: bool) -> dict:
    latencies = [s.latency_ms for s in samples]
    status_counts: dict[int, int] = {}
    for sample in samples:
        status_counts[sample.status_code] = status_counts.get(sample.status_code, 0) + 1

    report = {
        "base_url": base_url,
        "requests": requests,
        "warmup": warmup,
        "dry_run": dry_run,
        "status_counts": status_counts,
        "mean_ms": round(statistics.fmean(latencies), 2),
        "p50_ms": round(percentile(latencies, 0.50), 2),
        "p90_ms": round(percentile(latencies, 0.90), 2),
        "p95_ms": round(percentile(latencies, 0.95), 2),
        "p99_ms": round(percentile(latencies, 0.99), 2),
    }

    success_only = [s.latency_ms for s in samples if s.status_code == 200]
    if success_only:
        report["success_p95_ms"] = round(percentile(success_only, 0.95), 2)
    return report


def write_report(path_str: str, report: dict) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    samples: list[Sample] = []

    if args.dry_run:
        for _ in range(max(args.warmup, 0)):
            dry_run_sample()
        for _ in range(max(args.requests, 1)):
            samples.append(dry_run_sample())
    else:
        if not args.token.strip():
            raise SystemExit("--token is required unless --dry-run is enabled")
        headers = {"Authorization": f"Bearer {args.token}"}
        with httpx.Client(headers=headers, timeout=30.0) as client:
            for _ in range(max(args.warmup, 0)):
                request_once(client, args.base_url, args.page_size)

            for _ in range(max(args.requests, 1)):
                samples.append(request_once(client, args.base_url, args.page_size))

    report = build_report(
        samples,
        base_url=args.base_url,
        requests=len(samples),
        warmup=max(args.warmup, 0),
        dry_run=args.dry_run,
    )
    write_report(args.output_json, report)

    print("=== Ledger Detailed Costs Benchmark ===")
    print(f"base_url: {report['base_url']}")
    print(f"requests: {report['requests']}")
    print(f"dry_run: {report['dry_run']}")
    print(f"status_counts: {report['status_counts']}")
    print(f"mean_ms: {report['mean_ms']:.2f}")
    print(f"p50_ms: {report['p50_ms']:.2f}")
    print(f"p90_ms: {report['p90_ms']:.2f}")
    print(f"p95_ms: {report['p95_ms']:.2f}")
    print(f"p99_ms: {report['p99_ms']:.2f}")
    if "success_p95_ms" in report:
        print(f"success_p95_ms: {report['success_p95_ms']:.2f}")
    print(f"json_artifact: {args.output_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
