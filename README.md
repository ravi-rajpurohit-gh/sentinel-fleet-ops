# Sentinel Mission Analytics

**Detection intelligence, fleet sustainment, and pipeline telemetry for the Sentry autonomous surveillance network.**

A data engineering portfolio project built to demonstrate end-to-end analytics for a distributed autonomous sensor fleet — synthetic data, a dbt star schema on DuckDB, and a Streamlit interface surfacing four operational views.

**Live app →** https://sentinel-fleet-ops.streamlit.app/

---

## What problem does this solve?

A fleet of autonomous surveillance towers generates continuous telemetry, detection events, and subsystem failure data. Without a unified analytics layer, operators are answering three separate questions with three separate tools:

1. *"Where are my towers and what threats are they seeing right now?"* — Operations
2. *"Are my detection pipelines alerting fast enough?"* — Mission effectiveness
3. *"Are sensors staying healthy and are parts available to fix failures?"* — Sustainment

This platform integrates all three views onto a single compiled DuckDB file, so numbers are consistent and there is no latency from joining across systems at query time.

---

## Views and audiences

| View | Audience | Key question answered |
|---|---|---|
| **Operations** | Site leads, mission commanders | Where is coverage deployed? Which sites have the highest detection density? What incidents are open? |
| **Detection Analytics** | Mission analysts, product engineers | What is the target classification breakdown? How fast does the alert pipeline deliver escalations to operators? Where does latency accumulate overnight? |
| **Reliability** | Sustainment and reliability engineering | Which subsystems are missing their MTBF targets? How is network uptime trending? What failure signatures recur? |
| **Pipeline Health** | Data engineering | Did the last dbt build pass? Is telemetry fresh? What are the per-model execution times? |

---

## Architecture

```
scripts/generate_data.py
         │
         ▼ 9 parquet files (83K rows, deterministic seed=42)
data/raw/*.parquet
         │
         ▼ dbt-duckdb: staging (type casts, no logic)
stg_sites · stg_towers · stg_telemetry · stg_deployments
stg_incidents · stg_components · stg_inventory
stg_detections · stg_alert_pipeline
         │
         ▼ dbt-duckdb: marts (star schema)
dim_site · dim_tower
fct_fleet_health_daily · fct_deployment_status
fct_component_reliability · fct_inventory_status
fct_detection_events · fct_alert_pipeline_latency
         │
         ▼ compiled once, shipped as a static artifact
data/sentinel.duckdb  (read-only at runtime)
         │
         ▼ Streamlit + Plotly
sentinel-fleet-ops.streamlit.app
```

**Why DuckDB?** An embedded OLAP engine is the right fit here: no separate server process, the compiled database ships with the repo, and it runs efficiently in Streamlit Community Cloud's constrained environment. In a real Sentry deployment, this pattern maps naturally to air-gapped or edge scenarios where a remote database connection is unreliable.

**Stack:** Python · DuckDB · dbt-duckdb · Streamlit · Plotly · IBM Plex fonts

---

## Data model

### Dimensions

| Model | Grain | Description |
|---|---|---|
| `dim_site` | one row per site | 10 US sites with lat/lng, region, terrain, tower counts |
| `dim_tower` | one row per tower | 60 towers across 3 models (V2/V3/V3-Mast), age in days, site FK |

### Facts

| Model | Grain | Key fields |
|---|---|---|
| `fct_fleet_health_daily` | tower × day | avg CPU/mem/sensor health, comms uptime %, incidents opened |
| `fct_deployment_status` | one row per deployment | mission, site, status, duration hours/days |
| `fct_component_reliability` | one row per component | observed hours, target MTBF, failure flag |
| `fct_inventory_status` | one row per part number | on-hand, allocated, available, 4-level stock status |
| `fct_detection_events` | one row per detection | target class, confidence score, bearing/range, auto-resolved flag, time-of-day bucket |
| `fct_alert_pipeline_latency` | one row per escalated detection | 5-stage latency chain: detection → alert → notify → ack → resolve |

### Detection data design decisions

**Target classification weights** are set to realistic border patrol distributions: ~50% human, ~25% vehicle, ~15% UAS, ~10% unknown. Confidence scores vary by class — UAS and unknown have lower mean confidence (0.65/0.45 vs. 0.82/0.87 for human/vehicle), which drives the auto-resolve cutoff.

**Auto-resolve threshold** is `confidence >= 0.85 AND target_class != 'unknown'`. Everything below escalates to an operator. This creates a realistic ~65% auto-resolve rate with a meaningful escalation queue.

**Alert pipeline latency** is modeled with an overnight degradation multiplier (2–4×) on the notify→ack stage, reflecting reduced operator staffing. This makes the P95/P99 split informative: P50 ~21 min, P99 ~42 min, with overnight gaps clearly visible in the time-of-day chart.

**Site-specific detection rates** range from 4.0 detections/tower/day (Border Sector A) down to 0.5 (Northern Tundra), making the map's detection-density encoding immediately meaningful.

### dbt tests

66 total tests: uniqueness on every PK, `not_null` on FKs, `accepted_values` on all enums (`status`, `severity`, `target_class`, `time_of_day`, `component_type`, `stock_status`, `env`), `relationships` from staging to upstream dims. Source freshness configured on `telemetry`, `detections`, and `alert_pipeline` with 6-hour warn / 24-hour error thresholds.

---

## Local setup

```bash
# 1. Install dev dependencies (includes dbt-duckdb, numpy, pyarrow)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Regenerate synthetic source data (9 parquet files → data/raw/)
python scripts/generate_data.py

# 3. Build the dbt project (materializes sentinel.duckdb)
cd dbt && dbt build --profiles-dir . --project-dir . && cd ..

# 4. Serve the interface
streamlit run streamlit_app.py
```

Runtime only needs `requirements.txt` (streamlit, duckdb, pandas, plotly). The compiled database and dbt artifacts ship with the repo — no build step runs in production.

---

## Repository layout

```
sentinel-fleet-ops/
├── .github/workflows/keep-alive.yml  # pings app twice daily (Streamlit stay-alive)
├── .streamlit/config.toml            # theme + server config
├── data/
│   ├── raw/                          # 9 parquet source files
│   └── sentinel.duckdb               # compiled marts (read-only at runtime)
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/                  # 9 models + sources.yml + schema tests
│   │   └── marts/                    # 8 mart models + schema tests
│   └── target/                       # run_results.json (committed, parsed at runtime)
├── scripts/
│   └── generate_data.py              # deterministic synthetic generator (seed=42)
├── streamlit_app.py                  # Streamlit entry point (~1,000 lines)
├── requirements.txt                  # runtime (streamlit, duckdb, pandas, plotly)
└── requirements-dev.txt              # build (adds dbt-core, dbt-duckdb, numpy, pyarrow)
```

---

## Engineering decisions

**Static artifact pattern.** dbt builds once and the resulting DuckDB file ships with the repo. The Streamlit process reads it with `duckdb.connect(read_only=True)` — no working-directory coupling to parquet files at runtime. This simplifies deployment and makes the production environment identical to local.

**Staging materialized as tables, not views.** Views re-execute parquet reads on every query. Materializing staging eliminates that overhead and lets the mart layer join against in-memory tables.

**Grain choices are explicit and annotated.** `fct_fleet_health_daily` is at tower × day grain — not site × day — so per-tower reliability differences are preserved when aggregating up. `fct_alert_pipeline_latency` is at detection_id grain so percentile calculations run over individual events, not averages of averages.

**Four-level stock status.** `critical / reorder / watch / healthy` gives operations leads prioritization signal. A single boolean `below_threshold` flattens information that ops leads need to triage.

**Detection density on the map, not tower count.** Coloring by `dets_per_active_tower` instead of `active_tower_count` reveals which sites are operationally active, not just where hardware was deployed.

---

## Roadmap

1. **Streaming ingest path.** Replace the batch parquet generator with a continuous producer so telemetry and detections land in near-real-time.
2. **Component lifecycle forecasting.** Extend `fct_component_reliability` to project remaining life from observed-vs-target MTBF ratios, surfaced as a proactive replacement queue prioritized against inventory.
3. **Operator workload analysis.** Add a shift × site grain table tracking escalations per operator-hour, making overnight staffing pressure quantifiable rather than inferred from latency outliers.
4. **Environmental performance cohorts.** Group sites by terrain type and surface a comparative view for failure signatures and uptime — useful when deciding hardware spec changes for coastal vs. desert vs. tundra deployments.
5. **Source freshness alerting.** Wire the dbt freshness thresholds to a notification channel so stale telemetry escalates automatically without requiring a dashboard load.

---

*Synthetic data only. No classified or proprietary information.*
