"""
IoT Sensor Simulator: NASA Turbofan (CMAPSS-like) telemetry publisher over MQTT.

Features:
- Config via env vars or CLI args (broker host/port, topic, interval, engine count).
- Generates realistic CMAPSS-style sensor readings with slow degradation and noise.
- JSON payload conforms to payload_schema.json in this folder.
- QoS selectable (default 1), optional TLS, last will message.
- Graceful shutdown (SIGINT/SIGTERM).
- Logging with structured context.

Usage:
    python mqtt_publisher.py \
        --host localhost --port 1883 --topic turbofan/telemetry \
        --engines 4 --interval 0.5 --qos 1

Environment variables (fallbacks for CLI):
    MQTT_HOST, MQTT_PORT, MQTT_TOPIC, MQTT_QOS, MQTT_USERNAME, MQTT_PASSWORD,
    MQTT_TLS (true/false), MQTT_CLIENT_ID, SIM_ENGINES, SIM_INTERVAL

Author: Abhilakshay Singh Pathania
"""

import os
import sys
import ssl
import json
import time
import math
import random
import signal
import argparse
import logging
from datetime import datetime, timezone

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Missing dependency: paho-mqtt. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("mqtt_publisher")


def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "y", "on")


def parse_args():
    parser = argparse.ArgumentParser(description="CMAPSS-like turbofan telemetry MQTT publisher")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "localhost"), help="MQTT broker host")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "turbofan/telemetry"), help="MQTT topic")
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], default=int(os.getenv("MQTT_QOS", "1")), help="MQTT QoS")
    parser.add_argument("--username", default=os.getenv("MQTT_USERNAME"), help="MQTT username (optional)")
    parser.add_argument("--password", default=os.getenv("MQTT_PASSWORD"), help="MQTT password (optional)")
    parser.add_argument("--tls", action="store_true", default=env_bool("MQTT_TLS", False), help="Enable TLS")
    parser.add_argument("--client-id", default=os.getenv("MQTT_CLIENT_ID", "turbofan-sim"), help="MQTT client ID")
    parser.add_argument("--engines", type=int, default=int(os.getenv("SIM_ENGINES", "4")), help="Number of engines to simulate")
    parser.add_argument("--interval", type=float, default=float(os.getenv("SIM_INTERVAL", "0.5")), help="Publish interval in seconds")
    parser.add_argument("--retain", action="store_true", help="Retain messages on broker")
    parser.add_argument("--sequence-start", type=int, default=1, help="Starting sequence number for telemetry")
    return parser.parse_args()


class EngineSim:
    """
    Simple physics-inspired simulator with slow degradation.
    Produces CMAPSS-style features: EGT, T2, P30, Nf, Nc, Ps30, Wf, phi, NRc.
    """
    def __init__(self, engine_id: str, start_cycle: int = 1):
        self.engine_id = engine_id
        self.cycle = start_cycle
        # Baselines (approximate typical ranges; tune as needed)
        self.baseline = {
            "EGT": 800.0,   # Exhaust Gas Temperature (°C)
            "T2": 500.0,    # Fan inlet temperature (°R/°C depending; we treat as °C)
            "P30": 15.0,    # Compressor outlet pressure (psi/atm modeled abstractly)
            "Nf": 12000.0,  # Fan speed (RPM)
            "Nc": 8000.0,   # Core speed (RPM)
            "Ps30": 40.0,   # Static pressure at station 30
            "Wf": 0.70,     # Fuel flow (normalized 0-1)
            "phi": 0.50,    # Fuel-air ratio (normalized)
            "NRc": 0.85,    # Corrected core speed (normalized)
        }
        # Degradation rates (slow drift)
        self.degrade = {
            "EGT": 0.02, "T2": 0.01, "P30": -0.001, "Nf": -0.5, "Nc": -0.3,
            "Ps30": -0.005, "Wf": 0.0008, "phi": 0.0005, "NRc": -0.0004
        }

    def step(self):
        self.cycle += 1
        sensors = {}
        # Operating conditions (simplified)
        alt = 30000 + 5000 * math.sin(self.cycle / 200.0)  # feet
        mach = 0.75 + 0.05 * math.sin(self.cycle / 150.0)
        throttle = 0.6 + 0.2 * math.sin(self.cycle / 180.0)

        for k, base in self.baseline.items():
            # Apply slow degradation
            drift = self.degrade[k] * (self.cycle / 100.0)
            # Add operational response (throttle influences temps/flows/speeds)
            op = 0.0
            if k in ("EGT", "T2", "Wf", "phi"):
                op = throttle * random.uniform(0.5, 1.2)
            elif k in ("Nf", "Nc"):
                op = throttle * random.uniform(100, 250)
            elif k in ("P30", "Ps30"):
                op = throttle * random.uniform(0.2, 0.6)
            elif k in ("NRc"):
                op = throttle * random.uniform(0.001, 0.005)

            noise = random.gauss(0, {
                "EGT": 1.2, "T2": 1.0, "P30": 0.05, "Nf": 30.0, "Nc": 25.0,
                "Ps30": 0.08, "Wf": 0.005, "phi": 0.004, "NRc": 0.0015
            }[k])

            val = base + drift + op + noise
            # Clamp some normalized features
            if k in ("Wf", "phi", "NRc"):
                val = max(0.0, min(1.0, val))
            sensors[k] = round(val, 3)

        frame = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine_id": self.engine_id,
            "sequence": self.cycle,
            "operating_condition": {
                "alt": round(alt, 2),
                "Mach": round(mach, 3),
                "Throttle": round(throttle, 3)
            },
            "sensors": sensors,
            "quality": {"status": "OK", "missing": 0},
            "meta": {"source": "sim", "schema_version": "1.1"}
        }
        return frame


def make_client(client_id: str, username: str | None, password: str | None, tls: bool, topic: str):
    client = mqtt.Client(client_id=client_id, clean_session=True, protocol=mqtt.MQTTv311)

    # Last Will message (optional): indicate simulator stopped unexpectedly
    will_payload = json.dumps({
        "event": "simulator_disconnected",
        "client_id": client_id,
        "topic": topic,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    client.will_set(topic + "/events", payload=will_payload, qos=1, retain=False)

    if username and password:
        client.username_pw_set(username=username, password=password)

    if tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)

    return client


shutdown = False
def _handle_signal(signum, frame):
    global shutdown
    shutdown = True
    log.info("Received signal %s, shutting down...", signum)

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def main():
    args = parse_args()
    log.info("Starting MQTT simulator: host=%s port=%d topic=%s qos=%d tls=%s engines=%d interval=%.2fs",
             args.host, args.port, args.topic, args.qos, args.tls, args.engines, args.interval)

    # Create clients and connect (one client, multiple engines)
    client = make_client(args.client_id, args.username, args.password, args.tls, args.topic)

    def on_connect(cl, userdata, flags, rc):
        if rc == 0:
            log.info("Connected to MQTT broker.")
        else:
            log.error("MQTT connect failed: rc=%s", rc)

    def on_disconnect(cl, userdata, rc):
        log.info("Disconnected from MQTT broker: rc=%s", rc)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    try:
        client.connect(args.host, args.port, keepalive=60)
    except Exception as e:
        log.exception("Failed to connect to MQTT broker: %s", e)
        sys.exit(2)

    client.loop_start()

    # Initialize engines
    engines = [EngineSim(engine_id=f"E_{i:03d}", start_cycle=args.sequence_start) for i in range(1, args.engines + 1)]

    # Publish loop
    published = 0
    try:
        while not shutdown:
            for eng in engines:
                frame = eng.step()
                payload = json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
                info = client.publish(args.topic, payload=payload, qos=args.qos, retain=args.retain)
                if info.rc != mqtt.MQTT_ERR_SUCCESS:
                    log.warning("Publish returned rc=%s", info.rc)
                else:
                    published += 1

            # Optional: emit a heartbeat
            hb = {
                "event": "heartbeat",
                "count": published,
                "topic": args.topic,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            client.publish(args.topic + "/events", payload=json.dumps(hb), qos=0, retain=False)

            time.sleep(args.interval)

    except Exception as e:
        log.exception("Simulator error: %s", e)
    finally:
        client.loop_stop()
        client.disconnect()
        log.info("Simulator stopped. Total messages published: %d", published)

if __name__ == "__main__":
    main()
