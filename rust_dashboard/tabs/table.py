from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QCursor, QColor
import pandas as pd
import webbrowser

class TableTab(QWidget):
    def __init__(self, df=None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.init_ui()  # create widgets and layout

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; color: #CCCCCC; font-family: 'Segoe UI'; }
            QLineEdit {
                background-color: #252526;
                border: 1px solid #3C3C3C;
                border-radius: 4px;
                padding: 8px;
                font-size: 14px;
                color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #007ACC; }
            QTableWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                gridline-color: #3C3C3C;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #252526;
                color: #FFFFFF;
                padding: 4px;
                border: 0;
            }
            QTableWidget::item:hover { background-color: #2A2D2E; }
            QScrollBar:vertical {
                background-color: #1E1E1E;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #007ACC;
                min-height: 20px;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Search box
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search player by name or SteamID")
        self.search.textChanged.connect(self.update_table)
        layout.addWidget(self.search)

        # Table
        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setMouseTracking(True)
        self.table.cellClicked.connect(self.copy_cell_or_open_link)
        self.table.cellEntered.connect(self.update_hover_cursor)
        layout.addWidget(self.table)

        # Initial populate
        self.update_table()

    def update_data(self, df):
        """Update DataFrame and refresh table immediately."""
        if df is not None:
            self.df = df.copy()
            self.update_table()

    def update_table(self):
        if self.df.empty:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        df_public = self.df[self.df.get("private_profile", False) == False]
        text = self.search.text().lower()
        filtered = df_public[
            df_public["name"].str.lower().str.contains(text) |
            df_public["steam_id"].str.contains(text)
        ]

        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Total Hours", "2 Weeks", "Profile"])
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

        self.table.resizeColumnsToContents()

    def copy_cell_or_open_link(self, row, col):
        item = self.table.item(row, col)
        if not item:
            return
        if col == 3:
            webbrowser.open(item.text())
        else:
            QGuiApplication.clipboard().setText(item.text())
            self.show_copied_message(self.table.viewport())

    def show_copied_message(self, parent_widget):
        msg = QLabel("Copied!", parent_widget)
        msg.setStyleSheet("""
            QLabel {
                background-color: #007ACC;
                color: #FFFFFF;
                border-radius: 5px;
                padding: 2px 6px;
                font-weight: bold;
            }
        """)
        msg.setAttribute(Qt.WA_TransparentForMouseEvents)
        msg.setAlignment(Qt.AlignCenter)
        msg.adjustSize()
        x = (parent_widget.width() - msg.width()) // 2
        y = (parent_widget.height() - msg.height()) // 2
        msg.move(x, y)
        msg.show()
        QTimer.singleShot(1000, msg.deleteLater)

    def update_hover_cursor(self, row, col):
        if col == 3:
            self.table.viewport().setCursor(QCursor(Qt.PointingHandCursor))
        else:
            self.table.viewport().setCursor(QCursor(Qt.IBeamCursor))
