#!/usr/bin/env python3
"""Build GOLDEN_DAYLIGHT_CINEMA.cube from the published Apple Log 2 spec."""

from __future__ import annotations

import json
import os
import sys

import numpy as np

import apple_log2 as al
import grade
import lut_io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
SIZE = 33

COMMENTS = [
    "# Input : Apple Log 2 / Apple Wide Gamut (iPhone 17 Pro, Blackmagic Camera for iOS)",
    "# Output: Rec.709 SDR, gamma 2.4, full range",
    "# Size  : 33 x 33 x 33, DOMAIN 0-1 (normalised full-range log code values)",
    "# Apple Log 2 transfer function and Apple Wide Gamut primaries:",
    "#   Apple Inc., 'Apple Log 2 White Paper', Sept 2025, v1.1 (part 028-00834)",
    "# R0=-0.05641088 Rt=0.01 c=47.28711236 beta=0.00964052 gamma=0.08550479 delta=0.69336945",
    "# AWG primaries R(0.725,0.301) G(0.221,0.814) B(0.068,-0.076) D65(0.3127,0.3290)",
    "# Gamut conversion: pure primary matrix (both spaces are D65; Bradford = identity)",
    "# Applied as a single 3D LUT: decode -> grade -> Rec.709 gamma 2.4. No extra LUT needed.",
]


def main():
    lut = grade.build_lut(SIZE)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lut_io.write_cube(OUT, lut, title="GOLDEN DAYLIGHT CINEMA", extra_comments=COMMENTS)

    # --- quick structural report -------------------------------------------
    neutral = lut[np.arange(SIZE), np.arange(SIZE), np.arange(SIZE)]
    mono = np.all(np.diff(neutral, axis=0) >= -1e-9)
    print(f"wrote {OUT}")
    print(f"size {lut.shape}, range {lut.min():.6f}..{lut.max():.6f}, finite={np.isfinite(lut).all()}")
    print(f"neutral axis monotonic: {mono}")
    print("neutral ramp (code_in -> out R,G,B):")
    for i in (0, 4, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32):
        v = i / (SIZE - 1)
        print(f"  {v:.3f} -> {neutral[i,0]:.4f} {neutral[i,1]:.4f} {neutral[i,2]:.4f}"
              f"   (display {neutral[i].mean()**2.4:.4f})")

    meta = dict(
        name="GOLDEN DAYLIGHT CINEMA",
        size=SIZE,
        input="Apple Log 2 / Apple Wide Gamut",
        output="Rec.709 SDR gamma 2.4",
        params=grade.P,
        tone_stops=grade.TONE_STOPS.tolist(),
        tone_code=grade.TONE_CODE.tolist(),
    )
    with open(os.path.join(ROOT, "build", "lut_metadata.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
