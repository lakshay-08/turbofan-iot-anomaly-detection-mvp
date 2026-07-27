from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import os

from sqlalchemy import JSON, Boolean, Column, DateTime, Double, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")
JSON_TYPE = JSON if "sqlite" in DATABASE_URL.lower() else JSONB


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id = Column(String(100), index=True)
    event_timestamp = Column(DateTime, index=True)
    anomaly_score = Column(Double)
    is_anomaly = Column(Boolean, index=True)
    model_name = Column(String(100))
    model_version = Column(String(50))
    payload_metadata = Column("metadata", JSON_TYPE)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    alerts = relationship("Alert", back_populates="prediction", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"))
    engine_id = Column(String(100), index=True)
    severity = Column(String(20))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    prediction = relationship("Prediction", back_populates="alerts")
