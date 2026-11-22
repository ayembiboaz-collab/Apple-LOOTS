"""
gdc_render.py -- render the eight BEFORE / AFTER previews.

AFTER images are produced by reading the delivered .cube file with
lut_engine.py (an independent implementation, tetrahedral interpolation) --
never by calling the grading code.  BEFORE images are the plain, verified
Apple Log 2 -> Rec.709 conversion with no creative treatment.

Both sides start from the *same* quantised input: the simulated Apple Log 2
frame is quantised to 10 bits per channel (what an iPhone records) before either
transform is applied, so neither side gets an unfair precision advantage.

Display encoding of the PNGs
----------------------------
The LUT (and every number in the validation report) is Rec.709 SDR with a PURE
gamma 2.4 transfer function.  A PNG without an embedded profile is interpreted
as sRGB by browsers and by iOS, and sRGB's transfer function differs from a pure
2.4 power law (it is a piecewise curve with a 2.4 exponent and a linear toe), so
writing raw 2.4 codes into an untagged PNG would display slightly dark.
The preview PNGs are therefore converted from Rec.709 gamma-2.4 code to sRGB
encoding with the exact inverse/forward pair:

    sRGB_code = OETF_sRGB(EOTF_gamma24(rec709_code))

That is a display-encoding change only; it does not touch the grade, and the
.cube itself stays Rec.709 gamma 2.4 exactly as specified.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_colour as C
import gdc_config as CFG
import gdc_grade as G
import gdc_simulate as SIM
import lut_engine
import pngio

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DELIV = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
LUT_PATH = os.path.join(DELIV, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
PREV = os.path.join(DELIV, "PREVIEWS")


def to_srgb_display(codes: np.ndarray) -> np.ndarray:
    """Rec.709 gamma-2.4 code -> sRGB code (display encoding only)."""
    return C.linear_to_srgb(C.gamma24_decode(codes))


def save_png(path: str, codes: np.ndarray) -> None:
    disp = to_srgb_display(codes)
    q = np.round(np.clip(disp, 0.0, 1.0) * 255.0).astype(np.uint8)
    pngio.write_png_rgb8(path, q, adaptive=True)


def quantise10(p: np.ndarray) -> np.ndarray:
    return np.round(np.clip(p, 0.0, 1.0) * 1023.0) / 1023.0


def render_scene(scene: CFG.Scene, lut: lut_engine.LUT3D, long_edge: int,
                 save: bool = True, method: str = "tetra") -> dict:
    src = os.path.join(ROOT, "source_images", scene.file)
    srgb_img = SIM.load_srgb(src, long_edge)
    p_full = SIM.srgb_image_to_apple_log2(srgb_img)
    p = quantise10(p_full)

    before = G.reference_rec709(p)
    after = lut.apply(p, method=method)

    info = {
        "scene": scene.key,
        "size": [int(p.shape[1]), int(p.shape[0])],
        "input_sha256": hashlib.sha256(np.ascontiguousarray(p).tobytes()).hexdigest(),
        "before_sha256": hashlib.sha256(np.ascontiguousarray(before).tobytes()).hexdigest(),
        "after_sha256": hashlib.sha256(np.ascontiguousarray(after).tobytes()).hexdigest(),
        "lut_method": method,
    }
    if save:
        os.makedirs(PREV, exist_ok=True)
        num = f"{scene.number:02d}"
        save_png(os.path.join(PREV, f"{num}_{scene.key}_BEFORE.png"), before)
        save_png(os.path.join(PREV, f"{num}_{scene.key}_AFTER.png"), after)
    return info


def render_all(long_edge: int = CFG.PREVIEW_LONG_EDGE, save: bool = True) -> dict:
    lut = lut_engine.LUT3D.from_cube(LUT_PATH)
    out = {"lut": os.path.relpath(LUT_PATH, ROOT),
           "lut_sha256": hashlib.sha256(open(LUT_PATH, "rb").read()).hexdigest(),
           "long_edge": long_edge, "scenes": {}}
    for sc in CFG.SCENES:
        t0 = time.time()
        out["scenes"][sc.key] = render_scene(sc, lut, long_edge, save=save)
        out["scenes"][sc.key]["seconds"] = round(time.time() - t0, 2)
        print(f"  {sc.key:22s} {out['scenes'][sc.key]['size']} "
              f"({out['scenes'][sc.key]['seconds']}s)")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else CFG.PREVIEW_LONG_EDGE
    print(f"Rendering BEFORE/AFTER at long edge {n}px from {LUT_PATH}")
    info = render_all(n)
    hpath = os.path.join(ROOT, "validation", "render_hashes.json")
    os.makedirs(os.path.dirname(hpath), exist_ok=True)
    with open(hpath, "w") as f:
        json.dump(info, f, indent=2)
    print("wrote", hpath)
