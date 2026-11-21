"""
build_lut.py — bake GOLDEN DAYLIGHT CINEMA into a 33 x 33 x 33 .cube.

Run:  python3 scripts/build_lut.py
"""

from __future__ import annotations

import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import grade
from cube_io import write_cube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "LUT")
OUT_PATH = os.path.join(OUT_DIR, "GOLDEN_DAYLIGHT_CINEMA.cube")

SIZE = 33
TITLE = "GOLDEN DAYLIGHT CINEMA"

HEADER = [
    "GOLDEN DAYLIGHT CINEMA",
    "Standalone creative LUT for Apple Log 2 / Apple Wide Gamut footage",
    "",
    "INPUT   : Apple Log 2 (Apple Log transfer function + Apple Wide Gamut",
    "          primaries, D65), normalised full-range signal 0.0 - 1.0",
    "OUTPUT  : Rec.709 primaries, D65, gamma 2.4 (pure 2.4 power EOTF)",
    "SIZE    : 33 x 33 x 33 3D LUT",
    "",
    "This LUT is standalone. It performs the Apple Log 2 decode, the Apple",
    "Wide Gamut to Rec.709 gamut transform, the creative grade and the",
    "Rec.709 gamma 2.4 output encode in a single table. Do NOT stack it on",
    "top of a separate Apple Log conversion LUT, and do not apply it to",
    "footage that is already Rec.709.",
    "",
    "Apple Log transfer function constants (Apple Log Profile White Paper,",
    "September 2023; unchanged in the Apple Log 2 White Paper, September 2025):",
    "  R0 = -0.05641088   Rt = 0.01          sigma = 47.28711236",
    "  beta = 0.00964052  gamma = 0.08550479 delta = 0.69336945",
    "Apple Wide Gamut primaries (Apple Log 2 White Paper, September 2025):",
    "  R (0.725, 0.301)  G (0.221, 0.814)  B (0.068, -0.076)  W D65",
    "",
    "A LUT cannot recover clipped highlights. See VALIDATION_REPORT.txt.",
]


def build(size=SIZE, look=None):
    look = grade.LOOK if look is None else look
    axis = np.linspace(0.0, 1.0, size)
    # .cube ordering: red varies fastest, then green, then blue.
    b, g, r = np.meshgrid(axis, axis, axis, indexing="ij")
    grid = np.stack([r, g, b], axis=-1).reshape(-1, 3)
    return grade.transform(grid, look)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    table = build()

    assert np.all(np.isfinite(table)), "LUT contains NaN or Inf"
    assert table.min() >= 0.0 and table.max() <= 1.0, "LUT outside [0, 1]"

    header = list(HEADER) + [
        "",
        f"Built {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')} "
        f"by scripts/build_lut.py",
    ]
    write_cube(OUT_PATH, table, SIZE, TITLE, header_lines=header, decimals=6)

    size_kb = os.path.getsize(OUT_PATH) / 1024.0
    print(f"wrote {OUT_PATH}")
    print(f"  {SIZE}^3 = {SIZE ** 3} entries, {size_kb:.1f} KB")
    print(f"  output range: [{table.min():.6f}, {table.max():.6f}]")
    for name, P in [
        ("log black      P=0.0", [0.0, 0.0, 0.0]),
        ("0% reflectance P=Pt ", [0.150476, 0.150476, 0.150476]),
        ("18% grey            ", [0.488272, 0.488272, 0.488272]),
        ("90% white           ", [0.681687, 0.681687, 0.681687]),
        ("log white      P=1.0", [1.0, 1.0, 1.0]),
    ]:
        out = grade.transform(np.array(P))
        print(f"  {name} -> {np.round(out, 5).tolist()}")


if __name__ == "__main__":
    main()
