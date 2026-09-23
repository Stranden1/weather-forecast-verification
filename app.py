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
    load_timeline,
    VARIABLES,
    LEAD_BINS,
    LEAD_LABELS,
    mae_by_lead_bucket,
    past_rows as elapsed_rows,
    recent_runs,
)
from dashboard_scores import (load_shared_pairs, shared_accuracy, model_disagreement,
                              load_long_range_temperature, long_range_summary,
                              automatic_run_pair, selected_run_pairs)
from scoring.scorer import paired_score_rows
from scoring.precipitation import (METRIC as RAIN, LABELS as RAIN_LABELS,
                                   WET_THRESHOLD, WET_THRESHOLDS, DRY_CONTEXT, metrics as rain_metrics)
from collection_health import load_collection_health, yr_stale_warning
from weathernext_status import load_weathernext_status, load_weathernext_counts

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
BACKGROUND_LOG_PATH = Path(
    os.getenv("WEATHERAPP_BACKGROUND_LOG_PATH", BASE_DIR / "data" / "background.log")
)
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
        con, BACKGROUND_LOG_PATH, include_counts=False
    )
collection_health = load_collection_health(BACKGROUND_LOG_PATH)


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


def precipitation_summary(pairs):
    """Amount and event context together; never a rain winner or standalone MAE."""
    if pairs.empty:
        st.info("No fair shared hourly precipitation observations in this selection yet.")
        st.caption("0 shared samples · 0 stations · Evaluation period: —")
        return
    stats = rain_metrics(pairs).set_index('provider')
    st.caption(f"{len(pairs):,} shared samples · {pairs.location_id.nunique()} stations · "
               f"{pairs.drop_duplicates(['location_id','valid_at']).shape[0]:,} distinct targets · "
               f"Evaluation period (interval ends, UTC): {pairs.valid_at.min():%d %b %Y %H:%M} → {pairs.valid_at.max():%d %b %Y %H:%M}")
    for label, group in pairs.groupby('horizon', observed=True):
        suffix = ' · partial coverage' if label == RAIN_LABELS[-1] and min(group.met_lead_hours.max(), group.wn_lead_hours.max()) < 71 else ''
        st.caption(f"**{label}{suffix}**: actual leads Yr {group.met_lead_hours.min():.1f}–{group.met_lead_hours.max():.1f} h · "
                   f"WeatherNext {group.wn_lead_hours.min():.1f}–{group.wn_lead_hours.max():.1f} h")
    left, right = st.columns(2)
    with left:
        st.markdown("**Hourly amounts · mm/h**")
        amounts = stats[['wet_mae','mae','bias']].rename(columns={'wet_mae':'Wet-hour MAE','mae':'All-hour MAE','bias':'Bias'})
        st.dataframe(amounts.round(3), use_container_width=True, height=112, placeholder="—")
    with right:
        st.markdown(f"**Rain events · >{WET_THRESHOLD} mm/h**")
        events = (stats[['POD','FAR','CSI']].T * 100).rename(index={'POD':'Rain detected · POD %','FAR':'False alarms · FAR %','CSI':'Event skill · CSI %'})
        st.dataframe(events.round(1), use_container_width=True, height=140, placeholder="—")
    st.caption(f"{int(stats.wet.iloc[0]):,} wet / {int(stats.dry.iloc[0]):,} dry hours · "
               "POD: fraction of observed rain detected · FAR: fraction of predicted rain that was false · "
               "CSI: hits / (hits + misses + false alarms). Undefined rates are —.")
    st.caption(DRY_CONTEXT)
    with st.expander("Rain event counts and matching rules"):
        st.dataframe(stats[['hits','misses','false_alarms','correct_dry']].rename(columns={
            'hits':'Hits','misses':'Misses','false_alarms':'False alarms','correct_dry':'Correct dry'}), use_container_width=True)
        st.caption("Same physical hour [T−1h,T): Yr valid_at + 1h = WeatherNext end_time = Frost referenceTime. "
                   "Both issued and retrieved before interval start; leads measured to interval end, ≤3h apart, "
                   "same existing and precipitation buckets. Closest leads then newest runs; errors never select pairs. "
                   f"Wet observations and predictions are strictly >{WET_THRESHOLD} mm/h. Bias = forecast − observation. "
                   "WeatherNext ensemble mean; these are not rain probabilities. A target can recur across buckets.")


def accumulated_precipitation_summary(pairs, hours):
    """Compact verification of complete six-hour periods or UTC days."""
    label = '6-hour periods' if hours == 6 else 'UTC days'
    unit = 'mm/6h' if hours == 6 else 'mm/day'
    if pairs.empty:
        st.info(f"No fair shared complete {label} in this selection yet.")
        st.caption("0 shared periods · 0 stations · Evaluation period: —")
        return
    stats = rain_metrics(pairs, WET_THRESHOLDS[hours]).set_index('provider')
    distinct = pairs.drop_duplicates(['location_id', 'period_start']).shape[0]
    st.caption(f"{len(pairs):,} shared period/lead pairs · {distinct:,} distinct station {label} · "
               f"{pairs.location_id.nunique()} stations · "
               f"Evaluation period (UTC): {pairs.period_start.min():%d %b %Y %H:%M} → "
               f"{pairs.valid_at.max():%d %b %Y %H:%M}")
    for lead, group in pairs.groupby('horizon', observed=True):
        partial = ' · partial coverage' if (
            lead == RAIN_LABELS[-1] and min(group.met_lead_hours.max(), group.wn_lead_hours.max()) < 71
        ) else ''
        st.caption(f"**{lead}{partial}**: actual leads to period start: "
                   f"Yr {group.met_lead_hours.min():.1f}–{group.met_lead_hours.max():.1f} h · "
                   f"WeatherNext {group.wn_lead_hours.min():.1f}–{group.wn_lead_hours.max():.1f} h")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Accumulated amounts · {unit}**")
        amounts = stats[['wet_mae','mae','bias']].rename(columns={
            'wet_mae':'Wet-period MAE', 'mae':'MAE', 'bias':'Bias'})
        st.dataframe(amounts.round(3), use_container_width=True, height=112, placeholder="—")
    with right:
        st.markdown(f"**Rain events · >{WET_THRESHOLDS[hours]} {unit}**")
        events = (stats[['POD','FAR','CSI']].T * 100).rename(index={
            'POD':'Rain detected · POD %', 'FAR':'False alarms · FAR %',
            'CSI':'Event skill · CSI %'})
        st.dataframe(events.round(1), use_container_width=True, height=140, placeholder="—")
    st.caption(f"{int(stats.wet.iloc[0]):,} observed wet / {int(stats.dry.iloc[0]):,} dry {label} · "
               "MAE: average amount error · Wet MAE: amount error on observed wet periods · "
               "POD: observed rain detected · FAR: predicted rain that did not occur · "
               "CSI: event skill ignoring correctly dry periods. Undefined rates are —.")
    if hours == 24:
        st.caption("Daily results are preliminary: few independent UTC days; the same day may appear in multiple lead buckets.")
    else:
        st.caption("A period may appear in multiple lead buckets; shared pair counts are not independent events.")
    st.caption(DRY_CONTEXT)
    with st.expander("Rain event counts and matching rules"):
        st.dataframe(stats[['hits','misses','false_alarms','correct_dry']].rename(columns={
            'hits':'Hits','misses':'Misses','false_alarms':'False alarms',
            'correct_dry':'Correct dry'}), use_container_width=True)
        st.caption(f"Fixed, non-overlapping UTC windows; all {hours} aligned Frost, Yr and WeatherNext "
                   "hours required, with one complete run per provider. Both issues and all component "
                   "retrievals precede the window start. Leads are to window start, in the same "
                   "precipitation bucket and within 3 h. Closest leads then newest runs; forecast "
                   "errors never select pairs. Missing hours are excluded, never zero-filled. "
                   f"Wet is strictly >{WET_THRESHOLDS[hours]} {unit}. WeatherNext uses its ensemble mean.")

def accuracy_chart(rows, metric):
    rows = rows.copy()
    rows["provider"] = rows.provider.replace({MET_PROVIDER: "Yr/MET", WEATHERNEXT_PROVIDER: "WeatherNext"})
    return alt.Chart(rows).mark_bar().encode(
        x=alt.X("horizon:N", title="Lead time", sort=LEAD_LABELS, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(f"{metric}:Q", title="MAE (°C)" if metric == "MAE_C" else "MAE (m/s)"),
        xOffset="provider:N",
        color=alt.Color("provider:N", title=None, scale=alt.Scale(
            domain=["Yr/MET", "WeatherNext"], range=["#6099e8", "#55ad92"])),
        tooltip=["provider:N", "horizon:N", alt.Tooltip(f"{metric}:Q", format=".2f"), "samples:Q"],
    ).properties(height=230).configure_legend(orient="top")


health_sources = list(collection_health["sources"].values())
active_health = [row for row in health_sources if row["status"] != "OK"]
if not active_health:
    oldest_success = max(health_sources, key=lambda row: row["age_hours"])
    st.caption(f"● All collectors OK · All sources succeeded within {oldest_success['age']} · UTC")
else:
    st.warning("Collection attention: " + " · ".join(f"{row['label']}: {row['status']}" for row in active_health))
warning = yr_stale_warning(collection_health)
if warning:
    st.warning(warning)
with st.expander("Collection health details", expanded=False):
    health_table = pd.DataFrame(
        {
            "Source": row["label"],
            "Last success (UTC)": (
                row["last_success"].strftime("%Y-%m-%d %H:%M")
                if row["last_success"]
                else "—"
            ),
            "Age": row["age"],
            "Status": row["status"],
        }
        for row in collection_health["sources"].values()
    )
    st.dataframe(health_table, hide_index=True, use_container_width=True, height=143)
    st.caption("Completed source retrievals · Expected every 6 h · OK ≤8 h · Delayed ≤12 h · Stale >12 h")
    if collection_health["yr_gap"]:
        gap = collection_health["yr_gap"]
        st.caption(f"Recent Yr collection gap: {gap['hours']:.1f} h between {gap['start']:%d %b %H:%M} and {gap['end']:%d %b %H:%M} UTC.")


# Avoid running the expensive historical accuracy queries while browsing forecasts.
stateful_tabs = "on_change" in inspect.signature(st.tabs).parameters
pending = st.session_state.pop("inspect_disagreement", None)
if pending:
    st.session_state["comparison_mode"] = "Manual runs"
    station = int(pending["location_id"])
    st.session_state["forecast_actual_station"] = station
    st.session_state["forecast_variable"] = pending["metric"]
    st.session_state[f"met_run_{station}"] = int(pending["met_run_id"])
    st.session_state[f"wn_run_{station}"] = int(pending["wn_run_id"])
    if stateful_tabs:
        st.session_state["dashboard_tabs"] = "Forecast vs Actual"
forecast_tab, network_tab, accuracy_tab, long_range_tab, disagreement_tab = st.tabs(
    ["Forecast vs Actual", "Station network", "Overall accuracy", "Long-range temperature", "Model disagreement"],
    **({"on_change": "rerun", "key": "dashboard_tabs"} if stateful_tabs else {}),
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
            select_variable, select_station, select_mode, select_window = st.columns([1, 2.2, 1.6, 0.9], gap="small")
            metric = select_variable.selectbox("Variable", list(VARIABLES), format_func=lambda m: VARIABLES[m][0], key="forecast_variable")
            variable_label, unit = VARIABLES[metric]
            selected_location_id = select_station.selectbox(
                "Station",
                options=list(station_labels),
                format_func=station_labels.get,
                key="forecast_actual_station",
            )

            comparison_mode = select_mode.selectbox("Comparison", ["Automatic fair pair", "Manual runs"], key="comparison_mode")
            view_window = select_window.selectbox("Chart window", ["72 h", "7 days", "Full run"])
            now = pd.Timestamp.now(tz="UTC")
            automatic = comparison_mode == "Automatic fair pair"
            with connect() as con:
                auto_result = automatic_run_pair(con, selected_location_id, metric, view_window, now) if automatic else None
                met_runs = recent_runs(con, selected_location_id, MET_PROVIDER)
                wn_runs = recent_runs(con, selected_location_id, WEATHERNEXT_PROVIDER)

            if not met_runs or not wn_runs:
                missing = []
                if not met_runs:
                    missing.append("Yr/MET")
                if not wn_runs:
                    missing.append("WeatherNext")
                st.info(f"No stored {' and '.join(missing)} run is available for this station yet.")
            else:
                def run_label(run):
                    return pd.Timestamp(run["issued_at"]).strftime("%d %b · %H:%M")

                if automatic:
                    if auto_result['reason']:
                        st.info(auto_result['reason'])
                    if auto_result['pair']:
                        for prefix, runs in [('met', met_runs), ('wn', wn_runs)]:
                            chosen_run = auto_result['pair'][prefix]
                            if chosen_run['id'] not in [r['id'] for r in runs]:
                                runs.append(chosen_run)
                            st.session_state[f"{prefix}_run_{selected_location_id}"] = chosen_run['id']
                    else:
                        st.caption("Showing latest runs for inspection only; use Manual runs to choose others.")
                        st.session_state[f"met_run_{selected_location_id}"] = met_runs[0]['id']
                        st.session_state[f"wn_run_{selected_location_id}"] = wn_runs[0]['id']
                # Keep an automatically chosen older run selectable when entering manual mode.
                if not automatic:
                    with connect() as con:
                        for prefix, provider, runs in [('met', MET_PROVIDER, met_runs), ('wn', WEATHERNEXT_PROVIDER, wn_runs)]:
                            saved_id = st.session_state.get(f"{prefix}_run_{selected_location_id}")
                            if saved_id is not None and saved_id not in [r['id'] for r in runs]:
                                saved = con.execute('SELECT id, issued_at, retrieved_at FROM forecast_runs WHERE id=? AND location_id=? AND provider=?',
                                                    (saved_id, selected_location_id, provider)).fetchone()
                                if saved is not None:
                                    runs.append(dict(saved))
                with st.expander("Advanced / Manual run selection", expanded=not automatic):
                    if automatic:
                        st.caption("Choose Manual runs in Comparison to select independent runs.")
                    select_met, select_wn = st.columns(2)
                    met_run_id = select_met.selectbox(
                        "Yr/MET run", key=f"met_run_{selected_location_id}", disabled=automatic,
                        options=[run["id"] for run in met_runs],
                        format_func=lambda run_id: run_label(next(run for run in met_runs if run["id"] == run_id)))
                    wn_run_id = select_wn.selectbox(
                        "WeatherNext run", key=f"wn_run_{selected_location_id}", disabled=automatic,
                        options=[run["id"] for run in wn_runs],
                        format_func=lambda run_id: run_label(next(run for run in wn_runs if run["id"] == run_id)))
                met_run = next(r for r in met_runs if r['id'] == met_run_id)
                wn_run = next(r for r in wn_runs if r['id'] == wn_run_id)
                if automatic and auto_result['pair']:
                    st.caption(f"Auto pair: Yr {run_label(met_run)} · WeatherNext {run_label(wn_run)} UTC")

                with connect() as con:
                    timeline = load_timeline(
                        con, selected_location_id, met_run_id, wn_run_id, metric
                    )

                # Display only elapsed actuals; the selected runs remain unchanged.
                timeline.loc[timeline["valid_at"] > now, "actual_value"] = float("nan")
                if view_window != "Full run" and not timeline.empty:
                    cutoff = timeline["valid_at"].min() + pd.Timedelta(hours=72 if view_window == "72 h" else 168)
                    timeline = timeline[timeline["valid_at"] <= cutoff]
                past_rows = elapsed_rows(timeline, now)
                latest_actual = past_rows.iloc[-1] if not past_rows.empty else None
                paired = selected_run_pairs(timeline, met_run, wn_run, now, metric)
                if not automatic and paired.empty:
                    gap = abs((pd.Timestamp(met_run['issued_at']) - pd.Timestamp(wn_run['issued_at'])).total_seconds()) / 3600
                    if gap > 3:
                        st.info(f"These manual runs are {gap:.1f} h apart (fair comparison requires ≤3 h). Forecasts remain available for inspection.")
                    else:
                        st.info("No shared exact-time observations meet the fair comparison rules in this chart window yet.")
                if metric == RAIN:
                    stats = rain_metrics(paired)
                    cards = st.columns(4)
                    for card, (row, field, label) in zip(cards, [(stats.iloc[0], 'wet_mae', 'Yr wet-hour MAE'),
                            (stats.iloc[1], 'wet_mae', 'WeatherNext wet-hour MAE'),
                            (stats.iloc[0], 'CSI', 'Yr event skill · CSI'), (stats.iloc[1], 'CSI', 'WeatherNext event skill · CSI')]):
                        value = row[field]
                        card.metric(label, '—' if pd.isna(value) else (f"{value:.3f} mm/h" if field == 'wet_mae' else f"{100*value:.1f}%"))
                    st.caption(f"{len(paired):,} shared hours · {int(stats.wet.iloc[0])} wet / {int(stats.dry.iloc[0])} dry · "
                               "Hourly amounts plotted at interval end T for [T−1h,T). Leads are to interval end.")
                else:
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Latest observed", "—" if latest_actual is None else f"{latest_actual['actual_value']:.1f} {unit}")
                    m2.metric("Yr/MET MAE", "—" if paired.empty else f"{paired['met_abs_error'].mean():.2f} {unit}", help="Mean absolute error over shared observed hours for the selected runs.")
                    m3.metric("WeatherNext MAE", "—" if paired.empty else f"{paired['wn_abs_error'].mean():.2f} {unit}", help="Mean absolute error over the same shared observed hours as Yr/MET.")
                    m4.metric("Shared observed hours", len(paired))
                    if latest_actual is not None:
                        st.caption(f"Latest observation: {latest_actual['valid_at']:%d %b %H:%M UTC} · WeatherNext ensemble mean · Frost at forecast valid time")

                timeline = timeline.copy()
                timeline["time_utc"] = timeline["valid_at"].dt.strftime("%d %b %H:%M UTC")
                chart_lines = timeline[
                    ["valid_at", "time_utc", "met_value", "wn_value"]
                ].melt(
                    id_vars=["valid_at", "time_utc"],
                    var_name="series",
                    value_name="value",
                )
                chart_lines["series"] = chart_lines["series"].map(
                    {"met_value": "Yr/MET", "wn_value": "WeatherNext"}
                )
                lead_lookup = timeline.set_index("valid_at")
                chart_lines["lead_hours"] = chart_lines.valid_at.map(lead_lookup.met_lead_hours).where(
                    chart_lines.series == "Yr/MET", chart_lines.valid_at.map(lead_lookup.wn_lead_hours))
                chart_lines["issued"] = chart_lines["series"].map({
                    "Yr/MET": run_label(next(r for r in met_runs if r["id"] == met_run_id)),
                    "WeatherNext": run_label(next(r for r in wn_runs if r["id"] == wn_run_id))})
                colors = alt.Scale(
                    domain=["Yr/MET", "WeatherNext", "Frost actual"],
                    range=["#6099e8", "#55ad92", "#dfa44e"],
                )
                forecast_lines = (
                    alt.Chart(chart_lines.dropna(subset=["value"]))
                    .mark_line(strokeWidth=1.7)
                    .encode(
                        x=alt.X("valid_at:T", title="Interval end (UTC)" if metric == RAIN else "Time (UTC)", scale=alt.Scale(type="utc"),
                                axis=alt.Axis(labelExpr="utcFormat(datum.value, '%d %b %H:%M')", tickCount=8)),
                        y=alt.Y("value:Q", title=f"{variable_label} ({unit})", scale=alt.Scale(zero=False)),
                        color=alt.Color("series:N", title=None, scale=colors),
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("series:N", title="Source"),
                            alt.Tooltip("issued:N", title="Run UTC"),
                            alt.Tooltip("lead_hours:Q", title="Lead hours", format=".1f"),
                            alt.Tooltip("value:Q", title=f"{variable_label} {unit}", format=".1f"),
                        ],
                    )
                )
                uncertainty = (
                    alt.Chart(timeline.dropna(subset=["wn_p10", "wn_p90"]))
                    .mark_area(color="#55ad92", opacity=0.09)
                    .encode(
                        x=alt.X("valid_at:T", scale=alt.Scale(type="utc")),
                        y=alt.Y("wn_p10:Q", title=f"{variable_label} ({unit})", scale=alt.Scale(zero=False)),
                        y2="wn_p90:Q",
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("wn_p10:Q", title=f"WeatherNext p10 {unit}", format=".1f"),
                            alt.Tooltip("wn_p90:Q", title=f"WeatherNext p90 {unit}", format=".1f"),
                        ],
                    )
                )
                actual_data = timeline.dropna(subset=["actual_value"]).copy()
                actual_data["series"] = "Frost actual"
                actual_line = (
                    alt.Chart(actual_data)
                    .mark_line(point=alt.OverlayMarkDef(size=13, filled=True), strokeWidth=2)
                    .encode(
                        x=alt.X("valid_at:T", scale=alt.Scale(type="utc")),
                        y=alt.Y("actual_value:Q", title=f"{variable_label} ({unit})", scale=alt.Scale(zero=False)),
                        color=alt.Color("series:N", title=None, scale=colors),
                        tooltip=[
                            alt.Tooltip("time_utc:N", title="Time"),
                            alt.Tooltip("actual_value:Q", title=f"Frost actual {unit}", format=".1f"),
                        ],
                    )
                )
                now_rule = (
                    alt.Chart(pd.DataFrame({"now": [now] if not timeline.empty and timeline["valid_at"].min() <= now <= timeline["valid_at"].max() else []}))
                    .mark_rule(color="#929aa6", strokeDash=[3, 4], strokeWidth=1, opacity=0.7)
                    .encode(x=alt.X("now:T", scale=alt.Scale(type="utc")))
                )
                st.altair_chart(
                    polish_chart(alt.layer(uncertainty, forecast_lines, actual_line, now_rule)
                    .properties(height=245).interactive()),
                    use_container_width=True,
                )
                if metric == RAIN:
                    precipitation_summary(paired)
                else:
                    st.caption("Shading: WeatherNext p10–p90 · Dashed line: now · MAE: shared targets, leads ≤3 h apart in the same bucket, collected before valid time")
                if metric == "wind_speed":
                    st.caption("Wind speed at 10 m · Frost: preceding 10-minute mean · WeatherNext: gridded ensemble mean")
                if paired.empty and not past_rows.empty:
                    st.caption("No comparable observed targets for these runs. Choose runs issued closer together.")

                table_rows = past_rows[
                    [
                        "valid_at",
                        "met_value",
                        "wn_value",
                        "actual_value",
                        "met_lead_hours",
                        "wn_lead_hours",
                        "met_abs_error",
                        "wn_abs_error",
                    ]
                ].copy()
                table_rows.columns = [
                    "Time (UTC)",
                    "Yr",
                    "WeatherNext",
                    "Actual",
                    "Yr lead h",
                    "WN lead h",
                    "Yr |error|",
                    "WN |error|",
                ]
                table_rows = table_rows.sort_values("Time (UTC)", ascending=False)
                numeric_columns = table_rows.columns[1:]
                table_rows[numeric_columns] = table_rows[numeric_columns].round(1)

                table_c1, table_c2 = st.columns([3, 2])
                with table_c1:
                    st.markdown(f"**Recent results · {unit}**")
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
                    if metric != RAIN:
                        st.markdown("**MAE by forecast lead time**")
                        mae_rows = mae_by_lead_bucket(paired.rename(columns={"met_value": "met_temperature", "wn_value": "wn_temperature", "actual_value": "actual_temperature"}))
                        if mae_rows.empty:
                            st.caption("MAE appears when forecast timestamps have matching Frost observations.")
                        else:
                            mae_chart = (
                                alt.Chart(mae_rows)
                                .mark_point(filled=True, size=75, opacity=1)
                                .encode(
                                    y=alt.Y("lead bucket:N", title=None, sort=None, axis=alt.Axis(grid=False)),
                                    x=alt.X("MAE:Q", title=f"MAE ({unit}) · lower is better", scale=alt.Scale(zero=True), axis=alt.Axis(grid=True, tickCount=4)),
                                    yOffset="provider:N",
                                    shape=alt.Shape("provider:N", title=None, scale=alt.Scale(domain=["Yr/MET", "WeatherNext"], range=["circle", "diamond"])),
                                    color=alt.Color("provider:N", title=None, scale=alt.Scale(
                                        domain=["Yr/MET", "WeatherNext"], range=["#6099e8", "#55ad92"])),
                                    tooltip=[
                                        alt.Tooltip("provider:N", title="Provider"),
                                        alt.Tooltip("lead bucket:N", title="Lead time"),
                                        alt.Tooltip("MAE:Q", title=f"MAE {unit}", format=".2f"),
                                        alt.Tooltip("samples:Q", title="Matched hours"),
                                    ],
                                )
                                .properties(height=max(65, min(155, mae_rows["lead bucket"].nunique() * 38)))
                            )
                            st.altair_chart(polish_chart(mae_chart), use_container_width=True)
                            st.caption("Shared targets in the same lead bucket · hover for sample counts.")
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
        with connect() as con:
            stations = comparison_stations(con)
        names = {row["id"]: row["station_name"].title() for row in stations}
        c1, c2, c3, c4 = st.columns([1, 1, 2, 1])
        accuracy_metric = c1.selectbox("Variable", list(VARIABLES), format_func=lambda m: VARIABLES[m][0], key="accuracy_variable")
        period = c2.selectbox("Period", ["24 h", "7 days", "30 days", "All available"], index=1, key="accuracy_period")
        station_id = c3.selectbox("Station", [None, *names], format_func=lambda sid: "All stations" if sid is None else names[sid], key="accuracy_station")
        lead_options = [*RAIN_LABELS, "All buckets"] if accuracy_metric == RAIN else ["All buckets", *LEAD_LABELS]
        lead_key = 'rain_horizon' if accuracy_metric == RAIN else 'accuracy_horizon'
        horizon = c4.selectbox("Lead time", lead_options, index=1 if accuracy_metric == RAIN else 0, key=lead_key)
        accumulation_hours = 1
        if accuracy_metric == RAIN:
            accumulation = st.selectbox("Accumulation", ["1h", "6h", "24h"], key="rain_accumulation")
            accumulation_hours = {"1h": 1, "6h": 6, "24h": 24}[accumulation]
        unit = VARIABLES[accuracy_metric][1]
        with connect() as con:
            pairs = load_shared_pairs(con, accuracy_metric, {"24 h": 1, "7 days": 7, "30 days": 30, "All available": None}[period], station_id, accumulation_hours=accumulation_hours)
        if horizon != "All buckets":
            pairs = pairs[pairs.horizon == horizon]
        if accuracy_metric == RAIN:
            if accumulation_hours == 1:
                precipitation_summary(pairs)
            else:
                accumulated_precipitation_summary(pairs, accumulation_hours)
        elif pairs.empty:
            st.info("No shared observations with comparable forecast leads in this selection yet.")
        else:
            scored = paired_score_rows(pairs)
            totals = scored.groupby("provider").agg(MAE=("abs_error", "mean"), bias=("signed_error", "mean"), samples=("abs_error", "size"))
            m1, m2, m3, m4 = st.columns(4)
            for card, provider, label in ((m1, MET_PROVIDER, "Yr/MET"), (m2, WEATHERNEXT_PROVIDER, "WeatherNext")):
                row = totals.loc[provider]
                card.metric(f"{label} MAE", f"{row.MAE:.2f} {unit}")
                card.caption(f"Bias {row.bias:+.2f} {unit} · n={int(row.samples):,}")
            difference = totals.loc[WEATHERNEXT_PROVIDER, "MAE"] - totals.loc[MET_PROVIDER, "MAE"]
            m3.metric("MAE difference", f"{difference:+.2f} {unit}", help="WeatherNext minus Yr/MET. Positive means lower error for Yr/MET; negative means lower error for WeatherNext.")
            m3.caption("WeatherNext − Yr/MET")
            m4.metric("Shared samples", f"{len(pairs):,}")
            m4.caption(f"{pairs.location_id.nunique()} stations · {pairs.drop_duplicates(['location_id','valid_at']).shape[0]:,} targets")
            board = shared_accuracy(pairs, accuracy_metric)
            left, right = st.columns(2)
            with left:
                st.markdown("**MAE by lead time**")
                st.altair_chart(accuracy_chart(board, "MAE_C" if accuracy_metric == "air_temperature" else "MAE_ms"), use_container_width=True)
            with right:
                st.markdown("**Daily accuracy · shared targets**")
                scored["day"] = scored.valid_at.dt.floor("D")
                daily = scored.groupby(["day", "provider"], as_index=False).agg(MAE=("abs_error", "mean"), samples=("abs_error", "size"))
                daily["day_label"] = daily.day.dt.strftime("%d %b")
                daily["provider"] = daily.provider.replace({MET_PROVIDER: "Yr/MET", WEATHERNEXT_PROVIDER: "WeatherNext"})
                chart = alt.Chart(daily).mark_line(point=True).encode(
                    x=alt.X("day_label:O", title="Valid day (UTC)", sort=None, axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("MAE:Q", title=f"MAE ({unit})", scale=alt.Scale(zero=True)),
                    color=alt.Color("provider:N", scale=alt.Scale(domain=["Yr/MET", "WeatherNext"], range=["#6099e8", "#55ad92"])),
                    tooltip=["provider:N", alt.Tooltip("day:T", format="%d %b"), alt.Tooltip("MAE:Q", format=".2f"), "samples:Q"])
                st.altair_chart(polish_chart(chart.properties(height=230)), use_container_width=True)
            st.caption(f"One pair per station/time/lead bucket · Same observed targets · Mean lead gap {pairs.lead_gap.mean():.1f} h (maximum 3 h)")
            with st.expander("Score details and matching rules"):
                st.caption("Period filters forecast valid time. Use the closest forecast leads within the same existing bucket; break ties with the newest runs. Both forecasts must have been collected before valid time. Each station/time may appear once in each bucket. Bias = forecast − actual. Missing or conflicting exact-time observations are excluded.")
                st.dataframe(board.round(2), hide_index=True, use_container_width=True)
                by_station = scored.groupby(["station", "provider"], as_index=False).agg(MAE=("abs_error", "mean"), bias=("signed_error", "mean"), samples=("abs_error", "size"))
                st.dataframe(by_station.round(2), hide_index=True, use_container_width=True)
                st.caption("Lead times are close, not identical. Gridded wind differs from a station's 10-minute mean. No combined score across units.")


with long_range_tab:
    if not stateful_tabs or long_range_tab.open:
        st.markdown("**Temperature · 3, 5, 7 and 9 days ahead**")
        st.caption("Retrospective evaluation · Includes verified historical WeatherNext forecasts · Lower MAE is better")
        with connect() as con:
            long_stations = comparison_stations(con)
        long_names = {row["id"]: row["station_name"].title() for row in long_stations}
        c1, c2 = st.columns([1, 2])
        long_period = c1.selectbox("Evaluation window", ["All available", "30 days", "7 days", "24 h"], key="long_range_period")
        long_station = c2.selectbox("Station", [None, *long_names],
            format_func=lambda sid: "All stations" if sid is None else long_names[sid], key="long_range_station")
        with connect() as con:
            long_pairs = load_long_range_temperature(con,
                days={"All available": None, "30 days": 30, "7 days": 7, "24 h": 1}[long_period],
                location_id=long_station)
        summary = long_range_summary(long_pairs)
        if long_pairs.empty:
            st.info("No shared long-range temperature targets in this selection yet. Try All available or another station.")
            st.caption("Evaluation period: no matched targets · Shared samples: 0")
        else:
            first, last = long_pairs.valid_at.min(), long_pairs.valid_at.max()
            st.caption(f"Evaluation period (matched targets, UTC): {first:%d %b %Y %H:%M} – {last:%d %b %Y %H:%M} · {long_pairs.location_id.nunique()} stations")
        display = pd.DataFrame({
            "Ahead": summary.horizon.map(lambda h: f"{h // 24} days"),
            "Yr MAE °C": summary.yr_mae, "WeatherNext MAE °C": summary.wn_mae,
            "Δ MAE °C": summary.difference, "Shared samples": summary.samples,
            "Matched dates (UTC)": summary.apply(lambda r: "—" if not r.samples else
                f"{r.period_start:%d %b} – {r.period_end:%d %b}", axis=1),
        })
        st.dataframe(display, hide_index=True, use_container_width=True, height=178,
            column_config={name: st.column_config.NumberColumn(format="%.3f")
                           for name in ["Yr MAE °C", "WeatherNext MAE °C", "Δ MAE °C"]})
        st.caption("Shared samples = the same station/time targets for both models at each horizon. Δ = WeatherNext − Yr; negative favors WeatherNext. Empty horizons have no score.")
        if not long_pairs.empty:
            historical_count = int(summary.historical_samples.sum())
            st.caption(f"{historical_count:,} shared comparisons use verified historical forecasts. Short evaluation periods and slightly different leads can affect the result.")
        with st.expander("Bias, actual leads and matching rules"):
            st.caption("Both forecasts were issued before the observed time. Historical WeatherNext publication is verified before that time; local retrieval may be later. Unverified forecasts must have been collected before the target. Local collection dates are preserved.")
            st.caption("Exact Frost timestamps · Both leads within ±3 h of 72/120/168/216 h · Pair gap ≤3 h · One closest-lead pair per station/time/horizon, selected without using errors. Operational accuracy keeps its collected-before-target rule.")
            detail = summary.rename(columns={"horizon":"Horizon h", "samples":"Shared samples", "stations":"Stations",
                "yr_bias":"Yr bias °C", "wn_bias":"WeatherNext bias °C", "yr_lead_min":"Yr lead min h",
                "yr_lead_max":"Yr lead max h", "wn_lead_min":"WN lead min h", "wn_lead_max":"WN lead max h",
                "mean_gap":"Mean gap h", "max_gap":"Max gap h", "historical_samples":"Historical samples",
                "period_start":"First target UTC", "period_end":"Last target UTC"})
            st.dataframe(detail[["Horizon h", "Shared samples", "Historical samples", "Stations", "First target UTC", "Last target UTC",
                "Yr bias °C", "WeatherNext bias °C", "Yr lead min h", "Yr lead max h", "WN lead min h", "WN lead max h",
                "Mean gap h", "Max gap h"]].round(3), hide_index=True, use_container_width=True)


with disagreement_tab:
    if not stateful_tabs or disagreement_tab.open:
        c1, c2 = st.columns([1, 3])
        disagreement_metric = c1.selectbox("Variable", ["air_temperature", "wind_speed"], format_func=lambda m: VARIABLES[m][0], key="disagreement_variable")
        window = c2.selectbox("Future window", [72, 168, 360], format_func=lambda h: f"Next {h} hours", key="disagreement_window")
        unit = VARIABLES[disagreement_metric][1]
        with connect() as con:
            disagreements = model_disagreement(con, disagreement_metric, window)
        if disagreements.empty:
            st.info("No overlapping future forecasts for the latest stored runs yet.")
        else:
            top = disagreements.head(20).copy()
            top["target"] = top.station.str.title() + " · " + top.valid_at.dt.strftime("%d %b %H:%M")
            chart = alt.Chart(top.head(10)).mark_bar(color="#8496b0", cornerRadiusEnd=3).encode(
                y=alt.Y("target:N", sort="-x", title=None, axis=alt.Axis(labelLimit=290, labelOverlap=False)),
                x=alt.X("difference:Q", title=f"Absolute forecast difference ({unit})", axis=alt.Axis(tickCount=6)),
                tooltip=["station:N", alt.Tooltip("valid_at:T", title="Valid UTC"), alt.Tooltip("difference:Q", format=".1f"),
                         alt.Tooltip("met_value:Q", title="Yr/MET", format=".1f"), alt.Tooltip("wn_value:Q", title="WeatherNext", format=".1f")])
            st.altair_chart(polish_chart(chart.properties(height=250)), use_container_width=True)
            st.caption("Latest stored runs per station · Future shared times only · Run ages may differ; disagreement is not an accuracy score.")
            display = top[["station", "valid_at", "met_issued_at", "wn_issued_at", "met_lead_hours", "wn_lead_hours", "met_value", "wn_value", "difference"]].rename(columns={
                "station": "Station", "valid_at": "Valid UTC", "met_issued_at": "Yr run UTC", "wn_issued_at": "WN run UTC",
                "met_lead_hours": "Yr lead h", "wn_lead_hours": "WN lead h", "met_value": f"Yr {unit}", "wn_value": f"WN {unit}", "difference": f"Difference {unit}"})
            st.dataframe(display.round(1), hide_index=True, use_container_width=True, height=210, row_height=26,
                column_config={name: st.column_config.DatetimeColumn(format="DD MMM HH:mm")
                               for name in ["Valid UTC", "Yr run UTC", "WN run UTC"]})
            chosen = st.selectbox("Inspect forecast", list(top.index), format_func=lambda i: f"{top.loc[i, 'target']} UTC · Δ {top.loc[i, 'difference']:.1f} {unit}")
            if st.button("Inspect in Forecast vs Actual"):
                st.session_state["inspect_disagreement"] = {**top.loc[chosen].to_dict(), "metric": disagreement_metric}
                st.rerun()


with st.expander("WeatherNext system status"):
    st.caption(
        f"{weathernext_status['collector_status'].title()} · "
        f"Run {display_timestamp(weathernext_status['latest_run'])}"
    )
    st.caption(f"Last attempt: {display_timestamp(weathernext_status['last_attempt'])} · Last success: {display_timestamp(weathernext_status['last_success'])} · Latest additions: {weathernext_status['new_values'] if weathernext_status['new_values'] is not None else '—'}")
    counts_detail = st.session_state.get("weathernext_counts")
    if counts_detail and (
        counts_detail["latest_run"] != weathernext_status["latest_run"]
        or counts_detail["last_attempt"] != weathernext_status["last_attempt"]
    ):
        st.session_state.pop("weathernext_counts", None)
    if st.button("Refresh stored-data counts"):
        with connect() as con:
            st.session_state["weathernext_counts"] = {
                **load_weathernext_counts(con),
                "checked_at": pd.Timestamp.now(tz="UTC").isoformat(),
                "latest_run": weathernext_status["latest_run"],
                "last_attempt": weathernext_status["last_attempt"],
            }
    counts_detail = st.session_state.get("weathernext_counts")
    if counts_detail:
        st.caption(
            f"Stored forecasts: {counts_detail['forecast_points']:,} points · "
            f"{counts_detail['statistic_values']:,} statistic values · "
            f"Latest stored sample {display_timestamp(counts_detail['stored_at'])} · "
            f"Checked {display_timestamp(counts_detail['checked_at'])}"
        )
    else:
        st.caption("Stored-data counts are available on request.")
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
            st.session_state.pop("weathernext_counts", None)
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
