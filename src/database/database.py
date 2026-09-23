"""SQLite database connection and schema lifecycle management."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import sqlite3
from typing import Generator

from src.config.settings import get_settings


class DatabaseManager:
    """Manages SQLite connections and table schema initialization."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is not None:
            self._db_path = str(db_path)
        else:
            settings = get_settings()
            self._db_path = str(settings.full_database_path)

        self._shared_conn: sqlite3.Connection | None = None
        if self._db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")

    @property
    def db_path(self) -> str:
        """Get database path string."""
        return self._db_path

    def get_connection(self) -> sqlite3.Connection:
        """Create or retrieve SQLite connection with foreign keys enabled and Row factory."""
        if self._db_path == ":memory:":
            return self._shared_conn

        # Ensure directory exists for physical file databases
        target_dir = Path(self._db_path).parent
        target_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextlib.contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an atomic database transaction with auto-commit/rollback."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._db_path != ":memory:":
                conn.close()

    def close(self) -> None:
        """Close shared connection if any."""
        if self._shared_conn is not None:
            self._shared_conn.close()
            self._shared_conn = None

    def init_database(self) -> None:
        """Initialize required database tables and indices if they do not exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS temperature_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT NOT NULL,
            data_date TEXT NOT NULL,
            min_temp REAL,
            max_temp REAL,
            weather_condition TEXT,
            pop INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(region_name, data_date)
        );
        """

        create_region_idx = """
        CREATE INDEX IF NOT EXISTS idx_forecast_region_date
        ON temperature_forecasts (region_name, data_date);
        """

        create_date_idx = """
        CREATE INDEX IF NOT EXISTS idx_forecast_date
        ON temperature_forecasts (data_date);
        """

        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            cursor.execute(create_region_idx)
            cursor.execute(create_date_idx)
