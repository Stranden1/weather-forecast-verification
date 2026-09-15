from __future__ import annotations

import os
import inspect
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st
from dotenv import load_dotenv, set_key

from collectors.frost_observations import sync_recent
from collectors.met_forecast import collect_all
from collectors.station_network import discover_and_save, refresh_active_metadata
from database import DB_PATH
from forecast_comparison import (
    MET_PROVIDER,
    WEATHERNEXT_PROVIDER,
    comparison_stations,
    load_temperature_timeline,
    mae_by_lead_bucket,
    past_temperature_rows,
    recent_runs,
)
from dashboard_scores import load_accuracy_rows, accuracy_board
from weathernext_status import load_weathernext_status

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
BACKGROUND_LOG_PATH = BASE_DIR / "data" / "background.log"
load_dotenv(ENV_PATH)

st.set_page_config(page_title="Weather Benchmark", page_icon="🌦️", layout="wide")
st.markdown("""<style>
.block-container {padding-top:3.3rem; padding-bottom:1rem; max-width:1440px;}
[data-testid="stVerticalBlock"] {gap:0.45rem;}
[data-testid="stMetricValue"] {font-size:1.5rem; font-weight:600; font-variant-numeric:tabular-nums;}
[data-testid="stMetricLabel"] {font-size:0.78rem; opacity:0.75;}
[data-testid="stMetric"] {padding:0.6rem 0.85rem; border:1px solid color-mix(in srgb, currentColor 12%, transparent); border-radius:9px; background:color-mix(in srgb, currentColor 3%, transparent);}
[data-testid="stWidgetLabel"] p {font-size:0.78rem;}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {min-height:34px; font-size:0.82rem;}
[data-testid="stCaptionContainer"] p {font-size:0.75rem; line-height:1.4;}
[data-testid="stExpander"] summary {padding:0.45rem 0.65rem; min-height:2.2rem;}
[data-testid="stExpander"] summary p {font-size:0.8rem;}
div[data-testid="stHeadingWithActionElements"] h3 {font-size:1.35rem; padding:0 0 0.4rem;}
</style>""", unsafe_allow_html=True)
st.markdown("### Weather benchmark")
st.caption("Yr/MET + WeatherNext + Frost · Local forecast verification · UTC")

@contextmanager
def connect():
    # Browsing the dashboard must not seed, migrate or update production records.
    con = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()

if not DB_PATH.exists():
    st.info("No weather database yet. Run the existing collector setup first.")
    st.stop()

with connect() as con:
    counts = {
        "active_stations": con.execute("SELECT COUNT(*) FROM locations WHERE active=1").fetchone()[0],
        "forecast_runs": con.execute("SELECT COUNT(*) FROM forecast_runs").fetchone()[0],
        "forecast_rows": con.execute("SELECT COUNT(*) FROM forecasts").fetchone()[0],
        "observations": con.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
    }
    network = pd.read_sql_query(
        """
        SELECT
            l.id,
            l.name AS display_name,
            l.station_id,
            COALESCE(l.station_name, l.name) AS station,
            l.station_class AS class,
            l.latitude,
            l.longitude,
            l.elevation_m,
            l.municipality,
            l.county,
            l.station_holders,
            l.wmo_id,
            l.icao_codes,
            COALESCE(l.site_group, 'Not classified yet') AS site_group,
            l.source_valid_from,
            l.source_valid_to,
            EXISTS(SELECT 1 FROM observation_sources s WHERE s.location_id=l.id AND s.element='air_temperature') AS temperature,
            EXISTS(SELECT 1 FROM observation_sources s WHERE s.location_id=l.id AND s.element='wind_speed') AS wind,
            EXISTS(SELECT 1 FROM observation_sources s WHERE s.location_id=l.id AND s.element='precipitation_1h') AS hourly_precip
        FROM locations l
        WHERE l.active=1
        ORDER BY l.station_class, station
        """,
        con,
    )
    latest_log = pd.read_sql_query(
        """
        SELECT started_at, finished_at, mode, status, message
        FROM collection_log ORDER BY id DESC LIMIT 8
        """,
        con,
    )
    weathernext_status, weathernext_log = load_weathernext_status(
        con, BACKGROUND_LOG_PATH
    )


def display_timestamp(value):
    return value.replace("T", " ").replace("+00:00", " UTC").replace("Z", " UTC") if value else "—"


def polish_chart(chart):
    """Shared chart spacing; keep Streamlit's light/dark text colors."""
    return (chart.configure_view(strokeWidth=0)
            .configure_axis(domain=False, tickSize=0, labelPadding=7,
                            labelFontSize=11, titleFontSize=11, titleFontWeight="normal",
                            titlePadding=10, gridOpacity=0.14)
            .configure_axisX(grid=False)
            .configure_legend(orient="top", title=None, labelFontSize=11,
                              symbolSize=65, padding=0, offset=10))


def accuracy_chart(rows, metric):
    return alt.Chart(rows).mark_bar().encode(
        x=alt.X("horizon:N", title="Lead time", sort=None),
        y=alt.Y(f"{metric}:Q", title="MAE (°C)" if metric == "MAE_C" else "MAE (m/s)"),
        xOffset="provider:N",
        color=alt.Color("provider:N", title=None, scale=alt.Scale(
            domain=["MET", "WeatherNext3-mean"], range=["#3b82f6", "#2f9e44"])),
        tooltip=["provider:N", "horizon:N", alt.Tooltip(f"{metric}:Q", format=".2f"), "samples:Q"],
    ).properties(height=230).configure_legend(orient="top")



# Avoid running the expensive historical accuracy queries while browsing forecasts.
stateful_tabs = "on_change" in inspect.signature(st.tabs).parameters
forecast_tab, network_tab, accuracy_tab = st.tabs(
    ["Forecast vs Actual", "Station network", "Overall accuracy"],
    **({"on_change": "rerun"} if stateful_tabs else {}),
)
with forecast_tab:
    if not stateful_tabs or forecast_tab.open:
        with connect() as con:
            comparison_station_rows = comparison_stations(con)

        if not comparison_station_rows:
            st.info("Build the station network to start comparing forecasts.")
        else:
            station_labels = {
                row["id"]: f'{row["station_name"].title().replace(" - ", "-")} ({row["station_id"] or "no station ID"})'
                for row in comparison_station_rows
            }
            select_station, select_met, select_wn, select_window = st.columns([2.2, 1.5, 1.5, 0.9], gap="small")
            selected_location_id = select_station.selectbox(
                "Station",
                options=list(station_labels),
                format_func=station_labels.get,
                key="forecast_actual_station",
            )

            with connect() as con:
                met_runs = recent_runs(con, selected_location_id, MET_PROVIDER)
                wn_runs = recent_runs(con, selected_location_id, WEATHERNEXT_PROVIDER)

            if not met_runs or not wn_runs:
                missing = []
                if not met_runs:
                    missing.append("Yr/MET")
                if not wn_runs:
                    missing.append("WeatherNext")
                st.info(f"No stored {' and '.join(missing)} temperature run is available for this station yet.")
            else:
                def run_label(run):
                    return pd.Timestamp(run["issued_at"]).strftime("%d %b · %H:%M")

                with select_met:
                    met_run_id = st.selectbox(
                        "Yr/MET run",
                        key=f"met_run_{selected_location_id}",
                        options=[run["id"] for run in met_runs],
                        format_func=lambda run_id: run_label(next(run for run in met_runs if run["id"] == run_id)),
                    )
                with select_wn:
                    wn_run_id = st.selectbox(
                        "WeatherNext run",
                        key=f"wn_run_{selected_location_id}",
                        options=[run["id"] for run in wn_runs],
                        format_func=lambda run_id: run_label(next(run for run in wn_runs if run["id"] == run_id)),
                    )

                with connect() as con:
                    temperature_timeline = load_temperature_timeline(
                        con, selected_location_id, met_run_id, wn_run_id
                    )

                now = pd.Timestamp.now(tz="UTC")
                # Display only elapsed actuals; the selected runs remain unchanged.
                temperature_timeline.loc[temperature_timeline["valid_at"] > now, "actual_temperature"] = float("nan")
                past_rows = past_temperature_rows(temperature_timeline, now)
                view_window = select_window.selectbox("Chart window", ["72 h", "7 days", "Full run"])
                if view_window != "Full run" and not temperature_timeline.empty:
                    cutoff = temperature_timeline["valid_at"].min() + pd.Timedelta(hours=72 if view_window == "72 h" else 168)
                    temperature_timeline = temperature_timeline[temperature_timeline["valid_at"] <= cutoff]
                latest_actual = past_rows.iloc[-1] if not past_rows.empty else None
                paired = past_rows.dropna(subset=["met_abs_error", "wn_abs_error"])
                paired = paired[(paired["met_lead_hours"] >= 0) & (paired["wn_lead_hours"] >= 0)]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Latest observed", "—" if latest_actual is None else f"{latest_actual['actual_temperature']:.1f} °C")
                m2.metric("Yr/MET MAE", "—" if paired.empty else f"{paired['met_abs_error'].mean():.2f} °C", help="Mean absolute error over shared observed hours for the selected runs.")
                m3.metric("WeatherNext MAE", "—" if paired.empty else f"{paired['wn_abs_error'].mean():.2f} °C", help="Mean absolute error over the same shared observed hours as Yr/MET.")
                m4.metric("Shared observed hours", len(paired))
                if latest_actual is not None:
                    st.caption(f"Latest observation: {latest_actual['valid_at']:%d %b %H:%M UTC} · WeatherNext ensemble mean · Frost hourly average")

                temperature_timeline = temperature_timeline.copy()
                temperature_timeline["time_utc"] = temperature_timeline["valid_at"].dt.strftime("%d %b %H:%M UTC")
                chart_lines = temperature_timeline[
                    ["valid_at", "time_utc", "met_temperature", "wn_temperature"]
                ].melt(
                    id_vars=["valid_at", "time_utc"],
                    var_name="series",
                    value_name="temperature",
                )
                chart_lines["series"] = chart_lines["series"].map(
                    {"met_temperature": "Yr/MET", "wn_temperature": "WeatherNext"}
                )
                colors = alt.Scale(
                    domain=["Yr/MET", "WeatherNext", "Frost actual"],
                    range=["#6099e8", "#55ad92", "#dfa44e"],
                )
                forecast_lines = (
                    alt.Chart(chart_lines.dropna(subset=["temperature"]))
                    .mark_line(strokeWidth=1.7)
                    .encode(
                        x=alt.X("valid_at:T", title="Time (UTC)", scale=alt.Scale(type="utc"),
                                axis=alt.Axis(labelExpr="utcFormat(datum.value, '%d %b %H:%M')", tickCount=8)),
                        y=alt.Y("temperature:Q", title="Temperature (°C)", scale=alt.Scale(zero=False)),
                        color=alt.Color("series:N", title=None, scale=colors),
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("series:N", title="Source"),
                            alt.Tooltip("temperature:Q", title="Temperature °C", format=".1f"),
                        ],
                    )
                )
                uncertainty = (
                    alt.Chart(temperature_timeline.dropna(subset=["wn_p10", "wn_p90"]))
                    .mark_area(color="#55ad92", opacity=0.09)
                    .encode(
                        x=alt.X("valid_at:T", scale=alt.Scale(type="utc")),
                        y=alt.Y("wn_p10:Q", title="Temperature (°C)", scale=alt.Scale(zero=False)),
                        y2="wn_p90:Q",
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("wn_p10:Q", title="WeatherNext p10 °C", format=".1f"),
                            alt.Tooltip("wn_p90:Q", title="WeatherNext p90 °C", format=".1f"),
                        ],
                    )
                )
                actual_data = temperature_timeline.dropna(subset=["actual_temperature"]).copy()
                actual_data["series"] = "Frost actual"
                actual_line = (
                    alt.Chart(actual_data)
                    .mark_line(point=alt.OverlayMarkDef(size=13, filled=True), strokeWidth=2)
                    .encode(
                        x=alt.X("valid_at:T", scale=alt.Scale(type="utc")),
                        y=alt.Y("actual_temperature:Q", title="Temperature (°C)", scale=alt.Scale(zero=False)),
                        color=alt.Color("series:N", title=None, scale=colors),
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("actual_temperature:Q", title="Frost actual °C", format=".1f"),
                        ],
                    )
                )
                now_rule = (
                    alt.Chart(pd.DataFrame({"now": [now] if not temperature_timeline.empty and temperature_timeline["valid_at"].min() <= now <= temperature_timeline["valid_at"].max() else []}))
                    .mark_rule(color="#929aa6", strokeDash=[3, 4], strokeWidth=1, opacity=0.7)
                    .encode(x=alt.X("now:T", scale=alt.Scale(type="utc")))
                )
                st.altair_chart(
                    polish_chart(alt.layer(uncertainty, forecast_lines, actual_line, now_rule)
                    .properties(height=245).interactive()),
                    use_container_width=True,
                )
                st.caption("Shading: WeatherNext p10–p90 · Dashed line: now · Summary MAE uses shared observed hours")

                table_rows = past_rows[
                    [
                        "valid_at",
                        "met_temperature",
                        "wn_temperature",
                        "actual_temperature",
                        "met_abs_error",
                        "wn_abs_error",
                    ]
                ].copy()
                table_rows.columns = [
                    "Time (UTC)",
                    "Yr",
                    "WeatherNext",
                    "Actual",
                    "Yr |error|",
                    "WN |error|",
                ]
                table_rows = table_rows.sort_values("Time (UTC)", ascending=False)
                numeric_columns = table_rows.columns[1:]
                table_rows[numeric_columns] = table_rows[numeric_columns].round(1)

                table_c1, table_c2 = st.columns([3, 2])
                with table_c1:
                    st.markdown("**Recent results · °C**")
                    if table_rows.empty:
                        st.caption("No elapsed forecast timestamps have a matching Frost observation yet.")
                    else:
                        st.dataframe(table_rows.head(24),
                            use_container_width=True, hide_index=True, height=196, row_height=26, placeholder="—",
                            column_config={
                                "Time (UTC)": st.column_config.DatetimeColumn(format="DD MMM HH:mm", width="small"),
                                **{name: st.column_config.NumberColumn(format="%.1f", width="small")
                                   for name in numeric_columns},
                            })
                        st.caption("Latest 24 matched hours from the selected runs. Errors use available observations.")
                with table_c2:
                    st.markdown("**MAE by forecast lead time**")
                    mae_rows = mae_by_lead_bucket(past_rows)
                    if mae_rows.empty:
                        st.caption("MAE appears when forecast timestamps have matching Frost observations.")
                    else:
                        mae_chart = (
                            alt.Chart(mae_rows)
                            .mark_point(filled=True, size=75, opacity=1)
                            .encode(
                                y=alt.Y("lead bucket:N", title=None, sort=None, axis=alt.Axis(grid=False)),
                                x=alt.X("MAE:Q", title="MAE (°C) · lower is better", scale=alt.Scale(zero=True), axis=alt.Axis(grid=True, tickCount=4)),
                                yOffset="provider:N",
                                shape=alt.Shape("provider:N", title=None, scale=alt.Scale(domain=["Yr/MET", "WeatherNext"], range=["circle", "diamond"])),
                                color=alt.Color("provider:N", title=None, scale=alt.Scale(
                                    domain=["Yr/MET", "WeatherNext"], range=["#6099e8", "#55ad92"])),
                                tooltip=[
                                    alt.Tooltip("provider:N", title="Provider"),
                                    alt.Tooltip("lead bucket:N", title="Lead time"),
                                    alt.Tooltip("MAE:Q", title="MAE °C", format=".2f"),
                                    alt.Tooltip("samples:Q", title="Matched hours"),
                                ],
                            )
                            .properties(height=max(65, min(155, mae_rows["lead bucket"].nunique() * 38)))
                        )
                        st.altair_chart(polish_chart(mae_chart), use_container_width=True)
                        st.caption("Selected runs · each provider’s own lead time; hover for sample counts.")
                        # Keep detailed figures available without another always-open table.
                        with st.expander("MAE details"):
                            st.dataframe(
                            mae_rows.rename(
                                columns={"lead bucket": "Lead time", "provider": "Provider", "samples": "Hours"}
                            ).round({"MAE": 2}),
                            use_container_width=True,
                            hide_index=True,
                        )


with network_tab:
    if not stateful_tabs or network_tab.open:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Active Frost stations", counts["active_stations"])
        c2.metric("Forecast runs", counts["forecast_runs"])
        c3.metric("Forecast points", counts["forecast_rows"])
        c4.metric("Measured rows", counts["observations"])

        if not network.empty:
            grades = network["class"].fillna("?").value_counts()
            groups = network["site_group"].fillna("Not classified yet").value_counts()
            st.caption(" · ".join([f"Class {g}: {int(grades.get(g, 0))}" for g in ["A", "B", "C"]]))

            st.markdown("**Where are the stations?**")
            group_options = list(groups.index)
            chosen_groups = st.multiselect(
                "Show on map",
                options=group_options,
                default=group_options,
                help="This does not change which stations are collected; it only filters the map.",
            )
            map_df = network[network["site_group"].isin(chosen_groups)].copy()
            if not map_df.empty:
                for col in ["municipality", "county", "station_holders"]:
                    map_df[col] = map_df[col].fillna("—")
                map_df["elevation_label"] = map_df["elevation_m"].apply(
                    lambda x: "—" if pd.isna(x) else f"{float(x):.0f} m"
                )
                center_lat = float(map_df["latitude"].mean())
                center_lon = float(map_df["longitude"].mean())
                layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=map_df,
                    get_position="[longitude, latitude]",
                    get_radius=7000,
                    get_fill_color=[255, 140, 0, 220],
                    radius_min_pixels=4,
                    radius_max_pixels=11,
                    pickable=True,
                    auto_highlight=True,
                )
                tooltip = {
                    "html": (
                        "<b>{station}</b><br/>"
                        "{station_id} · Class {class}<br/>"
                        "{site_group}<br/>"
                        "Municipality: {municipality}<br/>County: {county}<br/>"
                        "Elevation: {elevation_label}<br/>Holder: {station_holders}<br/>"
                        "{latitude}, {longitude}"
                    ),
                    "style": {"backgroundColor": "#222", "color": "white"},
                }
                deck = pdk.Deck(
                    layers=[layer],
                    initial_view_state=pdk.ViewState(
                        latitude=center_lat,
                        longitude=center_lon,
                        zoom=3.2,
                        pitch=0,
                    ),
                    tooltip=tooltip,
                )
                st.pydeck_chart(deck, use_container_width=True, height=330)
                st.caption("Hover/click a dot to see the Frost station name, ID, municipality/county, elevation and station holder.")

            st.markdown("**Station list**")
            table = network.copy()
            table["latitude"] = table["latitude"].round(4)
            table["longitude"] = table["longitude"].round(4)
            st.dataframe(
                table[[
                    "station", "station_id", "class", "site_group", "municipality", "county",
                    "elevation_m", "temperature", "wind", "hourly_precip", "latitude", "longitude"
                ]],
                use_container_width=True,
                hide_index=True,
                height=240,
            )

            station_names = network["station"].tolist()
            selected_name = st.selectbox("Inspect one station", station_names)
            row = network.loc[network["station"] == selected_name].iloc[0]
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Station ID", row["station_id"] or "—")
            d2.metric("Elevation", "—" if pd.isna(row["elevation_m"]) else f"{float(row['elevation_m']):.0f} m")
            d3.metric("Municipality", row["municipality"] or "—")
            d4.metric("County", row["county"] or "—")
            st.caption(
                f"Coordinates: {row['latitude']:.5f}, {row['longitude']:.5f} · "
                f"Site group: {row['site_group']} · Holder: {row['station_holders'] or '—'} · "
                f"WMO: {row['wmo_id'] or '—'} · ICAO: {row['icao_codes'] or '—'}"
            )


with accuracy_tab:
    if not stateful_tabs or accuracy_tab.open:
        tab_temp, tab_wind = st.tabs(["Temperature", "Wind"])
        with tab_temp:
            with connect() as con:
                temperature_rows = load_accuracy_rows(con, "air_temperature")
            board = accuracy_board(temperature_rows, "air_temperature")
            if board.empty:
                st.info("No temperature scores yet. They appear automatically after stored forecast times pass and Frost observations are synced.")
            else:
                display = board.copy()
                display["MAE_C"] = display["MAE_C"].round(2)
                display["bias"] = display["bias"].round(2)
                chart = display.pivot(index="horizon", columns="provider", values="MAE_C")
                st.markdown("**Mean absolute error by forecast horizon**")
                st.altair_chart(accuracy_chart(display, "MAE_C"), use_container_width=True)
                with st.expander("Score details"):
                    st.dataframe(display, use_container_width=True, hide_index=True)

                rows = temperature_rows
                if not rows.empty:
                    by_location = (
                        rows.groupby(["location", "provider"], as_index=False)
                        .agg(MAE_C=("abs_error", "mean"), samples=("abs_error", "size"))
                        .sort_values(["location", "MAE_C"])
                    )
                    by_location["MAE_C"] = by_location["MAE_C"].round(2)
                    with st.expander("Accuracy by station"):
                        st.dataframe(by_location, use_container_width=True, hide_index=True)

        with tab_wind:
            with connect() as con:
                wind_rows = load_accuracy_rows(con, "wind_speed")
            board = accuracy_board(wind_rows, "wind_speed")
            if board.empty:
                st.info("Wind scores will appear for stations where Frost provides matching hourly wind observations.")
            else:
                display = board.copy()
                display["MAE_ms"] = display["MAE_ms"].round(2)
                display["bias"] = display["bias"].round(2)
                chart = display.pivot(index="horizon", columns="provider", values="MAE_ms")
                st.markdown("**Mean absolute wind-speed error by forecast horizon**")
                st.altair_chart(accuracy_chart(display, "MAE_ms"), use_container_width=True)
                with st.expander("Score details"):
                    st.dataframe(display, use_container_width=True, hide_index=True)


with st.expander("WeatherNext system status"):
    st.caption(
        f"{weathernext_status['collector_status'].title()} · "
        f"Run {display_timestamp(weathernext_status['latest_run'])} · "
        f"{weathernext_status['forecast_points']:,} points · "
        f"{weathernext_status['statistic_values']:,} values"
    )
    st.caption(f"Last attempt: {display_timestamp(weathernext_status['last_attempt'])} · Last success: {display_timestamp(weathernext_status['last_success'])} · Latest additions: {weathernext_status['new_values'] if weathernext_status['new_values'] is not None else '—'}")
with st.expander("Collection logs"):
    if not weathernext_log:
        st.caption("No WeatherNext background collection entries yet.")
    else:
        weather_log_table = pd.DataFrame(weathernext_log).rename(
            columns={
                "timestamp": "time (UTC)",
                "status": "status",
                "new_values": "new values",
                "model_run": "model run",
                "detail": "detail",
            }
        )
        weather_log_table["time (UTC)"] = weather_log_table["time (UTC)"].map(display_timestamp)
        st.dataframe(weather_log_table, use_container_width=True, hide_index=True)

    st.caption("All collectors · most recent runs")
    st.dataframe(latest_log, use_container_width=True, hide_index=True, height=200)

with st.expander("Admin / Manual controls", expanded=False):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        user_agent = st.text_input(
            "MET User-Agent",
            value=os.getenv("MET_USER_AGENT", ""),
            placeholder="WeatherApp/0.2 your-email@example.com",
        )
    with c2:
        frost_id = st.text_input(
            "Frost client ID",
            value=os.getenv("FROST_CLIENT_ID", ""),
            type="password",
            help="Client ID only. Never enter the hidden secret.",
        )
    with c3:
        current_target = int(os.getenv("TARGET_STATIONS", "50") or 50)
        options = [5, 25, 50, 75, 100, 150]
        if current_target not in options:
            options.append(current_target)
            options.sort()
        target = st.selectbox("Verification stations", options, index=options.index(current_target))

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Save settings"):
            ENV_PATH.touch(exist_ok=True)
            set_key(str(ENV_PATH), "MET_USER_AGENT", user_agent.strip())
            set_key(str(ENV_PATH), "FROST_CLIENT_ID", frost_id.strip())
            set_key(str(ENV_PATH), "TARGET_STATIONS", str(target))
            set_key(str(ENV_PATH), "AUTO_DISCOVER_STATIONS", "1")
            st.success("Saved locally in .env.")
    with b2:
        if st.button("Refresh network"):
            if not frost_id.strip():
                st.error("Enter your Frost client ID first.")
            else:
                with st.spinner(f"Finding a geographically spread network of {target} verifiable stations..."):
                    try:
                        result = discover_and_save(frost_id.strip(), target=target)
                        st.success(
                            f"Selected {result['selected']} stations from {result['recent_temperature']} with recent hourly temperature data. "
                            f"A={result['A']}, B={result['B']}, C={result['C']}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
    with b3:
        if st.button("Refresh metadata"):
            if not frost_id.strip():
                st.error("Enter your Frost client ID first.")
            else:
                with st.spinner("Fetching names, municipality/county, elevation and station holder from Frost..."):
                    try:
                        result = refresh_active_metadata(frost_id.strip())
                        st.success(f"Updated metadata for {result['updated']} of {result['requested']} active stations.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    b4, b5 = st.columns(2)
    with b4:
        if st.button("Fetch Yr/MET"):
            if not user_agent.strip():
                st.error("Enter a MET User-Agent first.")
            else:
                with st.spinner("Fetching forecasts for active verification stations..."):
                    result = collect_all(user_agent.strip())
                    st.success(f"Checked {result['locations']} stations; {result['rows_added']} new forecast rows saved.")
                    if result["errors"]:
                        st.error("\n".join(result["errors"][:20]))
    with b5:
        if st.button("Sync Frost"):
            if not frost_id.strip():
                st.error("Enter your Frost client ID first.")
            else:
                with st.spinner("Fetching measured temperature/wind..."):
                    result = sync_recent(frost_id.strip(), days=10)
                    st.success(f"Checked {result['locations']} stations; stored/refreshed {result['rows_added']} observation rows.")
                    if result["errors"]:
                        st.error("\n".join(result["errors"][:20]))

    with st.container():
        st.markdown("**Google WeatherNext 3**")
        st.caption("Uses the same active Frost stations. Fetches the latest complete 360-hour run; this can take several minutes.")
        if st.button("Fetch WeatherNext"):
            try:
                from collectors.weathernext import collect_all as collect_weathernext
                with st.spinner("Fetching WeatherNext temperature, wind, precipitation and pressure..."):
                    progress = st.empty()
                    result = collect_weathernext(progress=progress.caption)
                st.success(f"Checked {result['locations']} stations; saved {result['sample_values_added']} new statistic values.")
            except Exception as exc:
                st.error(f"WeatherNext: {exc}")
        st.caption("Temperature and wind means enter the scoreboards. Forecast uncertainty, wind components, rainfall and pressure are also saved. Rainfall is not yet scored against observations.")

    st.caption(
        "A = temperature + wind + hourly precipitation capability; B = temperature + one of those; C = temperature only. "
        "The site group shown below is for orientation only: municipality/county comes directly from Frost, while obvious offshore labels are inferred when administrative metadata is absent."
    )
