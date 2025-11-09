# rust_mute_list_windows_hotkeys_v4.2.py
import subprocess
import tempfile
import os
import re
import csv
import time
import threading
import keyboard
from PIL import ImageGrab, Image, ImageOps, ImageFilter

# ---------------- CONFIG ---------------- #
LEFT = 680
TOP = 385
RIGHT = 1877
BOTTOM = 1178

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
SAVE_CSV = r"C:\Users\GordanRamsey\Desktop\RustLobbyTracker\mute_list.csv"

steamid_re = re.compile(r"7656119\d{10}")

OVERLAP_PIXELS = 4
UPSCALE_FACTOR = 2

WHITELIST_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$=#- "

running = False
final_results = {}   # steamid64 -> name


# ---------------- CLEAN NAME (NEW & CORRECT) ---------------- #

def clean_name(name_raw):
    """
    Clean hallucinated garbage from OCR:
    - removes weird symbols
    - splits into chunks
    - picks the chunk with the most uppercase letters (actual name)
    """
    # 1. Replace weird characters with space
    name = re.sub(r"[^A-Za-z0-9_\- ]", " ", name_raw).strip()

    if not name:
        return ""

    # 2. Split into chunks
    chunks = [c for c in name.split(" ") if c.strip()]

    if not chunks:
        return ""

    # 3. Score each chunk: choose the one most like a real Steam name
    def score(chunk):
        score_upper = sum(1 for c in chunk if c.isupper())
        score_len = len(chunk)
        return score_upper * 3 + score_len

    best_chunk = max(chunks, key=score)

    return best_chunk.strip()


# ---------------- OCR FUNCTIONS ---------------- #

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


def split_columns(img):
    width, height = img.size
    left_box = (0, 0, int(width / 3) + OVERLAP_PIXELS, height)
    right_box = (int(width / 3) - OVERLAP_PIXELS, 0, width, height)
    return img.crop(left_box), img.crop(right_box)


def ocr_image(img, psm=6):
    tmp_file = os.path.join(tempfile.gettempdir(), "tmp_col.png")
    img.save(tmp_file)
    out_base = tmp_file + "_out"

    custom = f"--psm {psm} -c tessedit_char_whitelist={WHITELIST_CHARS}"

    subprocess.run(
        [TESSERACT_CMD, tmp_file, out_base] + custom.split(),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    with open(out_base + ".txt", "r", encoding="utf-8", errors="ignore") as f:
        return [line.strip() for line in f if line.strip()]


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


# ---------------- CAPTURE LOOP ---------------- #

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

        for name, sid in left_entries + right_entries:
            if sid not in final_results:
                final_results[sid] = name
                print(f"[CAPTURED] {name} — {sid}")

        time.sleep(0.15)

    print("\n[+] Capture stopped. Saving results...\n")

    with open(SAVE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "SteamID64", "ProfileURL"])
        for sid, name in final_results.items():
            writer.writerow([name, sid, f"https://steamcommunity.com/profiles/{sid}"])

    print(f"Saved {len(final_results)} entries to {SAVE_CSV}\n")
    for sid, name in final_results.items():
        print(f"{name} — {sid} — https://steamcommunity.com/profiles/{sid}")


# ---------------- HOTKEY CONTROL ---------------- #

def start_capture():
    global running
    if not running:
        running = True
        threading.Thread(target=capture_loop, daemon=True).start()


def stop_capture():
    global running
    running = False


print("Rust Mute List Tracker (Hotkey Mode)")
print("------------------------------------")
print("F8  = Start capture")
print("F9  = Stop capture & save")
print("F10 = Exit program\n")

keyboard.add_hotkey("F8", start_capture)
keyboard.add_hotkey("F9", stop_capture)
keyboard.wait("F10")

print("\n[+] Program terminated.")
