# ML Documentation

This section contains the machine learning and model-analysis material for the Turbofan IoT anomaly detection MVP.

## Contents

- Model training scripts
  - `training/train_autoencoder.py`
- Evaluation scripts
  - `evaluation/evaluate_autoencoder.py`
  - `evaluation/evaluate_isolation_forest.py`
  - `evaluation/compare_models.py`
- Model artifacts
  - `artifacts/autoencoder/`
  - `artifacts/isolation_forest/`
- Reports and comparison output
  - `reports/model_comparison.md`
  - `reports/model_comparison.json`
  - `reports/figures/`

## ML workflow

1. Prepare and normalize the turbine telemetry datasets.
2. Train the anomaly detection models using the scripts under `training/`.
3. Evaluate model performance using the scripts under `evaluation/`.
4. Compare model metrics and visualizations in `reports/`.
5. Store the selected trained artifacts under `artifacts/` for inference and runtime use.

## Key model assets

- Autoencoder model for reconstruction-based anomaly detection
- Isolation Forest baseline for unsupervised anomaly detection
- Common evaluation logic under `evaluation/common.py`

## Notes

This directory is meant to isolate all ML-related documentation, experimentation, and artifact tracking from the API, dashboard, and infrastructure docs.
