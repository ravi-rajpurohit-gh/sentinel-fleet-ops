with detections as (select * from {{ ref('stg_detections') }}),
towers as (select * from {{ ref('dim_tower') }})

select
    d.detection_id,
    d.tower_id,
    t.site_id,
    t.site_name,
    t.region,
    t.model                                         as tower_model,
    d.detected_at,
    date_trunc('day', d.detected_at)::date          as detection_date,
    extract('hour' from d.detected_at)              as hour_of_day,
    case
        when extract('hour' from d.detected_at) between 5  and 7  then 'dawn'
        when extract('hour' from d.detected_at) between 8  and 17 then 'day'
        when extract('hour' from d.detected_at) between 18 and 20 then 'dusk'
        else 'night'
    end                                             as time_of_day,
    d.target_class,
    d.confidence_score,
    d.bearing_deg,
    d.range_m,
    d.auto_resolved,
    d.escalated_to_operator,
    d.false_positive
from detections d
left join towers t on t.tower_id = d.tower_id
