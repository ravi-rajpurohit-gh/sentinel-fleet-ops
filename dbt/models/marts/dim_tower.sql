with towers as (select * from {{ ref('stg_towers') }}),
sites as (select * from {{ ref('stg_sites') }})

select
    t.tower_id,
    t.model,
    t.firmware_version,
    t.status,
    t.deploy_date,
    date_diff('day', t.deploy_date, current_date) as age_days,
    s.site_id,
    s.site_name,
    s.region,
    s.env
from towers t
left join sites s on s.site_id = t.site_id
