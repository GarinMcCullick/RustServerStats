from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QFrame,
    QScrollArea, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication

class SearchTab(QWidget):
    def __init__(self, df):
        super().__init__()
        self.df = df
        self.init_ui()

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

        # Position the label centered on the parent widget
        msg.adjustSize()
        x = (parent_widget.width() - msg.width()) // 2
        y = (parent_widget.height() - msg.height()) // 2
        msg.move(x, y)
        msg.show()

        # Auto-hide after 1 second
        QTimer.singleShot(1000, msg.deleteLater)

    def copy_text(self, label):
        from PySide6.QtGui import QGuiApplication
        # Copy text to clipboard
        QGuiApplication.clipboard().setText(label.text())
        # Show modern "Copied!" message on label
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

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

    def update_results(self):
        self.clear_results()
        text = self.search_input.text().lower()
        matches = self.df[
            self.df["name"].str.lower().str.contains(text) |
            self.df["steam_id"].str.contains(text)
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
                QLabel(row.steam_id),
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
                else:  # text columns
                    lbl.setCursor(QCursor(Qt.PointingHandCursor))
                    lbl.mousePressEvent = lambda e, l=lbl: self.copy_text(l)

                row_layout.addWidget(lbl)

            row_layout.addStretch()
            row_frame.setLayout(row_layout)
            self.results_layout.addWidget(row_frame)
