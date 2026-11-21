# GOLDEN DAYLIGHT CINEMA

A single, standalone cinematic 33×33×33 3D LUT for **Apple Log 2 / Apple Wide Gamut**
footage (iPhone 17 Pro / 17 Pro Max, e.g. recorded with Blackmagic Camera for iOS),
outputting **Rec.709 SDR, gamma 2.4**.

> **Download:** [`GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube`](GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube)
> · the whole folder as [`GOLDEN_DAYLIGHT_CINEMA.zip`](GOLDEN_DAYLIGHT_CINEMA.zip)

The LUT performs the Apple Log 2 decode, the Apple Wide Gamut → Rec.709 gamut
transform, the creative grade and the Rec.709 gamma 2.4 output encode in one
table. It must **not** be stacked on a separate conversion LUT.

| | |
|---|---|
| Input | Apple Log 2 / Apple Wide Gamut, normalised full range |
| Output | Rec.709 primaries, D65, gamma 2.4 (BT.1886) |
| Size | 33³ = 35,937 entries, 971,573 bytes |
| SHA-256 | `22032e6c5d779241328250115901a9501f6419b6bdb048e18e037a90bffc74c2` |

## Repository layout

| Path | Contents |
|---|---|
| `GOLDEN_DAYLIGHT_CINEMA/LUT/` | the delivered `.cube` |
| `GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/` | 8 BEFORE + 8 AFTER PNGs (+ neutral reference renders) |
| `GOLDEN_DAYLIGHT_CINEMA/GALLERY/` | responsive HTML preview gallery |
| `GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/` | visual overview |
| `GOLDEN_DAYLIGHT_CINEMA/README.txt` | install + usage for Blackmagic Camera on iPhone |
| `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` | sources, tests, results, limitations |
| `scripts/` | the complete, reproducible build pipeline |
| `sources/` | the eight source stills + `CREDITS.md` |
| `index.html` | redirect to the gallery, for GitHub Pages |

This repository was built over several separate sessions, each of which
produced its own pipeline and its own candidate LUT. Exactly **one** LUT ships:
the file above. The superseded material was removed from the tip of `main`
during the final merge and remains in the git history.

## Reproducing the build

```bash
pip install -r requirements.txt
python3 scripts/verify_colorscience.py     # independent maths verification
python3 scripts/build_lut.py               # bake the .cube
python3 scripts/simulate_log2.py           # simulated Apple Log 2 frames
python3 scripts/render_previews.py         # BEFORE / AFTER from the delivered .cube
python3 scripts/contact_sheet.py
python3 scripts/build_gallery.py
python3 scripts/validate.py                # validation suite, 34 checks
python3 scripts/package.py                 # ZIP + verification of the ZIP
```

`validate.py` and `package.py` both exit non-zero if any check fails.

## Validation

34 of 34 automated checks pass against the delivered file, including:

* valid 33³ `.cube` syntax, 35,937 entries, no NaN, no infinity, all values in [0, 1]
* Apple Log 2 decode reproduces all four of Apple's published anchor points
  (0 %, 18 %, 90 %, 1200 % reflectance) to within one 10-bit code
* the Apple Wide Gamut matrix, re-derived from the published chromaticities,
  matches the OpenColorIO reference to 2.4 × 10⁻¹⁵
* neutral ramp monotonic, no banding, no slope discontinuity
* skin / sky / foliage / stone / white / shadow behaviour measured on all eight scenes
* the look holds from −2 EV to +2 EV
* **all eight AFTER previews are bit-identical to a fresh render from the shipped `.cube`**

## Honesty notes

* The preview frames use **documented simulated Apple Log 2**, derived from
  stills by an explicit, published chain (`scripts/simulate_log2.py`).
  They are **not** iPhone sensor captures.
* **No physical iPhone or Blackmagic Camera testing has been performed.**
  The install instructions are transcribed from current vendor documentation,
  not from a device test.
* See `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` for exactly what was
  verified, what was assumed, and the known trade-offs.
