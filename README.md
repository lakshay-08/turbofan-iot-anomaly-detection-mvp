# Turbofan IoT Anomaly Detection MVP

This repository now provides an end-to-end predictive maintenance platform built around the existing FastAPI inference API and the new persistence, dashboard, and optional streaming pieces.

## Architecture

The platform keeps the original inference flow intact:

- Client → FastAPI → Loaded model → Prediction response

The missing platform features are layered on top without changing the primary inference contract:

- PostgreSQL persistence for predictions and alerts
- Dashboard API endpoints for recent anomalies, engine activity, alerts, and overview metrics
- React monitoring UI for operations teams
- Optional Kafka-based inference and dataset replay helpers
- Structured rotating logs under the logs directory

## Core workflow

1. The FastAPI service receives telemetry and returns an anomaly score.
2. Each prediction is stored in PostgreSQL through the shared persistence layer.
3. High-severity results can be written to the alerts table.
4. The dashboard consumes the PostgreSQL-backed API endpoints.
5. Optional Kafka consumers can process telemetry from Kafka and publish results to the same persistence path.

## Backend services

- FastAPI app: backend/app.py
- Shared prediction service: backend/services/prediction_service.py
- PostgreSQL models: backend/models/db_models.py
- Repository layer: backend/repositories/prediction_repository.py
- Kafka inference consumer: backend/services/inference_service.py
- Prediction writer service: backend/services/prediction_writer_service.py
- Dataset replay utility: backend/services/dataset_replay.py

## Database schema

The platform uses two tables:

- predictions
  - id UUID
  - engine_id
  - timestamp
  - anomaly_score
  - is_anomaly
  - model_name
  - metadata JSONB
  - created_at

- alerts
  - id UUID
  - prediction_id
  - engine_id
  - severity
  - message
  - created_at

## Dashboard API

The FastAPI service exposes the following endpoints:

- GET /api/recent-anomalies
- GET /api/engines
- GET /api/engine/{engine_id}
- GET /api/alerts
- GET /api/metrics/overview

Existing inference endpoints remain available:

- GET /health
- POST /predict
- POST /batch-predict
- GET /model-info

## Kafka integration

Kafka is optional and does not replace the existing API inference path.

- Raw telemetry can be replayed into the Kafka topic configured by RAW_TELEMETRY_TOPIC.
- The inference consumer uses the shared prediction service and publishes prediction results to the prediction results topic.
- The prediction writer service persists those results into PostgreSQL.

## Dataset replay

Use the replay utility to publish existing processed CSV datasets into the API or Kafka.

Example:

- python -m backend.services.dataset_replay --source-dir data/processed --mode api
- python -m backend.services.dataset_replay --source-dir data/processed --mode kafka

## Logging

Structured rotating logs are written under:

- logs/backend/
- logs/ingestion/
- logs/inference/

To mirror Docker container stdout and stderr for all compose services into the repository as well, run:

- `bash scripts/collect_docker_logs.sh`

This writes combined container logs under:

- logs/docker/

Note: direct bind-mounting of the repository `logs/` directory from Docker may require enabling this workspace path in Docker Desktop file sharing on macOS.

## Startup

1. Start PostgreSQL and Kafka (or use the provided Docker Compose configuration).
2. Install backend dependencies: pip install -r backend/requirements.txt
3. Start the API: uvicorn backend.app:app --host 0.0.0.0 --port 8000
4. Start the React dashboard: cd dasboard && npm install && npm start

## Notes

The inference API remains the primary prediction path. The additional persistence and streaming components are additive and backward-compatible.
