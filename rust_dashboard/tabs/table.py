from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QCheckBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from functools import partial
from datetime import datetime
import json
from pathlib import Path
import pandas as pd

DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")


def set_flag(steam_id, flagged):
    try:
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    player = next((p for p in data if p.get("steam_id") == steam_id), None)
    if not player:
        player = {"steam_id": steam_id, "name": "Unknown", "flags": {}}
        data.append(player)

    player.setdefault("flags", {})
    player["flags"]["flagged"] = flagged
    if flagged:
        player["flags"]["flagged_at"] = datetime.utcnow().isoformat(timespec="seconds")
    else:
        player["flags"].pop("flagged_at", None)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class TableTab(QWidget):
    flagUpdated = Signal(str, bool)  # steam_id, new_flag_value

    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self._suppress_checkbox = False
        self.init_ui()

        # Ensure dataframe has these columns for safe updating
        for col in ["flags", "flagged", "private_profile"]:
            if col not in self.df.columns:
                self.df[col] = [{} if col == "flags" else False for _ in range(len(self.df))]

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search player by name or SteamID")
        self.search.textChanged.connect(self.update_table)
        layout.addWidget(self.search)

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        layout.addWidget(self.table)

        self.update_table()

    def is_flagged(self, steam_id):
        """Check JSON directly for current flagged status."""
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data:
                if p.get("steam_id") == steam_id:
                    return p.get("flags", {}).get("flagged", False)
        except Exception:
            return False
        return False

    def toggle_flag(self, steam_id, state):
        flagged = state == Qt.Checked
        set_flag(steam_id, flagged)  # persists JSON

        print(f"[TableTab] toggled {steam_id} → {flagged}")

        # Refresh the flagged watcher tab
        if hasattr(self.parent(), "tabs") and "Flagged" in self.parent().tabs:
            flagged_tab = self.parent().tabs["Flagged"]
            if flagged:
                flagged_tab.refresh_single_player(steam_id)
            else:
                flagged_tab.refresh_flagged_status()


    def update_table(self):
        if self.df.empty:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        text = self.search.text().lower()
        filtered = self.df[
            self.df["name"].str.lower().str.contains(text) |
            self.df["steam_id"].str.contains(text)
        ]

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Total Hours", "2 Weeks", "Profile", "Flagged"])
        self.table.setRowCount(len(filtered))

        for i, row in enumerate(filtered.itertuples()):
            items = [
                row.name,
                f"{row.rust_hours_total:.1f} h",
                f"{row.rust_hours_2weeks:.1f} h",
                f"https://steamcommunity.com/profiles/{row.steam_id}"
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                if col == 3:
                    item.setForeground(QColor("#007ACC"))
                self.table.setItem(i, col, item)

            checkbox = QCheckBox()
            self._suppress_checkbox = True
            checkbox.setChecked(self.is_flagged(row.steam_id))
            self._suppress_checkbox = False
            checkbox.stateChanged.connect(partial(self.toggle_flag, row.steam_id))
            self.table.setCellWidget(i, 4, checkbox)

        self.table.resizeColumnsToContents()
