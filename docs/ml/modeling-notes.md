# Modeling Notes

## Overview

This project compares a reconstruction-based autoencoder against an isolation-forest baseline for anomaly detection on turbofan telemetry data.

## Model candidates

### Autoencoder

- Located in `models/autoencoder.py`
- Trained with the script in `training/train_autoencoder.py`
- Output stored in `artifacts/autoencoder/`

### Isolation Forest

- Evaluated with `evaluation/evaluate_isolation_forest.py`
- Output stored in `artifacts/isolation_forest/`

## Evaluation flow

- Shared evaluation helpers: `evaluation/common.py`
- Model comparison summary: `evaluation/compare_models.py`
- Report outputs: `reports/model_comparison.md` and `reports/model_comparison.json`

## Best practice

Keep model code, training logic, evaluation scripts, and runtime artifacts separated from the application service docs so the operating stack and the ML lifecycle remain easy to audit.
