"""Background ingestion scheduling via APScheduler.

APScheduler in-process is a deliberately simple choice for the MVP: it
needs no extra infrastructure and is a straightforward swap for Celery/RQ
later if ingestion volume or multi-worker scaling ever requires it — see
project rule on not overengineering ahead of a measured need.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.event_engine.ingest import run_event_ingestion
from app.services.impact_engine.graph import build_impact_links
from app.services.signal_engine.generator import generate_signals_for_event

logger = logging.getLogger("eye_of_horus")
_scheduler: BackgroundScheduler | None = None


def _run_ingestion_cycle() -> None:
    db = SessionLocal()
    try:
        events = run_event_ingestion(db)
        db.commit()
        for event in events:
            build_impact_links(db, event)
        db.commit()
        for event in events:
            generate_signals_for_event(db, event)
        db.commit()
        if events:
            logger.info("Ingestion cycle processed %d events", len(events))
    except Exception:  # noqa: BLE001
        logger.exception("Ingestion cycle failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    settings = get_settings()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_ingestion_cycle,
        "interval",
        seconds=settings.ingestion_interval_seconds,
        id="event_ingestion_cycle",
        next_run_time=None,  # first run already happened via bootstrap seeding
    )
    scheduler.start()
    _scheduler = scheduler
    return scheduler
