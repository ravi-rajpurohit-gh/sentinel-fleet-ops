select
    tower_id,
    model,
    firmware_version,
    site_id,
    cast(deploy_date as date) as deploy_date,
    status
from read_parquet('../data/raw/towers.parquet')
