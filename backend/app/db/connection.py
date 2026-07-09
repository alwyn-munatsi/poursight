"""Read-only connection factory for the PourSight SQLite database.

Opening the file in SQLite's URI read-only mode is the outermost safety net:
even if the query-text checks or the authorizer in query_engine.py had a bug,
the database file itself cannot be written to over this connection.
"""

import sqlite3
from pathlib import Path

from app import config

DEFAULT_DB_PATH = Path(__file__).parent / "poursight.db"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    raw_path = db_path or config.DATABASE_PATH
    if raw_path:
        # DATABASE_PATH in .env is written relative to the repo root, not
        # whatever directory the process happens to be launched from.
        path = Path(raw_path)
        if not path.is_absolute():
            path = config.REPO_ROOT / path
    else:
        path = DEFAULT_DB_PATH

    if not path.exists():
        raise FileNotFoundError(f"Database not found at {path}. Run `python -m app.db.seed` first.")

    uri = f"file:{path.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn
