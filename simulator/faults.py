"""Fault injection framework for turbofan telemetry simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from sim_types import FaultType

SENSOR_COLUMNS = [f"sensor_{index}" for index in range(1, 22)]
PREDICTION_FEATURES = {
    "sensor_2",
    "sensor_3",
    "sensor_4",
    "sensor_8",
    "sensor_9",
    "sensor_11",
    "sensor_13",
    "sensor_17",
}


@dataclass(slots=True)
class FaultInjectionConfig:
    fault_types: list[FaultType]
    fault_rate: float = 0.015
    fault_start_cycle: int = 80
    fault_duration: int = 65
    random_injection: bool = True


@dataclass(slots=True)
class EngineFaultState:
    active_faults: dict[FaultType, int] = field(default_factory=dict)
    drift_offsets: dict[str, float] = field(default_factory=dict)
    bias_offsets: dict[str, float] = field(default_factory=dict)
    stuck_values: dict[str, float | None] = field(default_factory=dict)


class FaultInjector:
    """Injects deterministic and random fault patterns over time."""

    def __init__(self, config: FaultInjectionConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng

    def _activate_new_fault(self, cycle: int, state: EngineFaultState) -> None:
        if cycle < self.config.fault_start_cycle:
            return
        if not self.config.fault_types:
            return
        if not self.config.random_injection:
            if not state.active_faults:
                fault = self.config.fault_types[cycle % len(self.config.fault_types)]
                state.active_faults[fault] = cycle + self.config.fault_duration
            return
        if self.rng.random() <= self.config.fault_rate:
            fault = self.rng.choice(self.config.fault_types)
            if fault not in state.active_faults:
                state.active_faults[fault] = cycle + self.config.fault_duration

    def _expire_faults(self, cycle: int, state: EngineFaultState) -> None:
        expired = [fault for fault, end_cycle in state.active_faults.items() if cycle >= end_cycle]
        for fault in expired:
            state.active_faults.pop(fault, None)

    def apply(self, sensors: dict[str, float | None], cycle: int, state: EngineFaultState) -> tuple[dict[str, float | None], list[str], list[dict[str, str]]]:
        self._expire_faults(cycle, state)
        self._activate_new_fault(cycle, state)

        anomalies: list[dict[str, str]] = []
        active_fault_names: list[str] = [fault.value for fault in state.active_faults]

        for fault in list(state.active_faults):
            if fault == FaultType.COMPRESSOR_EFFICIENCY_LOSS:
                sensors["sensor_3"] = float(sensors["sensor_3"] or 0.0) * 1.03
                sensors["sensor_4"] = float(sensors["sensor_4"] or 0.0) * 1.04
                sensors["sensor_9"] = float(sensors["sensor_9"] or 0.0) * 0.97
                sensors["sensor_13"] = float(sensors["sensor_13"] or 0.0) * 0.99
            elif fault == FaultType.TURBINE_DEGRADATION:
                sensors["sensor_11"] = float(sensors["sensor_11"] or 0.0) * 1.07
                sensors["sensor_17"] = float(sensors["sensor_17"] or 0.0) * 0.95
                sensors["sensor_20"] = float(sensors["sensor_20"] or 0.0) * 1.04
            elif fault == FaultType.FUEL_SYSTEM_DEGRADATION:
                sensors["sensor_12"] = float(sensors["sensor_12"] or 0.0) * 0.94
                sensors["sensor_15"] = float(sensors["sensor_15"] or 0.0) * 1.08
                sensors["sensor_21"] = float(sensors["sensor_21"] or 0.0) * 0.95
            elif fault == FaultType.SENSOR_DRIFT:
                sensor = self.rng.choice(SENSOR_COLUMNS)
                state.drift_offsets[sensor] = state.drift_offsets.get(sensor, 0.0) + self.rng.uniform(-0.002, 0.002)
            elif fault == FaultType.SENSOR_BIAS:
                sensor = self.rng.choice(SENSOR_COLUMNS)
                if sensor not in state.bias_offsets:
                    state.bias_offsets[sensor] = self.rng.uniform(-0.03, 0.03)
            elif fault == FaultType.STUCK_SENSOR:
                sensor = self.rng.choice(SENSOR_COLUMNS)
                if sensor not in state.stuck_values:
                    state.stuck_values[sensor] = sensors.get(sensor)
            elif fault == FaultType.INTERMITTENT_SENSOR_FAILURE:
                mutable_columns = [column for column in SENSOR_COLUMNS if column not in PREDICTION_FEATURES]
                sensor = self.rng.choice(mutable_columns or SENSOR_COLUMNS)
                if self.rng.random() < 0.25:
                    sensors[sensor] = None
                    anomalies.append({"type": "intermittent_sensor_failure", "sensor": sensor})

        for sensor, drift in state.drift_offsets.items():
            if sensors.get(sensor) is not None:
                sensors[sensor] = float(sensors[sensor] or 0.0) + drift

        for sensor, bias in state.bias_offsets.items():
            if sensors.get(sensor) is not None:
                sensors[sensor] = float(sensors[sensor] or 0.0) * (1.0 + bias)

        for sensor, stuck in state.stuck_values.items():
            sensors[sensor] = stuck

        return sensors, active_fault_names, anomalies
