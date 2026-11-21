================================================================================
GOLDEN DAYLIGHT CINEMA — STANDALONE 3D LUT FOR APPLE LOG 2 (iPHONE 17 PRO)
================================================================================

File Name          : GOLDEN_DAYLIGHT_CINEMA.cube
LUT Format         : 33 x 33 x 33 3D LUT (.cube, 35,937 lattice points)
Input Color Space  : Apple Log 2 / Apple Wide Gamut (CIE D65)
Output Color Space : ITU-R BT.709 (Rec.709) SDR, Gamma 2.4
Target Camera App  : Blackmagic Camera for iOS (iPhone 17 Pro / iPhone 17 Pro Max)

--------------------------------------------------------------------------------
1. OVERVIEW & CREATIVE INTENT
--------------------------------------------------------------------------------
GOLDEN DAYLIGHT CINEMA is a standalone, single-step technical + creative 3D LUT
engineered specifically for iPhone 17 Pro / Pro Max footage recorded in Apple Log 2
(Apple Wide Gamut).

It transforms harsh midday sunlight into a warm, rich, atmospheric, dimensional
cinema image inspired by luxury Mediterranean travel films and high-end lifestyle
commercials—without requiring a separate technical conversion LUT beforehand.

Key Visual Characteristics:
  * Golden Sunlight: Infuses sunlit stone, pavement, sand, and midtones with
    subtle honey-amber warmth while keeping cloud whites and speculars clean
    and believable (no overall yellow cast).
  * Authoritative Contrast & Midday Control: Does not make already-bright midday
    footage brighter. Anchors 18% middle gray with rich cinema density, carves
    clear separation between sun and open shade, maintains detailed shadows
    without crushed blacks, and rolls off highlights smoothly up to 1200%
    scene reflectance.
  * Natural Mediterranean Skies: Rotates greenish/turquoise midday skies toward
    true azure-cobalt blue while preserving natural cloud whites and avoiding
    artificially dark skies.
  * Grounded Botanical Greenery: Tames radioactive digital yellow-greens into
    natural, slightly warm olive/botanical greens with controlled saturation
    and subtractive filmic density (never teal).
  * Natural Skin Tones: Subtly warm, golden-peach skin reproduction across
    direct sun and open shade with a soft saturation ceiling that prevents
    orange, red, or yellow skin. Preserves 100% of natural skin texture.
  * Golden-Hour Versatility: Self-limiting warm chroma protection ensures that
    footage shot during actual golden hour retains velvety warmth without
    overheating or clipping warm channels.

--------------------------------------------------------------------------------
2. HOW TO DOWNLOAD & INSTALL ON iPHONE (BLACKMAGIC CAMERA FOR iOS)
--------------------------------------------------------------------------------
STEP 1 — Save the .cube File to the iPhone Files App:
  1. Download `GOLDEN_DAYLIGHT_CINEMA.cube` (or `GOLDEN_DAYLIGHT_CINEMA.zip`)
     using the direct GitHub links provided in the project delivery.
  2. When prompted in Safari on iPhone, tap "Download", then open the Downloads
     menu (blue arrow icon in the address bar) -> tap the file -> Save to Files
     (e.g., inside "On My iPhone" -> "Blackmagic Camera" -> "LUTs" or "Downloads").
  3. If you downloaded `GOLDEN_DAYLIGHT_CINEMA.zip`, tap the ZIP file inside the
     iPhone Files app to extract the `GOLDEN_DAYLIGHT_CINEMA/` folder automatically;
     the LUT is inside `GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube`.

STEP 2 — Configure Blackmagic Camera for Apple Log 2:
  1. Open Blackmagic Camera on your iPhone 17 Pro or iPhone 17 Pro Max.
  2. Tap the "Settings" gear icon (bottom-right).
  3. Go to "Camera" or "Codec":
     - Codec: Apple ProRes 422 HQ / 422 / 422 LT, or HEVC (H.265) 10-bit.
     - Color Space: Select "Apple Log 2 - HDR" (or "Apple Log 2").
       *Important*: Do NOT select Rec.709 or original Apple Log (Rec.2020) when
       using this LUT, as this LUT decodes Apple Wide Gamut directly.

STEP 3 — Import and Enable GOLDEN_DAYLIGHT_CINEMA.cube:
  1. In Blackmagic Camera Settings, tap "LUTs".
  2. Tap "LUTs Manager" -> tap "+" (Import LUT).
  3. Browse to `GOLDEN_DAYLIGHT_CINEMA.cube` in the iPhone Files app and select it.
  4. Tap the imported `GOLDEN_DAYLIGHT_CINEMA` entry to make it active (checkmark).
  5. Return to the main LUT settings screen and choose your workflow mode:
     - RECOMMENDED (Post-Production Grading Workflow):
       * Turn ON "Display LUT"
       * Turn OFF "Record LUT to Clip"
       This previews the Golden Daylight Cinema grade live on your iPhone screen
       for accurate exposure and framing while recording the full-dynamic-range
       Apple Log 2 signal to the movie file.
     - QUICK TURNAROUND (Direct-to-Social / Baked-In Workflow):
       * Turn ON "Record LUT to Clip"
       This bakes the Rec.709 Gamma 2.4 grade directly into the recorded video
       (the LUT badge on the HUD will outline in red).

--------------------------------------------------------------------------------
3. RECOMMENDED EXPOSURE SETTINGS FOR HARSH MIDDAY SUNLIGHT
--------------------------------------------------------------------------------
  * Important Limitation: A 3D LUT cannot recover highlights that have already
    clipped at the camera sensor (10-bit code value 1023 / P = 1.0).
  * Shutter Angle / Speed: Use a 180-degree shutter rule (e.g., 1/48s or 1/50s
    for 24fps/25fps) paired with a variable or fixed Neutral Density (ND) filter
    (ND8 to ND64 in direct midday sun).
  * ISO: In bright daylight on iPhone 17 Pro, keep ISO at or below native ISO 400
    (or ISO 50–250 without an ND filter) so bright clouds, white walls, and
    sunlit skin highlights retain full sensor headroom.
  * White Balance: Lock manual White Balance around 5400K–5600K for outdoor
    daylight consistency (avoid Auto White Balance shifting mid-shot).
  * Zebra / Histogram: Set Zebra to 95%–100% with LUT preview OFF (or monitor
    the Apple Log 2 waveform) to ensure bright clouds and sunlit stone remain
    below hard sensor clipping.

--------------------------------------------------------------------------------
4. DESKTOP POST-PRODUCTION USAGE (RESOLVE / FINAL CUT PRO / PREMIERE PRO)
--------------------------------------------------------------------------------
Because `GOLDEN_DAYLIGHT_CINEMA.cube` is a standalone LUT (Apple Log 2 / Apple
Wide Gamut -> Rec.709 Gamma 2.4):
  * DaVinci Resolve: In an unmanaged Rec.709 Gamma 2.4 timeline, disable automatic
    Color Space Transform on the clip and apply `GOLDEN_DAYLIGHT_CINEMA.cube` on
    your final LUT node (place exposure/offset and white-balance trim nodes BEFORE
    the LUT node so adjustments happen in Apple Log 2 space).
  * Final Cut Pro: Select the clip -> Inspector -> Info (Extended/Settings view)
    -> set "Camera LUT" to "None", then apply a Custom LUT effect with
    `GOLDEN_DAYLIGHT_CINEMA.cube` (Input: 100%, Output: Rec.709).
  * Adobe Premiere Pro: In Lumetri Color -> Input LUT (or Creative LUT with
    auto-tonemapping disabled in Sequence Settings), load
    `GOLDEN_DAYLIGHT_CINEMA.cube`.

--------------------------------------------------------------------------------
5. PACKAGE CONTENTS & SIMULATION / TESTING DISCLOSURE
--------------------------------------------------------------------------------
  GOLDEN_DAYLIGHT_CINEMA/
    LUT/
      GOLDEN_DAYLIGHT_CINEMA.cube            (Standalone 33x33x33 3D LUT)
    PREVIEWS/
      01_harsh_midday_city_BEFORE.png        (Simulated Apple Log 2 Input, 1920x1080)
      01_harsh_midday_city_AFTER.png         (Actual .cube Output, 1920x1080)
      ... (all 8 BEFORE and 8 AFTER high-resolution PNG pairs)
    GALLERY/
      index.html                             (Touch-friendly iPhone Safari Gallery)
    CONTACT_SHEET/
      GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png (Visual Master Overview & Telemetry)
    README.txt                               (This guide)
    VALIDATION_REPORT.txt                    (Full mathematical & visual audit)

Disclosure:
  * The 8 BEFORE preview images are documented Simulated Apple Log 2 / Apple Wide
    Gamut encodings derived mathematically from credited real photographs (Unsplash
    and V-Flat World; see `VALIDATION_REPORT.txt` and `sources/CREDITS_AND_SOURCES.json`).
    They are not claimed to be physical iPhone 17 Pro sensor captures.
  * Every AFTER image was rendered strictly by applying `GOLDEN_DAYLIGHT_CINEMA.cube`
    via 3D trilinear interpolation to the corresponding BEFORE PNG.
  * Physical iPhone / Blackmagic Camera on-device testing was not performed in
    this Linux build environment.
================================================================================
