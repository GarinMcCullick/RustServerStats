from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QTextEdit, QSizePolicy, QSpacerItem
from PySide6.QtCore import Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QGuiApplication
import ctypes
import subprocess
import threading

# Windows constants for native dragging
WM_NCLBUTTONDOWN = 0xA1
HTCAPTION = 2
user32 = ctypes.windll.user32

class InGameOverlay(QWidget):
    EDGE_MARGIN = 6

    def __init__(self, ocr_controller):
        super().__init__()
        self.ocr_controller = ocr_controller

        # Drag / resize state
        self.resizing = False
        self.resize_edge = None
        self.start_pos = None
        self.start_geom = None

        # Window flags
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Container
        self.container = QWidget(self)
        self.container.setStyleSheet("background-color: rgba(30,30,30,200); border-radius:12px;")
        self.layout = QVBoxLayout(self.container)

        # Buttons
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
        self.start_btn = QPushButton("Start OCR (F8)")
        self.stop_btn = QPushButton("Stop OCR (F9)")
        self.start_btn.setStyleSheet(btn_style)
        self.stop_btn.setStyleSheet(btn_style)
        self.start_btn.clicked.connect(self.ocr_controller.start_capture)
        self.stop_btn.clicked.connect(self.ocr_controller.stop_capture)
        self.layout.addWidget(self.start_btn)
        self.layout.addWidget(self.stop_btn)

        # Spacer between buttons and terminal
        self.layout.addItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Terminal
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet(
            "background-color: rgba(0,0,0,220); color:#00FF00; font-family: Consolas; font-size:11pt; border-radius:6px;"
        )
        self.terminal.setFixedHeight(0)
        self.terminal.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.terminal)

        # Spacer between terminal and dropdown
        self.layout.addItem(QSpacerItem(0, 6, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Dropdown
        self.dropdown_btn = QPushButton("Show Logs")
        self.dropdown_btn.setStyleSheet(btn_style)
        self.dropdown_btn.setCheckable(True)
        self.dropdown_btn.toggled.connect(self.toggle_terminal)
        self.layout.addWidget(self.dropdown_btn)

        # Default/expanded sizes
        self.default_width = 240
        self.default_height = 180
        self.expanded_width = 600
        self.expanded_height = 400
        self.resize(self.default_width, self.default_height)
        self.container.resize(self.default_width, self.default_height)

        # Top-right anchor
        QTimer.singleShot(0, self.position_top_right)

    def position_top_right(self):
        screen = QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        margin = 20
        self.top_right_x = geo.right() - margin
        self.top_right_y = geo.top() + margin
        self.move(self.top_right_x - self.width(), self.top_right_y)

    # ---------------------
    # Mouse events (drag & resize)
    # ---------------------
    def mousePressEvent(self, event):
        pos = event.pos()
        rect = self.rect()
        margin = self.EDGE_MARGIN

        left = pos.x() < margin
        right = pos.x() > rect.width() - margin
        top = pos.y() < margin
        bottom = pos.y() > rect.height() - margin

        if left or right or top or bottom:
            self.resizing = True
            self.start_pos = event.globalPosition().toPoint()
            self.start_geom = self.geometry()
            self.resize_edge = (left, right, top, bottom)
        elif event.button() == Qt.LeftButton:
            hwnd = self.winId().__int__()
            user32.ReleaseCapture()
            user32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
        event.accept()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.start_pos
            geom = QRect(self.start_geom)
            left, right, top, bottom = self.resize_edge

            # Adjust geometry smoothly
            if left:
                geom.setLeft(geom.left() + delta.x())
            if right:
                geom.setRight(geom.right() + delta.x())
            if top:
                geom.setTop(geom.top() + delta.y())
            if bottom:
                geom.setBottom(geom.bottom() + delta.y())

            geom.setWidth(max(150, geom.width()))
            geom.setHeight(max(150, geom.height()))
            self.setGeometry(geom)
            self.container.resize(geom.width(), geom.height())
        else:
            # Update cursor dynamically like Windows
            margin = self.EDGE_MARGIN
            cursor = Qt.ArrowCursor
            if pos.x() < margin and pos.y() < margin:
                cursor = Qt.SizeFDiagCursor
            elif pos.x() > self.width() - margin and pos.y() < margin:
                cursor = Qt.SizeBDiagCursor
            elif pos.x() < margin and pos.y() > self.height() - margin:
                cursor = Qt.SizeBDiagCursor
            elif pos.x() > self.width() - margin and pos.y() > self.height() - margin:
                cursor = Qt.SizeFDiagCursor
            elif pos.x() < margin or pos.x() > self.width() - margin:
                cursor = Qt.SizeHorCursor
            elif pos.y() < margin or pos.y() > self.height() - margin:
                cursor = Qt.SizeVerCursor
            self.setCursor(cursor)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        self.setCursor(Qt.ArrowCursor)

    # ---------------------
    # Toggle terminal
    # ---------------------
    def toggle_terminal(self, checked):
        if checked:
            new_width = self.expanded_width
            new_height = self.expanded_height
            self.terminal.setFixedHeight(new_height - 100)
            self.resize(new_width, new_height)
            self.container.resize(new_width, new_height)
            self.move(self.top_right_x - new_width, self.top_right_y)
            self.dropdown_btn.setText("Hide Logs")
        else:
            self.terminal.setFixedHeight(0)
            self.resize(self.default_width, self.default_height)
            self.container.resize(self.default_width, self.default_height)
            self.move(self.top_right_x - self.default_width, self.top_right_y)
            self.dropdown_btn.setText("Show Logs")

    # ---------------------
    # Logging with smooth scroll
    # ---------------------
    def log(self, text):
        self.terminal.append(text)
        self.smooth_scroll_to_bottom()

    def smooth_scroll_to_bottom(self):
        scroll = self.terminal.verticalScrollBar()
        target = scroll.maximum()
        current = scroll.value()
        step = max(1, (target - current) // 5)
        def step_scroll():
            nonlocal current
            if current < target:
                current += step
                scroll.setValue(min(current, target))
            else:
                scroll_timer.stop()
        scroll_timer = QTimer()
        scroll_timer.timeout.connect(step_scroll)
        scroll_timer.start(15)

    # ---------------------
    # Run script
    # ---------------------
    def run_script(self, command):
        def reader(proc):
            for line in iter(proc.stdout.readline, b''):
                try:
                    self.log(line.decode().rstrip())
                except Exception:
                    self.log(str(line).rstrip())

        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1)
        threading.Thread(target=reader, args=(proc,), daemon=True).start()