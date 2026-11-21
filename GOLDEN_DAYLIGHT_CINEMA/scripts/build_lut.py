"""
build_lut.py
=============

Bake the 33 x 33 x 33 "GOLDEN DAYLIGHT CINEMA" .cube LUT from the creative
grade pipeline.

Usage:
    python build_lut.py [--out PATH] [--size 33] [--params FILE]

The input grid spans the Apple Log 2 encoded domain 0..1 on each axis
(DOMAIN_MIN 0, DOMAIN_MAX 1).  Apple Log 2 code value 1.0 corresponds to
linear ~12, far above scene white, so the grid comfortably covers the full
highlight range and any super-whites in normal footage.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import color_science as cs
import grade
from cube_io import write_cube

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_OUT = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")


def build(size=33, params=None, out_path=DEFAULT_OUT, title=None):
    params = params or {}
    if title is None:
        title = "GOLDEN DAYLIGHT CINEMA - Apple Log 2 / Apple Wide Gamut -> Rec.709 gamma 2.4"

    # Grid coordinates in the Apple Log 2 encoded domain [0, 1].
    axis = np.linspace(0.0, 1.0, size, dtype=np.float64)

    # Build the full 33^3 input grid, shape (size, size, size, 3) indexed
    # [r, g, b] where r/g/b are the log-domain code values.
    # We'll evaluate the pipeline on the flattened grid.
    r, g, b = np.meshgrid(axis, axis, axis, indexing="ij")
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)  # (N^3, 3)

    # Evaluate the full standalone pipeline.
    out = grade.apple_log2_to_rec709_gamma24(grid, params=params)
    out = out.reshape(size, size, size, 3)

    write_cube(out_path, out, size, title=title)
    return out_path, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--size", type=int, default=33)
    ap.add_argument("--params", default=None,
                    help="Optional JSON file of grade parameter overrides")
    args = ap.parse_args()

    params = None
    if args.params:
        with open(args.params) as fh:
            raw = json.load(fh)
        params = {}
        # Allow overriding scalars / arrays.
        for k, v in raw.items():
            params[k] = np.array(v) if isinstance(v, list) else v

    out_path, out = build(size=args.size, params=params, out_path=args.out)
    print(f"Wrote {out_path}")
    print(f"  size={args.size}^3, values in "
          f"[{out.min():.4f}, {out.max():.4f}], "
          f"nan={np.isnan(out).any()}, inf={np.isinf(out).any()}")


if __name__ == "__main__":
    main()
