# NASA Turbofan Anomaly Detection

## Dataset Overview

- Processed FD003 train split: `fd003_healthy_baseline.csv`
- Processed FD003 evaluation split: `fd003_with_rul.csv`
- Feature set: sensor_11, sensor_4, sensor_13, sensor_8, sensor_17, sensor_3, sensor_2, sensor_9
- Autoencoder training uses normal samples only.
- Existing Isolation Forest ROC-AUC from the notebook: 0.982567865775417

## Isolation Forest Results

- ROC-AUC: 0.9803
- Precision: 0.5215
- Recall: 0.9787
- F1: 0.6804
- PR-AUC: 0.8823
- Accuracy: 0.8847
- Inference Time: 0.0021 ms/sample

## Autoencoder Results

- ROC-AUC: 0.8394
- Precision: 0.4168
- Recall: 0.4994
- F1: 0.4544
- PR-AUC: 0.4341
- Accuracy: 0.8496
- Inference Time: 0.0088 ms/sample
- Threshold: 0.0007
- Threshold Percentile: 95.0000

## ROC-AUC Comparison

- Isolation Forest ROC-AUC: 0.9803
- Autoencoder ROC-AUC: 0.8394
- Difference: -0.1409

## Precision / Recall Comparison

- Precision Difference: -0.1047
- Recall Difference: -0.4794
- F1 Difference: -0.2261

## Computational Cost Comparison

- Isolation Forest inference time: 0.0021 ms/sample
- Autoencoder inference time: 0.0088 ms/sample
- Difference: 0.0067 ms/sample

## Inference Latency Comparison

For a telemetry simulator -> Kafka -> real-time inference -> alerting -> dashboard pipeline, lower inference latency and simpler deployment usually matter more than marginal score gains. Isolation Forest is already lightweight and easy to scale. The Autoencoder is a stronger fit only if it brings a clear quality improvement that justifies TensorFlow serving overhead.

## Strengths and Weaknesses

### Isolation Forest
- Strengths: fast inference, low operational complexity, strong baseline performance, easy CPU deployment.
- Weaknesses: less expressive than a learned nonlinear model, may miss subtler multivariate structure.

### Autoencoder
- Strengths: learns nonlinear feature interactions, can improve detection on complex degradation signatures, flexible architecture.
- Weaknesses: higher training and serving complexity, heavier runtime dependencies, more tuning required.

## Recommendation

Isolation Forest is the stronger candidate for real-time deployment because it preserves the best accuracy-to-latency tradeoff and is simpler to operate.

### Metric Delta Summary

- ROC-AUC Difference: -0.1409
- Precision Difference: -0.1047
- Recall Difference: -0.4794
- F1 Difference: -0.2261
- Inference Latency Difference: 0.0067 ms/sample
