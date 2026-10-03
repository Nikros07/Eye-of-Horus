"""Idempotent startup seeding: ingest events, build impact links, sync price
history (demo or live, see market_engine.ingest.run_price_ingestion),
generate signals, and ensure a default paper portfolio exists. Safe to call
on every startup — everything here is a no-op once data already exists.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.event import Event
from app.models.trading import Portfolio
from app.services.event_engine.ingest import run_event_ingestion
from app.services.impact_engine.graph import build_impact_links
from app.services.market_engine.ingest import run_price_ingestion
from app.services.signal_engine.generator import generate_signals_for_event

logger = logging.getLogger("eye_of_horus")


def ensure_demo_data_seeded() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        existing_events = db.query(Event).count()
        if existing_events == 0:
            events = run_event_ingestion(db)
            db.commit()
            for event in events:
                build_impact_links(db, event)
            db.commit()
            logger.info("Seeded %d events", len(events))
        else:
            events = db.query(Event).all()

        run_price_ingestion(db)
        db.commit()

        for event in events:
            generate_signals_for_event(db, event)
        db.commit()

        default_portfolio = db.query(Portfolio).filter(Portfolio.name == "Main Portfolio").one_or_none()
        if default_portfolio is None:
            default_portfolio = Portfolio(
                name="Main Portfolio",
                mode="paper",
                cash=settings.default_paper_capital,
                initial_capital=settings.default_paper_capital,
                # The whole point of this portfolio is to demonstrate the
                # scheduler's automated event -> signal -> trade loop, so it
                # starts live rather than requiring a manual opt-in click
                # that a fresh deploy's ephemeral SQLite file would silently
                # lose on the next restart. Still 100% paper money either way.
                auto_trade_enabled=True,
            )
            db.add(default_portfolio)
            db.commit()
            from app.services.trading_engine.risk_engine import get_or_create_risk_config

            get_or_create_risk_config(db, default_portfolio)
            db.commit()
            logger.info("Created default paper portfolio with %.2f capital", settings.default_paper_capital)
    finally:
        db.close()
