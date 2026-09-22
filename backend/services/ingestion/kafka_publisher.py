from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer

from services.ingestion.config import IngestionSettings
try:
    from backend.utils.retry import RetryPolicy, run_with_retry
except ModuleNotFoundError:  # pragma: no cover - backend/ working_dir execution path
    from utils.retry import RetryPolicy, run_with_retry

LOGGER = logging.getLogger(__name__)


class KafkaEventPublisher:
    def __init__(self, settings: IngestionSettings) -> None:
        self._settings = settings
        self._producer = self._build_with_retry()

    def _build_with_retry(self) -> KafkaProducer:
        return run_with_retry(
            "connect kafka producer",
            lambda: KafkaProducer(
                bootstrap_servers=self._settings.kafka_bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                acks="all",
                linger_ms=5,
                retries=5,
            ),
            RetryPolicy(
                max_attempts=self._settings.kafka_max_retries,
                initial_delay_seconds=self._settings.kafka_retry_backoff_seconds,
                max_delay_seconds=30.0,
            ),
        )

    def publish(self, topic: str, event: dict[str, Any]) -> bool:
        run_with_retry(
            "publish kafka message",
            lambda: self._producer.send(topic, value=event).get(timeout=10),
            RetryPolicy(
                max_attempts=self._settings.kafka_max_retries,
                initial_delay_seconds=self._settings.kafka_retry_backoff_seconds,
                max_delay_seconds=30.0,
            ),
        )
        return True

    def close(self) -> None:
        self._producer.flush(timeout=10)
        self._producer.close(timeout=10)
