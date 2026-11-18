"""Synthetic migration fixtures: create the origin schema, never downgrade to it."""
from contextlib import contextmanager
from uuid import uuid4
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, select, text


@contextmanager
def origin_schema(source, revision):
    """Only a sibling schema of an explicitly guarded disposable fixture database."""
    assert source.dialect.name == 'postgresql' and source.url.host == 'pg'
    assert (source.url.database, source.url.username) in {
        ('biogamed_trivial_test', 'trivial_test'),
        ('biogamed_pasapalabra_test', 'codex_test'),
    }
    with source.connect() as connection:
        assert connection.execute(text('SELECT current_database(),current_user')).one() == (source.url.database, source.url.username)
    schema = 'migration_fixture_' + uuid4().hex
    with source.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    target = create_engine(source.url, connect_args={'options': f'-csearch_path={schema}'})
    try:
        with patch('app.database.engine', target):
            command.upgrade(Config('alembic.ini'), revision)
        yield target
    finally:
        target.dispose()
        with source.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


def copy_synthetic_rows(source, target, tables, *, omitted_defaults=None):
    """Copy only fixture data into the historical schema, checking omitted values.

    Current services create realistic synthetic receipts/copies in the source.
    Reflection avoids asking current ORM models to query columns not yet created.
    An absent newer column must be NULL or an explicitly checked initial default.
    """
    assert source.url == target.url and source.dialect.name == 'postgresql'
    omitted_defaults = omitted_defaults or {}
    with source.connect() as before, target.begin() as after:
        for name in tables:
            old = Table(name, MetaData(), autoload_with=after)
            current = Table(name, MetaData(), autoload_with=before)
            assert set(old.c.keys()) <= set(current.c.keys())
            rows = before.execute(select(current).order_by(*current.primary_key.columns)).mappings().all()
            for row in rows:
                for field in set(current.c.keys()) - set(old.c.keys()):
                    assert row[field] == omitted_defaults.get((name, field)), f'Non-default omitted field: {name}.{field}'
            if rows:
                after.execute(old.insert(), [{field: row[field] for field in old.c.keys()} for row in rows])
            if rows and 'id' in old.c:
                sequence = after.scalar(text("SELECT pg_get_serial_sequence(:name,'id')"), {'name': name})
                if sequence:
                    after.execute(text('SELECT setval(CAST(:sequence AS regclass),:value,true)'),
                                  {'sequence': sequence, 'value': max(row['id'] for row in rows)})


def column_names(engine, tables):
    return {name: tuple(Table(name, MetaData(), autoload_with=engine).c.keys()) for name in tables}


def snapshot(engine, tables, *, columns=None):
    with engine.connect() as connection:
        result = {}
        for name in tables:
            table = Table(name, MetaData(), autoload_with=connection)
            fields = columns[name] if columns else table.c.keys()
            query = select(*(table.c[field] for field in fields)).order_by(*table.primary_key.columns)
            result[name] = [dict(row) for row in connection.execute(query).mappings()]
        return result


def assert_guarded_downgrade(engine, revision):
    """Test the exact historical guard, without traversing later revisions.

    Always roll back even if a broken guard executed destructive DDL before the
    assertion failed. No stamp or migration history rewriting is involved.
    """
    assert revision in {'f75e841962a7', 'f17a20b30c41'}
    module = ScriptDirectory.from_config(Config('alembic.ini')).get_revision(revision).module
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Operations.context(MigrationContext.configure(connection)):
                with pytest.raises(RuntimeError, match='Cannot discard'):
                    module.downgrade()
        finally:
            transaction.rollback()
