### Convert json to csv to enable colleagues to cross-check the failed downloads

import pandas as pd

with open("failed_downloads.json", encoding="utf-8") as inputfile:
    df = pd.read_json("failed_downloads.json")

df.to_csv("failed_downloads.csv", encoding="utf-8", index=False)

print(df.shape[0]) # In total 54 downloads failed