"""Test env vars must be set before any `app.*` module is imported, since
Settings/engine are constructed at import time. conftest.py is imported by
pytest before any test module, so setting them here at module scope (not
inside a fixture) is what makes that ordering work.
"""
import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"
os.environ["DATA_MODE"] = "demo"
os.environ["ENVIRONMENT"] = "test"
os.environ["LIVE_TRADING_ENABLED"] = "false"

import pytest  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(db_session):
    """A TestClient sharing the same on-disk SQLite DB `db_session` just
    reset, so tests can seed via db_session and assert via HTTP."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client
