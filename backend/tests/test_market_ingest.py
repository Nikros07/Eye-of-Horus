from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.models.market import PriceBar
from app.models.system import DataSource
from app.services.market_engine.base import Bar, MarketSource, Quote
from app.services.market_engine.ingest import (
    MAX_SYMBOLS_PER_SYNC_CYCLE,
    ensure_assets,
    run_price_ingestion,
    sync_live_price_history,
)


class _FakeMarketSource(MarketSource):
    name = "FAKE_LIVE"
    is_demo = False

    def __init__(self, fail_symbols: set[str] | None = None) -> None:
        self.fail_symbols = fail_symbols or set()
        self.history_calls = 0
        self.quote_calls = 0

    def get_history(self, symbol, start, end, interval="1d"):
        if symbol in self.fail_symbols:
            raise RuntimeError(f"{symbol} rate-limited")
        self.history_calls += 1
        return [
            Bar(ts=start + timedelta(hours=i), open=100.0, high=101.0, low=99.0, close=100.5, volume=1000.0)
            for i in range(3)
        ]

    def get_quote(self, symbol):
        if symbol in self.fail_symbols:
            raise RuntimeError(f"{symbol} rate-limited")
        self.quote_calls += 1
        return Quote(symbol=symbol, price=123.45, change_pct=0.5, ts=datetime.now(timezone.utc), is_demo=False)


def _seed_one_bar_per_asset(db_session, assets, ts) -> None:
    for asset in assets.values():
        db_session.add(
            PriceBar(
                asset_id=asset.id,
                ts=ts,
                open=100.0,
                high=100.0,
                low=100.0,
                close=100.0,
                volume=0.0,
                source="SEED",
                availability_time=ts,
                is_demo=False,
            )
        )
    db_session.commit()


def test_sync_live_price_history_backfills_at_most_the_per_cycle_cap(db_session):
    source = _FakeMarketSource()
    sync_live_price_history(db_session, source)
    db_session.commit()

    assets = ensure_assets(db_session)
    assert len(assets) > MAX_SYMBOLS_PER_SYNC_CYCLE  # otherwise this test proves nothing
    assert db_session.query(PriceBar).count() == 3 * MAX_SYMBOLS_PER_SYNC_CYCLE
    assert source.history_calls == MAX_SYMBOLS_PER_SYNC_CYCLE
    assert source.quote_calls == 0

    ds = db_session.query(DataSource).filter(DataSource.name == "FAKE_LIVE").one()
    assert ds.status == "online"
    assert ds.is_demo is False


def test_sync_live_price_history_backfills_the_full_universe_over_several_cycles(db_session):
    source = _FakeMarketSource()
    assets = ensure_assets(db_session)
    db_session.commit()

    for _ in range(-(-len(assets) // MAX_SYMBOLS_PER_SYNC_CYCLE)):  # ceil division
        sync_live_price_history(db_session, source)
        db_session.commit()

    # Every symbol backfilled exactly once — no gaps, no duplicate backfills
    # (a symbol can additionally pick up a quote top-up once its backfilled
    # bars are stale enough, which is correct, just not asserted here).
    assert source.history_calls == len(assets)
    for asset in assets.values():
        assert db_session.query(PriceBar).filter(PriceBar.asset_id == asset.id).count() >= 3


def test_sync_live_price_history_appends_fresh_quote_when_latest_bar_is_stale(db_session):
    assets = ensure_assets(db_session)
    db_session.commit()
    _seed_one_bar_per_asset(db_session, assets, datetime.now(timezone.utc) - timedelta(hours=1))

    source = _FakeMarketSource()
    sync_live_price_history(db_session, source)
    db_session.commit()

    assert db_session.query(PriceBar).count() == len(assets) + MAX_SYMBOLS_PER_SYNC_CYCLE
    assert source.quote_calls == MAX_SYMBOLS_PER_SYNC_CYCLE
    assert source.history_calls == 0


def test_sync_live_price_history_skips_fresh_quote_when_latest_bar_is_recent(db_session):
    assets = ensure_assets(db_session)
    db_session.commit()
    _seed_one_bar_per_asset(db_session, assets, datetime.now(timezone.utc))

    source = _FakeMarketSource()
    sync_live_price_history(db_session, source)
    db_session.commit()

    assert db_session.query(PriceBar).count() == len(assets)
    assert source.quote_calls == 0
    assert source.history_calls == 0


def test_sync_live_price_history_one_failing_symbol_does_not_block_others(db_session):
    assets = ensure_assets(db_session)
    db_session.commit()
    failing_symbol = next(iter(assets))
    source = _FakeMarketSource(fail_symbols={failing_symbol})

    sync_live_price_history(db_session, source)
    db_session.commit()

    failed_asset = assets[failing_symbol]
    assert db_session.query(PriceBar).filter(PriceBar.asset_id == failed_asset.id).count() == 0

    other_symbol = next(s for s in assets if s != failing_symbol)
    other_asset = assets[other_symbol]
    assert db_session.query(PriceBar).filter(PriceBar.asset_id == other_asset.id).count() > 0

    ds = db_session.query(DataSource).filter(DataSource.name == "FAKE_LIVE").one()
    assert ds.status == "degraded"
    assert failing_symbol in ds.last_error


def test_run_price_ingestion_uses_demo_seeder_in_demo_mode(db_session):
    run_price_ingestion(db_session)
    db_session.commit()

    assert db_session.query(PriceBar).count() > 0
    ds = db_session.query(DataSource).filter(DataSource.name == "DEMO_MARKET").one()
    assert ds.is_demo is True


def test_run_price_ingestion_uses_live_sync_in_live_mode(db_session, monkeypatch):
    fake_source = _FakeMarketSource()
    monkeypatch.setattr(
        "app.services.market_engine.ingest.get_settings",
        lambda: SimpleNamespace(data_mode="live"),
    )
    monkeypatch.setattr(
        "app.services.market_engine.factory.get_market_source",
        lambda: fake_source,
    )

    run_price_ingestion(db_session)
    db_session.commit()

    assert fake_source.history_calls > 0
