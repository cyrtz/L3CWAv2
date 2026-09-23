"""Weather forecast domain models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class WeatherForecast:
    """Represents a standardized daily weather forecast for a region."""

    region_name: str
    data_date: str
    min_temp: float | None
    max_temp: float | None
    weather_condition: str | None = None
    pop: int | None = None

    @property
    def avg_temp(self) -> float | None:
        """Calculate the average temperature if both min and max are available."""
        if self.min_temp is not None and self.max_temp is not None:
            return round((self.min_temp + self.max_temp) / 2.0, 1)
        if self.min_temp is not None:
            return self.min_temp
        if self.max_temp is not None:
            return self.max_temp
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert forecast model to dictionary."""
        data = asdict(self)
        data["avg_temp"] = self.avg_temp
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeatherForecast:
        """Create a WeatherForecast instance from a dictionary."""
        return cls(
            region_name=data["region_name"],
            data_date=str(data["data_date"]),
            min_temp=float(data["min_temp"]) if data.get("min_temp") is not None else None,
            max_temp=float(data["max_temp"]) if data.get("max_temp") is not None else None,
            weather_condition=data.get("weather_condition"),
            pop=int(data["pop"]) if data.get("pop") is not None else None,
        )
