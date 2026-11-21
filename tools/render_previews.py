"""
Render BEFORE (neutral Apple Log 2 -> Rec.709 conversion) and AFTER
(the delivered .cube applied) for the eight preview scenes.

Output goes to GOLDEN_DAYLIGHT_CINEMA/ALT_PREVIEWS/ (not the canonical
PREVIEWS/ directory, which belongs to the main-line suite after the merge).

The source images are ordinary display-referred sRGB photographs. Apple Log 2
frames are SIMULATED as documented in VALIDATION_REPORT / README:

  sRGB JPEG -> sRGB EOTF -> linear Rec.709 (== Rec.709 primaries, D65)
  -> matrix to linear Apple Wide Gamut (D65)
  -> Apple Log 2 OETF (white paper constants)
  -> 10-bit quantization (round(v*1023)/1023)

This is NOT genuine iPhone 17 Pro sensor output; highlight values above 1.0
do not exist in the sources, so the highlight shoulder is exercised using
synthetic data in validate_lut.py instead.
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

from lut_core import (apple_log2_encode, apple_log2_decode, srgb_to_linear,
                      linear_to_srgb, M_R709_TO_AWG, M_AWG_TO_R709)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
SRC = os.path.join(HERE, 'source_images')
# NOTE (merge): writes to ALT_PREVIEWS so it cannot overwrite the canonical
# main-line deliverable renders in GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/.
OUT = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'ALT_PREVIEWS')
CUBE = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')
MAX_SIDE = 2048

SCENES = [
    ("01_midday_city",        "01_harsh_midday_city.jpg",        "Harsh midday city"),
    ("02_midday_portrait",    "02_midday_portrait.jpg",          "Midday portrait in direct sun"),
    ("03_mediterranean_street","03_mediterranean_street.jpg",    "Mediterranean street"),
    ("04_beach_daylight",     "04_beach_daylight.jpg",           "Bright beach daylight"),
    ("05_landscape_mountains","05_landscape_mountains.jpg",       "Natural landscape, greenery & mountains"),
    ("06_golden_hour",        "06_golden_hour.jpg",              "Golden-hour landscape"),
    ("07_modern_architecture","07_modern_architecture.jpg",       "Modern architecture"),
    ("08_travel_people",      "08_travel_people.jpg",            "Outdoor travel scene with people"),
]


def load_cube(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().splitlines()
    size = None
    vals = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith('#'):
            continue
        parts = s.split()
        key = parts[0].upper()
        if key == 'LUT_3D_SIZE':
            size = int(parts[1])
        elif key in ('TITLE', 'COMMENT', 'DOMAIN_MIN', 'DOMAIN_MAX', 'LUT_1D_SIZE'):
            continue
        else:
            vals.append([float(parts[0]), float(parts[1]), float(parts[2])])
    lut = np.array(vals, dtype=np.float64).reshape(size, size, size, 3)
    return size, lut


def apply_cube_trilinear(log_rgb, lut, size):
    """Trilinear interpolation of a 3D cube. log_rgb: (...,3) in [0,1]."""
    p = np.clip(log_rgb, 0.0, 1.0) * (size - 1)
    i0 = np.floor(p).astype(np.int64)
    i1 = np.minimum(i0 + 1, size - 1)
    t = p - i0
    # index order: axis0=B, axis1=G, axis2=R
    def corner(ib, ig, ir):
        return lut[ib, ig, ir]
    c000 = corner(i0[..., 2], i0[..., 1], i0[..., 0])
    c001 = corner(i0[..., 2], i0[..., 1], i1[..., 0])
    c010 = corner(i0[..., 2], i1[..., 1], i0[..., 0])
    c011 = corner(i0[..., 2], i1[..., 1], i1[..., 0])
    c100 = corner(i1[..., 2], i0[..., 1], i0[..., 0])
    c101 = corner(i1[..., 2], i0[..., 1], i1[..., 0])
    c110 = corner(i1[..., 2], i1[..., 1], i0[..., 0])
    c111 = corner(i1[..., 2], i1[..., 1], i1[..., 0])
    tr, tg, tb = t[..., 0:1], t[..., 1:2], t[..., 2:3]
    c00 = c000 * (1 - tr) + c001 * tr
    c01 = c010 * (1 - tr) + c011 * tr
    c10 = c100 * (1 - tr) + c101 * tr
    c11 = c110 * (1 - tr) + c111 * tr
    c0 = c00 * (1 - tg) + c01 * tg
    c1 = c10 * (1 - tg) + c11 * tg
    return c0 * (1 - tb) + c1 * tb


def simulate_apple_log2(rgb_srgb):
    lin709 = srgb_to_linear(rgb_srgb)
    lin_awg = lin709 @ M_R709_TO_AWG.T
    log_enc = apple_log2_encode(np.clip(lin_awg, 0.0, None))
    # 10-bit quantization, as delivered by the camera
    return np.round(log_enc * 1023.0) / 1023.0


def prep(img_path):
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    return np.asarray(img, dtype=np.float64) / 255.0


def to_png(path, rgb01_srgb):
    arr = np.clip(rgb01_srgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(arr, 'RGB').save(path, 'PNG', optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    size, lut = load_cube(CUBE)
    print(f"Loaded cube {CUBE} ({size}^3)")
    manifest = []
    for slug, fname, title in SCENES:
        src = os.path.join(SRC, fname)
        rgb = prep(src)
        log_enc = simulate_apple_log2(rgb)
        # BEFORE: neutral Apple Log 2 -> Rec.709 conversion (no creative grade)
        lin_neutral = apple_log2_decode(log_enc) @ M_AWG_TO_R709.T
        before = linear_to_srgb(np.clip(lin_neutral, 0.0, None))
        # AFTER: the actual delivered .cube applied to the simulated log frame
        codes = apply_cube_trilinear(log_enc.reshape(-1, 3), lut, size).reshape(rgb.shape)
        after = linear_to_srgb(np.power(np.clip(codes, 0.0, 1.0), 2.4))
        b_path = os.path.join(OUT, f"{slug}_BEFORE.png")
        a_path = os.path.join(OUT, f"{slug}_AFTER.png")
        to_png(b_path, before)
        to_png(a_path, after)
        manifest.append({"scene": slug, "title": title,
                         "before": os.path.basename(b_path), "after": os.path.basename(a_path)})
        print(f"{slug:26s} {rgb.shape[1]}x{rgb.shape[0]}  -> {os.path.basename(b_path)}, {os.path.basename(a_path)}")
    with open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)


if __name__ == '__main__':
    main()
