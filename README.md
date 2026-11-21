# GOLDEN DAYLIGHT CINEMA

A single, standalone cinematic 33×33×33 3D LUT for **Apple Log 2 / Apple Wide Gamut**
footage (iPhone 17 Pro / 17 Pro Max, e.g. recorded with Blackmagic Camera for iOS),
outputting **Rec.709 SDR, gamma 2.4**.

> **Deliverables live in [`GOLDEN_DAYLIGHT_CINEMA/`](GOLDEN_DAYLIGHT_CINEMA/)
> and in `GOLDEN_DAYLIGHT_CINEMA.zip`.**

The LUT performs the Apple Log 2 decode, the Apple Wide Gamut → Rec.709 gamut
transform, the creative grade and the Rec.709 gamma 2.4 output encode in one
table. It must **not** be stacked on a separate conversion LUT.

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
| `sources/` | source stills + credits |

## Reproducing the build

```bash
pip install numpy pillow
python3 scripts/verify_colorscience.py     # independent maths verification
python3 scripts/build_lut.py               # bake the .cube
python3 scripts/simulate_log2.py           # simulated Apple Log 2 frames
python3 scripts/render_previews.py         # BEFORE / AFTER from the delivered .cube
python3 scripts/contact_sheet.py
python3 scripts/build_gallery.py
python3 scripts/validate.py                # validation suite
python3 scripts/package.py                 # ZIP + verification of the ZIP
```

## Honesty notes

* The preview frames use **documented simulated Apple Log 2**, derived from
  stills by an explicit, published chain (`scripts/simulate_log2.py`).
  They are **not** iPhone sensor captures.
* **No physical iPhone or Blackmagic Camera testing has been performed.**
* See `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` for exactly what was
  verified, what was assumed, and the known trade-offs.
