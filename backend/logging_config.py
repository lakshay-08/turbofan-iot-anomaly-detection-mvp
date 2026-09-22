from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_ROOT = Path(os.getenv("LOG_ROOT", str(PROJECT_ROOT / "logs")))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service_name", "backend"),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "correlation_id", None):
            payload["correlation_id"] = record.correlation_id
        if getattr(record, "event_id", None):
            payload["event_id"] = record.event_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def build_logger(name: str, service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return logger

    log_dir = LOG_ROOT / service_name.replace("-", "_")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{service_name}.log"

    handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=5)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    os.environ.setdefault("SERVICE_NAME", service_name)
    return build_logger(service_name, service_name, level)


def get_correlation_id() -> str:
    return str(uuid4())
