select
    tower_id,
    cast(ts as timestamp) as ts,
    cpu_pct,
    mem_pct,
    sensor_health_score,
    comms_uptime_min,
    power_watts,
    ambient_temp_c
from read_parquet('../data/raw/telemetry.parquet')
