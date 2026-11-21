================================================================================
 GOLDEN DAYLIGHT CINEMA
 A standalone cinematic LUT for Apple Log 2 (Apple Wide Gamut) footage
================================================================================

WHAT THIS IS
------------
One 33 x 33 x 33 3D LUT (.cube) that turns harsh midday iPhone footage into a
warm, rich, dimensional, luxury-travel-film look:

  Input  : Apple Log 2, Apple Wide Gamut, D65, full range [0,1]
           (as recorded by iPhone 17 Pro / iPhone 17 Pro Max, e.g. with the
           Blackmagic Camera app or the Camera app's ProRes Log 2 encoding)
  Output : Rec.709 SDR, gamma 2.4 (display-referred)

The LUT is STANDALONE. It decodes Apple Log 2, converts Apple Wide Gamut to
Rec.709, applies the GOLDEN DAYLIGHT CINEMA grade, and encodes gamma 2.4 in a
single file. Do NOT stack it on top of another Log-to-Rec.709 conversion LUT,
and do not use it on already-graded or Rec.709 footage.

It is NOT for original "Apple Log" (iPhone 15/16 Pro era) footage - that uses
different primaries (BT.2020). Using this LUT on Apple Log (v1) files will
produce incorrect colour.

THE LOOK
--------
- Golden sunlight: honey/amber warmth in sunlit midtones; whites stay
  believable, no overall yellow cast.
- Filmic contrast: rich midtones, deep but detailed shadows, smooth highlight
  roll-off. Already-bright footage is never made brighter.
- Skies: richer, slightly deeper natural blue with controlled cyan; cloud
  whites stay clean.
- Greenery: natural, slightly warm greens with controlled saturation - never
  radioactive or teal.
- Skin: natural and subtly warm across lighting; sunlit skin rolls off creamy
  rather than clipping. No beauty-filter effects (it is a colour LUT only).
- A very slight cool shift in the deepest desaturated shadows gives
  sun/shade separation and dimensionality.

INSTALLATION - BLACKMAGIC CAMERA ON iPHONE
------------------------------------------
NOTE: these instructions follow Blackmagic Camera for iOS's documented LUT
support (custom .cube LUTs can be imported and used as view/burn-in LUTs).
This workflow was NOT tested on a physical iPhone in this project - see
VALIDATION_REPORT.txt for exactly what was and was not tested.

1. Copy GOLDEN_DAYLIGHT_CINEMA.cube to your iPhone (AirDrop, iCloud Drive or
   the Files app). Keep the .cube filename unchanged.
2. Open Blackmagic Camera and tap the settings (gear) button.
3. Go to LUTs (under Monitoring / Color section).
4. Choose "Import LUT" / the + button and pick
   GOLDEN_DAYLIGHT_CINEMA.cube from Files.
5. Select the imported LUT to preview it while recording.
6. Record in Apple Log 2:
     Settings > Formats & Capture > enable Apple Log, then set
     "ProRes Log Video Encoding" (iOS Settings > Camera > Formats) to Log 2
     where available, and shoot ProRes.
   IMPORTANT: apply the LUT for MONITORING only (view LUT). Keep the recorded
   files in Apple Log 2 so you keep full latitude for the final grade.
7. In the edit, apply the same .cube to the Log 2 clips for the final render
   (see below), or burn it in if you prefer straight-out-of-camera files.

Because the LUT is standalone, monitoring with it in Blackmagic Camera shows
you the final look while the recording stays log.

POST-PRODUCTION USE
-------------------
- DaVinci Resolve: clip > Color page > first node of each clip, right-click
  the node > 3D LUT > "Select LUT File..." (or copy the .cube to
  ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT and
  reload). Resolve's tetrahedral interpolation matches the method used to
  produce the preview images in this package.
- Final Cut Pro: Effects > Color > Camera LUT > "Choose Custom LUT" and select
  the .cube (place it in ~/Movies/Custom LUTs, then restart FCP to pick it up).
- Do not add an additional Camera LUT / colour space conversion before it.

RECOMMENDED SHOOTING SETTINGS
-----------------------------
- Apple Log 2 (not Log), ProRes, 10-bit.
- Expose so highlights you care about are not clipped in-camera (log records
  up to ~1200% reflectance at 100% signal, but clipped is clipped forever).
- White balance as normal (the look is designed to sit on correctly
  white-balanced Log 2 footage).

PACKAGE CONTENTS
----------------
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube            the LUT (the only required file)
  PREVIEWS/SCENE_01..08_BEFORE.png           neutral conversion of each scene
  PREVIEWS/SCENE_01..08_AFTER.png            the delivered LUT applied
  GALLERY/index.html                         preview gallery (open in Safari)
  CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png
  CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_EXPOSURE_SWEEP.png
  README.txt                                 this file
  VALIDATION_REPORT.txt                      sources, tests, results, limits

KNOWN LIMITATIONS (short version - see VALIDATION_REPORT.txt)
-------------------------------------------------------------
- A LUT cannot recover highlights that were clipped in-camera.
- The test footage is SIMULATED Apple Log 2 derived from AI-generated stills,
  not real iPhone 17 Pro sensor captures.
- No physical iPhone / Blackmagic Camera testing was performed.
- 33^3 grids slightly smooth the steep log toe; sensor black renders at a
  designed film floor of ~9/255 rather than absolute 0.
