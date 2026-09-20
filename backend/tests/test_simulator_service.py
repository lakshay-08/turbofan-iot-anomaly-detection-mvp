from backend.services.simulator_service import SimulationConfig, LiveTelemetrySimulator


def test_simulator_builds_valid_telemetry_frame() -> None:
    simulator = LiveTelemetrySimulator()
    frame = simulator.build_telemetry_frame(engine_id=7, cycle=12)

    assert frame["engine_id"] == 7
    assert "features" in frame
    assert set(frame["features"]).issuperset({"sensor_2", "sensor_3", "sensor_4", "sensor_8"})
    assert frame["metadata"]["source"] == "simulator"


def test_default_simulation_config_is_valid() -> None:
    config = SimulationConfig()

    assert config.engines >= 1
    assert config.interval > 0
    assert config.max_cycles >= 1
