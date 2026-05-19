"""Main worker runner — starts all background workers."""
import asyncio
import os
import time
from pathlib import Path

from app.core.alerting import AlertSeverity, send_alert
from app.core.logging import configure_logging, get_logger
from app.core.observability import observe_worker_lifecycle
from app.workers.anomaly_detection_worker import run_anomaly_detection_worker
from app.workers.audit_checkpoint_worker import run_audit_checkpoint_worker
from app.workers.carbon_sync_worker import run_carbon_sync_worker
from app.workers.export_worker import run_export_worker
from app.workers.ingestion_worker import run_ingestion_worker
from app.workers.keyring_rotation_worker import run_keyring_rotation_worker
from app.workers.maintenance_worker import run_maintenance_worker
from app.workers.notification_worker import run_notification_worker
from app.workers.scoring_worker import run_scoring_worker
from app.workers.usage_observation_worker import run_usage_observation_worker

log = get_logger(__name__)

# Heartbeat file path — orchestrators (Docker, k8s) can check file freshness
# to determine if the worker process is alive and making progress.
HEARTBEAT_FILE = Path(os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/worker_heartbeat"))
HEARTBEAT_INTERVAL_SECONDS = 15
# If the heartbeat file is older than this, the worker is considered unhealthy.
HEARTBEAT_STALE_SECONDS = 60


def _touch_heartbeat() -> None:
    """Update the heartbeat file timestamp."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(str(time.time()))
    except OSError:
        pass  # Best-effort — don't crash the worker over a heartbeat write failure


async def _heartbeat_loop() -> None:
    """Periodically update the heartbeat file to signal liveness."""
    log.info("worker.heartbeat.started", path=str(HEARTBEAT_FILE), interval=HEARTBEAT_INTERVAL_SECONDS)
    while True:
        _touch_heartbeat()
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


async def _run_worker(name: str, fn):
    observe_worker_lifecycle(name, "started")
    log.info("worker.started", worker=name)
    try:
        await fn()
        observe_worker_lifecycle(name, "exited")
        log.warning("worker.exited", worker=name)
    except Exception as exc:
        observe_worker_lifecycle(name, "crashed")
        log.exception("worker.crashed", worker=name)
        send_alert(
            subject=f"Worker '{name}' crashed",
            body=f"Worker '{name}' terminated with exception: {type(exc).__name__}: {str(exc)[:300]}",
            severity=AlertSeverity.CRITICAL,
            source=f"worker.{name}",
            context={"worker": name, "error": type(exc).__name__},
        )
        raise


async def main() -> None:
    configure_logging()
    log.info("workers.starting")
    _touch_heartbeat()  # Initial heartbeat before workers start
    await asyncio.gather(
        _heartbeat_loop(),
        _run_worker("ingestion", run_ingestion_worker),
        _run_worker("scoring", run_scoring_worker),
        _run_worker("anomaly_detection", run_anomaly_detection_worker),
        _run_worker("audit_checkpoint", run_audit_checkpoint_worker),
        _run_worker("economics_export", run_export_worker),
        _run_worker("keyring_rotation", run_keyring_rotation_worker),
        _run_worker("carbon_sync", run_carbon_sync_worker),
        _run_worker("maintenance", run_maintenance_worker),
        _run_worker("notification", run_notification_worker),
        _run_worker("usage_observation", run_usage_observation_worker),
    )


if __name__ == "__main__":
    asyncio.run(main())
