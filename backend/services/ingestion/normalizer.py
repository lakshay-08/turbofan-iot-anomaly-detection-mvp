from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



def _parse_timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return datetime.now(timezone.utc).isoformat()



def _sensor(payload: dict[str, Any], key: str) -> float | None:
    features = payload.get("features")
    if isinstance(features, dict):
        return _safe_float(features.get(key))
    return None



def normalize_mqtt_event(payload: dict[str, Any], source_topic: str) -> dict[str, Any] | None:
    engine_id = payload.get("engine_id")
    if engine_id is None:
        return None

    op_cond = payload.get("operating_condition")
    op_cond_dict = op_cond if isinstance(op_cond, dict) else {}

    faults = payload.get("faults")
    fault_state = "NORMAL"
    if isinstance(faults, list) and faults:
        fault_state = str(faults[0])
    elif payload.get("meta", {}).get("failed"):
        fault_state = "FAILED"

    return {
        "event_id": str(uuid.uuid4()),
        "source": "mqtt",
        "engine_id": str(engine_id),
        "timestamp": _parse_timestamp(payload.get("timestamp")),
        "altitude": _safe_float(payload.get("altitude")) or _safe_float(op_cond_dict.get("alt")),
        "airspeed": _safe_float(payload.get("airspeed")) or _safe_float(op_cond_dict.get("Mach")),
        "temperature": _safe_float(payload.get("temperature")) or _safe_float(op_cond_dict.get("ambient_temp_c")) or _sensor(payload, "sensor_11"),
        "vibration": _safe_float(payload.get("vibration")) or _sensor(payload, "sensor_4"),
        "fault_state": fault_state,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_topic": source_topic,
        "metadata": {
            "cycle": payload.get("cycle"),
            "sequence": payload.get("sequence"),
            "health_score": payload.get("health_score"),
            "anomaly_score": payload.get("anomaly_score"),
        },
    }



def normalize_dataset_row(
    row: dict[str, Any],
    source_label: str,
    event_timestamp: str,
    row_index: int,
) -> dict[str, Any] | None:
    engine_id = row.get("engine_id")
    if engine_id is None:
        return None

    anomaly_label = row.get("anomaly_label")
    fault_state = "ANOMALY" if str(anomaly_label) == "1" else str(row.get("health_stage") or "NORMAL")

    return {
        "event_id": str(uuid.uuid4()),
        "source": "dataset",
        "engine_id": str(engine_id),
        "timestamp": event_timestamp,
        "altitude": _safe_float(row.get("altitude")) or _safe_float(row.get("setting_1")),
        "airspeed": _safe_float(row.get("airspeed")) or _safe_float(row.get("setting_2")),
        "temperature": _safe_float(row.get("temperature")) or _safe_float(row.get("sensor_11")),
        "vibration": _safe_float(row.get("vibration")) or _safe_float(row.get("sensor_4")),
        "fault_state": fault_state,
        "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_topic": source_label,
        "metadata": {
            "cycle": row.get("cycle"),
            "rul": row.get("RUL"),
            "anomaly_label": anomaly_label,
            "row_index": row_index,
        },
    }
