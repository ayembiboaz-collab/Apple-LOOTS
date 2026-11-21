"""
scan.py — compact scorecard for candidate look parameters.

Usage:  python3 scripts/scan.py '<json overrides>' ['<json overrides>' ...]
Each override dict is merged over grade.LOOK and scored.
"""

from __future__ import annotations

import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import grade
import tune
from applelog2 import REC709_TO_AWG, apple_log_encode, apply_matrix, gamma24_decode

PATCHES = {
    "grey -3st": [0.0225] * 3,
    "grey -1st": [0.09] * 3,
    "grey 18%": [0.18] * 3,
    "grey 90%": [0.90] * 3,
    "concrete": [0.300, 0.305, 0.310],
    "caucasian": [0.355, 0.215, 0.148],
    "olive skin": [0.200, 0.123, 0.081],
    "deep skin": [0.072, 0.042, 0.029],
    "sky zenith": [0.090, 0.165, 0.420],
    "sky horiz": [0.330, 0.400, 0.560],
    "foliage sun": [0.085, 0.145, 0.040],
    "warm stone": [0.380, 0.330, 0.250],
}


def to_log2(lin709):
    return np.clip(
        apple_log_encode(apply_matrix(np.asarray(lin709, float), REC709_TO_AWG)), 0, 1
    )


def summary(look, label=""):
    print(f"\n########## {label} ##########")
    print(
        f"{'patch':12s} {'out display-linear':>24s} {'R/B':>6s} {'Y x':>6s} {'hue':>7s} "
        f"{'dh':>6s} {'sat':>6s} {'satx':>6s}"
    )
    for name, lin in PATCHES.items():
        out = gamma24_decode(grade.transform(to_log2(lin), look))
        hi, si, yi = tune.lin_hue_sat(np.array(lin))
        ho, so, yo = tune.lin_hue_sat(out)
        rb = out[0] / max(out[2], 1e-9)
        print(
            f"{name:12s} {str(np.round(out,4)):>24s} {rb:6.3f} {float(yo)/float(yi):6.2f}"
            f" {float(ho):7.1f} {tune.adiff(float(ho), float(hi)):+6.1f}"
            f" {float(so):6.3f} {float(so)/max(float(si),1e-9) if float(si)>0.01 else float('nan'):6.2f}"
        )
    rows, agg = tune.score(look, verbose=False)
    allr = np.array([r["ratios"] for r in rows])
    m = allr.mean(0)
    print(
        f"  LUMA RATIOS p5 {m[0]:.2f}  p25 {m[1]:.2f}  p50 {m[2]:.2f}  p75 {m[3]:.2f} "
        f" p95 {m[4]:.2f}   crush {np.mean([r['crush'] for r in rows]):.2f}%"
        f"  clip {np.mean([r['clip'] for r in rows]):.2f}%"
    )
    for name in tune.REGIONS:
        vals = agg.get(name, [])
        if not vals:
            continue
        w = np.array([v["n"] for v in vals], float)
        w /= w.sum()
        print(
            f"  {name:9s} hue {np.dot(w,[v['hs'] for v in vals]):6.1f} ->"
            f" {np.dot(w,[v['ho'] for v in vals]):6.1f} ({np.dot(w,[v['dh'] for v in vals]):+5.1f})"
            f"   satx {np.dot(w,[v['sr'] for v in vals]):5.2f}"
            f"  sat {np.dot(w,[v['so'] for v in vals]):5.3f}"
            f"  lumax {np.dot(w,[v['yr'] for v in vals]):5.2f}"
        )


def main():
    args = sys.argv[1:] or ["{}"]
    for a in args:
        look = copy.deepcopy(grade.LOOK)
        ov = json.loads(a)
        for k, v in ov.items():
            look[k] = tuple(v) if isinstance(v, list) else v
        summary(look, a[:110])


if __name__ == "__main__":
    main()
