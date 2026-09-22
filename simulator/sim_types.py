"""Shared types for the turbofan telemetry simulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FlightPhase(str, Enum):
    IDLE = "IDLE"
    TAKEOFF = "TAKEOFF"
    CLIMB = "CLIMB"
    CRUISE = "CRUISE"
    DESCENT = "DESCENT"


class FaultType(str, Enum):
    COMPRESSOR_EFFICIENCY_LOSS = "compressor_efficiency_loss"
    TURBINE_DEGRADATION = "turbine_degradation"
    FUEL_SYSTEM_DEGRADATION = "fuel_system_degradation"
    SENSOR_DRIFT = "sensor_drift"
    SENSOR_BIAS = "sensor_bias"
    STUCK_SENSOR = "stuck_sensor"
    INTERMITTENT_SENSOR_FAILURE = "intermittent_sensor_failure"


@dataclass(slots=True)
class OperatingCondition:
    altitude_ft: float
    mach: float
    ambient_temp_c: float
    throttle: float

    def to_payload(self) -> dict[str, float]:
        return {
            "alt": round(self.altitude_ft, 2),
            "Mach": round(self.mach, 3),
            "ambient_temp_c": round(self.ambient_temp_c, 2),
            "Throttle": round(self.throttle, 3),
        }


@dataclass(slots=True)
class QualityReport:
    status: str
    missing: int
    out_of_range: int
    comm_loss: bool

    def to_payload(self) -> dict[str, int | str | bool]:
        return {
            "status": self.status,
            "missing": self.missing,
            "out_of_range": self.out_of_range,
            "comm_loss": self.comm_loss,
        }
