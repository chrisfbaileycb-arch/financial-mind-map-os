"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from src import db
from src.db.seed import seed_database


@pytest.fixture()
def conn(tmp_path):
    """A migrated, empty database on a throwaway file."""
    path = tmp_path / "test.db"
    connection = db.get_connection(path)
    db.migrate(connection)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture()
def seeded_conn(tmp_path):
    """A database seeded with the sample household, pinned to a fixed date."""
    from datetime import date

    path = tmp_path / "seeded.db"
    connection = db.get_connection(path)
    seed_database(connection, today=date(2026, 6, 27))
    try:
        yield connection
    finally:
        connection.close()
