with inventory as (select * from {{ ref('stg_inventory') }})

select
    part_number,
    description,
    category,
    on_hand,
    in_transit,
    allocated,
    on_hand - allocated as available,
    reorder_point,
    case
        when (on_hand - allocated) < reorder_point then true
        else false
    end as needs_reorder,
    case
        when (on_hand - allocated) <= 0 then 'critical'
        when (on_hand - allocated) < reorder_point then 'reorder'
        when (on_hand - allocated) < reorder_point * 1.5 then 'watch'
        else 'healthy'
    end as stock_status,
    lead_time_days,
    last_updated
from inventory
