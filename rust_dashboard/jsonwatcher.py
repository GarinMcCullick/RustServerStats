import json
from PySide6.QtCore import QObject, QTimer
import pandas as pd
from pathlib import Path

DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")

class JSONWatcher(QObject):
    """Watches player_data.json and triggers dashboard + tabs refresh safely."""
    
    def __init__(self, dashboard, tabs=None):
        super().__init__()
        self.dashboard = dashboard
        self.tabs = tabs or []  # SearchTab, TableTab, etc.
        self.last_mtime = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_json)
        self.timer.start(1000)  # check every second

    def check_json(self):
        try:
            if not DATA_JSON.exists():
                return

            mtime = DATA_JSON.stat().st_mtime
            if mtime == self.last_mtime:
                return  # no change

            self.last_mtime = mtime
            print("[Watcher] JSON changed → refreshing dashboard + tabs")

            # Load JSON
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)

            df = pd.DataFrame(data)

            # Ensure needed columns
            if "rust_hours_total" not in df.columns:
                df["rust_hours_total"] = 0
            if "rust_hours_2weeks" not in df.columns:
                df["rust_hours_2weeks"] = 0

            # Extract private profile flag safely
            if "flags" in df.columns:
                df["private_profile"] = df["flags"].apply(
                    lambda f: f.get("private_profile", False) if isinstance(f, dict) else False
                )
            else:
                df["private_profile"] = False

            # --- REFRESH DASHBOARD ---
            QTimer.singleShot(0, lambda df=df: self.dashboard.refresh_data(df))

            # --- REFRESH ALL TABS ---
            for tab in self.tabs:
                if hasattr(tab, "refresh_data"):
                    # SearchTab
                    QTimer.singleShot(0, lambda df=df, t=tab: t.refresh_data(df))
                elif hasattr(tab, "update_data"):
                    # TableTab
                    QTimer.singleShot(0, lambda df=df, t=tab: t.update_data(df))

        except Exception as e:
            print("[Watcher] Error:", e)
