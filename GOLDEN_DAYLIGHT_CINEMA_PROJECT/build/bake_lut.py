"""Bake the Golden Daylight Cinema 33^3 .cube LUT.

The .cube maps Apple Log 2 encoded input (0..1) to Rec.709 gamma 2.4 output.
The analytic pipeline (pipeline.decode_and_grade) is evaluated at the 33^3
grid points.  The full pipeline — decode, grade, gamut-map, gamma 2.4
encode — is baked into the .cube so the file is fully standalone: no separate
conversion LUT, no assumptions.

Usage:
  python bake_lut.py [--size 33] [--params-out params.json]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs
import pipeline as pl

BUILD = Path(__file__).resolve().parent
OUT = BUILD.parent / 'GOLDEN_DAYLIGHT_CINEMA' / 'LUT' / 'GOLDEN_DAYLIGHT_CINEMA.cube'


def bake(size=33, params=None):
    p = dict(pl.DEFAULTS if params is None else params)
    # Grid of all points.  .cube ordering: RED varies fastest, then GREEN,
    # then BLUE.  With indexing='ij' the first meshgrid axis (R) is slowest,
    # so we transpose so that R is the LAST axis -> ravel() gives red-fastest.
    axis = np.linspace(0.0, 1.0, size)
    R, G, B = np.meshgrid(axis, axis, axis, indexing='ij')
    R = R.transpose(2, 1, 0)
    G = G.transpose(2, 1, 0)
    B = B.transpose(2, 1, 0)
    R = R.ravel().reshape(-1, 1)
    G = G.ravel().reshape(-1, 1)
    B = B.ravel().reshape(-1, 1)
    # Stack: (N^3, 3)
    inputs = np.concatenate([R, G, B], axis=1)

    # Analytic pipeline at grid points (red-fastest ordering preserved)
    outputs = pl.decode_and_grade(inputs, p)

    # Sanity: values in range
    outputs = np.clip(outputs, 0.0, 1.0)

    return axis, outputs


def write_cube(axis, outputs, out_path, size=33, title='Golden Daylight Cinema'):
    axis_vals = np.linspace(0.0, 1.0, size)
    lines = [
        f'# {title}',
        '# Golden Daylight Cinema - Apple Log 2 -> Rec.709 gamma 2.4',
        '# 33x33x33 3D LUT' if size == 33 else f'# {size}x{size}x{size} 3D LUT',
        f'LUT_3D_SIZE {size}',
        'DOMAIN_MIN 0.0 0.0 0.0',
        'DOMAIN_MAX 1.0 1.0 1.0',
    ]
    with open(out_path, 'w') as f:
        for ln in lines:
            f.write(ln + '\n')
        for row in outputs:
            r, g, b = row
            f.write(f'{r:.6f} {g:.6f} {b:.6f}\n')
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=33)
    ap.add_argument('--params-out', type=str, default=None)
    args = ap.parse_args()

    print(f'Baking {args.size}^3 cube (analytic evaluation)...')
    axis, outputs = bake(args.size)
    print(f'  outputs: {outputs.shape}, min={outputs.min():.4f}, max={outputs.max():.4f}')
    write_cube(axis, outputs, OUT, size=args.size)
    print(f'  -> {OUT}')
    print(f'  size: {OUT.stat().st_size} bytes')

    if args.params_out:
        with open(args.params_out, 'w') as f:
            json.dump(pl.DEFAULTS, f, indent=2)
        print(f'  params -> {args.params_out}')


if __name__ == '__main__':
    main()
