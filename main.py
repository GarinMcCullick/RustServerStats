import sys
import threading
import subprocess
import warnings
import json
import csv
from pathlib import Path
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtWidgets import QApplication
from rust_dashboard.launch_dashboard import RustDashboard
from rust_ocr import start_ocr_thread

CSV_PATH = Path("mute_list.csv")
DATA_JSON = Path("player_data.json")

# --- Ensure CSV exists with correct lowercase columns ---
if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
    print(f"[INFO] Created {CSV_PATH}")

# --- Ensure JSON exists ---
if not DATA_JSON.exists() or DATA_JSON.stat().st_size == 0:
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump({}, f)
    print(f"[INFO] Created empty {DATA_JSON}")

# --- Suppress Matplotlib warnings globally ---
warnings.simplefilter("ignore", category=UserWarning)

import csv
import os
import subprocess
from pathlib import Path
from PySide6.QtCore import QTimer, QObject

CSV_PATH = Path("mute_list.csv")

class DashboardUpdater(QObject):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.last_json_mtime = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_json)
        self.timer.start(1000)  # check every second

    def check_json(self):
        try:
            if DATA_JSON.exists():
                mtime = DATA_JSON.stat().st_mtime
                if mtime != self.last_json_mtime:
                    self.last_json_mtime = mtime
                    print("[Watcher] JSON changed → refreshing dashboard...")
                    self.dashboard.refresh_data()
        except Exception as e:
            print("[Watcher] Error:", e)


    def check_csv(self):
        try:
            if CSV_PATH.exists():
                size = CSV_PATH.stat().st_size
                if size != self.last_csv_size:
                    self.last_csv_size = size
                    print("[Watcher] CSV updated → Running getPlayerData.py...")

                    # Run getPlayerData.py
                    result = subprocess.run(
                        ["python", "getPlayerData.py"],
                        capture_output=True,
                        text=True
                    )

                    if result.returncode == 0:
                        print("[Watcher] getPlayerData.py finished successfully")
                    else:
                        print("[Watcher] getPlayerData.py ERROR")
                        print(result.stdout)
                        print(result.stderr)

                    # Refresh dashboard immediately
                    self.dashboard.refresh_data()
        except Exception as e:
            print("[Watcher] Error:", e)



if __name__ == "__main__":
    app = QApplication([])

    # Start OCR thread
    threading.Thread(target=start_ocr_thread, daemon=True).start()

    # Launch dashboard after files are ready
    dashboard = RustDashboard()
    dashboard.show()

    # Start CSV watcher thread
    DashboardUpdater(dashboard)

    sys.exit(app.exec())
