"""FastAPI backend for real-time anomaly inference and dashboard access."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from collections import Counter

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

try:
    from backend.config import settings
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
    from config import settings

from backend.database import SessionLocal
from backend.dependencies import get_current_user, require_roles
from backend.logging_config import configure_logging
from backend.repositories.prediction_repository import PredictionRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth import AccessTokenResponse, LoginRequest, UserCreateRequest, UserRead
from backend.security.auth import create_access_token, hash_password, verify_password
from backend.services.bootstrap import bootstrap_admin_user
from backend.services.prediction_service import PredictionService

LOGGER = configure_logging("backend")
METRICS = Counter()

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
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "event_id": "b9da6ad2-9d83-4f4d-9a0d-3f49ec2a9d6b",
                    "engine_id": 1,
                    "features": EXAMPLE_FEATURES,
                },
            ]
        }
    )

    event_id: UUID = Field(default_factory=uuid4, description="Immutable event identifier")
    engine_id: int | str | None = Field(default=None, description="Optional engine identifier")
    timestamp: datetime | None = Field(default=None, description="Optional event timestamp")
    source: str | None = Field(default=None, description="Event source")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Free-form event metadata")
    features: dict[str, float] = Field(description="Feature name to value mapping", examples=[EXAMPLE_FEATURES])


class PredictionResponse(BaseModel):
    event_id: UUID
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    model_name: str
    feature_columns: list[str]


class BatchPredictionResponse(BaseModel):
    predictions: list[PredictionResponse]


@asynccontextmanager
async def lifespan(app: FastAPI):
    session = SessionLocal()
    try:
        bootstrap_admin_user(
            session,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            role=settings.bootstrap_admin_role,
        )
    finally:
        session.close()
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
    METRICS["health_checks_total"] += 1
    return {"status": "ok"}


@app.post("/auth/login", response_model=AccessTokenResponse)
def login(payload: LoginRequest) -> AccessTokenResponse:
    session = SessionLocal()
    try:
        repository = UserRepository(session)
        user = repository.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_access_token(
            subject=str(user.id),
            email=user.email,
            role=user.role,
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            expires_minutes=settings.access_token_expire_minutes,
        )
        return AccessTokenResponse(
            access_token=token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserRead(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )
    finally:
        session.close()


@app.get("/auth/me", response_model=UserRead)
def me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    return current_user


@app.post("/auth/users", response_model=UserRead, dependencies=[Depends(require_roles("admin"))])
def create_user(payload: UserCreateRequest) -> UserRead:
    session = SessionLocal()
    try:
        repository = UserRepository(session)
        existing = repository.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

        user = repository.create_user(
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            is_active=True,
        )
        return UserRead(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )
    finally:
        session.close()


@app.get("/model-info", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def model_info() -> dict[str, Any]:
    service: PredictionService = app.state.prediction_service
    return service.model_info()


def _persist_prediction(payload: TelemetryFrame, prediction_result: Any, current_user: UserRead | None = None) -> None:
    session = SessionLocal()
    try:
        repository = PredictionRepository(session)
        repository.add_prediction(
            {
                "event_id": str(payload.event_id),
                "engine_id": payload.engine_id,
                "timestamp": payload.timestamp or datetime.now(timezone.utc),
                "anomaly_score": prediction_result.anomaly_score,
                "is_anomaly": prediction_result.is_anomaly,
                "model_name": prediction_result.model_name,
                "metadata": {
                    **(prediction_result.metadata or {}),
                    **payload.metadata,
                    "request_event_id": str(payload.event_id),
                    "request_engine_id": payload.engine_id,
                    "requested_by_user_id": str(current_user.id) if current_user else None,
                    "requested_by_role": current_user.role if current_user else None,
                },
            }
        )
    finally:
        session.close()


def _render_metrics() -> str:
    session = SessionLocal()
    try:
        overview = PredictionRepository(session).overview_metrics()
    finally:
        session.close()

    lines = [
        "# HELP turbofan_health_checks_total Total health checks served.",
        "# TYPE turbofan_health_checks_total counter",
        f"turbofan_health_checks_total {METRICS['health_checks_total']}",
        "# HELP turbofan_prediction_requests_total Total prediction requests served.",
        "# TYPE turbofan_prediction_requests_total counter",
        f"turbofan_prediction_requests_total {METRICS['prediction_requests_total']}",
        "# HELP turbofan_recent_events_total Total events currently stored in the dashboard database.",
        "# TYPE turbofan_recent_events_total gauge",
        f"turbofan_recent_events_total {overview['total_events']}",
        "# HELP turbofan_recent_anomalies_total Total anomalies currently stored in the dashboard database.",
        "# TYPE turbofan_recent_anomalies_total gauge",
        f"turbofan_recent_anomalies_total {overview['anomalies_detected']}",
        "# HELP turbofan_active_engines Total active engines currently stored in the dashboard database.",
        "# TYPE turbofan_active_engines gauge",
        f"turbofan_active_engines {overview['active_engines']}",
        "# HELP turbofan_models_running Number of models reported by the dashboard backend.",
        "# TYPE turbofan_models_running gauge",
        f"turbofan_models_running {overview['models_running']}",
    ]
    return "\n".join(lines) + "\n"


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: TelemetryFrame, current_user: UserRead = Depends(require_roles("operator", "admin"))) -> PredictionResponse:
    METRICS["prediction_requests_total"] += 1
    service: PredictionService = app.state.prediction_service
    prediction_result = service.predict(payload.model_dump())
    _persist_prediction(payload, prediction_result, current_user)
    return PredictionResponse(
        event_id=payload.event_id,
        anomaly_score=prediction_result.anomaly_score,
        threshold=prediction_result.threshold,
        is_anomaly=prediction_result.is_anomaly,
        model_name=prediction_result.model_name,
        feature_columns=prediction_result.feature_columns,
    )


@app.post("/predict-batch", response_model=BatchPredictionResponse)
@app.post("/batch-predict", response_model=BatchPredictionResponse)
def predict_batch(payloads: list[TelemetryFrame], current_user: UserRead = Depends(require_roles("operator", "admin"))) -> BatchPredictionResponse:
    METRICS["prediction_requests_total"] += len(payloads)
    service: PredictionService = app.state.prediction_service
    predictions: list[PredictionResponse] = []
    for payload in payloads:
        prediction_result = service.predict(payload.model_dump())
        _persist_prediction(payload, prediction_result, current_user)
        predictions.append(
            PredictionResponse(
                event_id=payload.event_id,
                anomaly_score=prediction_result.anomaly_score,
                threshold=prediction_result.threshold,
                is_anomaly=prediction_result.is_anomaly,
                model_name=prediction_result.model_name,
                feature_columns=prediction_result.feature_columns,
            )
        )
    return BatchPredictionResponse(predictions=predictions)


@app.get("/api/recent-anomalies", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def recent_anomalies(limit: int = 50) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        repository = PredictionRepository(session)
        records = repository.recent_anomalies(limit=limit)
        return [
            {
                "id": str(record.id),
                "event_id": str(record.event_id),
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


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return _render_metrics()


@app.get("/api/engines", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def engines() -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        return PredictionRepository(session).engines()
    finally:
        session.close()


@app.get("/api/engine/{engine_id}", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def engine_details(engine_id: str) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        records = PredictionRepository(session).engine_details(engine_id)
        return [
            {
                "engine_id": record.engine_id,
                "event_id": str(record.event_id),
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


@app.get("/api/metrics/overview", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def metrics_overview() -> dict[str, Any]:
    session = SessionLocal()
    try:
        return PredictionRepository(session).overview_metrics()
    finally:
        session.close()


@app.get("/api/metrics/trends", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def metrics_trends() -> dict[str, Any]:
    return {"trend": "stable"}


@app.get("/api/alerts", dependencies=[Depends(require_roles("viewer", "operator", "admin"))])
def alerts() -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        rows = PredictionRepository(session).alerts()
        return [
            {
                "id": str(alert.id),
                "event_id": str(alert.event_id),
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

