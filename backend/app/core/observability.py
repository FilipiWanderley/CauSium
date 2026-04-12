from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from collections import deque
from typing import DefaultDict
from uuid import uuid4

from fastapi import Request

_LOCK = threading.Lock()

_API_REQUESTS_TOTAL: DefaultDict[tuple[str, str, str], int] = defaultdict(int)
_API_DURATION_SUM_MS: DefaultDict[tuple[str, str, str], float] = defaultdict(float)
_API_DURATION_COUNT: DefaultDict[tuple[str, str, str], int] = defaultdict(int)
_API_DURATION_MAX_MS: DefaultDict[tuple[str, str, str], float] = defaultdict(float)
_API_DURATION_SAMPLES_MS: DefaultDict[tuple[str, str, str], deque[float]] = defaultdict(lambda: deque(maxlen=2000))

_WORKER_JOBS_TOTAL: DefaultDict[tuple[str, str], int] = defaultdict(int)
_WORKER_JOB_DURATION_SUM_MS: DefaultDict[tuple[str, str], float] = defaultdict(float)
_WORKER_JOB_DURATION_COUNT: DefaultDict[tuple[str, str], int] = defaultdict(int)
_WORKER_LIFECYCLE_TOTAL: DefaultDict[tuple[str, str], int] = defaultdict(int)

_UUID_LIKE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)
_INT_SEGMENT = re.compile(r"/\d+(?=/|$)")


def now_ms() -> float:
    return time.perf_counter() * 1000


def sanitize_path(path: str) -> str:
    normalized = _UUID_LIKE.sub(":id", path)
    normalized = _INT_SEGMENT.sub("/:id", normalized)
    return normalized


def resolve_trace_id(request: Request) -> str:
    header_trace = request.headers.get("x-trace-id")
    if header_trace:
        return header_trace.strip()

    header_request_id = request.headers.get("x-request-id")
    if header_request_id:
        return header_request_id.strip()

    return str(uuid4())


def observe_api_request(method: str, path: str, status_code: int, duration_ms: float) -> None:
    key = (method.upper(), sanitize_path(path), str(status_code))
    with _LOCK:
        _API_REQUESTS_TOTAL[key] += 1
        _API_DURATION_SUM_MS[key] += duration_ms
        _API_DURATION_COUNT[key] += 1
        _API_DURATION_MAX_MS[key] = max(_API_DURATION_MAX_MS[key], duration_ms)
        _API_DURATION_SAMPLES_MS[key].append(duration_ms)


def observe_worker_job(worker: str, status: str, duration_ms: float) -> None:
    key = (worker, status)
    with _LOCK:
        _WORKER_JOBS_TOTAL[key] += 1
        _WORKER_JOB_DURATION_SUM_MS[key] += duration_ms
        _WORKER_JOB_DURATION_COUNT[key] += 1


def observe_worker_lifecycle(worker: str, event: str) -> None:
    key = (worker, event)
    with _LOCK:
        _WORKER_LIFECYCLE_TOTAL[key] += 1


def _metric_labels(**labels: str) -> str:
    if not labels:
        return ""
    parts = [f'{k}="{v}"' for k, v in labels.items()]
    return "{" + ",".join(parts) + "}"


def render_metrics_prometheus() -> str:
    lines: list[str] = []

    lines.append("# HELP api_requests_total Total API requests by method, path and status.")
    lines.append("# TYPE api_requests_total counter")
    for (method, path, status), value in sorted(_API_REQUESTS_TOTAL.items()):
        lines.append(
            f"api_requests_total{_metric_labels(method=method, path=path, status=status)} {value}"
        )

    lines.append("# HELP api_request_duration_ms_sum Total API request duration in milliseconds.")
    lines.append("# TYPE api_request_duration_ms_sum counter")
    for (method, path, status), value in sorted(_API_DURATION_SUM_MS.items()):
        lines.append(
            f"api_request_duration_ms_sum{_metric_labels(method=method, path=path, status=status)} {value:.3f}"
        )

    lines.append("# HELP api_request_duration_ms_count API request samples for duration metrics.")
    lines.append("# TYPE api_request_duration_ms_count counter")
    for (method, path, status), value in sorted(_API_DURATION_COUNT.items()):
        lines.append(
            f"api_request_duration_ms_count{_metric_labels(method=method, path=path, status=status)} {value}"
        )

    lines.append("# HELP api_request_duration_ms_max Max API request duration in milliseconds.")
    lines.append("# TYPE api_request_duration_ms_max gauge")
    for (method, path, status), value in sorted(_API_DURATION_MAX_MS.items()):
        lines.append(
            f"api_request_duration_ms_max{_metric_labels(method=method, path=path, status=status)} {value:.3f}"
        )

    lines.append("# HELP worker_jobs_total Total processed worker jobs by worker and status.")
    lines.append("# TYPE worker_jobs_total counter")
    for (worker, status), value in sorted(_WORKER_JOBS_TOTAL.items()):
        lines.append(f"worker_jobs_total{_metric_labels(worker=worker, status=status)} {value}")

    lines.append("# HELP worker_job_duration_ms_sum Total worker job duration in milliseconds.")
    lines.append("# TYPE worker_job_duration_ms_sum counter")
    for (worker, status), value in sorted(_WORKER_JOB_DURATION_SUM_MS.items()):
        lines.append(
            f"worker_job_duration_ms_sum{_metric_labels(worker=worker, status=status)} {value:.3f}"
        )

    lines.append("# HELP worker_job_duration_ms_count Worker job duration samples.")
    lines.append("# TYPE worker_job_duration_ms_count counter")
    for (worker, status), value in sorted(_WORKER_JOB_DURATION_COUNT.items()):
        lines.append(
            f"worker_job_duration_ms_count{_metric_labels(worker=worker, status=status)} {value}"
        )

    lines.append("# HELP worker_lifecycle_total Worker lifecycle transitions by worker and event.")
    lines.append("# TYPE worker_lifecycle_total counter")
    for (worker, event), value in sorted(_WORKER_LIFECYCLE_TOTAL.items()):
        lines.append(
            f"worker_lifecycle_total{_metric_labels(worker=worker, event=event)} {value}"
        )

    return "\n".join(lines) + "\n"


def _percentile(samples: list[float], p: float) -> float:
    if not samples:
        return 0.0
    if len(samples) == 1:
        return samples[0]
    ordered = sorted(samples)
    idx = int(round((p / 100.0) * (len(ordered) - 1)))
    return ordered[idx]


def build_sli_slo_snapshot(*, error_budget_pct: float = 1.0, api_p95_ms_target: float = 500.0) -> dict:
    with _LOCK:
        api_requests = dict(_API_REQUESTS_TOTAL)
        api_duration_sum = dict(_API_DURATION_SUM_MS)
        api_duration_count = dict(_API_DURATION_COUNT)
        api_duration_max = dict(_API_DURATION_MAX_MS)
        api_duration_samples = {k: list(v) for k, v in _API_DURATION_SAMPLES_MS.items()}
        worker_jobs = dict(_WORKER_JOBS_TOTAL)
        worker_lifecycle = dict(_WORKER_LIFECYCLE_TOTAL)

    total_requests = 0
    total_5xx = 0
    path_rollup: dict[str, dict] = {}

    for (method, path, status), count in api_requests.items():
        status_code = int(status)
        duration_sum = api_duration_sum.get((method, path, status), 0.0)
        duration_count = api_duration_count.get((method, path, status), 0)
        duration_max = api_duration_max.get((method, path, status), 0.0)
        samples = api_duration_samples.get((method, path, status), [])

        total_requests += count
        if 500 <= status_code <= 599:
            total_5xx += count

        bucket = path_rollup.setdefault(
            path,
            {
                "path": path,
                "requests": 0,
                "errors_5xx": 0,
                "duration_sum_ms": 0.0,
                "duration_count": 0,
                "max_latency_ms": 0.0,
                "samples": [],
            },
        )
        bucket["requests"] += count
        bucket["duration_sum_ms"] += duration_sum
        bucket["duration_count"] += duration_count
        bucket["max_latency_ms"] = max(bucket["max_latency_ms"], duration_max)
        bucket["samples"].extend(samples)
        if 500 <= status_code <= 599:
            bucket["errors_5xx"] += count

    api_error_rate_pct = round((total_5xx / total_requests) * 100, 4) if total_requests else 0.0
    api_success_rate_pct = round(100.0 - api_error_rate_pct, 4) if total_requests else 100.0

    api_paths: list[dict] = []
    alerts: list[dict] = []

    for path, bucket in path_rollup.items():
        requests = bucket["requests"]
        errors = bucket["errors_5xx"]
        error_rate = round((errors / requests) * 100, 4) if requests else 0.0
        avg_latency = round((bucket["duration_sum_ms"] / bucket["duration_count"]), 2) if bucket["duration_count"] else 0.0
        p95_latency = round(_percentile(bucket["samples"], 95), 2) if bucket["samples"] else 0.0
        max_latency = round(bucket["max_latency_ms"], 2)

        api_paths.append(
            {
                "path": path,
                "requests": requests,
                "errors_5xx": errors,
                "error_rate_pct": error_rate,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "max_latency_ms": max_latency,
            }
        )

        if requests >= 20 and error_rate > error_budget_pct:
            alerts.append(
                {
                    "scope": "api",
                    "severity": "critical",
                    "title": f"Error budget breach on {path}",
                    "detail": (
                        f"error_rate={error_rate}% exceeded target={error_budget_pct}% "
                        f"with {requests} requests"
                    ),
                    "recommended_action": "Inspect recent 5xx logs by trace_id and rollback/retry failing dependency.",
                }
            )

        if requests >= 20 and p95_latency > api_p95_ms_target:
            alerts.append(
                {
                    "scope": "api",
                    "severity": "warning",
                    "title": f"Latency SLO breach on {path}",
                    "detail": (
                        f"p95_latency_ms={p95_latency} exceeded target={api_p95_ms_target} "
                        f"with {requests} requests"
                    ),
                    "recommended_action": "Profile slow queries/traces and apply cache/index tuning for this route.",
                }
            )

    api_paths.sort(key=lambda row: (-row["error_rate_pct"], -row["p95_latency_ms"], -row["requests"]))

    worker_rows: list[dict] = []
    worker_by_name: dict[str, dict] = {}
    for (worker, status), count in worker_jobs.items():
        row = worker_by_name.setdefault(
            worker,
            {"worker": worker, "success": 0, "retry": 0, "failed": 0, "locked": 0, "total": 0},
        )
        row[status] = row.get(status, 0) + count
        row["total"] += count

    for row in worker_by_name.values():
        total = row["total"]
        failed = row.get("failed", 0)
        retries = row.get("retry", 0)
        error_rate = round(((failed + retries) / total) * 100, 4) if total else 0.0
        row["error_rate_pct"] = error_rate
        worker_rows.append(row)

        if total >= 10 and error_rate > error_budget_pct:
            alerts.append(
                {
                    "scope": "worker",
                    "severity": "critical",
                    "title": f"Worker error budget breach: {row['worker']}",
                    "detail": (
                        f"error_rate={error_rate}% exceeded target={error_budget_pct}% "
                        f"(failed={failed}, retry={retries}, total={total})"
                    ),
                    "recommended_action": "Inspect DLQ/retry payloads and dependency health before increasing concurrency.",
                }
            )

    worker_rows.sort(key=lambda row: (-row["error_rate_pct"], -row["total"]))

    lifecycle = [
        {"worker": worker, "event": event, "count": count}
        for (worker, event), count in sorted(worker_lifecycle.items())
    ]

    return {
        "targets": {
            "api_error_budget_pct": error_budget_pct,
            "api_p95_latency_ms": api_p95_ms_target,
        },
        "global_sli": {
            "requests_total": total_requests,
            "errors_5xx_total": total_5xx,
            "api_error_rate_pct": api_error_rate_pct,
            "api_success_rate_pct": api_success_rate_pct,
            "error_budget_burn_rate": round((api_error_rate_pct / error_budget_pct), 4) if error_budget_pct > 0 else 0.0,
        },
        "api_paths": api_paths[:25],
        "workers": worker_rows,
        "worker_lifecycle": lifecycle,
        "alerts": alerts,
    }
