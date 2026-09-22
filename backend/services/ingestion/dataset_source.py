from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event
from typing import Any, Iterator

import pandas as pd

from preprocessing.pre_processing_test_set import load_test_file
from preprocessing.pre_processing_train_set import load_train_file
from services.ingestion.config import REPO_ROOT, IngestionSettings
from services.ingestion.normalizer import normalize_dataset_row

LOGGER = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".txt"}


@dataclass(slots=True)
class DatasetDiscoveryResult:
    files: list[Path]
    test_datasets: list[Path]
    processed_datasets: list[Path]
    evaluation_datasets: list[Path]



def _speed_divisor(speed: str) -> float | None:
    if speed == "max":
        return None
    if speed.endswith("x"):
        return max(float(speed[:-1]), 0.1)
    return 1.0


def _parse_row_timestamp(row: dict[str, Any]) -> datetime | None:
    raw_value = row.get("timestamp")
    if raw_value is None:
        return None
    parsed = pd.to_datetime(raw_value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()



def _read_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".txt":
        lower_name = path.name.lower()
        if lower_name.startswith("test_"):
            return load_test_file(path)
        if lower_name.startswith("train_"):
            return load_train_file(path)
        raise ValueError(f"Unsupported TXT dataset format: {path}")
    raise ValueError(f"Unsupported dataset extension: {path}")


class DatasetReplaySource:
    def __init__(self, settings: IngestionSettings) -> None:
        self._settings = settings

    def discover_datasets(self) -> DatasetDiscoveryResult:
        configured_path = Path(self._settings.dataset_path)
        files: list[Path] = []

        if configured_path.exists():
            if configured_path.is_file() and configured_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files = [configured_path]
            elif configured_path.is_dir():
                files = sorted(
                    file
                    for file in configured_path.rglob("*")
                    if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS
                )

        if not files:
            candidate_dirs = [
                REPO_ROOT / "data" / "processed" / "test",
                REPO_ROOT / "data" / "processed" / "train",
                REPO_ROOT / "evaluation",
                REPO_ROOT / "storage" / "raw" / "nasa_cmaps",
            ]
            for directory in candidate_dirs:
                if directory.exists():
                    files.extend(
                        sorted(
                            file
                            for file in directory.rglob("*")
                            if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS
                        )
                    )

        files = sorted({file.resolve() for file in files})

        test_datasets = [path for path in files if "processed/test" in str(path).replace("\\", "/")]
        processed_datasets = [path for path in files if "processed" in str(path).replace("\\", "/")]
        evaluation_datasets = [path for path in files if "/evaluation/" in str(path).replace("\\", "/")]

        return DatasetDiscoveryResult(
            files=files,
            test_datasets=test_datasets,
            processed_datasets=processed_datasets,
            evaluation_datasets=evaluation_datasets,
        )

    def _iter_rows(self, stop_event: Event) -> Iterator[dict[str, Any]]:
        discovery = self.discover_datasets()
        if not discovery.files:
            raise FileNotFoundError("No supported dataset files found for replay")

        LOGGER.info(
            "Dataset discovery complete",
            extra={"records": len(discovery.files)},
        )

        speed = _speed_divisor(self._settings.replay_speed)
        current_timestamp = datetime.now(timezone.utc)
        previous_input_timestamp: datetime | None = None

        emitted = 0
        global_index = 0
        max_records = self._settings.replay_limit
        start_idx = max(self._settings.replay_start_index, 0)
        end_idx = self._settings.replay_end_index

        for dataset_file in discovery.files:
            if stop_event.is_set():
                break

            try:
                df = _read_dataset(dataset_file)
            except Exception as exc:
                LOGGER.warning("Skipping unreadable dataset", extra={"file": str(dataset_file), "error": str(exc)})
                continue

            source_label = str(dataset_file.relative_to(REPO_ROOT)) if dataset_file.is_relative_to(REPO_ROOT) else str(dataset_file)
            LOGGER.info("Replaying dataset", extra={"file": source_label, "records": int(len(df))})

            for _, row in df.iterrows():
                if stop_event.is_set():
                    break

                if global_index < start_idx:
                    global_index += 1
                    continue
                if end_idx is not None and global_index > end_idx:
                    return
                if max_records is not None and emitted >= max_records:
                    return

                row_dict = row.to_dict()
                input_timestamp = _parse_row_timestamp(row_dict)

                event_timestamp = (
                    input_timestamp.isoformat()
                    if input_timestamp is not None
                    else current_timestamp.isoformat()
                )
                normalized = normalize_dataset_row(
                    row=row_dict,
                    source_label=source_label,
                    event_timestamp=event_timestamp,
                    row_index=global_index,
                )

                global_index += 1
                if normalized is None:
                    LOGGER.warning("Skipping malformed dataset row", extra={"file": source_label})
                    continue

                emitted += 1
                if emitted % 1000 == 0:
                    LOGGER.info("Replay progress", extra={"records": emitted, "file": source_label})

                yield normalized

                if speed is not None:
                    if input_timestamp is not None and previous_input_timestamp is not None:
                        delta_seconds = (input_timestamp - previous_input_timestamp).total_seconds()
                        time.sleep(max(delta_seconds / speed, 0.0))
                    else:
                        time.sleep(1.0 / speed)

                previous_input_timestamp = input_timestamp
                if input_timestamp is None:
                    current_timestamp += timedelta(seconds=1)

        LOGGER.info("Dataset replay completed", extra={"records": emitted})

    def events(self, stop_event: Event) -> Iterator[dict[str, Any]]:
        return self._iter_rows(stop_event)
