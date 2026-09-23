"""Helper for generating standardized CWA mock payloads covering all 22 Taiwan regions."""

from __future__ import annotations

import datetime
from typing import Any
from src.data.taiwan_locations import TAIWAN_COORDINATES
from src.models.weather import WeatherForecast
from src.parsers.weather_parser import WeatherParser


def generate_cwa_mock_payload() -> dict[str, Any]:
    """Generate a realistic CWA API F-C0032 structure payload for all 22 administrative regions.

    This ensures that when an API key is not yet provided, the exact same CWA parsing pipeline
    can be verified across every single Taiwan region and date.
    """
    today = datetime.date.today()
    dates = [today + datetime.timedelta(days=i) for i in range(7)]

    # Base temperature offsets for realistic geographic temperature distribution
    # (Northern regions slightly cooler, Southern regions warmer)
    base_temps: dict[str, tuple[float, float]] = {
        "基隆市": (22.0, 27.0),
        "臺北市": (23.0, 30.0),
        "新北市": (22.5, 29.5),
        "桃園市": (23.0, 29.0),
        "新竹市": (23.5, 29.0),
        "新竹縣": (22.0, 28.5),
        "苗栗縣": (22.5, 29.0),
        "臺中市": (24.0, 31.5),
        "彰化縣": (24.0, 31.0),
        "南投縣": (21.5, 29.0),
        "雲林縣": (24.5, 31.0),
        "嘉義市": (24.0, 31.5),
        "嘉義縣": (24.0, 31.0),
        "臺南市": (25.0, 32.0),
        "高雄市": (26.0, 33.0),
        "屏東縣": (25.5, 33.0),
        "宜蘭縣": (22.0, 27.5),
        "花蓮縣": (23.0, 28.5),
        "臺東縣": (24.5, 30.0),
        "澎湖縣": (25.0, 30.5),
        "金門縣": (22.5, 28.0),
        "連江縣": (19.0, 24.5),
    }

    locations_list: list[dict[str, Any]] = []

    for region_name in TAIWAN_COORDINATES.keys():
        min_base, max_base = base_temps.get(region_name, (23.0, 29.0))

        maxt_times = []
        mint_times = []
        wx_times = []
        pop_times = []

        weather_descriptions = ["晴時多雲", "多雲短暫雨", "晴天", "陰時多雲", "多雲"]

        for idx, dt in enumerate(dates):
            date_str = dt.strftime("%Y-%m-%d")
            start_time = f"{date_str} 06:00:00"
            end_time = f"{date_str} 18:00:00"

            # slight daily variance
            variation = (idx % 3) * 0.7 - 0.5
            d_min = round(min_base + variation, 0)
            d_max = round(max_base + variation, 0)

            maxt_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "parameter": {"parameterName": str(int(d_max)), "parameterUnit": "C"},
            })
            mint_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "parameter": {"parameterName": str(int(d_min)), "parameterUnit": "C"},
            })
            wx_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "parameter": {"parameterName": weather_descriptions[idx % len(weather_descriptions)], "parameterValue": "2"},
            })
            pop_times.append({
                "startTime": start_time,
                "endTime": end_time,
                "parameter": {"parameterName": str((idx * 15) % 60), "parameterUnit": "百分比"},
            })

        locations_list.append({
            "locationName": region_name,
            "weatherElement": [
                {"elementName": "MaxT", "time": maxt_times},
                {"elementName": "MinT", "time": mint_times},
                {"elementName": "Wx", "time": wx_times},
                {"elementName": "PoP", "time": pop_times},
            ],
        })

    return {
        "success": "true",
        "result": {"resource_id": "F-C0032-001"},
        "records": {
            "datasetDescription": "全臺各縣市天氣預報模擬測試資料",
            "location": locations_list,
        },
    }


def seed_database_with_sample_cwa_data(repository) -> int:
    """Parse simulated official CWA JSON and upsert to database."""
    payload = generate_cwa_mock_payload()
    forecasts = WeatherParser.parse_cwa_json(payload)
    return repository.save_weather_data(forecasts)
