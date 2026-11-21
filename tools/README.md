# tools/ — independent GOLDEN_DAYLIGHT_CINEMA pipeline (alternative, non-canonical)

> **Read this first.** This folder holds the *self-contained* build & validation
> pipeline written in the same week as the canonical deliverable. Three parallel
> lines of work converged on this repo (the canonical suite now on `main`, and
> this alternative implementation). The **canonical deliverable** is the one in
> `GOLDEN_DAYLIGHT_CINEMA/`, documented at the repo root (`README.md`) and in
> `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` — every validation section
> there reports PASS. This pipeline is kept as an **independent cross-check**:
> an entire second implementation agreeing on direction is worth more than
> either alone. Note it was *not* the code behind the shipped cube.

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
  F (trilinear fidelity) report known limitations of our pass-7 bake.
- `source_images/` — eight real photographs used as simulated-plate inputs
  (see `source_images/CREDITS.md`).
- `requirements.txt` — numpy, scipy, Pillow, colour-science, PyOpenColorIO

## Key differences vs canonical

| Aspect | tools/ pipeline (this) | canonical (on `main`) |
|---|---|---|
| Preview plates | real photographs, simulated Log 2 (`source_images/`) | real photographs, inverse-EOTF + scene headroom expansion, simulated Log 2 (`sources/master_scenes/`, credits in `sources/CREDITS_AND_SOURCES.json`) |
| Grade | honey gate + pass-7 luma-neutral toe | consolidated grade; canonical validation report all sections PASS (`33³ trilinear vs analytical: mean 0.00268, p99 0.0283`) |
| Validation | exit 0 **with warnings** (neutral spread ≈ 0.059, shoulder non-monotonicity ≈ −0.007, axis/trilinear outliers in the far out-of-gamut AWG corner) | all PASS, per `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` |
| Output paths | writes into `ALT_PREVIEWS/`, `GALLERY/alt_img/` (redirected) | canonical `PREVIEWS/`, `GALLERY/` |
| Our pass-7 cube | recoverable at git commit `b5a98a2` | — |

## Why keep it

- Second, independent implementation of Apple Log 2 decode + AWG handling — discrepancies between the two would be instantly suspicious.
- Self-contained (no dependency on `scripts/`), good for eyeballing the math.
- Documents *what didn't ship and why*, which is worth more than a clean success story.
