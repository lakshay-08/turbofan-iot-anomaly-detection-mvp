"""FastAPI backend for serving the trained Isolation Forest model."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
import uvicorn

try:
	from backend.config import settings
except ModuleNotFoundError:  # pragma: no cover - direct script execution path
	from config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "artifacts" / "isolation_forest"

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
	features: dict[str, float] = Field(
		description="Feature name to value mapping",
		examples=[EXAMPLE_FEATURES],
	)


class PredictionResponse(BaseModel):
	anomaly_score: float
	threshold: float
	is_anomaly: bool
	model_name: str
	feature_columns: list[str]


class BatchPredictionResponse(BaseModel):
	predictions: list[PredictionResponse]


@dataclass(slots=True)
class ModelBundle:
	model: Any
	scaler: Any
	feature_columns: list[str]
	threshold: float
	metrics: dict[str, Any]


def load_feature_columns() -> list[str]:
	feature_file = ARTIFACT_DIR / "feature_columns.joblib"
	if feature_file.exists():
		return list(joblib.load(feature_file))
	metrics_file = ARTIFACT_DIR / "metrics.json"
	if metrics_file.exists():
		metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
		return list(metrics.get("feature_columns", []))
	raise FileNotFoundError("Feature columns artifact is missing")


def load_model_bundle() -> ModelBundle:
	model_path = ARTIFACT_DIR / "model.joblib"
	scaler_path = ARTIFACT_DIR / "scaler.joblib"
	metrics_path = ARTIFACT_DIR / "metrics.json"

	if not model_path.exists():
		raise FileNotFoundError(f"Missing trained model artifact: {model_path}")
	if not scaler_path.exists():
		raise FileNotFoundError(f"Missing scaler artifact: {scaler_path}")
	if not metrics_path.exists():
		raise FileNotFoundError(f"Missing metrics artifact: {metrics_path}")

	model = joblib.load(model_path)
	scaler = joblib.load(scaler_path)
	metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
	feature_columns = load_feature_columns()
	threshold = float(metrics["threshold"])
	return ModelBundle(
		model=model,
		scaler=scaler,
		feature_columns=feature_columns,
		threshold=threshold,
		metrics=metrics,
	)


def build_feature_matrix(features: dict[str, float], feature_columns: list[str]) -> np.ndarray:
	missing = [column for column in feature_columns if column not in features]
	if missing:
		raise HTTPException(
			status_code=422,
			detail=f"Missing required features: {missing}",
		)
	ordered_values = [[float(features[column]) for column in feature_columns]]
	return np.asarray(ordered_values, dtype=np.float64)


@asynccontextmanager
async def lifespan(app: FastAPI):
	app.state.bundle = load_model_bundle()
	yield


app = FastAPI(
	title="Turbofan Anomaly Detection API",
	version="1.0.0",
	description="FastAPI inference service for the exported Isolation Forest model.",
	lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


@app.get("/model-info")
def model_info() -> dict[str, Any]:
	bundle: ModelBundle = app.state.bundle
	return {
		"model_name": "IsolationForest",
		"feature_columns": bundle.feature_columns,
		"threshold": bundle.threshold,
		"metrics": bundle.metrics,
	}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: TelemetryFrame) -> PredictionResponse:
	bundle: ModelBundle = app.state.bundle
	matrix = build_feature_matrix(payload.features, bundle.feature_columns)
	scaled = bundle.scaler.transform(matrix)
	anomaly_score = float(-bundle.model.score_samples(scaled)[0])
	return PredictionResponse(
		anomaly_score=anomaly_score,
		threshold=bundle.threshold,
		is_anomaly=anomaly_score >= bundle.threshold,
		model_name="IsolationForest",
		feature_columns=bundle.feature_columns,
	)


@app.post("/predict-batch", response_model=BatchPredictionResponse)
def predict_batch(payloads: list[TelemetryFrame]) -> BatchPredictionResponse:
	bundle: ModelBundle = app.state.bundle
	predictions: list[PredictionResponse] = []
	for payload in payloads:
		matrix = build_feature_matrix(payload.features, bundle.feature_columns)
		scaled = bundle.scaler.transform(matrix)
		anomaly_score = float(-bundle.model.score_samples(scaled)[0])
		predictions.append(
			PredictionResponse(
				anomaly_score=anomaly_score,
				threshold=bundle.threshold,
				is_anomaly=anomaly_score >= bundle.threshold,
				model_name="IsolationForest",
				feature_columns=bundle.feature_columns,
			)
		)
	return BatchPredictionResponse(predictions=predictions)


if __name__ == "__main__":
	uvicorn.run(
		app,
		host=settings.api_host,
		port=settings.api_port,
		reload=False,
	)

