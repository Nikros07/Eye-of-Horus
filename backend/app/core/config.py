"""Central runtime configuration.

Every switch that changes system behavior (data mode, live trading, broker
selection) lives here and is driven entirely by environment variables so the
same code runs unmodified across local dev, CI, and production.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Eye of Horus"
    environment: Literal["development", "test", "production"] = "development"

    database_url: str = "sqlite:///./eye_of_horus.db"

    # DATA_MODE=demo uses deterministic, clearly-flagged seeded generators.
    # DATA_MODE=live calls the real connectors (NASA EONET, Open-Meteo, yfinance).
    data_mode: Literal["demo", "live"] = "demo"

    # Trading safety. Live trading is refused everywhere unless this AND the
    # per-portfolio risk config both explicitly allow it.
    live_trading_enabled: bool = False

    default_paper_capital: float = 10_000.0

    # internal = PaperBroker simulates fills in-process against our own
    # ledger (default, zero setup). alpaca = AlpacaBroker submits real
    # orders to Alpaca's free paper-trading account (real fills/market data,
    # still fake money) — requires ALPACA_API_KEY/ALPACA_SECRET_KEY below.
    # Only ever affects portfolio.mode == "paper"; "live" mode is untouched
    # and still always resolves to the deliberately-unconfigured LiveBroker.
    broker_provider: Literal["internal", "alpaca"] = "internal"
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None

    # AI research layer. Without a key the system falls back to the
    # deterministic evidence synthesizer (never fabricates facts either way).
    anthropic_api_key: str | None = None

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    market_data_provider: Literal["demo", "yfinance"] = "demo"

    ingestion_interval_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
