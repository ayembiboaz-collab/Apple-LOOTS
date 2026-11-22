GOLDEN DAYLIGHT CINEMA — FLAGSHIP EDITION
========================================
Standalone 33x33x33 3D LUT for iPhone 17 Pro
Input:  Apple Log 2 (Apple Wide Gamut)
Output: Rec.709 SDR, Gamma 2.4

1. INSTALLATION IN BLACKMAGIC CAMERA (iOS)
- Transfer GOLDEN_DAYLIGHT_CINEMA.cube to your iPhone (Files app / AirDrop / iCloud Drive).
- Open Blackmagic Camera -> Settings -> LUTs -> Import LUT -> select GOLDEN_DAYLIGHT_CINEMA.cube.
- Set Recording Color Space to Apple Log 2.
- Enable Display LUT for live monitoring (leave "Record LUT to Clip" OFF if you want to keep raw Apple Log 2 for post-production).

2. RECOMMENDED EXPOSURE
- Expose for highlights (ETTR-friendly, ~0 to +0.5 EV) so sky and sunlit surfaces retain texture.
- Works on harsh midday sunlight as well as real golden-hour footage without excessive warmth.

3. LIMITATIONS
- A 3D LUT is a fixed per-pixel colour transform: it cannot add film grain, halation, bloom, sharpening, noise reduction, depth-aware edits, or recover clipped highlights.
- Tested in software with simulated Apple Log 2 derived from real-world photographs; no physical iPhone 17 Pro / Blackmagic Camera device test was performed.
