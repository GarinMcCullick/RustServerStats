import json
from pathlib import Path
from PySide6.QtCore import QObject, QTimer
import pandas as pd

DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")


class JSONWatcher(QObject):
    """Watches player_data.json and triggers dashboard + tabs refresh safely."""

    def __init__(self, dashboard, table_tab=None, tabs=None):
        super().__init__()
        self.dashboard = dashboard
        self.table_tab = table_tab
        self.tabs = tabs or []
        self.last_mtime = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_json)
        self.timer.start(1000)

    def check_json(self):
        if getattr(self.table_tab, "_suppress_checkbox", False):
            return

        if not DATA_JSON.exists():
            return

        mtime = DATA_JSON.stat().st_mtime
        if mtime == self.last_mtime:
            return

        self.last_mtime = mtime
        print("[Watcher] JSON changed → refreshing dashboard + tabs")

        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)

            df = pd.DataFrame(data)

            # Ensure required columns exist
            if "rust_hours_total" not in df.columns:
                df["rust_hours_total"] = 0
            if "rust_hours_2weeks" not in df.columns:
                df["rust_hours_2weeks"] = 0
            if "flags" not in df.columns:
                df["flags"] = [{} for _ in range(len(df))]

            # Flatten flags for easy access in GUI
            df["flagged"] = df["flags"].apply(lambda f: f.get("flagged", False) if isinstance(f, dict) else False)
            df["private_profile"] = df["flags"].apply(lambda f: f.get("private_profile", False) if isinstance(f, dict) else False)

            # Refresh dashboard and tabs
            self.dashboard.refresh_data(df)
            for tab in self.tabs:
                if hasattr(tab, "refresh_data"):
                    tab.refresh_data(df)
                elif hasattr(tab, "update_data"):
                    tab.update_data(df)

        except Exception as e:
            print("[Watcher] Error:", e)
