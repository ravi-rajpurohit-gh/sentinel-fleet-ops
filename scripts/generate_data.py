"""
Generate synthetic fleet operations data for the Sentinel Fleet Ops demo.

Writes 7 parquet files to data/raw/. Deterministic via fixed seed.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

NOW = datetime(2026, 5, 7, 12, 0, 0)
WINDOW_DAYS = 60
START = NOW - timedelta(days=WINDOW_DAYS)


# --- sites ---------------------------------------------------------------
SITE_DEFS = [
    ("S01", "Coastal North",     "PACIFIC_NW", "coastal", 47.61, -122.33),
    ("S02", "Coastal South",     "SOCAL",      "coastal", 32.72, -117.16),
    ("S03", "Desert East",       "SOUTHWEST",  "desert",  33.45, -112.07),
    ("S04", "Desert West",       "SOUTHWEST",  "desert",  34.86, -116.86),
    ("S05", "High Plains",       "MOUNTAIN",   "plains",  39.74, -104.99),
    ("S06", "Forest Belt",       "PACIFIC_NW", "forest",  46.87, -121.76),
    ("S07", "Border Sector A",   "SOUTHWEST",  "desert",  31.73, -106.49),
    ("S08", "Border Sector B",   "SOUTHWEST",  "desert",  32.22, -110.93),
    ("S09", "Coastal Range",     "SOCAL",      "coastal", 36.97, -122.03),
    ("S10", "Northern Tundra",   "MOUNTAIN",   "tundra",  64.84, -147.72),
]
sites = pd.DataFrame(SITE_DEFS, columns=["site_id", "site_name", "region", "env", "lat", "lng"])
sites["commissioned_date"] = [NOW - timedelta(days=int(d)) for d in rng.integers(180, 900, len(sites))]


# --- towers --------------------------------------------------------------
N_TOWERS = 60
MODELS = ["Sentinel-V2", "Sentinel-V3", "Sentinel-V3-Mast"]
MODEL_WEIGHTS = [0.30, 0.55, 0.15]
FIRMWARE_BY_MODEL = {
    "Sentinel-V2": ["2.4.1", "2.4.3", "2.5.0"],
    "Sentinel-V3": ["3.1.7", "3.2.0", "3.2.1"],
    "Sentinel-V3-Mast": ["3.2.0", "3.2.1"],
}

tower_ids = [f"T{1000+i}" for i in range(N_TOWERS)]
tower_sites = rng.choice(sites["site_id"].values, size=N_TOWERS,
                         p=np.array([0.08, 0.10, 0.12, 0.10, 0.08, 0.08, 0.15, 0.13, 0.08, 0.08]))
tower_models = rng.choice(MODELS, size=N_TOWERS, p=MODEL_WEIGHTS)
tower_firmware = [rng.choice(FIRMWARE_BY_MODEL[m]) for m in tower_models]
tower_deploy = [NOW - timedelta(days=int(d)) for d in rng.integers(15, 720, N_TOWERS)]
tower_status_choices = rng.choice(
    ["active", "active", "active", "active", "maintenance", "decommissioned"],
    size=N_TOWERS,
)
towers = pd.DataFrame({
    "tower_id": tower_ids,
    "model": tower_models,
    "firmware_version": tower_firmware,
    "site_id": tower_sites,
    "deploy_date": tower_deploy,
    "status": tower_status_choices,
})


# --- telemetry (hourly) --------------------------------------------------
def gen_telemetry(towers_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, t in towers_df.iterrows():
        if t.status == "decommissioned":
            continue
        # Each tower has a slight bias profile so the data isn't homogeneous.
        cpu_bias = rng.uniform(-8, 12)
        mem_bias = rng.uniform(-5, 15)
        health_bias = rng.uniform(-10, 4)
        for h in range(WINDOW_DAYS * 24):
            ts = START + timedelta(hours=h)
            cpu = float(np.clip(rng.normal(45 + cpu_bias, 12), 1, 99))
            mem = float(np.clip(rng.normal(55 + mem_bias, 10), 5, 99))
            sensor_health = float(np.clip(rng.normal(92 + health_bias, 5), 30, 100))
            comms_uptime_min = float(np.clip(rng.normal(58, 4), 0, 60))
            if t.status == "maintenance" and rng.random() < 0.3:
                comms_uptime_min = float(rng.uniform(0, 25))
            power_watts = float(np.clip(rng.normal(180, 25), 90, 300))
            ambient = float(np.clip(rng.normal(18, 12), -25, 48))
            rows.append((t.tower_id, ts, cpu, mem, sensor_health, comms_uptime_min, power_watts, ambient))
    return pd.DataFrame(
        rows,
        columns=["tower_id", "ts", "cpu_pct", "mem_pct", "sensor_health_score",
                 "comms_uptime_min", "power_watts", "ambient_temp_c"],
    )


telemetry = gen_telemetry(towers)


# --- deployments ---------------------------------------------------------
MISSION_NAMES = [
    "Perimeter Watch", "Coastal Survey", "Border Patrol Alpha", "Border Patrol Bravo",
    "Range Sentinel", "Forest Recon", "Highway Overwatch", "Port Approach",
    "Tundra Watch", "Desert Pickets",
]
deployments = []
dep_counter = 1
for _, t in towers.iterrows():
    n_deps = rng.integers(1, 4)
    cursor = max(t.deploy_date, START - timedelta(days=30))
    for _ in range(int(n_deps)):
        if cursor >= NOW:
            break
        start_ts = cursor + timedelta(hours=int(rng.integers(0, 72)))
        if start_ts >= NOW:
            break
        dur_days = int(rng.integers(3, 30))
        end_ts = start_ts + timedelta(days=dur_days)
        is_active = end_ts > NOW
        deployments.append({
            "deployment_id": f"D{dep_counter:05d}",
            "tower_id": t.tower_id,
            "mission_name": rng.choice(MISSION_NAMES),
            "start_ts": start_ts,
            "end_ts": None if is_active else end_ts,
            "status": "active" if is_active else "completed",
        })
        dep_counter += 1
        cursor = end_ts + timedelta(days=int(rng.integers(1, 8)))
deployments = pd.DataFrame(deployments)

# Ensure ~55% of active towers have an ongoing deployment as of NOW.
# We pick the latest deployment per active tower and reset it to active.
active_tower_ids = set(towers[towers.status == "active"].tower_id)
elig = deployments[deployments.tower_id.isin(active_tower_ids)]
latest_idx = (
    elig.sort_values(["tower_id", "start_ts"])
        .groupby("tower_id").tail(1).index
)
target_n = max(1, int(len(active_tower_ids) * 0.55))
to_activate = rng.choice(latest_idx.values, size=min(target_n, len(latest_idx)), replace=False)
deployments.loc[to_activate, "end_ts"] = pd.NaT
deployments.loc[to_activate, "status"] = "active"


# --- incidents -----------------------------------------------------------
N_INCIDENTS = 180
INC_CATEGORIES = ["sensor", "comm", "power", "compute", "mechanical", "other"]
INC_CAT_WEIGHTS = [0.30, 0.22, 0.16, 0.12, 0.12, 0.08]
SEVERITIES = ["P1", "P2", "P3", "P4"]
SEV_WEIGHTS = [0.05, 0.20, 0.45, 0.30]
ROOT_CAUSES = {
    "sensor": ["alignment drift", "lens occlusion", "calibration loss", "firmware bug"],
    "comm": ["link saturation", "antenna fault", "modem lockup", "interference"],
    "power": ["battery degradation", "solar fault", "regulator failure", "cable wear"],
    "compute": ["thermal throttling", "memory pressure", "process crash", "disk full"],
    "mechanical": ["pan/tilt jam", "gimbal slip", "mast vibration", "fastener loose"],
    "other": ["unknown", "operator error", "environmental"],
}
incident_active_towers = towers[towers.status != "decommissioned"]
incidents = []
for i in range(N_INCIDENTS):
    t = incident_active_towers.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
    opened_at = START + timedelta(hours=int(rng.integers(0, WINDOW_DAYS * 24)))
    sev = rng.choice(SEVERITIES, p=SEV_WEIGHTS)
    cat = rng.choice(INC_CATEGORIES, p=INC_CAT_WEIGHTS)
    age_hours = (NOW - opened_at).total_seconds() / 3600
    if age_hours < 24 * 3:
        is_open = rng.random() < 0.55
    elif age_hours < 24 * 10:
        is_open = rng.random() < 0.18
    else:
        is_open = False
    if is_open:
        closed_at = None
    else:
        ttr_hours = {
            "P1": rng.uniform(1, 6),
            "P2": rng.uniform(2, 24),
            "P3": rng.uniform(8, 96),
            "P4": rng.uniform(24, 240),
        }[sev]
        closed_at = opened_at + timedelta(hours=float(ttr_hours))
        if closed_at > NOW:
            closed_at = NOW - timedelta(hours=1)
    incidents.append({
        "incident_id": f"INC{10000+i}",
        "tower_id": t.tower_id,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "severity": sev,
        "category": cat,
        "root_cause": rng.choice(ROOT_CAUSES[cat]),
    })
incidents = pd.DataFrame(incidents)


# --- components ----------------------------------------------------------
COMPONENT_TYPES = {
    "radar":   ("RDR", 30000),
    "eo_ir":   ("EOIR", 22000),
    "comm":    ("COMM", 45000),
    "power":   ("PWR", 35000),
    "compute": ("CMP", 60000),
}
components = []
comp_counter = 1
for _, t in towers.iterrows():
    for ctype, (prefix, mtbf_target) in COMPONENT_TYPES.items():
        # 1-2 components of this type per tower (radars sometimes have a backup)
        n_units = 2 if ctype == "radar" and rng.random() < 0.3 else 1
        for _ in range(n_units):
            install = t.deploy_date + timedelta(days=int(rng.integers(0, 30)))
            # Some chance of failure within the window
            failure = None
            failed = False
            # Failure prob increases with age
            age_at_now = (NOW - install).total_seconds() / 3600
            failure_prob = min(0.35, age_at_now / (mtbf_target * 1.5))
            if rng.random() < failure_prob:
                hours_to_fail = float(rng.uniform(mtbf_target * 0.4, mtbf_target * 1.6))
                if hours_to_fail < age_at_now:
                    failure = install + timedelta(hours=hours_to_fail)
                    failed = True
            components.append({
                "component_id": f"C{comp_counter:06d}",
                "tower_id": t.tower_id,
                "component_type": ctype,
                "part_number": f"{prefix}-{rng.integers(1000, 9999)}",
                "installed_at": install,
                "failed_at": failure,
                "mtbf_target_hours": mtbf_target,
                "is_failed": failed,
            })
            comp_counter += 1
components = pd.DataFrame(components)


# --- inventory -----------------------------------------------------------
INVENTORY_PARTS = [
    ("RDR-1042", "Radar transceiver module",   "radar",   12, 50, 18),
    ("RDR-2310", "Radar antenna assembly",     "radar",    8, 35, 21),
    ("EOIR-204", "EO/IR sensor head",          "eo_ir",   15, 60, 28),
    ("EOIR-118", "Lens assembly",              "eo_ir",   25, 80, 14),
    ("COMM-512", "Mesh radio module",          "comm",    20, 70, 10),
    ("COMM-880", "Antenna kit",                "comm",    18, 65, 14),
    ("PWR-9001", "Battery pack 24V",           "power",   30, 90, 21),
    ("PWR-9020", "Solar regulator",            "power",   12, 45, 35),
    ("PWR-9034", "Power distribution unit",    "power",    6, 25, 42),
    ("CMP-7700", "Edge compute unit",          "compute",  9, 30, 56),
    ("CMP-7710", "Storage SSD 2TB",            "compute", 22, 75, 14),
    ("MAST-330", "Mast section",               "mechanical", 5, 18, 49),
    ("MAST-411", "Pan/tilt actuator",          "mechanical", 8, 28, 35),
    ("BOLT-001", "Mounting hardware kit",      "mechanical", 60, 200, 7),
    ("CABLE-12", "Power harness 12m",          "power",   25, 80, 14),
]
inventory_rows = []
for part_number, desc, category, reorder, target_qty, lead in INVENTORY_PARTS:
    on_hand = int(np.clip(rng.normal(target_qty * 0.65, target_qty * 0.25), 0, target_qty * 1.4))
    in_transit = int(rng.integers(0, max(target_qty // 4, 1)))
    allocated = int(rng.integers(0, max(on_hand // 2, 1) + 1))
    inventory_rows.append({
        "part_number": part_number,
        "description": desc,
        "category": category,
        "on_hand": on_hand,
        "in_transit": in_transit,
        "allocated": allocated,
        "reorder_point": reorder,
        "lead_time_days": lead,
        "last_updated": NOW - timedelta(hours=int(rng.integers(0, 36))),
    })
inventory = pd.DataFrame(inventory_rows)


# --- write parquet -------------------------------------------------------
out = {
    "sites": sites,
    "towers": towers,
    "telemetry": telemetry,
    "deployments": deployments,
    "incidents": incidents,
    "components": components,
    "inventory": inventory,
}
for name, df in out.items():
    path = RAW / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  {name:12s} {len(df):>7,} rows  →  {path.relative_to(ROOT)}")

print(f"\nGenerated {sum(len(d) for d in out.values()):,} rows across {len(out)} tables")
print(f"Window: {START.date()} → {NOW.date()}  ({WINDOW_DAYS} days)")
