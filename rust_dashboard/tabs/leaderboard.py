from PySide6.QtWidgets import QWidget, QGridLayout, QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication
import webbrowser
import pandas as pd
class LeaderboardTab(QWidget):
    def __init__(self, df=None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.main_layout = QGridLayout(self)
        self.main_layout.setSpacing(30)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setAlignment(Qt.AlignCenter)
        self.widgets = []  # track dynamic widgets
        self.refresh_data(self.df)

    def update_data(self, df):
        """Update the DataFrame and refresh tables."""
        if df is not None:
            self.df = df.copy()
            self.refresh_data(self.df)

    def refresh_data(self, df):
        # Clear old widgets
        for w in self.widgets:
            self.main_layout.removeWidget(w)
            w.setParent(None)
        self.widgets.clear()

        if df.empty:
            return

        self.df = df.copy()

        # Top-left: Lowest Total Hours (exclude 0)
        low_total_df = self.df[self.df['rust_hours_total'] > 0].sort_values('rust_hours_total').head(10)
        self.table_low_total = self.create_table(low_total_df, "Lowest Total Hours")
        self.main_layout.addWidget(self.table_low_total, 0, 0, alignment=Qt.AlignCenter)
        self.widgets.append(self.table_low_total)

        # Top-right: Highest Total Hours
        high_total_df = self.df.sort_values('rust_hours_total', ascending=False).head(10)
        self.table_high_total = self.create_table(high_total_df, "Highest Total Hours")
        self.main_layout.addWidget(self.table_high_total, 0, 1, alignment=Qt.AlignCenter)
        self.widgets.append(self.table_high_total)

        # Bottom-left: Last 2 Weeks – Highest Hours
        last2w_high_df = self.df.sort_values('rust_hours_2weeks', ascending=False).head(10)
        self.table_last2w_high = self.create_table(last2w_high_df, "Last 2 Weeks – Highest Hours")
        self.main_layout.addWidget(self.table_last2w_high, 1, 0, alignment=Qt.AlignCenter)
        self.widgets.append(self.table_last2w_high)

        # Bottom-right: Last 2 Weeks – Lowest Hours (exclude 0)
        last2w_low_df = self.df[self.df['rust_hours_2weeks'] > 0].sort_values('rust_hours_2weeks').head(10)
        self.table_last2w_low = self.create_table(last2w_low_df, "Last 2 Weeks – Lowest Hours")
        self.main_layout.addWidget(self.table_last2w_low, 1, 1, alignment=Qt.AlignCenter)
        self.widgets.append(self.table_last2w_low)

    def create_table(self, df_subset, title):
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(5)
        v_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

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
        table.setFixedHeight(30 * 10 + 30)
        table.setFixedWidth(int(900 * 0.48))

        table.setStyleSheet("""
            QTableWidget { background-color: #1E1E1E; color: #CCCCCC; gridline-color: #3C3C3C; }
            QHeaderView::section { background-color: #252526; color: #FFFFFF; padding: 6px; border: none; }
            QTableWidget::item { padding-left: 12px; padding-right: 12px; }
            QTableWidget::item:hover { background-color: #2A2D2E; }
        """)

        # Populate table
        for i, row in enumerate(df_subset.itertuples()):
            rank_item = QTableWidgetItem(str(i + 1))
            rank_item.setForeground(QColor("#FFD700") if i == 0 else QColor("#CCCCCC"))
            rank_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(i, 0, rank_item)

            for col_val, col_idx in zip([row.name, f"{row.rust_hours_total} h", f"{row.rust_hours_2weeks} h"], [1, 2, 3]):
                item = QTableWidgetItem(col_val)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, col_idx, item)

            profile_item = QTableWidgetItem("Link")
            profile_item.setForeground(QColor("#007ACC"))
            profile_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            profile_item.setToolTip(f"https://steamcommunity.com/profiles/{row.steam_id}")
            table.setItem(i, 4, profile_item)

        for col in range(4):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        table.horizontalHeaderItem(4).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

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
            import webbrowser
            webbrowser.open(f"https://steamcommunity.com/profiles/{steam_id}")
        else:  # Copy text
            QGuiApplication.clipboard().setText(item.text())
