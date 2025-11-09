from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class ChartsTab(QWidget):
    def __init__(self, df):
        super().__init__()
        self.df = df
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h2>Top 10 Players by Total Hours</h2>"))
        fig1, ax1 = plt.subplots(figsize=(6,4))
        df_sorted = self.df.sort_values("rust_hours_total", ascending=False).head(10)
        ax1.barh(df_sorted["name"], df_sorted["rust_hours_total"], color="#7289DA")
        ax1.invert_yaxis()
        canvas1 = FigureCanvas(fig1)
        layout.addWidget(canvas1)

        layout.addWidget(QLabel("<h2>Top 10 Players by 2 Weeks Hours</h2>"))
        fig2, ax2 = plt.subplots(figsize=(6,4))
        df_sorted2 = self.df.sort_values("rust_hours_2weeks", ascending=False).head(10)
        ax2.barh(df_sorted2["name"], df_sorted2["rust_hours_2weeks"], color="#99AAB5")
        ax2.invert_yaxis()
        canvas2 = FigureCanvas(fig2)
        layout.addWidget(canvas2)
