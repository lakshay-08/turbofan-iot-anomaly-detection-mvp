"""NASA CMAPSS-inspired engine digital twin for telemetry generation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from faults import EngineFaultState, FaultInjectionConfig, FaultInjector
from flight_model import FlightMission, MissionConfig
from sim_types import QualityReport

FEATURE_BOUNDS: dict[str, tuple[float, float]] = {
    "sensor_1": (518.2, 519.2),
    "sensor_2": (620.0, 690.0),
    "sensor_3": (1450.0, 1750.0),
    "sensor_4": (1280.0, 1500.0),
    "sensor_5": (14.2, 15.2),
    "sensor_6": (20.8, 22.5),
    "sensor_7": (510.0, 620.0),
    "sensor_8": (2360.0, 2410.0),
    "sensor_9": (8600.0, 9800.0),
    "sensor_10": (1.15, 1.45),
    "sensor_11": (42.0, 62.0),
    "sensor_12": (500.0, 580.0),
    "sensor_13": (2360.0, 2410.0),
    "sensor_14": (7600.0, 9100.0),
    "sensor_15": (7.5, 11.0),
    "sensor_16": (0.0, 0.08),
    "sensor_17": (350.0, 460.0),
    "sensor_18": (2386.0, 2390.0),
    "sensor_19": (99.0, 101.0),
    "sensor_20": (32.0, 52.0),
    "sensor_21": (20.0, 31.0),
}

PREDICTION_FEATURES = [
    "sensor_2",
    "sensor_3",
    "sensor_4",
    "sensor_8",
    "sensor_9",
    "sensor_11",
    "sensor_13",
    "sensor_17",
]


@dataclass(slots=True)
class EngineRuntimeConfig:
    max_life_min: int = 220
    max_life_max: int = 430
    debug_mode: bool = False
    spike_probability: float = 0.008
    dropout_probability: float = 0.004
    missing_probability: float = 0.004
    comm_loss_probability: float = 0.002
    out_of_range_probability: float = 0.004
    telemetry_mode: str = "full-cmapss"


@dataclass(slots=True)
class EngineState:
    engine_id: str
    cycle: int
    sequence: int
    max_life: int
    health_score: float
    rul: int
    failed: bool
    engine_noise_factor: float
    mission: FlightMission
    last_valid_features: dict[str, float]
    fault_state: EngineFaultState = field(default_factory=EngineFaultState)


class EngineDigitalTwin:
    """Stateful digital twin with mission dynamics, faults, and anomalies."""

    def __init__(
        self,
        engine_id: str,
        rng_seed: int,
        start_cycle: int,
        mission_config: MissionConfig,
        runtime_config: EngineRuntimeConfig,
        fault_config: FaultInjectionConfig,
    ) -> None:
        self.rng = random.Random(rng_seed)
        self.runtime_config = runtime_config
        self.fault_injector = FaultInjector(fault_config, self.rng)

        max_life = self.rng.randint(runtime_config.max_life_min, runtime_config.max_life_max)
        mission = FlightMission(self.rng, mission_config)
        self.state = EngineState(
            engine_id=engine_id,
            cycle=start_cycle,
            sequence=start_cycle,
            max_life=max_life,
            health_score=1.0,
            rul=max(0, max_life - start_cycle),
            failed=False,
            engine_noise_factor=self.rng.uniform(0.85, 1.25),
            mission=mission,
            last_valid_features={},
        )

    def _degradation_curve(self, cycle: int) -> float:
        normalized_age = min(1.2, cycle / max(1, self.state.max_life))
        if normalized_age < 0.45:
            degradation = 0.08 * math.pow(normalized_age, 1.35)
        elif normalized_age < 0.8:
            degradation = 0.04 + 0.28 * math.pow((normalized_age - 0.45) / 0.35, 1.8)
        else:
            degradation = 0.32 + 0.70 * math.pow((normalized_age - 0.8) / 0.4, 2.2)
        return max(0.0, min(1.0, degradation))

    def _feature_noise(self, sensor_name: str) -> float:
        std = {
            "sensor_1": 0.02,
            "sensor_2": 0.8,
            "sensor_3": 2.5,
            "sensor_4": 2.1,
            "sensor_5": 0.01,
            "sensor_6": 0.015,
            "sensor_7": 1.9,
            "sensor_8": 0.45,
            "sensor_9": 12.0,
            "sensor_10": 0.002,
            "sensor_11": 0.22,
            "sensor_12": 0.45,
            "sensor_13": 0.4,
            "sensor_14": 10.0,
            "sensor_15": 0.03,
            "sensor_16": 0.0015,
            "sensor_17": 1.0,
            "sensor_18": 0.05,
            "sensor_19": 0.02,
            "sensor_20": 0.18,
            "sensor_21": 0.11,
        }[sensor_name]
        return self.rng.gauss(0.0, std)

    def _clamp(self, value: float, sensor_name: str) -> float:
        lower, upper = FEATURE_BOUNDS[sensor_name]
        return min(upper, max(lower, value))

    def _generate_operational_settings(self, condition: dict[str, float], degradation: float) -> dict[str, float]:
        setting_1 = (condition["Throttle"] - 0.6) * 0.08 + (degradation - 0.25) * 0.02
        setting_2 = (condition["Mach"] - 0.65) * 0.0015
        setting_3 = 100.0
        return {
            "setting_1": round(setting_1, 4),
            "setting_2": round(setting_2, 4),
            "setting_3": setting_3,
        }

    def _generate_features(self, health: float, condition: dict[str, float], shared_noise: float) -> dict[str, float]:
        throttle = condition["Throttle"]
        mach = condition["Mach"]
        altitude = condition["alt"]
        ambient_temp = condition["ambient_temp_c"]

        degradation = 1.0 - health
        density_factor = max(0.78, 1.02 - altitude / 120000.0)

        features = {
            "sensor_1": 518.67 + shared_noise * 0.03,
            "sensor_2": 632.0 + throttle * 16.0 + degradation * 19.0 - ambient_temp * 0.25 + shared_noise * 0.8,
            "sensor_3": 1520.0 + throttle * 90.0 + degradation * 140.0 + shared_noise * 3.8,
            "sensor_4": 1365.0 + throttle * 55.0 + degradation * 118.0 + shared_noise * 3.5,
            "sensor_5": 14.62 + shared_noise * 0.01,
            "sensor_6": 21.61 + shared_noise * 0.02,
            "sensor_7": 535.0 + throttle * 55.0 + degradation * 95.0 + shared_noise * 2.4,
            "sensor_8": 2380.0 + throttle * 11.0 + degradation * 19.0 + density_factor * 4.0,
            "sensor_9": 8900.0 + throttle * 410.0 + degradation * 640.0 + shared_noise * 16.0,
            "sensor_10": 1.30 + shared_noise * 0.003,
            "sensor_11": 44.0 + throttle * 5.0 + degradation * 12.0 + shared_noise * 0.55,
            "sensor_12": 508.0 + throttle * 26.0 + degradation * 38.0 + shared_noise * 0.9,
            "sensor_13": 2382.0 + throttle * 10.0 + degradation * 18.0 + density_factor * 3.2,
            "sensor_14": 7850.0 + throttle * 320.0 + degradation * 780.0 + shared_noise * 14.0,
            "sensor_15": 7.95 + throttle * 1.1 + degradation * 1.6 + shared_noise * 0.06,
            "sensor_16": 0.03 + shared_noise * 0.002,
            "sensor_17": 365.0 + throttle * 32.0 + degradation * 44.0 + shared_noise * 1.4,
            "sensor_18": 2388.0 + shared_noise * 0.06,
            "sensor_19": 100.0 + shared_noise * 0.04,
            "sensor_20": 35.0 + throttle * 4.2 + degradation * 8.2 + shared_noise * 0.35,
            "sensor_21": 21.7 + throttle * 2.5 + degradation * 3.9 + shared_noise * 0.2,
        }

        for sensor_name, base_value in features.items():
            noisy_value = base_value + self._feature_noise(sensor_name)
            features[sensor_name] = round(self._clamp(noisy_value, sensor_name), 3)
        return features

    def _prediction_features_from_full(self, full_features: dict[str, float | None]) -> dict[str, float]:
        derived: dict[str, float] = {}
        for feature_name in PREDICTION_FEATURES:
            value = full_features.get(feature_name)
            if value is None:
                value = self.state.last_valid_features.get(feature_name, 0.0)
            derived[feature_name] = round(float(value), 3)
        return derived

    def _inject_anomalies(self, features: dict[str, float | None]) -> tuple[list[dict[str, str]], bool]:
        anomalies: list[dict[str, str]] = []
        communication_loss = False
        sensor_keys = list(features.keys())
        mutable_for_missing = [key for key in sensor_keys if key not in PREDICTION_FEATURES]

        if self.rng.random() < self.runtime_config.spike_probability:
            target = self.rng.choice(sensor_keys)
            spike_factor = self.rng.uniform(1.12, 1.35)
            if features[target] is not None:
                features[target] = round(float(features[target] or 0.0) * spike_factor, 3)
                anomalies.append({"type": "sudden_spike", "sensor": target})

        if mutable_for_missing and self.rng.random() < self.runtime_config.dropout_probability:
            target = self.rng.choice(mutable_for_missing)
            features[target] = None
            anomalies.append({"type": "sensor_dropout", "sensor": target})

        if mutable_for_missing and self.rng.random() < self.runtime_config.missing_probability:
            target = self.rng.choice(mutable_for_missing)
            features[target] = None
            anomalies.append({"type": "missing_value", "sensor": target})

        if self.rng.random() < self.runtime_config.out_of_range_probability:
            target = self.rng.choice(sensor_keys)
            _, upper = FEATURE_BOUNDS[target]
            features[target] = round(upper * self.rng.uniform(1.1, 1.25), 3)
            anomalies.append({"type": "out_of_range", "sensor": target})

        if self.rng.random() < self.runtime_config.comm_loss_probability:
            communication_loss = True
            anomalies.append({"type": "communication_loss", "sensor": "mqtt"})

        return anomalies, communication_loss

    def _quality_report(self, features: dict[str, float | None], communication_loss: bool) -> QualityReport:
        missing = sum(1 for value in features.values() if value is None)
        out_of_range = 0
        for sensor_name, value in features.items():
            if value is None:
                continue
            lower, upper = FEATURE_BOUNDS[sensor_name]
            if value < lower or value > upper:
                out_of_range += 1

        status = "OK"
        if communication_loss or missing > 0:
            status = "WARN"
        if out_of_range > 0 or self.state.failed:
            status = "BAD"

        return QualityReport(
            status=status,
            missing=missing,
            out_of_range=out_of_range,
            comm_loss=communication_loss,
        )

    def step(self) -> tuple[dict[str, object], bool]:
        self.state.cycle += 1
        self.state.sequence += 1

        degradation_index = self._degradation_curve(self.state.cycle)
        self.state.health_score = max(0.0, 1.0 - degradation_index)
        self.state.rul = max(0, self.state.max_life - self.state.cycle)
        self.state.failed = self.state.health_score <= 0.08 or self.state.rul == 0

        phase, operating_condition = self.state.mission.next_condition()
        condition_payload = operating_condition.to_payload()
        operational_settings = self._generate_operational_settings(condition_payload, degradation_index)

        shared_noise = self.rng.gauss(0.0, 1.0) * self.state.engine_noise_factor
        features = self._generate_features(self.state.health_score, condition_payload, shared_noise)

        features, active_faults, fault_anomalies = self.fault_injector.apply(
            features,
            cycle=self.state.cycle,
            state=self.state.fault_state,
        )

        random_anomalies, communication_loss = self._inject_anomalies(features)
        anomalies = fault_anomalies + random_anomalies

        prediction_features = self._prediction_features_from_full(features)
        for key, value in prediction_features.items():
            features[key] = value
            self.state.last_valid_features[key] = value

        quality = self._quality_report(features, communication_loss)

        anomaly_score = min(
            1.0,
            max(
                0.0,
                (1.0 - self.state.health_score) * 0.55
                + len(active_faults) * 0.12
                + len(anomalies) * 0.10,
            ),
        )
        failure_probability = 1.0 / (1.0 + math.exp(-8.0 * ((1.0 - self.state.health_score) - 0.45)))
        failure_probability = min(1.0, max(0.0, failure_probability + anomaly_score * 0.15))

        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine_id": self.state.engine_id,
            "cycle": self.state.cycle,
            "sequence": self.state.sequence,
            "health_score": round(self.state.health_score, 4),
            "degradation_index": round(1.0 - self.state.health_score, 4),
            "anomaly_score": round(anomaly_score, 4),
            "predicted_failure_probability": round(failure_probability, 4),
            "flight_phase": phase.value,
            "operational_settings": operational_settings,
            "operating_condition": condition_payload,
            "prediction_features": prediction_features,
            "quality": quality.to_payload(),
            "faults": active_faults,
            "meta": {
                "source": "sim",
                "schema_version": "2.1",
                "failed": self.state.failed,
                "anomalies": anomalies,
                "telemetry_mode": self.runtime_config.telemetry_mode,
            },
        }

        if self.runtime_config.telemetry_mode == "prediction-compatible":
            payload["features"] = prediction_features
        else:
            payload["features"] = features

        if self.runtime_config.debug_mode:
            payload["debug"] = {
                "true_rul": self.state.rul,
                "max_life": self.state.max_life,
            }

        return payload, communication_loss
