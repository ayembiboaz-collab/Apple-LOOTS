#!/usr/bin/env python3
"""
render.py -- render BEFORE / AFTER pairs for the eight scenes.

BEFORE : simulated Apple Log 2 -> plain technical conversion to Rec.709 gamma 2.4
         (bare decode, hard clip, no creative grade).
AFTER  : exactly the same simulated Apple Log 2 frame, pushed through the
         DELIVERED .cube file, re-read from disk and interpolated trilinearly.

Nothing in the AFTER path calls the analytic grade: the pixels you see are the
result of the shipped LUT. This is verified afterwards by validate.py, which
re-renders and compares against the files on disk.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade            # noqa: E402
import simulate         # noqa: E402
from cube import apply_cube, read_cube  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLATES = os.path.join(ROOT, "SOURCE_PLATES")
PREVIEWS = os.path.join(ROOT, "PREVIEWS")
LUT = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

SCENES = [
    ("scene01", "harsh_midday_city",              "Harsh Midday City"),
    ("scene02", "midday_portrait",                "Midday Portrait in Direct Sun"),
    ("scene03", "mediterranean_street",           "Mediterranean Street"),
    ("scene04", "bright_beach_daylight",          "Bright Beach Daylight"),
    ("scene05", "landscape_greenery_mountains",   "Landscape: Greenery and Mountains"),
    ("scene06", "golden_hour_landscape",          "Golden-Hour Landscape"),
    ("scene07", "modern_architecture",            "Modern Architecture"),
    ("scene08", "outdoor_travel_people",          "Outdoor Travel: People and Buildings"),
]


def load_plate(stem):
    path = os.path.join(PLATES, f"scene{stem}.png") if stem[0].isdigit() else \
        os.path.join(PLATES, f"{stem}.png")
    im = Image.open(path).convert("RGB")
    return np.asarray(im, dtype=np.float64) / 255.0


def _dither(h, w, seed=0):
    """Deterministic triangular-PDF dither, +-0.5 LSB, for 8-bit export only.

    An 8-bit PNG of a smooth sky bands even when the underlying float data is
    perfectly smooth; that is a *storage* artefact, not a property of the LUT.
    Dithering the final quantisation is standard practice and keeps the gallery
    honest about the smoothness of the actual transform. It is applied here and
    only here - the .cube and the 16-bit render path contain no dither.
    """
    rng = np.random.default_rng(1234 + seed)
    return ((rng.random((h, w, 1)) + rng.random((h, w, 1)) - 1.0) / 255.0)


def to_png(arr, path, dither=True, seed=0):
    a = np.clip(arr, 0.0, 1.0)
    if dither:
        a = np.clip(a + _dither(a.shape[0], a.shape[1], seed), 0.0, 1.0)
    Image.fromarray((a * 255.0 + 0.5).astype(np.uint8)).save(
        path, format="PNG", optimize=True)


def main(only=None):
    os.makedirs(PREVIEWS, exist_ok=True)
    table, meta = read_cube(LUT)
    report = {"lut": os.path.relpath(LUT, ROOT), "lut_shape": list(table.shape),
              "scenes": []}

    for idx, (sid, stem, title) in enumerate(SCENES, start=1):
        if only and sid not in only:
            continue
        srgb = load_plate(f"{sid[5:]}_{stem}" if False else
                          [f for f in os.listdir(PLATES) if f.endswith(f"{stem}.png")][0][:-4])
        log2 = simulate.plate_to_apple_log2(srgb)

        before = grade.neutral_technical(log2)
        after = apply_cube(log2, table, meta["domain_min"], meta["domain_max"])

        base = f"{sid}_{stem}"
        # The simulated log plate is included so the input can be inspected.
        # Dither is applied here for the same storage reason as below: 8-bit
        # PNG of the steep log signal bands on its own even when the float
        # data is smooth (measured: plateau 0.206 vs 0.133 on the source).
        to_png(log2, os.path.join(PREVIEWS, f"{base}_LOG2_SIMULATED.png"), seed=7)
        to_png(before, os.path.join(PREVIEWS, f"{base}_BEFORE.png"))
        to_png(after,  os.path.join(PREVIEWS, f"{base}_AFTER.png"))

        # measured summary for the LUT-lattice accuracy check
        exact = grade.apply_grade(log2)
        err = np.abs(exact - after)
        report["scenes"].append({
            "id": sid,
            "title": title,
            "plate": f"SOURCE_PLATES/{stem}.png",
            "resolution": list(srgb.shape[:2]),
            "lut_vs_analytic_max_abs": float(err.max()),
            "lut_vs_analytic_mean_abs": float(err.mean()),
            "mean_luma_before": float(before.mean()),
            "mean_luma_after": float(after.mean()),
            "p99_luma_before": float(np.percentile(before, 99)),
            "p99_luma_after": float(np.percentile(after, 99)),
            "clipped_fraction_before": float((before >= 0.999).mean()),
            "clipped_fraction_after": float((after >= 0.999).mean()),
            "crushed_fraction_before": float((before <= 0.004).mean()),
            "crushed_fraction_after": float((after <= 0.004).mean()),
        })
        print(f"{sid} {title:38s} LUT-vs-analytic max={err.max():.5f} "
              f"luma {before.mean():.3f}->{after.mean():.3f}")

    with open(os.path.join(ROOT, "VALIDATION", "render_stats.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    print("\nwrote PREVIEWS/*.png and VALIDATION/render_stats.json")


if __name__ == "__main__":
    main(only=set(sys.argv[1:]) or None)
