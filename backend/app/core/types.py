"""Custom SQLAlchemy column types.

SQLite (the default dev/test database) does not actually persist timezone
offsets for DateTime(timezone=True) columns — every value round-trips as
naive, even though every value written here is UTC. That silently breaks
any code comparing a DB-loaded datetime against a fresh
datetime.now(timezone.utc) (a TypeError on offset-naive vs offset-aware
comparison), which the temporal-integrity guard depends on constantly.
UTCDateTime fixes this at the type level so every model gets aware
datetimes back regardless of which backend (SQLite locally, Postgres in
production) is in use.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
