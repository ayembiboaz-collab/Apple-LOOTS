"""
tune.py -- fast analytic evaluation of the look against material probes.

Runs BEFORE (neutral) and AFTER (grade) on downsampled plates and reports the
behaviour of named material regions, plus writes a compact JPEG strip so the
look can be judged visually without a full render.

    python3 dev/tune.py                 # report
    python3 dev/tune.py --sheet         # also write /tmp/gdc_sheet_*.jpg
"""

from __future__ import annotations

import os
import sys

import numpy as np
from PIL import Image

import look as L
from colorlib import rec709_gamma_decode, linear_to_oklab
import scenes as S

TMP = '/tmp/gdc_tune'
W, H = 480, 270

# Probe boxes in normalised (x0, y0, x1, y1) of the 16:9 frame, plus an
# optional OkLab hue window that isolates the material inside the box.
PROBES = [
    ('02_midday_portrait', 'face',        (0.40, 0.12, 0.62, 0.62), (25, 85), 'skin'),
    ('02_midday_portrait', 'stone wall',  (0.72, 0.05, 0.95, 0.45), None,     'warm neutral'),
    ('01_harsh_midday_city', 'sky',       (0.30, 0.00, 0.70, 0.18), (195, 285), None),
    ('01_harsh_midday_city', 'awning shadow', (0.02, 0.55, 0.22, 0.95), None, None),
    ('03_mediterranean_street', 'limestone', (0.40, 0.20, 0.75, 0.55), (25, 95), None),
    ('04_beach_daylight', 'sea',          (0.05, 0.45, 0.45, 0.62), (180, 240), None),
    ('04_beach_daylight', 'sand/spray',   (0.55, 0.62, 0.95, 0.80), None, None),
    ('05_natural_landscape', 'foliage',   (0.20, 0.45, 0.80, 0.90), (85, 175), 'green'),
    ('05_natural_landscape', 'sky',       (0.05, 0.02, 0.55, 0.25), (195, 285), None),
    ('06_golden_hour', 'ground',          (0.05, 0.70, 0.55, 0.98), None, 'already warm'),
    ('06_golden_hour', 'sky near sun',    (0.45, 0.05, 0.95, 0.35), None, 'already warm'),
    ('07_modern_architecture', 'white concrete', (0.10, 0.05, 0.55, 0.75), None, 'white'),
    ('07_modern_architecture', 'sky',     (0.05, 0.00, 0.45, 0.18), (195, 285), None),
    ('08_travel_cinematography', 'piazza stone', (0.02, 0.80, 0.98, 0.98), None, None),
]


def oklch(code):
    lin = np.clip(rec709_gamma_decode(code), 0.0, None)
    lab = linear_to_oklab(lin)
    Cv = np.hypot(lab[..., 1], lab[..., 2])
    hv = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0
    return lab[..., 0], Cv, hv, lab[..., 1], lab[..., 2]


def load_plate(slug):
    path = os.path.join(S.HERE, 'tune_cache', f'{slug}.npy')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return np.load(path)
    fn = dict((s[0], s[1]) for s in S.SCENES)[slug]
    im = Image.open(os.path.join(S.SRC, fn)).convert('RGB').resize((W, H), Image.LANCZOS)
    ref = np.asarray(im, dtype=np.float64) / 255.0
    plate = S.simulate_apple_log2(ref)
    np.save(path, plate)
    return plate


def box(arr, x0, y0, x1, y1):
    h, w = arr.shape[:2]
    return arr[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]


def report(params=None, verbose=True):
    params = params or L.P
    rows = []
    sheet_before, sheet_after = [], []
    for slug, name, bx, hue, kind in PROBES:
        plate = load_plate(slug)
        before = L.full_pipeline(plate, creative=False)
        after = L.grade_display(before, params)
        mb = box(before, *bx)
        ma = box(after, *bx)
        Lb, Cb, hb, ab, bb = oklch(mb)
        La, Ca, ha, aa, ba = oklch(ma)
        m = np.ones(Lb.shape, bool)
        if hue is not None:
            m = (hb >= hue[0]) & (hb <= hue[1]) & (Cb > 0.012)
        if m.sum() < 50:
            continue
        dh = ((ha[m] - hb[m] + 180) % 360) - 180
        rows.append(dict(
            slug=slug, name=name, kind=kind, px=int(m.sum()),
            Lb=Lb[m].mean(), La=La[m].mean(),
            Cb=Cb[m].mean(), Ca=Ca[m].mean(),
            dL=100 * (La[m].mean() / max(Lb[m].mean(), 1e-6) - 1),
            dC=100 * (Ca[m].mean() / max(Cb[m].mean(), 1e-6) - 1),
            dh=dh.mean(), ab=ab[m].mean(), aa=aa[m].mean(),
            bb=bb[m].mean(), ba=ba[m].mean(),
            clip=100 * (ma[m].max(-1) >= 0.9995).mean(),
        ))
        if '--sheet' in sys.argv:
            sheet_before.append(mb)
            sheet_after.append(ma)

    if verbose:
        print(f"{'scene':26s} {'material':14s} {'L%':>7s} {'C%':>7s} {'dh':>6s} "
              f"{'da':>7s} {'db':>7s} {'clip%':>6s}")
        for r in rows:
            print(f"{r['slug'][:26]:26s} {r['name']:14s} {r['dL']:7.2f} "
                  f"{r['dC']:7.2f} {r['dh']:6.2f} {r['aa']-r['ab']:7.4f} "
                  f"{r['ba']-r['bb']:7.4f} {r['clip']:6.2f}")
    return rows


def sheet():
    os.makedirs(TMP, exist_ok=True)
    before, after = [], []
    for slug, fn, _, _ in S.SCENES:
        plate = load_plate(slug)
        b = L.full_pipeline(plate, creative=False)
        a = L.grade_display(b)
        before.append(b)
        after.append(a)
    def mont(arrs, name):
        rows = []
        for a in arrs:
            rows.append(np.concatenate([a], axis=1))
        top = np.concatenate(rows[:4], axis=0)
        bot = np.concatenate(rows[4:], axis=0)
        img = np.concatenate([top, bot], axis=0)
        Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8)).save(
            os.path.join(TMP, name), quality=90)
    mont(before, 'sheet_before.jpg')
    mont(after, 'sheet_after.jpg')
    # interleaved pairs
    pairs = []
    for b, a in zip(before, after):
        pairs.append(np.concatenate([b, a], axis=1))
    top = np.concatenate(pairs[:4], axis=0)
    bot = np.concatenate(pairs[4:], axis=0)
    img = np.concatenate([top, bot], axis=0)
    Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8)).save(
        os.path.join(TMP, 'pairs.jpg'), quality=92)
    print('wrote', TMP)


if __name__ == '__main__':
    report()
    if '--sheet' in sys.argv:
        sheet()
