from __future__ import annotations

import json
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.database import SessionLocal
from backend.repositories.prediction_repository import PredictionRepository
from backend.services.prediction_service import PredictionService


@dataclass
class SimulationConfig:
    engines: int = 4
    interval: float = 1.0
    max_cycles: int = 20
    seed: int = 42
    enabled: bool = True
    topic: str = "turbofan/telemetry"


class LiveTelemetrySimulator:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self.random = random.Random(self.config.seed)
        self._state: dict[int, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._running = False
        self._thread: threading.Thread | None = None
        self._prediction_service = PredictionService()

    def _init_engine_state(self, engine_id: int) -> dict[str, Any]:
        return {
            "engine_id": engine_id,
            "cycle": 0,
            "health": 0.95,
            "base": {
                "sensor_2": 600.0,
                "sensor_3": 1500.0,
                "sensor_4": 1350.0,
                "sensor_8": 2300.0,
                "sensor_9": 9000.0,
                "sensor_11": 45.0,
                "sensor_13": 2350.0,
                "sensor_17": 380.0,
            },
        }

    def build_telemetry_frame(self, engine_id: int, cycle: int | None = None) -> dict[str, Any]:
        with self._lock:
            state = self._state.setdefault(engine_id, self._init_engine_state(engine_id))
            current_cycle = cycle if cycle is not None else state["cycle"] + 1
            state["cycle"] = current_cycle

            drift = 1.0 + (current_cycle / 100.0)
            wave = self.random.uniform(-0.12, 0.12)
            feature_values = {
                "sensor_2": state["base"]["sensor_2"] * drift + wave * 70,
                "sensor_3": state["base"]["sensor_3"] * drift + wave * 160,
                "sensor_4": state["base"]["sensor_4"] * drift + wave * 150,
                "sensor_8": state["base"]["sensor_8"] * drift + wave * 220,
                "sensor_9": state["base"]["sensor_9"] * drift + wave * 120,
                "sensor_11": state["base"]["sensor_11"] * (1.0 + current_cycle / 200.0) + wave * 8,
                "sensor_13": state["base"]["sensor_13"] * drift + wave * 190,
                "sensor_17": state["base"]["sensor_17"] * (1.0 + current_cycle / 180.0) + wave * 24,
            }

            payload = {
                "event_id": str(uuid.uuid4()),
                "engine_id": engine_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cycle": current_cycle,
                "sequence": current_cycle,
                "source": "simulator",
                "features": feature_values,
                "prediction_features": feature_values,
                "health_score": round(max(0.2, 1.0 - (current_cycle / 120.0)), 4),
                "metadata": {
                    "source": "simulator",
                    "simulator_cycle": current_cycle,
                    "engine_id": engine_id,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            result = self._prediction_service.predict(payload)
            payload["anomaly_score"] = result.anomaly_score
            payload["is_anomaly"] = result.is_anomaly
            payload["threshold"] = result.threshold
            payload["model_name"] = result.model_name
            return payload

    def _persist_prediction(self, payload: dict[str, Any]) -> None:
        session = SessionLocal()
        try:
            repository = PredictionRepository(session)
            prediction = repository.add_prediction(
                {
                    "event_id": payload["event_id"],
                    "engine_id": str(payload["engine_id"]),
                    "timestamp": payload["timestamp"],
                    "anomaly_score": float(payload.get("anomaly_score", 0.0)),
                    "is_anomaly": bool(payload.get("is_anomaly", False)),
                    "model_name": payload.get("model_name", "IsolationForest"),
                    "metadata": {
                        **(payload.get("metadata") or {}),
                        "source": "simulator",
                    },
                }
            )
            if prediction and (payload.get("is_anomaly") or float(payload.get("anomaly_score", 0.0)) >= 0.75):
                repository.add_alert(
                    prediction,
                    "high",
                    f"Anomaly detected for engine {payload['engine_id']}",
                )
        finally:
            session.close()

    def _emit_loop(self) -> None:
        while not self._stop.is_set():
            for engine_id in range(1, self.config.engines + 1):
                if self._stop.is_set():
                    break
                payload = self.build_telemetry_frame(engine_id)
                self.publish(payload)
                self._persist_prediction(payload)
            time.sleep(self.config.interval)

    def publish(self, payload: dict[str, Any]) -> None:
        try:
            from paho.mqtt import client as mqtt

            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            broker = os.getenv("MQTT_BROKER", "localhost")
            port = int(os.getenv("MQTT_PORT", "1883"))
            topic = os.getenv("MQTT_TOPIC", self.config.topic)
            client.connect(broker, port, keepalive=30)
            client.publish(topic, json.dumps(payload), qos=1, retain=False)
            client.disconnect()
        except Exception:
            pass

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._emit_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def is_running(self) -> bool:
        return self._running

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "engines": self.config.engines,
            "interval": self.config.interval,
            "max_cycles": self.config.max_cycles,
        }

    def run_once(self) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for engine_id in range(1, self.config.engines + 1):
            payload = self.build_telemetry_frame(engine_id)
            self.publish(payload)
            self._persist_prediction(payload)
            payloads.append(payload)
        return payloads
