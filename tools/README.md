# tools/ — independent GOLDEN_DAYLIGHT_CINEMA pipeline (alternative, non-canonical)

> **Read this first.** This folder holds the *self-contained* build & validation
> pipeline written for this project. It was developed on the same base as the
> main-line suite and reaches the same destination, but the **canonical
> deliverable** that ships in `GOLDEN_DAYLIGHT_CINEMA/` is the main-line one
> (see `README.md`, `BUILDING.md`, root `SOURCES.md`, and
> `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt`): its `.cube` passed more
> rigorous checks (monotonic neutral ramp, tetrahedral ReproDiff = 0.0 for all
> 8 renders, OCIO cross-check ≈ 4.5e-07). This pipeline's pass-7 build measured
> worse on those axes (sub-1%-of-range shoulder non-monotonicity, neutral
> spread ≈ 0.059) and was superseded by the merge — but it is kept as an
> independent cross-check, since an entire second implementation agreeing on
> direction is worth more than either alone.

## Layout

- `lut_core.py` — Apple Log 2 OETF/EOTF + AWG/Rec.709 matrices + XYZ helpers
- `grade.py` — the creative grade (pass-7: honey gate, luma-neutral cool toe,
  highlight desaturation, vibrance, hue-shaping for greens/cyans/blues/skin/reds)
- `build_lut.py` — 33³ bake; writes `GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube`
  (**overwrites the canonical cube if run — back it up first**)
- `render_previews.py` — writes BEFORE/AFTER PNGs to `GOLDEN_DAYLIGHT_CINEMA/ALT_PREVIEWS/`
  (deliberately redirected so it can never clobber the canonical renders)
- `build_contact_sheet.py` — reads `ALT_PREVIEWS/`, writes
  `CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_ALT_contact_sheet.png`
- `build_gallery_assets.py` — reads `ALT_PREVIEWS/`, writes `GALLERY/alt_img/*.jpg`
- `validate_lut.py` — A–H suite (OCIO cross-check, monotonicity, sweeps, ROI skin/sky/foliage);
  reads `ALT_PREVIEWS/`. Note: this suite's "PASS" exit code does **not** imply
  the cube is clean — sections D (neutral spread), E (axis smoothness), and
  F (trilinear fidelity) report known limitations of the pass-7 bake.
- `source_images/` — eight real photographs used as simulated-plate inputs
  (see `source_images/CREDITS.md`). The canonical suite instead uses
  AI-generated photoreal plates (`sources/plates/`, see root `SOURCES.md`).
- `requirements.txt` — numpy, scipy, Pillow, colour-science, PyOpenColorIO

## Key difference vs canonical

| Aspect | tools/ pipeline (this) | canonical (main-line) |
|---|---|---|
| Preview plates | real sRGB photos, simulated Log 2 | AI-generated neutral plates, simulated Log 2 |
| Tone/grade | honey gate + pass-7 toe | integrated grade, passes monotonicity |
| Cube evaluation | trilinear | tetrahedral |
| Validation verdict | exit 0 with warnings (see VALIDATION_REPORT of the canonical suite vs `tools/validate_*.txt`) | stricter, all PASS |

If you want to compare the two cubes side by side, keep the canonical cube and
ours recoverable at git tag history: our pass-7 bake is commit `b5a98a2`.
