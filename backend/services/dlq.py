from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from typing import Any

from kafka import KafkaProducer

try:
    from backend.utils.retry import RetryPolicy, run_with_retry
except ModuleNotFoundError:  # pragma: no cover - backend/ working_dir execution path
    from utils.retry import RetryPolicy, run_with_retry


class DeadLetterPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = run_with_retry(
            "create dead-letter producer",
            lambda: KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                acks="all",
                linger_ms=5,
                retries=5,
            ),
            RetryPolicy(max_attempts=3, initial_delay_seconds=0.5, max_delay_seconds=3.0),
        )

    def publish(
        self,
        *,
        service_name: str,
        stage: str,
        event_id: str | None,
        original_payload: dict[str, Any] | None,
        error_message: str,
        stack_trace: str,
        source_topic: str | None = None,
    ) -> None:
        message = {
            "event_id": event_id,
            "service_name": service_name,
            "stage": stage,
            "source_topic": source_topic,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_payload": original_payload or {},
        }
        run_with_retry(
            f"publish dead-letter message for {service_name}",
            lambda: self.producer.send(self.topic, value=message).get(timeout=10),
            RetryPolicy(max_attempts=3, initial_delay_seconds=0.5, max_delay_seconds=3.0),
        )

    def publish_exception(
        self,
        *,
        service_name: str,
        stage: str,
        event_id: str | None,
        original_payload: dict[str, Any] | None,
        exc: Exception,
        source_topic: str | None = None,
    ) -> None:
        self.publish(
            service_name=service_name,
            stage=stage,
            event_id=event_id,
            original_payload=original_payload,
            error_message=str(exc),
            stack_trace=traceback.format_exc(),
            source_topic=source_topic,
        )

    def close(self) -> None:
        self.producer.flush(timeout=10)
        self.producer.close(timeout=10)
