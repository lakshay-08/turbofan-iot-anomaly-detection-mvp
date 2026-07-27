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

from backend.database import SessionLocal, init_db
from backend.logging_config import configure_logging
from backend.repositories.prediction_repository import PredictionRepository

LOGGER = configure_logging("alerts")


class AlertService:
    def __init__(self) -> None:
        self.stop_event = Event()
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.input_topic = os.getenv("PREDICTION_RESULTS_TOPIC", "turbofan.prediction.results")
        self.consumer = KafkaConsumer(
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset="earliest",
            value_deserializer=lambda payload: json.loads(payload.decode("utf-8")),
            enable_auto_commit=True,
        )
        init_db()

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: object) -> None:
            self.stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def run(self) -> None:
        self._install_signal_handlers()
        LOGGER.info("alert service started", extra={"service_name": "alerts"})
        try:
            for message in self.consumer:
                if self.stop_event.is_set():
                    break
                payload = message.value
                if not isinstance(payload, dict):
                    continue
                if float(payload.get("anomaly_score", 0.0)) >= 0.85:
                    session = SessionLocal()
                    repository = PredictionRepository(session)
                    repository.add_alert(
                        repository.add_prediction(payload),
                        severity="high",
                        message=f"Alert generated for engine {payload.get('engine_id')}",
                    )
                    session.close()
        finally:
            self.consumer.close()


def main() -> None:
    service = AlertService()
    service.run()


if __name__ == "__main__":
    main()
