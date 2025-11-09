import json
import pandas as pd

JSON_FILE = "../playerData.json"

def load_data():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df["rust_hours_total"] = pd.to_numeric(df["rust_hours_total"])
    df["rust_hours_2weeks"] = pd.to_numeric(df["rust_hours_2weeks"])
    return df
