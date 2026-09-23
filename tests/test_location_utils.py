"""Unit tests for location normalization and geographic coordinates."""

from __future__ import annotations

from src.data.taiwan_locations import TAIWAN_COORDINATES
from src.utils.location_utils import get_location_coordinates, normalize_region_name


def test_normalize_region_name() -> None:
    """Verify conversion of '台' to '臺' and alias resolution."""
    assert normalize_region_name("台北市") == "臺北市"
    assert normalize_region_name("台中市") == "臺中市"
    assert normalize_region_name("台南市") == "臺南市"
    assert normalize_region_name("台東縣") == "臺東縣"
    assert normalize_region_name(" 台北市 ") == "臺北市"
    assert normalize_region_name("高雄") == "高雄市"
    assert normalize_region_name("馬祖") == "連江縣"


def test_taiwan_all_regions_coordinates() -> None:
    """Ensure all 22 standard administrative divisions have valid coordinates."""
    expected_regions = [
        "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市",
        "基隆市", "新竹市", "新竹縣", "苗栗縣", "彰化縣", "南投縣",
        "雲林縣", "嘉義市", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
        "臺東縣", "澎湖縣", "金門縣", "連江縣",
    ]

    for region in expected_regions:
        coords = get_location_coordinates(region)
        assert coords is not None, f"Coordinates missing for {region}"
        lat, lon = coords
        # Latitude range for Taiwan territories: 21 to 27 degrees North
        assert 21.0 <= lat <= 27.0, f"Latitude {lat} out of range for {region}"
        # Longitude range for Taiwan territories: 118 to 123 degrees East
        assert 118.0 <= lon <= 123.0, f"Longitude {lon} out of range for {region}"
