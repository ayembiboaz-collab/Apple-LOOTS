#!/usr/bin/env python3
"""
make_chart_image.py -- render the reference chart as a before/after image.

Shows calibrated patches (light/medium/deep skin, sky, foliage, warm stone,
concrete, golden-hour light, shade, neutrals and primaries) decoded through the
delivered .cube next to the plain Apple Log 2 -> Rec.709 conversion.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chart  # noqa: E402
import grade   # noqa: E402
import simulate  # noqa: E402
from cube import apply_cube, read_cube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CELL, PAD, LBL = 96, 6, 26
FONT_SCALE = 1


def build():
    table, meta = read_cube(os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube"))
    names, keys, srgb = chart.patches()
    log2 = simulate.plate_to_apple_log2(srgb.reshape(1, -1, 3)).reshape(-1, 3)
    before = grade.neutral_technical(log2)
    after = apply_cube(log2, table, meta["domain_min"], meta["domain_max"])

    # lay out per group
    groups = list(chart.GROUPS.keys())
    maxcols = max(len(v) for v in chart.GROUPS.values())
    W = PAD + maxcols * (CELL + PAD)
    H = len(groups) * (CELL * 2 + LBL + PAD * 2) + 80
    im = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(im)
    d.text((PAD, 10), "GOLDEN DAYLIGHT CINEMA — reference chart",
           fill=(238, 234, 226))
    d.text((PAD, 28), "for each group: upper row = plain Apple Log 2 to Rec.709, "
                      "lower row = this LUT", fill=(150, 146, 140))

    y = 56
    for g in groups:
        idx = [i for i, n in enumerate(names) if n == g]
        d.text((PAD, y), g.replace("_", " "), fill=(150, 146, 140))
        yy = y + 14
        for j, i in enumerate(idx):
            x = PAD + j * (CELL + PAD)
            for row, arr in enumerate((before, after)):
                c = tuple(int(round(v * 255)) for v in np.clip(arr[i], 0, 1))
                d.rectangle([x, yy + row * (CELL + 2),
                             x + CELL, yy + row * (CELL + 2) + CELL], fill=c)
        y += LBL + CELL * 2 + PAD * 2
    out = os.path.join(ROOT, "VALIDATION", "reference_chart.png")
    im.save(out)
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    build()
