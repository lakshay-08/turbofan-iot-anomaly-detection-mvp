from backend.services.simulator_service import SimulationConfig, LiveTelemetrySimulator


def test_simulator_builds_valid_telemetry_frame() -> None:
    simulator = LiveTelemetrySimulator()
    frame = simulator.build_telemetry_frame(engine_id=7, cycle=12)

    assert frame["engine_id"] == 7
    assert "features" in frame
    assert set(frame["features"]).issuperset({"sensor_2", "sensor_3", "sensor_4", "sensor_8"})
    assert frame["metadata"]["source"] == "simulator"


def test_different_engines_produce_distinct_telemetry_profiles() -> None:
    simulator = LiveTelemetrySimulator()

    engine_1 = simulator.build_telemetry_frame(engine_id=1, cycle=20)
    engine_2 = simulator.build_telemetry_frame(engine_id=2, cycle=20)

    assert engine_1["engine_id"] == 1
    assert engine_2["engine_id"] == 2
    assert engine_1["features"] != engine_2["features"]
    assert engine_1["anomaly_score"] != engine_2["anomaly_score"]


def test_default_simulation_config_is_valid() -> None:
    config = SimulationConfig()

    assert config.engines >= 1
    assert config.interval > 0
    assert config.max_cycles >= 1
