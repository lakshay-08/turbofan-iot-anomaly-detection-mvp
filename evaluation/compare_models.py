"""Compare Isolation Forest and Autoencoder metrics and generate a markdown report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.common import ARTIFACTS_DIR, REPORTS_DIR, ensure_directory, load_json, save_json  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare the two anomaly detection approaches")
    parser.add_argument("--autoencoder-metrics", type=Path, default=ARTIFACTS_DIR / "autoencoder" / "metrics.json")
    parser.add_argument("--if-metrics", type=Path, default=ARTIFACTS_DIR / "isolation_forest" / "metrics.json")
    parser.add_argument("--output", type=Path, default=REPORTS_DIR / "model_comparison.md")
    return parser


def format_metric(value: Any, digits: int = 4) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def load_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing metrics file: {path}. Run the matching evaluation script first.")
    return load_json(path)


def metric_delta(autoencoder_value: float, baseline_value: float) -> float:
    return float(autoencoder_value - baseline_value)


def render_report(if_metrics: dict[str, Any], ae_metrics: dict[str, Any]) -> str:
    roc_auc_delta = metric_delta(float(ae_metrics["roc_auc"]), float(if_metrics["roc_auc"]))
    precision_delta = metric_delta(float(ae_metrics["precision"]), float(if_metrics["precision"]))
    recall_delta = metric_delta(float(ae_metrics["recall"]), float(if_metrics["recall"]))
    f1_delta = metric_delta(float(ae_metrics["f1"]), float(if_metrics["f1"]))
    latency_delta = metric_delta(
        float(ae_metrics["inference_ms_per_sample"]),
        float(if_metrics["inference_ms_per_sample"]),
    )

    if_a = float(if_metrics["roc_auc"])
    ae_a = float(ae_metrics["roc_auc"])
    if_latency = float(if_metrics["inference_ms_per_sample"])
    ae_latency = float(ae_metrics["inference_ms_per_sample"])

    if ae_a > if_a and ae_latency <= if_latency * 1.5:
        recommendation = (
            "The Autoencoder is the stronger candidate for production if the team wants "
            "a nonlinear detector and can absorb the extra operational complexity."
        )
    elif if_a >= ae_a and if_latency <= ae_latency:
        recommendation = (
            "Isolation Forest is the stronger candidate for real-time deployment because "
            "it preserves the best accuracy-to-latency tradeoff and is simpler to operate."
        )
    else:
        recommendation = (
            "Both approaches are viable. Isolation Forest is preferable for the current "
            "telemetry-to-alerting path when latency and simplicity dominate; the Autoencoder "
            "is useful when the team wants a deeper model and can support more training and serving complexity."
        )

    feature_columns = ", ".join(ae_metrics.get("feature_columns", []))

    return f"""# NASA Turbofan Anomaly Detection

## Dataset Overview

- Processed FD003 train split: `fd003_healthy_baseline.csv`
- Processed FD003 evaluation split: `fd003_with_rul.csv`
- Feature set: {feature_columns}
- Autoencoder training uses normal samples only.
- Existing Isolation Forest ROC-AUC from the notebook: 0.982567865775417

## Isolation Forest Results

- ROC-AUC: {format_metric(if_metrics['roc_auc'])}
- Precision: {format_metric(if_metrics['precision'])}
- Recall: {format_metric(if_metrics['recall'])}
- F1: {format_metric(if_metrics['f1'])}
- PR-AUC: {format_metric(if_metrics['pr_auc'])}
- Accuracy: {format_metric(if_metrics['accuracy'])}
- Inference Time: {format_metric(if_latency)} ms/sample

## Autoencoder Results

- ROC-AUC: {format_metric(ae_metrics['roc_auc'])}
- Precision: {format_metric(ae_metrics['precision'])}
- Recall: {format_metric(ae_metrics['recall'])}
- F1: {format_metric(ae_metrics['f1'])}
- PR-AUC: {format_metric(ae_metrics['pr_auc'])}
- Accuracy: {format_metric(ae_metrics['accuracy'])}
- Inference Time: {format_metric(ae_latency)} ms/sample
- Threshold: {format_metric(float(ae_metrics['threshold']))}
- Threshold Percentile: {format_metric(float(ae_metrics['threshold_percentile']))}

## ROC-AUC Comparison

- Isolation Forest ROC-AUC: {format_metric(if_a)}
- Autoencoder ROC-AUC: {format_metric(ae_a)}
- Difference: {format_metric(roc_auc_delta)}

## Precision / Recall Comparison

- Precision Difference: {format_metric(precision_delta)}
- Recall Difference: {format_metric(recall_delta)}
- F1 Difference: {format_metric(f1_delta)}

## Computational Cost Comparison

- Isolation Forest inference time: {format_metric(if_latency)} ms/sample
- Autoencoder inference time: {format_metric(ae_latency)} ms/sample
- Difference: {format_metric(latency_delta)} ms/sample

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

{recommendation}

### Metric Delta Summary

- ROC-AUC Difference: {format_metric(roc_auc_delta)}
- Precision Difference: {format_metric(precision_delta)}
- Recall Difference: {format_metric(recall_delta)}
- F1 Difference: {format_metric(f1_delta)}
- Inference Latency Difference: {format_metric(latency_delta)} ms/sample
"""


def main() -> None:
    args = build_parser().parse_args()
    output_path = args.output
    ensure_directory(output_path.parent)

    if_metrics = load_metrics(args.if_metrics)
    ae_metrics = load_metrics(args.autoencoder_metrics)
    report = render_report(if_metrics, ae_metrics)
    output_path.write_text(report, encoding="utf-8")

    summary_path = output_path.with_suffix(".json")
    save_json(
        summary_path,
        {
            "isolation_forest": if_metrics,
            "autoencoder": ae_metrics,
            "report_path": str(output_path),
        },
    )
    print(f"Saved comparison report to {output_path}")


if __name__ == "__main__":
    main()