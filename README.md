# Turbofan IoT Anomaly Detection MVP

This repository now provides an end-to-end predictive maintenance platform built around the existing FastAPI inference API and the new persistence, dashboard, and optional streaming pieces.

## Architecture

The platform keeps the original inference flow intact:

- Client → FastAPI → Loaded model → Prediction response

The platform layers on production controls without changing the primary inference contract:

- JWT-authenticated dashboard and prediction APIs
- PostgreSQL persistence for predictions, alerts, and users
- Alembic-managed schema migrations
- Event IDs for idempotency and traceability
- Retry and dead-letter handling for Kafka and database writes
- React monitoring UI for operations teams
- Optional Kafka-based inference and dataset replay helpers
- Structured rotating logs under the logs directory

## Core workflow

1. The FastAPI service receives telemetry and returns an anomaly score.
2. Each request and replayed event carries an immutable event ID.
3. Predictions and alerts are stored in PostgreSQL with unique event-id constraints.
4. High-severity results can be written to the alerts table.
5. The dashboard signs in with JWT and consumes protected API endpoints.
6. Optional Kafka consumers process telemetry, retry transient failures, and send poisoned messages to the dead-letter topic.

## Backend services

- FastAPI app: backend/app.py
- Shared prediction service: backend/services/prediction_service.py
- PostgreSQL models: backend/models/db_models.py
- Repository layer: backend/repositories/prediction_repository.py
- Kafka inference consumer: backend/services/inference_service.py
- Prediction writer service: backend/services/prediction_writer_service.py
- Dataset replay utility: backend/services/dataset_replay.py

## Database schema

The platform now uses three tables:

- users
  - id UUID
  - email unique
  - password_hash
  - role
  - is_active
  - created_at

- predictions
  - id UUID
  - event_id unique
  - engine_id
  - event_timestamp
  - anomaly_score
  - is_anomaly
  - model_name
  - model_version
  - metadata JSONB
  - created_at

- alerts
  - id UUID
  - event_id unique
  - prediction_id
  - engine_id
  - severity
  - message
  - created_at

## Dashboard API

The FastAPI service now protects dashboard and prediction routes with JWT authentication:

- POST /auth/login
- GET /auth/me
- POST /auth/users
- GET /api/recent-anomalies
- GET /api/engines
- GET /api/engine/{engine_id}
- GET /api/alerts
- GET /api/metrics/overview
- GET /model-info
- POST /predict
- POST /batch-predict

Use the dashboard login form with the bootstrap admin credentials configured in Docker Compose:

- Email: admin@turbofan.local
- Password: admin123!

Existing health and metrics endpoints remain available:

- GET /health
- GET /metrics

## Kafka integration

Kafka is optional and does not replace the existing API inference path.

- Raw telemetry can be replayed into the Kafka topic configured by RAW_TELEMETRY_TOPIC.
- The inference consumer uses the shared prediction service and publishes prediction results to the prediction results topic.
- The prediction writer service persists those results into PostgreSQL.
- Transient Kafka and database failures are retried with exponential backoff and jitter.
- Exhausted messages are routed to the dead-letter topic.

## Dataset replay

Use the replay utility to publish existing processed CSV datasets into the API or Kafka.

The API mode accepts a bearer token through `API_BEARER_TOKEN` or `AUTH_TOKEN` if you want to post directly to the protected `/predict` endpoint.

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

1. Start the full stack with Docker Compose: docker compose -f docker-compose.local.yml up --build
2. The migration job runs Alembic upgrade head before the API and writer services start.
3. If you run the backend manually, install dependencies with `pip install -r backend/requirements.txt` and run `alembic upgrade head` first.
4. Start the API manually with `uvicorn backend.app:app --host 0.0.0.0 --port 8000`.
5. Start the React dashboard with `cd dasboard && npm install && npm start`.

## Notes

The inference API remains the primary prediction path. The additional persistence and streaming components are additive and backward-compatible.
