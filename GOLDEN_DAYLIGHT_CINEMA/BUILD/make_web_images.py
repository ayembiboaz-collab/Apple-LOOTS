#!/usr/bin/env python3
"""
make_web_images.py -- downscale the PNG deliverables for the mobile gallery.

PREVIEWS/*.png remain the high-resolution PNG deliverables. The gallery loads
these JPEG derivatives (1400 px wide, quality 90) so it stays fast on a phone
over a mobile connection. Nothing here feeds back into the LUT or the AFTER
renders; it is a display-only derivative.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREV = os.path.join(ROOT, "PREVIEWS")
OUT = os.path.join(ROOT, "GALLERY", "img")


def main(width=1400, quality=90):
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for sid, stem, title in R.SCENES:
        for tag in ("BEFORE", "AFTER", "LOG2_SIMULATED"):
            src = os.path.join(PREV, f"{sid}_{stem}_{tag}.png")
            if not os.path.exists(src):
                continue
            im = Image.open(src).convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)),
                               Image.LANCZOS)
            name = "LOG2" if tag == "LOG2_SIMULATED" else tag
            im.save(os.path.join(OUT, f"{sid}_{name}.jpg"), quality=quality,
                    optimize=True, progressive=True)
            n += 1
    # the gallery contact sheet is written by make_contact_sheet.py directly
    print(f"wrote {n} gallery images to GALLERY/img")


if __name__ == "__main__":
    main()
