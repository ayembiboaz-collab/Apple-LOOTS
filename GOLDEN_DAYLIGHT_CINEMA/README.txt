================================================================================
GOLDEN DAYLIGHT CINEMA — STANDALONE 3D LUT (33x33x33 .cube)
================================================================================

Target Camera & App : iPhone 17 Pro / 17 Pro Max — Blackmagic Camera for iOS
Input Color Space   : Apple Log 2 (Apple Log curve + Apple Wide Gamut primaries)
Output Color Space  : Rec.709 SDR, Display Gamma 2.4
LUT Format          : 33 x 33 x 33 3D .cube (DOMAIN_MIN 0..0, DOMAIN_MAX 1..1)
Delivered File      : LUT/GOLDEN_DAYLIGHT_CINEMA.cube

--------------------------------------------------------------------------------
1. WHAT THIS LUT DOES
--------------------------------------------------------------------------------
GOLDEN DAYLIGHT CINEMA is a single, standalone conversion + creative look LUT.
Do NOT stack a separate Apple Log 2 -> Rec.709 conversion LUT before or after it.

It is engineered to transform harsh midday Mediterranean/daylight footage into a
warm, dimensional, film-like grade while remaining natural on skin tones, skies,
foliage, white highlights, and genuine golden-hour scenes:
  - Decodes Apple Log 2 transfer curve & Apple Wide Gamut (D65) primaries.
  - Controls bright midday exposure without inflating already-bright highlights.
  - Separates cool skylight shadows from honey-amber sunlit midtones.
  - Preserves neutral cloud whites, white fabrics, and natural skin texture.
  - Compresses high-saturation orange/amber cleanly so golden-hour footage does
    not turn overly orange.

--------------------------------------------------------------------------------
2. HOW TO INSTALL IN BLACKMAGIC CAMERA FOR iOS (iPhone 17 Pro)
--------------------------------------------------------------------------------
Note: These steps follow Blackmagic Camera for iOS (v3.1+) documentation.
Physical iPhone hardware testing was not performed in the build environment.

Step 1 — Get the .cube file onto your iPhone:
  - Download `GOLDEN_DAYLIGHT_CINEMA.cube` directly on your iPhone (or extract
    `GOLDEN_DAYLIGHT_CINEMA.zip` in the iOS Files app by tapping the ZIP once).
  - Make sure you are importing the `.cube` file itself (970 KB), not the `.zip`.
  - If stored in iCloud Drive, tap to ensure it is downloaded locally onto
    "On My iPhone" before importing.

Step 2 — Set Blackmagic Camera to record Apple Log 2:
  1. Open Blackmagic Camera on your iPhone 17 Pro.
  2. Tap Settings (gear icon) -> Record -> Color Space.
  3. Select "Apple Log 2" (Apple ProRes or HEVC).
     (Do NOT use an Apple Log 1 clip with this LUT without a color space match,
      as Apple Log 1 uses BT.2020 rather than Apple Wide Gamut.)

Step 3 — Import & enable the Display LUT:
  1. In Blackmagic Camera, go to Settings -> LUTs.
  2. Open LUT Selection / LUT Actions and tap "Import LUT".
  3. Browse in the iOS Files picker and select `GOLDEN_DAYLIGHT_CINEMA.cube`.
  4. Select `GOLDEN_DAYLIGHT_CINEMA` from your loaded LUTs list.
  5. Enable "Display LUT" to preview the graded Rec.709 look live on screen
     while recording clean Apple Log 2 footage.
  6. Recommended: Leave "Record LUT to Clip" OFF if you want flexibility to trim
     exposure or white balance in DaVinci Resolve / Final Cut Pro later. Turn
     "Record LUT to Clip" ON only if you intentionally want the look baked in.

--------------------------------------------------------------------------------
3. USING IN DESKTOP EDITORS (OPTIONAL)
--------------------------------------------------------------------------------
  - DaVinci Resolve (Project / Node Timeline):
    Set clip input color space bypass (do not double-apply RCM/CST Apple Log 2
    conversion before the LUT), apply `GOLDEN_DAYLIGHT_CINEMA.cube` directly on
    a node, and place any exposure/WB trim nodes BEFORE the LUT node.
  - Final Cut Pro / Premiere Pro:
    Disable automatic Apple Log -> Rec.709 camera LUT override on the clip if
    enabled, then apply `GOLDEN_DAYLIGHT_CINEMA.cube` as a custom 3D LUT.

--------------------------------------------------------------------------------
4. EXPOSURE & SHOOTING TIPS
--------------------------------------------------------------------------------
  - A LUT cannot recover highlights that clipped on the iPhone sensor. Protect
    bright clouds, white linen, and midday sand with zebra warnings (~80-85%
    IRE or slightly below Apple Log 2 white clipping).
  - Lock White Balance manually before recording outdoors (e.g., ~5500K-5600K
    daylight) so auto white balance does not shift color temperature mid-shot.
================================================================================
