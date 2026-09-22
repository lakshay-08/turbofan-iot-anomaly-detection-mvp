"""Shared utilities for anomaly-detection training and evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "train"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

TRAIN_FILE = "fd003_healthy_baseline.csv"
EVAL_FILE = "fd003_with_rul.csv"
LABEL_COLUMN = "anomaly_label"
DEFAULT_RANDOM_STATE = 42
DEFAULT_VALIDATION_FRACTION = 0.15
DEFAULT_THRESHOLD_PERCENTILE = 95.0

FEATURE_COLUMNS: list[str] = [
    "sensor_11",
    "sensor_4",
    "sensor_13",
    "sensor_8",
    "sensor_17",
    "sensor_3",
    "sensor_2",
    "sensor_9",
]


def ensure_directory(path: Path | str) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_json(path: Path | str, payload: dict[str, object]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_json(path: Path | str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_processed_frames(data_dir: Path | str = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_dir = Path(data_dir)
    train_df = pd.read_csv(base_dir / TRAIN_FILE)
    eval_df = pd.read_csv(base_dir / EVAL_FILE)
    return train_df, eval_df


def validate_feature_columns(df: pd.DataFrame, feature_columns: Sequence[str]) -> None:
    missing = [column for column in feature_columns if column not in df.columns]
    if missing:
        raise KeyError(f"Missing required feature columns: {missing}")


def extract_feature_frame(df: pd.DataFrame, feature_columns: Sequence[str] = FEATURE_COLUMNS) -> pd.DataFrame:
    validate_feature_columns(df, feature_columns)
    return df.loc[:, list(feature_columns)].copy()


def normal_samples(df: pd.DataFrame) -> pd.DataFrame:
    if LABEL_COLUMN not in df.columns:
        raise KeyError(f"Expected '{LABEL_COLUMN}' column in dataframe")
    return df.loc[df[LABEL_COLUMN].astype(int) == 0].copy()


def split_train_validation(
    df: pd.DataFrame,
    validation_fraction: float = DEFAULT_VALIDATION_FRACTION,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction must be between 0 and 1")
    train_df, validation_df = train_test_split(
        df,
        test_size=validation_fraction,
        random_state=random_state,
        shuffle=True,
    )
    return train_df.reset_index(drop=True), validation_df.reset_index(drop=True)


def reconstruction_threshold(errors: np.ndarray, percentile: float = DEFAULT_THRESHOLD_PERCENTILE) -> float:
    if errors.size == 0:
        raise ValueError("Cannot compute a threshold from an empty error array")
    return float(np.percentile(errors, percentile))


def binary_predictions(errors: np.ndarray, threshold: float) -> np.ndarray:
    return (errors >= threshold).astype(int)


def classification_metrics(y_true: np.ndarray, y_score: np.ndarray, threshold: float) -> dict[str, object]:
    y_true_int = np.asarray(y_true, dtype=int)
    y_score_float = np.asarray(y_score, dtype=float)
    y_pred = binary_predictions(y_score_float, threshold)

    metrics: dict[str, object] = {
        "roc_auc": float(roc_auc_score(y_true_int, y_score_float)),
        "precision": float(precision_score(y_true_int, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true_int, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true_int, y_pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true_int, y_score_float)),
        "accuracy": float(accuracy_score(y_true_int, y_pred)),
        "confusion_matrix": confusion_matrix(y_true_int, y_pred).tolist(),
    }
    return metrics


def inference_latency_ms(total_seconds: float, sample_count: int) -> float:
    if sample_count <= 0:
        return 0.0
    return float((total_seconds / sample_count) * 1000.0)


def format_seconds(total_seconds: float) -> str:
    if total_seconds < 1:
        return f"{total_seconds * 1000.0:.2f} ms"
    return f"{total_seconds:.2f} s"


def load_history(path: Path | str) -> dict[str, list[float]]:
    payload = load_json(path)
    return {key: [float(value) for value in values] for key, values in payload.items()}
