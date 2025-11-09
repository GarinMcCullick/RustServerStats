from PySide6.QtWidgets import (
    QWidget, QGridLayout, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QVBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication
import webbrowser

class LeaderboardTab(QWidget):
    def __init__(self, df):
        super().__init__()
        self.df = df
        self.init_ui()

    def init_ui(self):
        grid = QGridLayout(self)
        grid.setSpacing(30)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setAlignment(Qt.AlignCenter)

        # Top-left: Lowest Total Hours (exclude 0)
        low_total_df = self.df[self.df['rust_hours_total'] > 0].sort_values('rust_hours_total').head(10)
        self.table_low_total = self.create_table(low_total_df, "Lowest Total Hours")
        grid.addWidget(self.table_low_total, 0, 0, alignment=Qt.AlignCenter)

        # Top-right: Highest Total Hours
        high_total_df = self.df.sort_values('rust_hours_total', ascending=False).head(10)
        self.table_high_total = self.create_table(high_total_df, "Highest Total Hours")
        grid.addWidget(self.table_high_total, 0, 1, alignment=Qt.AlignCenter)

        # Bottom-left: Last 2 Weeks – Highest Hours
        last2w_high_df = self.df.sort_values('rust_hours_2weeks', ascending=False).head(10)
        self.table_last2w_high = self.create_table(last2w_high_df, "Last 2 Weeks – Highest Hours")
        grid.addWidget(self.table_last2w_high, 1, 0, alignment=Qt.AlignCenter)

        # Bottom-right: Last 2 Weeks – Lowest Hours (exclude 0)
        last2w_low_df = self.df[self.df['rust_hours_2weeks'] > 0].sort_values('rust_hours_2weeks').head(10)
        self.table_last2w_low = self.create_table(last2w_low_df, "Last 2 Weeks – Lowest Hours")
        grid.addWidget(self.table_last2w_low, 1, 1, alignment=Qt.AlignCenter)

    def create_table(self, df_subset, title):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(5)
        v_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Title label
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#FFFFFF; font-weight:bold; font-size:14px;")
        title_lbl.setAlignment(Qt.AlignCenter)
        v_layout.addWidget(title_lbl)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Rank", "Name", "Total Hours", "2 Weeks", "Profile"])
        table.setRowCount(len(df_subset))
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setFocusPolicy(Qt.NoFocus)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setFixedHeight(30 * 10 + 30)  # 10 rows + header
        table.setFixedWidth(int(900 * 0.48))  # 20% narrower

        table.setStyleSheet("""
            QTableWidget { background-color: #1E1E1E; color: #CCCCCC; gridline-color: #3C3C3C; }
            QHeaderView::section { background-color: #252526; color: #FFFFFF; padding: 6px; border: none; }
            QTableWidget::item { padding-left: 12px; padding-right: 12px; }
            QTableWidget::item:hover { background-color: #2A2D2E; }
        """)

        # Populate table
        for i, row in enumerate(df_subset.itertuples()):
            # Rank
            rank_item = QTableWidgetItem(str(i + 1))
            rank_item.setForeground(QColor("#FFD700") if i == 0 else QColor("#CCCCCC"))
            rank_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, rank_item)

            # Name, Total Hours, 2 Weeks
            for col_val, col_idx in zip(
                [row.name, f"{row.rust_hours_total} h", f"{row.rust_hours_2weeks} h"],
                [1, 2, 3]
            ):
                item = QTableWidgetItem(col_val)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, col_idx, item)

            # Profile column (left-aligned)
            profile_item = QTableWidgetItem("Link")
            profile_item.setForeground(QColor("#007ACC"))
            profile_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            profile_item.setToolTip(f"https://steamcommunity.com/profiles/{row.steam_id}")
            table.setItem(i, 4, profile_item)

        # Resize columns: first 4 to contents, Profile column stretches
        for col in range(4):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        table.horizontalHeaderItem(4).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # left-align header

        table.cellClicked.connect(lambda r, c, tbl=table, df=df_subset: self.handle_click(tbl, r, c, df))
        table.viewport().setCursor(QCursor(Qt.PointingHandCursor))

        v_layout.addWidget(table)
        return container

    def handle_click(self, table, row, col, df_subset):
        item = table.item(row, col)
        if not item:
            return
        if col == 4:  # Profile link
            steam_id = df_subset.iloc[row].steam_id
            webbrowser.open(f"https://steamcommunity.com/profiles/{steam_id}")
        else:  # Copy text
            QGuiApplication.clipboard().setText(item.text())
