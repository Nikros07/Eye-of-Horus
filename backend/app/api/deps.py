from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.trading import Portfolio

MAIN_PORTFOLIO_NAME = "Main Portfolio"


def get_main_portfolio(db: Session) -> Portfolio:
    portfolio = db.query(Portfolio).filter(Portfolio.name == MAIN_PORTFOLIO_NAME).one_or_none()
    if portfolio is None:
        raise HTTPException(404, "No portfolio found — startup seeding may not have completed yet.")
    return portfolio
