#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iteration renderer: simulated Apple Log 2 footage -> BEFORE (neutral technical
conversion) / AFTER (GOLDEN DAYLIGHT CINEMA grade, direct pipeline) previews.

Writes compact JPEGs into iterate/ for visual tuning of the grade parameters.
The final deliverable previews are rendered from the actual .cube by
render_final.py.
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdc_core as G

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'sources')
OUT = os.path.join(ROOT, 'iterate')

SCENES = [
    ('SCENE_01.jpg', 'Harsh midday city'),
    ('SCENE_02.jpg', 'Midday portrait, direct sun'),
    ('SCENE_03.jpg', 'Mediterranean street'),
    ('SCENE_04.jpg', 'Bright beach daylight'),
    ('SCENE_05.jpg', 'Landscape, greenery & mountains'),
    ('SCENE_06.jpg', 'Golden-hour landscape'),
    ('SCENE_07.jpg', 'Modern architecture'),
    ('SCENE_08.jpg', 'Travel scene, people & buildings'),
]

TARGET_W, TARGET_H = 1280, 720  # 16:9 working size for all scenes


def load_scene(path):
    """Load a source still, centre-crop to 16:9 and resize to the working size."""
    im = Image.open(path).convert('RGB')
    w, h = im.size
    tr = TARGET_W / TARGET_H
    if w / h > tr:  # too wide -> crop width
        nw = int(round(h * tr))
        x0 = (w - nw) // 2
        im = im.crop((x0, 0, x0 + nw, h))
    else:           # too tall -> crop height
        nh = int(round(w / tr))
        y0 = (h - nh) // 2
        im = im.crop((0, y0, w, y0 + nh))
    if im.size != (TARGET_W, TARGET_H):
        im = im.resize((TARGET_W, TARGET_H), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def to_image(code01):
    """Rec.709 gamma-2.4 code values [0,1] -> 8-bit PNG-ready array."""
    return np.clip(np.round(code01 * 255.0), 0, 255).astype(np.uint8)


def render_pair(sim, width=704):
    before = to_image(G.pipeline_neutral(sim))
    after = to_image(G.pipeline_creative(sim))
    return before, after


def main():
    os.makedirs(OUT, exist_ok=True)
    pairs = []
    for fname, title in SCENES:
        img = load_scene(os.path.join(SRC, fname))
        sim = G.simulate_apple_log2(img)
        before, after = render_pair(sim)
        Image.fromarray(before).save(os.path.join(OUT, fname.replace('.jpg', '_BEFORE.jpg')),
                                     quality=90)
        Image.fromarray(after).save(os.path.join(OUT, fname.replace('.jpg', '_AFTER.jpg')),
                                    quality=90)
        pairs.append((before, after, title))
        print('rendered', fname)

    # combined review sheet: rows = scenes, cols = BEFORE | AFTER (800px wide each)
    cw, ch = 760, 428
    label_h = 34
    sheet = Image.new('RGB', (cw * 2, (ch + label_h) * len(pairs)), (12, 11, 9))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, (before, after, title) in enumerate(pairs):
        y = i * (ch + label_h)
        d.text((12, y + 9), f'{i + 1}. {title}   |   BEFORE (neutral conversion)', fill=(200, 200, 195))
        d.text((cw + 12, y + 9), f'AFTER (GOLDEN DAYLIGHT CINEMA)', fill=(226, 185, 119))
        sheet.paste(Image.fromarray(before).resize((cw, ch), Image.LANCZOS), (0, y + label_h))
        sheet.paste(Image.fromarray(after).resize((cw, ch), Image.LANCZOS), (cw, y + label_h))
    sheet.save(os.path.join(OUT, 'REVIEW_SHEET.jpg'), quality=88)
    print('wrote', os.path.join(OUT, 'REVIEW_SHEET.jpg'))


if __name__ == '__main__':
    main()
