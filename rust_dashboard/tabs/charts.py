from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import pandas as pd

class ChartsTab(QWidget):
    def __init__(self, df: pd.DataFrame = None):
        super().__init__()
        self.df = df.copy() if df is not None else pd.DataFrame()
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.canvas1 = None
        self.canvas2 = None
        self.init_ui()

    def init_ui(self):
        # Titles
        self.title1 = QLabel("<h2>Top 10 Players by Total Hours</h2>")
        self.layout.addWidget(self.title1)

        self.title2 = QLabel("<h2>Top 10 Players by 2 Weeks Hours</h2>")
        self.layout.addWidget(self.title2)

        # Initial draw
        self.refresh_charts()

    def update_data(self, df: pd.DataFrame):
        """Update DataFrame and refresh charts."""
        if df is not None and not df.empty:
            self.df = df.copy()
            self.refresh_charts()

    def refresh_charts(self):
        # Remove old canvases if they exist
        if self.canvas1:
            self.layout.removeWidget(self.canvas1)
            self.canvas1.setParent(None)
            self.canvas1.deleteLater()
            self.canvas1 = None
        if self.canvas2:
            self.layout.removeWidget(self.canvas2)
            self.canvas2.setParent(None)
            self.canvas2.deleteLater()
            self.canvas2 = None

        if self.df.empty:
            return  # nothing to plot

        # Top 10 by total hours
        df_sorted_total = self.df.sort_values("rust_hours_total", ascending=False).head(10)
        fig1, ax1 = plt.subplots(figsize=(6, 4))
        ax1.barh(df_sorted_total["name"], df_sorted_total["rust_hours_total"], color="#7289DA")
        ax1.invert_yaxis()
        ax1.set_xlabel("Total Hours")
        self.canvas1 = FigureCanvas(fig1)
        self.layout.insertWidget(1, self.canvas1)  # below first title

        # Top 10 by 2 weeks hours
        df_sorted_2w = self.df.sort_values("rust_hours_2weeks", ascending=False).head(10)
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.barh(df_sorted_2w["name"], df_sorted_2w["rust_hours_2weeks"], color="#99AAB5")
        ax2.invert_yaxis()
        ax2.set_xlabel("Last 2 Weeks Hours")
        self.canvas2 = FigureCanvas(fig2)
        self.layout.insertWidget(3, self.canvas2)  # below second title
