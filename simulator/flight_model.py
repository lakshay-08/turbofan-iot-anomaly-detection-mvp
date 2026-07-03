"""Flight mission profile generator for turbofan telemetry simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass

from sim_types import FlightPhase, OperatingCondition


@dataclass(slots=True)
class FlightPoint:
    altitude_ft: float
    mach: float
    ambient_temp_c: float
    throttle: float


PHASE_BASELINES: dict[FlightPhase, FlightPoint] = {
    FlightPhase.IDLE: FlightPoint(altitude_ft=1200.0, mach=0.03, ambient_temp_c=31.0, throttle=0.22),
    FlightPhase.TAKEOFF: FlightPoint(altitude_ft=2500.0, mach=0.24, ambient_temp_c=26.0, throttle=0.98),
    FlightPhase.CLIMB: FlightPoint(altitude_ft=19000.0, mach=0.58, ambient_temp_c=-8.0, throttle=0.86),
    FlightPhase.CRUISE: FlightPoint(altitude_ft=34000.0, mach=0.78, ambient_temp_c=-44.0, throttle=0.67),
    FlightPhase.DESCENT: FlightPoint(altitude_ft=9000.0, mach=0.44, ambient_temp_c=2.0, throttle=0.34),
}


@dataclass(slots=True)
class MissionConfig:
    idle_cycles: int = 18
    takeoff_cycles: int = 8
    climb_cycles: int = 35
    cruise_cycles: int = 110
    descent_cycles: int = 24
    transition_cycles: int = 6


class FlightMission:
    """Stateful flight profile with smooth phase transitions."""

    def __init__(self, rng: random.Random, config: MissionConfig | None = None) -> None:
        self.rng = rng
        self.config = config or MissionConfig()
        self.sequence = [
            (FlightPhase.IDLE, self.config.idle_cycles),
            (FlightPhase.TAKEOFF, self.config.takeoff_cycles),
            (FlightPhase.CLIMB, self.config.climb_cycles),
            (FlightPhase.CRUISE, self.config.cruise_cycles),
            (FlightPhase.DESCENT, self.config.descent_cycles),
        ]
        self.phase_index = 0
        self.phase_elapsed = 0

    @property
    def current_phase(self) -> FlightPhase:
        return self.sequence[self.phase_index][0]

    def _advance_phase_if_needed(self) -> None:
        _, duration = self.sequence[self.phase_index]
        if self.phase_elapsed >= duration:
            self.phase_index = (self.phase_index + 1) % len(self.sequence)
            self.phase_elapsed = 0

    def next_condition(self) -> tuple[FlightPhase, OperatingCondition]:
        phase, duration = self.sequence[self.phase_index]
        transition_window = min(self.config.transition_cycles, max(1, duration // 3))
        transition_alpha = max(0.0, (self.phase_elapsed - (duration - transition_window)) / transition_window)

        current_point = PHASE_BASELINES[phase]
        next_phase = self.sequence[(self.phase_index + 1) % len(self.sequence)][0]
        next_point = PHASE_BASELINES[next_phase]

        altitude = current_point.altitude_ft + (next_point.altitude_ft - current_point.altitude_ft) * transition_alpha
        mach = current_point.mach + (next_point.mach - current_point.mach) * transition_alpha
        ambient = current_point.ambient_temp_c + (next_point.ambient_temp_c - current_point.ambient_temp_c) * transition_alpha
        throttle = current_point.throttle + (next_point.throttle - current_point.throttle) * transition_alpha

        # Add small operational randomness without breaking mission shape.
        altitude += self.rng.uniform(-220.0, 220.0)
        mach = max(0.0, mach + self.rng.uniform(-0.015, 0.015))
        ambient += self.rng.uniform(-1.8, 1.8)
        throttle = min(1.0, max(0.05, throttle + self.rng.uniform(-0.02, 0.02)))

        self.phase_elapsed += 1
        self._advance_phase_if_needed()

        return phase, OperatingCondition(
            altitude_ft=altitude,
            mach=mach,
            ambient_temp_c=ambient,
            throttle=throttle,
        )
