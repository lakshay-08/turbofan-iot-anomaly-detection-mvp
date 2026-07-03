"""Production-grade CMAPSS-inspired turbofan telemetry simulator over MQTT."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import signal
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from engine_model import EngineDigitalTwin, EngineRuntimeConfig
from faults import FaultInjectionConfig
from flight_model import MissionConfig
from sim_types import FaultType

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Missing dependency: paho-mqtt. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("turbofan_simulator")


def log_event(level: str, event: str, **fields: object) -> None:
    payload = {"event": event, **fields}
    getattr(log, level, log.info)(json.dumps(payload, separators=(",", ":"), default=str))


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "y", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(slots=True)
class SimulatorConfig:
    host: str
    port: int
    topic: str
    qos: int
    username: str | None
    password: str | None
    tls: bool
    client_id: str
    retain: bool
    engines: int
    interval: float
    sequence_start: int
    debug_mode: bool
    batch_mode: bool
    batch_size: int
    heartbeat_interval_sec: float
    random_seed: int
    fault_types: list[FaultType]
    fault_rate: float
    fault_start_cycle: int
    fault_duration: int
    random_faults: bool
    spike_probability: float
    dropout_probability: float
    missing_probability: float
    comm_loss_probability: float
    out_of_range_probability: float
    max_life_min: int
    max_life_max: int
    telemetry_mode: str


SHUTDOWN = False


def _handle_signal(signum: int, frame: object) -> None:
    del frame
    global SHUTDOWN
    SHUTDOWN = True
    log_event("info", "shutdown_requested", signal=signum)


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def parse_fault_types(raw_fault_types: list[str]) -> list[FaultType]:
    parsed: list[FaultType] = []
    for fault_name in raw_fault_types:
        fault_normalized = fault_name.strip().lower()
        try:
            parsed.append(FaultType(fault_normalized))
        except ValueError as exc:
            valid = [fault.value for fault in FaultType]
            raise argparse.ArgumentTypeError(
                f"Unsupported fault type '{fault_name}'. Valid values: {valid}"
            ) from exc
    return parsed


def parse_args() -> SimulatorConfig:
    parser = argparse.ArgumentParser(description="CMAPSS-inspired turbofan telemetry MQTT publisher")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "turbofan/telemetry"), help="Base telemetry topic")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=int(os.getenv("MQTT_QOS", "1")), help="MQTT QoS")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password")
    parser.add_argument("--tls", action=argparse.BooleanOptionalAction, default=env_bool("MQTT_TLS", False), help="Enable TLS")
    parser.add_argument("--client-id", default=os.getenv("MQTT_CLIENT_ID", "turbofan-sim"), help="MQTT client ID")
    parser.add_argument("--retain", action=argparse.BooleanOptionalAction, default=env_bool("MQTT_RETAIN", False), help="MQTT retain flag")

    parser.add_argument("--engines", type=int, default=int(os.getenv("SIM_ENGINES", "4")), help="Number of engines (1..1000)")
    parser.add_argument("--interval", type=float, default=float(os.getenv("SIM_INTERVAL", "0.5")), help="Publish interval in seconds")
    parser.add_argument("--sequence-start", type=int, default=int(os.getenv("SIM_SEQUENCE_START", "1")), help="Starting sequence number")
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction, default=env_bool("SIM_DEBUG", False), help="Include hidden RUL in payload")

    parser.add_argument("--batch-mode", action=argparse.BooleanOptionalAction, default=env_bool("SIM_BATCH_MODE", False), help="Publish batches instead of per-engine frames")
    parser.add_argument("--batch-size", type=int, default=int(os.getenv("SIM_BATCH_SIZE", "100")), help="Batch publish size")
    parser.add_argument("--heartbeat-interval", type=float, default=float(os.getenv("SIM_HEARTBEAT_INTERVAL", "5.0")), help="Heartbeat interval in seconds")
    parser.add_argument("--random-seed", type=int, default=int(os.getenv("SIM_RANDOM_SEED", "42")), help="Random seed")

    parser.add_argument("--fault-types", default=",".join(env_list("SIM_FAULT_TYPES", "")), help="Comma separated fault types")
    parser.add_argument("--fault-rate", type=float, default=float(os.getenv("SIM_FAULT_RATE", "0.015")), help="Random fault activation probability")
    parser.add_argument("--fault-start-cycle", type=int, default=int(os.getenv("SIM_FAULT_START_CYCLE", "80")), help="Cycle at which fault injection may start")
    parser.add_argument("--fault-duration", type=int, default=int(os.getenv("SIM_FAULT_DURATION", "65")), help="Fault duration in cycles")
    parser.add_argument("--random-faults", action=argparse.BooleanOptionalAction, default=env_bool("SIM_RANDOM_FAULTS", True), help="Enable random fault injection")

    parser.add_argument("--spike-prob", type=float, default=float(os.getenv("SIM_SPIKE_PROB", "0.008")), help="Sudden spike anomaly probability")
    parser.add_argument("--dropout-prob", type=float, default=float(os.getenv("SIM_DROPOUT_PROB", "0.004")), help="Sensor dropout probability")
    parser.add_argument("--missing-prob", type=float, default=float(os.getenv("SIM_MISSING_PROB", "0.004")), help="Missing value anomaly probability")
    parser.add_argument("--comm-loss-prob", type=float, default=float(os.getenv("SIM_COMM_LOSS_PROB", "0.002")), help="Communication loss anomaly probability")
    parser.add_argument("--out-of-range-prob", type=float, default=float(os.getenv("SIM_OUT_OF_RANGE_PROB", "0.004")), help="Out-of-range anomaly probability")

    parser.add_argument("--max-life-min", type=int, default=int(os.getenv("SIM_MAX_LIFE_MIN", "220")), help="Minimum synthetic max-life cycles")
    parser.add_argument("--max-life-max", type=int, default=int(os.getenv("SIM_MAX_LIFE_MAX", "430")), help="Maximum synthetic max-life cycles")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--prediction-compatible",
        action="store_true",
        default=env_bool("SIM_PREDICTION_COMPATIBLE", False),
        help="Publish prediction feature subset while still deriving from full CMAPSS internally",
    )
    mode_group.add_argument(
        "--full-cmapss",
        action="store_true",
        default=env_bool("SIM_FULL_CMAPSS", False),
        help="Publish full CMAPSS sensor_1..sensor_21 payload",
    )

    args = parser.parse_args()

    if args.engines < 1 or args.engines > 1000:
        parser.error("--engines must be in range [1, 1000]")
    if args.interval <= 0:
        parser.error("--interval must be > 0")
    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")
    if args.max_life_min < 50 or args.max_life_max <= args.max_life_min:
        parser.error("--max-life values are invalid")

    fault_types = parse_fault_types([part.strip() for part in args.fault_types.split(",") if part.strip()])
    telemetry_mode = "prediction-compatible" if args.prediction_compatible else "full-cmapss"
    if args.full_cmapss:
        telemetry_mode = "full-cmapss"

    return SimulatorConfig(
        host=args.host,
        port=args.port,
        topic=args.topic.rstrip("/"),
        qos=args.qos,
        username=args.username,
        password=args.password,
        tls=args.tls,
        client_id=args.client_id,
        retain=args.retain,
        engines=args.engines,
        interval=args.interval,
        sequence_start=args.sequence_start,
        debug_mode=args.debug,
        batch_mode=args.batch_mode,
        batch_size=args.batch_size,
        heartbeat_interval_sec=args.heartbeat_interval,
        random_seed=args.random_seed,
        fault_types=fault_types,
        fault_rate=args.fault_rate,
        fault_start_cycle=args.fault_start_cycle,
        fault_duration=args.fault_duration,
        random_faults=args.random_faults,
        spike_probability=args.spike_prob,
        dropout_probability=args.dropout_prob,
        missing_probability=args.missing_prob,
        comm_loss_probability=args.comm_loss_prob,
        out_of_range_probability=args.out_of_range_prob,
        max_life_min=args.max_life_min,
        max_life_max=args.max_life_max,
        telemetry_mode=telemetry_mode,
    )


def make_client(config: SimulatorConfig) -> mqtt.Client:
    client = mqtt.Client(client_id=config.client_id, clean_session=True, protocol=mqtt.MQTTv311)

    will_payload = json.dumps(
        {
            "event": "simulator_disconnected",
            "client_id": config.client_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        separators=(",", ":"),
    )
    client.will_set(f"{config.topic}/events", payload=will_payload, qos=1, retain=False)

    if config.username:
        client.username_pw_set(username=config.username, password=config.password)

    if config.tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)

    return client


def publish_individual_frames(
    client: mqtt.Client,
    config: SimulatorConfig,
    frames: list[dict[str, object]],
) -> int:
    published = 0
    for frame in frames:
        payload = json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
        info = client.publish(config.topic, payload=payload, qos=config.qos, retain=config.retain)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            published += 1
        else:
            log_event("warning", "publish_failed", rc=info.rc, topic=config.topic)
    return published


def publish_batch_frames(
    client: mqtt.Client,
    config: SimulatorConfig,
    frames: list[dict[str, object]],
) -> int:
    if not frames:
        return 0
    batch_topic = f"{config.topic}/batch"
    published = 0
    for index in range(0, len(frames), config.batch_size):
        chunk = frames[index:index + config.batch_size]
        batch_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(chunk),
            "frames": chunk,
            "mode": "batch",
        }
        info = client.publish(
            batch_topic,
            payload=json.dumps(batch_payload, separators=(",", ":"), ensure_ascii=False),
            qos=config.qos,
            retain=config.retain,
        )
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            published += len(chunk)
        else:
            log_event("warning", "batch_publish_failed", rc=info.rc, topic=batch_topic)
    return published


def main() -> None:
    config = parse_args()
    log_event(
        "info",
        "simulator_starting",
        host=config.host,
        port=config.port,
        topic=config.topic,
        engines=config.engines,
        interval=config.interval,
        qos=config.qos,
        batch_mode=config.batch_mode,
        telemetry_mode=config.telemetry_mode,
    )

    mission_config = MissionConfig()
    runtime_config = EngineRuntimeConfig(
        max_life_min=config.max_life_min,
        max_life_max=config.max_life_max,
        debug_mode=config.debug_mode,
        spike_probability=config.spike_probability,
        dropout_probability=config.dropout_probability,
        missing_probability=config.missing_probability,
        comm_loss_probability=config.comm_loss_probability,
        out_of_range_probability=config.out_of_range_probability,
        telemetry_mode=config.telemetry_mode,
    )
    fault_config = FaultInjectionConfig(
        fault_types=config.fault_types,
        fault_rate=config.fault_rate,
        fault_start_cycle=config.fault_start_cycle,
        fault_duration=config.fault_duration,
        random_injection=config.random_faults,
    )

    rng = random.Random(config.random_seed)
    twins: list[EngineDigitalTwin] = []
    for index in range(1, config.engines + 1):
        twins.append(
            EngineDigitalTwin(
                engine_id=f"E_{index:03d}",
                rng_seed=rng.randint(1, 10_000_000),
                start_cycle=config.sequence_start,
                mission_config=mission_config,
                runtime_config=runtime_config,
                fault_config=fault_config,
            )
        )

    client = make_client(config)

    def on_connect(cl: mqtt.Client, userdata: object, flags: dict[str, int], rc: int) -> None:
        del cl, userdata, flags
        if rc == 0:
            log_event("info", "mqtt_connected", rc=rc)
        else:
            log_event("error", "mqtt_connect_failed", rc=rc)

    def on_disconnect(cl: mqtt.Client, userdata: object, rc: int) -> None:
        del cl, userdata
        log_event("info", "mqtt_disconnected", rc=rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(config.host, config.port, keepalive=60)
    except Exception as exc:  # pragma: no cover - external IO
        log_event("error", "mqtt_connect_exception", error=str(exc))
        sys.exit(2)

    client.loop_start()

    total_published = 0
    total_dropped_comm_loss = 0
    last_heartbeat = time.monotonic()

    try:
        while not SHUTDOWN:
            cycle_frames: list[dict[str, object]] = []
            for twin in twins:
                frame, comm_loss = twin.step()
                if comm_loss:
                    total_dropped_comm_loss += 1
                    continue
                cycle_frames.append(frame)

            if config.batch_mode:
                total_published += publish_batch_frames(client, config, cycle_frames)
            else:
                total_published += publish_individual_frames(client, config, cycle_frames)

            now = time.monotonic()
            if now - last_heartbeat >= config.heartbeat_interval_sec:
                heartbeat = {
                    "event": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "topic": config.topic,
                    "published": total_published,
                    "dropped_comm_loss": total_dropped_comm_loss,
                    "engines": config.engines,
                    "batch_mode": config.batch_mode,
                }
                client.publish(
                    f"{config.topic}/events",
                    payload=json.dumps(heartbeat, separators=(",", ":")),
                    qos=0,
                    retain=False,
                )
                last_heartbeat = now

            time.sleep(config.interval)

    except Exception as exc:  # pragma: no cover - runtime guard
        log_event("error", "simulator_runtime_exception", error=str(exc))
    finally:
        client.loop_stop()
        client.disconnect()
        log_event(
            "info",
            "simulator_stopped",
            total_published=total_published,
            dropped_comm_loss=total_dropped_comm_loss,
        )


if __name__ == "__main__":
    main()
