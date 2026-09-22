# Turbofan Digital Twin MQTT Simulator

Production-grade NASA CMAPSS-inspired turbofan telemetry simulator for predictive maintenance, anomaly detection, digital twin, and RUL validation workloads.

## Capabilities

- MQTT publishing via `paho-mqtt` using MQTT v3.1.1.
- Configurable via CLI and environment variables.
- Mission-aware flight profile: `IDLE -> TAKEOFF -> CLIMB -> CRUISE -> DESCENT`.
- Non-linear degradation model with hidden health and RUL.
- CMAPSS-style sensor generation (`EGT`, `T2`, `P30`, `Nf`, `Nc`, `Ps30`, `Wf`, `phi`, `NRc`).
- Full CMAPSS-like feature coverage (`sensor_1..sensor_21`) with operational settings.
- Correlated noise through per-engine shared noise factors.
- Fault injection framework with random and time-based activation.
- Anomaly simulation: spikes, dropouts, missing values, communication loss, out-of-range values.
- Digital twin outputs: health score, degradation index, anomaly score, failure probability.
- Supports 1..1000 engines.
- Individual and batch publishing modes.

## Files

- `mqtt_publisher.py`: main simulator entrypoint.
- `engine_model.py`: digital twin state and telemetry synthesis.
- `flight_model.py`: mission phase simulation and condition transitions.
- `faults.py`: fault injection engine.
- `sim_types.py`: shared enums and typed payload helpers.
- `payload_schema.json`: telemetry schema reference.

## MQTT Topic Hierarchy

- `turbofan/telemetry`: per-engine telemetry frames (individual mode).
- `turbofan/telemetry/batch`: telemetry batches (batch mode).
- `turbofan/telemetry/events`: heartbeat and lifecycle events.

Use `--topic` (or `MQTT_TOPIC`) to override the `turbofan/telemetry` base topic.

## Example Payload

```json
{
  "timestamp": "2026-07-02T10:43:10.123456+00:00",
  "engine_id": "E_001",
  "cycle": 221,
  "sequence": 221,
  "health_score": 0.8421,
  "degradation_index": 0.1579,
  "anomaly_score": 0.1083,
  "predicted_failure_probability": 0.1422,
  "flight_phase": "CRUISE",
  "operational_settings": {
    "setting_1": -0.0012,
    "setting_2": 0.0002,
    "setting_3": 100.0
  },
  "operating_condition": {
    "alt": 33980.12,
    "Mach": 0.781,
    "ambient_temp_c": -43.6,
    "Throttle": 0.672
  },
  "features": {
    "sensor_1": 518.67,
    "sensor_2": 642.36,
    "sensor_3": 1583.23,
    "sensor_4": 1396.84,
    "sensor_5": 14.62,
    "sensor_6": 21.61,
    "sensor_7": 553.97,
    "sensor_8": 2387.96,
    "sensor_9": 9062.17,
    "sensor_10": 1.30,
    "sensor_11": 47.30,
    "sensor_12": 522.31,
    "sensor_13": 2388.01,
    "sensor_14": 8145.32,
    "sensor_15": 8.42,
    "sensor_16": 0.03,
    "sensor_17": 391.00,
    "sensor_18": 2388.00,
    "sensor_19": 100.00,
    "sensor_20": 39.11,
    "sensor_21": 23.35
  },
  "prediction_features": {
    "sensor_2": 642.36,
    "sensor_3": 1583.23,
    "sensor_4": 1396.84,
    "sensor_8": 2387.96,
    "sensor_9": 9062.17,
    "sensor_11": 47.30,
    "sensor_13": 2388.01,
    "sensor_17": 391.00
  },
  "quality": {
    "status": "OK",
    "missing": 0,
    "out_of_range": 0,
    "comm_loss": false
  },
  "faults": [],
  "meta": {
    "source": "sim",
    "schema_version": "2.0",
    "failed": false,
    "anomalies": []
  }
}
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (CLI)

```bash
python mqtt_publisher.py \
  --host localhost \
  --port 1883 \
  --topic turbofan/telemetry \
  --engines 8 \
  --interval 0.5 \
  --qos 1 \
  --fault-types compressor_efficiency_loss,turbine_degradation,sensor_drift \
  --fault-rate 0.02 \
  --batch-mode false
```

## Run (Environment Variables)

```bash
export MQTT_HOST=localhost
export MQTT_PORT=1883
export MQTT_TOPIC=turbofan/telemetry
export SIM_ENGINES=8
export SIM_INTERVAL=0.5
export SIM_FAULT_TYPES=compressor_efficiency_loss,turbine_degradation,sensor_drift
python mqtt_publisher.py
```

## Local Simulator Config File

The Docker Compose simulator service reads its settings from:

- `simulator/simulator.env`

Edit that file to change values such as:

- `SIM_INTERVAL`
- `SIM_ENGINES`
- `SIM_FAULT_RATE`
- `SIM_BATCH_MODE`

After changing the file, recreate the simulator service:

```bash
docker compose -f docker-compose.local.yml up -d --force-recreate simulator
```

You can also use the same file for local runs from the repository root:

```bash
set -a
source simulator/simulator.env
set +a
python simulator/mqtt_publisher.py
```

## Important CLI/Env Controls

- `--engines` / `SIM_ENGINES`: number of engines (`1..1000`).
- `--interval` / `SIM_INTERVAL`: publish interval seconds.
- `--batch-mode` / `SIM_BATCH_MODE`: publish batch payloads.
- `--batch-size` / `SIM_BATCH_SIZE`: frames per batch message.
- `--prediction-compatible` / `SIM_PREDICTION_COMPATIBLE`: publish only the prediction subset in `features` while still deriving from full CMAPSS internally.
- `--full-cmapss` / `SIM_FULL_CMAPSS`: publish full `sensor_1..sensor_21` in `features` (default mode).
- `--fault-types` / `SIM_FAULT_TYPES`: comma-separated fault set.
- `--fault-rate` / `SIM_FAULT_RATE`: random fault activation rate.
- `--debug` / `SIM_DEBUG`: include hidden true RUL.
- `--spike-prob`, `--dropout-prob`, `--missing-prob`, `--comm-loss-prob`, `--out-of-range-prob`: anomaly controls.

## Docker

Build and run directly:

```bash
docker build -t turbofan-simulator .
docker run --rm -e MQTT_HOST=host.docker.internal -e MQTT_PORT=1883 turbofan-simulator
```

Or use bundled compose file:

```bash
docker compose up --build
```
