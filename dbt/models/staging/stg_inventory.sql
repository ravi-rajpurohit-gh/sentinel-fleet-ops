select
    part_number,
    description,
    category,
    on_hand,
    in_transit,
    allocated,
    reorder_point,
    lead_time_days,
    cast(last_updated as timestamp) as last_updated
from read_parquet('../data/raw/inventory.parquet')
