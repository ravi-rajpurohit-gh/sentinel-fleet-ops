select
    detection_id,
    cast(detection_ts           as timestamp) as detection_ts,
    cast(alert_generated_ts     as timestamp) as alert_generated_ts,
    cast(operator_notified_ts   as timestamp) as operator_notified_ts,
    cast(operator_ack_ts        as timestamp) as operator_ack_ts,
    cast(resolved_ts            as timestamp) as resolved_ts,
    cast(is_overnight           as boolean)   as is_overnight,
    cast(detection_to_alert_s   as double)    as detection_to_alert_s,
    cast(alert_to_notify_s      as double)    as alert_to_notify_s,
    cast(notify_to_ack_s        as double)    as notify_to_ack_s,
    cast(ack_to_resolve_s       as double)    as ack_to_resolve_s,
    cast(total_response_s       as double)    as total_response_s
from read_parquet('../data/raw/alert_pipeline.parquet')
