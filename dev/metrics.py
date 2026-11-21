"""
metrics.py -- region-level BEFORE/AFTER statistics used to tune the look.

Regions are segmented from the BEFORE (neutral) frame in OkLab, so the mask
describes what is actually in the frame rather than what the grade did to it.

    python3 dev/metrics.py
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

import look as L
from colorlib import rec709_gamma_decode, linear_to_oklab
import scenes as S

REGIONS = {
    'sky':      dict(h=(200, 285), L=(0.30, 1.01), C=(0.015, 1.0)),
    'foliage':  dict(h=(85, 175),  L=(0.06, 0.85), C=(0.020, 1.0)),
    'skin':     dict(h=(25, 85),   L=(0.20, 0.92), C=(0.030, 1.0)),
    'neutral':  dict(C=(0.0, 0.020), L=(0.55, 1.01)),
    'white':    dict(C=(0.0, 0.030), L=(0.85, 1.01)),
    'shadow':   dict(C=(0.0, 1.0), L=(0.0, 0.18)),
    'midtone':  dict(C=(0.0, 1.0), L=(0.30, 0.70)),
}


def oklch(code):
    lin = np.clip(rec709_gamma_decode(code), 0.0, None)
    lab = linear_to_oklab(lin)
    Lv = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    return Lv, C, h, a, b


def region_mask(Lv, C, h, spec):
    m = np.ones(Lv.shape, dtype=bool)
    if 'h' in spec:
        lo, hi = spec['h']
        m &= (h >= lo) & (h <= hi)
    if 'L' in spec:
        lo, hi = spec['L']
        m &= (Lv >= lo) & (Lv <= hi)
    if 'C' in spec:
        lo, hi = spec['C']
        m &= (C >= lo) & (C <= hi)
    return m


def analyse(before, after):
    Lb, Cb, hb, ab, bb = oklch(before)
    La, Ca, ha, aa, ba = oklch(after)
    out = {}
    for name, spec in REGIONS.items():
        m = region_mask(Lb, Cb, hb, spec)
        n = int(m.sum())
        if n < 200:
            out[name] = dict(px=n)
            continue
        # hue difference wrapped to +-180
        dh = (ha[m] - hb[m] + 180.0) % 360.0 - 180.0
        out[name] = dict(
            px=n,
            dL=float((La[m] - Lb[m]).mean()),
            dL_pct=float(100 * (La[m].mean() / max(Lb[m].mean(), 1e-9) - 1)),
            dC_pct=float(100 * (Ca[m].mean() / max(Cb[m].mean(), 1e-9) - 1)),
            dh=float(dh.mean()),
            dE=float(np.sqrt(((La[m] - Lb[m]) ** 2 + (aa[m] - ab[m]) ** 2
                              + (ba[m] - bb[m]) ** 2).mean()) * 100),
            b_before=float(bb[m].mean()), b_after=float(ba[m].mean()),
            clip_before=float((before[m].max(axis=-1) >= 0.9995).mean()),
            clip_after=float((after[m].max(axis=-1) >= 0.9995).mean()),
        )
    # global
    out['ALL'] = dict(
        px=int(Lb.size),
        dL=float((La - Lb).mean()),
        dC_pct=float(100 * (Ca.mean() / max(Cb.mean(), 1e-9) - 1)),
        dE=float(np.sqrt(((La - Lb) ** 2 + (aa - ab) ** 2
                          + (ba - bb) ** 2).mean()) * 100),
        clip_before=float((before.max(axis=-1) >= 0.9995).mean()),
        clip_after=float((after.max(axis=-1) >= 0.9995).mean()),
        luma_before=float(before.mean()), luma_after=float(after.mean()),
    )
    return out


def main():
    prev = os.path.join(S.PROJ, 'PREVIEWS')
    rows = {}
    for slug, fn, label, _ in S.SCENES:
        fb = os.path.join(prev, f'{slug}_BEFORE.png')
        fa = os.path.join(prev, f'{slug}_AFTER.png')
        if not (os.path.exists(fb) and os.path.exists(fa)):
            print('missing', slug)
            continue
        from PIL import Image
        before = np.asarray(Image.open(fb).convert('RGB'), dtype=np.float64) / 255.0
        after = np.asarray(Image.open(fa).convert('RGB'), dtype=np.float64) / 255.0
        rows[slug] = analyse(before, after)

    print(f"{'scene':28s} {'region':9s} {'px':>8s} {'dL%':>7s} {'dC%':>7s} "
          f"{'dh':>6s} {'dE':>6s} {'b':>7s} {'clipA%':>7s}")
    for slug, r in rows.items():
        for name, v in r.items():
            if v['px'] < 200:
                continue
            print(f"{slug:28s} {name:9s} {v['px']:8d} {v.get('dL_pct',0):7.2f} "
                  f"{v.get('dC_pct',0):7.2f} {v.get('dh',0):6.2f} "
                  f"{v.get('dE',0):6.2f} {v.get('b_after',0):7.4f} "
                  f"{100*v.get('clip_after',0):7.3f}")
    with open(os.path.join(S.HERE, 'metrics.json'), 'w') as fh:
        json.dump(rows, fh, indent=2)


if __name__ == '__main__':
    main()
