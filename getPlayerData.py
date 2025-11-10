import csv
import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

CSV_INPUT = "mute_list.csv"
JSON_OUTPUT = "player_data.json"

STEAM_KEY = "2D01D80224108A449432583EA81C08B3"

PLAYER_SUMMARY_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
RUST_APP_ID = 252490
MAX_THREADS = 5  # concurrent threads

def log(msg):
    print(f"[LOG] {msg}")

def fetch_profile(steam_id):
    try:
        log(f"Fetching profile for {steam_id}")
        r = requests.get(
            PLAYER_SUMMARY_URL,
            params={"key": STEAM_KEY, "steamids": steam_id},
            timeout=10,
        )
        log(f"Profile response {steam_id}: {r.status_code}")
        r.raise_for_status()
        players = r.json().get("response", {}).get("players", [])
        if not players:
            log(f"No profile found for {steam_id}")
        return players[0] if players else None
    except Exception as e:
        log(f"[Profile ERROR] {steam_id}: {e}")
        return None

def fetch_rust_hours(steam_id):
    try:
        log(f"Fetching Rust hours for {steam_id}")
        r = requests.get(
            OWNED_GAMES_URL,
            params={
                "key": STEAM_KEY,
                "steamid": steam_id,
                "include_played_free_games": 1,
                "include_appinfo": 0,
            },
            timeout=10,
        )
        log(f"Rust hours response {steam_id}: {r.status_code}")
        r.raise_for_status()
        games = r.json().get("response", {}).get("games", [])
        for g in games:
            if g["appid"] == RUST_APP_ID:
                total = round(g.get("playtime_forever", 0) / 60, 1)
                recent = round(g.get("playtime_2weeks", 0) / 60, 1)
                return total, recent
        return 0, 0
    except Exception as e:
        log(f"[Rust Hours ERROR] {steam_id}: {e}")
        return 0, 0

def fetch_player_data(steam_id, profile_url):
    profile = fetch_profile(steam_id)
    total, recent = fetch_rust_hours(steam_id)
    name = profile.get("personaname", "UNKNOWN") if profile else "UNKNOWN"
    private = profile is None
    return {
        "steam_id": steam_id,
        "name": name,
        "rust_hours_total": total,
        "rust_hours_2weeks": recent,
        "profile_url": profile_url,
        "flags": {"private_profile": private}
    }

def main():
    if not os.path.exists(CSV_INPUT):
        log(f"{CSV_INPUT} not found. Nothing to do.")
        return

    # Load existing JSON
    existing_data = {}
    if os.path.exists(JSON_OUTPUT):
        with open(JSON_OUTPUT, "r", encoding="utf-8") as f:
            existing_data_list = json.load(f)
            existing_data = {entry["steam_id"]: entry for entry in existing_data_list}

    # Read CSV
    with open(CSV_INPUT, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        steam_rows = [row for row in reader if row["steamid"].strip() and row["steamid"].strip() not in existing_data]

    if not steam_rows:
        log("All Steam IDs already fetched or invalid. Nothing to do.")
        return

    results = list(existing_data.values())

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_sid = {
            executor.submit(fetch_player_data, row["steamid"].strip(), row.get("profile_url", "").strip()): row["steamid"].strip()
            for row in steam_rows
        }

        for future in as_completed(future_to_sid):
            sid = future_to_sid[future]
            try:
                data = future.result()
                results.append(data)
                log(f"[{sid}] -> {data['name']} | Total: {data['rust_hours_total']}h | 2w: {data['rust_hours_2weeks']}h")
            except Exception as e:
                log(f"[{sid}] ERROR: {e}")
                # Continue processing all other SteamIDs

    # Save JSON
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    log(f"Done! Output written to {JSON_OUTPUT}")

if __name__ == "__main__":
    main()
