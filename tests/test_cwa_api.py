"""Unit tests for CWA API client error handling and status code validation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest
import requests

from src.config.settings import Settings
from src.services.cwa_api import (
    CWAAPIError,
    CWAAuthError,
    CWAClient,
    CWAConnectionError,
    CWANoDataError,
    CWATimeoutError,
)


@pytest.fixture
def dummy_settings() -> Settings:
    """Create settings with dummy values."""
    return Settings(
        cwa_api_key="CWA-TEST-KEY-12345",
        cwa_dataset_id="F-C0032-001",
        cwa_base_url="https://opendata.cwa.gov.tw/api/v1/rest/datastore",
        cwa_request_timeout=5,
    )


def test_missing_api_key_raises_auth_error() -> None:
    """Verify that calling fetch_forecast_data without an API key raises CWAAuthError."""
    settings = Settings(cwa_api_key="")
    client = CWAClient(settings=settings)
    with pytest.raises(CWAAuthError, match="CWA API Key 未設定"):
        client.fetch_forecast_data(api_key="")


@patch("requests.get")
def test_timeout_raises_timeout_error(mock_get: MagicMock, dummy_settings: Settings) -> None:
    """Verify requests Timeout is mapped to CWATimeoutError."""
    mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
    client = CWAClient(settings=dummy_settings)

    with pytest.raises(CWATimeoutError, match="超時"):
        client.fetch_forecast_data()


@patch("requests.get")
def test_connection_error_raises_connection_error(
    mock_get: MagicMock, dummy_settings: Settings
) -> None:
    """Verify requests ConnectionError is mapped to CWAConnectionError."""
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
    client = CWAClient(settings=dummy_settings)

    with pytest.raises(CWAConnectionError, match="無法連線至中央氣象署 API"):
        client.fetch_forecast_data()


@patch("requests.get")
def test_http_401_raises_auth_error(mock_get: MagicMock, dummy_settings: Settings) -> None:
    """Verify HTTP 401 Unauthorized raises CWAAuthError."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_get.return_value = mock_response

    client = CWAClient(settings=dummy_settings)
    with pytest.raises(CWAAuthError, match="CWA API 金鑰認證失敗"):
        client.fetch_forecast_data()


@patch("requests.get")
def test_empty_records_raises_no_data_error(
    mock_get: MagicMock, dummy_settings: Settings
) -> None:
    """Verify empty records raises CWANoDataError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": "true", "records": {}}
    mock_get.return_value = mock_response

    client = CWAClient(settings=dummy_settings)
    with pytest.raises(CWANoDataError, match="無任何天氣觀測/預報 records 資料"):
        client.fetch_forecast_data()


@patch("requests.get")
def test_invalid_json_raises_api_error(mock_get: MagicMock, dummy_settings: Settings) -> None:
    """Verify malformed JSON response raises CWAAPIError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON string")
    mock_get.return_value = mock_response

    client = CWAClient(settings=dummy_settings)
    with pytest.raises(CWAAPIError, match="非有效 JSON 格式"):
        client.fetch_forecast_data()
