# Changelog — Sentinel Mission Analytics

> **For Claude:** This file is the authoritative project history for `sentinel-fleet-ops`.
> Read it at the start of any new session to restore full context — purpose, decisions,
> current state, and what comes next.

---

## Project Context

**What:** A mission analytics platform for Anduril's Sentry autonomous surveillance network.
Synthetic data → dbt star schema on DuckDB → Streamlit dashboard.

**Why this exists:** Portfolio project for a Data/Analytics Engineer interview with Anduril's
Sentry Analytics team. Demonstrates: domain understanding of the Sentry product (detection
events, threat classification, alert pipeline), data engineering depth (embedded OLAP,
dbt star schema, pipeline testing), and analytical thinking.

**Live app:** https://sentinel-fleet-ops.streamlit.app/
**Repo:** https://github.com/ravi-rajpurohit-gh/sentinel-fleet-ops
**Local path:** /Users/ravirajpurohit/Downloads/Developer/sentinel-fleet-ops

**Stack:** Python · DuckDB (embedded OLAP) · dbt-duckdb · Streamlit · Plotly

---

## Key Architectural Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Keep DuckDB as embedded OLAP, not a server DB | Appropriate for air-gapped/edge deployments — maps to real Sentry field constraints. DuckDB ships precompiled with the repo; no external dependency at runtime. |
| D2 | Add detection events as a new data domain, not cosmetic changes | Generic ops dashboards don't impress. Sentry-specific data (target class, confidence, escalation) gives the app genuine domain depth. |
| D3 | Alert pipeline latency (P50/P95/P99 per stage) as the key new metric | Sentry's value is not just detecting targets but doing so fast enough for operators to respond. Latency stages expose where the pipeline slows down. |
| D4 | Deep refinement scope, not a full rebuild | The existing dbt architecture already demonstrates good data engineering practice. Add on top, don't discard what works. |
| D5 | Tab order: Operations → Detection Analytics → Reliability → Pipeline Health | Detection Analytics is the new centerpiece — it should be the second thing an interviewer sees, not buried. |
| D6 | Separate detection density query from base site_status query | Defensive pattern: if fct_detection_events is missing on a new deployment, the Operations tab degrades gracefully instead of crashing. |

---

## [1.1.0] — 2026-05-17 · Bug fixes (post-launch)

### Fixed
- **CatalogException on Operations tab** — `site_status` query referenced
  `fct_detection_events` inline. If the table was absent on a fresh Streamlit Cloud
  deployment, the entire Operations tab crashed. Separated into a try/except block;
  map falls back to active-tower-count coloring gracefully (Decision D6).
- **Open Incidents delta showing "-9.0"** — Delta was comparing
  *incidents opened in last 7 days* vs *prior 7 days* — unrelated to the "currently open"
  headline. Fixed to compare `open_now` vs `open_as_of_7d_ago` (meaningful backlog trend).
- **Network Uptime delta showing "+nan"** — Data window ends 2026-05-07; current 7-day
  window has no rows → NULL. The `or 0` fallback silently converted NULL to 0, producing
  `0 - 90.3 = nan` on display. Fixed `_delta()` to guard with `pd.notna` on both inputs
  and return `None` when either value is missing.

---

## [1.0.0] — 2026-05-17 · Sentinel Mission Analytics upgrade

### Summary
Transformed the app from a generic fleet ops dashboard into an Anduril Sentry-specific
mission analytics platform. Added a new data domain (detection events + alert pipeline),
a new Detection Analytics tab, and upgraded the Operations map and KPI metrics.

### Data model changes
- **New sources:** `detections.parquet` (7,476 rows), `alert_pipeline.parquet` (4,844 rows)
- **New staging models:** `stg_detections`, `stg_alert_pipeline`
- **New mart models:** `fct_detection_events`, `fct_alert_pipeline_latency`
- **New dbt tests:** 10 additional tests (uniqueness, not_null, accepted_values on target_class, time_of_day)
- **Source freshness:** Added 6h warn / 24h error thresholds on both new sources
- **Total pipeline:** 9 parquet sources → 9 staging tables → 8 mart tables · 66 dbt tests

### Detection data design
- Target class weights: 50% human / 25% vehicle / 15% UAS / 10% unknown
- Confidence by class: human μ=0.82, vehicle μ=0.87, UAS μ=0.65, unknown μ=0.45
- Auto-resolve threshold: confidence ≥ 0.85 AND target_class ≠ 'unknown' (~65% auto-resolve rate)
- False positive rates: human 5% / vehicle 4% / UAS 18% / unknown 35%
- Alert pipeline overnight degradation: notify→ack latency multiplied 2–4× for hours 22:00–06:00
- Site detection rates: Border Sector A/B highest (4.0/3.5 dets/tower/day), Tundra lowest (0.5)

### New: Detection Analytics tab
- KPI row: detections 7d (with Δ), auto-resolve %, escalation %, false positive %, avg confidence
- Detection volume stacked bar by target class (60-day trend)
- Classification breakdown horizontal bar with avg confidence overlay
- Time-of-day pattern bar chart colored by escalation rate (dawn/dusk surge visible)
- Alert pipeline latency P50/P95/P99 per stage (detection→alert→notify→ack→resolve)
- Per-tower detection summary table sorted by escalation rate

### Updated: Operations map
- Bubble size = active towers; color = detection density (dets/tower, last 7 days)
- Hover tooltip includes detections (7d) and open incidents per site
- Border sites visibly hotter than inland/tundra sites

### Updated: KPI row
- Network Uptime 7d: shows Δ vs prior week
- Sensor Failures 30d: shows Δ vs prior 30-day window
- Open Incidents: shows Δ vs open-incident count 7 days ago

### Updated: Narrative and domain language
- App renamed "Sentinel Mission Analytics"
- All tabs, KPIs, table columns, and chart labels use Sentry-domain vocabulary:
  missions, terrain, subsystem, patrol, detection, escalation

### Updated: README
- Full portfolio document with architecture diagram, data model table with grain annotations,
  detection design decisions, dbt test coverage summary, and 5 engineering decisions

---

## [0.1.0] — 2026-05-13 · Initial build

### Summary
Initial commit establishing the project foundation.

### Data model
- 7 parquet sources → 7 staging tables → 6 mart tables · 39 dbt tests
- `dim_site` (10 US sites), `dim_tower` (60 towers, 3 models)
- `fct_fleet_health_daily`, `fct_deployment_status`, `fct_component_reliability`, `fct_inventory_status`

### Features
- Operations tab: geographic map, active deployments, open incidents, inventory below reorder
- Reliability tab: component MTBF chart, comms uptime trend, incidents by category, top root causes
- Pipeline Health tab: dbt build results, step detail, source freshness
- Dark theme with amber accent (#c99a2c), IBM Plex fonts

---

## Roadmap (next candidates)

| Priority | Feature | Why |
|----------|---------|-----|
| High | Confidence score degradation over tower age | Ties detection quality to fleet health; directly Sentry-relevant cross-domain analysis |
| High | Operator workload analysis | Escalations per shift; quantifies overnight staffing pressure surfaced as latency outliers |
| Medium | Component lifecycle forecasting | Project remaining life from observed vs target MTBF; proactive replacement queue |
| Medium | Environmental performance cohorts | Compare failure rates and uptime by terrain type (coastal vs desert vs tundra) |
| Low | Source freshness alerting | Wire dbt freshness thresholds to a notification channel |

---

## Infrastructure

- **Keep-alive:** `.github/workflows/keep-alive.yml` pings the app at 08:00 and 20:00 UTC daily
  to prevent Streamlit Community Cloud sleep
- **dbt build note:** `dbt run` is OOM-killed in the local sandbox; new tables are materialized
  directly via `duckdb.connect()` in Python as an equivalent workaround. The dbt SQL files
  remain the source of truth for the transformation logic.
