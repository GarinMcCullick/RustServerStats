import threading
import time
import os
import csv
import keyboard
from PIL import Image, ImageGrab, ImageOps, ImageFilter
import re
import tempfile
import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, QTimer, Qt, QMetaObject, Q_ARG
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor

# --- Globals ---
running = False
final_results = {}  # steamid64 -> name
debug_overlay = None

SAVE_CSV = r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\mute_list.csv"
DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")

LEFT, TOP, RIGHT, BOTTOM = 580, 385, 1877, 1178
UPSCALE_FACTOR = 2

steamid_re = re.compile(r"7656119\d{10}")
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- Ensure CSV exists ---
if not os.path.exists(SAVE_CSV):
    with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
    print(f"[INFO] Created {SAVE_CSV}")


# --- Overlay ---
class OCRDebugOverlay(QWidget):
    def __init__(self, regions):
        super().__init__()
        self.regions = regions
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        screen = QApplication.primaryScreen()
        self.setGeometry(0, 0, screen.size().width(), screen.size().height())
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)

    def paintEvent(self, event):
        if not self.regions:
            return
        with QPainter(self) as painter:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 0, 0, 50))
            left = min(r[0] for r in self.regions)
            top = min(r[1] for r in self.regions)
            right = max(r[2] for r in self.regions)
            bottom = max(r[3] for r in self.regions)
            painter.drawRect(left, top, right - left, bottom - top)

    def update_regions(self, regions):
        self.regions = regions
        self.update()


# --- Helpers ---
def capture_region():
    return ImageGrab.grab(bbox=(LEFT, TOP, RIGHT, BOTTOM))


def preprocess(img):
    gray = ImageOps.grayscale(img)
    gray = ImageOps.autocontrast(gray, cutoff=2)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
    if UPSCALE_FACTOR > 1:
        w, h = gray.size
        gray = gray.resize((w * UPSCALE_FACTOR, h * UPSCALE_FACTOR), Image.LANCZOS)
    return gray


def clean_name(name_raw):
    return re.sub(r"[^A-Za-z0-9_\- ]", " ", name_raw).strip()


def ocr_full_tsv(img):
    tmp_file = os.path.join(tempfile.gettempdir(), "tmp_full.png")
    img.save(tmp_file)
    out_base = tmp_file + "_out"
    try:
        subprocess.run(
            [TESSERACT_CMD, tmp_file, out_base, "--oem", "1", "--psm", "3", "tsv"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        words = []
        with open(out_base + ".tsv", "r", encoding="utf-8", errors="ignore") as f:
            for line in f.readlines()[1:]:
                parts = line.strip().split("\t")
                if len(parts) < 12 or not parts[11].strip():
                    continue
                words.append({
                    "text": parts[11].strip(),
                    "x": int(parts[6]),
                    "y": int(parts[7]),
                    "w": int(parts[8]),
                    "h": int(parts[9])
                })
        return words
    except subprocess.CalledProcessError:
        return []


def save_csv():
    with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
        for sid, name in final_results.items():
            writer.writerow([name, sid, f"https://steamcommunity.com/profiles/{sid}"])
    print(f"[INFO] Saved {len(final_results)} entries to {SAVE_CSV}")


def log_capture(sid, name=None):
    if name:
        print(f"[CAPTURED] {name} — {sid}")
    else:
        print(f"[CAPTURED] {sid}")


# --- Capture Loop ---
def capture_loop(controller, include_names=False):
    global debug_overlay
    print("\n[+] Capture started — scroll the mute list in Rust...\n")

    while controller.running:
        img = preprocess(capture_region())
        words = ocr_full_tsv(img)
        absolute_boxes = []
        new_entries = 0

        steam_words = [w for w in words if steamid_re.fullmatch(w["text"])]

        for steam in steam_words:
            sid = steam["text"]
            sx, sy, sw, sh = steam["x"], steam["y"], steam["w"], steam["h"]

            name = sid
            if include_names:
                candidates = [
                    w for w in words
                    if w["y"] < sy and sy - w["y"] < 90
                    and abs((w["x"] + w["w"]//2) - (sx + sw//2)) < 300
                ]
                if candidates:
                    name = clean_name(sorted(candidates, key=lambda w: sy - w["y"])[0]["text"])

            if sid not in final_results:
                final_results[sid] = name
                new_entries += 1
                log_capture(sid, name if include_names else None)

            absolute_boxes.append((LEFT + sx, TOP + sy, LEFT + sx + sw, TOP + sy + sh))

        if debug_overlay:
            debug_overlay.update_regions(absolute_boxes)

        if new_entries > 0:
            save_csv()
            try:
                subprocess.Popen(["python", "getPlayerData.py"])
            except Exception:
                pass

        time.sleep(0.15)

    print("\n[+] Capture stopped.")
    save_csv()


# --- Hotkeys / Thread ---
def start_ocr_thread(controller):
    global debug_overlay
    if not debug_overlay:
        debug_overlay = OCRDebugOverlay([])
        debug_overlay.hide()

    class OverlayController(QObject):
        def toggle(self, visible: bool):
            QMetaObject.invokeMethod(
                debug_overlay,
                "setVisible",
                Qt.QueuedConnection,
                Q_ARG(bool, visible)
            )

    overlay_controller = OverlayController()

    def start_capture():
        if not controller.running:
            controller.running = True
            overlay_controller.toggle(True)
            threading.Thread(target=capture_loop, args=(controller, True), daemon=True).start()
            print("[HOTKEY] F8 → Capture started")

    def stop_capture():
        if controller.running:
            controller.running = False
            overlay_controller.toggle(False)
            print("[HOTKEY] F9 → Capture stopped")

    def exit_program():
        controller.running = False
        overlay_controller.toggle(False)
        print("[HOTKEY] F10 → Exit")
        time.sleep(0.2)
        os._exit(0)

    keyboard.add_hotkey("F8", start_capture)
    keyboard.add_hotkey("F9", stop_capture)
    keyboard.add_hotkey("F10", exit_program)


# --- Run ---
if __name__ == "__main__":
    app = QApplication([])

    from main import OCRController
    ocr_controller = OCRController()

    start_ocr_thread(ocr_controller)

    app.exec()