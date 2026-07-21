"""Tests for the query engine's safety layer.

Runs against the real seeded dataset (deterministic, RANDOM_SEED=42 in seed.py)
rather than a fixture DB, since the whole point is to prove the whitelist and
authorizer hold up against the actual schema.
"""

import sqlite3

import pytest

from app.db.connection import get_connection
from app.db.query_engine import ALLOWED_TABLES, MAX_ROWS, QueryValidationError, run_query


def test_valid_query_returns_rows():
    result = run_query(
        "SELECT name, category, price_usd FROM menu_items WHERE category = ?", ("Beer",)
    )
    assert result.row_count == 16
    assert all(row["category"] == "Beer" for row in result.rows)
    assert result.columns == ["name", "category", "price_usd"]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE orders;",
        "DELETE FROM orders",
        "INSERT INTO orders (order_id) VALUES (999999)",
        "PRAGMA table_info(orders)",
        "ATTACH DATABASE 'x.db' AS evil",
        "",
        "   ",
    ],
)
def test_rejected_before_reaching_sqlite(sql):
    with pytest.raises(QueryValidationError):
        run_query(sql)


def test_count_star_is_allowed_on_a_whitelisted_table():
    # COUNT(*) triggers an internal rowid-only read with an empty column name,
    # not a real column - regression test for that authorizer edge case.
    result = run_query("SELECT COUNT(*) AS n FROM orders")
    assert result.rows[0]["n"] > 0


def test_authorizer_denies_unlisted_table():
    # Passes the text-level check (starts with SELECT), must be caught by the authorizer.
    with pytest.raises(sqlite3.DatabaseError):
        run_query("SELECT * FROM sqlite_master")


def test_authorizer_denies_unknown_function():
    with pytest.raises(sqlite3.DatabaseError):
        run_query("SELECT load_extension('x') FROM orders")


def test_truncates_at_max_rows():
    result = run_query("SELECT * FROM order_items")
    assert result.row_count == MAX_ROWS
    assert result.truncated is True


def test_whitelist_matches_live_schema():
    conn = get_connection()
    try:
        for table, expected_columns in ALLOWED_TABLES.items():
            actual_columns = {
                row["name"] for row in conn.execute(f"PRAGMA table_info({table})")
            }
            assert actual_columns == expected_columns, (
                f"{table}: whitelist {expected_columns} != schema {actual_columns}"
            )
    finally:
        conn.close()
