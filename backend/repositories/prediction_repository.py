from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.db_models import Alert, Prediction


class PredictionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_prediction(self, payload: dict[str, Any]) -> Prediction:
        prediction = Prediction(
            engine_id=str(payload.get("engine_id") or "unknown"),
            event_timestamp=payload.get("timestamp") or datetime.now(timezone.utc),
            anomaly_score=float(payload.get("anomaly_score", 0.0)),
            is_anomaly=bool(payload.get("is_anomaly", False)),
            model_name=str(payload.get("model_name", "unknown")),
            model_version=str(payload.get("model_version", "unknown")),
            payload_metadata=payload.get("metadata") or {},
        )
        self.session.add(prediction)
        self.session.commit()
        self.session.refresh(prediction)
        return prediction

    def add_alert(self, prediction: Prediction, severity: str, message: str) -> Alert:
        alert = Alert(
            prediction_id=prediction.id,
            engine_id=prediction.engine_id,
            severity=severity,
            message=message,
        )
        self.session.add(alert)
        self.session.commit()
        self.session.refresh(alert)
        return alert

    def recent_anomalies(self, limit: int = 50) -> list[Prediction]:
        return (
            self.session.execute(
                select(Prediction)
                .where(Prediction.is_anomaly.is_(True))
                .order_by(Prediction.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

    def engines(self) -> list[dict[str, Any]]:
        rows = self.session.execute(
            select(Prediction.engine_id, func.max(Prediction.created_at).label("last_seen"))
            .group_by(Prediction.engine_id)
            .order_by(func.max(Prediction.created_at).desc())
        ).all()
        return [{"engine_id": engine_id, "last_seen": last_seen} for engine_id, last_seen in rows]

    def engine_details(self, engine_id: str, hours: int = 24) -> list[Prediction]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.session.execute(
                select(Prediction)
                .where(Prediction.engine_id == engine_id)
                .where(Prediction.created_at >= cutoff)
                .order_by(Prediction.created_at.asc())
            )
            .scalars()
            .all()
        )

    def overview_metrics(self) -> dict[str, Any]:
        total_events = self.session.scalar(select(func.count(Prediction.id))) or 0
        anomalies = self.session.scalar(select(func.count(Prediction.id)).where(Prediction.is_anomaly.is_(True))) or 0
        engines = self.session.scalar(select(func.count(func.distinct(Prediction.engine_id)))) or 0
        models = self.session.execute(select(Prediction.model_name).distinct()).scalars().all()
        return {
            "total_events": int(total_events),
            "anomalies_detected": int(anomalies),
            "active_engines": int(engines),
            "models_running": len(models),
        }

    def alerts(self) -> list[Alert]:
        return self.session.execute(select(Alert).order_by(Alert.created_at.desc())).scalars().all()
