"""Sentinel Mission Analytics — detection intelligence, fleet sustainment, and
pipeline telemetry for the Sentry autonomous surveillance network. Reads from a
precompiled DuckDB file produced by the dbt build step."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "sentinel.duckdb"
RUN_RESULTS = ROOT / "dbt" / "target" / "run_results.json"


# ---------------------------------------------------------------------------
# Visual system
# ---------------------------------------------------------------------------
PALETTE = {
    "amber":   "#c99a2c",
    "amber_b": "#d4a042",
    "amber_l": "#e8b762",
    "teal":    "#4a8e9e",
    "sage":    "#6b8e7f",
    "tan":     "#a89c7f",
    "brick":   "#c14a3a",
    "warn":    "#d4884c",
    "grey":    "#8a8784",
    "fg":      "#e8e6e1",
    "fg_dim":  "#8a8784",
    "fg_xdim": "#5a5754",
    "bg":      "#0a0a0b",
    "bg2":     "#141416",
    "border":  "#222226",
}

CATEGORICAL = [
    PALETTE["amber"], PALETTE["teal"], PALETTE["sage"],
    PALETTE["tan"], PALETTE["brick"], PALETTE["warn"],
]
SEVERITY_COLORS = {
    "P1": PALETTE["brick"],
    "P2": PALETTE["warn"],
    "P3": PALETTE["tan"],
    "P4": PALETTE["grey"],
}


def style_chart(fig, *, height: int | None = None, show_legend: bool = True):
    fig.update_layout(
        font=dict(family="IBM Plex Sans, -apple-system, sans-serif",
                  color=PALETTE["fg"], size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=8, b=8),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["fg_dim"], size=11),
            title=None,
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right",  x=1,
        ),
        hoverlabel=dict(
            bgcolor=PALETTE["bg2"],
            font_color=PALETTE["fg"],
            bordercolor=PALETTE["border"],
            font_family="IBM Plex Mono, monospace",
        ),
        showlegend=show_legend,
    )
    fig.update_xaxes(
        gridcolor=PALETTE["border"],
        zerolinecolor=PALETTE["border"],
        color=PALETTE["fg_dim"],
        tickfont=dict(family="IBM Plex Mono, monospace", size=10),
        linecolor=PALETTE["border"],
    )
    fig.update_yaxes(
        gridcolor=PALETTE["border"],
        zerolinecolor=PALETTE["border"],
        color=PALETTE["fg_dim"],
        tickfont=dict(family="IBM Plex Mono, monospace", size=10),
        linecolor=PALETTE["border"],
    )
    if height:
        fig.update_layout(height=height)
    return fig


# ---------------------------------------------------------------------------
# App config + custom CSS
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Sentinel · Mission Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stMarkdown, .stApp {
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }

h1, h2, h3, h4 { font-family: 'IBM Plex Sans', sans-serif !important; color: #e8e6e1; }
h1 { font-size: 1.55rem; font-weight: 500; letter-spacing: -0.005em; margin-bottom: 0.15rem; }
h2 { font-size: 0.78rem; font-weight: 500; letter-spacing: 0.12em;
     text-transform: uppercase; color: #b0aea9; margin-top: 1.6rem; margin-bottom: 0.6rem; }
h3 { font-size: 0.75rem; font-weight: 500; letter-spacing: 0.12em;
     text-transform: uppercase; color: #8a8784; margin-top: 1.2rem; margin-bottom: 0.5rem; }

[data-testid="stMetric"] {
    background: rgba(255,255,255,0.012);
    border: 1px solid #222226;
    padding: 0.85rem 1rem 0.7rem;
    border-radius: 2px;
}
[data-testid="stMetricLabel"] p {
    color: #8a8784 !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
}
[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    font-weight: 500;
    color: #e8e6e1;
    font-family: 'IBM Plex Mono', monospace !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.72rem !important;
    font-family: 'IBM Plex Mono', monospace !important;
}

[data-testid="stTabs"] [role="tablist"] { border-bottom: 1px solid #222226; gap: 0; }
[data-testid="stTabs"] [role="tab"] {
    font-size: 0.78rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.12em;
    padding: 0.65rem 1.4rem; color: #8a8784; border-bottom: 2px solid transparent;
    background: transparent;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #e8e6e1; border-bottom-color: #c99a2c; background: transparent;
}

[data-testid="stCaptionContainer"], .stCaption {
    color: #8a8784; font-size: 0.78rem; line-height: 1.5;
}

[data-testid="stDataFrame"] { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; }

hr { border-color: #1a1a1d !important; margin: 1.4rem 0 1rem !important; }

[data-testid="stSidebar"] {
    background: #0c0c0d;
    border-right: 1px solid #1a1a1d;
}
[data-testid="stSidebar"] .stMarkdown h2 { margin-top: 0.6rem; }

.sfo-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 1px solid #222226;
    padding-bottom: 1rem; margin-bottom: 1.4rem;
}
.sfo-title { font-size: 0.7rem; letter-spacing: 0.18em; text-transform: uppercase;
             color: #8a8784; font-weight: 500; margin-bottom: 0.15rem; }
.sfo-name { font-size: 1.45rem; font-weight: 500; color: #e8e6e1; letter-spacing: -0.005em; }
.sfo-tag { color: #8a8784; font-size: 0.85rem; margin-top: 0.2rem; }

.sfo-status-pill {
    display: inline-flex; align-items: center; gap: 0.5rem;
    padding: 0.4rem 0.75rem; border: 1px solid; border-radius: 2px;
    font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
    font-family: 'IBM Plex Mono', monospace; font-weight: 500;
}
.sfo-status-ok    { color: #6b8e7f; border-color: #2c3a36; background: rgba(107,142,127,0.06); }
.sfo-status-warn  { color: #d4884c; border-color: #3e2e1f; background: rgba(212,136,76,0.06); }
.sfo-status-fail  { color: #c14a3a; border-color: #3e2422; background: rgba(193,74,58,0.06); }
.sfo-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.sfo-dot-ok   { background: #6b8e7f; box-shadow: 0 0 6px #6b8e7f; }
.sfo-dot-warn { background: #d4884c; box-shadow: 0 0 6px #d4884c; }
.sfo-dot-fail { background: #c14a3a; box-shadow: 0 0 6px #c14a3a; }

.sfo-footer {
    border-top: 1px solid #1a1a1d;
    padding-top: 0.9rem; margin-top: 2.5rem;
    color: #5a5754; font-size: 0.72rem;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.06em;
    display: flex; justify-content: space-between;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
.stDeployButton { display: none; }

div[data-baseweb="select"] > div {
    background: #141416 !important;
    border-color: #222226 !important;
}

[data-testid="stDataFrame"] [role="columnheader"],
[data-testid="stDataFrame"] [data-testid="StyledDataFrameHeader"],
[data-testid="stDataFrame"] thead th,
[data-testid="stDataFrame"] thead th > div {
    text-align: center !important;
    justify-content: center !important;
}
[data-testid="stDataFrame"] [role="columnheader"] > div,
[data-testid="stDataFrame"] [role="columnheader"] span {
    text-align: center !important;
    width: 100% !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=600)
def q(sql: str) -> pd.DataFrame:
    return get_conn().execute(sql).df()


@st.cache_data(ttl=600)
def load_run_results() -> dict:
    if not RUN_RESULTS.exists():
        return {}
    with open(RUN_RESULTS) as f:
        return json.load(f)


def get_generated_at(rr: dict) -> str:
    """Locate the build timestamp. dbt 1.10 puts it under metadata."""
    return (rr.get("metadata", {}) or {}).get("generated_at") or rr.get("generated_at") or ""


def pipeline_status() -> tuple[str, str, str]:
    rr = load_run_results()
    if not rr:
        return ("warn", "PIPELINE STATUS UNAVAILABLE", "")
    results = rr.get("results", [])
    n_total = len(results)
    n_pass = sum(1 for r in results if r.get("status") in ("pass", "success"))
    ts = get_generated_at(rr)
    if n_total == 0:
        return ("warn", "NO PIPELINE RUNS RECORDED", ts)
    if n_pass == n_total:
        return ("ok", f"PIPELINE NOMINAL · {n_pass}/{n_total}", ts)
    return ("fail", f"PIPELINE DEGRADED · {n_pass}/{n_total}", ts)


# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## Filters")

    sites_df = q("select site_id, site_name, region from dim_site order by site_name")
    site_options = ["All sites"] + [
        f"{r.site_name}  ·  {r.site_id}" for r in sites_df.itertuples()
    ]
    site_selection = st.selectbox("Site", site_options, label_visibility="visible")
    if site_selection == "All sites":
        site_filter_clause = ""
        site_label = "All sites"
    else:
        sid = site_selection.split("·")[-1].strip()
        site_filter_clause = f"and site_id = '{sid}'"
        site_label = site_selection.split("·")[0].strip()

    st.markdown("## Status")
    status_kind, status_text, status_ts = pipeline_status()
    status_html = (
        f'<div class="sfo-status-pill sfo-status-{status_kind}" style="display:flex">'
        f'<span class="sfo-dot sfo-dot-{status_kind}"></span>'
        f'<span>{status_text}</span></div>'
    )
    st.markdown(status_html, unsafe_allow_html=True)
    if status_ts:
        try:
            ts = datetime.fromisoformat(status_ts.replace("Z", "+00:00"))
            st.caption(f"Last build · {ts.strftime('%Y-%m-%d %H:%M UTC')}")
        except Exception:
            st.caption(f"Last build · {status_ts}")

    st.markdown("## Maintainer")
    st.caption("Ravi Rajpurohit  ·  [ravirajpurohit.com](https://ravirajpurohit.com)")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
last_telemetry_ts = q("select max(ts) as ts from stg_telemetry").iloc[0].ts
last_refresh_str = pd.Timestamp(last_telemetry_ts).strftime("%Y-%m-%d %H:%M UTC") \
                   if pd.notna(last_telemetry_ts) else "—"

header_html = f"""
<div class="sfo-header">
  <div>
    <div class="sfo-title">Sentinel · Mission Analytics</div>
    <div class="sfo-name">Sentinel Mission Analytics</div>
    <div class="sfo-tag">Detection intelligence, fleet sustainment, and pipeline telemetry for the Sentry autonomous surveillance network.</div>
  </div>
  <div style="text-align:right">
    <div class="sfo-status-pill sfo-status-{status_kind}">
      <span class="sfo-dot sfo-dot-{status_kind}"></span>
      <span>{status_text}</span>
    </div>
    <div style="margin-top:0.5rem; font-size:0.7rem; color:#5a5754;
                font-family:'IBM Plex Mono',monospace; letter-spacing:0.06em;">
      Last telemetry · {last_refresh_str}
    </div>
  </div>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Top-line KPIs
# ---------------------------------------------------------------------------
kpi = q(f"""
    with active_t as (
        select count(*) as n from dim_tower
        where status = 'active' {site_filter_clause}
    ),
    active_d as (
        select count(*) as n from fct_deployment_status
        where status = 'active' {site_filter_clause}
    ),
    open_inc as (
        select count(*) as n from stg_incidents i
        join dim_tower t using (tower_id)
        where i.closed_at is null {site_filter_clause}
    ),
    crit_inc as (
        select count(*) as n from stg_incidents i
        join dim_tower t using (tower_id)
        where i.closed_at is null and i.severity in ('P1','P2') {site_filter_clause}
    ),
    uptime_curr as (
        select avg(comms_uptime_pct) as up
        from fct_fleet_health_daily
        where health_date >= current_date - 7 {site_filter_clause}
    ),
    uptime_prev as (
        select avg(comms_uptime_pct) as up
        from fct_fleet_health_daily
        where health_date >= current_date - 14 and health_date < current_date - 7
              {site_filter_clause}
    ),
    failed_curr as (
        select count(*) as n from fct_component_reliability
        where is_failed and failed_at >= current_timestamp - interval 30 day
              {site_filter_clause}
    ),
    failed_prev as (
        select count(*) as n from fct_component_reliability
        where is_failed
          and failed_at >= current_timestamp - interval 60 day
          and failed_at <  current_timestamp - interval 30 day
              {site_filter_clause}
    ),
    inc_prev as (
        select count(*) as n from stg_incidents i
        join dim_tower t using (tower_id)
        where i.opened_at >= current_timestamp - interval 14 day
          and i.opened_at <  current_timestamp - interval 7 day
              {site_filter_clause}
    ),
    inc_curr_window as (
        select count(*) as n from stg_incidents i
        join dim_tower t using (tower_id)
        where i.opened_at >= current_timestamp - interval 7 day
              {site_filter_clause}
    )
    select
        (select n from active_t)               as active_towers,
        (select n from active_d)               as active_deployments,
        (select n from open_inc)               as open_incidents,
        (select n from crit_inc)               as critical_open,
        (select up from uptime_curr)           as uptime_7d,
        (select up from uptime_prev)           as uptime_prev_7d,
        (select n from failed_curr)            as failed_components_30d,
        (select n from failed_prev)            as failed_components_prev_30d,
        (select n from inc_curr_window)        as inc_opened_7d,
        (select n from inc_prev)               as inc_opened_prev_7d
""").iloc[0]

def _delta(curr, prev, good_direction: str = "down") -> str | None:
    """Return a formatted delta string. good_direction='down' means lower = better."""
    try:
        d = float(curr) - float(prev)
        if abs(d) < 0.05:
            return None
        return f"{d:+.1f}"
    except Exception:
        return None

uptime_delta = _delta(kpi.uptime_7d or 0, kpi.uptime_prev_7d or 0, good_direction="up")
fail_delta   = _delta(kpi.failed_components_30d, kpi.failed_components_prev_30d, good_direction="down")
inc_delta    = _delta(kpi.inc_opened_7d, kpi.inc_opened_prev_7d, good_direction="down")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Active Sentry Towers", int(kpi.active_towers))
c2.metric("Active Patrol Missions", int(kpi.active_deployments))
c3.metric("Open Incidents", int(kpi.open_incidents),
          delta=inc_delta, delta_color="inverse")
c4.metric("Critical Alerts · P1+P2", int(kpi.critical_open))
c5.metric(
    "Network Uptime · 7d",
    f"{kpi.uptime_7d:.1f}%" if pd.notna(kpi.uptime_7d) else "—",
    delta=uptime_delta,
)
c6.metric("Sensor Failures · 30d", int(kpi.failed_components_30d),
          delta=fail_delta, delta_color="inverse")


tab_ops, tab_det, tab_rel, tab_pipeline = st.tabs(
    ["Operations", "Detection Analytics", "Reliability", "Pipeline Health"]
)


# ---------------------------------------------------------------------------
# OPERATIONS
# ---------------------------------------------------------------------------
with tab_ops:
    st.markdown("## Sentry Deployment Map")

    site_status = q(f"""
        select s.site_name, s.site_id, s.region, s.env,
               s.tower_count, s.active_tower_count, s.maintenance_tower_count,
               s.lat, s.lng,
               coalesce(d.dets_7d, 0) as dets_7d,
               coalesce(d.open_incidents, 0) as open_incidents,
               case
                   when s.active_tower_count > 0
                   then round(coalesce(d.dets_7d, 0) * 1.0 / s.active_tower_count, 1)
                   else 0
               end as dets_per_active_tower
        from dim_site s
        left join (
            select site_id,
                   count(*) as dets_7d
            from fct_detection_events
            where detection_date >= current_date - 7
            group by site_id
        ) d on d.site_id = s.site_id
        left join (
            select t.site_id, count(*) as open_incidents
            from stg_incidents i
            join dim_tower t using (tower_id)
            where i.closed_at is null
            group by t.site_id
        ) inc on inc.site_id = s.site_id
        where 1=1 {site_filter_clause.replace('site_id', 's.site_id')}
        order by s.tower_count desc
    """)

    col_left, col_right = st.columns([1.4, 1])
    with col_left:
        fig = px.scatter_geo(
            site_status,
            lat="lat", lon="lng",
            size="active_tower_count",
            color="dets_per_active_tower",
            hover_name="site_name",
            hover_data={
                "region": True, "env": True,
                "active_tower_count": True,
                "dets_7d": True,
                "open_incidents": True,
                "dets_per_active_tower": True,
                "lat": False, "lng": False,
            },
            labels={
                "region": "Region", "env": "Terrain",
                "active_tower_count": "Active Towers",
                "dets_7d": "Detections (7d)",
                "open_incidents": "Open Incidents",
                "dets_per_active_tower": "Dets / Tower (7d)",
            },
            color_continuous_scale=[[0, PALETTE["teal"]],
                                    [0.5, PALETTE["amber"]],
                                    [1, PALETTE["brick"]]],
            scope="north america",
            size_max=28,
        )
        fig.update_geos(
            bgcolor="rgba(0,0,0,0)",
            showland=True,        landcolor=PALETTE["bg2"],
            showocean=True,       oceancolor=PALETTE["bg"],
            showlakes=True,       lakecolor=PALETTE["bg"],
            showcoastlines=True,  coastlinecolor=PALETTE["border"],
            showsubunits=True,    subunitcolor=PALETTE["border"],
            showcountries=True,   countrycolor=PALETTE["border"],
            showframe=False,
            fitbounds="locations",
            visible=True,
        )
        fig.update_traces(
            marker=dict(line=dict(width=0.5, color=PALETTE["bg"])),
        )
        fig.update_layout(
            coloraxis_colorbar=dict(
                title=dict(text="Dets/Tower", font=dict(size=10, color=PALETTE["fg_dim"])),
                tickfont=dict(size=10, color=PALETTE["fg_dim"]),
                thickness=10, len=0.5, x=1.0,
                outlinewidth=0,
            ),
            geo=dict(projection_scale=1.05),
        )
        style_chart(fig, height=480, show_legend=False)
        st.plotly_chart(fig, width="stretch")
        st.caption("Bubble size = active towers · Color = detection density (last 7 days per active tower)")
    with col_right:
        display = site_status[["site_name", "region", "env", "active_tower_count",
                               "maintenance_tower_count", "dets_7d", "open_incidents"]].copy()
        display.columns = ["Site", "Region", "Terrain", "Active", "Maintenance",
                           "Dets (7d)", "Open Incidents"]
        st.dataframe(display, hide_index=True, width="stretch", height=480)

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("## Active Patrol Missions")
        active_deps = q(f"""
            select
                mission_name  as "Mission",
                tower_id      as "Tower ID",
                site_name     as "Site",
                start_ts      as "Deployed",
                duration_days as "Days On Station"
            from fct_deployment_status
            where status = 'active' {site_filter_clause}
            order by start_ts desc
            limit 25
        """)
        if len(active_deps) == 0:
            st.markdown(
                '<div style="color:#8a8784; font-size:0.85rem; padding:0.6rem 0;">'
                'No active deployments under the current filter.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(active_deps, hide_index=True, width="stretch", height=360)

    with col_b:
        st.markdown("## Open Incidents")
        open_inc = q(f"""
            select
                i.incident_id as "Incident ID",
                i.severity    as "Sev",
                i.category    as "Subsystem",
                i.tower_id    as "Tower ID",
                t.site_name   as "Site",
                i.opened_at   as "Opened",
                date_diff('hour', i.opened_at, current_timestamp) as "Age (hrs)",
                i.root_cause  as "Root Cause"
            from stg_incidents i
            join dim_tower t using (tower_id)
            where i.closed_at is null {site_filter_clause}
            order by case i.severity when 'P1' then 1 when 'P2' then 2
                                     when 'P3' then 3 else 4 end,
                     i.opened_at
            limit 25
        """)
        if len(open_inc) == 0:
            st.markdown(
                '<div style="color:#6b8e7f; font-size:0.85rem; padding:0.6rem 0;">'
                'No incidents open under the current filter.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.dataframe(open_inc, hide_index=True, width="stretch", height=360)

    st.markdown("## Parts at Resupply Threshold")
    low_inv = q("""
        select
            part_number    as "Part Number",
            description    as "Component",
            category       as "Subsystem",
            on_hand        as "On Hand",
            allocated      as "Allocated",
            available      as "Available",
            reorder_point  as "Reorder Point",
            stock_status   as "Stock Status",
            lead_time_days as "Lead Time (days)"
        from fct_inventory_status
        where stock_status in ('critical', 'reorder', 'watch')
        order by case stock_status when 'critical' then 1 when 'reorder' then 2 else 3 end,
                 available
    """)
    if len(low_inv) == 0:
        st.markdown(
            '<div style="color:#6b8e7f; font-size:0.85rem; padding:0.6rem 0;">'
            'All tracked parts are above reorder thresholds.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.dataframe(low_inv, hide_index=True, width="stretch")


# ---------------------------------------------------------------------------
# DETECTION ANALYTICS
# ---------------------------------------------------------------------------
with tab_det:

    # ---- KPIs --------------------------------------------------------------
    det_kpi = q(f"""
        with base as (
            select * from fct_detection_events
            where 1=1 {site_filter_clause}
        ),
        window_7d as (select * from base where detection_date >= current_date - 7),
        window_prev as (
            select * from base
            where detection_date >= current_date - 14 and detection_date < current_date - 7
        )
        select
            (select count(*)                                         from base)           as total_dets,
            (select count(*)                                         from window_7d)      as dets_7d,
            (select count(*)                                         from window_prev)    as dets_prev_7d,
            (select round(avg(auto_resolved::int)*100,1)             from base)           as auto_resolve_pct,
            (select round(avg(escalated_to_operator::int)*100,1)     from base)           as escalation_pct,
            (select round(avg(false_positive::int)*100,1)            from base)           as fp_pct,
            (select round(avg(confidence_score)*100,1)               from base)           as avg_confidence
    """).iloc[0]

    lat_kpi = q(f"""
        select
            round(percentile_cont(0.50) within group (order by total_response_s), 0) as p50,
            round(percentile_cont(0.95) within group (order by total_response_s), 0) as p95,
            round(percentile_cont(0.99) within group (order by total_response_s), 0) as p99
        from fct_alert_pipeline_latency
        where 1=1 {site_filter_clause}
    """).iloc[0]

    delta_dets = int(det_kpi.dets_7d) - int(det_kpi.dets_prev_7d)
    delta_sign = f"+{delta_dets}" if delta_dets >= 0 else str(delta_dets)

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Detections · 7d", int(det_kpi.dets_7d), delta=delta_sign)
    k2.metric("Auto-Resolve Rate", f"{det_kpi.auto_resolve_pct:.1f}%")
    k3.metric("Escalation Rate", f"{det_kpi.escalation_pct:.1f}%")
    k4.metric("False Positive Rate", f"{det_kpi.fp_pct:.1f}%")
    k5.metric("Avg Confidence", f"{det_kpi.avg_confidence:.1f}%")

    st.markdown("## Detection Volume · By Target Class")

    vol = q(f"""
        select
            detection_date,
            target_class,
            count(*) as detections
        from fct_detection_events
        where 1=1 {site_filter_clause}
        group by detection_date, target_class
        order by detection_date, target_class
    """)
    if len(vol) > 0:
        CLASS_COLORS = {
            "human":   PALETTE["amber"],
            "vehicle": PALETTE["teal"],
            "UAS":     PALETTE["brick"],
            "unknown": PALETTE["grey"],
        }
        fig = px.bar(
            vol, x="detection_date", y="detections", color="target_class",
            labels={"detection_date": "", "detections": "Detections", "target_class": ""},
            color_discrete_map=CLASS_COLORS,
            category_orders={"target_class": ["human", "vehicle", "UAS", "unknown"]},
            barmode="stack",
        )
        fig.update_traces(marker_line_width=0)
        style_chart(fig, height=300)
        st.plotly_chart(fig, width="stretch")

    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        st.markdown("## Classification Breakdown")
        breakdown = q(f"""
            select
                target_class,
                count(*) as detections,
                round(avg(confidence_score)*100,1) as avg_confidence_pct,
                round(avg(false_positive::int)*100,1) as fp_rate_pct
            from fct_detection_events
            where 1=1 {site_filter_clause}
            group by target_class
            order by detections desc
        """)
        if len(breakdown) > 0:
            fig = px.bar(
                breakdown, x="detections", y="target_class",
                color="target_class",
                orientation="h",
                labels={"detections": "Total Detections", "target_class": ""},
                color_discrete_map=CLASS_COLORS,
                text="avg_confidence_pct",
            )
            fig.update_traces(
                texttemplate="%{text:.0f}% conf",
                textposition="inside",
                marker_line_width=0,
            )
            style_chart(fig, height=280, show_legend=False)
            st.plotly_chart(fig, width="stretch")

    with col_r:
        st.markdown("## Time-of-Day Pattern")
        tod = q(f"""
            select
                hour_of_day,
                count(*) as detections,
                round(avg(escalated_to_operator::int)*100,1) as escalation_pct
            from fct_detection_events
            where 1=1 {site_filter_clause}
            group by hour_of_day
            order by hour_of_day
        """)
        if len(tod) > 0:
            fig = px.bar(
                tod, x="hour_of_day", y="detections",
                labels={"hour_of_day": "Hour (UTC)", "detections": "Detections"},
                color="escalation_pct",
                color_continuous_scale=[[0, PALETTE["teal"]], [0.5, PALETTE["amber"]], [1, PALETTE["brick"]]],
            )
            fig.update_traces(marker_line_width=0)
            fig.update_layout(
                coloraxis_colorbar=dict(
                    title=dict(text="Escalation %", font=dict(size=10, color=PALETTE["fg_dim"])),
                    tickfont=dict(size=10, color=PALETTE["fg_dim"]),
                    thickness=10, len=0.6, x=1.0,
                    outlinewidth=0,
                )
            )
            style_chart(fig, height=280)
            st.plotly_chart(fig, width="stretch")

    st.markdown("## Alert Pipeline Latency")
    st.caption(
        "End-to-end response latency for escalated detections — from sensor trigger to operator "
        "resolution. P95/P99 degradation during overnight shifts reveals operator staffing pressure."
    )

    lat_stages = q(f"""
        select
            'Detection → Alert'      as stage,
            round(percentile_cont(0.50) within group (order by detection_to_alert_s),   1) as p50,
            round(percentile_cont(0.95) within group (order by detection_to_alert_s),   1) as p95,
            round(percentile_cont(0.99) within group (order by detection_to_alert_s),   1) as p99,
            round(avg(detection_to_alert_s), 1)   as avg_s
        from fct_alert_pipeline_latency where 1=1 {site_filter_clause}
        union all
        select
            'Alert → Operator Notified',
            round(percentile_cont(0.50) within group (order by alert_to_notify_s),   1),
            round(percentile_cont(0.95) within group (order by alert_to_notify_s),   1),
            round(percentile_cont(0.99) within group (order by alert_to_notify_s),   1),
            round(avg(alert_to_notify_s), 1)
        from fct_alert_pipeline_latency where 1=1 {site_filter_clause}
        union all
        select
            'Notified → Operator Ack',
            round(percentile_cont(0.50) within group (order by notify_to_ack_s),   1),
            round(percentile_cont(0.95) within group (order by notify_to_ack_s),   1),
            round(percentile_cont(0.99) within group (order by notify_to_ack_s),   1),
            round(avg(notify_to_ack_s), 1)
        from fct_alert_pipeline_latency where 1=1 {site_filter_clause}
        union all
        select
            'Ack → Resolved',
            round(percentile_cont(0.50) within group (order by ack_to_resolve_s),   1),
            round(percentile_cont(0.95) within group (order by ack_to_resolve_s),   1),
            round(percentile_cont(0.99) within group (order by ack_to_resolve_s),   1),
            round(avg(ack_to_resolve_s), 1)
        from fct_alert_pipeline_latency where 1=1 {site_filter_clause}
        union all
        select
            'Total Response',
            round(percentile_cont(0.50) within group (order by total_response_s),   1),
            round(percentile_cont(0.95) within group (order by total_response_s),   1),
            round(percentile_cont(0.99) within group (order by total_response_s),   1),
            round(avg(total_response_s), 1)
        from fct_alert_pipeline_latency where 1=1 {site_filter_clause}
    """)

    col_chart, col_table = st.columns([1.2, 1], gap="large")
    with col_chart:
        fig = px.bar(
            lat_stages[lat_stages["stage"] != "Total Response"],
            x="stage", y=["p50", "p95", "p99"],
            barmode="group",
            labels={"stage": "", "value": "Seconds", "variable": ""},
            color_discrete_map={
                "p50": PALETTE["teal"],
                "p95": PALETTE["amber"],
                "p99": PALETTE["brick"],
            },
        )
        fig.update_traces(marker_line_width=0)
        style_chart(fig, height=300)
        st.plotly_chart(fig, width="stretch")
    with col_table:
        lat_stages.columns = ["Stage", "P50 (s)", "P95 (s)", "P99 (s)", "Avg (s)"]
        st.dataframe(lat_stages, hide_index=True, width="stretch", height=228)

    st.markdown("## Per-Tower Detection Summary")
    tower_det = q(f"""
        select
            d.tower_id                                        as "Tower ID",
            d.site_name                                       as "Site",
            count(*)                                          as "Detections",
            round(avg(d.auto_resolved::int)*100, 1)          as "Auto-Resolve %",
            round(avg(d.escalated_to_operator::int)*100, 1)  as "Escalation %",
            round(avg(d.false_positive::int)*100, 1)         as "FP Rate %",
            round(avg(d.confidence_score)*100, 1)            as "Avg Confidence %"
        from fct_detection_events d
        where 1=1 {site_filter_clause}
        group by d.tower_id, d.site_name
        order by "Escalation %" desc
        limit 30
    """)
    st.dataframe(tower_det, hide_index=True, width="stretch", height=380)


# ---------------------------------------------------------------------------
# RELIABILITY
# ---------------------------------------------------------------------------
with tab_rel:
    st.markdown("## Sensor Subsystem MTBF · Target vs Observed")

    mtbf = q(f"""
        select
            component_type,
            avg(mtbf_target_hours)                         as target_hours,
            avg(case when is_failed then observed_hours end) as actual_hours_when_failed,
            count(*)                                       as installed,
            sum(case when is_failed then 1 else 0 end)     as failed
        from fct_component_reliability
        where 1=1 {site_filter_clause}
        group by component_type
        order by component_type
    """)
    mtbf["failure_rate_pct"] = (mtbf["failed"] / mtbf["installed"] * 100).round(1)

    col_l, col_r = st.columns([1.2, 1])
    with col_l:
        melted = mtbf.melt(
            id_vars="component_type",
            value_vars=["target_hours", "actual_hours_when_failed"],
            var_name="metric", value_name="hours",
        )
        melted["metric"] = melted["metric"].map({
            "target_hours": "Target",
            "actual_hours_when_failed": "Observed at failure",
        })
        fig = px.bar(
            melted, x="component_type", y="hours", color="metric",
            barmode="group",
            labels={"component_type": "", "hours": "Hours"},
            color_discrete_map={
                "Target": PALETTE["teal"],
                "Observed at failure": PALETTE["brick"],
            },
        )
        fig.update_traces(marker_line_width=0)
        style_chart(fig, height=360)
        st.plotly_chart(fig, width="stretch")
    with col_r:
        display = mtbf.copy()
        display.columns = ["Subsystem", "Target MTBF (hrs)", "Observed at Failure (hrs)",
                           "Units Deployed", "Failures", "Failure Rate (%)"]
        display["Target MTBF (hrs)"] = display["Target MTBF (hrs)"].round(0).astype(int)
        display["Observed at Failure (hrs)"] = display["Observed at Failure (hrs)"].round(0)
        st.dataframe(display, hide_index=True, width="stretch", height=360)

    st.markdown("## Network Uptime & Sensor Health · 30-Day Trend")
    uptime = q(f"""
        select health_date,
               avg(comms_uptime_pct) as uptime_pct,
               avg(avg_sensor_health) as sensor_health
        from fct_fleet_health_daily
        where 1=1 {site_filter_clause}
        group by health_date
        order by health_date
    """)
    melted = uptime.melt(
        id_vars="health_date",
        value_vars=["uptime_pct", "sensor_health"],
        var_name="metric", value_name="value",
    )
    melted["metric"] = melted["metric"].map({
        "uptime_pct": "Comms uptime %",
        "sensor_health": "Sensor health score",
    })
    fig = px.line(
        melted, x="health_date", y="value", color="metric",
        labels={"health_date": "", "value": ""},
        color_discrete_map={
            "Comms uptime %": PALETTE["amber"],
            "Sensor health score": PALETTE["teal"],
        },
    )
    fig.update_traces(line_width=2)
    style_chart(fig, height=300)
    st.plotly_chart(fig, width="stretch")

    col_a, col_b = st.columns(2, gap="large")
    with col_a:
        st.markdown("## Failures by Subsystem · Last 30 Days")
        inc_cat = q(f"""
            select i.category as Category, i.severity as Severity, count(*) as Count
            from stg_incidents i
            join dim_tower t using (tower_id)
            where i.opened_at >= current_timestamp - interval 30 day
                  {site_filter_clause}
            group by i.category, i.severity
            order by Count desc
        """)
        if len(inc_cat) > 0:
            fig = px.bar(
                inc_cat, x="Category", y="Count", color="Severity",
                color_discrete_map=SEVERITY_COLORS,
                category_orders={"Severity": ["P1", "P2", "P3", "P4"]},
            )
            fig.update_traces(marker_line_width=0)
            style_chart(fig, height=320)
            st.plotly_chart(fig, width="stretch")
        else:
            st.markdown(
                '<div style="color:#8a8784; font-size:0.85rem; padding:0.6rem 0;">'
                'No incidents in the last 30 days for the current filter.</div>',
                unsafe_allow_html=True,
            )

    with col_b:
        st.markdown("## Top Failure Signatures")
        top_rc = q(f"""
            select i.root_cause as "Root Cause", i.category as "Subsystem",
                   count(*) as "Incidents"
            from stg_incidents i
            join dim_tower t using (tower_id)
            where 1=1 {site_filter_clause}
            group by i.root_cause, i.category
            order by "Incidents" desc
            limit 10
        """)
        st.dataframe(top_rc, hide_index=True, width="stretch", height=320)


# ---------------------------------------------------------------------------
# PIPELINE HEALTH
# ---------------------------------------------------------------------------
with tab_pipeline:
    st.markdown("## Analytics Pipeline · Latest Build")

    rr = load_run_results()
    if not rr:
        st.markdown(
            '<div style="color:#d4884c; font-size:0.85rem; padding:0.6rem 0;">'
            'Pipeline run results unavailable. Run the build job to populate.</div>',
            unsafe_allow_html=True,
        )
    else:
        results = rr.get("results", [])
        elapsed = rr.get("elapsed_time", 0)

        n_total = len(results)
        n_ok = sum(1 for r in results if r.get("status") in ("pass", "success"))
        n_fail = sum(1 for r in results if r.get("status") not in ("pass", "success", "skipped"))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total steps", n_total)
        m2.metric("Passed", n_ok)
        m3.metric("Failed", n_fail)
        m4.metric("Elapsed (seconds)", f"{elapsed:.2f}")

        rows = []
        for r in results:
            uid = r.get("unique_id", "")
            parts = uid.split(".")
            kind = parts[0] if parts else "unknown"
            name = parts[-1] if parts else ""
            rows.append({
                "kind": kind, "name": name,
                "status": r.get("status"),
                "elapsed_s": round(r.get("execution_time", 0), 3),
            })
        rdf = pd.DataFrame(rows)

        st.markdown("## Steps by Kind")
        agg = (
            rdf.groupby("kind")
               .agg(steps=("name", "count"),
                    passed=("status", lambda s: s.isin(["pass", "success"]).sum()),
                    failed=("status",
                            lambda s: (~s.isin(["pass", "success", "skipped"])).sum()),
                    avg_s=("elapsed_s", "mean"))
               .reset_index()
        )
        agg["avg_s"] = agg["avg_s"].round(3)
        agg.columns = ["Kind", "Steps", "Passed", "Failed", "Average elapsed (seconds)"]
        st.dataframe(agg, hide_index=True, width="stretch")

        st.markdown("## Step Detail")
        rdf.columns = ["Kind", "Name", "Status", "Elapsed (seconds)"]
        st.dataframe(rdf, hide_index=True, width="stretch", height=420)

    st.markdown("## Source Freshness")
    freshness = q("""
        with sources as (
            select 'telemetry'   as source, max(ts)           as last_ts from stg_telemetry
            union all
            select 'incidents'   as source, max(opened_at)    as last_ts from stg_incidents
            union all
            select 'deployments' as source, max(start_ts)     as last_ts from stg_deployments
            union all
            select 'inventory'   as source, max(last_updated) as last_ts from stg_inventory
        )
        select source as "Source",
               last_ts as "Last record",
               date_diff('minute', last_ts, current_timestamp) as "Age (minutes)"
        from sources
        order by source
    """)
    st.dataframe(freshness, hide_index=True, width="stretch")
    st.caption(
        "Freshness measures the age of the most recent record per source against wall-clock now. "
        "Source-level warn/error thresholds are configured in dbt sources.yml. A stale telemetry "
        "feed or detection stream degrades situational awareness — this view surfaces lag before "
        "it affects operational decisions."
    )


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
gen_time = ""
rr = load_run_results()
gen_at = get_generated_at(rr) if rr else ""
if gen_at:
    try:
        ts = datetime.fromisoformat(gen_at.replace("Z", "+00:00"))
        gen_time = ts.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        gen_time = gen_at

build_segment = f"BUILD {gen_time}" if gen_time else "BUILD UNAVAILABLE"
st.markdown(
    f'<div class="sfo-footer">'
    f'<span>SENTINEL MISSION ANALYTICS  ·  {site_label.upper()}</span>'
    f'<span>{build_segment}</span>'
    f'</div>',
    unsafe_allow_html=True,
)
