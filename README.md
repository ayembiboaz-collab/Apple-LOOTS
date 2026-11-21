# Apple LOOTS — GOLDEN DAYLIGHT CINEMA

A premium, standalone 3D LUT for **Apple Log 2 / Apple Wide Gamut** footage
recorded on **iPhone 17 Pro** with **Blackmagic Camera for iOS**, graded to
**Rec.709 SDR, gamma 2.4**.

Deliverables live in `GOLDEN_DAYLIGHT_CINEMA/`:

| Path | What it is |
|---|---|
| `GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube` | the LUT (33×33×33) |
| `GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/` | eight BEFORE / AFTER PNG pairs |
| `GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html` | interactive preview gallery |
| `GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/` | visual overview |
| `GOLDEN_DAYLIGHT_CINEMA/README.txt` | installation and usage |
| `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt` | sources, tests, results, limits |
| `GOLDEN_DAYLIGHT_CINEMA.zip` | the complete package |

`dev/` contains the build and validation scripts that reproduce every artefact
(the LUT, the renders, the gallery, the contact sheet and the ZIP).

## Honest scope

* The eight scene sources are **AI-generated reference photographs**, not
  iPhone footage. They are converted into **simulated Apple Log 2** plates with
  the published Apple Log 2 transfer function and Apple Wide Gamut primaries.
  This is documented in `SCENES/prompts.txt` and in the validation report.
* No physical iPhone or Blackmagic Camera for iOS device test was performed.
* The LUT cannot recover clipped sensor highlights.
