# Golden Daylight Cinema — Build guide

Pipeline and tooling for the `GOLDEN_DAYLIGHT_CINEMA.cube` deliverable.
This file documents how the .cube, previews, validation, and gallery are
produced.  All simulation is transparent and labelled.

## Layout

    GOLDEN_DAYLIGHT_CINEMA_PROJECT/
      GOLDEN_DAYLIGHT_CINEMA/    the deliverable (zipped)
      build/                        the pipeline + tools (NOT in the zip)
      source_images/                 the 8 real photographs (NOT in the zip)
      simulated_log/                 8 simulated Apple Log 2 PNGs (NOT in zip)
      validation/                    synthetic charts (NOT in zip)

## Dependencies

    python -m venv .venv
    .venv/bin/pip install -r requirements.txt

Pinned: `numpy==2.4.6`, `Pillow==13.0.0` (repo-root requirements.txt).

## Build sequence

From the repository root:

    . .venv/bin/activate

    # 1. Simulate Apple Log 2 from real photos (transparent, deterministic)
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/simulate_log.py

    # 2. Bake the analytic .cube (33^3, RED varies fastest)
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/bake_lut.py

    # 3. Render BEFORE (neutral ref) / AFTER (shipped .cube, independent parser)
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/render_previews.py

    # 4. Render synthetic charts (grey ramp, hue sweep, saturation sweep,
    #    colorchecker-style patches, exposure ladder, skin line)
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/charts.py

    # 5. Run the full validation suite (writes GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt)
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/validate_lut.py

    # 6. Build the dark premium gallery
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/build_gallery.py

    # 7. Build the contact sheet
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/build_contact_sheet.py

    # 8. Build the ZIP and verify it
    python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/build_zip.py

## Pipeline notes

- **Verified Apple Log 2 (OETF + AWG)**: constants from Apple's Apple Log 2
  White Paper (September 2025); see build/color_science.py for the verified
  decode function and the Apple Wide Gamut -> Rec.709 matrix.  The neutral
  reference transform is `pipeline.neutral_reference`.
- **Grade** (`pipeline.grade_oklab`): OKLab-based parametric grade
  (density-style saturation, filmic toe/mid/shoulder, hue-selective
  sky/green/stone/skin protection, luminance-weighted warm split-tone,
  highlight roll, soft color gamut compression into Rec.709).  All stages
  are float64 scene-referred.
- **Bake**: analytic evaluation at 33^3 grid points; output Rec.709 gamma 2.4.
  The .cube is the ONLY deliverable; previews render through an *independent*
  .cube parser (`render_previews.py`) so the AFTER images validate the actual
  shipped file.
- **Simulation** (`simulate_log.py`): sRGB -> linear Rec.709 -> XYZ -> linear
  Apple Wide Gamut -> photon/read noise -> Apple Log 2 OETF -> 8-bit.  NOT real
  iPhone footage; labelled everywhere.

## Validation

`build/validate_lut.py` writes VALIDATION_REPORT.txt into
`GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` and prints to stdout.  It covers
cube integrity, trilinear/tetrahedral interpolation error vs analytic
(image-domain + uniform random), smoothness/monotonicity on diagonal,
8-bit/10-bit quantization, clipping % (BEFORE vs AFTER), shadow-noise gain,
±4-stop exposure ladder, skin-line check, sky/foliage hue histograms, and
SHA256 checksums of the .cube, previews, and charts.

## Notes / limitations

- .cube was baked at 33^3 points; trilinear interpolation is accurate in the
  image domain (max ΔE ~0.05) but outlier points at extreme chroma are larger.
- Previews use 8-bit PNGs.  No physical iPhone/Blackmagic Camera validation
  was performed.
