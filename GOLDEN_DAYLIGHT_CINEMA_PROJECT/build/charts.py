"""Synthetic charts rendered through the shipped .cube.

Produces PNGs in validation/:
  grey_ramp.png, hue_sweep.png, saturation_sweep.png,
  colorchecker_style.png, exposure_ladder.png, skin_line.png

Each chart shows fair neutral reference (top) and shipped-.cube output (bottom)
so the grade is visible honestly.  Inputs are synthesized OKLab patterns
converted through the inverse Apple Log 2 encode — no real footage is used
for these charts.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs
import pipeline as pl
import render_previews as rp
import validate_lut as vl

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
CUBE = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'LUT' / 'GOLDEN_DAYLIGHT_CINEMA.cube'
VAL = PROJECT / 'validation'
VAL.mkdir(parents=True, exist_ok=True)


def encoded_from_oklch(L, C, h):
    """OKLab pattern (...,3) -> encoded Apple Log 2 (...,3). Mirrors pipeline."""
    L = np.asarray(L, dtype=np.float64)
    C = np.asarray(C, dtype=np.float64)
    h = np.asarray(h, dtype=np.float64)
    ok = cs.oklch_to_oklab(L, C, h)
    lin = cs.oklab_to_awg_linear(ok)
    return cs.apple_log2_encode(lin)


def draw_chart(rows, labels, out_name, tile=64, H=56, gap=3):
    """rows: list of (N,3) gamma-2.4 RGB charts. Each row = one grid of tiles."""
    N = rows[0].shape[0]
    total_rows = len(rows)
    W = gap + N * tile + (N - 1) * gap + gap
    H_total = gap + total_rows * H + (total_rows - 1) * gap + gap
    canvas = Image.new('RGB', (W, H_total), (24, 24, 24))
    for ri, row in enumerate(rows):
        for k in range(N):
            rgb = np.round(np.clip(row[k], 0.0, 1.0) * 255).astype(np.uint8)
            x0 = gap + k * (tile + gap)
            y0 = gap + ri * (H + gap)
            for dy in range(H):
                for dx in range(tile):
                    canvas.putpixel((x0 + dx, y0 + dy), tuple(rgb))
    canvas.save(VAL / out_name)
    print(f'wrote {VAL/out_name}')


def build_charts():
    size, cube = rp.load_cube(CUBE)

    # ---- grey ramp --------------------------------------------------------
    levels = np.linspace(0.02, 0.98, 32)
    pts = np.stack([levels, levels, levels], axis=-1)
    neutral = pl.neutral_reference(pts)
    graded = vl.flat_apply_cube(pts, cube, size)
    draw_chart([neutral, graded], None, 'grey_ramp.png', tile=28)

    # ---- hue sweep --------------------------------------------------------
    hvals = np.linspace(0.0, 2 * np.pi, 36, endpoint=False)
    L = np.full_like(hvals, 0.55)
    C = np.full_like(hvals, 0.08)
    enc = encoded_from_oklch(L, C, hvals)
    neutral = pl.neutral_reference(enc)
    graded = vl.flat_apply_cube(enc, cube, size)
    draw_chart([neutral, graded], None, 'hue_sweep.png', tile=22)

    # ---- saturation sweep -------------------------------------------------
    sat_vals = np.linspace(0.0, 0.22, 28)
    neutral_rows = []
    graded_rows = []
    for h in (1.00, 4.60):  # stone-warm hue and sky hue
        enc = encoded_from_oklch(np.full_like(sat_vals, 0.55), sat_vals, np.full_like(sat_vals, h))
        neutral_rows.append(pl.neutral_reference(enc))
        graded_rows.append(vl.flat_apply_cube(enc, cube, size))
    chart_rows = []
    for strip in range(2):
        chart_rows.append(neutral_rows[strip])
        chart_rows.append(graded_rows[strip])
    draw_chart(chart_rows, None, 'saturation_sweep.png', tile=24, H=44)

    # ---- colorchecker style (24 diverse patches) ----------------------------
    # neutrals/skins + saturated hues (reds, yellow, green, blue, purple)
    patches = [
        (0.95, 0.00, 0.05), (0.84, 0.00, 0.20), (0.74, 0.01, 0.85), (0.62, 0.04, 0.62),
        (0.55, 0.04, 0.72), (0.46, 0.03, 0.65), (0.34, 0.06, 0.55), (0.50, 0.00, 0.30),
        (0.80, 0.16, 0.05), (0.84, 0.18, 0.55), (0.74, 0.17, 1.05), (0.64, 0.19, 2.95),
        (0.70, 0.16, 4.05), (0.55, 0.19, 5.05), (0.78, 0.13, 5.65), (0.62, 0.16, 2.15),
        (0.36, 0.09, 0.60), (0.48, 0.10, 1.55), (0.82, 0.10, 3.90), (0.58, 0.15, 4.80),
        (0.86, 0.14, 0.30), (0.40, 0.14, 5.30), (0.58, 0.09, 2.50), (0.32, 0.12, 0.40),
    ]
    rows_n = []
    rows_g = []
    for (L, C, h) in patches:
        ok = cs.oklch_to_oklab(np.array([L]), np.array([C]), np.array([h]))[0]
        enc = cs.apple_log2_encode(cs.oklab_to_awg_linear(ok[None])[0])
        neutral_ref = pl.neutral_reference(enc)
        graded = vl.flat_apply_cube(enc[None], cube, size)[0]
        rows_n.append(neutral_ref)
        rows_g.append(graded)
    tile = 60
    cw = 24 * (tile + 2) + 4
    canvas = Image.new('RGB', (cw, 2 * 56 + 3 * 4), (24, 24, 24))
    for k in range(24):
        x = 2 + k * (tile + 2)
        y = 2
        rgb = np.round(np.clip(rows_n[k], 0.0, 1.0) * 255).astype(np.uint8)
        for dy in range(56):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
        y = 2 + 56 + 2
        rgb = np.round(np.clip(rows_g[k], 0.0, 1.0) * 255).astype(np.uint8)
        for dy in range(56):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
    canvas.save(VAL / 'colorchecker_style.png')
    print('wrote', VAL / 'colorchecker_style.png')

    # ---- ± exposure ladder (neutral gray) ----------------------------------
    stops = list(range(-4, 5))
    rows_n = []
    rows_g = []
    for s in stops:
        lin = 0.18 * (2.0 ** s)
        enc = cs.apple_log2_encode(np.array([lin, lin, lin]))
        neutral_ref = pl.neutral_reference(enc)
        graded = vl.flat_apply_cube(enc[None], cube, size)[0]
        rows_n.append(neutral_ref)
        rows_g.append(graded)
    tile = 80
    canvas = Image.new('RGB', (len(stops) * (tile + 2) + 2, 2 * 64 + 3 * 2), (24, 24, 24))
    for k, s in enumerate(stops):
        x = 2 + k * (tile + 2)
        y = 2
        rgb = np.round(np.clip(rows_n[k], 0.0, 1.0) * 255).astype(np.uint8)
        for dy in range(64):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
        y = 2 + 64 + 2
        rgb = np.round(np.clip(rows_g[k], 0.0, 1.0) * 255).astype(np.uint8)
        for dy in range(64):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
    canvas.save(VAL / 'exposure_ladder.png')
    print('wrote', VAL / 'exposure_ladder.png')

    # ---- skin line strip --------------------------------------------------
    skin_h = np.linspace(0.15, 1.00, 16)
    skin_c = np.linspace(0.03, 0.14, 16)
    tile = 24
    canvas = Image.new('RGB', (1 + 0, 0), (24, 24, 24))  # placeholder replaced below
    cw = 16 * (tile + 2) + 2
    canvas = Image.new('RGB', (cw, 2 * 56 + 3 * 4), (24, 24, 24))
    for k in range(16):
        h = skin_h[k]
        c = skin_c[k]
        ok = cs.oklch_to_oklab(np.array([0.60]), np.array([c]), np.array([h]))[0]
        enc = cs.apple_log2_encode(cs.oklab_to_awg_linear(ok[None])[0])
        n = pl.neutral_reference(enc)
        g = vl.flat_apply_cube(enc[None], cube, size)[0]
        x = 2 + k * (tile + 2)
        rgb = np.round(np.clip(n, 0.0, 1.0) * 255).astype(np.uint8)
        y = 2
        for dy in range(56):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
        rgb = np.round(np.clip(g, 0.0, 1.0) * 255).astype(np.uint8)
        y = 2 + 56 + 2
        for dy in range(56):
            for dx in range(tile):
                canvas.putpixel((x + dx, y + dy), tuple(rgb))
    canvas.save(VAL / 'skin_line.png')
    print('wrote', VAL / 'skin_line.png')


if __name__ == '__main__':
    build_charts()
