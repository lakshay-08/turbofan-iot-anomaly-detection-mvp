from __future__ import annotations

import json
import logging
import queue
import time
from dataclasses import dataclass
from threading import Event
from typing import Any, Iterator

import paho.mqtt.client as mqtt

from services.ingestion.config import IngestionSettings
from services.ingestion.normalizer import normalize_mqtt_event

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class MqttMessage:
    topic: str
    payload: bytes


class MqttIngestionSource:
    def __init__(self, settings: IngestionSettings) -> None:
        self._settings = settings
        self._queue: queue.Queue[MqttMessage] = queue.Queue(maxsize=5000)
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _flags: dict[str, Any],
        reason_code: mqtt.ReasonCode,
        _properties: Any,
    ) -> None:
        if reason_code.value == 0:
            client.subscribe(self._settings.mqtt_topic)
            LOGGER.info("Subscribed to MQTT topic", extra={"topic": self._settings.mqtt_topic})
        else:
            LOGGER.warning("MQTT connect returned non-zero code", extra={"error": str(reason_code)})

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        try:
            self._queue.put_nowait(MqttMessage(topic=msg.topic, payload=msg.payload))
        except queue.Full:
            LOGGER.warning("MQTT message queue full, dropping message", extra={"topic": msg.topic})

    def _connect_with_retry(self) -> None:
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        last_error: Exception | None = None
        for _ in range(self._settings.mqtt_max_retries):
            try:
                self._client.connect(self._settings.mqtt_broker, self._settings.mqtt_port, keepalive=60)
                self._client.loop_start()
                return
            except Exception as exc:  # pragma: no cover - network dependent
                last_error = exc
                LOGGER.warning("MQTT connect failed, retrying", extra={"error": str(exc)})
                time.sleep(self._settings.mqtt_retry_backoff_seconds)
        raise RuntimeError(f"Unable to connect to MQTT after retries: {last_error}")

    def events(self, stop_event: Event) -> Iterator[dict[str, Any]]:
        self._connect_with_retry()
        try:
            while not stop_event.is_set():
                try:
                    message = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                try:
                    payload = json.loads(message.payload.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    LOGGER.warning("Skipping malformed MQTT JSON", extra={"error": str(exc), "topic": message.topic})
                    continue

                normalized = normalize_mqtt_event(payload=payload, source_topic=message.topic)
                if normalized is None:
                    LOGGER.warning("Skipping MQTT payload missing required fields", extra={"topic": message.topic})
                    continue
                yield normalized
        finally:
            self.close()

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
