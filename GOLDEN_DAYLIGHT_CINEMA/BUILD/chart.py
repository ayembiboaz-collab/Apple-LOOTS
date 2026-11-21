#!/usr/bin/env python3
"""
chart.py -- synthetic reference chart + objective measurements.

Renders a grid of real-world-relevant patches (skin of several ethnicities,
sky, foliage, stone, golden-hour light, neutrals) through the SAME simulate ->
LUT path used for the scene previews, and reports per-patch errors against
ideal behaviour. This is the tuning instrument for the look.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade
import simulate
from cube import apply_cube, read_cube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUT = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

# ---- patch definitions: sRGB 0-255, grouped -------------------------------
GROUPS = {
    "skin_light":  [(244, 205, 184), (232, 188, 166), (216, 170, 148)],
    "skin_medium": [(198, 148, 118), (176, 128, 100), (150, 106,  82)],
    "skin_deep":   [(120,  80,  58), ( 96,  62,  44), ( 74,  46,  33)],
    "sky_zenith":  [( 42, 104, 186), ( 62, 124, 200), ( 88, 146, 214)],
    "sky_horizon": [(150, 190, 226), (176, 208, 234), (198, 220, 240)],
    "foliage":     [( 72, 106,  52), ( 96, 124,  62), ( 58,  88,  46)],
    "stone":       [(214, 198, 176), (186, 168, 146), (156, 138, 118)],
    "concrete":    [(198, 198, 196), (168, 168, 166), (138, 138, 136)],
    "golden_light":[(246, 196, 120), (236, 176,  96), (222, 154,  74)],
    "shadow_blue": [( 62,  70,  92), ( 46,  54,  76), ( 34,  40,  58)],
    "neutral":     [(250, 250, 250), (200, 200, 200), (128, 128, 128), (60, 60, 60)],
    "saturated":   [(220,  40,  40), ( 40, 200,  60), ( 40,  80, 220)],
}


def patches():
    names, keys, vals = [], [], []
    for g, cols in GROUPS.items():
        for c in cols:
            names.append(g)
            keys.append(f"{g}({c[0]},{c[1]},{c[2]})")
            vals.append(np.array(c, dtype=np.float64) / 255.0)
    return names, keys, np.array(vals)


def srgb_to_oklab(rgb):
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return grade.linear_to_oklab(lin)


def lab_hue(lab):
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0


def run(lut_path=LUT, verbose=True):
    table, meta = read_cube(lut_path)
    names, keys, srgb = patches()
    log2 = simulate.plate_to_apple_log2(srgb.reshape(1, -1, 3)).reshape(-1, 3)
    out = apply_cube(log2, table, meta["domain_min"], meta["domain_max"])
    before = grade.neutral_technical(log2)
    ref = srgb                      # ideal reference = source display colour

    # Measure in a display-referred space: `before` is the plain technical
    # decode of the same log frame, so in/out deltas describe the GRADE only.
    l_in, l_out = srgb_to_oklab(before), srgb_to_oklab(out)
    h_in, h_out = lab_hue(l_in), lab_hue(l_out)
    c_in = np.hypot(l_in[..., 1], l_in[..., 2])
    c_out = np.hypot(l_out[..., 1], l_out[..., 2])
    l_ref = srgb_to_oklab(ref)
    c_ref = np.hypot(l_ref[..., 1], l_ref[..., 2])
    hue_ok = (c_in > 0.02) & (c_out > 0.02)

    rows = []
    for i, k in enumerate(keys):
        rows.append(dict(
            patch=k, group=names[i],
            luma_in=float(l_in[i, 0]), luma_out=float(l_out[i, 0]),
            L_ref=float(l_ref[i, 0]),
            chroma_in=float(c_in[i]), chroma_out=float(c_out[i]),
            chroma_ref=float(c_ref[i]),
            chroma_ratio=float(c_out[i] / c_in[i]) if c_in[i] > 1e-6 else 1.0,
            hue_in=float(h_in[i]), hue_out=float(h_out[i]),
            hue_shift=(float(((h_out[i] - h_in[i] + 180) % 360) - 180)
                       if hue_ok[i] else float("nan")),
            luma_delta=float(l_out[i, 0] - l_in[i, 0]),
            b_out=float(l_out[i, 2]), a_out=float(l_out[i, 1]),
            r=float(out[i, 0]), g=float(out[i, 1]), b=float(out[i, 2]),
        ))
    if verbose:
        print(f"{'patch':26s} {'L-in':>6s} {'L-out':>6s} {'C-ratio':>8s} "
              f"{'hueΔ':>7s} {'b*out':>7s} {'ΔL':>7s}")
        for r in rows:
            print(f"{r['patch']:26s} {r['luma_in']:6.3f} {r['luma_out']:6.3f} "
                  f"{r['chroma_ratio']:8.3f} {r['hue_shift']:7.2f} {r['b_out']:7.4f} "
                  f"{r['luma_delta']:+7.3f}")
    return rows


if __name__ == "__main__":
    run()
