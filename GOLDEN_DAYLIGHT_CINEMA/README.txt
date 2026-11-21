GOLDEN DAYLIGHT CINEMA — 3D LUT for iPhone 17 Pro (Apple Log 2)
=================================================================

OVERVIEW
--------
GOLDEN_DAYLIGHT_CINEMA.cube is a standalone 33x33x33 3D LUT designed for
iPhone 17 Pro footage recorded in Apple Log 2 (Apple Wide Gamut) using
Blackmagic Camera for iOS.

It decodes Apple Log 2, converts Apple Wide Gamut to Rec.709, applies a
cinematic Mediterranean daylight grade, and outputs Rec.709 SDR (Gamma 2.4).
Do NOT stack a separate Apple Log 2 -> Rec.709 conversion LUT in front of it.

INSTALLATION IN BLACKMAGIC CAMERA (iOS)
---------------------------------------
1. Download GOLDEN_DAYLIGHT_CINEMA.cube to your iPhone (Files app -> Downloads
   or iCloud Drive).
2. Open Blackmagic Camera on your iPhone 17 Pro.
3. Tap Settings (gear icon) -> LUTs.
4. Tap "Import LUT" and select GOLDEN_DAYLIGHT_CINEMA.cube from Files.
5. Enable "Display LUT" to preview the grade while shooting, or "Record LUT"
   only if you want the look baked into the recorded file (recommended: leave
   Record LUT OFF and shoot Apple Log 2, using Display LUT for monitoring).

CAMERA SETTINGS RECOMMENDATION
------------------------------
- Color Space: Apple Log 2 (Apple Wide Gamut)
- Codec: Apple ProRes 422 HQ / 422 or HEVC 10-bit
- Exposure: Expose for highlights (zebras at 90-95%) to preserve sky and
  sunlit stone detail.

NOTE: Physical iPhone 17 Pro / Blackmagic Camera testing was not performed
in this sandbox environment.
