from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "storage" / "raw" / "nasa_cmaps"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "test"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


DATASETS = [
    "FD001",
    "FD002",
    "FD003",
    "FD004"
]


COLUMNS = (
    ["engine_id", "cycle"]
    + [f"setting_{i}" for i in range(1, 4)]
    + [f"sensor_{i}" for i in range(1, 22)]
)


def label_health(rul):
    if rul > 120:
        return "Healthy"
    elif rul > 60:
        return "Early_Wear"
    elif rul > 20:
        return "Warning"
    else:
        return "Critical"


def load_test_file(path):
    df = pd.read_csv(
        path,
        sep=r"\s+",
        header=None
    )

    if df.shape[1] > 26:
        df = df.iloc[:, :26]

    df.columns = COLUMNS

    return df



def process_test_dataset(dataset):

    print(f"\nProcessing TEST {dataset}")

    test_file = RAW_DIR / f"test_{dataset}.txt"
    rul_file = RAW_DIR / f"RUL_{dataset}.txt"

    if not test_file.exists():
        print(f"Missing {test_file}")
        return

    if not rul_file.exists():
        print(f"Missing {rul_file}")
        return


    test_df = load_test_file(test_file)

    rul_df = pd.read_csv(
        rul_file,
        header=None,
        names=["final_rul"]
    )


    max_cycles = (
        test_df.groupby("engine_id")["cycle"]
        .max()
        .reset_index()
        .rename(columns={"cycle": "max_cycle"})
    )

    max_cycles["final_rul"] = rul_df["final_rul"]

    test_df = test_df.merge(
        max_cycles,
        on="engine_id"
    )

    test_df["RUL"] = (
        test_df["max_cycle"]
        - test_df["cycle"]
        + test_df["final_rul"]
    )


    test_df["health_stage"] = (
        test_df["RUL"]
        .apply(label_health)
    )

    test_df["anomaly_label"] = (
        test_df["RUL"] <= 30
    ).astype(int)


    output_file = (
        PROCESSED_DIR
        / f"{dataset.lower()}_test_with_rul.csv"
    )

    test_df.to_csv(
        output_file,
        index=False
    )

    print(f"Saved: {output_file.name}")
    print(f"Rows: {len(test_df):,}")
    print(
        f"Engines: {test_df['engine_id'].nunique()}"
    )


if __name__ == "__main__":

    for dataset in DATASETS:
        process_test_dataset(dataset)

    print("\nAll test datasets processed.")