"""FastAPI backend for real-time anomaly inference and dashboard access."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

try:
    from backend.config import settings
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from config import settings

from backend.database import SessionLocal, init_db
from backend.logging_config import configure_logging
from backend.repositories.prediction_repository import PredictionRepository
from backend.services.prediction_service import PredictionService

LOGGER = configure_logging("backend")

EXAMPLE_FEATURES = {
    "sensor_11": 47.3,
    "sensor_4": 1396.84,
    "sensor_13": 2388.01,
    "sensor_8": 9062.17,
    "sensor_17": 391.0,
    "sensor_3": 1583.23,
    "sensor_2": 642.36,
    "sensor_9": 8145.32,
}


class TelemetryFrame(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "engine_id": 1,
                    "features": EXAMPLE_FEATURES,
                },
            ]
        }
    )

    engine_id: int | str | None = Field(default=None, description="Optional engine identifier")
    features: dict[str, float] = Field(description="Feature name to value mapping", examples=[EXAMPLE_FEATURES])


class PredictionResponse(BaseModel):
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    model_name: str
    feature_columns: list[str]


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.prediction_service = PredictionService()
    yield


app = FastAPI(
    title="Turbofan Anomaly Detection API",
    version="1.0.0",
    description="FastAPI inference service and dashboard API for the turbofan anomaly platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
    service: PredictionService = app.state.prediction_service
    return service.model_info()


def _persist_prediction(payload: TelemetryFrame, prediction_result: Any) -> None:
    session = SessionLocal()
    try:
        repository = PredictionRepository(session)
        repository.add_prediction(
            {
                "engine_id": payload.engine_id,
                "timestamp": datetime.now(timezone.utc),
                "anomaly_score": prediction_result.anomaly_score,
                "is_anomaly": prediction_result.is_anomaly,
                "model_name": prediction_result.model_name,
                "metadata": {
                    **(prediction_result.metadata or {}),
                    "request_engine_id": payload.engine_id,
                },
            }
        )
    finally:
        session.close()


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: TelemetryFrame) -> PredictionResponse:
    service: PredictionService = app.state.prediction_service
    prediction_result = service.predict(payload.model_dump())
    _persist_prediction(payload, prediction_result)
    return PredictionResponse(
        anomaly_score=prediction_result.anomaly_score,
        threshold=prediction_result.threshold,
        is_anomaly=prediction_result.is_anomaly,
        model_name=prediction_result.model_name,
        feature_columns=prediction_result.feature_columns,
    )


@app.post("/predict-batch", response_model=BatchPredictionResponse)
@app.post("/batch-predict", response_model=BatchPredictionResponse)
def predict_batch(payloads: list[TelemetryFrame]) -> BatchPredictionResponse:
    service: PredictionService = app.state.prediction_service
    predictions: list[PredictionResponse] = []
    for payload in payloads:
        prediction_result = service.predict(payload.model_dump())
        _persist_prediction(payload, prediction_result)
        predictions.append(
            PredictionResponse(
                anomaly_score=prediction_result.anomaly_score,
                threshold=prediction_result.threshold,
                is_anomaly=prediction_result.is_anomaly,
                model_name=prediction_result.model_name,
                feature_columns=prediction_result.feature_columns,
            )
        )
    return BatchPredictionResponse(predictions=predictions)


@app.get("/api/recent-anomalies")
def recent_anomalies(limit: int = 50) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        repository = PredictionRepository(session)
        records = repository.recent_anomalies(limit=limit)
        return [
            {
                "id": str(record.id),
                "engine_id": record.engine_id,
                "timestamp": record.event_timestamp.isoformat() if record.event_timestamp else None,
                "anomaly_score": record.anomaly_score,
                "is_anomaly": record.is_anomaly,
                "model_name": record.model_name,
                "model_version": record.model_version,
                "metadata": record.payload_metadata or {},
            }
            for record in records
        ]
    finally:
        session.close()


@app.get("/api/engines")
def engines() -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        return PredictionRepository(session).engines()
    finally:
        session.close()


@app.get("/api/engine/{engine_id}")
def engine_details(engine_id: str) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        records = PredictionRepository(session).engine_details(engine_id)
        return [
            {
                "engine_id": record.engine_id,
                "timestamp": record.event_timestamp.isoformat() if record.event_timestamp else None,
                "anomaly_score": record.anomaly_score,
                "is_anomaly": record.is_anomaly,
                "model_name": record.model_name,
                "metadata": record.payload_metadata or {},
            }
            for record in records
        ]
    finally:
        session.close()


@app.get("/api/metrics/overview")
def metrics_overview() -> dict[str, Any]:
    session = SessionLocal()
    try:
        return PredictionRepository(session).overview_metrics()
    finally:
        session.close()


@app.get("/api/metrics/trends")
def metrics_trends() -> dict[str, Any]:
    return {"trend": "stable"}


@app.get("/api/alerts")
def alerts() -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        rows = PredictionRepository(session).alerts()
        return [
            {
                "id": str(alert.id),
                "engine_id": alert.engine_id,
                "severity": alert.severity,
                "message": alert.message,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }
            for alert in rows
        ]
    finally:
        session.close()


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port, reload=False)

