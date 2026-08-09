from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import os

from sqlalchemy import JSON, Boolean, CheckConstraint, Column, DateTime, Double, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from backend.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "")
JSON_TYPE = JSON if "sqlite" in DATABASE_URL.lower() else JSONB


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_predictions_event_id"),
        Index("ix_predictions_engine_created_at", "engine_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
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
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_alerts_event_id"),
        Index("ix_alerts_engine_created_at", "engine_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"))
    engine_id = Column(String(100), index=True)
    severity = Column(String(20))
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    prediction = relationship("Prediction", back_populates="alerts")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('admin', 'operator', 'viewer')", name="ck_users_role"),
        Index("ix_users_role", "role"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
