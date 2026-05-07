select
    site_id,
    site_name,
    region,
    env,
    lat,
    lng,
    cast(commissioned_date as date) as commissioned_date
from read_parquet('../data/raw/sites.parquet')
