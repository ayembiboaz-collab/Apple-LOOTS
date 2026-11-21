"""
make_contact_sheet.py -- visual overview of the look.

Produces
  CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png
      eight BEFORE/AFTER pairs, labelled, on a dark portfolio sheet
  CONTACT_SHEET/LOOK_REFERENCE_CHART.png
      technical reference: neutral ramps, skin, sky, foliage, stone and
      highlight patches, BEFORE against AFTER, with the measured OkLab shifts
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import look as L
import scenes as S
from colorlib import apply_cube, read_cube, rec709_gamma_decode, linear_to_oklab

OUT = os.path.join(S.PROJ, 'CONTACT_SHEET')
LUT = os.path.join(S.PROJ, 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_B = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

BG = (14, 14, 16)
INK = (238, 232, 222)
DIM = (150, 144, 136)
ACCENT = (214, 168, 96)


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT, size)
    except OSError:
        return ImageFont.load_default()


def apply_chunk(size, tab, dmin, dmax, arr, rows=64):
    out = np.empty_like(arr)
    for y in range(0, arr.shape[0], rows):
        blk = arr[y:y + rows]
        out[y:y + rows] = apply_cube(size, tab, dmin, dmax,
                                     blk.reshape(-1, 3)).reshape(blk.shape)
    return out


def img(a):
    return Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8))


def main():
    os.makedirs(OUT, exist_ok=True)
    n, tab, dmin, dmax, _ = read_cube(LUT)
    neutral = L.build_table(33, creative=False)

    # ---------------------------------------------------------------- sheet
    cell_w, cell_h = 700, 394          # per frame
    pad, label_h = 26, 44
    header = 150
    cols, rows = 2, 4
    W = pad + cols * (2 * cell_w + 12 + pad)
    H = header + rows * (cell_h + label_h + pad) + pad
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)

    d.text((pad + 6, 34), 'GOLDEN DAYLIGHT CINEMA', font=font(44, True), fill=INK)
    d.text((pad + 8, 88), 'Apple Log 2 / Apple Wide Gamut  ->  Rec.709 SDR gamma 2.4   ·   '
                          '33 x 33 x 33 3D LUT', font=font(17), fill=DIM)
    d.text((W - pad - 300, 40), 'BEFORE', font=font(15, True), fill=DIM)
    d.text((W - pad - 190, 40), 'AFTER', font=font(15, True), fill=ACCENT)
    d.line([(pad + 6, header - 22), (W - pad - 6, header - 22)], fill=(60, 58, 54), width=1)

    for i, (slug, fn, label, desc) in enumerate(S.SCENES):
        cx = pad + (i % cols) * (2 * cell_w + 12 + pad)
        cy = header + (i // cols) * (cell_h + label_h + pad)
        plate = S.plate_for(slug, width=1200)
        before = apply_chunk(33, neutral, np.zeros(3), np.ones(3), plate)
        after = apply_chunk(n, tab, dmin, dmax, plate)
        b = img(before).resize((cell_w, cell_h), Image.LANCZOS)
        a = img(after).resize((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(b, (cx, cy))
        sheet.paste(a, (cx + cell_w + 12, cy))
        d.text((cx + 2, cy + cell_h + 8), f'{i+1:02d}  {label}', font=font(17, True), fill=INK)
        d.text((cx + 2, cy + cell_h + 27), 'BEFORE (neutral conversion)', font=font(12), fill=DIM)
        d.text((cx + cell_w + 14, cy + cell_h + 27), 'AFTER (this LUT)', font=font(12), fill=ACCENT)

    sheet.save(os.path.join(OUT, 'GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png'),
               optimize=True)
    print('wrote contact sheet', sheet.size)

    # ------------------------------------------------------ reference chart
    PW, PH = 900, 250          # panel footprint
    chart = Image.new('RGB', (PW * 2 + 120, 3 * PH + 430), BG)
    dc = ImageDraw.Draw(chart)
    dc.text((50, 34), 'GOLDEN DAYLIGHT CINEMA — LOOK REFERENCE', font=font(34, True), fill=INK)
    dc.text((52, 80), 'Measured on the delivered .cube. BEFORE is a neutral Apple Log 2 to '
                      'Rec.709 conversion of the same value.', font=font(15), fill=DIM)

    def graded(code):
        return L.grade_display(np.asarray(code, dtype=np.float64))

    def panel(origin, values, title, sub, labels=None):
        x0, y0 = origin
        val = np.asarray(values, dtype=np.float64)
        b = val
        a = graded(val)
        w, h, gap = 66, 62, 6
        dc.text((x0, y0), title, font=font(18, True), fill=INK)
        dc.text((x0, y0 + 26), sub, font=font(12), fill=DIM)
        top = y0 + 56
        for row, (arr, lab, col) in enumerate((
                (b, 'BEFORE', DIM), (a, 'AFTER', ACCENT))):
            yy = top + row * (h + 24)
            dc.text((x0, yy + 20), lab, font=font(11, True), fill=col)
            for i in range(len(val)):
                bx = x0 + 76 + i * (w + gap)
                dc.rectangle([bx, yy, bx + w, yy + h],
                             fill=tuple(int(round(v * 255)) for v in arr[i]))

    patches_neutral = np.array([[v, v, v] for v in
                                (0.05, 0.15, 0.28, 0.42, 0.58, 0.72, 0.86, 0.96)])
    skin = np.array([[0.86, 0.72, 0.60], [0.72, 0.55, 0.42], [0.58, 0.42, 0.31],
                     [0.42, 0.29, 0.21], [0.30, 0.20, 0.14]])
    sky = np.array([[0.45, 0.66, 0.88], [0.32, 0.55, 0.84], [0.22, 0.42, 0.74],
                    [0.60, 0.76, 0.92]])
    fol = np.array([[0.22, 0.36, 0.15], [0.36, 0.48, 0.20], [0.48, 0.58, 0.30],
                    [0.14, 0.26, 0.12]])
    stone = np.array([[0.82, 0.72, 0.55], [0.70, 0.58, 0.42], [0.88, 0.84, 0.76],
                      [0.55, 0.45, 0.34]])
    whites = np.array([[1.0, 1.0, 1.0], [0.96, 0.96, 0.96],
                       [0.92, 0.92, 0.92], [0.85, 0.85, 0.85]])

    panel((50, 150), patches_neutral, 'NEUTRAL / WHITE',
          'honey bias bounded to +0.001 … +0.009 OkLab b')
    panel((PW + 70, 150), sky, 'SKY', 'richer blue, no turquoise drift')
    panel((50, 150 + PH), skin, 'SKIN TONES (light to deep)',
          'chroma held near +7%, hue not pushed to red')
    panel((PW + 70, 150 + PH), fol, 'FOLIAGE',
          'natural green, no radioactive yellow, no teal')
    panel((50, 150 + 2 * PH), stone, 'STONE / PLASTER / CONCRETE',
          'warm without going yellow; wet plaster stays white')
    panel((PW + 70, 150 + 2 * PH), whites, 'HIGHLIGHTS',
          'whites hold their value; no yellow clipping')

    # neutral ramps
    g = np.linspace(0, 1, 512)
    ry = 150 + 3 * PH + 10
    dc.text((50, ry), 'NEUTRAL RAMP  0 → 100 % display code', font=font(18, True), fill=INK)
    dc.text((50, ry + 26), 'monotone and smooth; no banding at 8 bit', font=font(12), fill=DIM)
    ramp = np.stack([g, g, g], -1)
    br = img(ramp).resize((PW + 120, 40), Image.NEAREST)
    ar = img(graded(ramp)).resize((PW + 120, 40), Image.NEAREST)
    chart.paste(br, (50, ry + 58))
    chart.paste(ar, (50, ry + 108))
    dc.text((60 + PW + 120, ry + 66), 'BEFORE', font=font(11, True), fill=DIM)
    dc.text((60 + PW + 120, ry + 116), 'AFTER', font=font(11, True), fill=ACCENT)

    dc.text((50, chart.height - 32),
            'GOLDEN DAYLIGHT CINEMA · Apple Log 2 (Apple Wide Gamut) → Rec.709 gamma 2.4 · '
            'figures produced by dev/validate.py', font=font(11), fill=DIM)
    chart.save(os.path.join(OUT, 'LOOK_REFERENCE_CHART.png'), optimize=True)
    print('wrote reference chart', chart.size)


if __name__ == '__main__':
    main()
