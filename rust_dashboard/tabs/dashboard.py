from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
matplotlib.rcParams['font.family'] = 'DejaVu Sans'

class DashboardTab(QWidget):
    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.extract_flags()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
        self.setLayout(self.main_layout)
        self.widgets = []  # keep track of dynamic widgets
        self.refresh_data(self.df)

    def extract_flags(self):
        if 'flags' in self.df.columns:
            self.df['private_profile'] = self.df['flags'].apply(
                lambda f: f.get('private_profile', False) if isinstance(f, dict) else False
            )
        else:
            self.df['private_profile'] = False

    def update_data(self, df: pd.DataFrame):
        """Update internal DataFrame and refresh dashboard."""
        if df is not None:
            self.df = df.copy()
            self.extract_flags()
            self.refresh_data(self.df)

    def refresh_data(self, df: pd.DataFrame):
        # Clear old widgets safely
        for w in self.widgets:
            if isinstance(w, QWidget):
                self.main_layout.removeWidget(w)
                w.setParent(None)
                w.deleteLater()
            elif isinstance(w, QHBoxLayout):
                # Remove all child widgets in layout
                for i in reversed(range(w.count())):
                    child = w.itemAt(i).widget()
                    if child:
                        child.setParent(None)
                        child.deleteLater()
                self.main_layout.removeItem(w)
        self.widgets.clear()

        self.df = df.copy()
        self.extract_flags()

        # Title
        title_lbl = QLabel("Server Sweatiness Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        title_lbl.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(title_lbl)
        self.widgets.append(title_lbl)

        # Filter public players
        df_public = self.df[(self.df['private_profile'] == False) & (self.df['rust_hours_total'] > 0)]
        if df_public.empty:
            empty_lbl = QLabel("No public player data available.")
            empty_lbl.setStyleSheet("color: #CCCCCC; font-size: 14px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(empty_lbl)
            self.widgets.append(empty_lbl)
            return

        total_hours = df_public['rust_hours_total']
        recent_hours = df_public['rust_hours_2weeks']
        total_players = len(df_public)

        noobs_count = (total_hours < 1000).sum()
        somewhat_sweaty_count = ((total_hours >= 1000) & (total_hours < 2000)).sum()
        sweaty_count = (total_hours >= 2000).sum()

        # Chart
        fig = Figure(figsize=(4, 4))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.pie(
            [sweaty_count, somewhat_sweaty_count, noobs_count],
            labels=["Sweaty Players (≥2000 h)", "Somewhat Sweaty (1k–2k h)", "Noobs (<1k h)"],
            autopct="%1.1f%%",
            startangle=90,
            colors=["#FF4500", "#FFA500", "#1E90FF"],
            wedgeprops={"edgecolor": "black"}
        )
        ax.set_title("Total Hours Sweatiness", color="white")
        fig.patch.set_facecolor("#1E1E1E")
        ax.set_facecolor("#1E1E1E")
        for text in ax.texts:
            text.set_color("white")

        # Metrics
        median_total = total_hours.median()
        average_total = total_hours.mean()
        median_recent = recent_hours.median()
        average_recent = recent_hours.mean()
        std_total = total_hours.std()
        gini_total = self.gini(total_hours)
        composite_index = min(
            somewhat_sweaty_count / total_players * 50 +
            sweaty_count / total_players * 110, 100
        )
        composite_color = self.get_color(composite_index)

        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(6)
        metrics_layout.addWidget(self.create_metric_label(f"<b>Composite Sweatiness Index:</b> {composite_index:.1f}%", color=composite_color))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Total Players:</b> {total_players}"))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Sweaty Players (≥2000 h):</b> {sweaty_count}"))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Somewhat Sweaty (1k–2k h):</b> {somewhat_sweaty_count}"))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Noobs (<1k h):</b> {noobs_count}"))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Median Total Hours:</b> {median_total:.1f} h", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Average Total Hours:</b> {average_total:.1f} h", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Median Last 2 Weeks:</b> {median_recent:.1f} h", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Average Last 2 Weeks:</b> {average_recent:.1f} h", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Std Dev Total Hours:</b> {std_total:.1f} h", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Gini Coefficient:</b> {gini_total:.2f}", secondary=True))

        # Combine chart and metrics
        content_layout = QHBoxLayout()
        content_layout.addWidget(canvas)
        content_layout.addLayout(metrics_layout)
        self.main_layout.addLayout(content_layout)

        self.widgets.extend([canvas, content_layout])

    def create_metric_label(self, text, secondary=False, color=None):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12 if not secondary else 10))
        lbl.setStyleSheet(f"color: {color if color else ('#CCCCCC' if not secondary else '#888888')};")
        lbl.setAlignment(Qt.AlignLeft)
        lbl.setWordWrap(True)
        return lbl

    def get_color(self, value):
        if value <= 30: return "#00FF00"
        elif value <= 70: return "#FFFF00"
        else: return "#FF4500"

    def gini(self, x):
        array = np.sort(np.array(x))
        n = len(array)
        if n == 0: return 0
        cumx = np.cumsum(array)
        return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n
