from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from threading import Event
from typing import Any

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.logging_config import configure_logging, get_correlation_id
from backend.services.prediction_service import PredictionService

LOGGER = configure_logging("inference")


class InferenceService:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.input_topic = os.getenv("RAW_TELEMETRY_TOPIC", "turbofan.raw.telemetry")
        self.output_topic = os.getenv("PREDICTION_RESULTS_TOPIC", "turbofan.prediction.results")
        self.model_name = os.getenv("MODEL_TYPE", "isolation_forest")
        self.prediction_service = PredictionService()
        self.consumer = KafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
            enable_auto_commit=True,
        )
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: object) -> None:
            self.stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def _build_output(self, message: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
        return {
            "event_id": message.get("event_id") or message.get("id") or get_correlation_id(),
            "engine_id": message.get("engine_id"),
            "timestamp": message.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "anomaly_score": prediction["anomaly_score"],
            "is_anomaly": prediction["is_anomaly"],
            "model_name": prediction["model_name"],
            "model_version": prediction["model_version"],
            "metadata": {
                **(message.get("metadata") or {}),
                **prediction.get("metadata", {}),
            },
        }

    def run(self) -> None:
        self._install_signal_handlers()
        LOGGER.info("inference service started", extra={"service_name": "inference"})
        try:
            for raw_message in self.consumer:
                if self.stop_event.is_set():
                    break
                try:
                    payload = raw_message.value
                    if not isinstance(payload, dict):
                        continue
                    prediction = self.prediction_service.predict(payload)
                    event = self._build_output(payload, {"anomaly_score": prediction.anomaly_score, "is_anomaly": prediction.is_anomaly, "model_name": prediction.model_name, "model_version": "1.0", "metadata": prediction.metadata})
                    self.producer.send(self.output_topic, value=event)
                    self.producer.flush(timeout=10)
                    LOGGER.info(
                        "prediction emitted",
                        extra={"service_name": "inference", "event_id": event["event_id"], "engine_id": event["engine_id"]},
                    )
                except Exception as exc:  # pragma: no cover - runtime guard
                    LOGGER.exception("inference failed", extra={"service_name": "inference", "error": str(exc)})
        finally:
            self.consumer.close()
            self.producer.close()


def main() -> None:
    service = InferenceService()
    service.run()


if __name__ == "__main__":
    main()
