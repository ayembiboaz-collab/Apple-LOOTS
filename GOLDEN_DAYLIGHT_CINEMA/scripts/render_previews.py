#!/usr/bin/env python3
"""
Render BEFORE / AFTER previews for the 8 scenes and print quantitative
diagnostics. AFTER is produced by evaluating the ACTUAL delivered .cube file
(trilinear), not the in-memory function.
"""
import os, sys, glob
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden_daylight as gd
from cube_reader import CubeLUT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEWS = os.path.join(ROOT, "PREVIEWS")
CUBE = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

SCENES = [
    ("scene1_midday_city", "1. Harsh midday city"),
    ("scene2_midday_portrait", "2. Midday portrait in direct sunlight"),
    ("scene3_mediterranean_street", "3. Mediterranean street"),
    ("scene4_beach_daylight", "4. Bright beach daylight"),
    ("scene5_landscape_greenery", "5. Natural landscape with greenery"),
    ("scene6_golden_hour", "6. Golden-hour landscape"),
    ("scene7_modern_architecture", "7. Modern architecture"),
    ("scene8_travel_people", "8. Outdoor travel scene"),
]


def stats(name, rgb):
    lum = gd._luma(rgb)
    hue, sat = gd._hue_sat(rgb)
    return dict(lum=float(np.mean(lum)), p1=float(np.percentile(lum, 1)),
                p99=float(np.percentile(lum, 99)),
                hue=float(np.median(hue)), sat=float(np.mean(sat)))


def region_stats(rgb, mask):
    if mask.sum() == 0:
        return None
    sub = rgb[mask]
    lum = gd._luma(sub)
    hue, sat = gd._hue_sat(sub)
    return dict(n=int(mask.sum()), lum=float(np.mean(lum)),
                hue=float(np.median(hue)), sat=float(np.mean(sat)))


def masks(src):
    lum = gd._luma(src)
    hue, sat = gd._hue_sat(src)
    sky = ((hue > 195) & (hue < 250) & (lum > 0.30))
    fol = ((hue > 70) & (hue < 170) & (sat > 0.12))
    skin = ((hue > 10) & (hue < 50) & (sat > 0.10) & (sat < 0.55) & (lum > 0.15) & (lum < 0.85))
    return sky, fol, skin


def main():
    os.makedirs(PREVIEWS, exist_ok=True)
    lut = CubeLUT(CUBE)
    print(f"Loaded delivered cube: {CUBE}  size={lut.size}\n")
    for stem, label in SCENES:
        src_path = os.path.join(ROOT, "SOURCES", f"{stem}.png")
        im = Image.open(src_path).convert("RGB")
        src = np.asarray(im, dtype=np.float64) / 255.0

        log = gd.simulate_apple_log2_from_rec709(src)
        before = gd.view_log_as_rec709(log)
        after = np.clip(lut(log), 0.0, 1.0)

        Image.fromarray((np.clip(before, 0, 1) * 255).astype(np.uint8)).save(
            os.path.join(PREVIEWS, f"{stem}_BEFORE.png"))
        Image.fromarray((np.clip(after, 0, 1) * 255).astype(np.uint8)).save(
            os.path.join(PREVIEWS, f"{stem}_AFTER.png"))

        sky, fol, skin = masks(src)
        print(f"=== {label} ({stem}) ===")
        print(f"  src   : {stats('src', src)}")
        print(f"  before: {stats('bf', before)}")
        print(f"  after : {stats('af', after)}")
        for nm, m in (("sky", sky), ("foliage", fol), ("skin", skin)):
            s = region_stats(src, m)
            a = region_stats(after, m)
            if s and a:
                print(f"  {nm:8s} src hue/sat={s['hue']:.0f}/{s['sat']:.3f} lum={s['lum']:.3f}"
                      f"  | after hue/sat={a['hue']:.0f}/{a['sat']:.3f} lum={a['lum']:.3f}")
            else:
                print(f"  {nm:8s} (no pixels detected)")
        print()


if __name__ == "__main__":
    main()
