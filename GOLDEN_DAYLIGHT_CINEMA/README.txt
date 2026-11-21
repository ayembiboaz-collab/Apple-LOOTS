GOLDEN DAYLIGHT CINEMA
=====================
A standalone cinematic LUT for iPhone 17 Pro / iPhone 17 Pro Max footage
recorded in Apple Log 2 with the Blackmagic Camera app.

    Apple Log 2 · Apple Wide Gamut  ->  Rec.709 SDR · gamma 2.4
    Format: single 33 x 33 x 33 3D LUT (.cube) — standalone
    Look:   warm Mediterranean travel-film grade. Honey sunlight, rich
            midtones, deep-but-detailed shadows, azure skies, warm greens,
            believable skin, warm stone and concrete.


CONTENTS
--------
GOLDEN_DAYLIGHT_CINEMA/
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube    The LUT (only file you need)
  PREVIEWS/                          8 BEFORE + 8 AFTER PNGs (2048px class)
  GALLERY/index.html                 Interactive before/after gallery
  CONTACT_SHEET/                     Contact sheet PNG (all 8 AFTER renders)
  README.txt                         This file
  VALIDATION_REPORT.txt              Sources, tests, results, limitations
  SOURCES.md                         Image credits for the preview plates

The repository also contains tools/ (Python build & validation scripts and
source images). Image credits live in SOURCES.md in this folder.


QUICK START — BLACKMAGIC CAMERA ON iPHONE
------------------------------------------
1. Get GOLDEN_DAYLIGHT_CINEMA.cube onto your iPhone:
   a. Tap the LUT file in Safari/Files and "Save to Files" (or AirDrop it,
      or download it from the GitHub links in the release/PR, or unzip the
      project ZIP on the phone and copy the .cube out).
   b. Place it in:  On My iPhone  ->  Blackmagic Camera  ->  LUTs
      (Files app -> Browse -> On My iPhone -> Blackmagic Camera -> LUTs,
       then move/copy the .cube there).
   Alternative: inside the Blackmagic Camera app, use the app's
   LUT import option (Settings -> LUTs) and browse to the .cube file —
   iCloud Drive works too.

2. In the Blackmagic Camera app:
   - Record:  codec ProRes (422 LT or higher) or HEVC, 4K recommended,
     colour space = Apple Log 2 (HDR), Full Range / Video as applicable.
     Keep ISO at/below native 400 where possible for highlight headroom.
   - Monitoring: Settings -> LUTs -> select GOLDEN_DAYLIGHT_CINEMA.
     Toggle the Display/Monitoring LUT ON to preview the grade while
     shooting. The recording itself stays untouched Apple Log 2.
   - Colour space tag for the monitoring path: Rec.709.

3. Shooting habits that flatter this LUT:
   - Expose for the highlights. This LUT preserves texture where the sensor
     captured it; it cannot invent it where the sensor clipped.
   - Keep white balance near neutral daylight (e.g. 5600K) to let the grade
     provide the warmth; avoid already-warm WB stacked on the LUT.
   - Midday: do not add exposure compensation "for safety"; the LUT is built
     to hold bright scenes without lifting them.

4. IMPORTANT:
   - The LUT affects the preview/monitor path. Leave "bake in" OFF unless
     you explicitly want the grade printed into the file
     (e.g. "Apply LUT to Output/Recording"). Best practice: record clean
     Apple Log 2, keep full latitude, grade in post.
   - Do NOT stack this with another Apple Log -> Rec.709 conversion before
     it. This LUT already contains the complete conversion. A neutral or
     conversion LUT in front of it will double-transform the image.


GRADING IN POST (DaVinci Resolve, Final Cut Pro, Premiere)
-----------------------------------------------------------
1. Import GOLDEN_DAYLIGHT_CINEMA.cube into your LUT folder:
   - Resolve: place the .cube in Resolve's LUT directory or point the app
     at it (Project Settings -> Color Management -> 3D LUT path), then
     "Refresh LUTs". Apply on the FIRST node from Apple Log 2 footage.
   - Final Cut Pro: copy the .cube into
     ~/Library/Application Support/ProApps/MIOCustomLUT/
     then use Effects -> LUT Utility -> Custom LUT.
   - Premiere: copy into the .cube LUT folder for CUBE files, refresh,
     apply as an Input LUT (preferred) or a creative LUT on an adjustment
     layer.
2. Keep the timeline / colour management neutral (DaVinci Wide Gamut or
   project Rec.709 with the Input LUT doing the work — not both).
3. Optional: node tree for fine-tuning (exposure -> WB -> this LUT ->
   trim), but the LUT is designed to stand alone.


EXPECTED CHARACTER
-------------------
- Harsh midday: richer azure sky, warm stone, dimensional shade, no
  yellow-everything wash, bright scenes NOT brightened further.
- Golden hour: still golden — the LUT adds shape, not extra heat.
- Skin: natural on most complexions; if you want more/less warmth on your
  specific subject, trim with WB after the LUT (not before).
- Seas/pools can lean a touch teal by nature; if you want less, reduce
  blue saturation slightly after the LUT — the LUT itself aims to keep
  cyans natural, not turquoise.


WHAT THIS LUT IS NOT / HONEST LIMITS
-------------------------------------
- It cannot recover clipped highlights (sensor-level problem; nothing can).
- It is NOT a camera match LUT and was NOT shot on a physical iPhone for
  this release. Previews are documented simulated Apple Log 2 derived from
  credited sources; the gamut math is verified against OpenColorIO 2.6
  builtins (see VALIDATION_REPORT.txt).
- Output is Rec.709 SDR gamma 2.4. Not for HDR, P3, HLG, PQ or print.
- Apple Log 2 decoding constants are from Apple's white papers (via
  OpenColorIO's AppleCameras.cpp, which cites the Apple Log 2 white paper).
  Genuine iPhone 17 Pro camera-side rendering into Apple Log 2/AWG may
  differ slightly at the margins; verify on your own footage.
- 33^3 trilinear interpolation is excellent over most of the cube; the far
  out-of-gamut neon corner (Y<0, impossible on Rec.709 displays) is
  intentionally steep — see VALIDATION_REPORT.txt section F.


FILE VERIFICATION
-----------------
GOLDEN_DAYLIGHT_CINEMA.cube
  Size:    ~0.97 MB
  Nodes:   35,937 (33^3), DOMAIN_MIN 0 0 0, DOMAIN_MAX 1 1 1
  SHA-256: see VALIDATION_REPORT.txt (appended at release time)


LICENCE
-------
The LUT itself (.cube), the GALLERY page, contact sheet and text files are
provided for use and modification for any purpose, commercial or not,
no warranty. Preview photographs remain the property of their respective
authors/license-holders — see SOURCES.md.
