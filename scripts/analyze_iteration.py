#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantitative look-development analyser.

Measures BEFORE (neutral conversion) vs AFTER (grade) render pairs against the
project's visual targets, scene by scene:

  * overall: mean luma (must not get brighter), contrast (std), tonal extremes,
    clipping / crush percentages
  * warmth: R-B balance in mid-luma chromatic pixels (honey/amber target) vs
    white region (must stay believable, no yellow cast)
  * sky: saturation / value / hue behaviour in the blue region
  * foliage: hue & saturation behaviour in the green region
  * skin: hue & saturation stability in the skin region
"""
import os
import sys
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = os.path.join(ROOT, 'iterate')

SCENES = ['SCENE_01', 'SCENE_02', 'SCENE_03', 'SCENE_04',
          'SCENE_05', 'SCENE_06', 'SCENE_07', 'SCENE_08']

LUMA = np.array([0.2126, 0.7152, 0.0722])


def hsv(rgb01):
    r, g, b = rgb01[..., 0], rgb01[..., 1], rgb01[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    c = mx - mn
    H = np.zeros_like(mx)
    m = c > 1e-6
    i1 = m & (mx == r); H[i1] = 60.0 * (((g[i1] - b[i1]) / c[i1]) % 6.0)
    i2 = m & (mx == g) & ~i1; H[i2] = 60.0 * ((b[i2] - r[i2]) / c[i2] + 2.0)
    i3 = m & (mx == b) & ~i1 & ~i2; H[i3] = 60.0 * ((r[i3] - g[i3]) / c[i3] + 4.0)
    S = np.where(mx > 1e-6, c / np.maximum(mx, 1e-6), 0.0)
    return H, S, mx


def stats(img, name, verbose=True):
    y = img @ LUMA
    H, S, V = hsv(img)
    out = dict(
        mean=y.mean(), std=y.std(),
        p1=np.percentile(y, 1), p50=np.percentile(y, 50), p99=np.percentile(y, 99),
        clip=(y >= 254 / 255).mean() * 100, crush=(y <= 1 / 255).mean() * 100)
    # regions (hue masks on this image's own HSV)
    sky = (H > 190) & (H < 265) & (S > 0.15) & (V > 0.08) & (V < 0.97)
    fol = (H > 68) & (H < 165) & (S > 0.10)
    skin = (H > 10) & (H < 45) & (S > 0.10) & (S < 0.65) & (V > 0.10)
    whites = (V > 0.72) & (S < 0.13)
    mids_chrom = (V > 0.15) & (V < 0.75) & (S > 0.16)
    shadows = (V < 0.10)
    for key, m in [('sky', sky), ('fol', fol), ('skin', skin),
                   ('whites', whites), ('mids', mids_chrom), ('shad', shadows)]:
        n = int(m.sum())
        if n > 200:
            out[f'{key}_n'] = n
            out[f'{key}_sat'] = S[m].mean()
            out[f'{key}_hue'] = np.degrees(np.angle(np.exp(1j * np.radians(H[m])))).mean() \
                if key in ('sky', 'fol', 'skin') else np.nan
            out[f'{key}_v'] = V[m].mean()
            out[f'{key}_rb'] = (img[m][..., 0] - img[m][..., 2]).mean()
    return out


def pct(a, b):
    return (a - b) / b * 100.0 if b else float('nan')


def main():
    rows = []
    for sc in SCENES:
        fb = os.path.join(ITER, sc + '_BEFORE.jpg')
        fa = os.path.join(ITER, sc + '_AFTER.jpg')
        if not (os.path.exists(fb) and os.path.exists(fa)):
            continue
        before = np.asarray(Image.open(fb).convert('RGB'), float) / 255.0
        after = np.asarray(Image.open(fa).convert('RGB'), float) / 255.0
        sb, sa = stats(before, sc), stats(after, sc)
        print(f'== {sc} ' + '=' * 60)
        print(f'  luma mean {sb["mean"]:.3f}->{sa["mean"]:.3f} ({pct(sa["mean"], sb["mean"]):+.1f}%)   '
              f'std {sb["std"]:.3f}->{sa["std"]:.3f} ({pct(sa["std"], sb["std"]):+.1f}%)   '
              f'p1 {sb["p1"]:.3f}->{sa["p1"]:.3f}   p99 {sb["p99"]:.3f}->{sa["p99"]:.3f}   '
              f'clip% {sb["clip"]:.2f}->{sa["clip"]:.2f}   crush% {sb["crush"]:.2f}->{sa["crush"]:.2f}')
        for reg, label in [('sky', 'sky'), ('fol', 'foliage'), ('skin', 'skin'),
                           ('whites', 'whites'), ('mids', 'mids/chromatic'), ('shad', 'shadows')]:
            kb, ka = f'{reg}_n', f'{reg}_n'
            if kb in sb and ka in sa and sb.get(kb, 0) > 200 and sa.get(ka, 0) > 200:
                hs = f'hue {sb[f"{reg}_hue"]:6.1f}->{sa[f"{reg}_hue"]:6.1f}deg' \
                    if not np.isnan(sb[f'{reg}_hue']) else ''
                print(f'  {label:15s} n={sb[kb]:7d}  sat {sb[f"{reg}_sat"]:.3f}->{sa[f"{reg}_sat"]:.3f}'
                      f' ({pct(sa[f"{reg}_sat"], sb[f"{reg}_sat"]):+.1f}%)   '
                      f'V {sb[f"{reg}_v"]:.3f}->{sa[f"{reg}_v"]:.3f} ({pct(sa[f"{reg}_v"], sb[f"{reg}_v"]):+.1f}%)   '
                      f'R-B {sb[f"{reg}_rb"]:+.3f}->{sa[f"{reg}_rb"]:+.3f}   {hs}')
            else:
                print(f'  {label:15s} (region not significant in this scene)')
        rows.append((sc, sb, sa))
    print('\n== SUMMARY ACROSS SCENES ' + '=' * 45)
    for key in ['mean', 'std']:
        vals = [(sa[key] - sb[key]) / max(sb[key], 1e-6) * 100 for _, sb, sa in rows]
        print(f'  {key:6s} change: ' + '  '.join(f'{sc[-2:]}:{v:+.1f}%' for (sc, _, _), v in zip(rows, vals)))
    for reg in ['sky', 'fol', 'skin', 'whites', 'mids']:
        ds, dv, drb, dh = [], [], [], []
        for _, sb, sa in rows:
            if f'{reg}_sat' in sb and f'{reg}_sat' in sa:
                ds.append(pct(sa[f'{reg}_sat'], sb[f'{reg}_sat']))
                dv.append(pct(sa[f'{reg}_v'], sb[f'{reg}_v']))
                drb.append(sa[f'{reg}_rb'] - sb[f'{reg}_rb'])
                if not np.isnan(sb.get(f'{reg}_hue', np.nan)):
                    dh.append(sa[f'{reg}_hue'] - sb[f'{reg}_hue'])
        if ds:
            print(f'  {reg:7s} sat {np.mean(ds):+6.1f}%  V {np.mean(dv):+6.1f}%  '
                  f'dR-B {np.mean(drb):+.3f}' + (f'  dHue {np.mean(dh):+.1f}deg' if dh else ''))


if __name__ == '__main__':
    main()
