"""Folium map generation for Taiwan regional temperature visualization."""

from __future__ import annotations

import branca.element
import folium
import pandas as pd

from src.utils.location_utils import get_location_coordinates, normalize_region_name


def get_temperature_color(avg_temp: float | None) -> str:
    """Return categorical hex color based on average temperature.

    Classification:
    - < 20°C: Cool Blue (#3498db)
    - 20°C <= temp < 25°C: Comfortable Green (#2ecc71)
    - 25°C <= temp <= 30°C: Warm Orange (#f39c12)
    - > 30°C: Hot Red (#e74c3c)
    """
    if avg_temp is None:
        return "#95a5a6"  # Neutral Gray
    if avg_temp < 20.0:
        return "#3498db"
    if avg_temp < 25.0:
        return "#2ecc71"
    if avg_temp <= 30.0:
        return "#f39c12"
    return "#e74c3c"


def create_taiwan_weather_map(df_date: pd.DataFrame, selected_date: str) -> folium.Map:
    """Build an interactive Folium map visualizing regional weather forecasts across Taiwan.

    Args:
        df_date: DataFrame containing records for the specified date.
        selected_date: Target date string for display.

    Returns:
        folium.Map instance.
    """
    # Center map on Taiwan geographic central area
    taiwan_map = folium.Map(
        location=[23.7, 120.9],
        zoom_start=7.3,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # Add custom HTML legend
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 9999;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 13px;
        line-height: 1.6;
        min-width: 170px;
    ">
        <b style="font-size: 14px; color: #2c3e50;">🌡️ 氣溫分級 ({selected_date})</b><br>
        <span style="display:inline-block; width:12px; height:12px; background:#e74c3c; border-radius:50%; margin-right:6px;"></span>&gt; 30°C (炎熱)<br>
        <span style="display:inline-block; width:12px; height:12px; background:#f39c12; border-radius:50%; margin-right:6px;"></span>25 ~ 30°C (溫暖)<br>
        <span style="display:inline-block; width:12px; height:12px; background:#2ecc71; border-radius:50%; margin-right:6px;"></span>20 ~ 25°C (舒適)<br>
        <span style="display:inline-block; width:12px; height:12px; background:#3498db; border-radius:50%; margin-right:6px;"></span>&lt; 20°C (偏涼)<br>
    </div>
    """
    taiwan_map.get_root().html.add_child(branca.element.Element(legend_html))

    if df_date.empty:
        return taiwan_map

    for _, row in df_date.iterrows():
        region_name = normalize_region_name(str(row["region_name"]))
        coords = get_location_coordinates(region_name)
        if not coords:
            continue

        lat, lon = coords
        min_temp = row.get("min_temp")
        max_temp = row.get("max_temp")
        avg_temp = row.get("avg_temp")
        cond = row.get("weather_condition")
        pop_val = row.get("pop")

        # Format display strings
        min_str = f"{min_temp:.1f}°C" if pd.notna(min_temp) else "無資料"
        max_str = f"{max_temp:.1f}°C" if pd.notna(max_temp) else "無資料"
        avg_str = f"{avg_temp:.1f}°C" if pd.notna(avg_temp) else "無資料"
        cond_str = f"{cond}" if pd.notna(cond) else "—"
        pop_str = f"{pop_val}%" if pd.notna(pop_val) else "—"

        color = get_temperature_color(avg_temp if pd.notna(avg_temp) else None)

        popup_content = f"""
        <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.5; min-width: 150px;">
            <div style="font-size: 15px; font-weight: bold; color: #2c3e50; border-bottom: 2px solid {color}; padding-bottom: 4px; margin-bottom: 6px;">
                📍 {region_name}
            </div>
            <div><b>日期:</b> {selected_date}</div>
            <div style="color: #e74c3c;"><b>最高溫:</b> {max_str}</div>
            <div style="color: #2980b9;"><b>最低溫:</b> {min_str}</div>
            <div style="color: #16a085;"><b>平均溫:</b> {avg_str}</div>
            <div><b>天氣現象:</b> {cond_str}</div>
            <div><b>降雨機率:</b> {pop_str}</div>
        </div>
        """

        tooltip_text = f"<b>{region_name}</b>: {avg_str} ({min_str} ~ {max_str})"

        folium.CircleMarker(
            location=[lat, lon],
            radius=12,
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=tooltip_text,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=2,
        ).add_to(taiwan_map)

    return taiwan_map
