"""SQLite persistence with constrained schema and consistent connections."""
from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "nova.db"

def database_path():
    return Path(os.environ.get("NOVA_DB_PATH", str(DEFAULT_DB))).expanduser()

@contextmanager
def connect(path=None):
    target = Path(path) if path is not None else database_path()
    if str(target) != ":memory:":
        target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    phone TEXT,
    program TEXT NOT NULL,
    year INTEGER NOT NULL CHECK(year BETWEEN 1 AND 6),
    gpa REAL NOT NULL CHECK(gpa BETWEEN 0 AND 4),
    attendance INTEGER NOT NULL CHECK(attendance BETWEEN 0 AND 100),
    status TEXT NOT NULL CHECK(status IN ('Active','On leave','Graduated','Suspended')),
    enrolled_on TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_student_program ON students(program);
CREATE INDEX IF NOT EXISTS idx_student_status ON students(status);
CREATE INDEX IF NOT EXISTS idx_student_name ON students(last_name, first_name);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    student_name TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('created','updated','deleted','demo')),
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_time ON activity(created_at DESC);
"""

def initialize(path=None):
    with connect(path) as conn:
        conn.executescript(SCHEMA)
