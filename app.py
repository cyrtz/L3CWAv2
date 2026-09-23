"""Taiwan Weather Forecast — 台灣天氣預報互動式 Web App.

A production-grade Streamlit Dashboard connecting CWA Open Data API,
SQLite storage, Plotly interactive trend charts, and Folium geospatial maps.
"""

from __future__ import annotations

import datetime
from typing import Any
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.config.settings import Settings, get_settings
from src.database.database import DatabaseManager
from src.parsers.weather_parser import WeatherParser
from src.repositories.weather_repository import WeatherRepository
from src.services.cwa_api import (
    CWAAPIError,
    CWAAuthError,
    CWAClient,
    CWAConnectionError,
    CWANoDataError,
    CWATimeoutError,
)
from src.visualization.weather_chart import create_temperature_chart
from src.visualization.weather_map import create_taiwan_weather_map
from src.data.seed_data import seed_database_with_sample_cwa_data


# ==============================================================================
# Page Configuration & Modern Styling
# ==============================================================================
st.set_page_config(
    page_title="Taiwan Weather Forecast | 台灣天氣預報",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for enhanced aesthetics and card design
st.markdown(
    """
    <style>
    /* Metric card styling */
    div[data-testid="stMetric"] {
        background-color: rgba(240, 244, 248, 0.6);
        border: 1px solid rgba(220, 226, 235, 0.8);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #555 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
    /* Section headers */
    .dashboard-header {
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .badge-success { background-color: #d4edda; color: #155724; }
    .badge-warning { background-color: #fff3cd; color: #856404; }
    .badge-info { background-color: #e2f0fd; color: #0c5460; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# Dependency Injection & Cached Resources
# ==============================================================================
@st.cache_resource
def get_db_manager() -> DatabaseManager:
    """Singleton database manager instance."""
    return DatabaseManager()


@st.cache_resource
def get_repository() -> WeatherRepository:
    """Singleton repository instance."""
    db_manager = get_db_manager()
    return WeatherRepository(db_manager)


def refresh_all_caches() -> None:
    """Clear all data caches so newly fetched data is immediately reflected."""
    st.cache_data.clear()


# ==============================================================================
# Cached Data Fetchers
# ==============================================================================
@st.cache_data
def fetch_cached_regions() -> list[str]:
    """Fetch distinct regions with caching."""
    repo = get_repository()
    return repo.get_regions()


@st.cache_data
def fetch_cached_dates() -> list[str]:
    """Fetch distinct forecast dates with caching."""
    repo = get_repository()
    return repo.get_dates()


@st.cache_data
def fetch_cached_region_forecast(region_name: str) -> pd.DataFrame:
    """Fetch forecast history for a specific region with caching."""
    repo = get_repository()
    return repo.get_weather_by_region(region_name)


@st.cache_data
def fetch_cached_date_forecast(data_date: str) -> pd.DataFrame:
    """Fetch all regional forecasts on a specific date with caching."""
    repo = get_repository()
    return repo.get_weather_by_date(data_date)


# ==============================================================================
# API Synchronization Service
# ==============================================================================
def execute_cwa_update(api_key: str | None = None, dataset_id: str | None = None) -> tuple[bool, str]:
    """Fetch newest data from CWA API, parse, and UPSERT into SQLite."""
    settings = get_settings()
    target_key = (api_key or settings.cwa_api_key or "").strip()
    target_dataset = (dataset_id or settings.cwa_dataset_id or "F-C0032-001").strip()

    if not target_key:
        return False, "未設定 CWA API Key。請於 .env 填寫或在側邊欄輸入。"

    client = CWAClient(settings=settings)
    try:
        payload = client.fetch_forecast_data(dataset_id=target_dataset, api_key=target_key)
        forecasts = WeatherParser.parse_cwa_json(payload)

        if not forecasts:
            return False, "CWA API 回傳成功，但解析後未取得有效氣溫預報紀錄。"

        repo = get_repository()
        count = repo.save_weather_data(forecasts)
        refresh_all_caches()
        return True, f"成功從中央氣象署更新 {count} 筆氣象預報資料！"

    except CWAAuthError as err:
        return False, f"金鑰認證失敗: {err}"
    except CWATimeoutError as err:
        return False, f"API 請求超時: {err}"
    except CWAConnectionError as err:
        return False, f"網路連線異常: {err}"
    except CWANoDataError as err:
        return False, f"查無預報資料: {err}"
    except CWAAPIError as err:
        return False, f"API 處理失敗: {err}"
    except Exception as err:
        return False, f"資料庫更新異常: {err}"


# ==============================================================================
# Sidebar Components
# ==============================================================================
def render_sidebar() -> dict[str, Any]:
    """Render the sidebar controls and return user options."""
    st.sidebar.title("🌤️ 控制面板")
    st.sidebar.caption("Taiwan Weather Forecast Dashboard")

    settings = get_settings()
    repo = get_repository()

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔑 CWA API 設定")

    # Show key status
    has_env_key = settings.has_api_key
    if has_env_key:
        st.sidebar.markdown('<span class="status-badge badge-success">✓ .env 金鑰已載入</span>', unsafe_allow_html=True)
        custom_key = ""
    else:
        st.sidebar.markdown('<span class="status-badge badge-warning">! 尚未設定 .env 金鑰</span>', unsafe_allow_html=True)
        custom_key = st.sidebar.text_input(
            "臨時輸入 API Key:",
            type="password",
            help="中央氣象署 Open Data API Key (CWA_API_KEY)。未存於硬碟，僅限本次執行會話。",
        )

    dataset_options = ["F-C0032-001", "F-D0047-089", "F-D0047-091"]
    current_dataset = settings.cwa_dataset_id
    if current_dataset not in dataset_options:
        dataset_options.insert(0, current_dataset)

    selected_dataset = st.sidebar.selectbox(
        "選擇預報資料集 (Dataset ID):",
        options=dataset_options,
        index=dataset_options.index(current_dataset) if current_dataset in dataset_options else 0,
        help="F-C0032-001: 36小時預報 | F-D0047-089: 縣市一週預報",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 資料同步")

    effective_key = custom_key.strip() or settings.cwa_api_key.strip()

    if st.sidebar.button("🔄 更新天氣資料", use_container_width=True, type="primary"):
        with st.spinner("正在連線中央氣象署 CWA API 下載最新資料並寫入 SQLite..."):
            success, msg = execute_cwa_update(api_key=effective_key, dataset_id=selected_dataset)
            if success:
                st.sidebar.success(msg)
                st.rerun()
            else:
                st.sidebar.error(msg)

    # Initial sample load button if DB is empty or user wants to test
    record_count = repo.get_record_count()
    if record_count == 0:
        st.sidebar.info("💡 目前資料庫尚未有紀錄。")
        if st.sidebar.button("📥 載入氣象署格式模擬資料 (快速體驗)", use_container_width=True):
            with st.spinner("正在將 22 縣市官方格式模擬資料注入 SQLite..."):
                count = seed_database_with_sample_cwa_data(repo)
                refresh_all_caches()
                st.sidebar.success(f"已初始化 {count} 筆預報紀錄！")
                st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        f"""
        **資料庫狀態**
        - 資料筆數: `{record_count}` 筆
        - 資料庫檔案: `{settings.database_path}`
        - 最新更新: `{repo.get_latest_update_time() or '無紀錄'}`
        """
    )

    with st.sidebar.expander("ℹ️ 關於 CWA Open Data"):
        st.markdown(
            """
            1. 前往 [氣象署會員中心](https://opendata.cwa.gov.tw/user/authkey) 免費申請會員。
            2. 取得 API Key (授權碼)。
            3. 將金鑰寫入專案 `.env` 的 `CWA_API_KEY`。
            4. 點擊「更新天氣資料」即可自動抓取最新實時氣候預報！
            """
        )

    return {
        "dataset_id": selected_dataset,
        "effective_key": effective_key,
    }


# ==============================================================================
# Main Dashboard
# ==============================================================================
def main() -> None:
    """Main dashboard application logic."""
    sidebar_opts = render_sidebar()
    repo = get_repository()

    # Header
    st.markdown(
        """
        <div class="dashboard-header">
            <h1 style="margin-bottom: 4px;">🌤️ Taiwan Weather Forecast</h1>
            <p style="color: #666; font-size: 1.05rem;">
                台灣氣象預報互動式儀表板 — 串接交通部中央氣象署 CWA Open Data API，即時解析、SQLite 結構化儲存與空間視覺化。
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Available regions from DB
    regions = fetch_cached_regions()
    available_dates = fetch_cached_dates()

    if not regions or not available_dates:
        st.warning(
            "⚠️ 目前資料庫中無任何天氣預報資料。\n\n"
            "請於左側側邊欄輸入 CWA API Key 並點擊 **「🔄 更新天氣資料」**，"
            "或點擊 **「📥 載入氣象署格式模擬資料」** 即可立即啟動完整儀表板！"
        )
        return

    # Filter Section
    col_filter_region, col_filter_date = st.columns([1, 1])

    with col_filter_region:
        region_options = ["請選擇地區"] + regions
        selected_region = st.selectbox(
            "📍 選擇地區 (Region):",
            options=region_options,
            index=1 if len(region_options) > 1 else 0,
            help="從 SQLite 資料庫動態查詢之地區清單",
        )

    with col_filter_date:
        default_date_idx = 0
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        if today_str in available_dates:
            default_date_idx = available_dates.index(today_str)

        selected_date = st.selectbox(
            "📅 選擇預報日期 (Date):",
            options=available_dates,
            index=default_date_idx,
            help="選擇特定日期以檢視全台溫度地圖與各地數值",
        )

    st.markdown("---")

    # ==========================================================================
    # Summary Metrics Row
    # ==========================================================================
    if selected_region != "請選擇地區":
        # Fetch data for selected region & date
        region_date_data = repo.get_weather_by_region_and_date(selected_region, selected_date)
        df_region = fetch_cached_region_forecast(selected_region)

        col1, col2, col3, col4 = st.columns(4)

        if region_date_data:
            max_t = region_date_data.get("max_temp")
            min_t = region_date_data.get("min_temp")
            avg_t = region_date_data.get("avg_temp")
            wx = region_date_data.get("weather_condition") or "無特殊狀態"
            pop = region_date_data.get("pop")

            delta_t = round(max_t - min_t, 1) if (max_t is not None and min_t is not None) else None

            with col1:
                st.metric(
                    label=f"🔥 {selected_region} 最高溫 (MaxT)",
                    value=f"{max_t:.1f} °C" if max_t is not None else "無資料",
                    delta=f"溫差 {delta_t}°C" if delta_t is not None else None,
                )
            with col2:
                st.metric(
                    label=f"❄️ {selected_region} 最低溫 (MinT)",
                    value=f"{min_t:.1f} °C" if min_t is not None else "無資料",
                )
            with col3:
                st.metric(
                    label="🌡️ 當日平均氣溫",
                    value=f"{avg_t:.1f} °C" if avg_t is not None else "無資料",
                    delta=f"降雨機率 {pop}%" if pop is not None else None,
                )
            with col4:
                st.metric(
                    label="☁️ 天氣現象 (Wx)",
                    value=wx,
                    help=f"預報日期: {selected_date}",
                )
        else:
            with col1:
                st.metric(label="選擇地區", value=selected_region)
            with col2:
                st.metric(label="預報日期", value=selected_date)
            with col3:
                st.metric(label="氣象資訊", value="此日期查無記錄")
            with col4:
                st.metric(label="狀態", value="請切換日期")

        st.markdown("<br>", unsafe_allow_html=True)

        # ======================================================================
        # Visualizations: Charts & Data Table
        # ======================================================================
        chart_col, table_col = st.columns([1.6, 1.0])

        with chart_col:
            st.subheader(f"📊 {selected_region} 氣溫預報走勢圖")
            fig = create_temperature_chart(df_region, selected_region)
            st.plotly_chart(fig, use_container_width=True)

        with table_col:
            st.subheader("📋 每日天氣預報詳細表")
            display_df = df_region[
                ["data_date", "min_temp", "max_temp", "weather_condition", "pop"]
            ].copy()
            display_df.rename(
                columns={
                    "data_date": "預報日期",
                    "min_temp": "最低溫 (°C)",
                    "max_temp": "最高溫 (°C)",
                    "weather_condition": "天氣現象",
                    "pop": "降雨機率 (%)",
                },
                inplace=True,
            )
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

            # CSV Download
            csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下載預報資料 (CSV)",
                data=csv_data,
                file_name=f"{selected_region}_weather_forecast.csv",
                mime="text/csv",
                use_container_width=True,
            )

    else:
        st.info("👆 請在上方的下拉選單中選擇台灣特定縣市地區，即可檢視專屬折線圖與預報指標！")

    st.markdown("---")

    # ==========================================================================
    # Geospatial Map: Taiwan Weather Map
    # ==========================================================================
    st.subheader(f"🗺️ 全台灣縣市氣溫地理分佈圖 ({selected_date})")
    st.caption("各縣市圓點顏色代表平均氣溫分級：藍色(<20°C)、綠色(20 ~ 25°C)、橘色(25 ~ 30°C)、紅色(>30°C)。點擊可查看詳細預報。")

    df_for_date = fetch_cached_date_forecast(selected_date)

    if not df_for_date.empty:
        taiwan_map = create_taiwan_weather_map(df_for_date, selected_date)
        st_folium(taiwan_map, width="100%", height=560, returned_objects=[])
    else:
        st.warning(f"目前在 {selected_date} 無各縣市氣象資料。")


if __name__ == "__main__":
    main()
