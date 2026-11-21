#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bake the GOLDEN DAYLIGHT CINEMA look into a standalone 33x33x33 .cube 3D LUT.

Input domain : Apple Log 2 code values, full range [0,1] (Apple Wide Gamut, D65)
Output       : Rec.709 SDR code values, gamma 2.4 (display-referred)

The .cube line order follows the Adobe/Iridas convention: the red component
varies fastest, then green, then blue.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdc_core as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')

TITLE = 'GOLDEN DAYLIGHT CINEMA'
N = 33  # grid size


def build_grid(n=N):
    """Evaluate the full pipeline at every grid point -> (n^3, 3) output values."""
    ax = np.arange(n) / (n - 1)
    # cube order: R fastest, then G, then B
    r, g, b = np.meshgrid(ax, ax, ax, indexing='ij')  # r varies along last axis
    pts = np.stack([r.ravel(order='F'), g.ravel(order='F'), b.ravel(order='F')], axis=-1)
    # meshgrid with indexing='ij' then ravel('F') gives r fastest; verify by construction:
    # pt i has r = i % n, g = (i // n) % n, b = i // n^2
    return pts


def main():
    n = N
    ax = np.arange(n) / (n - 1)
    total = n ** 3
    out = np.empty((total, 3))
    # straightforward triple loop in cube order: b outer, g, r inner
    idx = 0
    chunk = []
    coords = []
    for bi in range(n):
        for gi in range(n):
            for ri in range(n):
                chunk.append((ax[ri], ax[gi], ax[bi]))
                coords.append((ri, gi, bi))
                idx += 1
    pts = np.array(chunk)
    # process in batches to keep memory bounded
    B = 65536
    for i in range(0, total, B):
        out[i:i + B] = G.pipeline_creative(pts[i:i + B])

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', newline='\n') as f:
        f.write(f'# {TITLE}\n')
        f.write('# Apple Log 2 / Apple Wide Gamut -> Rec.709 SDR (gamma 2.4)\n')
        f.write('# Standalone creative LUT: decodes Apple Log 2, converts Apple Wide\n')
        f.write('# Gamut to Rec.709, applies the GOLDEN DAYLIGHT CINEMA grade and\n')
        f.write('# encodes gamma 2.4. Input full range [0,1].\n')
        f.write(f'TITLE "{TITLE}"\n')
        f.write(f'LUT_3D_SIZE {n}\n')
        f.write('DOMAIN_MIN 0.0 0.0 0.0\n')
        f.write('DOMAIN_MAX 1.0 1.0 1.0\n')
        for i in range(total):
            r_, g_, b_ = out[i]
            f.write(f'{r_:.8f} {g_:.8f} {b_:.8f}\n')
    size_mb = os.path.getsize(OUT_PATH) / 1e6
    print(f'wrote {OUT_PATH} ({size_mb:.2f} MB, {total} entries)')
    # quick integrity summary
    print(f'output range: [{out.min():.6f}, {out.max():.6f}]  finite: {np.all(np.isfinite(out))}')
    return OUT_PATH


if __name__ == '__main__':
    main()
