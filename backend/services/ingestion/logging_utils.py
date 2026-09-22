from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("event_id", "source", "engine_id", "file", "topic", "records", "error"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    formatter = JsonFormatter()
    handlers: list[logging.Handler] = []

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    handlers.append(stream_handler)

    log_root = os.getenv("LOG_ROOT")
    if log_root:
        service_name = os.getenv("SERVICE_NAME", "ingest-service")
        log_dir = Path(log_root) / service_name.replace("-", "_")
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(log_dir / f"{service_name}.log", maxBytes=5_000_000, backupCount=5)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root.handlers = handlers
