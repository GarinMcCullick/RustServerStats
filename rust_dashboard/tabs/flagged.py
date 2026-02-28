from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from PySide6.QtCore import QTimer
import requests
import json
from pathlib import Path
from datetime import datetime

DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")
STEAM_API_KEY = "2D01D80224108A449432583EA81C08B3"
CHECK_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes


class FlaggedWatcherTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.status_label = QLabel("Checking flagged profiles every 5 minutes...")
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Name", "SteamID", "Status", "Game", "Flagged At"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_flagged_status)
        self.timer.start(CHECK_INTERVAL_MS)

        self.refresh_flagged_status()

    # ---------------- JSON ---------------- #
    def load_json_players(self):
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.status_label.setText(f"Error loading player data: {e}")
            return []

    # ---------------- STEAM API ---------------- #
    def fetch_steam_statuses(self, steam_ids):
        """Fetch live status from Steam API for a list of SteamIDs."""
        if not steam_ids:
            return {}
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={STEAM_API_KEY}&steamids={','.join(steam_ids)}"
        try:
            data = requests.get(url, timeout=10).json()
            players = data.get("response", {}).get("players", [])
            results = {}
            for sid in steam_ids:
                player = next((p for p in players if p.get("steamid") == sid), None)
                if not player:
                    results[sid] = {"status": "Private", "game": "—", "private_profile": True}
                    continue
                private = player.get("communityvisibilitystate", 0) != 3
                results[sid] = {
                    "status": "Private" if private else ["Offline","Online","Busy","Away","Snooze","LTrade","LPlay"][player.get("personastate",0)],
                    "game": "—" if private else player.get("gameextrainfo", "—"),
                    "private_profile": private
                }
            return results
        except Exception:
            return {sid: {"status":"Private","game":"—","private_profile":True} for sid in steam_ids}

    # ---------------- UPDATE TABLE ---------------- #
    def refresh_flagged_status(self):
        """Read JSON, fetch Steam API, and update table."""
        players_json = self.load_json_players()
        flagged = [p for p in players_json if p.get("flags", {}).get("flagged", False)]
        steam_ids = [p["steam_id"] for p in flagged if "steam_id" in p]

        statuses = self.fetch_steam_statuses(steam_ids)

        self.table.setRowCount(len(flagged))
        for i, p in enumerate(flagged):
            sid = p.get("steam_id", "—")
            name = p.get("name", "Unknown")
            flagged_at = p.get("flags", {}).get("flagged_at", "—")
            info = statuses.get(sid, {"status":"Private","game":"—","private_profile":True})

            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(sid))
            self.table.setItem(i, 2, QTableWidgetItem(info["status"]))
            self.table.setItem(i, 3, QTableWidgetItem(info["game"]))
            self.table.setItem(i, 4, QTableWidgetItem(flagged_at.replace("T", " ")))

        self.status_label.setText(f"Updated — {len(flagged)} flagged total.")
