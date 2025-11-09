import json
import sys
import webbrowser
import pandas as pd
import matplotlib.pyplot as plt

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QLineEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# ---------------- CONFIG ---------------- #
JSON_FILE = "playerData.json"

# Load data
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
df["rust_hours_total"] = pd.to_numeric(df["rust_hours_total"])
df["rust_hours_2weeks"] = pd.to_numeric(df["rust_hours_2weeks"])

# ---------------- DASHBOARD ---------------- #
class RustDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rust Player Stats Dashboard")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet("background-color: #2C2F33; color: #FFFFFF; font-family: 'Segoe UI';")

        # Layouts
        self.main_layout = QHBoxLayout(self)
        self.sidebar_layout = QVBoxLayout()
        self.content_layout = QVBoxLayout()

        self.main_layout.addLayout(self.sidebar_layout, 1)
        self.main_layout.addLayout(self.content_layout, 4)

        # Sidebar buttons
        self.btn_leaderboard = QPushButton("Leaderboard")
        self.btn_charts = QPushButton("Charts")
        self.btn_table = QPushButton("Full Table")
        self.btn_search = QPushButton("Search Player")

        for btn in [self.btn_leaderboard, self.btn_charts, self.btn_table, self.btn_search]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #23272A;
                    border-radius: 8px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #7289DA;
                }
            """)
            self.sidebar_layout.addWidget(btn)

        self.sidebar_layout.addStretch()

        # Connect buttons
        self.btn_leaderboard.clicked.connect(self.show_leaderboard)
        self.btn_charts.clicked.connect(self.show_charts)
        self.btn_table.clicked.connect(self.show_table)
        self.btn_search.clicked.connect(self.show_search)

        # Content placeholder
        self.content_frame = QFrame()
        self.content_layout.addWidget(self.content_frame)

        self.show_leaderboard()  # default view

    # ---------------- VIEWS ---------------- #
    def clear_content(self):
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def show_leaderboard(self):
        self.clear_content()
        frame = QFrame()
        layout = QVBoxLayout(frame)

        title = QLabel("Top 10 Players by Total Hours")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        table = QTableWidget()
        top10 = df.sort_values("rust_hours_total", ascending=False).head(10)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Name", "Total Hours", "2 Weeks Hours", "Profile"])
        table.setRowCount(len(top10))
        table.setStyleSheet("background-color: #23272A; color: #FFFFFF;")
        table.verticalHeader().setVisible(False)

        for i, row in enumerate(top10.itertuples()):
            table.setItem(i, 0, QTableWidgetItem(row.name))
            table.setItem(i, 1, QTableWidgetItem(str(row.rust_hours_total)))
            table.setItem(i, 2, QTableWidgetItem(str(row.rust_hours_2weeks)))
            link_item = QTableWidgetItem(f"https://steamcommunity.com/profiles/{row.steam_id}")
            table.setItem(i, 3, link_item)

        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(table)
        self.content_layout.addWidget(frame)

    def show_charts(self):
        self.clear_content()
        frame = QFrame()
        layout = QVBoxLayout(frame)

        # Top 10 Total Hours
        fig, ax = plt.subplots(figsize=(8,4))
        top10 = df.sort_values("rust_hours_total", ascending=False).head(10)
        ax.barh(top10["name"], top10["rust_hours_total"], color="#7289DA")
        ax.set_xlabel("Total Hours")
        ax.set_title("Top 10 Players by Total Hours")
        ax.invert_yaxis()
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        # Top 10 2-weeks Hours
        fig2, ax2 = plt.subplots(figsize=(8,4))
        top10_2w = df.sort_values("rust_hours_2weeks", ascending=False).head(10)
        ax2.barh(top10_2w["name"], top10_2w["rust_hours_2weeks"], color="#99AAB5")
        ax2.set_xlabel("2-Weeks Hours")
        ax2.set_title("Top 10 Players by 2 Weeks Hours")
        ax2.invert_yaxis()
        canvas2 = FigureCanvas(fig2)
        layout.addWidget(canvas2)

        self.content_layout.addWidget(frame)

    def show_table(self):
        self.clear_content()
        frame = QFrame()
        layout = QVBoxLayout(frame)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Name", "Total Hours", "2 Weeks Hours", "Private", "Profile"])
        table.setRowCount(len(df))
        table.setStyleSheet("background-color: #23272A; color: #FFFFFF;")
        table.verticalHeader().setVisible(False)

        for i, row in enumerate(df.itertuples()):
            table.setItem(i, 0, QTableWidgetItem(row.name))
            table.setItem(i, 1, QTableWidgetItem(str(row.rust_hours_total)))
            table.setItem(i, 2, QTableWidgetItem(str(row.rust_hours_2weeks)))
            table.setItem(i, 3, QTableWidgetItem(str(row.flags["private_profile"])))
            table.setItem(i, 4, QTableWidgetItem(f"https://steamcommunity.com/profiles/{row.steam_id}"))

        table.resizeColumnsToContents()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        scroll = QScrollArea()
        scroll.setWidget(table)
        scroll.setWidgetResizable(True)
        layout.addWidget(table)

        self.content_layout.addWidget(frame)

    def show_search(self):
        self.clear_content()
        frame = QFrame()
        layout = QVBoxLayout(frame)

        search_label = QLabel("Search Player by Name or SteamID:")
        layout.addWidget(search_label)

        search_input = QLineEdit()
        layout.addWidget(search_input)

        result_label = QLabel("")
        layout.addWidget(result_label)

        def search():
            text = search_input.text().lower()
            matches = df[df["name"].str.lower().str.contains(text) | df["steam_id"].str.contains(text)]
            if matches.empty:
                result_label.setText("No matches found.")
            else:
                results = []
                for row in matches.itertuples():
                    results.append(f"{row.name} | Total: {row.rust_hours_total}h | 2w: {row.rust_hours_2weeks}h | Profile: https://steamcommunity.com/profiles/{row.steam_id}")
                result_label.setText("\n".join(results))

        search_input.textChanged.connect(search)
        self.content_layout.addWidget(frame)


# ---------------- RUN ---------------- #
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = RustDashboard()
    dashboard.show()
    sys.exit(app.exec())
