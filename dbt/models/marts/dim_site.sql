with sites as (select * from {{ ref('stg_sites') }}),
towers as (select * from {{ ref('stg_towers') }}),

tower_counts as (
    select
        site_id,
        count(*) as tower_count,
        sum(case when status = 'active' then 1 else 0 end) as active_tower_count,
        sum(case when status = 'maintenance' then 1 else 0 end) as maintenance_tower_count
    from towers
    group by site_id
)

select
    s.site_id,
    s.site_name,
    s.region,
    s.env,
    s.lat,
    s.lng,
    s.commissioned_date,
    coalesce(tc.tower_count, 0) as tower_count,
    coalesce(tc.active_tower_count, 0) as active_tower_count,
    coalesce(tc.maintenance_tower_count, 0) as maintenance_tower_count
from sites s
left join tower_counts tc on tc.site_id = s.site_id
