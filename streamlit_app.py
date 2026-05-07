"""
Sentinel Fleet Ops — analytics demo for an autonomous sensor tower fleet.

A dual-audience operations dashboard with three persona tabs:
  - Operations:  ground truth on the fleet today (where, what, what's broken)
  - Reliability: long-horizon component health and MTBF
  - Data Trust:  pipeline freshness and dbt test results

Reads from a pre-built DuckDB file produced by dbt-duckdb. dbt does not run at
serve time; it ran offline and compiled marts to data/sentinel.duckdb.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "sentinel.duckdb"
RUN_RESULTS = ROOT / "dbt" / "target" / "run_results.json"
MANIFEST = ROOT / "dbt" / "target" / "manifest.json"

st.set_page_config(
    page_title="Sentinel Fleet Ops",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Sentinel Fleet Ops")
    st.caption(
        "Analytics demo for a fleet of autonomous sensor towers. "
        "Synthetic data, dbt + DuckDB, three persona views."
    )

    sites_df = q("select site_id, site_name, region from dim_site order by site_name")
    site_options = ["All sites"] + [
        f"{r.site_name} ({r.site_id})" for r in sites_df.itertuples()
    ]
    site_selection = st.selectbox("Site filter", site_options)
    if site_selection == "All sites":
        site_filter_clause = ""
        site_filter_label = "all sites"
    else:
        sid = site_selection.split("(")[-1].rstrip(")")
        site_filter_clause = f"and site_id = '{sid}'"
        site_filter_label = site_selection

    st.markdown("---")
    st.caption("Stack")
    st.markdown(
        "- Python · DuckDB · dbt-duckdb\n"
        "- Streamlit · Plotly\n"
        "- 7 sources · 6 marts · 39 tests"
    )
    st.caption("Built by Ravi Rajpurohit · [ravirajpurohit.com](https://ravirajpurohit.com)")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Sentinel Fleet Ops")
st.caption(
    "A dual-audience operations dashboard for an autonomous sensor tower fleet. "
    "Same fact layer, three personas: operations, reliability, data engineering."
)

# Top-line KPIs
kpi = q(f"""
    with active_t as (
        select count(*) as n_active from dim_tower
        where status = 'active' {site_filter_clause}
    ),
    open_inc as (
        select count(*) as n_open from stg_incidents i
        join dim_tower t using (tower_id)
        where i.closed_at is null {site_filter_clause}
    ),
    crit_inc as (
        select count(*) as n_crit from stg_incidents i
        join dim_tower t using (tower_id)
        where i.closed_at is null and i.severity in ('P1','P2') {site_filter_clause}
    ),
    avg_uptime as (
        select avg(comms_uptime_pct) as up
        from fct_fleet_health_daily
        where health_date >= current_date - 7 {site_filter_clause}
    ),
    failed_comp as (
        select count(*) as n_failed from fct_component_reliability
        where is_failed and failed_at >= current_timestamp - interval 30 day
              {site_filter_clause}
    )
    select
        (select n_active from active_t) as active_towers,
        (select n_open from open_inc) as open_incidents,
        (select n_crit from crit_inc) as critical_open,
        (select up from avg_uptime) as uptime_7d,
        (select n_failed from failed_comp) as failed_components_30d
""").iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Active towers", int(kpi.active_towers))
c2.metric("Open incidents", int(kpi.open_incidents),
          delta=f"{int(kpi.critical_open)} critical",
          delta_color="inverse" if kpi.critical_open > 0 else "off")
c3.metric("Comms uptime (7d)", f"{kpi.uptime_7d:.1f}%" if pd.notna(kpi.uptime_7d) else "—")
c4.metric("Component failures (30d)", int(kpi.failed_components_30d))
c5.metric("Scope", site_filter_label)


tab_ops, tab_rel, tab_trust = st.tabs([
    "🛰  Operations", "🔧  Reliability", "✅  Data Trust"
])


# ---------------------------------------------------------------------------
# OPERATIONS TAB
# ---------------------------------------------------------------------------
with tab_ops:
    st.subheader("Fleet status by site")

    site_status = q(f"""
        select
            s.site_name,
            s.region,
            s.env,
            s.tower_count,
            s.active_tower_count,
            s.maintenance_tower_count,
            s.lat, s.lng
        from dim_site s
        where 1=1 {site_filter_clause.replace('site_id', 's.site_id')}
        order by s.tower_count desc
    """)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        fig = px.scatter_mapbox(
            site_status,
            lat="lat", lon="lng",
            size="tower_count",
            color="active_tower_count",
            hover_name="site_name",
            hover_data={"region": True, "env": True, "tower_count": True,
                        "active_tower_count": True, "lat": False, "lng": False},
            color_continuous_scale="Viridis",
            size_max=40,
            zoom=2,
            mapbox_style="carto-darkmatter",
            height=420,
        )
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        st.dataframe(
            site_status[["site_name", "region", "env",
                         "tower_count", "active_tower_count", "maintenance_tower_count"]]
            .rename(columns={
                "site_name": "Site", "region": "Region", "env": "Env",
                "tower_count": "Towers", "active_tower_count": "Active",
                "maintenance_tower_count": "Maint",
            }),
            hide_index=True, use_container_width=True, height=420,
        )

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Active deployments")
        active_deps = q(f"""
            select
                mission_name as Mission,
                tower_id as Tower,
                site_name as Site,
                start_ts as "Start",
                duration_days as "Days active"
            from fct_deployment_status
            where status = 'active' {site_filter_clause}
            order by start_ts desc
            limit 20
        """)
        st.dataframe(active_deps, hide_index=True, use_container_width=True)

    with col_b:
        st.subheader("Open incidents (P1–P2 first)")
        open_inc = q(f"""
            select
                i.incident_id as ID,
                i.severity as Sev,
                i.category as Category,
                i.tower_id as Tower,
                t.site_name as Site,
                i.opened_at as Opened,
                date_diff('hour', i.opened_at, current_timestamp) as "Age (hr)",
                i.root_cause as "Root cause"
            from stg_incidents i
            join dim_tower t using (tower_id)
            where i.closed_at is null {site_filter_clause}
            order by case i.severity when 'P1' then 1 when 'P2' then 2
                                     when 'P3' then 3 else 4 end,
                     i.opened_at
            limit 25
        """)
        st.dataframe(open_inc, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.subheader("Inventory — items below reorder point")
    low_inv = q("""
        select
            part_number as "Part #",
            description as Description,
            category as Category,
            on_hand as "On hand",
            allocated as Allocated,
            available as Available,
            reorder_point as "Reorder pt",
            stock_status as Status,
            lead_time_days as "Lead (days)"
        from fct_inventory_status
        where stock_status in ('critical', 'reorder', 'watch')
        order by case stock_status when 'critical' then 1 when 'reorder' then 2 else 3 end,
                 available
    """)
    if len(low_inv) == 0:
        st.success("All inventory above reorder thresholds.")
    else:
        st.dataframe(low_inv, hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# RELIABILITY TAB
# ---------------------------------------------------------------------------
with tab_rel:
    st.subheader("Component MTBF — actual vs target")

    mtbf = q(f"""
        select
            component_type,
            avg(mtbf_target_hours) as target_hours,
            avg(case when is_failed then observed_hours end) as actual_hours_when_failed,
            count(*) as installed,
            sum(case when is_failed then 1 else 0 end) as failed
        from fct_component_reliability
        where 1=1 {site_filter_clause}
        group by component_type
        order by component_type
    """)
    mtbf["failure_rate_pct"] = (mtbf["failed"] / mtbf["installed"] * 100).round(1)

    col_l, col_r = st.columns(2)
    with col_l:
        fig = px.bar(
            mtbf.melt(
                id_vars="component_type",
                value_vars=["target_hours", "actual_hours_when_failed"],
                var_name="metric", value_name="hours",
            ),
            x="component_type", y="hours", color="metric", barmode="group",
            labels={"component_type": "Component", "hours": "Hours"},
            color_discrete_map={
                "target_hours": "#5b8def",
                "actual_hours_when_failed": "#f04e4e",
            },
            height=380,
        )
        fig.update_layout(legend_title_text="", margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with col_r:
        st.dataframe(
            mtbf.rename(columns={
                "component_type": "Component",
                "target_hours": "Target hrs",
                "actual_hours_when_failed": "Actual when failed",
                "installed": "Installed",
                "failed": "Failed",
                "failure_rate_pct": "Failure %",
            }),
            hide_index=True, use_container_width=True, height=380,
        )

    st.markdown("---")
    st.subheader("Comms uptime trend (daily, fleet average)")
    uptime = q(f"""
        select
            health_date,
            avg(comms_uptime_pct) as uptime_pct,
            avg(avg_sensor_health) as sensor_health
        from fct_fleet_health_daily
        where 1=1 {site_filter_clause}
        group by health_date
        order by health_date
    """)
    fig = px.line(
        uptime.melt(id_vars="health_date",
                    value_vars=["uptime_pct", "sensor_health"],
                    var_name="metric", value_name="value"),
        x="health_date", y="value", color="metric",
        labels={"health_date": "Date", "value": "%"},
        color_discrete_map={"uptime_pct": "#5cd6a8", "sensor_health": "#d6c45c"},
        height=320,
    )
    fig.update_layout(legend_title_text="", margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Incidents by category — last 30 days")
        inc_cat = q(f"""
            select
                i.category as Category,
                i.severity as Severity,
                count(*) as Incidents
            from stg_incidents i
            join dim_tower t using (tower_id)
            where i.opened_at >= current_timestamp - interval 30 day
                  {site_filter_clause}
            group by i.category, i.severity
            order by Incidents desc
        """)
        if len(inc_cat) > 0:
            fig = px.bar(
                inc_cat, x="Category", y="Incidents", color="Severity",
                color_discrete_map={
                    "P1": "#d94343", "P2": "#e08641",
                    "P3": "#5b8def", "P4": "#7a8693",
                },
                height=320,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No incidents in the last 30 days for this filter.")

    with col_b:
        st.subheader("Top 10 root causes")
        top_rc = q(f"""
            select
                i.root_cause as "Root cause",
                i.category as Category,
                count(*) as Count
            from stg_incidents i
            join dim_tower t using (tower_id)
            where 1=1 {site_filter_clause}
            group by i.root_cause, i.category
            order by Count desc
            limit 10
        """)
        st.dataframe(top_rc, hide_index=True, use_container_width=True, height=320)


# ---------------------------------------------------------------------------
# DATA TRUST TAB
# ---------------------------------------------------------------------------
with tab_trust:
    st.subheader("Pipeline run status")

    rr = load_run_results()
    if not rr:
        st.warning("dbt run_results.json not found. Run `dbt build` from the dbt/ directory.")
    else:
        results = rr.get("results", [])
        ts = rr.get("generated_at")
        elapsed = rr.get("elapsed_time", 0)

        n_pass = sum(1 for r in results if r.get("status") == "pass")
        n_ok = sum(1 for r in results if r.get("status") in ("success", "pass"))
        n_fail = sum(1 for r in results if r.get("status") not in ("success", "pass", "skipped"))
        n_total = len(results)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total steps", n_total)
        m2.metric("Passed", n_ok)
        m3.metric("Failed", n_fail, delta_color="inverse")
        m4.metric("Elapsed", f"{elapsed:.2f}s")
        st.caption(f"Last run: {ts}")

        st.markdown("---")
        st.subheader("Tests by model")
        rows = []
        for r in results:
            uid = r.get("unique_id", "")
            kind = uid.split(".")[0] if uid else "unknown"
            rows.append({
                "kind": kind,
                "name": uid.split(".")[-1] if uid else "",
                "status": r.get("status"),
                "elapsed_s": round(r.get("execution_time", 0), 3),
            })
        rdf = pd.DataFrame(rows)
        if len(rdf) > 0:
            agg = (
                rdf.groupby("kind")
                   .agg(steps=("name", "count"),
                        passed=("status", lambda s: (s.isin(["pass", "success"])).sum()),
                        failed=("status", lambda s: (~s.isin(["pass", "success", "skipped"])).sum()),
                        avg_s=("elapsed_s", "mean"))
                   .reset_index()
                   .rename(columns={"kind": "Kind"})
            )
            agg["avg_s"] = agg["avg_s"].round(3)
            st.dataframe(agg, hide_index=True, use_container_width=True)

            st.markdown("---")
            st.subheader("Step detail")
            st.dataframe(
                rdf.rename(columns={
                    "kind": "Kind", "name": "Name",
                    "status": "Status", "elapsed_s": "Elapsed (s)",
                }),
                hide_index=True, use_container_width=True, height=420,
            )

    st.markdown("---")
    st.subheader("Mart freshness")
    freshness = q("""
        with sources as (
            select 'telemetry'      as source, max(ts)         as last_ts from stg_telemetry
            union all
            select 'incidents'      as source, max(opened_at)  as last_ts from stg_incidents
            union all
            select 'deployments'    as source, max(start_ts)   as last_ts from stg_deployments
            union all
            select 'inventory'      as source, max(last_updated) as last_ts from stg_inventory
        )
        select
            source as Source,
            last_ts as "Last record",
            date_diff('minute', last_ts, current_timestamp) as "Age (min)"
        from sources
        order by source
    """)
    st.dataframe(freshness, hide_index=True, use_container_width=True)
    st.caption(
        "Freshness is the age of the most recent record per source vs. wall-clock now. "
        "In production, sources.yml `freshness` rules raise warnings/errors when these gaps "
        "exceed thresholds — wired up in `dbt/models/staging/sources.yml`."
    )


st.markdown("---")
st.caption(
    "Synthetic data, deterministic via fixed seed. "
    "Source: github.com/ravi-rajpurohit-gh/sentinel-fleet-ops (private). "
    "See README for architecture and design notes."
)
