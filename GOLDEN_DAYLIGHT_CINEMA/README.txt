================================================================================
GOLDEN DAYLIGHT CINEMA  —  Installation & Usage (Blackmagic Camera on iPhone)
================================================================================

WHAT THIS IS
------------
GOLDEN_DAYLIGHT_CINEMA.cube is a single, standalone 33 x 33 x 33 cinematic 3D LUT
for iPhone 17 Pro footage recorded in Apple Log 2 / Apple Wide Gamut with
Blackmagic Camera for iOS.

It does the full pipeline in one LUT:
  1. Decodes the Apple Log 2 transfer function.
  2. Converts Apple Wide Gamut to Rec.709.
  3. Applies the GOLDEN DAYLIGHT CINEMA creative grade (warm, rich, atmospheric
     daylight look).
  4. Outputs Rec.709 SDR, gamma 2.4.

You do NOT need a separate Apple Log 2 -> Rec.709 conversion LUT. Apply this one
LUT to Apple Log 2 footage and you get the graded Rec.709 result.

REQUIREMENTS
------------
- iPhone 17 Pro or iPhone 17 Pro Max (Apple Log 2 requires iPhone 17 Pro or later).
- Blackmagic Camera for iOS, version 3.1 or later (Apple Log 2 support began in
  3.1, Sep 2025).
- Footage recorded in Apple Log 2 (ProRes Log or HEVC Log) in Apple Wide Gamut.
- The GOLDEN_DAYLIGHT_CINEMA.cube file.

BEFORE YOU START — RECORD IN APPLE LOG 2
----------------------------------------
The LUT only works correctly on Apple Log 2 footage. In Blackmagic Camera:

  1. Open Blackmagic Camera.
  2. Open the recording / format settings (gear icon).
  3. Set the colour / log recording option to "Apple Log 2" (ProRes Log or HEVC
     Log). Confirm the gamut is Apple Wide Gamut.
  4. Frame and expose for the log curve (protect highlights; log keeps detail in
     bright skies and speculars).
  5. Record.

(Exact menu names vary slightly between Blackmagic Camera versions; use the
Apple Log 2 / Log option in the recording settings.)

INSTALLING THE LUT
------------------
  1. Get the .cube onto your iPhone:
       - Download GOLDEN_DAYLIGHT_CINEMA.cube (see the GitHub link), then open it
         in the Files app; or
       - AirDrop / transfer the .cube file to your iPhone.
  2. In Blackmagic Camera, open the project / clip you recorded in Apple Log 2.
  3. Open the colour / LUT settings and choose the custom 3D LUT / import LUT
     option.
  4. Select GOLDEN_DAYLIGHT_CINEMA.cube from the Files app.
  5. The LUT is now available; enable it on the clip.

(The LUT is a standard .cube 3D LUT. If Blackmagic Camera offers a LUT strength
or mix control, start at 100%. The look is intentionally noticeable but realistic.)

APPLYING IT CORRECTLY
---------------------
- Apply the LUT to Apple Log 2 footage only. Do NOT apply it to already-converted
  Rec.709 footage (that would double-convert and wash out the image).
- If your project/timeline is already set to Rec.709 and Blackmagic Camera is
  auto-converting the Apple Log 2 clip, you may get a double conversion. In that
  case, either let the app convert and apply the LUT as a creative look only, or
  disable the automatic conversion so this LUT performs the full decode+grade.
- Exposure: the grade preserves the log exposure. If it looks too dark or too
  bright, adjust the clip exposure/gain, not the LUT strength.

VERIFICATION
------------
After applying, check:
- Midday footage looks warm, rich and dimensional, not yellow or orange.
- Whites (clouds, bright walls) stay believable, not yellow.
- Skies are a natural, controlled blue (not turquoise, not artificially dark).
- Skin is naturally, subtly warm (not orange/red).
- Foliage is natural, slightly warm green (not yellow-green, not teal).
- Highlights roll off smoothly (no harsh digital clipping).

TROUBLESHOOTING
---------------
- Looks washed out / low contrast: you are likely double-converting (the app is
  already converting Apple Log 2 to Rec.709 and then the LUT converts again).
  Disable the automatic conversion so this LUT does the full job.
- Looks too orange/yellow: reduce the LUT mix/strength slightly, or check you are
  not also applying another warm look on top.
- Looks too dark: raise clip exposure/gain; the LUT does not brighten midday
  footage by design.
- LUT not accepted: confirm the file is the unmodified .cube and that
  Blackmagic Camera supports 33-point 3D .cube LUTs (it does).

COMPATIBILITY
-------------
- Blackmagic Camera for iOS 3.1+ (Apple Log 2).
- Also works in DaVinci Resolve, Final Cut Pro, Premiere Pro and other
  LUT-capable tools set to Apple Log 2 input / Rec.709 gamma 2.4 output.

IMPORTANT NOTE ON THE PREVIEWS
------------------------------
The before/after preview images in this package were rendered from SIMULATED
Apple Log 2 (no iPhone 17 Pro sensor footage was available when the LUT was
built). The simulation encodes a Rec.709 reference image into the documented
Apple Log 2 curve and Apple Wide Gamut, then the delivered .cube is applied.
See VALIDATION_REPORT.txt for the full method, tests and limitations.

FILES
-----
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube      the LUT (the deliverable)
  PREVIEWS/                            eight BEFORE and eight AFTER PNGs
  GALLERY/index.html                   interactive before/after gallery
  CONTACT_SHEET/contact_sheet.png      visual overview
  README.txt                           this file
  VALIDATION_REPORT.txt                sources, tests, results, limitations
  SOURCES/                             reference scenes + technical notes
  scripts/                             build & validation scripts
================================================================================
