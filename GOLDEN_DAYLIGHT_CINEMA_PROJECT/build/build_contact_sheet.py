"""Build the CONTACT_SHEET/ PNG: all 8 scenes, BEFORE | AFTER."""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
PREVIEWS = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'PREVIEWS'
OUT = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'CONTACT_SHEET'
OUT.mkdir(parents=True, exist_ok=True)

SCENES = [
    ('01_midday_city', 'Midday City'),
    ('02_midday_portrait', 'Midday Portrait'),
    ('03_mediterranean_street', 'Mediterranean Street'),
    ('04_bright_beach', 'Bright Beach Daylight'),
    ('05_natural_landscape', 'Natural Landscape'),
    ('06_golden_hour_landscape', 'Golden Hour Landscape'),
    ('07_modern_architecture', 'Modern Architecture'),
    ('08_travel_street', 'Outdoor Travel Scene'),
]

TILE_W = 460
TILE_H = 300
LABEL_H = 44
CAPTION_H = 34
GAP = 12

def main():
    rows = []
    for stem, title in SCENES:
        bf = Image.open(PREVIEWS / f'{stem}_BEFORE_NEUTRAL.png').convert('RGB')
        af = Image.open(PREVIEWS / f'{stem}_AFTER_GOLDEN_DAYLIGHT.png').convert('RGB')
        bf.thumbnail((TILE_W, TILE_H))
        af.thumbnail((TILE_W, TILE_H))
        rows.append((title, bf, af))

    card_w = TILE_W + TILE_W + GAP * 2
    card_h = LABEL_H + TILE_H + CAPTION_H + GAP
    canvas = Image.new('RGB', (card_w, card_h * len(rows) + GAP * (len(rows) + 1)), (16, 14, 12))
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
        font_sub = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
    except Exception:
        font_title = font_sub = ImageFont.load_default()

    for i, (title, bf, af) in enumerate(rows):
        y0 = GAP + i * (card_h + GAP)
        draw = ImageDraw.Draw(canvas)
        # labels
        draw.text((GAP, y0), title.upper(), fill=(240, 166, 79), font=font_title)
        draw.text((card_w - GAP, y0 + 4), 'BEFORE  |  AFTER', fill=(168, 156, 136), font=font_sub, anchor='ra')
        # images, centred vertically
        bf_x = GAP
        af_x = GAP + TILE_W + GAP
        bf_y = y0 + LABEL_H + (TILE_H - bf.size[1]) // 2
        af_y = y0 + LABEL_H + (TILE_H - af.size[1]) // 2
        canvas.paste(bf, (bf_x, bf_y))
        canvas.paste(af, (af_x, af_y))
        # caption strip between
        cap_y = y0 + LABEL_H + TILE_H + 14
        draw.text((GAP + bf.size[0] // 2, cap_y), 'BEFORE (neutral ref)', fill=(150, 140, 122), font=font_sub, anchor='mm')
        draw.text((af_x + af.size[0] // 2, cap_y), 'AFTER (GOLDEN DAYLIGHT)', fill=(240, 166, 79), font=font_sub, anchor='mm')

    out = OUT / 'contact_sheet.png'
    canvas.save(out)
    print(f'wrote {out}  ({canvas.size[0]}x{canvas.size[1]})')


if __name__ == '__main__':
    main()
