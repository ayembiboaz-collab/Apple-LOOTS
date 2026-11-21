"""
analyse.py — measurement tool used to steer the grade.

Reports, per scene, measured in a common sRGB display space so the numbers
are directly comparable:
  * mean / percentile luminance of the source vs the graded render
  * hue and saturation of automatically located sky / foliage / skin / stone
    / neutral regions
  * clipping and black-crush counts

Run:  python3 scripts/analyse.py [scene_number ...]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import grade
from applelog2 import REC709_LUMA, gamma24_decode, srgb_eotf, srgb_inverse_eotf
from cube_io import apply_cube, read_cube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUT_PATH = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

SCENES = [
    "01_midday_city",
    "02_midday_portrait",
    "03_mediterranean_street",
    "04_bright_beach",
    "05_landscape_greenery",
    "06_golden_hour_landscape",
    "07_modern_architecture",
    "08_travel_people_buildings",
]


def srgb_stats(rgb_srgb):
    lin = srgb_eotf(rgb_srgb)
    Y = np.einsum("...i,i->...", lin, REC709_LUMA)
    return Y


def hue_sat(rgb):
    Y, cb, cr = grade.to_ych(rgb)
    chroma = np.sqrt(cb * cb + cr * cr)
    return grade.hue_angle(cb, cr), chroma / np.maximum(Y, 1e-9), Y


def region_report(name, mask, src, out):
    n = int(mask.sum())
    if n < 60:
        return f"    {name:11s} (no pixels found)"
    hs, ss, ys = hue_sat(src[mask])
    ho, so, yo = hue_sat(out[mask])
    # circular mean of hue
    def cmean(h):
        a = np.radians(h)
        return float(np.degrees(np.arctan2(np.sin(a).mean(), np.cos(a).mean())) % 360.0)

    return (
        f"    {name:11s} n={n:7d}  hue {cmean(hs):6.1f} -> {cmean(ho):6.1f} "
        f"({((cmean(ho)-cmean(hs)+180)%360)-180:+6.1f})   "
        f"sat {ss.mean():5.3f} -> {so.mean():5.3f} ({so.mean()/max(ss.mean(),1e-9):5.2f}x)   "
        f"Y {ys.mean():5.3f} -> {yo.mean():5.3f} ({yo.mean()/max(ys.mean(),1e-9):5.2f}x)"
    )


def main():
    table, size, dmin, dmax, _ = read_cube(LUT_PATH)
    wanted = sys.argv[1:]

    for key in SCENES:
        if wanted and not any(key.startswith(w) for w in wanted):
            continue
        src = (
            np.asarray(Image.open(os.path.join(ROOT, "sources", f"{key}.png")).convert("RGB"))
            / 255.0
        )
        P = np.load(os.path.join(ROOT, "work", "simulated_log2", f"{key}_LOG2.npy")).astype(
            np.float64
        )
        out_code = apply_cube(P, table, size, dmin, dmax)
        out = srgb_inverse_eotf(gamma24_decode(out_code))  # to the same sRGB space

        Ys, Yo = srgb_stats(src), srgb_stats(out)
        hs, ss, ys = hue_sat(src)

        print(f"\n=== {key} ===")
        ps = np.percentile(Ys, [1, 5, 25, 50, 75, 95, 99])
        po = np.percentile(Yo, [1, 5, 25, 50, 75, 95, 99])
        print("    display-linear luminance percentiles (source -> graded)")
        for lbl, a, b in zip(["p1", "p5", "p25", "p50", "p75", "p95", "p99"], ps, po):
            print(f"      {lbl:>4s} {a:8.5f} -> {b:8.5f}   ({b/max(a,1e-9):5.2f}x)")
        print(
            f"    crushed (<0.3/255): src {np.mean(src.max(-1) < 0.0012)*100:5.2f}%  "
            f"-> {np.mean(out.max(-1) < 0.0012)*100:5.2f}%"
            f"   |  clipped (>254/255): src {np.mean(src.min(-1) > 0.996)*100:5.2f}%"
            f"  -> {np.mean(out.min(-1) > 0.996)*100:5.2f}%"
        )

        bright = ys > 0.12
        sat_ok = ss > 0.10
        masks = {
            "sky": (hs > 200) & (hs < 290) & sat_ok & (ys > 0.25),
            "cyan-ish": (hs > 170) & (hs < 205) & (ss > 0.14) & (ys > 0.2),
            "foliage": (hs > 75) & (hs < 160) & (ss > 0.22) & (ys > 0.02),
            "skin/warm": (hs > 25) & (hs < 62) & (ss > 0.14) & (ys > 0.10) & (ys < 0.80),
            "stone": (hs > 55) & (hs < 95) & (ss > 0.05) & (ss < 0.22) & (ys > 0.25),
            "near-white": (ss < 0.05) & (ys > 0.62),
            "shadow": ys < 0.045,
        }
        for n, m in masks.items():
            print(region_report(n, m, src, out))


if __name__ == "__main__":
    main()
