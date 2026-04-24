"""Main worker runner — starts all background workers."""
import asyncio

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


async def _run_worker(name: str, fn):
    observe_worker_lifecycle(name, "started")
    log.info("worker.started", worker=name)
    try:
        await fn()
        observe_worker_lifecycle(name, "exited")
        log.warning("worker.exited", worker=name)
    except Exception:
        observe_worker_lifecycle(name, "crashed")
        log.exception("worker.crashed", worker=name)
        raise


async def main() -> None:
    configure_logging()
    log.info("workers.starting")
    await asyncio.gather(
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
