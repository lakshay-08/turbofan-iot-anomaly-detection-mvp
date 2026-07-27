from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib import request, error

import joblib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_feature_columns(artifact_dir: Path) -> list[str]:
    feature_file = artifact_dir / "feature_columns.joblib"
    if feature_file.exists():
        return list(joblib.load(feature_file))
    metrics_path = artifact_dir / "metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        return list(metrics.get("feature_columns", []))
    return []


def iter_rows(source_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for csv_path in sorted(source_dir.rglob("*.csv")):
        with csv_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append(row)
    return rows


def build_payload(row: dict[str, Any], feature_columns: list[str]) -> dict[str, Any]:
    payload: dict[str, Any] = {"engine_id": row.get("engine_id")}
    features: dict[str, float] = {}
    for column in feature_columns:
        if column in row:
            value = row[column]
            features[column] = float(value) if value not in (None, "") else 0.0
    payload["features"] = features
    return payload


def replay_via_api(rows: list[dict[str, Any]], feature_columns: list[str], api_url: str) -> None:
    endpoint = f"{api_url.rstrip('/')}/predict"
    for index, row in enumerate(rows, start=1):
        payload = build_payload(row, feature_columns)
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=10) as response:
                response.read()
        except error.URLError as exc:
            print(f"replay failed for row {index}: {exc}")
            continue
    print(f"replayed {len(rows)} rows through {endpoint}")


def replay_via_kafka(rows: list[dict[str, Any]], feature_columns: list[str], topic: str) -> None:
    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        for index, row in enumerate(rows, start=1):
            payload = build_payload(row, feature_columns)
            producer.send(topic, value=payload)
            producer.flush(timeout=10)
        print(f"published {len(rows)} rows to topic {topic}")
    finally:
        producer.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay processed telemetry datasets into the API or Kafka")
    parser.add_argument("--source-dir", default="data/processed")
    parser.add_argument("--mode", default=os.getenv("REPLAY_MODE", "api"), choices=["api", "kafka"])
    parser.add_argument("--api-url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--topic", default=os.getenv("RAW_TELEMETRY_TOPIC", "turbofan.raw.telemetry"))
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    artifact_dir = Path(__file__).resolve().parents[1] / "artifacts" / "isolation_forest"
    feature_columns = load_feature_columns(artifact_dir)
    rows = iter_rows(source_dir)
    if args.mode == "api":
        replay_via_api(rows, feature_columns, args.api_url)
    else:
        replay_via_kafka(rows, feature_columns, args.topic)


if __name__ == "__main__":
    main()
