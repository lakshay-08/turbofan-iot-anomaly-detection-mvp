"""Dense feedforward autoencoder for NASA C-MAPSS anomaly detection.

This module contains a reusable Keras autoencoder implementation with a
configurable dense architecture, reconstruction helpers, and persistence
utilities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    raise ImportError(
        "TensorFlow is required to use the autoencoder module. Install tensorflow "
        "before running the training or evaluation scripts."
    ) from exc


@dataclass(slots=True)
class AutoencoderConfig:
    """Configuration for a dense feedforward autoencoder."""

    input_dim: int
    encoder_units: tuple[int, ...] = (64, 32, 16)
    activation: str = "relu"
    output_activation: str = "linear"
    learning_rate: float = 1e-3
    model_name: str = "turbofan_autoencoder"

    def __post_init__(self) -> None:
        if self.input_dim <= 0:
            raise ValueError("input_dim must be a positive integer")
        if len(self.encoder_units) < 1:
            raise ValueError("encoder_units must contain at least one layer size")
        if any(unit <= 0 for unit in self.encoder_units):
            raise ValueError("encoder_units must contain only positive integers")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "AutoencoderConfig":
        encoder_units = tuple(int(value) for value in payload["encoder_units"])
        return cls(
            input_dim=int(payload["input_dim"]),
            encoder_units=encoder_units,
            activation=str(payload.get("activation", "relu")),
            output_activation=str(payload.get("output_activation", "linear")),
            learning_rate=float(payload.get("learning_rate", 1e-3)),
            model_name=str(payload.get("model_name", "turbofan_autoencoder")),
        )


class DenseAutoencoder:
    """Convenience wrapper around a dense autoencoder Keras model."""

    def __init__(self, config: AutoencoderConfig) -> None:
        self.config = config
        self.model: keras.Model = self._build_model()

    def _build_model(self) -> keras.Model:
        inputs = keras.Input(shape=(self.config.input_dim,), name="features")
        x = inputs

        for index, units in enumerate(self.config.encoder_units):
            x = layers.Dense(
                units,
                activation=self.config.activation,
                name=f"encoder_dense_{index + 1}",
            )(x)

        for index, units in enumerate(reversed(self.config.encoder_units[:-1])):
            x = layers.Dense(
                units,
                activation=self.config.activation,
                name=f"decoder_dense_{index + 1}",
            )(x)

        outputs = layers.Dense(
            self.config.input_dim,
            activation=self.config.output_activation,
            name="reconstruction",
        )(x)

        model = keras.Model(inputs=inputs, outputs=outputs, name=self.config.model_name)
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.config.learning_rate),
            loss="mse",
        )
        return model

    def fit(
        self,
        X_train: np.ndarray,
        X_validation: np.ndarray,
        epochs: int,
        batch_size: int,
        callbacks: Sequence[keras.callbacks.Callback] | None = None,
        verbose: int = 1,
    ) -> keras.callbacks.History:
        train_array = np.asarray(X_train, dtype=np.float32)
        validation_array = np.asarray(X_validation, dtype=np.float32)
        return self.model.fit(
            train_array,
            train_array,
            validation_data=(validation_array, validation_array),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=list(callbacks) if callbacks is not None else None,
            verbose=verbose,
            shuffle=True,
        )

    def reconstruct(self, X: np.ndarray, verbose: int = 0) -> np.ndarray:
        array = np.asarray(X, dtype=np.float32)
        return self.model.predict(array, verbose=verbose)

    def reconstruction_error(self, X: np.ndarray, verbose: int = 0) -> np.ndarray:
        array = np.asarray(X, dtype=np.float32)
        reconstructed = self.reconstruct(array, verbose=verbose)
        return np.mean(np.square(array - reconstructed), axis=1)

    def save(self, path: Path | str) -> None:
        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(target_path)

    @classmethod
    def load(cls, path: Path | str) -> "DenseAutoencoder":
        loaded_model = keras.models.load_model(Path(path))
        input_dim = int(loaded_model.input_shape[-1])
        config = AutoencoderConfig(input_dim=input_dim)
        instance = cls.__new__(cls)
        instance.config = config
        instance.model = loaded_model
        return instance


__all__ = ["AutoencoderConfig", "DenseAutoencoder"]