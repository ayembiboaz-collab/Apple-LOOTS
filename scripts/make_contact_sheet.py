#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the GOLDEN DAYLIGHT CINEMA contact sheet (8 scenes, BEFORE | AFTER)
and the exposure-robustness sweep strip.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdc_core as G
from apply_lut import read_cube, apply_tetrahedral
from render_final import load_scene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'PREVIEWS')
CS = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'CONTACT_SHEET')

FONT_DIR = '/usr/share/fonts/truetype/dejavu'
F_BOLD = os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')
F_SERIF = os.path.join(FONT_DIR, 'DejaVuSerif.ttf')
F_SANS = os.path.join(FONT_DIR, 'DejaVuSans.ttf')

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

BG = (13, 12, 10)
GOLD = (212, 165, 86)
TEXT = (205, 200, 190)
DIM = (120, 115, 106)


def contact_sheet():
    cw, ch = 560, 315  # cell size
    pad = 26
    label_h = 30
    header_h = 148
    footer_h = 64
    W = pad * 3 + cw * 2
    H = header_h + (label_h + ch + pad) * len(SCENES) + footer_h
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)

    f_title = ImageFont.truetype(F_SERIF, 54)
    f_sub = ImageFont.truetype(F_SANS, 19)
    f_label = ImageFont.truetype(F_BOLD, 17)
    f_small = ImageFont.truetype(F_SANS, 14)

    d.text((pad, 34), 'GOLDEN DAYLIGHT CINEMA', font=f_title, fill=GOLD)
    d.text((pad, 100), 'Contact sheet  ·  Apple Log 2 / Apple Wide Gamut  →  Rec.709 SDR (gamma 2.4)'
                        '  ·  LEFT: neutral conversion   RIGHT: GOLDEN DAYLIGHT CINEMA',
           font=f_sub, fill=TEXT)
    d.line((pad, 92, W - pad, 92), fill=(60, 52, 38), width=1)

    for i, (name, title) in enumerate(SCENES):
        y = header_h + i * (label_h + ch + pad)
        before = Image.open(os.path.join(PREV, f'{name}_BEFORE.png')).resize((cw, ch), Image.LANCZOS)
        after = Image.open(os.path.join(PREV, f'{name}_AFTER.png')).resize((cw, ch), Image.LANCZOS)
        d.text((pad, y + 8), f'{i + 1}.  {title.upper()}', font=f_label, fill=TEXT)
        d.text((pad * 2 + cw, y + 8), 'GOLDEN DAYLIGHT CINEMA', font=f_label, fill=GOLD)
        sheet.paste(before, (pad, y + label_h))
        sheet.paste(after, (pad * 2 + cw, y + label_h))
        d.rectangle((pad, y + label_h, pad + cw, y + label_h + ch), outline=(45, 42, 36), width=1)
        d.rectangle((pad * 2 + cw, y + label_h, pad * 2 + cw * 2, y + label_h + ch),
                    outline=(45, 42, 36), width=1)

    fy = H - footer_h + 18
    d.line((pad, fy - 12, W - pad, fy - 12), fill=(60, 52, 38), width=1)
    d.text((pad, fy), 'Simulated Apple Log 2 footage derived from AI-generated stills — see '
            'VALIDATION_REPORT.txt. Preview images show the delivered .cube applied '
            'with tetrahedral interpolation.', font=f_small, fill=DIM)
    os.makedirs(CS, exist_ok=True)
    out = os.path.join(CS, 'GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png')
    sheet.save(out, optimize=True)
    print('wrote', out, sheet.size, f'{os.path.getsize(out)/1e6:.2f} MB')


def exposure_sweep():
    """SCENE_01 at -2..+2 stops of simulated exposure, all through the delivered cube."""
    lut, n, _ = read_cube(os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT',
                                       'GOLDEN_DAYLIGHT_CINEMA.cube'))
    img = load_scene(os.path.join(ROOT, 'sources', 'SCENE_01.jpg'))
    evs = [-2, -1, 0, 1, 2]
    cw, ch = 560, 315
    pad = 22
    header = 96
    W = pad + (cw + pad) * len(evs)
    H = header + ch + 2 * pad + 34
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f_title = ImageFont.truetype(F_SERIF, 34)
    f_sub = ImageFont.truetype(F_SANS, 16)
    f_label = ImageFont.truetype(F_BOLD, 16)
    d.text((pad, 22), 'EXPOSURE ROBUSTNESS', font=f_title, fill=GOLD)
    d.text((pad, 64), 'Harsh midday city through the delivered .cube at five simulated exposure '
            'levels (scene-linear exposure, pre-encode)', font=f_sub, fill=TEXT)
    for i, ev in enumerate(evs):
        sim = G.simulate_apple_log2(img, exposure_stops=ev)
        out = apply_tetrahedral(lut, sim)
        arr = np.clip(np.round(out * 255), 0, 255).astype(np.uint8)
        tile = Image.fromarray(arr).resize((cw, ch), Image.LANCZOS)
        x = pad + i * (cw + pad)
        sheet.paste(tile, (x, header))
        d.rectangle((x, header, x + cw, header + ch), outline=(45, 42, 36), width=1)
        d.text((x + 4, header + ch + 12), f'{ev:+d} EV', font=f_label, fill=GOLD)
    out = os.path.join(CS, 'GOLDEN_DAYLIGHT_CINEMA_EXPOSURE_SWEEP.png')
    sheet.save(out, optimize=True)
    print('wrote', out, sheet.size, f'{os.path.getsize(out)/1e6:.2f} MB')


if __name__ == '__main__':
    contact_sheet()
    exposure_sweep()
