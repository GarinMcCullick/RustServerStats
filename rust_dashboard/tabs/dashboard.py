from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

class DashboardTab(QWidget):
    def __init__(self, df):
        super().__init__()
        self.df = df.copy()
        self.extract_flags()
        self.init_ui()

    def extract_flags(self):
        """Flatten nested 'flags' JSON column to extract private_profile"""
        if 'flags' in self.df.columns:
            self.df['private_profile'] = self.df['flags'].apply(lambda f: f.get('private_profile', False) if isinstance(f, dict) else False)
        else:
            self.df['private_profile'] = False

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_lbl = QLabel("Server Sweatiness Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_lbl.setStyleSheet("color: #FFFFFF;")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        # Filter public and active players
        df_public = self.df[(self.df['private_profile'] == False) & (self.df['rust_hours_total'] > 0)]
        if df_public.empty:
            empty_lbl = QLabel("No public player data available.")
            empty_lbl.setStyleSheet("color: #CCCCCC; font-size: 14px;")
            empty_lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty_lbl)
            return

        total_hours = df_public['rust_hours_total']
        recent_hours = df_public['rust_hours_2weeks']
        total_players = len(df_public)

        # --- Composite Sweat Index calculation ---
        noobs_count = (total_hours < 1000).sum()
        somewhat_sweaty_count = ((total_hours >= 1000) & (total_hours < 2000)).sum()
        sweaty_count = (total_hours >= 2000).sum()

        fig = Figure(figsize=(4,4))
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        ax.pie(
            [sweaty_count, somewhat_sweaty_count, noobs_count],
            labels=["Sweaty Players (≥2000 h)", "Somewhat Sweaty (1k–2k h)", "Noobs (<1k h)"],
            autopct="%1.1f%%",
            startangle=90,
            colors=["#FF4500", "#FFA500", "#1E90FF"],
            wedgeprops={"edgecolor":"black"}
        )
        ax.set_title("Total Hours Sweatiness", color="white")
        fig.patch.set_facecolor("#1E1E1E")
        ax.set_facecolor("#1E1E1E")
        for text in ax.texts:
            text.set_color("white")

        # --- Metrics calculation ---
        median_total = total_hours.median()
        average_total = total_hours.mean()
        median_recent = recent_hours.median()
        average_recent = recent_hours.mean()
        std_total = total_hours.std()
        gini_total = self.gini(total_hours)

        # Weighted: somewhat sweaty = 50, sweaty = 50
        composite_index = (
            somewhat_sweaty_count / total_players * 50 +
            sweaty_count / total_players * 110
        )
        composite_index = min(composite_index, 100)
        composite_color = self.get_color(composite_index)

        # --- Metrics layout ---
        metrics_layout = QVBoxLayout()
        metrics_layout.setSpacing(6)

        # Primary metrics
        metrics_layout.addWidget(self.create_metric_label(
            f"<b>Composite Sweatiness Index:</b> {composite_index:.1f}%",
            tooltip="Weighted score: % of somewhat sweaty and sweaty players.",
            color=composite_color
        ))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Total Players:</b> {total_players}", tooltip="Number of public, active players."))
        metrics_layout.addWidget(self.create_metric_label(
            f"<b>Sweaty Players (≥2000 h):</b> {sweaty_count} ({sweaty_count/total_players*100:.1f}%)",
            tooltip="Players with 2,000 hours or more total playtime."
        ))
        metrics_layout.addWidget(self.create_metric_label(
            f"<b>Somewhat Sweaty (1k–2k h):</b> {somewhat_sweaty_count} ({somewhat_sweaty_count/total_players*100:.1f}%)",
            tooltip="Players with 1,000–1,999 hours."
        ))
        metrics_layout.addWidget(self.create_metric_label(
            f"<b>Noobs (<1000 h):</b> {noobs_count} ({noobs_count/total_players*100:.1f}%)",
            tooltip="Players with less than 1,000 total hours."
        ))

        # Secondary metrics
        metrics_layout.addWidget(self.create_metric_label(f"<b>Median Total Hours:</b> {median_total:.1f} h", tooltip="Middle value of total hours played.", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Average Total Hours:</b> {average_total:.1f} h", tooltip="Average total hours across all players.", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Median Last 2 Weeks:</b> {median_recent:.1f} h", tooltip="Middle value of hours played in last 2 weeks.", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Average Last 2 Weeks:</b> {average_recent:.1f} h", tooltip="Average recent hours across all players.", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Std Dev Total Hours:</b> {std_total:.1f} h", tooltip="Spread of total hours among players.", secondary=True))
        metrics_layout.addWidget(self.create_metric_label(f"<b>Gini Coefficient:</b> {gini_total:.2f}", tooltip="0 = everyone plays the same, 1 = one player dominates.", secondary=True))

        # Combine pie chart and metrics
        content_layout = QHBoxLayout()
        content_layout.addWidget(canvas)
        content_layout.addLayout(metrics_layout)
        layout.addLayout(content_layout)

    def create_metric_label(self, text, tooltip=None, secondary=False, color=None):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 12 if not secondary else 10))
        lbl.setStyleSheet(f"color: {color if color else ('#CCCCCC' if not secondary else '#888888')};")
        lbl.setAlignment(Qt.AlignLeft)
        lbl.setToolTip(tooltip or "")
        lbl.setWordWrap(True)
        return lbl

    def get_color(self, value):
        """Color code: green (0–30), yellow (30–70), red (70–100)"""
        if value <= 30: return "#00FF00"
        elif value <= 70: return "#FFFF00"
        else: return "#FF4500"

    def gini(self, x):
        """Gini coefficient: 0 = everyone plays the same, 1 = one player dominates"""
        array = np.sort(np.array(x))
        n = len(array)
        if n == 0: return 0
        cumx = np.cumsum(array)
        return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n
