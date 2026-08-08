from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "isolation_forest"


@dataclass(slots=True)
class PredictionResult:
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    model_name: str
    feature_columns: list[str]
    metadata: dict[str, Any]


class PredictionService:
    def __init__(self, artifact_dir: Path | None = None) -> None:
        self.artifact_dir = artifact_dir or ARTIFACT_DIR
        self.model = joblib.load(self.artifact_dir / "model.joblib")
        self.scaler = joblib.load(self.artifact_dir / "scaler.joblib")
        self.metrics = json.loads((self.artifact_dir / "metrics.json").read_text(encoding="utf-8"))
        self.feature_columns = list(self.metrics.get("feature_columns", []))
        self.threshold = float(self.metrics.get("threshold", 0.0))

    def model_info(self) -> dict[str, Any]:
        return {
            "model_name": "IsolationForest",
            "feature_columns": self.feature_columns,
            "threshold": self.threshold,
            "metrics": self.metrics,
        }

    def _build_matrix(self, features: dict[str, Any]) -> np.ndarray:
        ordered = [[float(features[column]) for column in self.feature_columns]]
        return np.asarray(ordered, dtype=np.float64)

    def predict(self, payload: dict[str, Any]) -> PredictionResult:
        features = payload.get("features", {})
        matrix = self._build_matrix(features)
        scaled = self.scaler.transform(matrix)
        anomaly_score = float(-self.model.score_samples(scaled)[0])
        return PredictionResult(
            anomaly_score=anomaly_score,
            threshold=self.threshold,
            is_anomaly=anomaly_score >= self.threshold,
            model_name="IsolationForest",
            feature_columns=self.feature_columns,
            metadata={"threshold": self.threshold, "feature_columns": self.feature_columns},
        )
