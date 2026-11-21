"""
Generate a high-resolution dark-portfolio Contact Sheet PNG comparing all 8
Simulated Apple Log 2 (BEFORE) and GOLDEN_DAYLIGHT_CINEMA.cube (AFTER) pairs.
"""

from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

SCENES = [
    ("01_harsh_midday_city", "01 · HARSH MIDDAY CITY"),
    ("02_midday_portrait", "02 · MIDDAY PORTRAIT"),
    ("03_mediterranean_street", "03 · MEDITERRANEAN STREET"),
    ("04_bright_beach_daylight", "04 · BRIGHT BEACH DAYLIGHT"),
    ("05_natural_landscape_greenery_mountains", "05 · NATURAL LANDSCAPE"),
    ("06_golden_hour_landscape", "06 · GOLDEN-HOUR LANDSCAPE"),
    ("07_modern_architecture", "07 · MODERN ARCHITECTURE"),
    ("08_outdoor_travel_people_buildings", "08 · OUTDOOR TRAVEL SCENE"),
]


def load_font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prev_dir = os.path.join(root, "GOLDEN_DAYLIGHT_CINEMA", "PREVIEWS")
    cs_dir = os.path.join(root, "GOLDEN_DAYLIGHT_CINEMA", "CONTACT_SHEET")
    os.makedirs(cs_dir, exist_ok=True)

    # Layout: 2 columns x 4 rows of paired BEFORE|AFTER cards
    # Each image thumb: 540 x 295 (exact 1408:768 aspect ratio)
    thumb_w, thumb_h = 540, 295
    pair_gap = 8
    card_pad = 16
    label_h = 34
    card_w = thumb_w * 2 + pair_gap + card_pad * 2
    card_h = thumb_h + label_h + card_pad * 2

    cols, rows = 2, 4
    col_gap = 28
    row_gap = 26
    margin_x = 48
    header_h = 150
    footer_h = 72

    canvas_w = margin_x * 2 + cols * card_w + (cols - 1) * col_gap
    canvas_h = header_h + rows * card_h + (rows - 1) * row_gap + footer_h

    canvas = Image.new("RGB", (canvas_w, canvas_h), (12, 13, 16))
    draw = ImageDraw.Draw(canvas)

    f_title = load_font(38, bold=True)
    f_sub = load_font(18, bold=False)
    f_card = load_font(17, bold=True)
    f_badge = load_font(13, bold=True)
    f_foot = load_font(15, bold=False)

    # Header
    draw.text((margin_x, 34), "GOLDEN DAYLIGHT CINEMA — CONTACT SHEET", fill=(242, 232, 212), font=f_title)
    draw.text(
        (margin_x, 86),
        "Apple Log 2 (Apple Wide Gamut)  ->  Rec.709 SDR Gamma 2.4   |   33x33x33 Standalone 3D LUT   |   iPhone 17 Pro / Blackmagic Camera",
        fill=(182, 174, 160),
        font=f_sub,
    )
    draw.text(
        (margin_x, 114),
        "Note: BEFORE frames are documented Simulated Apple Log 2 inputs derived from SDR reference plates; AFTER frames are rendered directly via GOLDEN_DAYLIGHT_CINEMA.cube.",
        fill=(212, 168, 92),
        font=f_foot,
    )

    for idx, (slug, label) in enumerate(SCENES):
        r = idx // cols
        c = idx % cols
        cx = margin_x + c * (card_w + col_gap)
        cy = header_h + r * (card_h + row_gap)

        # Card background
        draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=10, fill=(22, 24, 29), outline=(48, 50, 58), width=1)
        draw.text((cx + card_pad, cy + 12), label, fill=(238, 228, 208), font=f_card)
        draw.text((cx + card_w - card_pad - 230, cy + 14), "BEFORE (Log 2 Sim)  /  AFTER (.cube)", fill=(140, 144, 154), font=f_badge)

        im_b = Image.open(os.path.join(prev_dir, f"{slug}_BEFORE.png")).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        im_a = Image.open(os.path.join(prev_dir, f"{slug}_AFTER.png")).convert("RGB").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)

        iy = cy + card_pad + label_h - 6
        bx = cx + card_pad
        ax = bx + thumb_w + pair_gap

        canvas.paste(im_b, (bx, iy))
        canvas.paste(im_a, (ax, iy))

        # Subtle badges
        draw.rectangle([bx + 8, iy + 8, bx + 84, iy + 28], fill=(16, 17, 20))
        draw.text((bx + 14, iy + 11), "BEFORE", fill=(195, 198, 205), font=f_badge)

        draw.rectangle([ax + 8, iy + 8, ax + 74, iy + 28], fill=(184, 134, 48))
        draw.text((ax + 14, iy + 11), "AFTER", fill=(14, 15, 18), font=f_badge)

    draw.text(
        (margin_x, canvas_h - 44),
        "GOLDEN_DAYLIGHT_CINEMA.cube  |  33^3 Tetrahedral Interpolation  |  See VALIDATION_REPORT.txt and SOURCES.md for methodology & disclosures",
        fill=(132, 136, 146),
        font=f_foot,
    )

    out_path = os.path.join(cs_dir, "GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png")
    canvas.save(out_path, format="PNG", optimize=True)
    print(f"Wrote {out_path} ({canvas.size[0]}x{canvas.size[1]}, {os.path.getsize(out_path) / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    main()
