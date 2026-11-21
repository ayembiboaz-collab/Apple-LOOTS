#!/usr/bin/env python3
"""
make_contact_sheet.py -- build CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png

Eight scenes as paired BEFORE / AFTER panels with labels, on a premium dark
background. Also writes a compact web-sized version used by the gallery.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(ROOT, "PREVIEWS")
OUT = os.path.join(ROOT, "CONTACT_SHEET")

INK = (14, 14, 16)
TXT = (232, 228, 220)
DIM = (138, 134, 128)
ACCENT = (214, 176, 112)


def font(size, bold=False):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def panel(src, dst, w, label_before="BEFORE", label_after="AFTER"):
    im = Image.open(src).convert("RGB")
    h = int(w * im.height / im.width)
    return im.resize((w, h), Image.LANCZOS)


def build(width=1800):
    margin = 64
    gutter = 28
    pw = (width - margin * 2 - gutter) // 2
    ph = int(pw * 768 / 1408)

    rows = []
    for sid, stem, title in R.SCENES:
        rows.append((title, os.path.join(PREV, f"{sid}_{stem}_BEFORE.png"),
                     os.path.join(PREV, f"{sid}_{stem}_AFTER.png")))

    head = 210
    cap = 46
    rowh = ph + cap + 34
    H = head + len(rows) * rowh + margin + 40
    im = Image.new("RGB", (width, H), INK)
    d = ImageDraw.Draw(im)

    d.text((margin, 64), "GOLDEN DAYLIGHT CINEMA", font=font(58, True), fill=TXT)
    d.text((margin, 138), "Apple Log 2 / Apple Wide Gamut  \u2192  Rec.709 SDR, "
                          "gamma 2.4   \u00b7   iPhone 17 Pro \u00b7 Blackmagic Camera",
           font=font(24), fill=DIM)
    d.text((width - margin - 330, 148), "BEFORE  \u00b7  AFTER", font=font(24, True),
           fill=ACCENT)
    d.line([(margin, head - 30), (width - margin, head - 30)], fill=(52, 50, 48), width=2)

    y = head
    for title, b, a in rows:
        d.text((margin, y - 2), title, font=font(26, True), fill=TXT)
        yy = y + cap
        im.paste(panel(b, None, pw), (margin, yy))
        im.paste(panel(a, None, pw), (margin + pw + gutter, yy))
        d.text((margin + 8, yy + 8), "BEFORE", font=font(18, True), fill=(255, 255, 255))
        d.text((margin + pw + gutter + 8, yy + 8), "AFTER", font=font(18, True),
               fill=(255, 255, 255))
        y += rowh

    d.text((margin, H - 34),
           "BEFORE and AFTER are the same simulated Apple Log 2 frame; AFTER is rendered "
           "through the delivered .cube. Simulated input - not iPhone sensor footage.",
           font=font(20), fill=DIM)

    os.makedirs(OUT, exist_ok=True)
    full = os.path.join(OUT, "GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png")
    im.save(full, optimize=True)
    # web derivative for the gallery, written straight to its final home so the
    # archive does not carry a second copy
    gdir = os.path.join(ROOT, "GALLERY", "img")
    os.makedirs(gdir, exist_ok=True)
    web = im.resize((1400, round(H * 1400 / width)), Image.LANCZOS)
    web.save(os.path.join(gdir, "contact_sheet.jpg"), quality=90, optimize=True,
             progressive=True)
    print("wrote", os.path.relpath(full, ROOT), im.size,
          f"({os.path.getsize(full)/1e6:.1f} MB)")


if __name__ == "__main__":
    build()
