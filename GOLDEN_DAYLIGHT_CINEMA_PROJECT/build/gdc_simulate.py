"""
gdc_simulate.py -- build simulated Apple Log 2 / Apple Wide Gamut frames from
the real-world source photographs.

WHAT THIS IS
------------
Not iPhone footage.  There is no iPhone 17 Pro recording in this build, so the
eight scenes are documented *simulations* of an Apple Log 2 / Apple Wide Gamut
recording, derived from real photographs.  The simulation is deliberately
simple and fully invertible:

  1. Read the sRGB JPEG (8-bit, IEC 61966-2-1) that the photographer published.
  2. Undo the sRGB display transfer function -> linear-light sRGB               (float64)
  3. linear sRGB -> CIE XYZ (D65) -> linear Apple Wide Gamut, using the verified
     primaries in gdc_colour.py.  No chromatic adaptation is needed (all three
     spaces are D65).  Result is clamped at 0: the expansion never needs
     negative values for sRGB input, and clamping keeps the file honest.
  4. Encode with the verified Apple Log curve (Apple Log 2 = Apple Log curve,
     Apple Wide Gamut primaries) -> nominal 0..1 log code.
  5. Quantise to 10-bit-equivalent precision inside a 16-bit PNG
     (round(P * 65535)).

WHAT IS *NOT* DONE, AND WHY
---------------------------
* No highlight reconstruction.  The source JPEGs are 8-bit display-referred
  files; anything the camera clipped is gone.  We do not invent a highlight
  roll-off above display white, so the simulated files carry less highlight
  headroom than a real Apple Log 2 recording (real footage keeps ~3.5 stops of
  unused log range above display white; the simulation's log maximum sits at
  the code value for scene-linear 1.0 = 0.6946, and the top 30 % of the code
  range is unused).
* No noise added.  Shot noise in the photographs is whatever the original
  camera produced and whatever JPEG compression left behind.
* No camera colour matrix.  We assume the published sRGB rendering is a fair
  stand-in for the scene, i.e. an idealised "Standard" camera rendering.  Real
  Apple Log 2 data has Apple's own sensor-to-gamut matrix on top; that is one
  more reason these frames are labelled simulated everywhere.

LIMITATION, STATED UP FRONT
---------------------------
Dynamic range is limited by the 8-bit source (about 8 stops of usable
information), not by Apple Log 2.  Scenes where the photographer clipped the
sky stay clipped after the LUT as well; the LUT cannot recover them.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_colour as C
import gdc_config as CFG
import pngio

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_DIR = os.path.join(ROOT, "source_images")
LOG_DIR = os.path.join(ROOT, "simulated_log")


def load_srgb(path: str, long_edge: int | None) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if long_edge:
        w, h = im.size
        if max(w, h) > long_edge:
            s = long_edge / max(w, h)
            im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def srgb_image_to_apple_log2(im_srgb: np.ndarray) -> np.ndarray:
    lin = C.srgb_to_linear(im_srgb)
    xyz = lin @ C.REC709_TO_XYZ.T
    awg = xyz @ C.XYZ_TO_AWG.T
    awg = np.clip(awg, 0.0, None)
    p = C.apple_log2_encode(awg)
    return np.clip(p, 0.0, 1.0)


def save_log16(p: np.ndarray, path: str) -> None:
    q = np.round(np.clip(p, 0.0, 1.0) * 65535.0).astype(np.uint16)
    pngio.write_png_rgb16(path, q)


def load_log16(path: str) -> np.ndarray:
    return pngio.read_png(path).astype(np.float64) / 65535.0


def simulate_all(long_edge: int = CFG.PREVIEW_LONG_EDGE, quiet: bool = False) -> dict:
    os.makedirs(LOG_DIR, exist_ok=True)
    stats = {}
    for sc in CFG.SCENES:
        src = os.path.join(SRC_DIR, sc.file)
        im = load_srgb(src, long_edge)
        p = srgb_image_to_apple_log2(im)
        out = os.path.join(LOG_DIR, sc.file.replace(".jpg", "_applelog2.png"))
        save_log16(p, out)
        # round-trip check on the quantised file
        p2 = load_log16(out)
        lin = np.clip(C.apple_log2_decode(p2), 0, None)
        stats[sc.key] = {
            "source": f"source_images/{sc.file}",
            "simulated_log": f"simulated_log/{os.path.basename(out)}",
            "size": list(p.shape[1::-1]),
            "log_code_min": float(p.min()),
            "log_code_max": float(p.max()),
            "log_code_mean": float(p.mean()),
            "linear_y_mean": float(np.mean(lin @ C.AWG_LUMINANCE_WEIGHTS)),
            "quantisation_max_err_code": float(np.max(np.abs(p2 - p))),
            "below_black_fraction": float(np.mean(p < C.APPLE_LOG_PBLACK)),
            "log_top_used_fraction": float(np.mean(p > 0.9)),
        }
        if not quiet:
            print(f"  {sc.key:24s} {p.shape[1]}x{p.shape[0]}  "
                  f"log {p.min():.3f}..{p.max():.3f} mean {p.mean():.3f}")
    with open(os.path.join(LOG_DIR, "simulation_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)
    return stats


if __name__ == "__main__":
    long_edge = int(sys.argv[1]) if len(sys.argv) > 1 else CFG.PREVIEW_LONG_EDGE
    print(f"Simulating Apple Log 2 (Apple Wide Gamut) at long edge {long_edge} px")
    s = simulate_all(long_edge)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "size"} for k, v in list(s.items())[:2]}, indent=2))
