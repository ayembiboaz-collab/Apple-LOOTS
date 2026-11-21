# GOLDEN DAYLIGHT CINEMA — Standalone Apple Log 2 3D LUT (iPhone 17 Pro)

A standalone **33 × 33 × 33 3D `.cube` LUT** engineered for **iPhone 17 Pro / Pro Max** footage recorded in **Apple Log 2 (Apple Wide Gamut)** using **Blackmagic Camera for iOS**, outputting **ITU-R BT.709 (Rec.709) SDR, Gamma 2.4**.

---

## Direct Downloads (iPhone Safari & Desktop)

- **Standalone `.cube` LUT (`GOLDEN_DAYLIGHT_CINEMA.cube`)**:
  - [Direct Raw Download (`GOLDEN_DAYLIGHT_CINEMA.cube`)](https://raw.githubusercontent.com/ayembiboaz-collab/Apple-LOOTS/main/GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube)
  - [GitHub Blob Page (`GOLDEN_DAYLIGHT_CINEMA.cube`)](https://github.com/ayembiboaz-collab/Apple-LOOTS/blob/main/GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube)
- **Complete Deliverable Package (`GOLDEN_DAYLIGHT_CINEMA.zip`)**:
  - [Direct ZIP Download (`GOLDEN_DAYLIGHT_CINEMA.zip`)](https://github.com/ayembiboaz-collab/Apple-LOOTS/raw/main/GOLDEN_DAYLIGHT_CINEMA.zip)
  - [GitHub Blob Page (`GOLDEN_DAYLIGHT_CINEMA.zip`)](https://github.com/ayembiboaz-collab/Apple-LOOTS/blob/main/GOLDEN_DAYLIGHT_CINEMA.zip)

---

## Deliverable Structure

```text
GOLDEN_DAYLIGHT_CINEMA/
  LUT/
    GOLDEN_DAYLIGHT_CINEMA.cube
  PREVIEWS/
    01_harsh_midday_city_BEFORE.png
    01_harsh_midday_city_AFTER.png
    02_midday_portrait_BEFORE.png
    02_midday_portrait_AFTER.png
    03_mediterranean_street_BEFORE.png
    03_mediterranean_street_AFTER.png
    04_bright_beach_daylight_BEFORE.png
    04_bright_beach_daylight_AFTER.png
    05_natural_landscape_greenery_BEFORE.png
    05_natural_landscape_greenery_AFTER.png
    06_golden_hour_landscape_BEFORE.png
    06_golden_hour_landscape_AFTER.png
    07_modern_architecture_BEFORE.png
    07_modern_architecture_AFTER.png
    08_outdoor_travel_scene_BEFORE.png
    08_outdoor_travel_scene_AFTER.png
  GALLERY/
    index.html
  CONTACT_SHEET/
    GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png
  README.txt
  VALIDATION_REPORT.txt
GOLDEN_DAYLIGHT_CINEMA.zip
```

---

## Reproducible Build Pipeline

All build, rendering, validation, and packaging scripts are included in `scripts/` alongside the master scene sources and credits in `sources/`:

```bash
PYTHONPATH=. python3 scripts/build_lut.py
PYTHONPATH=. python3 scripts/render_previews.py
PYTHONPATH=. python3 scripts/validate_lut.py
PYTHONPATH=. python3 scripts/package_project.py
```

### Disclosures
- **Simulated Apple Log 2 Test Scenes**: Because native ungraded iPhone 17 Pro sensor captures were not bundled in this build environment, the 8 `BEFORE` preview images are documented **Simulated Apple Log 2 / Apple Wide Gamut** encodings derived mathematically from credited real photographs (see `sources/CREDITS_AND_SOURCES.json` and `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt`). Every `AFTER` image was generated strictly by applying `GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube` via 3D trilinear interpolation to the corresponding `BEFORE` PNG.
- **Hardware Testing**: Physical iPhone 17 Pro / Blackmagic Camera on-device testing was not performed in this Linux sandbox environment.
