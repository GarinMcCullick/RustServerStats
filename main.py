import threading
import time
import subprocess
from pathlib import Path

from rust_dashboard.dashboard import launch_dashboard, dashboard_update_event

CSV_PATH = Path("mute_list.csv")
DATA_JSON = Path("player_data.json")

# ---- WATCH CSV FOR CHANGES ---- #
def watch_csv_loop():
    last_size = 0
    while True:
        try:
            if CSV_PATH.exists():
                size = CSV_PATH.stat().st_size
                if size != last_size:
                    last_size = size
                    print("[Orchestrator] Detected CSV update → Running data fetcher...")

                    subprocess.run(
                        ["python", "getPlayerData.py"],
                        check=False
                    )

                    dashboard_update_event.set()
        except Exception as e:
            print("Watcher error:", e)

        time.sleep(1)

# ---- RUN OCR HOTKEY SCRIPT ---- #
def start_ocr():
    subprocess.run(
        ["python", "ocr.py"],
        check=False
    )

def main():
    threading.Thread(target=watch_csv_loop, daemon=True).start()
    threading.Thread(target=start_ocr, daemon=True).start()
    launch_dashboard(DATA_JSON)

if __name__ == "__main__":
    main()
