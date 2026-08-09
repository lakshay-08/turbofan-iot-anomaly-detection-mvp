from __future__ import annotations

import json
import os
import signal
import sys
from threading import Event
from typing import Any

from kafka import KafkaConsumer

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal
from backend.logging_config import configure_logging
from backend.repositories.prediction_repository import PredictionRepository
from backend.services.dlq import DeadLetterPublisher
from backend.utils.retry import RetryPolicy, run_with_retry

LOGGER = configure_logging("writer")


class PredictionWriterService:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.input_topic = os.getenv("PREDICTION_RESULTS_TOPIC", "turbofan.prediction.results")
        self.alert_threshold = float(os.getenv("ALERT_THRESHOLD", "0.85"))
        self.dlq_topic = os.getenv("DLQ_TOPIC", "turbofan.dead-letter")
        self.processing_retry_policy = RetryPolicy(
            max_attempts=int(os.getenv("PROCESSING_RETRY_ATTEMPTS", "3")),
            initial_delay_seconds=float(os.getenv("PROCESSING_RETRY_BACKOFF_SECONDS", "0.5")),
            max_delay_seconds=float(os.getenv("PROCESSING_RETRY_MAX_DELAY_SECONDS", "5.0")),
        )
        self.consumer = KafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
            enable_auto_commit=False,
        )
        self.dlq = DeadLetterPublisher(self.bootstrap_servers, self.dlq_topic)

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: object) -> None:
            self.stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def run(self) -> None:
        self._install_signal_handlers()
        LOGGER.info("writer service started", extra={"service_name": "writer"})
        try:
            for message in self.consumer:
                if self.stop_event.is_set():
                    break
                payload: dict[str, Any] = {}
                try:
                    payload = message.value
                    if not isinstance(payload, dict):
                        continue
                    def persist_payload() -> None:
                        session = SessionLocal()
                        try:
                            repository = PredictionRepository(session)
                            prediction = repository.add_prediction(payload)
                            if bool(payload.get("is_anomaly", False)) or float(payload.get("anomaly_score", 0.0)) >= self.alert_threshold:
                                repository.add_alert(
                                    prediction,
                                    severity="high" if float(payload.get("anomaly_score", 0.0)) >= self.alert_threshold else "medium",
                                    message=f"Anomaly detected for engine {payload.get('engine_id')}",
                                )
                        finally:
                            session.close()

                    run_with_retry("persist prediction result", persist_payload, self.processing_retry_policy)
                    self.consumer.commit()
                    LOGGER.info(
                        "prediction persisted",
                        extra={"service_name": "writer", "event_id": payload.get("event_id"), "engine_id": payload.get("engine_id")},
                    )
                except Exception as exc:  # pragma: no cover - runtime guard
                    LOGGER.exception("writer failed", extra={"service_name": "writer", "error": str(exc)})
                    self.dlq.publish_exception(
                        service_name="prediction-writer",
                        stage="persistence",
                        event_id=str(payload.get("event_id") or payload.get("id")),
                        original_payload=payload,
                        exc=exc,
                        source_topic=self.input_topic,
                    )
                    self.consumer.commit()
        finally:
            self.consumer.close()
            self.dlq.close()


def main() -> None:
    service = PredictionWriterService()
    service.run()


if __name__ == "__main__":
    main()
