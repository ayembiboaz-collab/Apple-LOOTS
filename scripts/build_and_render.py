"""
Build GOLDEN_DAYLIGHT_CINEMA.cube and render all 8 BEFORE (Simulated Apple Log 2)
and AFTER (Rec.709 Gamma 2.4 via actual .cube tetrahedral evaluation) PNG previews.
"""

from __future__ import annotations

import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from color_pipeline import (
    GradeParams,
    build_3d_lut,
    write_cube_file,
    read_cube_file,
    apply_3d_lut_tetrahedral,
    sdr_srgb_to_simulated_apple_log2,
)

SCENES = [
    ("01_harsh_midday_city", "Harsh Midday City"),
    ("02_midday_portrait", "Midday Portrait in Direct Sunlight"),
    ("03_mediterranean_street", "Mediterranean Street"),
    ("04_bright_beach_daylight", "Bright Beach Daylight"),
    ("05_natural_landscape_greenery_mountains", "Natural Landscape with Greenery & Mountains"),
    ("06_golden_hour_landscape", "Golden-Hour Landscape"),
    ("07_modern_architecture", "Modern Architecture"),
    ("08_outdoor_travel_people_buildings", "Outdoor Travel Scene with People & Buildings"),
]


def main() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_root = os.path.join(root, "GOLDEN_DAYLIGHT_CINEMA")
    lut_dir = os.path.join(out_root, "LUT")
    prev_dir = os.path.join(out_root, "PREVIEWS")
    os.makedirs(lut_dir, exist_ok=True)
    os.makedirs(prev_dir, exist_ok=True)

    cube_path = os.path.join(lut_dir, "GOLDEN_DAYLIGHT_CINEMA.cube")

    print("Building 33x33x33 3D LUT...")
    params = GradeParams()
    lut = build_3d_lut(size=33, params=params)
    write_cube_file(cube_path, lut, title="GOLDEN_DAYLIGHT_CINEMA")
    print(f"Wrote {cube_path} ({os.path.getsize(cube_path) / 1024:.1f} KB)")

    # Read back the actual written .cube file to guarantee rendered proofs come
    # exclusively from the delivered .cube file.
    size, loaded_lut, meta = read_cube_file(cube_path)
    assert size == 33

    rng = np.random.default_rng(42)

    for slug, label in SCENES:
        src_path = os.path.join(root, "sources", "plates", f"{slug}.png")
        im = Image.open(src_path).convert("RGB")
        arr_srgb = np.asarray(im, dtype=np.float64) / 255.0

        # Simulate Apple Log 2 input with triangular-PDF 8-bit dither (0.5 LSB)
        # to prevent 8-bit log posterization while remaining reproducible.
        log2_f = sdr_srgb_to_simulated_apple_log2(arr_srgb)
        tpdf = (rng.uniform(-0.5, 0.5, log2_f.shape) + rng.uniform(-0.5, 0.5, log2_f.shape)) / 255.0
        before_u8 = np.clip(np.round((log2_f + tpdf) * 255.0), 0, 255).astype(np.uint8)

        before_path = os.path.join(prev_dir, f"{slug}_BEFORE.png")
        Image.fromarray(before_u8, mode="RGB").save(before_path, format="PNG", optimize=True)

        # Apply the ACTUAL delivered .cube file to the saved BEFORE image
        before_norm = before_u8.astype(np.float64) / 255.0
        after_norm = apply_3d_lut_tetrahedral(before_norm, loaded_lut)
        after_u8 = np.clip(np.round(after_norm * 255.0), 0, 255).astype(np.uint8)

        after_path = os.path.join(prev_dir, f"{slug}_AFTER.png")
        Image.fromarray(after_u8, mode="RGB").save(after_path, format="PNG", optimize=True)

        print(f"Rendered {slug}: BEFORE mean={before_norm.mean():.3f}, AFTER mean={after_norm.mean():.3f}")


if __name__ == "__main__":
    main()
