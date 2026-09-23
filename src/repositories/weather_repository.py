"""Repository layer for weather forecast persistence and parameterized queries."""

from __future__ import annotations

from typing import Any
import pandas as pd

from src.database.database import DatabaseManager
from src.models.weather import WeatherForecast


class WeatherRepository:
    """Provides abstracted data-access operations on the SQLite weather store."""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        self.db = db_manager or DatabaseManager()
        # Ensure schema is ready
        self.db.init_database()

    def save_weather_data(self, data: list[WeatherForecast] | pd.DataFrame) -> int:
        """Insert or update weather forecast records using SQLite UPSERT.

        Args:
            data: A list of WeatherForecast domain objects or a Pandas DataFrame.

        Returns:
            Number of records processed.
        """
        records: list[tuple[str, str, float | None, float | None, str | None, int | None]] = []

        if isinstance(data, pd.DataFrame):
            for _, row in data.iterrows():
                min_t = float(row["min_temp"]) if pd.notna(row.get("min_temp")) else None
                max_t = float(row["max_temp"]) if pd.notna(row.get("max_temp")) else None
                cond = str(row["weather_condition"]) if pd.notna(row.get("weather_condition")) else None
                pop_val = int(row["pop"]) if pd.notna(row.get("pop")) else None

                records.append(
                    (
                        str(row["region_name"]),
                        str(row["data_date"]),
                        min_t,
                        max_t,
                        cond,
                        pop_val,
                    )
                )
        else:
            for item in data:
                records.append(
                    (
                        item.region_name,
                        item.data_date,
                        item.min_temp,
                        item.max_temp,
                        item.weather_condition,
                        item.pop,
                    )
                )

        if not records:
            return 0

        upsert_sql = """
        INSERT INTO temperature_forecasts (
            region_name,
            data_date,
            min_temp,
            max_temp,
            weather_condition,
            pop,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(region_name, data_date) DO UPDATE SET
            min_temp = excluded.min_temp,
            max_temp = excluded.max_temp,
            weather_condition = excluded.weather_condition,
            pop = excluded.pop,
            updated_at = CURRENT_TIMESTAMP;
        """

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.executemany(upsert_sql, records)
            return len(records)

    def get_regions(self) -> list[str]:
        """Fetch a distinct, sorted list of all available region names."""
        query = """
        SELECT DISTINCT region_name
        FROM temperature_forecasts
        ORDER BY region_name ASC;
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query).fetchall()
            return [row["region_name"] for row in rows]

    def get_dates(self) -> list[str]:
        """Fetch a distinct, chronologically sorted list of all available forecast dates."""
        query = """
        SELECT DISTINCT data_date
        FROM temperature_forecasts
        ORDER BY data_date ASC;
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query).fetchall()
            return [row["data_date"] for row in rows]

    def get_weather_by_region(self, region_name: str) -> pd.DataFrame:
        """Fetch all chronological forecasts for a specific region.

        Args:
            region_name: The target county/city name.

        Returns:
            Pandas DataFrame containing forecast history and future predictions.
        """
        query = """
        SELECT
            region_name,
            data_date,
            min_temp,
            max_temp,
            weather_condition,
            pop,
            updated_at
        FROM temperature_forecasts
        WHERE region_name = ?
        ORDER BY data_date ASC;
        """
        with self.db.transaction() as conn:
            df = pd.read_sql_query(query, conn, params=[region_name])
            if not df.empty:
                df["avg_temp"] = (df["min_temp"] + df["max_temp"]) / 2.0
            return df

    def get_weather_by_date(self, data_date: str) -> pd.DataFrame:
        """Fetch forecasts across all regions for a specified calendar date.

        Args:
            data_date: Target date string in 'YYYY-MM-DD' format.

        Returns:
            Pandas DataFrame containing forecasts for all regions on that date.
        """
        query = """
        SELECT
            region_name,
            data_date,
            min_temp,
            max_temp,
            weather_condition,
            pop,
            updated_at
        FROM temperature_forecasts
        WHERE data_date = ?
        ORDER BY region_name ASC;
        """
        with self.db.transaction() as conn:
            df = pd.read_sql_query(query, conn, params=[data_date])
            if not df.empty:
                df["avg_temp"] = (df["min_temp"] + df["max_temp"]) / 2.0
            return df

    def get_weather_by_region_and_date(
        self, region_name: str, data_date: str
    ) -> dict[str, Any] | None:
        """Fetch a single forecast record for a given region and date.

        Args:
            region_name: The region name.
            data_date: The date string.

        Returns:
            dict containing record fields, or None if not found.
        """
        query = """
        SELECT
            region_name,
            data_date,
            min_temp,
            max_temp,
            weather_condition,
            pop,
            updated_at
        FROM temperature_forecasts
        WHERE region_name = ? AND data_date = ?
        LIMIT 1;
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            row = cursor.execute(query, [region_name, data_date]).fetchone()
            if row:
                result = dict(row)
                if result["min_temp"] is not None and result["max_temp"] is not None:
                    result["avg_temp"] = round(
                        (result["min_temp"] + result["max_temp"]) / 2.0, 1
                    )
                return result
            return None

    def get_all_weather(self) -> pd.DataFrame:
        """Fetch all stored weather forecasts.

        Returns:
            Pandas DataFrame of the entire dataset.
        """
        query = """
        SELECT
            region_name,
            data_date,
            min_temp,
            max_temp,
            weather_condition,
            pop,
            updated_at
        FROM temperature_forecasts
        ORDER BY data_date ASC, region_name ASC;
        """
        with self.db.transaction() as conn:
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                df["avg_temp"] = (df["min_temp"] + df["max_temp"]) / 2.0
            return df

    def get_latest_update_time(self) -> str | None:
        """Fetch the most recent updated_at timestamp in the database."""
        query = """
        SELECT MAX(updated_at) AS latest_time
        FROM temperature_forecasts;
        """
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            row = cursor.execute(query).fetchone()
            if row and row["latest_time"]:
                return str(row["latest_time"])
            return None

    def get_record_count(self) -> int:
        """Count total forecast records in the database."""
        query = "SELECT COUNT(*) AS total FROM temperature_forecasts;"
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            row = cursor.execute(query).fetchone()
            return int(row["total"]) if row else 0

    def clear_all(self) -> None:
        """Clear all records from temperature_forecasts table (primarily for testing)."""
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM temperature_forecasts;")
