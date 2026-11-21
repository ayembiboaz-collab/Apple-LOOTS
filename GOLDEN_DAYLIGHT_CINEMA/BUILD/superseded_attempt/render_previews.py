"""
render_previews.py — render the BEFORE / AFTER / neutral-reference stills.

CRITICAL: the AFTER images are produced by PARSING THE DELIVERED .cube FILE
from disk and interpolating it tetrahedrally. The grade function is never
called directly here, so the AFTER renders are genuine proof of the shipped
LUT rather than of an approximation of it.

Run:  python3 scripts/render_previews.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import grade
from applelog2 import gamma24_decode, srgb_inverse_eotf
from cube_io import apply_cube, read_cube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUT_PATH = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
LOG_DIR = os.path.join(ROOT, "work", "simulated_log2")
PREVIEW_DIR = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "PREVIEWS")
REF_DIR = os.path.join(PREVIEW_DIR, "REFERENCE")

SCENES = [
    ("01", "midday_city", "Harsh midday city", "Bright limestone facades, deep blue sky, hard architectural shadows."),
    ("02", "midday_portrait", "Midday portrait, direct sun", "Olive skin under hard overhead sun, white linen, sunlit stone behind."),
    ("03", "mediterranean_street", "Mediterranean street", "Sunlit plaster and open shade in the same frame, terracotta and foliage."),
    ("04", "bright_beach", "Bright beach daylight", "Pale sand, specular glare on water, white foam near clipping."),
    ("05", "landscape_greenery", "Landscape, greenery and mountains", "Broad foliage field, distant haze, large clean sky area."),
    ("06", "golden_hour_landscape", "Golden-hour landscape", "Already-warm light: the test for over-warming."),
    ("07", "modern_architecture", "Modern architecture", "Neutral concrete and glass: the test for an overall colour cast."),
    ("08", "travel_people_buildings", "Outdoor travel scene with people", "Mixed skin tones, half sun half shade, warm stone."),
]


# ---------------------------------------------------------------------------


def to_srgb_png(code_rec709_g24):
    """Rec.709 gamma-2.4 code values -> 8-bit sRGB pixels for viewing.

    The deliverable is Rec.709 / gamma 2.4. PNG viewers assume sRGB, so the
    stills are re-encoded: gamma 2.4 is linearised and re-encoded with the
    sRGB transfer function. Primaries are unchanged (Rec.709 and sRGB share
    them), so this is a pure transfer-function change and is LOSSLESS in
    appearance on a standard sRGB display.
    """
    disp_lin = gamma24_decode(np.clip(code_rec709_g24, 0.0, 1.0))
    srgb = srgb_inverse_eotf(disp_lin)
    return (np.clip(srgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def log2_to_viewable(P):
    """The simulated Apple Log 2 signal shown as-is, with no LUT.

    This is literally what an operator sees on an un-LUTted monitor: the log
    code values sent straight to a display. Shown here through the sRGB
    transfer function, which is how a PNG is displayed.
    """
    return (np.clip(P, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def save_png(arr, path, optimize=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr, mode="RGB").save(path, optimize=optimize, compress_level=9)
    return os.path.getsize(path)


def main():
    table, size, dmin, dmax, title = read_cube(LUT_PATH)
    print(f'parsed delivered LUT: "{title}"  {size}^3  domain {dmin} - {dmax}')

    os.makedirs(PREVIEW_DIR, exist_ok=True)
    os.makedirs(REF_DIR, exist_ok=True)

    manifest = []
    total = 0
    for num, key, label, note in SCENES:
        npy = os.path.join(LOG_DIR, f"{num}_{key}_LOG2.npy")
        P = np.load(npy).astype(np.float64)

        before = log2_to_viewable(P)
        after_code = apply_cube(P, table, size, dmin, dmax)
        after = to_srgb_png(after_code)
        neutral_code = grade.technical_only(P)
        neutral = to_srgb_png(neutral_code)

        b_path = os.path.join(PREVIEW_DIR, f"{num}_{key}_BEFORE.png")
        a_path = os.path.join(PREVIEW_DIR, f"{num}_{key}_AFTER.png")
        n_path = os.path.join(REF_DIR, f"{num}_{key}_NEUTRAL709.png")

        nb = save_png(before, b_path)
        na = save_png(after, a_path)
        # half resolution reference: supplementary, keeps the package small
        h, w = neutral.shape[:2]
        nref = np.asarray(
            Image.fromarray(neutral, "RGB").resize((w // 2, h // 2), Image.LANCZOS)
        )
        nn = save_png(nref, n_path)
        total += nb + na + nn

        manifest.append(
            dict(
                num=num,
                key=key,
                label=label,
                note=note,
                width=P.shape[1],
                height=P.shape[0],
                before=os.path.basename(b_path),
                after=os.path.basename(a_path),
                neutral=f"REFERENCE/{os.path.basename(n_path)}",
            )
        )
        print(
            f"  {num} {label:36s} {P.shape[1]}x{P.shape[0]}  "
            f"before {nb/1e6:.2f} MB  after {na/1e6:.2f} MB  ref {nn/1e6:.2f} MB"
        )

    with open(os.path.join(ROOT, "work", "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"total preview bytes: {total/1e6:.1f} MB")


if __name__ == "__main__":
    main()
