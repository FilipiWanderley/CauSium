from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from typing import DefaultDict
from uuid import uuid4

from fastapi import Request

_LOCK = threading.Lock()

_API_REQUESTS_TOTAL: DefaultDict[tuple[str, str, str], int] = defaultdict(int)
_API_DURATION_SUM_MS: DefaultDict[tuple[str, str, str], float] = defaultdict(float)
_API_DURATION_COUNT: DefaultDict[tuple[str, str, str], int] = defaultdict(int)
_API_DURATION_MAX_MS: DefaultDict[tuple[str, str, str], float] = defaultdict(float)

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
