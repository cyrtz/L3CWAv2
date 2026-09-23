"""Unit tests for WeatherParser and schema transformation."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pandas as pd

from src.models.weather import WeatherForecast
from src.parsers.weather_parser import WeatherParser


@pytest.fixture
def mock_fc0032_payload() -> dict:
    """Load mock CWA F-C0032 payload."""
    fixture_path = Path(__file__).parent / "fixtures" / "mock_cwa_fc0032.json"
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


def test_parse_valid_fc0032_json(mock_fc0032_payload: dict) -> None:
    """Verify parsing of valid CWA F-C0032 format into WeatherForecast objects."""
    forecasts = WeatherParser.parse_cwa_json(mock_fc0032_payload)
    assert len(forecasts) > 0

    # Check Taipei records
    taipei_records = [f for f in forecasts if f.region_name == "臺北市"]
    assert len(taipei_records) >= 1

    first = taipei_records[0]
    assert first.region_name == "臺北市"
    assert first.min_temp is not None
    assert first.max_temp is not None
    assert first.min_temp <= first.max_temp
    assert first.avg_temp is not None


def test_parse_nested_locations_format() -> None:
    """Verify parser correctly handles F-D0047 nested 'locations' -> 'location' structure."""
    nested_payload = {
        "records": {
            "locations": [
                {
                    "datasetDescription": "未來一週天氣預報",
                    "location": [
                        {
                            "locationName": "新北市",
                            "weatherElement": [
                                {
                                    "elementName": "MinT",
                                    "time": [
                                        {
                                            "startTime": "2026-09-24 00:00:00",
                                            "elementValue": [{"value": "22", "measures": "攝氏度"}],
                                        }
                                    ],
                                },
                                {
                                    "elementName": "MaxT",
                                    "time": [
                                        {
                                            "startTime": "2026-09-24 00:00:00",
                                            "elementValue": [{"value": "28", "measures": "攝氏度"}],
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    }
    forecasts = WeatherParser.parse_cwa_json(nested_payload)
    assert len(forecasts) == 1
    assert forecasts[0].region_name == "新北市"
    assert forecasts[0].min_temp == 22.0
    assert forecasts[0].max_temp == 28.0
    assert forecasts[0].avg_temp == 25.0


def test_parse_empty_payload() -> None:
    """Verify parser returns an empty list when given empty or null payloads."""
    assert WeatherParser.parse_cwa_json({}) == []
    assert WeatherParser.parse_cwa_json({"records": {}}) == []
    assert WeatherParser.parse_cwa_json({"records": {"location": []}}) == []


def test_parse_missing_mint() -> None:
    """Verify parser handles records with missing MinT gracefully."""
    payload = {
        "records": {
            "location": [
                {
                    "locationName": "臺南市",
                    "weatherElement": [
                        {
                            "elementName": "MaxT",
                            "time": [
                                {
                                    "startTime": "2026-09-24 06:00:00",
                                    "parameter": {"parameterName": "32"},
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    forecasts = WeatherParser.parse_cwa_json(payload)
    assert len(forecasts) == 1
    assert forecasts[0].region_name == "臺南市"
    assert forecasts[0].min_temp is None
    assert forecasts[0].max_temp == 32.0
    assert forecasts[0].avg_temp == 32.0


def test_parse_missing_maxt() -> None:
    """Verify parser handles records with missing MaxT gracefully."""
    payload = {
        "records": {
            "location": [
                {
                    "locationName": "宜蘭縣",
                    "weatherElement": [
                        {
                            "elementName": "MinT",
                            "time": [
                                {
                                    "startTime": "2026-09-24 06:00:00",
                                    "parameter": {"parameterName": "21"},
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    }
    forecasts = WeatherParser.parse_cwa_json(payload)
    assert len(forecasts) == 1
    assert forecasts[0].region_name == "宜蘭縣"
    assert forecasts[0].min_temp == 21.0
    assert forecasts[0].max_temp is None
    assert forecasts[0].avg_temp == 21.0


def test_to_dataframe_transformation() -> None:
    """Verify to_dataframe produces properly typed, deduplicated, sorted DataFrames."""
    forecasts = [
        WeatherForecast("高雄市", "2026-09-25", 25.0, 32.0),
        WeatherForecast("臺北市", "2026-09-24", 23.0, 29.0),
        WeatherForecast("高雄市", "2026-09-24", 24.0, 31.0),
        # Duplicate with updated value
        WeatherForecast("臺北市", "2026-09-24", 22.0, 30.0),
    ]

    df = WeatherParser.to_dataframe(forecasts)
    assert isinstance(df, pd.DataFrame)
    # Duplicate removed
    assert len(df) == 3

    # Check sorting: 2026-09-24 comes before 2026-09-25
    assert df.iloc[0]["data_date"] == "2026-09-24"
    assert df.iloc[-1]["data_date"] == "2026-09-25"

    # Last occurrence kept for duplicate
    taipei_0924 = df[(df["region_name"] == "臺北市") & (df["data_date"] == "2026-09-24")].iloc[0]
    assert taipei_0924["min_temp"] == 22.0
    assert taipei_0924["max_temp"] == 30.0
