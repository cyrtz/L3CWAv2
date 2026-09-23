"""Visualization module for interactive weather forecast charts using Plotly."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def create_temperature_chart(df: pd.DataFrame, region_name: str) -> go.Figure:
    """Generate an interactive Plotly dual-line chart for MaxT and MinT forecasts.

    Args:
        df: DataFrame containing at least 'data_date', 'min_temp', 'max_temp'.
        region_name: The display name of the selected region.

    Returns:
        plotly.graph_objects.Figure instance.
    """
    fig = go.Figure()

    if df.empty or "data_date" not in df.columns:
        fig.add_annotation(
            text="查無此地區的天氣預報資料",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font={"size": 18, "color": "#7f8c8d"},
        )
        fig.update_layout(
            title={"text": f"{region_name} — 溫度趨勢預報", "x": 0.5},
            xaxis={"visible": False},
            yaxis={"visible": False},
            height=380,
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
        )
        return fig

    # Ensure sorted by date
    df_sorted = df.sort_values(by="data_date").copy()

    # Max Temperature line (Warm / Coral Red)
    fig.add_trace(
        go.Scatter(
            x=df_sorted["data_date"],
            y=df_sorted["max_temp"],
            name="最高溫 (MaxT)",
            mode="lines+markers+text",
            text=[f"{v:.0f}°C" if pd.notna(v) else "" for v in df_sorted["max_temp"]],
            textposition="top center",
            textfont={"size": 11, "color": "#e74c3c"},
            line={"color": "#e74c3c", "width": 3, "shape": "spline"},
            marker={"size": 8, "color": "#c0392b", "symbol": "circle"},
            hovertemplate="<b>%{x}</b><br>最高溫: <b>%{y:.1f}°C</b><extra></extra>",
        )
    )

    # Min Temperature line (Cool / Dodger Blue)
    fig.add_trace(
        go.Scatter(
            x=df_sorted["data_date"],
            y=df_sorted["min_temp"],
            name="最低溫 (MinT)",
            mode="lines+markers+text",
            text=[f"{v:.0f}°C" if pd.notna(v) else "" for v in df_sorted["min_temp"]],
            textposition="bottom center",
            textfont={"size": 11, "color": "#2980b9"},
            line={"color": "#3498db", "width": 3, "shape": "spline"},
            marker={"size": 8, "color": "#2980b9", "symbol": "diamond"},
            hovertemplate="<b>%{x}</b><br>最低溫: <b>%{y:.1f}°C</b><extra></extra>",
        )
    )

    # Compute reasonable Y-axis range with padding
    valid_temps = pd.concat([df_sorted["min_temp"], df_sorted["max_temp"]]).dropna()
    if not valid_temps.empty:
        y_min = max(0, int(valid_temps.min() - 3))
        y_max = int(valid_temps.max() + 4)
        yaxis_range = [y_min, y_max]
    else:
        yaxis_range = [10, 35]

    fig.update_layout(
        title={
            "text": f"📈 {region_name} 未來氣溫預報趨勢 (MaxT / MinT)",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "family": "Inter, Roboto, sans-serif"},
        },
        xaxis={
            "title": "預報日期",
            "tickformat": "%Y-%m-%d",
            "showgrid": True,
            "gridcolor": "rgba(200, 200, 200, 0.2)",
            "linecolor": "#bdc3c7",
        },
        yaxis={
            "title": "溫度 (°C)",
            "range": yaxis_range,
            "showgrid": True,
            "gridcolor": "rgba(200, 200, 200, 0.2)",
            "linecolor": "#bdc3c7",
            "ticksuffix": "°C",
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.03,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(255, 255, 255, 0.6)",
        },
        hovermode="x unified",
        plot_bgcolor="rgba(248, 249, 250, 0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin={"l": 50, "r": 30, "t": 70, "b": 40},
    )

    return fig
