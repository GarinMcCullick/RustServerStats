import sys
import threading
from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtCore import QTimer
from rust_dashboard.data_loader import load_data
from rust_dashboard.tabs.leaderboard import LeaderboardTab
from rust_dashboard.tabs.table import TableTab
from rust_dashboard.tabs.search import SearchTab
from rust_dashboard.tabs.charts import ChartsTab
from rust_dashboard.tabs.dashboard import DashboardTab
from rust_dashboard.tabs.flagged import FlaggedWatcherTab

from rust_dashboard.jsonwatcher import JSONWatcher

import keyboard
import subprocess
import os
import time

os.environ["STREAMLIT_SUPPRESS_OUTPUT_WARNING"] = "1"

CSV_PATH = Path("mute_list.csv")
JSON_PATH = Path("player_data.json")


class RustDashboard(QWidget):
    def __init__(self):
        super().__init__()

        self.df = load_data()
        self.setWindowTitle("Rust Dashboard")
        self.setMinimumSize(1200, 700)
        self.setStyleSheet("background-color: #2C2F33; color: #FFFFFF; font-family: 'Segoe UI';")

        self.main_layout = QHBoxLayout(self)
        self.sidebar_layout = QVBoxLayout()
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.sidebar_layout, 1)
        self.main_layout.addLayout(self.content_layout, 4)

        # Tabs
        self.tabs = {
            "Dashboard": DashboardTab(self.df),
            "Leaderboard": LeaderboardTab(self.df),
            "Flagged": FlaggedWatcherTab(),
            "Table": TableTab(self.df),
            "Search": SearchTab(self.df),
            "Charts": ChartsTab(self.df)
        }

        # Connect TableTab's flag signal to method
        if hasattr(self.tabs["Table"], "flagUpdated"):
            self.tabs["Table"].flagUpdated.connect(self.on_flag_updated)

        # Sidebar buttons
        for name in self.tabs.keys():
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #23272A;
                    border-radius: 8px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #7289DA;
                }
            """)
            btn.clicked.connect(lambda checked, n=name: self.load_tab(self.tabs[n]))
            self.sidebar_layout.addWidget(btn)

        self.sidebar_layout.addStretch()
        self.load_tab(self.tabs["Dashboard"])

        # OCR hotkeys
        self.running = False
        self.final_results = {}
        keyboard.add_hotkey("F8", self.start_capture)
        keyboard.add_hotkey("F9", self.stop_capture)

        # JSON Watcher
        self.watcher = JSONWatcher(
            dashboard=self,
            tabs=[
                self.tabs["Search"],
                self.tabs["Table"],
                self.tabs["Leaderboard"],
                self.tabs["Charts"],
                self.tabs["Dashboard"],
            ]
        )

    # ---------------- Flag handling ---------------- #
    def on_flag_updated(self, steam_id: str, flagged: bool):
        """Called when a player is flagged/unflagged in the Table tab."""
        flagged_tab = self.tabs["Flagged"]
        print(f"[FlaggedWatcher] Player {steam_id} flagged={flagged} — refreshing table...")
        flagged_tab.refresh_flagged_status()

    # ---------------- TAB LOADING ---------------- #
    def load_tab(self, widget):
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        self.content_layout.addWidget(widget)

    # ---------------- DASHBOARD REFRESH ---------------- #
    def refresh_data(self, df):
        self.df = df.copy()
        for tab in self.tabs.values():
            if hasattr(tab, "refresh_data"):
                tab.refresh_data(self.df)
            elif hasattr(tab, "update_data"):
                tab.update_data(self.df)
        if self.content_layout.count() > 0:
            widget = self.content_layout.itemAt(0).widget()
            if hasattr(widget, "refresh_data"):
                widget.refresh_data(self.df)
        print("[+] Dashboard and all tabs refreshed")

    # ---------------- OCR CAPTURE SYSTEM ---------------- #
    def capture_loop(self):
        from rust_ocr import capture_region, preprocess, split_columns, ocr_image, parse_ocr, SAVE_CSV
        import csv

        print("\n[+] Capture started — scroll the mute list in Rust...\n")
        while self.running:
            img = capture_region()
            img = preprocess(img)
            left_img, right_img = split_columns(img)
            left_lines = ocr_image(left_img, psm=6)
            right_lines = ocr_image(right_img, psm=4)
            left_entries = parse_ocr(left_lines)
            right_entries = parse_ocr(right_lines)

            for name, sid in left_entries + right_entries:
                if sid not in self.final_results:
                    self.final_results[sid] = name
                    print(f"[CAPTURED] {name} — {sid}")

            time.sleep(0.15)

        with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "steamid", "profile_url"])
            for sid, name in self.final_results.items():
                writer.writerow([name, sid, f"https://steamcommunity.com/profiles/{sid}"])

        print(f"\n[+] OCR capture stopped. Saved {len(self.final_results)} entries to {SAVE_CSV}")

        try:
            print("[+] Triggering getPlayerData.py to fetch player data...")
            subprocess.Popen(["python", "getPlayerData.py"])
        except Exception as e:
            print(f"[!] Failed to run getPlayerData.py: {e}")

    def start_capture(self):
        if not self.running:
            self.running = True
            threading.Thread(target=self.capture_loop, daemon=True).start()

    def stop_capture(self):
        self.running = False
