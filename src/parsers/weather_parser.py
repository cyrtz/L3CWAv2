"""Parser for Central Weather Administration (CWA) forecast JSON payloads."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
import pandas as pd

from src.models.weather import WeatherForecast
from src.utils.location_utils import normalize_region_name


class WeatherParser:
    """Parses various CWA JSON forecast formats into standard WeatherForecast objects."""

    @staticmethod
    def _extract_locations_list(records: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the list of location nodes regardless of dataset structure."""
        if not isinstance(records, dict):
            return []

        # Format 1: Direct 'location' list (e.g. F-C0032-001)
        if "location" in records and isinstance(records["location"], list):
            return records["location"]

        # Format 2: Nested under 'locations' list (e.g. F-D0047-089 / F-D0047-091)
        if "locations" in records and isinstance(records["locations"], list):
            all_locs: list[dict[str, Any]] = []
            for loc_group in records["locations"]:
                if isinstance(loc_group, dict) and "location" in loc_group:
                    sub_locs = loc_group.get("location", [])
                    if isinstance(sub_locs, list):
                        all_locs.extend(sub_locs)
            return all_locs

        return []

    @staticmethod
    def _extract_element_value(time_node: dict[str, Any]) -> str | None:
        """Extract scalar value from a time node across different CWA schema flavors."""
        if not isinstance(time_node, dict):
            return None

        # Schema flavor A: 'parameter' object
        param = time_node.get("parameter")
        if isinstance(param, dict) and "parameterName" in param:
            return str(param["parameterName"]).strip()

        # Schema flavor B: 'elementValue' list
        elem_val = time_node.get("elementValue")
        if isinstance(elem_val, list) and len(elem_val) > 0:
            first = elem_val[0]
            if isinstance(first, dict):
                return str(first.get("value", "")).strip()
            return str(first).strip()

        return None

    @classmethod
    def parse_cwa_json(cls, payload: dict[str, Any]) -> list[WeatherForecast]:
        """Parse raw CWA JSON payload into a list of standardized WeatherForecast objects.

        Args:
            payload: JSON dictionary returned by CWA API.

        Returns:
            list of WeatherForecast instances, aggregated per region per calendar day.
        """
        if not payload or not isinstance(payload, dict):
            return []

        records = payload.get("records")
        if not isinstance(records, dict):
            return []

        locations = cls._extract_locations_list(records)
        forecasts: list[WeatherForecast] = []

        for loc in locations:
            raw_name = loc.get("locationName") or loc.get("regionName") or ""
            region_name = normalize_region_name(raw_name)
            if not region_name:
                continue

            elements = loc.get("weatherElement")
            if not isinstance(elements, list):
                continue

            # Group daily values: { date_str: { "min_temps": [...], "max_temps": [...], "wx": [...], "pop": [...] } }
            daily_aggregates: dict[str, dict[str, list[Any]]] = defaultdict(
                lambda: {"min_temps": [], "max_temps": [], "wx": [], "pop": []}
            )

            for elem in elements:
                if not isinstance(elem, dict):
                    continue
                elem_name = elem.get("elementName", "").strip()
                time_list = elem.get("time", [])
                if not isinstance(time_list, list):
                    continue

                for t_node in time_list:
                    start_time = t_node.get("startTime") or t_node.get("dataTime") or ""
                    if not start_time or len(start_time) < 10:
                        continue
                    # Extract YYYY-MM-DD
                    date_str = start_time[:10]
                    raw_val = cls._extract_element_value(t_node)
                    if raw_val is None or raw_val == "":
                        continue

                    if elem_name in ("MinT", "minT", "MIN_T"):
                        try:
                            daily_aggregates[date_str]["min_temps"].append(float(raw_val))
                        except (ValueError, TypeError):
                            pass
                    elif elem_name in ("MaxT", "maxT", "MAX_T"):
                        try:
                            daily_aggregates[date_str]["max_temps"].append(float(raw_val))
                        except (ValueError, TypeError):
                            pass
                    elif elem_name in ("Wx", "wx", "Weather"):
                        daily_aggregates[date_str]["wx"].append(raw_val)
                    elif elem_name in ("PoP", "PoP12h", "pop"):
                        try:
                            daily_aggregates[date_str]["pop"].append(int(raw_val))
                        except (ValueError, TypeError):
                            pass

            for date_str, values in daily_aggregates.items():
                min_temp = min(values["min_temps"]) if values["min_temps"] else None
                max_temp = max(values["max_temps"]) if values["max_temps"] else None

                # Both or at least one temperature is required for a meaningful forecast
                if min_temp is None and max_temp is None:
                    continue

                # Ensure min_temp <= max_temp if both are present
                if min_temp is not None and max_temp is not None and min_temp > max_temp:
                    min_temp, max_temp = max_temp, min_temp

                condition = values["wx"][0] if values["wx"] else None
                pop_val = max(values["pop"]) if values["pop"] else None

                forecasts.append(
                    WeatherForecast(
                        region_name=region_name,
                        data_date=date_str,
                        min_temp=min_temp,
                        max_temp=max_temp,
                        weather_condition=condition,
                        pop=pop_val,
                    )
                )

        return forecasts

    @classmethod
    def to_dataframe(cls, forecasts: list[WeatherForecast]) -> pd.DataFrame:
        """Convert a list of WeatherForecast objects into a clean, typed Pandas DataFrame.

        DataFrame schema:
        - region_name: str
        - data_date: str (YYYY-MM-DD)
        - min_temp: float
        - max_temp: float
        - weather_condition: str (optional)
        - pop: int or None
        - avg_temp: float
        """
        if not forecasts:
            return pd.DataFrame(
                columns=[
                    "region_name",
                    "data_date",
                    "min_temp",
                    "max_temp",
                    "weather_condition",
                    "pop",
                    "avg_temp",
                ]
            )

        rows = [f.to_dict() for f in forecasts]
        df = pd.DataFrame(rows)

        # Type conversion & cleaning
        df["region_name"] = df["region_name"].astype(str)
        df["data_date"] = pd.to_datetime(df["data_date"]).dt.strftime("%Y-%m-%d")
        df["min_temp"] = pd.to_numeric(df["min_temp"], errors="coerce")
        df["max_temp"] = pd.to_numeric(df["max_temp"], errors="coerce")

        # Deduplicate on region_name and data_date
        df = df.drop_duplicates(subset=["region_name", "data_date"], keep="last")

        # Sort chronologically by date, then alphabetically by region
        df = df.sort_values(by=["data_date", "region_name"]).reset_index(drop=True)

        return df
