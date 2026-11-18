"""Clock extraction preserves the existing consumers' semantics."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.utils.server_time import server_now, utc


def test_postgres_uses_server_clock_and_truncates_to_milliseconds():
    db = Mock(bind=SimpleNamespace(dialect=SimpleNamespace(name='postgresql')))
    db.scalar.return_value = datetime(2030, 1, 2, 3, 4, 5, 123999, tzinfo=timezone.utc)
    assert server_now(db) == datetime(2030, 1, 2, 3, 4, 5, 123000, tzinfo=timezone.utc)
    assert 'clock_timestamp' in str(db.scalar.call_args.args[0])


def test_fallback_and_naive_datetime_compatibility():
    db = SimpleNamespace(bind=SimpleNamespace(dialect=SimpleNamespace(name='sqlite')))
    with patch('app.utils.server_time.datetime') as clock:
        clock.now.return_value = datetime(2030, 1, 2, microsecond=999999, tzinfo=timezone.utc)
        assert server_now(db).microsecond == 999000
        clock.now.assert_called_once_with(timezone.utc)
    naive = datetime(2030, 1, 2)
    aware = naive.replace(tzinfo=timezone.utc)
    assert utc(naive) == aware and utc(aware) is aware
