===========================================================================
  GOLDEN DAYLIGHT CINEMA
  Warm, rich, atmospheric Mediterranean travel & lifestyle look
  Apple Log 2 -> Rec.709 gamma 2.4  |  33 x 33 x 33 3D .cube LUT
===========================================================================

CONTENTS
---------
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube   Standalone 3D LUT (33^3), input = Apple Log 2
                                   encoder (0..1), output = Rec.709 gamma 2.4.
                                   No other LUT or conversion file required.
  PREVIEWS/                        BEFORE (neutral reference) and AFTER (the
                                   shipped .cube via independent parser) PNGs
                                   for 8 scenes, plus side-by-side comparisons.
  GALLERY/index.html               Picture-perfect dark premium site: sliders,
                                   fullscreen, contact sheet, credits, .cube link.
  CONTACT_SHEET/contact_sheet.png  All 8 scenes, BEFORE | AFTER.
  VALIDATION_REPORT.txt            Every check with measured numbers and SHA256
                                   checksums of every file.
  SOURCES.txt                      Per-image photographer, URL, licence, and
                                   modifications (see SIMULATION NOTE).

HOW TO USE (Blackmagic Camera for iOS / iPhone 17 Pro)
----------------------------------------------------
  1. Read VALIDATION_REPORT.txt and SOURCES.txt in this folder.
  2. Copy GOLDEN_DAYLIGHT_CINEMA.cube to the camera (iOS Files app, Copy to
     Camera, etc.).  Sources and file transfer were NOT tested on the physical
     device — see SIMULATION NOTE.
  3. In Blackmagic Camera, open Settings > LUTs > LUTs Manager.  Import from
     Files.  Assign the new LUT under the recording profile / look you will be
     shooting.
  4. The .cube consumes Apple Log 2 encoded (0..1) input directly.  It does NOT
     contain any sRGB-to-Log 2 conversion, so it is NOT a standard video LUT
     that takes Rec.709 input — it must be applied to Apple Log 2 recordings.
  5. Choose the .cube for preview, then burn-in if you want it baked into the
     file.
  6. Monitor or export in Rec.709 gamma 2.4.

WHAT THIS LOOKS LIKE
--------------------
Warm Mediterranean / coastal travel cinematic: saturated amber sand and stone,
natural blue skies (protected), unaltered greens, modest high-light roll,
cool shadows.  Skin tones are protected from warm-cast shifts toward orange,
chroma is capped softly above 0.135 in the skin range.  Golden at the top,
clean at the bottom.

SIMULATION NOTE (read before using)
----------------------------------
No physical iPhone 17 Pro footage or Blackmagic Camera validation was performed
for this deliverable.  Every preview was generated from real photographs run
through a transparent Apple Log 2 *simulation* (sRGB -> linear Rec.709 -> XYZ ->
linear Apple Wide Gamut -> sensor-like noise -> Apple Log 2 OETF -> 8-bit).  The
simulated images are labelled as such and MUST NOT be presented as genuine
iPhone footage.  Behaviour with real Apple Log 2 footage is not guaranteed.

Validated pipeline (see VALIDATION_REPORT.txt)
---------------------------------------------
  - .cube integrity (33^3, 0..1, finite, anchors correct)
  - Trilinear + tetrahedral interpolation error vs analytic pipeline
  - Neutral-axis warmth (no orange cast)
  - Monotonicity + smoothness (diagonal)
  - 8-bit / 10-bit quantisation
  - Clipping percent BEFORE vs AFTER (all 8 scenes, aggregate)
  - Shadow noise gain
  - +/-4 stops exposure ladder
  - Skin-line check (OKLab h 0.15..1.00)
  - Sky/foliage hue histograms (before/after)
  - Synthetic charts (grey ramp, hue sweep, saturation sweep,
    ColorChecker-style patches, exposure ladder, skin line)

LIMITATIONS / DISCLAIMERS
-----------------------
- Real-world product validation is not performed here (no physical camera):
  this is a digital, open, reproducible grade.  Results with live footage may
  vary with the camera, lighting, and processing order.
- The .cube consumes Apple Log 2 encoded (0..1) input.  Neutral reference
  renders (BEFORE) use the verified Apple Log 2 reference transform from
  Apple's Apple Log 2 White Paper; AFTER images use the shipped .cube.
- The .cube was baked at 33^3 points; small interpolation error is reported.

DEEP DIVE
---------
  build/pipeline.py      analytic grade (single source of truth)
  build/color_science.py Apple Log 2 constants, AWG matrices, OKLab
  build/bake_lut.py      analytic bake of the .cube
  build/render_previews.py independent .cube parser + BEFORE/AFTER previews
  build/simulate_log.py  Apple Log 2 simulation from real photographs
  build/validate_lut.py  full validation suite
  build/charts.py        synthetic charts
  build/build_gallery.py / build_contact_sheet.py / build_zip.py

See BUILD.md for full build/render/validate/test instructions.
