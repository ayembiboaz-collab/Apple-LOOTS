#!/usr/bin/env python3
"""Build the printed-style contact sheets shipped in CONTACT_SHEET/."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

import render_previews as rp

ROOT = rp.ROOT
PROJ = rp.PROJ
OUT = os.path.join(PROJ, "CONTACT_SHEET")
PREV = os.path.join(PROJ, "PREVIEWS")

BG = (14, 14, 16)
FG = (232, 228, 220)
DIM = (150, 146, 138)
ACCENT = (214, 168, 92)


def font(size, bold=False):
    for name in (("DejaVuSans-Bold.ttf", "DejaVuSans.ttf") if bold else ("DejaVuSans.ttf",)):
        for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fit(img, w, h):
    """Contain-fit into w x h on the sheet background (no cropping)."""
    r = min(w / img.width, h / img.height)
    im = img.resize((max(1, int(img.width * r + 0.5)), max(1, int(img.height * r + 0.5))), Image.LANCZOS)
    box = Image.new("RGB", (w, h), BG)
    box.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return box


def sheet_scenes(scenes, rows, cols, thumb_w, thumb_h, title, subtitle, path):
    pad, gap = 44, 22
    label_h = 30
    w = pad * 2 + cols * thumb_w * 2 + gap * (2 * cols - 1) + gap * cols
    h = pad * 2 + 96 + rows * (thumb_h + label_h + gap) + (rows - 1) * gap
    canvas = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(canvas)
    d.text((pad, pad - 6), title, font=font(40, True), fill=FG)
    d.text((pad, pad + 46), subtitle, font=font(19), fill=DIM)

    y = pad + 96
    for r in range(rows):
        x = pad
        for c in range(cols):
            idx = r * cols + c
            if idx >= len(scenes):
                break
            num, slug, name, _ = scenes[idx]
            before = Image.open(os.path.join(PREV, "BEFORE", f"BEFORE_{num}_{slug}.png")).convert("RGB")
            after = Image.open(os.path.join(PREV, "AFTER", f"AFTER_{num}_{slug}.png")).convert("RGB")
            canvas.paste(fit(before, thumb_w, thumb_h), (x, y))
            canvas.paste(fit(after, thumb_w, thumb_h), (x + thumb_w + gap, y))
            d.text((x + 4, y + thumb_h + 7), "BEFORE", font=font(15, True), fill=DIM)
            d.text((x + thumb_w + gap + 4, y + thumb_h + 7), "AFTER", font=font(15, True), fill=ACCENT)
            d.text((x + 96, y + thumb_h + 7), f"{num}  {name}", font=font(15), fill=FG)
            x += thumb_w * 2 + gap * 3
        y += thumb_h + label_h + gap

    footer = "Apple Log 2 / Apple Wide Gamut  ->  Rec.709 gamma 2.4    |    GOLDEN DAYLIGHT CINEMA 33^3"
    d.text((pad, h - pad + 4), footer, font=font(15), fill=DIM)
    canvas.save(path, quality=94, optimize=True, subsampling=1)
    print("wrote", path, canvas.size)


rows_scenes = rp.SCENES


def main():
    os.makedirs(OUT, exist_ok=True)
    sheet_scenes(rp.SCENES[:4], 2, 2, 430, 287,
                 "GOLDEN DAYLIGHT CINEMA",
                 "Eight daylight scenes - top row 01-02, bottom row 03-04. "
                 "Before = neutral Rec.709 render of the same Apple Log 2 frame.",
                 os.path.join(OUT, "contact_sheet_A_scenes_01-04.jpg"))
    sheet_scenes(rp.SCENES[4:], 2, 2, 430, 287,
                 "GOLDEN DAYLIGHT CINEMA",
                 "Eight daylight scenes - top row 05-06, bottom row 07-08.",
                 os.path.join(OUT, "contact_sheet_B_scenes_05-08.jpg"))

    # exposure test sheet
    files = ["AFTER_03_mediterranean_-1_stop.jpg",
             "AFTER_03_mediterranean_normal.jpg",
             "AFTER_03_mediterranean_+1_stop.jpg"]
    labels = ["-1 stop", "normal", "+1 stop"]
    tw, th, gap, pad = 480, 320, 20, 44
    w = pad * 2 + 3 * tw + 2 * gap
    h = pad * 2 + 96 + th + 34
    canvas = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(canvas)
    d.text((pad, pad - 6), "EXPOSURE ROBUSTNESS", font=font(40, True), fill=FG)
    d.text((pad, pad + 46), "Scene 03 re-exposed +/-1 stop before the LUT. No channel clips at either end.",
           font=font(19), fill=DIM)
    for i, (f, lab) in enumerate(zip(files, labels)):
        im = Image.open(os.path.join(PREV, "EXPOSURE_TESTS", f)).convert("RGB")
        canvas.paste(fit(im, tw, th), (pad + i * (tw + gap), pad + 96))
        d.text((pad + i * (tw + gap) + 4, pad + 96 + th + 7), lab.upper(), font=font(16, True), fill=ACCENT)
    canvas.save(os.path.join(OUT, "contact_sheet_C_exposure.jpg"), quality=94, optimize=True, subsampling=1)
    print("wrote contact_sheet_C_exposure.jpg", canvas.size)


if __name__ == "__main__":
    main()
