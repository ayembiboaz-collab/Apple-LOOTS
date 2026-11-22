"""
Bake GOLDEN_DAYLIGHT_CINEMA.cube, generate simulated Apple Log 2 intermediates,
render 8 BEFORE/AFTER PNGs using the delivered .cube, and build the contact sheet.
"""

import glob
import hashlib
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from color_science_core import (
    bake_cube_lut,
    load_cube_lut,
    simulate_apple_log2_from_srgb,
    neutral_apple_log2_to_rec709,
    apply_cube_tetrahedral,
)

ROOT = "GOLDEN_DAYLIGHT_CINEMA_PROJECT"
DELIV = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
LUT_PATH = os.path.join(DELIV, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
PREVIEWS_DIR = os.path.join(DELIV, "PREVIEWS")
CONTACT_DIR = os.path.join(DELIV, "CONTACT_SHEET")
SIM_LOG_DIR = os.path.join(ROOT, "simulated_log")
SRC_DIR = os.path.join(ROOT, "source_images")

SCENES = [
    ("scene_01_harsh_midday_city.jpg", "01_harsh_midday_city", "01. Harsh Midday City"),
    ("scene_02_midday_portrait.jpg", "02_midday_portrait", "02. Midday Portrait"),
    ("scene_03_mediterranean_street.jpg", "03_mediterranean_street", "03. Mediterranean Street"),
    ("scene_04_bright_beach.jpg", "04_bright_beach", "04. Bright Beach Daylight"),
    ("scene_05_natural_landscape.jpg", "05_natural_landscape", "05. Natural Landscape"),
    ("scene_06_golden_hour.jpg", "06_golden_hour", "06. Golden-Hour Landscape"),
    ("scene_07_modern_architecture.jpg", "07_modern_architecture", "07. Modern Architecture"),
    ("scene_08_outdoor_travel.jpg", "08_outdoor_travel", "08. Outdoor Travel Scene"),
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def resize_max_width(im: Image.Image, max_w: int = 1600) -> Image.Image:
    w, h = im.size
    if w <= max_w:
        return im
    new_h = int(round(h * (max_w / w)))
    return im.resize((max_w, new_h), Image.Resampling.LANCZOS)


def main():
    os.makedirs(os.path.dirname(LUT_PATH), exist_ok=True)
    os.makedirs(PREVIEWS_DIR, exist_ok=True)
    os.makedirs(CONTACT_DIR, exist_ok=True)
    os.makedirs(SIM_LOG_DIR, exist_ok=True)

    print("1. Baking 33x33x33 .cube LUT...")
    bake_cube_lut(LUT_PATH, size=33)
    lut_hash = sha256_file(LUT_PATH)
    print(f"   Saved {LUT_PATH} (SHA-256: {lut_hash})")

    lut, size = load_cube_lut(LUT_PATH)
    assert size == 33

    pairs = []
    for src_name, slug, title in SCENES:
        src_path = os.path.join(SRC_DIR, src_name)
        im = Image.open(src_path).convert("RGB")
        im = resize_max_width(im, 1400)
        srgb = np.asarray(im, dtype=np.float64) / 255.0

        print(f"2. Processing {title} ({im.size[0]}x{im.size[1]})...")
        sim_log = simulate_apple_log2_from_srgb(srgb)

        # Save simulated Apple Log 2 intermediate (8-bit PNG for repo size efficiency)
        sim_path = os.path.join(SIM_LOG_DIR, f"{slug}_sim_apple_log2.png")
        Image.fromarray((np.clip(sim_log, 0, 1) * 255.0 + 0.5).astype(np.uint8)).save(
            sim_path, optimize=True
        )

        # BEFORE: Neutral Apple Log 2 -> Rec.709 Gamma 2.4
        before = neutral_apple_log2_to_rec709(sim_log)
        before_path = os.path.join(PREVIEWS_DIR, f"{slug}_BEFORE.png")
        before_im = Image.fromarray((np.clip(before, 0, 1) * 255.0 + 0.5).astype(np.uint8))
        before_im.save(before_path, optimize=True)

        # AFTER: Apply delivered .cube via independent tetrahedral interpolation
        after = apply_cube_tetrahedral(sim_log, lut)
        after_path = os.path.join(PREVIEWS_DIR, f"{slug}_AFTER.png")
        after_im = Image.fromarray((np.clip(after, 0, 1) * 255.0 + 0.5).astype(np.uint8))
        after_im.save(after_path, optimize=True)

        pairs.append((title, before_im, after_im))

    print("3. Building contact sheet...")
    thumb_w, thumb_h = 560, 420
    pad = 24
    header_h = 80
    cols = 2
    rows = 8
    sheet_w = pad + cols * (thumb_w + pad)
    sheet_h = header_h + rows * (thumb_h + 44 + pad)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (16, 17, 20))
    draw = ImageDraw.Draw(sheet)

    draw.text((pad, 24), "GOLDEN DAYLIGHT CINEMA — BEFORE (Neutral Rec.709) vs AFTER (.cube LUT)", fill=(240, 232, 215))

    for idx, (title, b_im, a_im) in enumerate(pairs):
        y = header_h + idx * (thumb_h + 44 + pad)
        draw.text((pad, y), f"{title} — BEFORE", fill=(180, 185, 195))
        draw.text((pad + thumb_w + pad, y), f"{title} — AFTER (Golden Daylight Cinema)", fill=(235, 195, 120))

        b_thumb = b_im.copy()
        b_thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        a_thumb = a_im.copy()
        a_thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)

        sheet.paste(b_thumb, (pad, y + 24))
        sheet.paste(a_thumb, (pad + thumb_w + pad, y + 24))

    contact_path = os.path.join(CONTACT_DIR, "contact_sheet.png")
    sheet.save(contact_path, optimize=True)
    print(f"   Saved {contact_path}")


if __name__ == "__main__":
    main()
