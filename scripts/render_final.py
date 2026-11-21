#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final deliverable renderer.

For each of the eight scenes:
  1. load the source still (credited in sources/SOURCES_AND_CREDITS.md);
  2. simulate Apple Log 2 / Apple Wide Gamut footage (10-bit full range);
  3. BEFORE = neutral technical conversion (Apple Log 2 -> Rec.709, gamma 2.4,
     no creative grade);
  4. AFTER  = the ACTUAL delivered .cube file applied with tetrahedral
     interpolation (the same method DaVinci Resolve uses for 3D LUTs).

Also reports the fidelity of the baked cube versus the direct pipeline.
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdc_core as G
from apply_lut import read_cube, apply_tetrahedral

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
PREV = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'PREVIEWS')
CUBE = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')

SCENES = [
    ('SCENE_01', 'Harsh midday city'),
    ('SCENE_02', 'Midday portrait in direct sunlight'),
    ('SCENE_03', 'Mediterranean street'),
    ('SCENE_04', 'Bright beach daylight'),
    ('SCENE_05', 'Landscape with greenery and mountains'),
    ('SCENE_06', 'Golden-hour landscape'),
    ('SCENE_07', 'Modern architecture'),
    ('SCENE_08', 'Travel scene with people and buildings'),
]


def load_scene(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    tr = 16 / 9
    if w / h > tr:
        nw = int(round(h * tr)); x0 = (w - nw) // 2
        im = im.crop((x0, 0, x0 + nw, h))
    else:
        nh = int(round(w / tr)); y0 = (h - nh) // 2
        im = im.crop((0, y0, w, y0 + nh))
    if im.size != (1280, 720):
        im = im.resize((1280, 720), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def to_u8(code01):
    return np.clip(np.round(code01 * 255.0), 0, 255).astype(np.uint8)


def main():
    os.makedirs(PREV, exist_ok=True)
    lut, n, title = read_cube(CUBE)
    print(f'loaded cube "{title}" ({n}^3)')
    fidelity = []
    for name, _label in SCENES:
        img = load_scene(os.path.join(SRC, name + '.jpg'))
        sim = G.simulate_apple_log2(img)
        before = to_u8(G.pipeline_neutral(sim))
        after = to_u8(apply_tetrahedral(lut, sim))
        direct = G.pipeline_creative(sim)
        cube_val = apply_tetrahedral(lut, sim)
        fidelity.append(np.abs(direct - cube_val).max())
        Image.fromarray(before).save(os.path.join(PREV, f'{name}_BEFORE.png'),
                                     optimize=True)
        Image.fromarray(after).save(os.path.join(PREV, f'{name}_AFTER.png'),
                                    optimize=True)
        print(f'{name}: BEFORE/AFTER written (cube-vs-direct max diff '
              f'{fidelity[-1] * 255:.2f}/255)')
    print(f'\ncube interpolation fidelity vs direct pipeline: '
          f'max {max(fidelity) * 255:.2f}/255 across all scenes')


if __name__ == '__main__':
    main()
