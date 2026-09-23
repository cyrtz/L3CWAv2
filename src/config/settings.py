"""Application configuration and settings management.

Supports two configuration modes:
- Local development: reads from .env file via python-dotenv
- Streamlit Cloud deployment: reads from st.secrets (set in the Streamlit dashboard)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded from project root (only affects local dev)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")


def _get_secret(key: str, default: str = "") -> str:
    """Read config value from st.secrets (Streamlit Cloud) or os.environ / .env (local).

    Priority:
    1. st.secrets (Streamlit Community Cloud)
    2. Environment variables / .env
    3. Provided default
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key]).strip()
    except Exception:
        pass
    return os.getenv(key, default).strip()


@dataclass(frozen=True)
class Settings:
    """System configuration settings loaded from environment variables or st.secrets."""

    # CWA Open Data API configurations
    cwa_api_key: str = ""
    cwa_dataset_id: str = "F-C0032-001"
    cwa_base_url: str = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
    cwa_request_timeout: int = 10

    # Database configuration
    database_path: str = "data/weather.db"

    @property
    def full_database_path(self) -> Path:
        """Return the absolute path to the SQLite database file."""
        return BASE_DIR / self.database_path

    @property
    def has_api_key(self) -> bool:
        """Check if an API key has been configured."""
        return bool(self.cwa_api_key)


def get_settings() -> Settings:
    """Factory function to get application settings.

    Reads from st.secrets if running on Streamlit Cloud,
    otherwise falls back to .env / environment variables.
    """
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

    timeout_raw = _get_secret("CWA_REQUEST_TIMEOUT", "10")
    try:
        timeout = int(timeout_raw)
    except (ValueError, TypeError):
        timeout = 10

    return Settings(
        cwa_api_key=_get_secret("CWA_API_KEY", ""),
        cwa_dataset_id=_get_secret("CWA_DATASET_ID", "F-C0032-001"),
        cwa_base_url=_get_secret(
            "CWA_BASE_URL", "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
        ).rstrip("/"),
        cwa_request_timeout=timeout,
        database_path=_get_secret("DATABASE_PATH", "data/weather.db"),
    )
