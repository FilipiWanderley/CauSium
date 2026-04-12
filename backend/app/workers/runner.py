"""Main worker runner — starts all background workers."""
import asyncio

from app.core.logging import configure_logging, get_logger
from app.workers.audit_checkpoint_worker import run_audit_checkpoint_worker
from app.workers.export_worker import run_export_worker
from app.workers.ingestion_worker import run_ingestion_worker
from app.workers.scoring_worker import run_scoring_worker

log = get_logger(__name__)


async def main() -> None:
    configure_logging()
    log.info("workers.starting")
    await asyncio.gather(
        run_ingestion_worker(),
        run_scoring_worker(),
        run_audit_checkpoint_worker(),
        run_export_worker(),
    )


if __name__ == "__main__":
    asyncio.run(main())
