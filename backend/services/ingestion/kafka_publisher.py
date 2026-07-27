from __future__ import annotations

import json
import logging
import time
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from services.ingestion.config import IngestionSettings

LOGGER = logging.getLogger(__name__)


class KafkaEventPublisher:
    def __init__(self, settings: IngestionSettings) -> None:
        self._settings = settings
        self._producer = self._build_with_retry()

    def _build_with_retry(self) -> KafkaProducer:
        last_error: Exception | None = None
        for attempt in range(1, self._settings.kafka_max_retries + 1):
            try:
                return KafkaProducer(
                    bootstrap_servers=self._settings.kafka_bootstrap_servers,
                    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                    acks="all",
                    linger_ms=5,
                    retries=5,
                )
            except NoBrokersAvailable as exc:
                last_error = exc
                LOGGER.warning(
                    "Kafka broker not available, retrying",
                    extra={"error": str(exc)},
                )
                time.sleep(self._settings.kafka_retry_backoff_seconds)
        raise RuntimeError(f"Unable to connect to Kafka after retries: {last_error}")

    def publish(self, topic: str, event: dict[str, Any]) -> bool:
        for _ in range(self._settings.kafka_max_retries):
            try:
                self._producer.send(topic, value=event).get(timeout=10)
                return True
            except KafkaError as exc:
                LOGGER.warning(
                    "Kafka publish failed, retrying",
                    extra={"event_id": event.get("event_id"), "error": str(exc)},
                )
                time.sleep(self._settings.kafka_retry_backoff_seconds)
        return False

    def close(self) -> None:
        self._producer.flush(timeout=10)
        self._producer.close(timeout=10)
