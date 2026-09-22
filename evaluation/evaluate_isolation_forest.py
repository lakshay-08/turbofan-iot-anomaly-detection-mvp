"""Evaluate the existing Isolation Forest baseline on the same FD003 split."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.common import (  # noqa: E402
    ARTIFACTS_DIR,
    DEFAULT_RANDOM_STATE,
    DEFAULT_THRESHOLD_PERCENTILE,
    DEFAULT_VALIDATION_FRACTION,
    FEATURE_COLUMNS,
    ensure_directory,
    extract_feature_frame,
    classification_metrics,
    inference_latency_ms,
    load_processed_frames,
    normal_samples,
    reconstruction_threshold,
    save_json,
    split_train_validation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the Isolation Forest baseline")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "processed" / "train")
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACTS_DIR / "isolation_forest")
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    parser.add_argument("--threshold-percentile", type=float, default=DEFAULT_THRESHOLD_PERCENTILE)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--contamination", type=float, default=0.01)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    artifact_dir = ensure_directory(args.artifact_dir)

    train_df, eval_df = load_processed_frames(args.data_dir)
    normal_train_df = normal_samples(train_df)
    feature_frame = extract_feature_frame(normal_train_df, FEATURE_COLUMNS)
    train_split_df, _ = split_train_validation(
        feature_frame,
        validation_fraction=args.validation_fraction,
        random_state=args.random_state,
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_split_df)
    X_eval = scaler.transform(extract_feature_frame(eval_df, FEATURE_COLUMNS))

    model = IsolationForest(
        n_estimators=args.n_estimators,
        contamination=args.contamination,
        random_state=args.random_state,
    )
    model.fit(X_train)

    train_scores = -model.score_samples(X_train)
    threshold = reconstruction_threshold(train_scores, percentile=args.threshold_percentile)

    inference_start = perf_counter()
    eval_scores = -model.score_samples(X_eval)
    inference_seconds = perf_counter() - inference_start

    y_true = eval_df["anomaly_label"].astype(int).to_numpy()
    metrics = classification_metrics(y_true, eval_scores, threshold)
    metrics.update(
        {
            "threshold": float(threshold),
            "threshold_percentile": float(args.threshold_percentile),
            "train_score_mean": float(np.mean(train_scores)),
            "train_score_std": float(np.std(train_scores)),
            "eval_score_mean": float(np.mean(eval_scores)),
            "eval_score_std": float(np.std(eval_scores)),
            "inference_seconds_total": float(inference_seconds),
            "inference_ms_per_sample": inference_latency_ms(inference_seconds, len(X_eval)),
            "n_train_normal": int(len(train_split_df)),
            "n_eval_samples": int(len(eval_df)),
            "feature_columns": FEATURE_COLUMNS,
            "n_estimators": int(args.n_estimators),
            "contamination": float(args.contamination),
        }
    )

    save_json(artifact_dir / "metrics.json", metrics)
    joblib.dump(model, artifact_dir / "model.joblib")
    joblib.dump(scaler, artifact_dir / "scaler.joblib")
    save_json(
        artifact_dir / "training_manifest.json",
        {
            "train_source": str(args.data_dir / "fd003_healthy_baseline.csv"),
            "feature_columns": FEATURE_COLUMNS,
            "validation_fraction": args.validation_fraction,
            "random_state": args.random_state,
        },
    )

    print(f"Saved Isolation Forest metrics to {artifact_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()