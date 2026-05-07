with components as (select * from {{ ref('stg_components') }}),
towers as (select * from {{ ref('dim_tower') }})

select
    c.component_id,
    c.tower_id,
    t.site_id,
    t.site_name,
    t.region,
    t.model as tower_model,
    c.component_type,
    c.part_number,
    c.installed_at,
    c.failed_at,
    c.is_failed,
    c.mtbf_target_hours,
    case
        when c.failed_at is not null
            then date_diff('hour', c.installed_at, c.failed_at)
        else date_diff('hour', c.installed_at, current_timestamp)
    end as observed_hours,
    case
        when c.failed_at is not null
            then round(date_diff('hour', c.installed_at, c.failed_at) * 1.0 / c.mtbf_target_hours, 3)
        else null
    end as actual_vs_target_ratio
from components c
left join towers t on t.tower_id = c.tower_id
