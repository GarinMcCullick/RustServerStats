from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
import ctypes

# Windows constants for native dragging
WM_NCLBUTTONDOWN = 0xA1
HTCAPTION = 2
user32 = ctypes.windll.user32


class InGameOverlay(QWidget):
    def __init__(self, ocr_controller):
        super().__init__()

        self.ocr_controller = ocr_controller

        # ===== Window flags =====
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )

        self.setAttribute(Qt.WA_TranslucentBackground)

        # ===== Visible Container =====
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            background-color: rgba(30, 30, 30, 200);
            border-radius: 12px;
        """)

        layout = QVBoxLayout(self.container)

        self.start_btn = QPushButton("Start OCR")
        self.stop_btn = QPushButton("Stop OCR")

        self.start_btn.clicked.connect(self.ocr_controller.start_capture)
        self.stop_btn.clicked.connect(self.ocr_controller.stop_capture)

        btn_style = """
            QPushButton {
                background-color: #5865F2;
                color: white;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #4752C4;
            }
        """
        self.start_btn.setStyleSheet(btn_style)
        self.stop_btn.setStyleSheet(btn_style)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        self.resize(220, 140)
        self.container.resize(220, 140)

        # Default position AFTER show
        QTimer.singleShot(0, self.position_top_right)

    # ==============================
    # Position top-right primary monitor
    # ==============================
    def position_top_right(self):
        screen = QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        margin = 20
        x = geo.right() - self.width() - margin
        y = geo.top() + margin
        self.move(x, y)

    # ==============================
    # Windows-native dragging
    # ==============================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            hwnd = self.winId().__int__()
            # Let Windows handle dragging like a title bar
            user32.ReleaseCapture()
            user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
            event.accept()