"""
tune.py — fast scorecard used to steer the grade while developing the look.

Measures everything in DISPLAY-LINEAR so that hue and saturation numbers are
not polluted by the sRGB-vs-gamma-2.4 encoding difference. Runs the grade
function directly (not the baked .cube) at reduced resolution so iteration is
quick; the final look is always re-verified through the delivered .cube by
render_previews.py and validate.py.

Run:  python3 scripts/tune.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import grade
from applelog2 import REC709_LUMA, gamma24_decode, srgb_eotf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 3  # subsample factor

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

_CACHE = {}


def load(key):
    if key not in _CACHE:
        src = (
            np.asarray(Image.open(os.path.join(ROOT, "sources", f"{key}.png")).convert("RGB"))
            / 255.0
        )[::SCALE, ::SCALE]
        P = np.load(os.path.join(ROOT, "work", "simulated_log2", f"{key}_LOG2.npy")).astype(
            np.float64
        )[::SCALE, ::SCALE]
        _CACHE[key] = (srgb_eotf(src), P)  # source as DISPLAY-LINEAR
    return _CACHE[key]


def lin_hue_sat(lin):
    """Hue / saturation / luminance of display-linear RGB."""
    Y = np.einsum("...i,i->...", lin, REC709_LUMA)
    cb = lin[..., 2] - Y
    cr = lin[..., 0] - Y
    h = np.degrees(np.arctan2(-cb, cr)) % 360.0
    sat = np.sqrt(cb * cb + cr * cr) / np.maximum(Y, 1e-9)
    return h, sat, Y


def cmean(h):
    a = np.radians(h)
    return float(np.degrees(np.arctan2(np.sin(a).mean(), np.cos(a).mean())) % 360.0)


def adiff(a, b):
    return ((a - b + 180.0) % 360.0) - 180.0


REGIONS = {
    #  name        hue_lo hue_hi sat_lo sat_hi  Y_lo   Y_hi
    "sky": (205, 285, 0.12, 9.0, 0.18, 1.0),
    "foliage": (70, 165, 0.25, 9.0, 0.010, 0.60),
    "skin": (22, 60, 0.12, 0.70, 0.045, 0.60),
    "stone": (50, 95, 0.04, 0.22, 0.18, 0.90),
    "white": (0, 360, 0.00, 0.045, 0.45, 1.0),
    "shade": (0, 360, 0.00, 9.0, 0.0, 0.020),
}


def score(look=None, scenes=None, verbose=True):
    look = grade.LOOK if look is None else look
    scenes = SCENES if scenes is None else scenes
    agg = {}
    rows = []
    for key in scenes:
        src, P = load(key)
        out = gamma24_decode(grade.transform(P, look))  # display-linear

        hs, ss, ys = lin_hue_sat(src)
        ho, so, yo = lin_hue_sat(out)

        pct_s = np.percentile(ys, [5, 25, 50, 75, 95])
        pct_o = np.percentile(yo, [5, 25, 50, 75, 95])
        crush = float(np.mean(yo < 0.0008) * 100)
        clip = float(np.mean(out.min(-1) > 0.995) * 100)

        row = dict(scene=key, ratios=pct_o / np.maximum(pct_s, 1e-9), crush=crush, clip=clip)
        for name, (h0, h1, s0, s1, y0, y1) in REGIONS.items():
            if h0 == 0 and h1 == 360:
                hm = np.ones_like(hs, bool)
            elif h0 < h1:
                hm = (hs >= h0) & (hs <= h1)
            else:
                hm = (hs >= h0) | (hs <= h1)
            m = hm & (ss >= s0) & (ss <= s1) & (ys >= y0) & (ys <= y1)
            if m.sum() < 80:
                row[name] = None
                continue
            r = dict(
                n=int(m.sum()),
                dh=adiff(cmean(ho[m]), cmean(hs[m])),
                hs=cmean(hs[m]),
                ho=cmean(ho[m]),
                sr=float(so[m].mean() / max(ss[m].mean(), 1e-9)),
                so=float(so[m].mean()),
                yr=float(yo[m].mean() / max(ys[m].mean(), 1e-9)),
            )
            row[name] = r
            agg.setdefault(name, []).append(r)
        rows.append(row)

    if verbose:
        print(
            f"{'scene':26s} {'p5':>6s} {'p25':>6s} {'p50':>6s} {'p75':>6s} {'p95':>6s}"
            f" {'crush%':>7s} {'clip%':>6s}"
        )
        for r in rows:
            q = r["ratios"]
            print(
                f"{r['scene']:26s} {q[0]:6.2f} {q[1]:6.2f} {q[2]:6.2f} {q[3]:6.2f} {q[4]:6.2f}"
                f" {r['crush']:7.2f} {r['clip']:6.2f}"
            )
        print()
        print(f"{'region':10s} {'hue in':>8s} {'hue out':>8s} {'d hue':>7s} {'sat x':>7s} {'sat out':>8s} {'luma x':>7s}")
        for name in REGIONS:
            vals = agg.get(name, [])
            if not vals:
                continue
            w = np.array([v["n"] for v in vals], float)
            w = w / w.sum()
            print(
                f"{name:10s} {np.dot(w,[v['hs'] for v in vals]):8.1f}"
                f" {np.dot(w,[v['ho'] for v in vals]):8.1f}"
                f" {np.dot(w,[v['dh'] for v in vals]):+7.1f}"
                f" {np.dot(w,[v['sr'] for v in vals]):7.2f}"
                f" {np.dot(w,[v['so'] for v in vals]):8.3f}"
                f" {np.dot(w,[v['yr'] for v in vals]):7.2f}"
            )
        allr = np.array([r["ratios"] for r in rows])
        print()
        print(
            "MEAN luminance ratios  p5 %.2f  p25 %.2f  p50 %.2f  p75 %.2f  p95 %.2f   "
            "crush %.2f%%  clip %.2f%%"
            % (
                *allr.mean(0),
                np.mean([r["crush"] for r in rows]),
                np.mean([r["clip"] for r in rows]),
            )
        )
    return rows, agg


def probe_curve(look=None):
    """Synthetic probe: what the transform does to reference patches."""
    look = grade.LOOK if look is None else look
    from applelog2 import REC709_TO_AWG, apple_log_encode, apply_matrix

    def to_log2(lin709):
        return np.clip(apple_log_encode(apply_matrix(np.asarray(lin709, float), REC709_TO_AWG)), 0, 1)

    patches = {
        "neutral -3 st": [0.0225] * 3,
        "neutral -1 st": [0.09] * 3,
        "neutral 18%": [0.18] * 3,
        "neutral 90%": [0.90] * 3,
        "neutral +3 st": [1.44] * 3,
        "caucasian skin": [0.355, 0.215, 0.148],
        "olive skin": [0.200, 0.123, 0.081],
        "deep skin": [0.072, 0.042, 0.029],
        "sky zenith": [0.090, 0.165, 0.420],
        "sky horizon": [0.330, 0.400, 0.560],
        "cloud white": [0.640, 0.660, 0.700],
        "foliage sun": [0.085, 0.145, 0.040],
        "foliage shade": [0.020, 0.034, 0.013],
        "grass dry": [0.200, 0.170, 0.070],
        "warm stone": [0.380, 0.330, 0.250],
        "concrete": [0.300, 0.305, 0.310],
        "sea blue": [0.045, 0.150, 0.230],
    }
    print(f"{'patch':16s} {'in (disp-lin ref)':>26s} {'out disp-lin':>26s}  {'hue in':>7s} {'hue out':>8s} {'dh':>6s} {'satx':>6s}")
    for name, lin in patches.items():
        P = to_log2(lin)
        out = gamma24_decode(grade.transform(P, look))
        hi, si, yi = lin_hue_sat(np.array(lin))
        ho, so, yo = lin_hue_sat(out)
        print(
            f"{name:16s} {str(np.round(lin,3)):>26s} {str(np.round(out,4)):>26s}"
            f"  {float(hi):7.1f} {float(ho):8.1f} {adiff(float(ho),float(hi)):+6.1f}"
            f" {float(so)/max(float(si),1e-9):6.2f}"
        )


if __name__ == "__main__":
    if "--probe" in sys.argv:
        probe_curve()
    else:
        score()
