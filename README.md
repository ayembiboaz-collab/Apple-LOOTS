# GOLDEN DAYLIGHT CINEMA

A premium, standalone **33 × 33 × 33 3D `.cube` LUT** for **iPhone 17 Pro / Pro Max**
footage recorded in **Apple Log 2 (Apple Wide Gamut)** — e.g. with **Blackmagic Camera
for iOS** — delivering **Rec.709 SDR, gamma 2.4**.

One file, whole pipeline: it decodes Apple Log 2, converts Apple Wide Gamut to
Rec.709, applies the *Golden Daylight Cinema* grade and encodes gamma 2.4.
No separate conversion LUT required.

## The look

Harsh midday footage becomes warm, rich and dimensional — the honeyed light of a
luxury Mediterranean travel film, not a yellow Instagram preset:

- **Golden sunlight** — honey/amber warmth in sunlit midtones; whites stay believable, no overall yellow cast; warmth is attenuated on already-warm golden-hour content
- **Filmic contrast** — rich midtones, deep but detailed shadows, smooth highlight roll-off; never brightens already-bright footage
- **Skies** — richer, slightly deeper natural blue, cyan controlled, cloud whites clean
- **Greenery** — natural, slightly warm greens, controlled saturation, never radioactive or teal
- **Skin** — natural and subtly warm across lighting; sunlit highlights roll off creamy; no beauty-filter effects
- **Shade** — a very subtle cool split-tone in deep desaturated shadows for sun/shade separation

## Contents

| Path | What it is |
|---|---|
| `GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube` | **the LUT** |
| `GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/` | 8 × BEFORE / 8 × AFTER PNGs (AFTER rendered from the delivered cube) |
| `GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html` | responsive, touch-friendly dark preview gallery |
| `GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/` | contact sheet + exposure sweep (−2…+2 EV) |
| `GOLDEN_DAYLIGHT_CINEMA/README.txt` | installation & usage (Blackmagic Camera on iPhone) |
| `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` | sources, tests, results, limitations |
| `GOLDEN_DAYLIGHT_CINEMA.zip` | the complete package (extract- and md5-verified) |
| `scripts/` | full reproducible build system (Python, numpy + Pillow) |
| `sources/` | credited AI-generated test-scene stills + credits |

## Engineering & verification

- Transfer function and Apple Wide Gamut chromaticities from Apple's **Apple Log 2
  White Paper (September 2025)** — anchor points reproduced exactly
  (18 % → 0.488272, 90 % → 0.681686, 1200 % → 1.0).
- Gamut mathematics cross-checked against **OpenColorIO's** Apple Wide Gamut
  implementation to **3.55 × 10⁻¹⁵**.
- **29/29 validation checks** pass on the delivered `.cube`: structure/syntax,
  33³ dimensions, no NaN/Inf, grey-axis neutrality, monotonicity, banding probes,
  skin/sky/foliage swatch behaviour across exposures, exposure sweeps, and
  pixel-exact reproduction of every shipped AFTER render.
- Run it yourself: `python3 scripts/validate_lut.py`

## Honest disclosures

- The eight test scenes are **simulated Apple Log 2** derived from **AI-generated
  stills** (method documented in `VALIDATION_REPORT.txt`); they are not iPhone
  sensor captures.
- **No physical iPhone, Blackmagic Camera, Resolve or Final Cut testing** was
  performed in this environment.
