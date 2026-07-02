"""Train the dense autoencoder on normal NASA C-MAPSS samples only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.common import (  # noqa: E402
    ARTIFACTS_DIR,
    DEFAULT_RANDOM_STATE,
    DEFAULT_VALIDATION_FRACTION,
    FEATURE_COLUMNS,
    ensure_directory,
    extract_feature_frame,
    load_processed_frames,
    normal_samples,
    save_json,
    split_train_validation,
)
from models.autoencoder import AutoencoderConfig, DenseAutoencoder  # noqa: E402

try:
    import tensorflow as tf
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise ImportError(
        "TensorFlow is required to train the autoencoder. Install tensorflow before running this script."
    ) from exc


def parse_units(raw_value: str) -> tuple[int, ...]:
    units = tuple(int(part.strip()) for part in raw_value.split(",") if part.strip())
    if not units:
        raise argparse.ArgumentTypeError("encoder units must contain at least one integer")
    if any(unit <= 0 for unit in units):
        raise argparse.ArgumentTypeError("encoder units must be positive integers")
    return units


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a dense autoencoder for C-MAPSS anomaly detection")
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "processed" / "train")
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACTS_DIR / "autoencoder")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--validation-fraction", type=float, default=DEFAULT_VALIDATION_FRACTION)
    parser.add_argument("--random-state", type=int, default=DEFAULT_RANDOM_STATE)
    parser.add_argument("--encoder-units", type=parse_units, default=parse_units("64,32,16"))
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--min-delta", type=float, default=1e-4)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    artifact_dir = ensure_directory(args.artifact_dir)

    train_df, _ = load_processed_frames(args.data_dir)
    normal_train_df = normal_samples(train_df)
    feature_frame = extract_feature_frame(normal_train_df, FEATURE_COLUMNS)
    train_split_df, validation_split_df = split_train_validation(
        feature_frame,
        validation_fraction=args.validation_fraction,
        random_state=args.random_state,
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(train_split_df)
    X_validation = scaler.transform(validation_split_df)

    config = AutoencoderConfig(
        input_dim=X_train.shape[1],
        encoder_units=tuple(args.encoder_units),
        learning_rate=args.learning_rate,
    )
    autoencoder = DenseAutoencoder(config)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=args.patience,
            min_delta=args.min_delta,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(artifact_dir / "best_model.keras"),
            monitor="val_loss",
            save_best_only=True,
            save_weights_only=False,
            verbose=1,
        ),
    ]

    history = autoencoder.fit(
        X_train=X_train,
        X_validation=X_validation,
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    autoencoder.save(artifact_dir / "model.keras")
    joblib.dump(scaler, artifact_dir / "scaler.joblib")

    history_payload = {
        key: [float(value) for value in values]
        for key, values in history.history.items()
    }
    save_json(artifact_dir / "training_history.json", history_payload)
    save_json(
        artifact_dir / "config.json",
        {
            **config.to_dict(),
            "validation_fraction": args.validation_fraction,
            "random_state": args.random_state,
            "batch_size": args.batch_size,
            "epochs": args.epochs,
            "feature_columns": FEATURE_COLUMNS,
        },
    )
    save_json(
        artifact_dir / "training_manifest.json",
        {
            "train_source": str(args.data_dir / "fd003_healthy_baseline.csv"),
            "feature_columns": FEATURE_COLUMNS,
            "n_train_rows": int(len(train_split_df)),
            "n_validation_rows": int(len(validation_split_df)),
            "validation_fraction": args.validation_fraction,
            "random_state": args.random_state,
        },
    )

    print(f"Saved autoencoder artifacts to {artifact_dir}")


if __name__ == "__main__":
    main()