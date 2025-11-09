from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QLineEdit, QLabel
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QCursor, QColor
import webbrowser

class TableTab(QWidget):
    def __init__(self, df):
        super().__init__()
        self.df = df
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #1E1E1E; color: #CCCCCC; font-family: 'Segoe UI', sans-serif; }
            QLineEdit {
                background-color: #252526; border: 1px solid #3C3C3C; border-radius: 4px;
                padding: 8px; font-size: 14px; color: #FFFFFF;
            }
            QLineEdit:focus { border: 1px solid #007ACC; }
            QTableWidget {
                background-color: #1E1E1E; color: #CCCCCC; gridline-color: #3C3C3C;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #252526; color: #FFFFFF; padding: 4px; border: none;
            }
            QScrollBar:vertical {
                background-color: #1E1E1E; width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #007ACC; min-height: 20px; border-radius: 5px;
            }
        """)

        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search player...")
        layout.addWidget(self.search)

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)  # enable sorting
        self.table.setMouseTracking(True)   # track hover
        layout.addWidget(self.table)

        # Signals
        self.search.textChanged.connect(self.update_table)
        self.table.cellClicked.connect(self.copy_cell_or_open_link)
        self.table.cellEntered.connect(self.update_hover_cursor)

        self.update_table()

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

    def update_table(self):
        text = self.search.text().lower()
        filtered = self.df[
            self.df["name"].str.lower().str.contains(text) |
            self.df["steam_id"].str.contains(text)
        ]

        # Only 4 columns
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Total Hours", "2 Weeks", "Profile"])
        self.table.setRowCount(len(filtered))

        for i, row in enumerate(filtered.itertuples()):
            items = [
                row.name,
                f"{row.rust_hours_total} h",
                f"{row.rust_hours_2weeks} h",
                f"https://steamcommunity.com/profiles/{row.steam_id}"
            ]
            for col, text_val in enumerate(items):
                item = QTableWidgetItem(text_val)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(i, col, item)
                # Set color for link
                if col == 3:
                    item.setForeground(QColor("#007ACC"))
                else:
                    item.setData(Qt.UserRole, text_val)

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

    def update_hover_cursor(self, row, col):
        """Set cursor based on column hover."""
        if col == 3:
            self.table.viewport().setCursor(QCursor(Qt.PointingHandCursor))
        else:
            # Use standard copy cursor (ArrowCursor) because PySide6 does not have a dedicated copy cursor
            self.table.viewport().setCursor(QCursor(Qt.IBeamCursor))
