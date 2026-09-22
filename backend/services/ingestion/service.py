from __future__ import annotations

import logging
import signal
from threading import Event

from services.ingestion.config import load_settings
from services.ingestion.dataset_source import DatasetReplaySource
from services.ingestion.kafka_publisher import KafkaEventPublisher
from services.ingestion.logging_utils import configure_logging
from services.ingestion.mqtt_source import MqttIngestionSource
try:
    from backend.services.dlq import DeadLetterPublisher
except ModuleNotFoundError:  # pragma: no cover - backend/ working_dir execution path
    from services.dlq import DeadLetterPublisher

LOGGER = logging.getLogger(__name__)


class IngestionService:
    def __init__(self) -> None:
        self.settings = load_settings()
        configure_logging(self.settings.log_level)
        self.stop_event = Event()

        self.publisher = KafkaEventPublisher(self.settings)
        self.dlq = DeadLetterPublisher(self.settings.kafka_bootstrap_servers, self.settings.dlq_topic)
        if self.settings.ingestion_mode == "mqtt":
            self.source = MqttIngestionSource(self.settings)
        else:
            self.source = DatasetReplaySource(self.settings)

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum: int, _frame: object) -> None:
            LOGGER.info("Shutdown signal received")
            self.stop_event.set()

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

    def run(self) -> None:
        self._install_signal_handlers()
        LOGGER.info(
            "Ingestion service started",
            extra={
                "source": self.settings.ingestion_mode,
                "topic": self.settings.kafka_topic,
            },
        )

        published = 0
        try:
            for event in self.source.events(self.stop_event):
                if self.stop_event.is_set():
                    break

                try:
                    self.publisher.publish(self.settings.kafka_topic, event)
                except Exception as exc:  # pragma: no cover - network/runtime dependent
                    LOGGER.error("Dropping event after Kafka retries", extra={"event_id": event.get("event_id")})
                    self.dlq.publish_exception(
                        service_name="ingest-service",
                        stage="kafka_publish",
                        event_id=str(event.get("event_id")),
                        original_payload=event,
                        exc=exc,
                        source_topic=self.settings.kafka_topic,
                    )
                    continue

                published += 1
                if published % 1000 == 0:
                    LOGGER.info("Published events", extra={"records": published})
        finally:
            close_fn = getattr(self.source, "close", None)
            if callable(close_fn):
                close_fn()
            self.publisher.close()
            self.dlq.close()
            LOGGER.info("Ingestion service stopped", extra={"records": published})


def main() -> None:
    service = IngestionService()
    service.run()


if __name__ == "__main__":
    main()
