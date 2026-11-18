"""Existing server clock semantics shared by game coordinators."""
from datetime import datetime, timezone
from sqlalchemy import select, func


def server_now(db):
    value = (db.scalar(select(func.clock_timestamp())) if db.bind.dialect.name == 'postgresql'
             else datetime.now(timezone.utc))
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
