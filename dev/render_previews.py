"""
render_previews.py -- build the .cube, then render all eight BEFORE/AFTER pairs.

AFTER is produced by reading the delivered .cube back off disk and trilinearly
interpolating it -- the same thing a video app does -- not by calling the
analytic grade. BEFORE is the same simulated Apple Log 2 plate through the
neutral technical conversion (creative look bypassed).

    python3 dev/render_previews.py            # full resolution
    python3 dev/render_previews.py --half     # fast iteration renders
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

import look as L
from colorlib import read_cube, apply_cube, write_cube
import scenes as S

HALF = '--half' in sys.argv
PREV = os.path.join(S.PROJ, 'PREVIEWS')
LUT_DIR = os.path.join(S.PROJ, 'LUT')
LUT_PATH = os.path.join(LUT_DIR, 'GOLDEN_DAYLIGHT_CINEMA.cube')

# Work at the source resolution -- no upscaling. 1600 px wide is the true
# resolution of the AI reference stills.
OUT_W, OUT_H = (800, 450) if HALF else (1600, 900)


def fit(im, w, h):
    """Centre-crop to w:h then resize."""
    sw, sh = im.size
    target = w / h
    if sw / sh > target:
        nw = int(round(sh * target))
        x = (sw - nw) // 2
        im = im.crop((x, 0, x + nw, sh))
    else:
        nh = int(round(sw / target))
        y = (sh - nh) // 2
        im = im.crop((0, y, sw, y + nh))
    return im.convert('RGB').resize((w, h), Image.LANCZOS)


def apply_cube_chunked(size, table, dmin, dmax, arr, rows=64):
    out = np.empty_like(arr)
    for y in range(0, arr.shape[0], rows):
        blk = arr[y:y + rows]
        out[y:y + rows] = apply_cube(size, table, dmin, dmax,
                                     blk.reshape(-1, 3)).reshape(blk.shape)
    return out


def to_u8(a):
    return np.clip(np.round(np.clip(a, 0.0, 1.0) * 255.0), 0, 255).astype(np.uint8)


def save_png(arr, path):
    Image.fromarray(to_u8(arr)).save(path, optimize=True)


def main():
    os.makedirs(LUT_DIR, exist_ok=True)
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(os.path.join(PREV, 'SIMULATED_APPLE_LOG2_SOURCES'), exist_ok=True)

    print('[1/4] building the LUT ...')
    table = L.build_table(33)
    write_cube(LUT_PATH, 33, table, title=L.TITLE, comment=L.COMMENT, decimals=7)
    print(f'      {LUT_PATH} ({os.path.getsize(LUT_PATH):,} bytes)')

    print('[2/4] reading it back off disk ...')
    n, tab, dmin, dmax, title = read_cube(LUT_PATH)
    print(f'      size={n} rows={tab.size // 3:,} title={title!r}')

    neutral = L.build_table(33, creative=False)

    print('[3/4] rendering ...')
    report = []
    for slug, fn, label, desc in S.SCENES:
        src = Image.open(os.path.join(S.SRC, fn)).convert('RGB')
        ref = np.asarray(fit(src, OUT_W, OUT_H), dtype=np.float64) / 255.0
        logq = S.simulate_apple_log2(ref)

        before = apply_cube_chunked(33, neutral, np.zeros(3), np.ones(3), logq)
        after = apply_cube_chunked(n, tab, dmin, dmax, logq)

        # verify the delivered cube against the analytic pipeline
        analytic = L.full_pipeline(logq.reshape(-1, 3)).reshape(after.shape)
        err = np.abs(after - analytic)

        save_png(before, os.path.join(PREV, f'{slug}_BEFORE.png'))
        save_png(after, os.path.join(PREV, f'{slug}_AFTER.png'))
        save_png(logq, os.path.join(PREV, 'SIMULATED_APPLE_LOG2_SOURCES',
                                    f'{slug}_APPLOG2_PLATE.png'))
        np.save(os.path.join(S.PROJ, 'SCENES', f'{slug}_plate.npy'), logq.astype(np.float32))

        report.append(dict(
            slug=slug, label=label, description=desc,
            width=int(after.shape[1]), height=int(after.shape[0]),
            lut_max_abs_err=float(err.max()),
            lut_mean_abs_err=float(err.mean()),
            before_mean=float(before.mean()), after_mean=float(after.mean()),
            before_clip_frac=float((before >= 0.9995).mean()),
            after_clip_frac=float((after >= 0.9995).mean()),
        ))
        print(f"      {slug:26s} cube-vs-analytic max {err.max():.2e} "
              f"mean {err.mean():.2e} | clip B {report[-1]['before_clip_frac']*100:.2f}% "
              f"A {report[-1]['after_clip_frac']*100:.2f}%")

    with open(os.path.join(S.HERE, 'render_report.json'), 'w') as fh:
        json.dump(report, fh, indent=2)
    print('[4/4] done.')


if __name__ == '__main__':
    main()
