select
    deployment_id,
    tower_id,
    mission_name,
    cast(start_ts as timestamp) as start_ts,
    cast(end_ts as timestamp) as end_ts,
    status
from read_parquet('../data/raw/deployments.parquet')
