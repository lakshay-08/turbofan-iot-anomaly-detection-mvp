from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

IngestionMode = Literal["mqtt", "dataset"]


def _find_repo_root() -> Path:
    """Find repository root by walking up until key folders are present."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "backend").exists() and (parent / "data").exists():
            return parent
    return current.parents[3]


REPO_ROOT = _find_repo_root()


@dataclass(frozen=True, slots=True)
class IngestionSettings:
    ingestion_mode: IngestionMode

    mqtt_broker: str
    mqtt_port: int
    mqtt_topic: str

    kafka_bootstrap_servers: str
    kafka_topic: str

    dataset_path: str
    replay_speed: str
    replay_limit: int | None
    replay_start_index: int
    replay_end_index: int | None

    log_level: str
    dlq_topic: str
    processing_retry_attempts: int

    kafka_max_retries: int
    kafka_retry_backoff_seconds: float
    mqtt_max_retries: int
    mqtt_retry_backoff_seconds: float



def _parse_int(name: str, default: int) -> int:
    value = os.getenv(name, str(default)).strip()
    return int(value)



def _parse_float(name: str, default: float) -> float:
    value = os.getenv(name, str(default)).strip()
    return float(value)



def _parse_optional_int(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    return int(raw.strip())



def load_settings() -> IngestionSettings:
    mode_raw = os.getenv("INGESTION_MODE", "mqtt").strip().lower()
    if mode_raw not in {"mqtt", "dataset"}:
        raise ValueError("INGESTION_MODE must be either 'mqtt' or 'dataset'")

    default_dataset_dir = REPO_ROOT / "data" / "processed" / "test"

    return IngestionSettings(
        ingestion_mode=mode_raw,  # type: ignore[arg-type]
        mqtt_broker=os.getenv("MQTT_BROKER", "localhost").strip(),
        mqtt_port=_parse_int("MQTT_PORT", 1883),
        mqtt_topic=os.getenv("MQTT_TOPIC", "turbofan/telemetry").strip(),
        kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").strip(),
        kafka_topic=os.getenv("KAFKA_TOPIC", "turbofan.raw.telemetry").strip(),
        dataset_path=os.getenv("DATASET_PATH", str(default_dataset_dir)).strip(),
        replay_speed=os.getenv("REPLAY_SPEED", "1x").strip().lower(),
        replay_limit=_parse_optional_int("REPLAY_LIMIT"),
        replay_start_index=_parse_int("REPLAY_START_INDEX", 0),
        replay_end_index=_parse_optional_int("REPLAY_END_INDEX"),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        dlq_topic=os.getenv("DLQ_TOPIC", "turbofan.dead-letter").strip(),
        processing_retry_attempts=_parse_int("PROCESSING_RETRY_ATTEMPTS", 3),
        kafka_max_retries=_parse_int("KAFKA_MAX_RETRIES", 10),
        kafka_retry_backoff_seconds=_parse_float("KAFKA_RETRY_BACKOFF_SECONDS", 2.0),
        mqtt_max_retries=_parse_int("MQTT_MAX_RETRIES", 10),
        mqtt_retry_backoff_seconds=_parse_float("MQTT_RETRY_BACKOFF_SECONDS", 2.0),
    )
