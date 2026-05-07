select
    incident_id,
    tower_id,
    cast(opened_at as timestamp) as opened_at,
    cast(closed_at as timestamp) as closed_at,
    severity,
    category,
    root_cause
from read_parquet('../data/raw/incidents.parquet')
