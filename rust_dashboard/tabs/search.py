from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QFrame,
    QScrollArea, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
import pandas as pd
import json
from pathlib import Path

DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")

class SearchTab(QWidget):
    def __init__(self, df=None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.init_ui()
        self.start_json_watcher()

    # Called when JSON updates
    def refresh_data(self, df):
        """Update tab with new data."""
        self.df = df.copy()
        self.update_results()

    def start_json_watcher(self):
        """Watch JSON file and refresh automatically."""
        self.last_mtime = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_json)
        self.timer.start(1000)  # every second

    def check_json(self):
        try:
            if DATA_JSON.exists():
                mtime = DATA_JSON.stat().st_mtime
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    with open(DATA_JSON, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    df = pd.DataFrame(data)
                    # Ensure essential columns exist
                    for col in ["rust_hours_total", "rust_hours_2weeks", "flags"]:
                        if col not in df.columns:
                            df[col] = 0 if "hours" in col else [{}]
                    self.refresh_data(df)
        except Exception as e:
            print("[Watcher] Error:", e)

    def show_copied_message(self, parent_widget):
        msg = QLabel("Copied!", parent_widget)
        msg.setStyleSheet("""
            QLabel {
                background-color: #007ACC;
                color: #FFFFFF;
                border-radius: 5px;
                padding: 4px 8px;
                font-weight: bold;
            }
        """)
        msg.setAttribute(Qt.WA_TransparentForMouseEvents)
        msg.setAlignment(Qt.AlignCenter)

        # Center the label on parent
        msg.adjustSize()
        x = (parent_widget.width() - msg.width()) // 2
        y = (parent_widget.height() - msg.height()) // 2
        msg.move(x, y)
        msg.show()

        QTimer.singleShot(1000, msg.deleteLater)

    def copy_text(self, label):
        QGuiApplication.clipboard().setText(label.text())
        self.show_copied_message(label)

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; color: #CCCCCC; font-family: 'Segoe UI', sans-serif; }
            QLineEdit {
                background-color: #252526; border: 1px solid #3C3C3C; border-radius: 4px;
                padding: 8px; font-size: 14px; color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #007ACC; }
            QLabel { font-size: 13px; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search player by name or SteamID")
        main_layout.addWidget(self.search_input)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; }
            QScrollBar:vertical {
                background-color: #1E1E1E; width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #007ACC; min-height: 20px; border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.scroll_area)

        # Container inside scroll area
        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(6)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.container_widget)

        # Header (persistent)
        self.header_frame = QFrame()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(5, 5, 5, 5)
        header_layout.setSpacing(0)
        headers = ["Name", "SteamID", "Total Hours", "Last 2 Weeks", "Profile"]
        widths = [250, 200, 120, 120, 150]
        for h, w in zip(headers, widths):
            lbl = QLabel(h)
            lbl.setStyleSheet("font-weight:bold; color:#CCCCCC;")
            lbl.setFixedWidth(w)
            header_layout.addWidget(lbl)
        header_layout.addStretch()
        self.header_frame.setLayout(header_layout)
        self.container_layout.addWidget(self.header_frame)

        # Results layout
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(6)
        self.results_layout.setAlignment(Qt.AlignTop)
        self.container_layout.addLayout(self.results_layout)

        # Connect search
        self.search_input.textChanged.connect(self.update_results)

        # Initial populate
        self.update_results()

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def update_results(self):
        self.clear_results()
        text = self.search_input.text().lower() if self.search_input.text() else ""
        if self.df.empty:
            return

        # Add missing columns to avoid errors
        for col in ["rust_hours_total", "rust_hours_2weeks"]:
            if col not in self.df.columns:
                self.df[col] = 0

        matches = self.df[
            self.df["name"].str.lower().str.contains(text) |
            self.df["steam_id"].astype(str).str.contains(text)
        ]

        for row in matches.itertuples():
            row_frame = QFrame()
            row_frame.setFixedHeight(30)
            row_frame.setStyleSheet("""
                QFrame { background-color: #252526; border: 1px solid #3C3C3C; border-radius: 4px; }
                QFrame:hover { background-color: #2A2D2E; }
            """)

            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(5, 5, 5, 5)

            labels = [
                QLabel(row.name),
                QLabel(str(row.steam_id)),
                QLabel(f"{row.rust_hours_total} h"),
                QLabel(f"{row.rust_hours_2weeks} h"),
                QLabel(f"<a href='https://steamcommunity.com/profiles/{row.steam_id}'>Link</a>")
            ]
            widths = [250, 200, 120, 120, 150]

            for idx, (lbl, w) in enumerate(zip(labels, widths)):
                lbl.setFixedWidth(w)

                if idx == len(labels) - 1:  # last column = link
                    lbl.setTextFormat(Qt.TextFormat.RichText)
                    lbl.setOpenExternalLinks(True)
                    lbl.setCursor(QCursor(Qt.PointingHandCursor))
                else:
                    lbl.setCursor(QCursor(Qt.PointingHandCursor))
                    lbl.mousePressEvent = lambda e, l=lbl: self.copy_text(l)

                row_layout.addWidget(lbl)

            row_layout.addStretch()
            row_frame.setLayout(row_layout)
            self.results_layout.addWidget(row_frame)
