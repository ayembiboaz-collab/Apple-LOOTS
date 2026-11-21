"""Build CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_contact_sheet.png (8 AFTER scenes)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
PREVIEWS = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'ALT_PREVIEWS')
OUT = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'CONTACT_SHEET', 'GOLDEN_DAYLIGHT_CINEMA_ALT_contact_sheet.png')

BG = (14, 13, 12)
GOLD = (201, 162, 75)
CREAM = (236, 228, 214)
DIM = (150, 142, 130)

manifest = json.load(open(os.path.join(PREVIEWS, 'manifest.json')))
assert len(manifest) == 8

COLS, ROWS = 4, 2
CELL_W = 560
IMG_H = 315  # 16:9-ish crop height
LABEL_H = 54
TITLE_H = 120
FOOT_H = 64
MARGIN = 36
GAP = 18
W = MARGIN * 2 + COLS * CELL_W + (COLS - 1) * GAP
H = MARGIN + TITLE_H + ROWS * (IMG_H + LABEL_H) + (ROWS - 1) * GAP + FOOT_H + MARGIN

def font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

canvas = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(canvas)

# header
d.text((MARGIN, MARGIN + 6), "GOLDEN DAYLIGHT CINEMA", font=font(54, bold=True), fill=GOLD)
d.text((MARGIN, MARGIN + 66), "Apple Log 2  ·  Apple Wide Gamut  →  Rec.709  SDR  γ2.4   ·   iPhone 17 Pro / Blackmagic Camera", font=font(20), fill=CREAM)
d.rectangle([MARGIN, MARGIN + TITLE_H - 14, W - MARGIN, MARGIN + TITLE_H - 12], fill=(58, 50, 38))

y0 = MARGIN + TITLE_H
for idx, item in enumerate(manifest):
    row, col = divmod(idx, COLS)
    x = MARGIN + col * (CELL_W + GAP)
    y = y0 + row * (IMG_H + LABEL_H + GAP)
    img = Image.open(os.path.join(PREVIEWS, item['after'])).convert('RGB')
    # center-crop to 16:9
    w, h = img.size
    target = 16 / 9
    if w / h > target:
        nw = int(h * target); x0 = (w - nw) // 2; img = img.crop((x0, 0, x0 + nw, h))
    else:
        nh = int(w / target); y0c = (h - nh) // 2; img = img.crop((0, y0c, w, y0c + nh))
    img = img.resize((CELL_W, IMG_H), Image.LANCZOS)
    canvas.paste(img, (x, y))
    d.rectangle([x, y, x + CELL_W - 1, y + IMG_H - 1], outline=(52, 47, 40), width=1)
    num = item['scene'].split('_')[0]
    d.text((x, y + IMG_H + 8), num, font=font(22, bold=True), fill=GOLD)
    d.text((x + 42, y + IMG_H + 11), item['title'], font=font(19), fill=CREAM)

# footer
fy = H - MARGIN - FOOT_H + 10
d.text((MARGIN, fy), "AFTER grades rendered from the delivered GOLDEN_DAYLIGHT_CINEMA.cube  ·  simulated Apple Log 2 plates derived from credited sources (see SOURCES.md)", font=font(15), fill=DIM)
d.text((MARGIN, fy + 26), "33³ · standalone · no external conversion LUT required · NOT a generic warm filter", font=font(15), fill=DIM)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
canvas.save(OUT, 'PNG', optimize=True)
print("Wrote", OUT, canvas.size)
