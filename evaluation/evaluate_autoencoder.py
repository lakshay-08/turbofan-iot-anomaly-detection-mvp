"""Evaluate the trained dense autoencoder and generate plots and metrics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_curve
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.common import (  # noqa: E402
    ARTIFACTS_DIR,
    DEFAULT_THRESHOLD_PERCENTILE,
    DEFAULT_VALIDATION_FRACTION,
    FEATURE_COLUMNS,
    FIGURES_DIR,
    ensure_directory,
    extract_feature_frame,
    classification_metrics,
    inference_latency_ms,
    load_history,
    load_json,
    load_processed_frames,
    normal_samples,
    reconstruction_threshold,
    save_json,
    split_train_validation,
)
from models.autoencoder import AutoencoderConfig, DenseAutoencoder  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate the autoencoder on the FD003 evaluation split")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "processed" / "train")
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACTS_DIR / "autoencoder")
    parser.add_argument("--figure-dir", type=Path, default=FIGURES_DIR)
    parser.add_argument("--threshold-percentile", type=float, default=DEFAULT_THRESHOLD_PERCENTILE)
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--random-state", type=int, default=42)
    return parser


def load_autoencoder(artifact_dir: Path) -> tuple[DenseAutoencoder, StandardScaler, dict[str, object]]:
    config_payload = load_json(artifact_dir / "config.json")
    config = AutoencoderConfig.from_dict(config_payload)
    autoencoder = DenseAutoencoder.load(artifact_dir / "model.keras")
    autoencoder.config = config
    scaler = joblib.load(artifact_dir / "scaler.joblib")
    return autoencoder, scaler, config_payload


def plot_roc_curve(y_true: np.ndarray, y_score: np.ndarray, target_path: Path) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, label="Autoencoder", linewidth=2)
    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target_path, dpi=160)
    plt.close()


def plot_pr_curve(y_true: np.ndarray, y_score: np.ndarray, target_path: Path) -> None:
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    pr_auc = average_precision_score(y_true, y_score)
    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, label=f"PR-AUC = {pr_auc:.4f}", linewidth=2)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target_path, dpi=160)
    plt.close()


def plot_confusion_matrix(confusion_matrix_values: list[list[int]], target_path: Path) -> None:
    matrix = np.asarray(confusion_matrix_values)
    plt.figure(figsize=(6, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig(target_path, dpi=160)
    plt.close()


def plot_error_distribution(train_errors: np.ndarray, eval_errors: np.ndarray, threshold: float, target_path: Path) -> None:
    plt.figure(figsize=(10, 6))
    sns.histplot(train_errors, bins=60, color="#1f77b4", stat="density", label="Train normal", kde=True, alpha=0.35)
    sns.histplot(eval_errors, bins=60, color="#d62728", stat="density", label="Evaluation", kde=True, alpha=0.30)
    plt.axvline(threshold, color="black", linestyle="--", linewidth=1.5, label=f"Threshold = {threshold:.6f}")
    plt.xlabel("Reconstruction Error")
    plt.ylabel("Density")
    plt.title("Reconstruction Error Distribution")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target_path, dpi=160)
    plt.close()


def plot_training_history(history_payload: dict[str, list[float]], target_dir: Path) -> None:
    loss = history_payload.get("loss", [])
    val_loss = history_payload.get("val_loss", [])
    epochs = range(1, max(len(loss), len(val_loss)) + 1)

    plt.figure(figsize=(8, 6))
    plt.plot(list(epochs)[: len(loss)], loss, label="Training Loss", linewidth=2)
    if val_loss:
        plt.plot(list(epochs)[: len(val_loss)], val_loss, label="Validation Loss", linewidth=2)
    plt.xlabel("Epoch")
    plt.ylabel("MSE Loss")
    plt.title("Training Loss Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target_dir / "training_loss_curve.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 6))
    if val_loss:
        plt.plot(list(epochs)[: len(val_loss)], val_loss, label="Validation Loss", linewidth=2, color="#d62728")
    else:
        plt.plot(list(epochs)[: len(loss)], loss, label="Training Loss", linewidth=2, color="#1f77b4")
    plt.xlabel("Epoch")
    plt.ylabel("MSE Loss")
    plt.title("Validation Loss Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target_dir / "validation_loss_curve.png", dpi=160)
    plt.close()


def main() -> None:
    args = build_parser().parse_args()
    artifact_dir = ensure_directory(args.artifact_dir)
    figure_dir = ensure_directory(args.figure_dir)

    autoencoder, scaler, config_payload = load_autoencoder(artifact_dir)
    train_df, eval_df = load_processed_frames(args.data_dir)
    normal_train_df = normal_samples(train_df)
    feature_frame = extract_feature_frame(normal_train_df, FEATURE_COLUMNS)
    train_split_df, _ = split_train_validation(
        feature_frame,
        validation_fraction=float(config_payload.get("validation_fraction", args.validation_fraction)),
        random_state=int(config_payload.get("random_state", args.random_state)),
    )

    X_train = scaler.transform(train_split_df)
    X_eval = scaler.transform(extract_feature_frame(eval_df, FEATURE_COLUMNS))

    train_errors = autoencoder.reconstruction_error(X_train, verbose=0)
    threshold = reconstruction_threshold(
        train_errors,
        percentile=float(config_payload.get("threshold_percentile", args.threshold_percentile)),
    )

    inference_start = perf_counter()
    eval_reconstructions = autoencoder.reconstruct(X_eval, verbose=0)
    inference_seconds = perf_counter() - inference_start
    eval_errors = np.mean(np.square(X_eval - eval_reconstructions), axis=1)

    y_true = eval_df["anomaly_label"].astype(int).to_numpy()
    metrics = classification_metrics(y_true, eval_errors, threshold)
    metrics.update(
        {
            "threshold": float(threshold),
            "threshold_percentile": float(config_payload.get("threshold_percentile", args.threshold_percentile)),
            "train_reconstruction_error_mean": float(np.mean(train_errors)),
            "train_reconstruction_error_std": float(np.std(train_errors)),
            "eval_reconstruction_error_mean": float(np.mean(eval_errors)),
            "eval_reconstruction_error_std": float(np.std(eval_errors)),
            "inference_seconds_total": float(inference_seconds),
            "inference_ms_per_sample": inference_latency_ms(inference_seconds, len(X_eval)),
            "n_train_normal": int(len(train_split_df)),
            "n_eval_samples": int(len(eval_df)),
            "feature_columns": FEATURE_COLUMNS,
        }
    )

    save_json(artifact_dir / "metrics.json", metrics)

    plot_roc_curve(y_true, eval_errors, figure_dir / "autoencoder_roc_curve.png")
    plot_pr_curve(y_true, eval_errors, figure_dir / "autoencoder_precision_recall_curve.png")
    plot_confusion_matrix(metrics["confusion_matrix"], figure_dir / "autoencoder_confusion_matrix.png")
    plot_error_distribution(
        train_errors,
        eval_errors,
        threshold,
        figure_dir / "autoencoder_reconstruction_error_distribution.png",
    )
    plot_training_history(load_history(artifact_dir / "training_history.json"), figure_dir)

    print(f"Saved autoencoder metrics to {artifact_dir / 'metrics.json'}")
    print(f"Saved figures to {figure_dir}")


if __name__ == "__main__":
    main()