"""Unit tests for SQLite WeatherRepository operations."""

from __future__ import annotations

import pytest
import pandas as pd

from src.database.database import DatabaseManager
from src.models.weather import WeatherForecast
from src.repositories.weather_repository import WeatherRepository


@pytest.fixture
def in_memory_repo() -> WeatherRepository:
    """Provide a fresh WeatherRepository using an in-memory SQLite database."""
    db_mgr = DatabaseManager(db_path=":memory:")
    return WeatherRepository(db_manager=db_mgr)


def test_table_initialization(in_memory_repo: WeatherRepository) -> None:
    """Verify that temperature_forecasts table is initialized and empty."""
    assert in_memory_repo.get_record_count() == 0
    assert in_memory_repo.get_regions() == []
    assert in_memory_repo.get_dates() == []


def test_insert_and_select_by_region(in_memory_repo: WeatherRepository) -> None:
    """Verify inserting forecasts and querying by region."""
    records = [
        WeatherForecast("臺北市", "2026-09-24", 22.0, 29.0, "多雲", 20),
        WeatherForecast("臺北市", "2026-09-25", 23.0, 30.0, "晴天", 10),
        WeatherForecast("高雄市", "2026-09-24", 25.0, 32.0, "晴時多雲", 0),
    ]

    inserted = in_memory_repo.save_weather_data(records)
    assert inserted == 3
    assert in_memory_repo.get_record_count() == 3

    # Query by region
    taipei_df = in_memory_repo.get_weather_by_region("臺北市")
    assert len(taipei_df) == 2
    assert list(taipei_df["data_date"]) == ["2026-09-24", "2026-09-25"]
    assert taipei_df.iloc[0]["avg_temp"] == 25.5

    # Query distinct regions
    regions = in_memory_repo.get_regions()
    assert sorted(regions) == ["臺北市", "高雄市"]


def test_upsert_behavior(in_memory_repo: WeatherRepository) -> None:
    """Verify that re-inserting with the same region and date updates existing data without duplicate rows."""
    initial = [
        WeatherForecast("臺中市", "2026-09-24", 20.0, 28.0, "多雲", 30),
    ]
    in_memory_repo.save_weather_data(initial)
    assert in_memory_repo.get_record_count() == 1

    updated = [
        # Updated temperature values and weather condition
        WeatherForecast("臺中市", "2026-09-24", 21.5, 30.0, "晴時多雲", 15),
    ]
    in_memory_repo.save_weather_data(updated)

    # Count must remain 1
    assert in_memory_repo.get_record_count() == 1

    record = in_memory_repo.get_weather_by_region_and_date("臺中市", "2026-09-24")
    assert record is not None
    assert record["min_temp"] == 21.5
    assert record["max_temp"] == 30.0
    assert record["weather_condition"] == "晴時多雲"
    assert record["pop"] == 15


def test_select_by_date(in_memory_repo: WeatherRepository) -> None:
    """Verify querying all regions on a specific date."""
    records = [
        WeatherForecast("基隆市", "2026-09-24", 21.0, 26.0),
        WeatherForecast("臺南市", "2026-09-24", 24.0, 31.0),
        WeatherForecast("基隆市", "2026-09-25", 22.0, 27.0),
    ]
    in_memory_repo.save_weather_data(records)

    df_24 = in_memory_repo.get_weather_by_date("2026-09-24")
    assert len(df_24) == 2
    assert sorted(list(df_24["region_name"])) == ["基隆市", "臺南市"]

    df_empty = in_memory_repo.get_weather_by_date("2026-12-31")
    assert df_empty.empty


def test_save_from_dataframe(in_memory_repo: WeatherRepository) -> None:
    """Verify that save_weather_data can accept a Pandas DataFrame."""
    df = pd.DataFrame([
        {
            "region_name": "花蓮縣",
            "data_date": "2026-09-24",
            "min_temp": 22.0,
            "max_temp": 28.0,
            "weather_condition": "陰天",
            "pop": 40,
        }
    ])
    saved = in_memory_repo.save_weather_data(df)
    assert saved == 1
    record = in_memory_repo.get_weather_by_region_and_date("花蓮縣", "2026-09-24")
    assert record is not None
    assert record["region_name"] == "花蓮縣"
    assert record["min_temp"] == 22.0
