#!/usr/bin/env python3
"""
build_lut.py -- bake GOLDEN DAYLIGHT CINEMA into a 33x33x33 .cube.

    python3 build_lut.py            # writes ../LUT/GOLDEN_DAYLIGHT_CINEMA.cube

The lattice is sampled from the analytic grade in float64, with the LUT domain
being Apple Log 2 code value 0..1 (Apple Wide Gamut primaries). The file is
therefore standalone: it expects log input, never Rec.709 input.
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade  # noqa: E402
from cube import write_cube  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def bake(n=33, params=None):
    p = params or grade.PARAMS
    axis = np.linspace(0.0, 1.0, n)
    r, g, b = np.meshgrid(axis, axis, axis, indexing="ij")
    log_rgb = np.stack([r, g, b], axis=-1)
    return grade.apply_grade(log_rgb, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=33)
    ap.add_argument("--out", default=os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube"))
    args = ap.parse_args()

    table = bake(args.size)
    assert np.isfinite(table).all(), "non-finite value in LUT lattice"
    table = np.clip(table, 0.0, 1.0)

    comments = [
        "GOLDEN DAYLIGHT CINEMA v1.0",
        "Input : Apple Log 2 / Apple Wide Gamut (iPhone 17 Pro, Blackmagic Camera)",
        "Output: Rec.709 SDR, gamma 2.4",
        f"Size  : {args.size} x {args.size} x {args.size}",
        "Decodes Apple Log (Apple Log Profile White Paper 2023 constants), converts",
        "Apple Wide Gamut primaries (Apple Log 2 White Paper 2025) to Rec.709, then",
        "applies the creative grade. Apply directly to log footage: no extra",
        "conversion LUT required.",
        "Baked by BUILD/build_lut.py -- do not hand edit.",
    ]
    n = write_cube(args.out, table, "GOLDEN DAYLIGHT CINEMA", comments)
    print(f"wrote {args.out} ({n} entries, {os.path.getsize(args.out)/1e6:.2f} MB)")


if __name__ == "__main__":
    main()
