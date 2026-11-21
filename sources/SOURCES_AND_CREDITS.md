# Source images & credits

## The eight test scenes

All eight scene images used to develop and demonstrate **GOLDEN DAYLIGHT CINEMA**
are **AI-generated photographs** (photorealistic stills generated with Arena's
image-generation tool for this project). They are **not** photographs taken with
an iPhone and **not** captured by Blackmagic Camera.

| File | Scene | Source |
|---|---|---|
| `SCENE_01.jpg` | Harsh midday city | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_02.jpg` | Midday portrait in direct sunlight | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_03.jpg` | Mediterranean street | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_04.jpg` | Bright beach daylight | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_05.jpg` | Landscape with greenery and mountains | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_06.jpg` | Golden-hour landscape | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_07.jpg` | Modern architecture | AI-generated (Arena image generation), 2026-11-21 |
| `SCENE_08.jpg` | Travel scene with people and buildings | AI-generated (Arena image generation), 2026-11-21 |

Prompts are recorded in the project history (git log of this repository) and in
`scripts/render_iteration.py` scene titles. Native generator output is
approximately 1376–1584 px wide (see `python3 -c "from PIL import Image; ..."`).
No stock photographs or third-party copyrighted images are used, so no
third-party licensing restrictions apply to the preview renders.

## How the simulated Apple Log 2 footage is derived

For every scene, `scripts/gdc_core.py : simulate_apple_log2()` performs:

1. sRGB decode of the still to linear light (IEC 61966-2-1 EOTF).
2. The linear-light values are treated as a **scene-linear Rec.709 proxy**
   of the scene (system gamma 1.0 assumption — documented assumption, see
   `VALIDATION_REPORT.txt`).
3. 3×3 conversion Rec.709 → Apple Wide Gamut primaries (D65).
4. Encoding with the **official Apple Log 2 transfer function** (Apple Log 2
   White Paper, September 2025 — same curve as Apple Log).
5. Quantisation to **10-bit full range** (values ×1023, rounded), matching the
   container precision of Apple Log 2 ProRes recordings.

The resulting files behave exactly like Apple Log 2 / Apple Wide Gamut code
values in the [0,1] range, but the *scene content behind them* comes from an
SDR still image, not from an iPhone sensor. This limitation, and its
consequences, are described in `VALIDATION_REPORT.txt`.

## Technical references used

- Apple Inc., *Apple Log 2 White Paper*, September 2025 (Part 028-00834,
  Version 1.1) — transfer-function constants, Apple Wide Gamut chromaticities.
  (Available from Apple's developer resources; a mirrored copy was reviewed via
  the colour-science/colour issue #1428 attachment on GitHub.)
- OpenColorIO, `src/OpenColorIO/transforms/builtins/AppleCameras.cpp` and the
  built-in studio config (GitHub, AcademySoftwareFoundation/OpenColorIO) —
  independent cross-check of constants and the Apple Wide Gamut matrix.
- ITU-R BT.709-6 (Rec.709 primaries), ITU-R BT.1886 (gamma 2.4 EOTF),
  IEC 61966-2-1 (sRGB).
