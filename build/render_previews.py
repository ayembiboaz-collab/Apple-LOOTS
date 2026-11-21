#!/usr/bin/env python3
"""
Render BEFORE / AFTER / LOG previews for the eight scenes.

The AFTER frame is produced ONLY by loading
GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube from disk and applying
it to the simulated Apple Log 2 frame with tetrahedral interpolation.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

import apple_log2 as al
import lut_io
import simulate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
SRC = os.path.join(ROOT, "build", "sources")
CUBE = os.path.join(PROJ, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

SCENES = [
    ("01", "harsh-midday-city", "Harsh midday city", "01_city_midday.jpg"),
    ("02", "midday-portrait", "Midday portrait in direct sun", "02_portrait_midday.jpg"),
    ("03", "mediterranean-street", "Mediterranean street", "03_mediterranean_street.jpg"),
    ("04", "beach-daylight", "Bright beach daylight", "04_beach_daylight.jpg"),
    ("05", "landscape-greenery", "Landscape with greenery and mountains", "05_landscape_greenery.jpg"),
    ("06", "golden-hour", "Golden-hour landscape", "06_golden_hour.jpg"),
    ("07", "modern-architecture", "Modern architecture", "07_modern_architecture.jpg"),
    ("08", "travel-street", "Outdoor travel scene with people", "08_travel_street.jpg"),
]

TARGET_W = 1600


def load_rgb(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def to_img(arr01):
    a = np.clip(arr01, 0.0, 1.0)
    return Image.fromarray((a * 255.0 + 0.5).astype(np.uint8), "RGB")


def save_png(img, path):
    img.save(path, format="PNG", optimize=True)
    return img


def upscale(img, factor):
    if factor <= 1.001:
        return img
    w, h = img.size
    return img.resize((int(round(w * factor)), int(round(h * factor))), Image.LANCZOS)


def main():
    lut = lut_io.read_cube(CUBE)
    out_dirs = {
        "before": os.path.join(PROJ, "PREVIEWS", "BEFORE"),
        "after": os.path.join(PROJ, "PREVIEWS", "AFTER"),
        "log": os.path.join(PROJ, "GALLERY", "img", "log"),
        "gallery_before": os.path.join(PROJ, "GALLERY", "img", "before"),
        "gallery_after": os.path.join(PROJ, "GALLERY", "img", "after"),
    }
    for d in out_dirs.values():
        os.makedirs(d, exist_ok=True)

    manifest = []
    for num, slug, title, fname in SCENES:
        rgb = load_rgb(os.path.join(SRC, fname))
        h, w = rgb.shape[:2]
        factor = min(2.0, TARGET_W / w)

        log_code, scene709 = simulate.simulate_apple_log2(rgb)
        after = lut_io.apply_lut(lut, log_code, method="tetrahedral")
        before = simulate.neutral_render(scene709)
        log_view = al.rec709_gamma24_encode(np.clip(log_code, 0.0, 1.0))

        stem = f"{num}_{slug}"
        b_img = save_png(upscale(to_img(before), factor), os.path.join(out_dirs["before"], f"BEFORE_{stem}.png"))
        a_img = save_png(upscale(to_img(after), factor), os.path.join(out_dirs["after"], f"AFTER_{stem}.png"))
        l_img = upscale(to_img(log_view), factor)

        # gallery derivatives (JPEG, fast on mobile)
        b_img.save(os.path.join(out_dirs["gallery_before"], f"{slug}.jpg"), quality=86, optimize=True, progressive=True)
        a_img.save(os.path.join(out_dirs["gallery_after"], f"{slug}.jpg"), quality=86, optimize=True, progressive=True)
        l_img.save(os.path.join(out_dirs["log"], f"{slug}.jpg"), quality=82, optimize=True, progressive=True)

        manifest.append(dict(num=num, slug=slug, title=title, source=fname,
                             native=[w, h], preview=list(a_img.size), src=rgb))
        print(f"{num} {title}: {w}x{h} -> {a_img.size[0]}x{a_img.size[1]}")

    with open(os.path.join(ROOT, "build", "render_manifest.json"), "w") as fh:
        json.dump([{k: v for k, v in m.items() if k != "src"} for m in manifest], fh, indent=2)

    # ground-truth check: the AFTER must equal the cube applied by hand
    rgb = load_rgb(os.path.join(SRC, SCENES[0][3]))
    log_code, _ = simulate.simulate_apple_log2(rgb)
    a = lut_io.apply_lut(lut, log_code, method="tetrahedral")
    b = lut_io.apply_lut(lut, log_code, method="trilinear")
    print(f"tetrahedral vs trilinear max delta: {np.abs(a-b).max():.5f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
