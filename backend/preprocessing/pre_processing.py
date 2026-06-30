from pathlib import Path
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "storage" / "raw" / "nasa_cmaps"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


DATASETS = [
    "FD001",
    "FD002",
    "FD003",
    "FD004",
]

HEALTHY_CYCLES = 50

# =====================================================
# COLUMN NAMES
# =====================================================

COLUMNS = (
    ["engine_id", "cycle"]
    + [f"setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)


# =====================================================
# HELPERS
# =====================================================

def label_health(rul):
    if rul > 120:
        return "Healthy"
    elif rul > 60:
        return "Early_Wear"
    elif rul > 20:
        return "Warning"
    else:
        return "Critical"


def load_train_file(file_path):
    df = pd.read_csv(
        file_path,
        sep=r"\s+",
        header=None
    )

    # Remove trailing blank columns if present
    if df.shape[1] > 26:
        df = df.iloc[:, :26]

    df.columns = COLUMNS

    return df


def create_train_dataset(df):
    max_cycles = (
        df.groupby("engine_id")["cycle"]
        .max()
        .reset_index()
        .rename(columns={"cycle": "max_cycle"})
    )

    df = df.merge(max_cycles, on="engine_id")

    df["RUL"] = df["max_cycle"] - df["cycle"]

    df["health_stage"] = df["RUL"].apply(label_health)

    df["health_percent"] = (
        100 * df["RUL"] / df["max_cycle"]
    ).clip(0, 100).round(2)

    df["anomaly_label"] = np.where(
        df["RUL"] <= 30,
        1,
        0,
    )

    return df


# =====================================================
# MAIN PROCESSING
# =====================================================

def process_dataset(dataset):

    print(f"\n{'=' * 60}")
    print(f"Processing {dataset}")
    print(f"{'=' * 60}")

    train_file = RAW_DIR / f"train_{dataset}.txt"

    if not train_file.exists():
        print(f"Missing file: {train_file}")
        return

    # -----------------------------
    # Load train data
    # -----------------------------

    train_df = load_train_file(train_file)

    print("Raw Shape:", train_df.shape)

    # -----------------------------
    # Create RUL dataset
    # -----------------------------

    processed_df = create_train_dataset(train_df)

    # -----------------------------
    # Save processed dataset
    # -----------------------------

    processed_output = (
        PROCESSED_DIR /
        f"{dataset.lower()}_with_rul.csv"
    )

    processed_df.to_csv(
        processed_output,
        index=False
    )

    # -----------------------------
    # Save healthy baseline data
    # -----------------------------

    healthy_df = processed_df[
        processed_df["cycle"] <= HEALTHY_CYCLES
    ].copy()

    healthy_output = (
        PROCESSED_DIR /
        f"{dataset.lower()}_healthy_baseline.csv"
    )

    healthy_df.to_csv(
        healthy_output,
        index=False
    )

    # -----------------------------
    # Summary
    # -----------------------------

    print(f"Saved: {processed_output.name}")
    print(f"Saved: {healthy_output.name}")

    print(
        f"Rows: {len(processed_df):,}"
    )

    print(
        f"Engines: {processed_df['engine_id'].nunique()}"
    )

    print(
        processed_df["health_stage"]
        .value_counts()
        .to_string()
    )


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    for dataset in DATASETS:
        process_dataset(dataset)

    print("\nDone.")