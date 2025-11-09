# calibrate_region_preview.py
import pyautogui
from PIL import ImageGrab

print("Move your mouse to the TOP-LEFT corner of the mute list and press Enter.")
input("Press Enter when ready...")
x1, y1 = pyautogui.position()
print(f"Top-left: ({x1}, {y1})")

print("Move your mouse to the BOTTOM-RIGHT corner of the mute list and press Enter.")
input("Press Enter when ready...")
x2, y2 = pyautogui.position()
print(f"Bottom-right: ({x2}, {y2})")

# Ensure correct order
left = min(x1, x2)
top = min(y1, y2)
right = max(x1, x2)
bottom = max(y1, y2)

print(f"Use these coordinates in your capture script:")
print(f"LEFT = {left}, TOP = {top}, RIGHT = {right}, BOTTOM = {bottom}")

# ---------------- Preview the capture ---------------- #
print("Previewing the selected area...")
img = ImageGrab.grab(bbox=(left, top, right, bottom))
img.show()
