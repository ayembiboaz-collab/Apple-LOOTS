#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply a 3D .cube LUT to an image using tetrahedral interpolation (the method
used by DaVinci Resolve and other professional LUT engines).

Usage:
    python3 apply_lut.py input.png lut.cube output.png
"""
import os
import sys
import numpy as np
from PIL import Image


def read_cube(path):
    """Parse an Adobe/Iridas .cube 3D LUT. Returns (lut ndarray (n,n,n,3), n)."""
    size = None
    title = ''
    vals = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            key = parts[0].upper()
            if key == 'TITLE':
                title = ' '.join(parts[1:]).strip('"')
            elif key == 'LUT_3D_SIZE':
                size = int(parts[1])
            elif key in ('DOMAIN_MIN', 'DOMAIN_MAX', 'LUT_1D_SIZE'):
                continue
            else:
                try:
                    vals.append([float(x) for x in parts[:3]])
                except ValueError:
                    continue
    if size is None:
        raise ValueError('LUT_3D_SIZE not found in ' + path)
    arr = np.asarray(vals, dtype=np.float64)
    if arr.shape != (size ** 3, 3):
        raise ValueError(f'expected {size**3} entries, got {arr.shape[0]}')
    # line order: R fastest, then G, then B -> reshape (B, G, R, 3) then transpose
    lut = arr.reshape(size, size, size, 3).transpose(2, 1, 0, 3)
    return np.ascontiguousarray(lut), size, title


def apply_tetrahedral(lut, rgb):
    """Tetrahedral interpolation of a (...,3) image in [0,1] through lut (n,n,n,3)."""
    n = lut.shape[0]
    rgb = np.clip(rgb, 0.0, 1.0)
    f = rgb * (n - 1)
    i = np.floor(f).astype(np.int64)
    i = np.clip(i, 0, n - 2)
    d = f - i
    dr, dg, db = d[..., 0], d[..., 1], d[..., 2]
    r0, g0, b0 = i[..., 0], i[..., 1], i[..., 2]

    c000 = lut[r0, g0, b0]
    c100 = lut[r0 + 1, g0, b0]
    c010 = lut[r0, g0 + 1, b0]
    c110 = lut[r0 + 1, g0 + 1, b0]
    c001 = lut[r0, g0, b0 + 1]
    c101 = lut[r0 + 1, g0, b0 + 1]
    c011 = lut[r0, g0 + 1, b0 + 1]
    c111 = lut[r0 + 1, g0 + 1, b0 + 1]

    # six tetrahedral decompositions of the unit cell around the 000->111 diagonal
    out = np.empty_like(c000)
    m1 = (dr >= dg) & (dg >= db)   # r >= g >= b
    m2 = (dr >= db) & (db > dg)    # r >= b > g
    m3 = (db > dr) & (dr >= dg)    # b > r >= g
    m4 = (dg > dr) & (dr >= db)    # g > r >= b
    m5 = (dg >= db) & (db > dr)    # g >= b > r
    m6 = (db > dg) & (dg > dr)     # b > g > r

    def acc(mask, v0, v1, v2, v3, w0, w1, w2, w3):
        out[mask] = (v0[mask] * w0[mask][..., None] + v1[mask] * w1[mask][..., None] +
                     v2[mask] * w2[mask][..., None] + v3[mask] * w3[mask][..., None])

    acc(m1, c000, c100, c110, c111, 1 - dr, dr - dg, dg - db, db)
    acc(m2, c000, c100, c101, c111, 1 - dr, dr - db, db - dg, dg)
    acc(m3, c000, c001, c101, c111, 1 - db, db - dr, dr - dg, dg)
    acc(m4, c000, c010, c110, c111, 1 - dg, dg - dr, dr - db, db)
    acc(m5, c000, c010, c011, c111, 1 - dg, dg - db, db - dr, dr)
    acc(m6, c000, c001, c011, c111, 1 - db, db - dg, dg - dr, dr)
    return out


def self_test():
    """An affine LUT must reproduce exactly under tetrahedral interpolation."""
    rng = np.random.RandomState(1)
    n = 33
    ax = np.arange(n) / (n - 1)
    r, g, b = np.meshgrid(ax, ax, ax, indexing='ij')
    M = np.array([[0.85, 0.05, 0.02], [0.03, 0.88, 0.04], [0.01, 0.06, 0.85]])
    off = np.array([0.02, 0.015, 0.01])
    lin = np.stack([r, g, b], -1) @ M.T + off
    lut = lin.reshape(n, n, n, 3)  # affine, unclipped; already R-fastest layout
    img = rng.rand(1000, 3)
    out = apply_tetrahedral(lut, img)
    ref = img @ M.T + off
    err = np.abs(out - ref).max()
    assert err < 1e-9, f'tetrahedral self-test failed: {err}'
    print(f'  [PASS] tetrahedral interpolation reproduces affine LUT (max err {err:.2e})')


if __name__ == '__main__':
    self_test()
    if len(sys.argv) == 4:
        lut, n, title = read_cube(sys.argv[2])
        img = np.asarray(Image.open(sys.argv[1]).convert('RGB'), np.float64) / 255.0
        out = apply_tetrahedral(lut, img)
        Image.fromarray(np.clip(np.round(out * 255), 0, 255).astype(np.uint8)).save(sys.argv[3])
        print(f'applied "{title}" -> {sys.argv[3]}')
