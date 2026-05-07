with telemetry as (select * from {{ ref('stg_telemetry') }}),
towers as (select * from {{ ref('dim_tower') }}),
incidents as (select * from {{ ref('stg_incidents') }}),

t_daily as (
    select
        tower_id,
        cast(ts as date) as health_date,
        avg(cpu_pct) as avg_cpu_pct,
        avg(mem_pct) as avg_mem_pct,
        avg(sensor_health_score) as avg_sensor_health,
        avg(comms_uptime_min) / 60.0 as comms_uptime_pct,
        avg(power_watts) as avg_power_watts,
        avg(ambient_temp_c) as avg_ambient_temp_c,
        max(ts) as last_heartbeat_ts
    from telemetry
    group by tower_id, cast(ts as date)
),

i_daily as (
    select
        tower_id,
        cast(opened_at as date) as health_date,
        count(*) as incidents_opened,
        sum(case when severity in ('P1', 'P2') then 1 else 0 end) as critical_incidents
    from incidents
    group by tower_id, cast(opened_at as date)
)

select
    t.tower_id,
    dt.site_id,
    dt.site_name,
    dt.region,
    dt.model,
    t.health_date,
    round(t.avg_cpu_pct, 2) as avg_cpu_pct,
    round(t.avg_mem_pct, 2) as avg_mem_pct,
    round(t.avg_sensor_health, 2) as avg_sensor_health,
    round(t.comms_uptime_pct * 100, 2) as comms_uptime_pct,
    round(t.avg_power_watts, 2) as avg_power_watts,
    round(t.avg_ambient_temp_c, 2) as avg_ambient_temp_c,
    t.last_heartbeat_ts,
    coalesce(i.incidents_opened, 0) as incidents_opened,
    coalesce(i.critical_incidents, 0) as critical_incidents
from t_daily t
left join towers dt on dt.tower_id = t.tower_id
left join i_daily i on i.tower_id = t.tower_id and i.health_date = t.health_date
