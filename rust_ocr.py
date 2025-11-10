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
from PySide6.QtCore import QObject, QTimer

# --- Globals ---
running = False
final_results = {}  # steamid64 -> name

SAVE_CSV = r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\mute_list.csv"
DATA_JSON = Path(r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\player_data.json")
LEFT, TOP, RIGHT, BOTTOM = 680, 385, 1877, 1178
OVERLAP_PIXELS = 4
UPSCALE_FACTOR = 2
WHITELIST_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$=#"
steamid_re = re.compile(r"7656119\d{10}")
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- Ensure CSV exists ---
if not os.path.exists(SAVE_CSV):
    with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
    print(f"[INFO] Created {SAVE_CSV}")

# --- Helper functions ---
def capture_region():
    return ImageGrab.grab(bbox=(LEFT, TOP, RIGHT, BOTTOM))

def split_columns(img):
    width, height = img.size
    left_box = (0, 0, int(width / 3) + OVERLAP_PIXELS, height)
    right_box = (int(width / 3) - OVERLAP_PIXELS, 0, width, height)
    return img.crop(left_box), img.crop(right_box)

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

def clean_steamid(text):
    match = steamid_re.search(text.replace(" ", ""))
    return match.group(0) if match else None

def parse_ocr(lines):
    entries = []
    buffer_name = ""
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        sid = clean_steamid(line_clean)
        if sid:
            name_raw = buffer_name.strip() if buffer_name else line_clean.replace(sid, "").strip()
            name = clean_name(name_raw)
            entries.append((name, sid))
            buffer_name = ""
        else:
            buffer_name = (buffer_name + " " + line_clean).strip() if buffer_name else line_clean
    return entries

def save_csv():
    global final_results
    with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "steamid", "profile_url"])
        for sid, name in final_results.items():
            writer.writerow([name, sid, f"https://steamcommunity.com/profiles/{sid}"] )
    print(f"[+] Saved {len(final_results)} entries to {SAVE_CSV}")

def ocr_image(img, psm=6):
    tmp_file = os.path.join(tempfile.gettempdir(), "tmp_col.png")
    img.save(tmp_file)
    out_base = tmp_file + "_out"
    try:
        subprocess.run(
            [TESSERACT_CMD, tmp_file, out_base,
             "--psm", str(psm),
             "-c", f"tessedit_char_whitelist={WHITELIST_CHARS}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        with open(out_base + ".txt", "r", encoding="utf-8", errors="ignore") as f:
            return [line.strip() for line in f if line.strip()]
    except subprocess.CalledProcessError:
        return []

# --- Capture loop ---
def capture_loop():
    global running, final_results
    print("\n[+] Capture started — scroll the mute list in Rust...\n")
    while running:
        img = capture_region()
        img = preprocess(img)
        left_img, right_img = split_columns(img)

        left_lines = ocr_image(left_img, psm=6)
        right_lines = ocr_image(right_img, psm=4)

        left_entries = parse_ocr(left_lines)
        right_entries = parse_ocr(right_lines)

        new_entries = 0
        for name, sid in left_entries + right_entries:
            if sid not in final_results:
                final_results[sid] = name
                new_entries += 1
                print(f"[CAPTURED] {name} — {sid}")

        if new_entries > 0:
            save_csv()
            try:
                subprocess.Popen(["python", "getPlayerData.py"])
                print("[OCR] Triggered getPlayerData.py to fetch player stats")
            except Exception as e:
                print("[OCR] Failed to run getPlayerData.py:", e)

        time.sleep(0.15)

    print("\n[+] Capture stopped. Saving results...\n")
    save_csv()

# --- OCR hotkeys ---
def start_ocr_thread():
    global running

    def start_capture():
        global running
        if not running:
            running = True
            threading.Thread(target=capture_loop, daemon=True).start()
            print("[HOTKEY] F8 pressed → Capture started")

    def stop_capture():
        global running
        running = False
        print("[HOTKEY] F9 pressed → Capture stopping...")

    def exit_program():
        global running
        running = False
        print("[HOTKEY] F10 pressed → Exiting program...")
        time.sleep(0.5)
        os._exit(0)

    keyboard.add_hotkey("F8", start_capture)
    keyboard.add_hotkey("F9", stop_capture)
    keyboard.add_hotkey("F10", exit_program)
    keyboard.wait()

# --- JSON watcher ---
class JSONWatcher(QObject):
    """Watches player_data.json and triggers dashboard refresh only when it changes"""
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.last_mtime = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_json)
        self.timer.start(1000)  # check every second

    def check_json(self):
        try:
            if DATA_JSON.exists():
                mtime = DATA_JSON.stat().st_mtime
                if mtime != self.last_mtime:
                    self.last_mtime = mtime
                    print("[Watcher] JSON changed → refreshing dashboard")
                    self.dashboard.refresh_data()
        except Exception as e:
            print("[Watcher] Error:", e)
