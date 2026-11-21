# GOLDEN DAYLIGHT CINEMA

A daylight colour transform for **Apple Log 2 / Apple Wide Gamut** footage from the iPhone 17 Pro
(shot with Blackmagic Camera for iOS), converting it to a finished **Rec.709 SDR image at display
gamma 2.4**. One LUT, no look pack, every claim measured.

```
GOLDEN_DAYLIGHT_CINEMA/
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube    33^3 .cube, 35,937 rows, 971,140 bytes
  PREVIEWS/BEFORE/                   plain Rec.709 conversion of each test frame
  PREVIEWS/AFTER/                    the same frames through the LUT
  PREVIEWS/EXPOSURE_TESTS/           scene 03 at -1 / 0 / +1 stop
  CONTACT_SHEET/                     printable contact sheets
  GALLERY/index.html                 offline gallery, drag to compare
  README.txt                         install + shooting guidance
  VALIDATION_REPORT.txt              all measurements, including the weak spots
```

## Start here

| | |
|---|---|
| **See it** | [`GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html`](GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html) — open locally, no network needed |
| **Use it** | [`GOLDEN_DAYLIGHT_CINEMA/README.txt`](GOLDEN_DAYLIGHT_CINEMA/README.txt) — Resolve, Final Cut, Premiere, FFmpeg |
| **Audit it** | [`GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt`](GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt) |
| **The LUT itself** | [`GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube`](GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube) |

## What it does

* Converts Apple Wide Gamut to Rec.709 with a Bradford D65 adaptation — white stays exactly white
  (error 2.2e-16), and the matrix inverts cleanly.
* Applies a filmic tone curve anchored to Apple's published Apple Log 2 curve
  (18% reflectance → code 0.4883, max deviation from the white paper 8.0e-7).
* Eases highlights into white instead of clipping them, cools shadows and warms highlights in a way
  that is gated on the input, so already-warm footage does not double-warm.
* Compresses saturated colours into the 709 gamut with a smooth minimum, so turquoise water and blue
  skies roll off instead of turning into colour blocks.
* Holds skin hue to **0.2°** across the reference portrait and clips **0.00%** of pixels at ±1 stop.

## Measured on the shipped file

| Test | Result |
|---|---|
| Cube structure | 33³, 0 NaN, 0 Inf, 0 out-of-range, no 1.0 or 0.0 outputs |
| Apple curve | max error 8.0e-7 code; 10-bit 154 / 500 / 697 / 1023 all match the paper |
| Gamut matrix | row sums and inverse exact to 2.2e-16 |
| Neutral axis | monotonic, **0 flat steps**, no back-steps, mid-grey channel spread 0.0085 |
| 2.4 encoding | exact at every node (1.1e-6 linear) |
| Preview provenance | every preview re-rendered from the .cube: **0/255 max difference** |
| Skin hue drift | 0.2° max |
| Clipping at ±1 stop | 0.00% |

The honest caveats — deep-shadow contrast is deliberately compressed, saturated colours can be
slightly non-monotonic off-axis, and the preview sources are simulated log frames — are written up
in section 12 of the validation report.

## Rebuilding

Everything is generated from Apple's published transfer function and primaries; nothing is hand-tuned
in a paint program.

```bash
python3 build/make_lut.py            # writes the .cube
python3 build/render_previews.py     # renders PREVIEWS/ from the .cube on disk
python3 build/validate.py            # 12 test groups -> build/validation_results.json
python3 build/make_report.py         # VALIDATION_REPORT.txt from that JSON
python3 build/make_contact_sheet.py  # CONTACT_SHEET/
python3 build/make_gallery.py        # GALLERY/index.html
```

Requires Python 3.10+, numpy, Pillow.

`build/apple_log2.py` holds the Apple Log 2 encode/decode, the primaries and colour matrices,
Bradford/CAT02 adaptation and OKLab. `build/grade.py` holds the grade and the analytic transform that
the LUT samples. `build/simulate.py` turns SDR photographs into physically plausible Apple Log 2
frames so the previews exercise real image statistics rather than test patches.

## Credits

Preview photographs are royalty-free stock images (Pexels) used as demonstration frames. The Apple
Log 2 frames in this package are simulations of those photographs built from Apple's published
transfer function and primaries — not recordings from an iPhone.
