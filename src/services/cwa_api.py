"""Central Weather Administration (CWA) Open Data API client."""

from __future__ import annotations

import json
from typing import Any
import requests

from src.config.settings import Settings, get_settings


class CWAAPIError(Exception):
    """Base exception for CWA API errors."""


class CWAAuthError(CWAAPIError):
    """Raised when the CWA API key is missing, unauthorized, or invalid."""


class CWATimeoutError(CWAAPIError):
    """Raised when an API request times out."""


class CWAConnectionError(CWAAPIError):
    """Raised when unable to establish connection to CWA API."""


class CWANoDataError(CWAAPIError):
    """Raised when the API returns an empty or invalid payload."""


class CWAClient:
    """Client for fetching weather forecast data from CWA Open Data API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def fetch_forecast_data(
        self,
        dataset_id: str | None = None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """Fetch raw weather forecast JSON from CWA API.

        Args:
            dataset_id: The CWA dataset ID (e.g., 'F-C0032-001' or 'F-D0047-089').
            api_key: Optional explicit API key. If omitted, uses environment settings.

        Returns:
            dict containing parsed JSON response from CWA.

        Raises:
            CWAAuthError: When API key is missing or authentication fails.
            CWATimeoutError: When request exceeds timeout.
            CWAConnectionError: On network connection failure.
            CWANoDataError: When API response contains no data records.
            CWAAPIError: On unexpected HTTP or response parsing errors.
        """
        key = (api_key or self.settings.cwa_api_key or "").strip()
        if not key:
            raise CWAAuthError(
                "CWA API Key 未設定。請在 .env 檔案中填入 CWA_API_KEY，或於系統側邊欄輸入。"
            )

        target_dataset = (dataset_id or self.settings.cwa_dataset_id or "F-C0032-001").strip()
        url = f"{self.settings.cwa_base_url}/{target_dataset}"

        params = {
            "Authorization": key,
            "format": "JSON",
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.settings.cwa_request_timeout,
            )

            # Check HTTP Status Code
            if response.status_code in (401, 403):
                raise CWAAuthError(
                    f"CWA API 金鑰認證失敗 (HTTP {response.status_code})。請確認 API Key 是否有效。"
                )
            if response.status_code == 404:
                raise CWANoDataError(
                    f"找不到資料集 {target_dataset} (HTTP 404)。請確認 CWA_DATASET_ID 設定。"
                )

            response.raise_for_status()

            # Parse JSON
            try:
                payload = response.json()
            except (json.JSONDecodeError, ValueError) as err:
                raise CWAAPIError(f"CWA API 回傳非有效 JSON 格式: {err}") from err

            # Check CWA specific success status if provided
            if isinstance(payload, dict):
                success_flag = str(payload.get("success", "true")).lower()
                if success_flag == "false":
                    message = payload.get("message", "未知 API 錯誤")
                    raise CWAAPIError(f"CWA API 呼叫失敗: {message}")

                records = payload.get("records")
                if not records:
                    raise CWANoDataError("CWA API 回傳成功，但無任何天氣觀測/預報 records 資料。")

            return payload

        except requests.exceptions.Timeout as err:
            raise CWATimeoutError(
                f"連線中央氣象署 API 超時 (超過 {self.settings.cwa_request_timeout} 秒)，請檢查網路或稍後重試。"
            ) from err

        except requests.exceptions.ConnectionError as err:
            raise CWAConnectionError(
                "無法連線至中央氣象署 API (Connection Error)，請檢查網路連線狀態。"
            ) from err

        except (CWAAPIError, CWAAuthError, CWATimeoutError, CWANoDataError):
            raise

        except requests.exceptions.RequestException as err:
            raise CWAAPIError(f"CWA API 請求發生未預期錯誤: {err}") from err
