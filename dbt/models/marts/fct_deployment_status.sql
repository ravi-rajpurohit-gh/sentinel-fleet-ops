with deployments as (select * from {{ ref('stg_deployments') }}),
towers as (select * from {{ ref('dim_tower') }})

select
    d.deployment_id,
    d.tower_id,
    t.site_id,
    t.site_name,
    t.region,
    t.model,
    d.mission_name,
    d.start_ts,
    d.end_ts,
    d.status,
    case
        when d.end_ts is null then date_diff('hour', d.start_ts, current_timestamp)
        else date_diff('hour', d.start_ts, d.end_ts)
    end as duration_hours,
    case
        when d.end_ts is null then date_diff('day', d.start_ts, current_timestamp)
        else date_diff('day', d.start_ts, d.end_ts)
    end as duration_days
from deployments d
left join towers t on t.tower_id = d.tower_id
