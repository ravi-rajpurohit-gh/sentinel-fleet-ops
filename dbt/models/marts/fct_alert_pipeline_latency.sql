with pipeline as (select * from {{ ref('stg_alert_pipeline') }}),
detections as (select * from {{ ref('stg_detections') }}),
towers as (select * from {{ ref('dim_tower') }})

select
    p.detection_id,
    d.tower_id,
    t.site_id,
    t.site_name,
    d.target_class,
    d.confidence_score,
    p.detection_ts,
    date_trunc('day', p.detection_ts)::date         as detection_date,
    p.is_overnight,
    -- Raw latency stages (seconds)
    p.detection_to_alert_s,
    p.alert_to_notify_s,
    p.notify_to_ack_s,
    p.ack_to_resolve_s,
    p.total_response_s,
    -- Stage timestamps
    p.alert_generated_ts,
    p.operator_notified_ts,
    p.operator_ack_ts,
    p.resolved_ts
from pipeline p
inner join detections d on d.detection_id = p.detection_id
left join towers t on t.tower_id = d.tower_id
