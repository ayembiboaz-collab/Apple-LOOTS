"""
dev_preview.py -- development contact sheet: BEFORE (reference transform) vs
AFTER (analytic pipeline).  Fast, low resolution, for iterating on the look.

This script is NOT used for any deliverable image; the deliverable previews are
rendered by gdc_render.py, which applies the delivered .cube file through an
independent LUT engine.
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_colour as C
import gdc_config as CFG
import gdc_grade as G
import pngio

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG_DIR = os.path.join(ROOT, "simulated_log")


def load_log(key: str, long_edge: int | None = None) -> np.ndarray:
    sc = CFG.SCENE_BY_KEY[key]
    path = os.path.join(LOG_DIR, sc.file.replace(".jpg", "_applelog2.png"))
    p = pngio.read_png(path).astype(np.float64) / 65535.0
    if long_edge:
        h, w, _ = p.shape
        if max(w, h) > long_edge:
            s = long_edge / max(w, h)
            im = Image.fromarray((p * 65535).astype(np.uint16).view if False else np.zeros((1, 1, 3), np.uint8))
            # resize via float channels to stay linear in the code domain
            out = []
            for i in range(3):
                ch = Image.fromarray(p[..., i].astype(np.float32), mode="F")
                out.append(np.asarray(ch.resize((round(w * s), round(h * s)), Image.LANCZOS)))
            p = np.stack(out, axis=-1).astype(np.float64)
    return p


DEF = G.GoldenDaylightCinema()


def _disp(codes):
    """Rec.709 gamma-2.4 code -> sRGB display code, so the review JPEG shows the
    look exactly as the browser/iOS gallery will (see gdc_render.py)."""
    return C.linear_to_srgb(C.gamma24_decode(codes))


def render(key: str, long_edge=800):
    p = load_log(key, long_edge)
    before = _disp(G.reference_rec709(p))
    after = _disp(DEF.apply_codes(p))
    return before, after


def sheet(keys, path, long_edge=800):
    rows = []
    for k in keys:
        b, a = render(k, long_edge)
        h, w, _ = b.shape
        row = np.concatenate([(b * 255).astype(np.uint8), np.full((h, 6, 3), 30, np.uint8),
                              (a * 255).astype(np.uint8)], axis=1)
        rows.append(row)
    W = max(r.shape[1] for r in rows)
    out = np.full((sum(r.shape[0] + 6 for r in rows), W, 3), 12, np.uint8)
    y = 0
    for r in rows:
        out[y:y + r.shape[0], :r.shape[1]] = r
        y += r.shape[0] + 6
    Image.fromarray(out).save(path, quality=90)
    print("wrote", path, out.shape)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    keys = CFG.ORDER if which == "all" else which.split(",")
    sheet(keys, "/tmp/preview.png", 780)
