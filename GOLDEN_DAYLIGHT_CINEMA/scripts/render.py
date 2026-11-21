"""
render.py
=========

Render the eight before/after comparisons and the contact sheet.

For every scene:
  * generate the source sRGB image (procedural) and save it to assets/
  * simulate Apple Log 2 / Apple Wide Gamut capture from it
  * BEFORE = neutral Apple Log 2 -> Rec.709 gamma 2.4 decode (NO creative
    grade) -- the "correct but ungraded" baseline
  * AFTER  = the delivered GOLDEN_DAYLIGHT_CINEMA.cube applied to the
    *same* simulated Apple Log 2 input (read back from the .cube file and
    trilinearly interpolated), so the preview shows exactly what the LUT
    ships.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import color_science as cs
import scenes
from cube_io import read_cube, apply_cube

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")
PREVIEWS = os.path.join(ROOT, "PREVIEWS")
CONTACT = os.path.join(ROOT, "CONTACT_SHEET")
LUT_PATH = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

AWG_TO_709 = cs.apple_wide_gamut_to_rec709()


def to_uint8(img):
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def neutral_decode(log2):
    """Apple Log 2 -> Rec.709 gamma 2.4, no creative grade."""
    lin709 = cs.apple_log_to_linear(log2) @ AWG_TO_709.T
    return cs.rec709_gamma24(np.clip(lin709, 0.0, None))


def render_scene(name, fn, lut, exposure=1.0):
    srgb = fn()
    Image.fromarray(to_uint8(srgb)).save(os.path.join(ASSETS, f"{name}_source.png"))

    log2 = scenes.simulate_apple_log2(srgb, exposure=exposure)

    before = neutral_decode(log2)
    after = apply_cube(lut, log2)

    Image.fromarray(to_uint8(before)).save(os.path.join(PREVIEWS, f"{name}_before.png"))
    Image.fromarray(to_uint8(after)).save(os.path.join(PREVIEWS, f"{name}_after.png"))
    return srgb, before, after


def build_contact_sheet(entries):
    """entries: list of (name, before, after). Build a labelled grid."""
    thumb_w = 520
    n = len(entries)
    cols = 2
    rows = (n + cols - 1) // cols
    pad = 16
    label_h = 46
    thumb_h = int(thumb_w * entries[0][1].shape[0] / entries[0][1].shape[1])
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * (thumb_h + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (14, 16, 20))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except Exception:
        font = ImageFont.load_default()

    for i, (name, before, after) in enumerate(entries):
        col, row = i % cols, i // cols
        bx = pad + col * (thumb_w + pad)
        by = pad + row * (thumb_h + label_h + pad)
        bt = Image.fromarray(to_uint8(before)).resize((thumb_w, thumb_h))
        at = Image.fromarray(to_uint8(after)).resize((thumb_w, thumb_h))
        sheet.paste(bt, (bx, by))
        sheet.paste(at, (bx + thumb_w + pad, by))
        label = name.replace("_", " ").upper()
        draw.text((bx, by + thumb_h + 6), label, fill=(220, 220, 220), font=font)
        draw.text((bx + thumb_w + pad, by + thumb_h + 6), "AFTER",
                  fill=(230, 200, 120), font=font)
    out = os.path.join(CONTACT, "contact_sheet.png")
    sheet.save(out)
    return out


def main():
    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(PREVIEWS, exist_ok=True)
    os.makedirs(CONTACT, exist_ok=True)

    lut = read_cube(LUT_PATH)
    print(f"Loaded LUT: {LUT_PATH} ({lut['size']}^3, title={lut['title'][:40]}...)")

    entries = []
    for name, fn in scenes.SCENES.items():
        srgb, before, after = render_scene(name, fn, lut)
        entries.append((name, before, after))
        print(f"  rendered {name}")

    sheet = build_contact_sheet(entries)
    print(f"Contact sheet: {sheet}")
    print("Done.")


if __name__ == "__main__":
    main()
