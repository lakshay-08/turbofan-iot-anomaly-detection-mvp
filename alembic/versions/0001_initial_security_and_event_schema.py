"""initial security and event schema

Revision ID: 0001_initial_security_and_event_schema
Revises: 
Create Date: 2026-08-09 00:00:00.000000
"""

from __future__ import annotations

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_security_and_event_schema"
down_revision = None
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _table_exists(name: str) -> bool:
    inspector = sa.inspect(_bind())
    return inspector.has_table(name)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'operator', 'viewer')),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id UUID PRIMARY KEY,
            event_id UUID NOT NULL UNIQUE,
            engine_id VARCHAR(100),
            event_timestamp TIMESTAMP WITH TIME ZONE,
            anomaly_score DOUBLE PRECISION,
            is_anomaly BOOLEAN,
            model_name VARCHAR(100),
            model_version VARCHAR(50),
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id UUID PRIMARY KEY,
            event_id UUID NOT NULL UNIQUE,
            prediction_id UUID REFERENCES predictions(id),
            engine_id VARCHAR(100),
            severity VARCHAR(20),
            message TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS event_id UUID")
    op.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS event_timestamp TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS model_version VARCHAR(50)")
    op.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE predictions ADD COLUMN IF NOT EXISTS metadata JSONB")

    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS event_id UUID")
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE")

    bind = _bind()

    if _table_exists("predictions"):
        prediction_rows = bind.execute(sa.text("SELECT id FROM predictions WHERE event_id IS NULL")).fetchall()
        for row in prediction_rows:
            bind.execute(
                sa.text("UPDATE predictions SET event_id = :event_id WHERE id = :id"),
                {"id": row.id, "event_id": str(uuid4())},
            )

        bind.execute(sa.text("ALTER TABLE predictions ALTER COLUMN event_id SET NOT NULL"))
        bind.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_event_id ON predictions (event_id)"))
        bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_predictions_engine_created_at ON predictions (engine_id, created_at)"))

    if _table_exists("alerts"):
        bind.execute(
            sa.text(
                """
                UPDATE alerts
                SET event_id = predictions.event_id
                FROM predictions
                WHERE alerts.prediction_id = predictions.id AND alerts.event_id IS NULL
                """
            )
        )
        alert_rows = bind.execute(sa.text("SELECT id FROM alerts WHERE event_id IS NULL")).fetchall()
        for row in alert_rows:
            bind.execute(
                sa.text("UPDATE alerts SET event_id = :event_id WHERE id = :id"),
                {"id": row.id, "event_id": str(uuid4())},
            )

        bind.execute(sa.text("ALTER TABLE alerts ALTER COLUMN event_id SET NOT NULL"))
        bind.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_alerts_event_id ON alerts (event_id)"))
        bind.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_alerts_engine_created_at ON alerts (engine_id, created_at)"))


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alerts_engine_created_at")
    op.execute("DROP INDEX IF EXISTS uq_alerts_event_id")
    op.execute("DROP INDEX IF EXISTS ix_predictions_engine_created_at")
    op.execute("DROP INDEX IF EXISTS uq_predictions_event_id")
    op.execute("DROP TABLE IF EXISTS alerts")
    op.execute("DROP TABLE IF EXISTS predictions")
    op.execute("DROP TABLE IF EXISTS users")
