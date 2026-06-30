import pandas as pd

train = pd.read_csv("data/processed/fd003_with_rul.csv")
test = pd.read_csv("data/processed/fd003_test_with_rul.csv")

print(train.groupby("engine_id")["cycle"].max().describe())
print(test.groupby("engine_id")["cycle"].max().describe())
