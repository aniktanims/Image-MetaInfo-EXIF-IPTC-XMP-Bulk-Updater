import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable

from .config import DB_PATH


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                write_mode TEXT NOT NULL,
                output_folder TEXT,
                total_files INTEGER NOT NULL,
                processed_files INTEGER NOT NULL,
                failed_files INTEGER NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS job_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                output_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS unresolved_failures (
                file_path TEXT PRIMARY KEY,
                last_error TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                resolved INTEGER NOT NULL DEFAULT 0,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


@contextmanager
def get_connection() -> Iterable[sqlite3.Connection]:
    connection = sqlite3.connect(DB_PATH)
    try:
        yield connection
    finally:
        connection.close()


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")
