select
    component_id,
    tower_id,
    component_type,
    part_number,
    cast(installed_at as timestamp) as installed_at,
    cast(failed_at as timestamp) as failed_at,
    mtbf_target_hours,
    is_failed
from read_parquet('../data/raw/components.parquet')
