"""Dedicated ingestion worker runner.

Starts only the ingestion worker loop, without importing FastAPI app/main.
"""

from __future__ import annotations

import asyncio

from app.core.logging import configure_logging, get_logger
from app.workers.ingestion_worker import run_ingestion_worker

log = get_logger(__name__)


async def _main() -> int:
    log.info("ingestion_runner.starting")
    try:
        await run_ingestion_worker()
        log.info("ingestion_runner.stopped", reason="worker_exited")
        return 0
    except asyncio.CancelledError:
        log.info("ingestion_runner.stopped", reason="cancelled")
        return 0
    except Exception:
        log.exception("ingestion_runner.failed")
        return 1


def main() -> int:
    configure_logging()
    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        log.info("ingestion_runner.stopped", reason="keyboard_interrupt")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
