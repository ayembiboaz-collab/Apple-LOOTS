"""
contact_sheet.py — visual overview of all eight BEFORE/AFTER pairs.

Builds GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png
from the PNGs that render_previews.py produced from the delivered .cube.

Run:  python3 scripts/contact_sheet.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "PREVIEWS")
OUT_DIR = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "CONTACT_SHEET")
OUT = os.path.join(OUT_DIR, "GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png")

BG = (14, 13, 12)
FG = (236, 230, 222)
DIM = (150, 142, 132)
ACCENT = (214, 162, 86)

CELL_W = 620
MARGIN = 46
GAP_X = 26
GAP_Y = 54
HEADER = 196
FOOTER = 112


def font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    manifest = json.load(open(os.path.join(ROOT, "work", "manifest.json")))
    os.makedirs(OUT_DIR, exist_ok=True)

    probe = Image.open(os.path.join(PREVIEWS, manifest[0]["before"]))
    aspect = probe.size[1] / probe.size[0]
    cell_h = int(CELL_W * aspect)
    pair_w = CELL_W * 2 + 6
    label_h = 46

    cols, rows = 2, 4
    W = MARGIN * 2 + pair_w * cols + GAP_X * (cols - 1)
    H = HEADER + rows * (cell_h + label_h + GAP_Y) - GAP_Y + FOOTER

    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)

    f_title = font(58, True)
    f_sub = font(25)
    f_small = font(20)
    f_cell = font(23, True)
    f_cell_s = font(19)
    f_tag = font(17, True)

    d.text((MARGIN, 46), "GOLDEN DAYLIGHT CINEMA", font=f_title, fill=FG)
    d.text(
        (MARGIN, 120),
        "Apple Log 2 / Apple Wide Gamut  \u2192  Rec.709 SDR, gamma 2.4   \u00b7   "
        "33\u00d733\u00d733 3D LUT   \u00b7   contact sheet",
        font=f_sub,
        fill=ACCENT,
    )
    d.text(
        (MARGIN, 154),
        "Left: simulated Apple Log 2, no LUT.   Right: the same frame through the "
        "delivered GOLDEN_DAYLIGHT_CINEMA.cube.",
        font=f_small,
        fill=DIM,
    )
    d.line([(MARGIN, HEADER - 22), (W - MARGIN, HEADER - 22)], fill=(52, 48, 44), width=2)

    for i, m in enumerate(manifest):
        c, r = i % cols, i // cols
        x = MARGIN + c * (pair_w + GAP_X)
        y = HEADER + r * (cell_h + label_h + GAP_Y)

        for j, (fn, tag) in enumerate(
            [(m["before"], "BEFORE \u00b7 APPLE LOG 2 (SIMULATED)"), (m["after"], "AFTER \u00b7 GRADED")]
        ):
            im = Image.open(os.path.join(PREVIEWS, fn)).convert("RGB")
            im = im.resize((CELL_W, cell_h), Image.LANCZOS)
            px = x + j * (CELL_W + 6)
            sheet.paste(im, (px, y))
            d.rectangle([px, y, px + CELL_W - 1, y + cell_h - 1], outline=(58, 53, 48))
            tw = d.textlength(tag, font=f_tag)
            d.rectangle([px + 10, y + 10, px + 22 + tw + 10, y + 38], fill=(10, 9, 8))
            d.text((px + 16, y + 16), tag, font=f_tag, fill=ACCENT if j else DIM)

        d.text((x, y + cell_h + 10), f"{m['num']}.  {m['label']}", font=f_cell, fill=FG)
        d.text((x, y + cell_h + 38), m["note"], font=f_cell_s, fill=DIM)

    fy = H - FOOTER + 14
    d.line([(MARGIN, fy - 16), (W - MARGIN, fy - 16)], fill=(52, 48, 44), width=2)
    d.text(
        (MARGIN, fy),
        "AFTER frames were produced by parsing GOLDEN_DAYLIGHT_CINEMA.cube from disk and "
        "interpolating it tetrahedrally \u2014 not by an approximation of the look.",
        font=f_small,
        fill=DIM,
    )
    d.text(
        (MARGIN, fy + 30),
        "BEFORE frames are DOCUMENTED SIMULATED Apple Log 2 derived from the source stills "
        "(scripts/simulate_log2.py). They are not iPhone sensor captures.",
        font=f_small,
        fill=DIM,
    )
    d.text(
        (MARGIN, fy + 60),
        "No physical iPhone or Blackmagic Camera testing was performed. "
        "See VALIDATION_REPORT.txt.",
        font=f_small,
        fill=DIM,
    )

    sheet.save(OUT, optimize=True, compress_level=9)
    print(f"wrote {OUT}  ({W}x{H}, {os.path.getsize(OUT)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
