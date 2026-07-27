from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts"


class ModelRegistryError(RuntimeError):
    pass


class BaseModelHandler:
    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class IsolationForestHandler(BaseModelHandler):
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir
        self.model = joblib.load(artifact_dir / "model.joblib")
        self.scaler = joblib.load(artifact_dir / "scaler.joblib")
        self.metrics = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
        self.feature_columns = list(self.metrics.get("feature_columns", []))

    def _build_matrix(self, features: dict[str, Any]) -> np.ndarray:
        ordered = [[float(features[column]) for column in self.feature_columns]]
        return np.asarray(ordered, dtype=np.float64)

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        features = payload.get("features", {})
        matrix = self._build_matrix(features)
        scaled = self.scaler.transform(matrix)
        anomaly_score = float(-self.model.score_samples(scaled)[0])
        threshold = float(self.metrics.get("threshold", 0.0))
        return {
            "anomaly_score": anomaly_score,
            "is_anomaly": anomaly_score >= threshold,
            "model_name": "isolation_forest",
            "model_version": self.metrics.get("model_version", "1.0"),
            "metadata": {"threshold": threshold, "feature_columns": self.feature_columns},
        }


class AutoencoderHandler(BaseModelHandler):
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir
        self.scaler = joblib.load(artifact_dir / "scaler.joblib")
        self.metrics = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
        self.feature_columns = list(self.metrics.get("feature_columns", []))
        self._load_model()

    def _load_model(self) -> None:
        from models.autoencoder import DenseAutoencoder

        self.model = DenseAutoencoder.load(self.artifact_dir / "model.keras")

    def _build_matrix(self, features: dict[str, Any]) -> np.ndarray:
        ordered = [[float(features[column]) for column in self.feature_columns]]
        return np.asarray(ordered, dtype=np.float64)

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        features = payload.get("features", {})
        matrix = self._build_matrix(features)
        scaled = self.scaler.transform(matrix)
        reconstruction = self.model.reconstruct(scaled)[0]
        error = float(np.mean(np.abs(reconstruction - scaled)))
        threshold = float(self.metrics.get("threshold", 0.0))
        return {
            "anomaly_score": error,
            "is_anomaly": error >= threshold,
            "model_name": "autoencoder",
            "model_version": self.metrics.get("model_version", "1.0"),
            "metadata": {"threshold": threshold, "feature_columns": self.feature_columns},
        }


class ModelRegistry:
    def __init__(self, artifact_root: Path | None = None) -> None:
        self.artifact_root = artifact_root or ARTIFACT_ROOT
        self._handlers: dict[str, BaseModelHandler] = {}

    def get_handler(self, model_name: str | None = None) -> BaseModelHandler:
        name = (model_name or os.getenv("MODEL_TYPE", "isolation_forest")).strip().lower()
        if name in self._handlers:
            return self._handlers[name]

        artifact_dir = self.artifact_root / name
        if not artifact_dir.exists():
            raise ModelRegistryError(f"Model artifacts not found for {name}")

        if name == "autoencoder":
            handler = AutoencoderHandler(artifact_dir)
        elif name == "isolation_forest":
            handler = IsolationForestHandler(artifact_dir)
        else:
            raise ModelRegistryError(f"Unsupported model {name}")

        self._handlers[name] = handler
        return handler
