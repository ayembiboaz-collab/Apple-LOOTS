"""
render_previews.py -- build the .cube, then render all eight BEFORE/AFTER pairs.

AFTER is produced by reading the delivered .cube back off disk and trilinearly
interpolating it -- the same operation a video app performs -- not by calling
the analytic grade. BEFORE is the same simulated Apple Log 2 plate through the
neutral technical conversion (creative look bypassed).

    python3 dev/render_previews.py
"""

from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from PIL import Image

import look as L
from colorlib import read_cube, apply_cube, write_cube
import scenes as S

PREV = os.path.join(S.PROJ, 'PREVIEWS')
PLATES = os.path.join(PREV, 'SIMULATED_APPLE_LOG2_SOURCES')
LUT_DIR = os.path.join(S.PROJ, 'LUT')
LUT_PATH = os.path.join(LUT_DIR, 'GOLDEN_DAYLIGHT_CINEMA.cube')


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


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(LUT_DIR, exist_ok=True)
    os.makedirs(PREV, exist_ok=True)
    os.makedirs(PLATES, exist_ok=True)

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
        plate = S.plate_for(slug)
        before = apply_cube_chunked(33, neutral, np.zeros(3), np.ones(3), plate)
        after = apply_cube_chunked(n, tab, dmin, dmax, plate)

        analytic = L.full_pipeline(plate.reshape(-1, 3)).reshape(after.shape)
        err = np.abs(after - analytic)

        save_png(before, os.path.join(PREV, f'{slug}_BEFORE.png'))
        save_png(after, os.path.join(PREV, f'{slug}_AFTER.png'))
        # The log plate is provenance, not a deliverable image, so it is stored
        # as a high-quality JPEG to keep the repository and the ZIP reasonable.
        Image.fromarray(to_u8(plate)).save(
            os.path.join(PLATES, f'{slug}_APPLOG2_PLATE.jpg'),
            quality=94, optimize=True)

        report.append(dict(
            slug=slug, label=label, description=desc,
            width=int(after.shape[1]), height=int(after.shape[0]),
            lut_max_abs_err=float(err.max()),
            lut_mean_abs_err=float(err.mean()),
            before_mean=float(before.mean()), after_mean=float(after.mean()),
            before_clip_frac=float((before.max(axis=-1) >= 0.9995).mean()),
            after_clip_frac=float((after.max(axis=-1) >= 0.9995).mean()),
        ))
        print(f"      {slug:26s} {after.shape[1]}x{after.shape[0]} "
              f"mean {report[-1]['before_mean']:.4f} -> {report[-1]['after_mean']:.4f} "
              f"| clip {100*report[-1]['before_clip_frac']:.2f}% -> "
              f"{100*report[-1]['after_clip_frac']:.2f}%")

    manifest = {
        'lut': {
            'path': 'LUT/GOLDEN_DAYLIGHT_CINEMA.cube',
            'bytes': os.path.getsize(LUT_PATH),
            'sha256': sha256(LUT_PATH),
            'size': 33,
        },
        'scenes': report,
        'previews': {},
    }
    for slug, _, _, _ in S.SCENES:
        for kind in ('BEFORE', 'AFTER'):
            p = os.path.join(PREV, f'{slug}_{kind}.png')
            manifest['previews'][os.path.basename(p)] = sha256(p)

    with open(os.path.join(S.PROJ, 'SCENES', 'render_manifest.json'), 'w') as fh:
        json.dump(manifest, fh, indent=2)
    print('[4/4] done.')


if __name__ == '__main__':
    main()
