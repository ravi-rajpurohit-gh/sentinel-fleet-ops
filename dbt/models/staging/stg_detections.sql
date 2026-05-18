select
    detection_id,
    tower_id,
    site_id,
    cast(detected_at as timestamp) as detected_at,
    target_class,
    cast(confidence_score as double) as confidence_score,
    cast(bearing_deg as double)      as bearing_deg,
    cast(range_m as integer)         as range_m,
    cast(auto_resolved as boolean)          as auto_resolved,
    cast(escalated_to_operator as boolean)  as escalated_to_operator,
    cast(false_positive as boolean)         as false_positive
from read_parquet('../data/raw/detections.parquet')
