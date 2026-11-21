#!/usr/bin/env python3
"""Build a visual contact sheet of all 8 before/after comparisons."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS = os.path.join(ROOT, "PREVIEWS")
OUT = os.path.join(ROOT, "CONTACT_SHEET", "contact_sheet.png")

SCENES = [
    ("scene1_midday_city", "1. Harsh midday city"),
    ("scene2_midday_portrait", "2. Midday portrait (sun)"),
    ("scene3_mediterranean_street", "3. Mediterranean street"),
    ("scene4_beach_daylight", "4. Bright beach daylight"),
    ("scene5_landscape_greenery", "5. Landscape & greenery"),
    ("scene6_golden_hour", "6. Golden-hour landscape"),
    ("scene7_modern_architecture", "7. Modern architecture"),
    ("scene8_travel_people", "8. Outdoor travel scene"),
]

COL_W = 760
ROW_H = 460
PAD = 18
LABEL_H = 46
BG = (14, 15, 18)

try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    font_s = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
except Exception:
    font = ImageFont.load_default()
    font_s = font

os.makedirs(os.path.dirname(OUT), exist_ok=True)
W = PAD * 3 + COL_W * 2
H = PAD * 2 + (ROW_H + LABEL_H) * len(SCENES)
sheet = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(sheet)

draw.text((PAD, PAD), "GOLDEN DAYLIGHT CINEMA  —  BEFORE / AFTER CONTACT SHEET",
          fill=(230, 225, 215), font=font)
draw.text((PAD, PAD + 38),
          "BEFORE = simulated Apple Log 2 (flat).  AFTER = delivered GOLDEN_DAYLIGHT_CINEMA.cube",
          fill=(150, 145, 135), font=font_s)

y = PAD * 2 + 70
for stem, label in SCENES:
    before = Image.open(os.path.join(PREVIEWS, f"{stem}_BEFORE.png")).convert("RGB")
    after = Image.open(os.path.join(PREVIEWS, f"{stem}_AFTER.png")).convert("RGB")
    b = before.resize((COL_W, ROW_H))
    a = after.resize((COL_W, ROW_H))
    sheet.paste(b, (PAD, y))
    sheet.paste(a, (PAD * 2 + COL_W, y))
    draw.rectangle([PAD, y, PAD + COL_W, y + ROW_H], outline=(40, 42, 48))
    draw.rectangle([PAD * 2 + COL_W, y, PAD * 2 + COL_W * 2, y + ROW_H], outline=(40, 42, 48))
    draw.text((PAD + 6, y + 6), f"BEFORE  ·  {label}", fill=(180, 175, 165), font=font_s)
    draw.text((PAD * 2 + COL_W + 6, y + 6), f"AFTER  ·  {label}", fill=(230, 205, 150), font=font_s)
    y += ROW_H + LABEL_H

sheet.save(OUT)
print("wrote", OUT, sheet.size)
