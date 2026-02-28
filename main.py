import sys
import threading
import subprocess
import warnings
import json
import csv
from pathlib import Path
from datetime import datetime
from functools import partial
import keyboard

from PySide6.QtCore import Qt, QTimer, QObject, Signal
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QLabel, QCheckBox
from PySide6.QtGui import QGuiApplication, QCursor, QColor
from rust_dashboard.overlay import InGameOverlay
from rust_ocr import capture_loop
from rust_ocr import OCRDebugOverlay

# ========================================================
# FILE PATHS
# ========================================================
CSV_PATH = Path("mute_list.csv")
DATA_JSON = Path("player_data.json")

# ========================================================
# INITIALIZE FILES IF MISSING
# ========================================================
if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
    print(f"[INFO] Created {CSV_PATH}")

if not DATA_JSON.exists() or DATA_JSON.stat().st_size == 0:
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump([], f)
    print(f"[INFO] Created empty {DATA_JSON}")

warnings.simplefilter("ignore", category=UserWarning)

# ========================================================
# TABLE TAB
# ========================================================
class TableTab(QWidget):
    flagUpdated = Signal(str, bool)  # steam_id, new_flag_value

    def __init__(self, df=None):
        super().__init__()
        self.df = df.copy() if df is not None else None
        self._suppress_checkbox = False
        self._suppress_watcher = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or SteamID")
        self.search.textChanged.connect(self.update_table)
        layout.addWidget(self.search)

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.cellClicked.connect(self.copy_cell_or_open_link)
        self.table.cellEntered.connect(self.update_hover_cursor)
        layout.addWidget(self.table)

        self.update_table()

    def update_data(self, df):
        """Called by DashboardUpdater on JSON changes"""
        if self._suppress_watcher:
            return
        if df is not None:
            self.df = df.copy()
            self.update_table()

    def update_table(self):
        if self.df is None or self.df.empty:
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
                else:
                    item.setData(Qt.UserRole, val)
                self.table.setItem(i, col, item)

            # Flag checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(self.is_flagged(row.steam_id))
            checkbox.stateChanged.connect(partial(self.toggle_flag, row.steam_id))
            self.table.setCellWidget(i, 4, checkbox)

    def is_flagged(self, steam_id):
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data:
                if p.get("steam_id") == steam_id:
                    return p.get("flags", {}).get("flagged", False)
        except Exception:
            pass
        return False

    def toggle_flag(self, steam_id, state):
        """User toggles a checkbox"""
        if self._suppress_checkbox:
            return

        flagged = state == Qt.Checked

        # Temporarily suppress watcher refresh
        self._suppress_watcher = True
        QTimer.singleShot(500, lambda: setattr(self, "_suppress_watcher", False))

        # Update JSON
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = []

        found = False
        for p in data:
            if p.get("steam_id") == steam_id:
                p.setdefault("flags", {})
                p["flags"]["flagged"] = flagged
                if flagged:
                    p["flags"]["flagged_at"] = datetime.utcnow().isoformat()
                else:
                    p["flags"].pop("flagged_at", None)
                found = True
                break

        if not found:
            data.append({
                "steam_id": steam_id,
                "name": "Unknown",
                "flags": {
                    "flagged": flagged,
                    "flagged_at": datetime.utcnow().isoformat() if flagged else None,
                    "private_profile": True
                }
            })

        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # Update DataFrame immediately
        if "steam_id" in self.df.columns:
            self.df.loc[self.df["steam_id"] == steam_id, "flags"] = self.df.get("flags", [{}])
            if "flagged" in self.df.columns:
                self.df.loc[self.df["steam_id"] == steam_id, "flagged"] = flagged

        # Emit signal to refresh Flagged tab
        self.flagUpdated.emit(steam_id, flagged)

    def copy_cell_or_open_link(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return
        if col == 3:
            import webbrowser
            webbrowser.open(item.text())
        else:
            QGuiApplication.clipboard().setText(item.text())

    def update_hover_cursor(self, row, col):
        if col == 3:
            self.table.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.table.viewport().setCursor(Qt.IBeamCursor)


# ========================================================
# DASHBOARD FILE WATCHER
# ========================================================
class DashboardUpdater(QObject):
    """Watches JSON and CSV files and refreshes dashboard/tabs."""

    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.last_json_mtime = 0
        self.last_csv_size = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_files)
        self.timer.start(1000)

    def check_files(self):
        self.check_json()
        self.check_csv()

    def check_json(self):
        if not DATA_JSON.exists():
            return

        mtime = DATA_JSON.stat().st_mtime
        if mtime == self.last_json_mtime:
            return
        self.last_json_mtime = mtime

        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[Watcher] JSON changed → refreshing dashboard + tabs ({len(data)} players)")
            if hasattr(self.dashboard, "table_tab") and not getattr(self.dashboard.table_tab, "_suppress_watcher", False):
                self.dashboard.refresh_data(data)
        except Exception as e:
            print("[Watcher] JSON load error:", e)

    def check_csv(self):
        if not CSV_PATH.exists():
            return

        size = CSV_PATH.stat().st_size
        if size == self.last_csv_size:
            return
        self.last_csv_size = size

        print("[Watcher] CSV updated → running getPlayerData.py...")
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

        # Refresh JSON after CSV
        self.check_json()

# ========================================================
# MAIN APPLICATION
# ========================================================
if __name__ == "__main__":
    app = QApplication([])

    # --- Ensure global running exists ---
    running = False

    # --- Controller ---
    class OCRController:
        def __init__(self):
            self.running = False

        def start_capture(self):
            if not self.running:
                self.running = True
                threading.Thread(target=capture_loop, args=(self,), daemon=True).start()
                print("[Overlay] Start OCR (button)")
            else:
                print("[Overlay] OCR already running")

        def stop_capture(self):
            if self.running:
                self.running = False
                print("[Overlay] Stop OCR (button)")
            else:
                print("[Overlay] OCR not running")

    # --- Create overlay and controller ---
    ocr_controller = OCRController()
    # --- Overlay ---
    overlay = InGameOverlay(ocr_controller)
    overlay.start_btn.clicked.connect(ocr_controller.start_capture)
    overlay.stop_btn.clicked.connect(ocr_controller.stop_capture)
    overlay.show()
    overlay.run_script(["python", "getPlayerData.py"])

    # --- Debug overlay ---
    LEFT, TOP, RIGHT, BOTTOM = 380, 285, 1600, 1000
    OVERLAP_PIXELS = 4
    ocr_regions = [
        (LEFT, TOP, LEFT + (RIGHT-LEFT)//3 + OVERLAP_PIXELS, BOTTOM),
        (LEFT + (RIGHT-LEFT)//3 - OVERLAP_PIXELS, TOP, RIGHT, BOTTOM)
    ]
    debug_overlay = OCRDebugOverlay(ocr_regions)
    debug_overlay.hide()

    # --- Overlay Controller ---
    class OverlayController(QObject):
        toggle_signal = Signal(bool)
        def __init__(self, overlay):
            super().__init__()
            self.overlay = overlay
            self.toggle_signal.connect(self.overlay.setVisible)

        def toggle(self, visible: bool):
            self.toggle_signal.emit(visible)

    overlay_controller = OverlayController(debug_overlay)

    # --- Hotkey functions ---
    def start_capture():
        ocr_controller.start_capture()
        overlay_controller.toggle(True)
        debug_overlay.show()

    def stop_capture():
        ocr_controller.stop_capture()
        overlay_controller.toggle(False)
        debug_overlay.hide()

    # --- Hotkeys ---
    overlay.start_btn.clicked.connect(start_capture)
    overlay.stop_btn.clicked.connect(stop_capture)
    keyboard.add_hotkey("F8", start_capture)
    keyboard.add_hotkey("F9", stop_capture)
    keyboard.add_hotkey("F10", lambda: os._exit(0))

    class StreamRedirector:
        def __init__(self, overlay):
            self.overlay = overlay

        def write(self, text):
            if text.strip():  # avoid blank lines
                self.overlay.log(text)

        def flush(self):
            pass  # required for file-like objects

    # Redirect stdout/stderr to overlay
    sys.stdout = StreamRedirector(overlay)
    sys.stderr = StreamRedirector(overlay)

    # Launch dashboard
    from rust_dashboard.launch_dashboard import RustDashboard
    dashboard = RustDashboard()
    dashboard.show()

    # Start file watcher
    DashboardUpdater(dashboard)

    sys.exit(app.exec())