import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from data_loader import load_data
from tabs.leaderboard import LeaderboardTab
from tabs.table import TableTab
from tabs.search import SearchTab
from tabs.charts import ChartsTab
from tabs.dashboard import DashboardTab
import os
os.environ["STREAMLIT_SUPPRESS_OUTPUT_WARNING"] = "1"

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

        self.tabs = {
            "Dashboard": DashboardTab(self.df),
            "Leaderboard": LeaderboardTab(self.df),
            "Table": TableTab(self.df),
            "Search": SearchTab(self.df),
            "Charts": ChartsTab(self.df)
        }

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

    def load_tab(self, widget):
        for i in reversed(range(self.content_layout.count())):
            w = self.content_layout.itemAt(i).widget()
            if w:
                w.setParent(None)
        self.content_layout.addWidget(widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply global styling
    app.setStyleSheet("""
        QWidget {
            background-color: #2C2F33;
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
        }
        QPushButton {
            background-color: #23272A;
            border-radius: 8px;
            padding: 10px;
            color: #FFFFFF;
        }
        QPushButton:hover {
            background-color: #7289DA;
        }
        QTableWidget {
            background-color: #2C2F33;
            gridline-color: #99AAB5;
            color: #FFFFFF;
            font-size: 13px;
        }
        QHeaderView::section {
            background-color: #23272A;
            color: #FFFFFF;
            padding: 4px;
            border: none;
        }
        QScrollBar:vertical {
            background-color: #23272A;
            width: 12px;
            margin: 0px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #7289DA;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            height: 0;
        }
    """)

    dashboard = RustDashboard()
    dashboard.show()
    sys.exit(app.exec())

