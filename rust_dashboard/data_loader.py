from pathlib import Path
import json
import pandas as pd

# Adjust the path to your JSON file
JSON_FILE = Path(__file__).parent.parent / "player_data.json"

def load_data():
    expected_columns = [
        "steam_id", "name", "rust_hours_total", "rust_hours_2weeks",
        "profile_url", "private_profile"
    ]

    # Return empty DataFrame if file doesn't exist
    if not JSON_FILE.exists():
        print(f"[WARN] {JSON_FILE} not found, returning empty DataFrame")
        return pd.DataFrame(columns=expected_columns)

    # Read JSON safely
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load JSON: {e}")
        return pd.DataFrame(columns=expected_columns)

    # Ensure data is a list
    if isinstance(data, dict):
        data = list(data.values())
    elif not isinstance(data, list):
        print("[WARN] JSON is not a list, returning empty DataFrame")
        return pd.DataFrame(columns=expected_columns)

    # Flatten and clean data
    cleaned_data = []
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            print(f"[WARN] Skipping invalid entry at index {i}: {entry}")
            continue
        cleaned_entry = {
            "steam_id": str(entry.get("steam_id", "")),
            "name": str(entry.get("name", "")),
            "rust_hours_total": pd.to_numeric(entry.get("rust_hours_total", 0), errors="coerce"),
            "rust_hours_2weeks": pd.to_numeric(entry.get("rust_hours_2weeks", 0), errors="coerce"),
            "profile_url": str(entry.get("profile_url", "")),
            "private_profile": entry.get("flags", {}).get("private_profile", False)
        }
        cleaned_data.append(cleaned_entry)

    df = pd.DataFrame(cleaned_data, columns=expected_columns)
    print(f"[load_data] Loaded {len(df)} players from JSON")
    print(df.head(3))  # Show first 3 rows for debug
    return df
