from app import config
from app.db.connection import get_connection


def test_get_connection_resolves_relative_database_path_from_repo_root(monkeypatch, tmp_path):
    # DATABASE_PATH in .env is written relative to the repo root — this must
    # keep working even if the process is launched from some other cwd
    # (regression: it previously resolved relative to the process cwd instead).
    monkeypatch.setattr(config, "DATABASE_PATH", "backend/app/db/poursight.db")
    monkeypatch.chdir(tmp_path)

    conn = get_connection()
    try:
        assert tuple(conn.execute("SELECT 1").fetchone()) == (1,)
    finally:
        conn.close()


def test_get_connection_still_works_with_database_path_unset(monkeypatch):
    monkeypatch.setattr(config, "DATABASE_PATH", None)
    conn = get_connection()
    try:
        assert tuple(conn.execute("SELECT 1").fetchone()) == (1,)
    finally:
        conn.close()
