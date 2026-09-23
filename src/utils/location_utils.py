"""Utility functions for Taiwan location name normalization and coordinates."""

from __future__ import annotations

from src.data.taiwan_locations import TAIWAN_COORDINATES, load_taiwan_locations

# Cache coordinates map
_LOCATIONS_MAP = load_taiwan_locations()

# Known county aliases (e.g. shorthand without 市/縣 or common variations)
_NAME_ALIASES: dict[str, str] = {
    "台北": "臺北市",
    "臺北": "臺北市",
    "新北": "新北市",
    "基隆": "基隆市",
    "桃園": "桃園市",
    "新竹": "新竹市",
    "苗栗": "苗栗縣",
    "台中": "臺中市",
    "臺中": "臺中市",
    "彰化": "彰化縣",
    "南投": "南投縣",
    "雲林": "雲林縣",
    "嘉義": "嘉義市",
    "台南": "臺南市",
    "臺南": "臺南市",
    "高雄": "高雄市",
    "屏東": "屏東縣",
    "宜蘭": "宜蘭縣",
    "花蓮": "花蓮縣",
    "台東": "臺東縣",
    "臺東": "臺東縣",
    "澎湖": "澎湖縣",
    "金門": "金門縣",
    "連江": "連江縣",
    "馬祖": "連江縣",
}


def normalize_region_name(name: str) -> str:
    """Normalize a Taiwan region name by converting '台' to '臺' and resolving aliases.

    Examples:
        >>> normalize_region_name("台北市")
        '臺北市'
        >>> normalize_region_name(" 台中市 ")
        '臺中市'
        >>> normalize_region_name("高雄")
        '高雄市'
    """
    if not name:
        return ""

    cleaned = name.strip()
    # Normalize '台' to '臺'
    cleaned = cleaned.replace("台", "臺")

    # If it's already one of the canonical 22 regions
    if cleaned in _LOCATIONS_MAP:
        return cleaned

    # Check aliases
    if cleaned in _NAME_ALIASES:
        return _NAME_ALIASES[cleaned]

    return cleaned


def get_location_coordinates(region_name: str) -> tuple[float, float] | None:
    """Get the latitude and longitude for a region.

    Args:
        region_name: Administrative region name (e.g. '臺北市' or '台北市')

    Returns:
        tuple[float, float] of (latitude, longitude) or None if not found.
    """
    normalized = normalize_region_name(region_name)
    info = _LOCATIONS_MAP.get(normalized)
    if info:
        return (float(info["lat"]), float(info["lon"]))
    return None
