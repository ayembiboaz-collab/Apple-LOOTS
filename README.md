# GOLDEN DAYLIGHT CINEMA

One standalone, premium cinematic **33×33×33 3D LUT** for **Apple Log 2 / Apple
Wide Gamut** footage from the **iPhone 17 Pro / 17 Pro Max** (recorded with
Blackmagic Camera for iOS), delivering **Rec.709 SDR at gamma 2.4**.

Harsh midday becomes warm, rich, dimensional and expensive-looking: honeyed
sunlight, deep but detailed shadows, clean sun/shade separation, believed
whites, natural blue sky, natural foliage and natural skin — without becoming a
warm filter or an orange overlay.

## Get the files

| File | What it is |
|---|---|
| [`GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube`](GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube) | **the LUT** (1.19 MB) |
| [`GOLDEN_DAYLIGHT_CINEMA.zip`](GOLDEN_DAYLIGHT_CINEMA.zip) | the complete folder, verified (85 MB) |
| [`GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html`](GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html) | interactive before/after gallery |
| [`GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/`](GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/) | one-page visual overview |
| [`GOLDEN_DAYLIGHT_CINEMA/README.txt`](GOLDEN_DAYLIGHT_CINEMA/README.txt) | installation and usage |
| [`GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt`](GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt) | sources, tests, results, limitations |

On an iPhone, tap a `.cube` link and confirm **Download**; it lands in
*Files › Downloads*. GitHub serves these files with a download disposition, so
Safari saves the LUT rather than displaying it as text.

## The colour science

- **Apple Log transfer function** — Apple Log Profile White Paper (2023)
  constants, reproducing Apple's published anchors: 18% grey → 0.48827
  (Apple: 0.488 / code 500), 90% white → 0.68169 (0.682), 12× white → 1.000000.
  Apple Log 2 uses the same curve.
- **Apple Wide Gamut** — primaries from the Apple Log 2 White Paper (2025),
  R(0.725, 0.301) G(0.221, 0.814) B(0.068, −0.076), D65. Both ends are D65, so
  no chromatic adaptation is needed; the derived matrix was additionally
  cross-checked through ACES AP0 against the value merged into
  OpenColorIO-Config-ACES and agrees to **2.7 × 10⁻¹⁵**.
- **Output** — linear light raised to 1/2.4 (Rec.709 SDR gamma 2.4).

The LUT is standalone: it decodes the log curve, converts the gamut, applies
the grade and encodes the display gamma. Do **not** stack a separate Apple Log
conversion in front of it.

## Validation

13 checks pass on the delivered file. Full method, per-scene numbers and every
limitation are in
[`VALIDATION_REPORT.txt`](GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt).

Three real defects were found by measurement and fixed rather than shipped — a
luminance-ratio tone transfer that banded bright skies, a white-balance tilt
that put a measurable cast into neutral greys, and 8-bit quantisation banding in
the previews. Three test thresholds were also corrected where the *test* was
measuring the wrong thing; that is documented in §7 of the report.

## Honest status

- **Not tested on a physical iPhone** or in Blackmagic Camera.
- **The footage is simulated.** Eight AI-generated photorealistic plates were
  converted to Apple Log 2 / Apple Wide Gamut by a documented, reversible
  simulation. The LUT genuinely operates on real log code values, but this is
  not a device test and not iPhone sensor data.
- A LUT cannot recover clipped highlights or invent shadow detail.

## Rebuilding

```bash
pip install numpy pillow
cd GOLDEN_DAYLIGHT_CINEMA/BUILD
python3 build_lut.py && python3 render.py && python3 validate.py
python3 make_chart_image.py && python3 make_contact_sheet.py
python3 make_web_images.py && python3 make_report.py && python3 package_zip.py
```

The rebuilt `.cube` is byte-identical to the delivered one; the ZIP is
byte-reproducible.

> **Note on repository history.** An earlier, independent attempt at this
> project was previously merged into `main`. It has been superseded by this one:
> a pure grey card through the earlier file carries a 0.044 channel spread
> (≈11/255, visibly warm) and its black pins at 0.0000, whereas this delivery
> keeps a grey card grey (0.012, below the plain ungraded conversion's own
> 0.015) and lifts black to 0.057 so shadow detail survives. Its scripts are
> retained under `GOLDEN_DAYLIGHT_CINEMA/BUILD/superseded_attempt/` for
> provenance, and §10 of the validation report carries the full comparison.
