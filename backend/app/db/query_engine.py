"""The only path by which generated SQL is allowed to touch the database.

Three independent layers, so a bug in any one of them isn't enough on its own
to run something unintended:
  1. Text-level check: must be a single read-only statement.
  2. SQLite authorizer: every table/column/function touched is checked against
     an explicit whitelist as the statement compiles.
  3. The connection itself is opened read-only at the OS/SQLite level
     (see connection.py) - writes fail even if 1 and 2 are bypassed.

Every question the LLM turns into SQL runs through `run_query()`.
"""

import sqlite3
from dataclasses import dataclass, field

from app.db.connection import get_connection

MAX_ROWS = 500

# Column names as they appear in schema.sql. This is the single source of
# truth for what a generated query is allowed to touch - kept in sync with
# the schema by tests/test_query_engine.py, not by introspecting it live.
ALLOWED_TABLES: dict[str, set[str]] = {
    "menu_items": {"item_id", "name", "category", "price_usd", "cost_usd", "is_active"},
    "ingredients": {"ingredient_id", "name", "unit", "unit_cost_usd", "stock_on_hand", "reorder_level"},
    "recipe_items": {"item_id", "ingredient_id", "quantity_per_serving"},
    "fx_rates": {"rate_date", "usd_to_zwg"},
    "match_days": {"match_date", "opponent", "is_home", "competition", "kickoff_local"},
    "orders": {
        "order_id", "order_datetime", "day_of_week", "is_weekend",
        "is_match_day", "payment_method", "currency", "table_number",
    },
    "order_items": {"order_item_id", "order_id", "item_id", "quantity", "unit_price_usd", "line_total_usd"},
}

ALLOWED_FUNCTIONS = {
    "count", "sum", "avg", "min", "max", "round", "abs", "coalesce", "ifnull", "nullif",
    "date", "datetime", "strftime", "julianday", "cast", "length", "upper", "lower",
    "trim", "printf", "group_concat", "total", "like", "glob",
}


class QueryValidationError(Exception):
    """Raised when generated SQL fails validation before ever reaching SQLite."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool = False
    error: str | None = field(default=None)


def _check_single_read_statement(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise QueryValidationError("Empty query.")
    if ";" in stripped:
        raise QueryValidationError("Only a single statement is allowed.")
    first_word = stripped.split(None, 1)[0].lower()
    if first_word not in ("select", "with"):
        raise QueryValidationError("Only SELECT (or SELECT via WITH) statements are allowed.")
    return stripped


def _authorizer(action, arg1, arg2, dbname, source):  # noqa: ANN001 - fixed sqlite3 callback signature
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        table, column = arg1, arg2
        allowed_columns = ALLOWED_TABLES.get(table)
        if not allowed_columns:
            return sqlite3.SQLITE_DENY
        # COUNT(*) and similar don't touch a specific column - SQLite reports an
        # empty column name for that internal rowid-only read. The table is
        # already fully whitelisted, so this exposes nothing beyond "a row exists".
        if column in allowed_columns or column == "":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        func_name = (arg2 or "").lower()
        if func_name in ALLOWED_FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    # Default-deny everything else: writes, PRAGMA, ATTACH, DDL, triggers, etc.
    return sqlite3.SQLITE_DENY


def run_query(sql: str, params: tuple | dict = ()) -> QueryResult:
    """Validate and execute a single read-only, whitelisted query.

    Raises QueryValidationError for anything rejected before it reaches SQLite.
    SQLite-level denials (caught by the authorizer) surface as sqlite3.DatabaseError.
    """
    statement = _check_single_read_statement(sql)

    conn = get_connection()
    conn.set_authorizer(_authorizer)
    try:
        cursor = conn.execute(statement, params)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(MAX_ROWS + 1)
        truncated = len(rows) > MAX_ROWS
        rows = rows[:MAX_ROWS]
        return QueryResult(
            columns=columns,
            rows=[dict(row) for row in rows],
            row_count=len(rows),
            truncated=truncated,
        )
    finally:
        conn.close()
