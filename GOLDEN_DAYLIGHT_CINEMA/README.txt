================================================================================
GOLDEN DAYLIGHT CINEMA
A standalone cinematic LUT for Apple Log 2 / Apple Wide Gamut
Output: Rec.709 SDR, gamma 2.4  ·  Format: 33 x 33 x 33 .cube
================================================================================

WHAT THIS IS
------------
GOLDEN DAYLIGHT_CINEMA.cube is a single, self-contained 3D LUT that takes
Apple Log 2 footage (Apple Wide Gamut) and turns it into a warm, rich,
atmospheric, dimensional cinematic look — like a luxury Mediterranean travel
film or high-end lifestyle commercial.

It does everything in one file:
  1. Decodes Apple Log 2 (Apple's published log transfer function).
  2. Converts Apple Wide Gamut to Rec.709 (white-preserving primaries matrix).
  3. Applies the creative grade (filmic tone curve, hue-aware honey/amber
     split toning, luminance-weighted saturation).
  4. Outputs Rec.709 SDR at gamma 2.4.

No separate conversion LUT is needed, and the LUT does NOT assume the footage
is already Rec.709. Just load it and the look is applied.

The look is noticeable but realistic and versatile: honey/amber warmth in
sunlit midtones with believable whites (no yellow/orange cast), rich detailed
shadows, smooth highlight roll-off, natural blue skies, natural warm greens,
and natural subtly-warm skin. It also works on golden-hour footage without
excessive warmth.


REQUIREMENTS
------------
- iPhone 17 Pro or iPhone 17 Pro Max (Apple Log 2 requires iPhone 17 Pro or
  later) shooting in Apple Log 2.
- Blackmagic Camera for iOS (supports .cube LUTs; Apple Log 2 supported from
  Blackmagic Camera 3.1+).
- Shoot in Apple Log 2 / Apple Wide Gamut (ProRes or HEVC).


INSTALLING THE LUT IN BLACKMAGIC CAMERA (iOS)
--------------------------------------------
Method A — Files app (simplest)
  1. Download GOLDEN_DAYLIGHT_CINEMA.cube to your iPhone (AirDrop, iCloud, or
     from the GitHub link / this ZIP).
  2. Open the Files app, find the .cube file.
  3. Tap "Share" → "Save to Files" if needed, then move/copy it to:
         On My iPhone  >  Blackmagic Camera  >  LUTs
     (Create the Blackmagic Camera/LUTs folder if it does not exist.)
  4. Open Blackmagic Camera. The LUT should appear in its LUT list.

Method B — LUT Import
  1. Open Blackmagic Camera → Settings → LUTs (or LUT Import).
  2. Import / browse to the .cube file (from Files, iCloud Drive, etc.).
  3. The LUT is now available in the LUT list.

If the LUT does not appear, confirm the file is a plain .cube (not renamed
.txt), is inside the Blackmagic Camera/LUTs folder, and that Blackmagic
Camera is up to date.


USING THE LUT
-------------
  1. In Blackmagic Camera, set your recording format to Apple Log 2 (ProRes
     or HEVC) so the camera records clean, un-graded log.
  2. Open the LUT list and select GOLDEN DAYLIGHT CINEMA.
  3. Choose how to apply it:
       - Preview only ("Apply LUT to Output"): the monitor shows the graded
         look while the file still records clean Apple Log 2. Recommended —
         you keep full dynamic range for post.
       - Burn-in ("Apply LUT to Recording"): the grade is baked into the
         recorded file. Use only if you want a one-pass, no-post workflow.
  4. Expose for your subject (not the sky). The LUT enriches and rolls off
     highlights smoothly, but a LUT cannot recover highlights that were
     clipped at capture — protect them in camera.

TIPS
----
- For the best result, expose so highlights are not clipped; the LUT preserves
  highlight texture that exists but cannot recover detail that is already gone.
- The LUT is designed for Apple Log 2. Do not apply it to Apple Log (Rec.2020)
  or non-log footage — the decode stage is specific to Apple Log 2.
- If a specific shot needs more or less warmth, adjust white balance / exposure
  in camera, or blend the LUT in post.


FOLDER CONTENTS
---------------
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube      The deliverable LUT (33^3).
  PREVIEWS/                            16 PNGs: 8 BEFORE + 8 AFTER (1600x1000).
  GALLERY/index.html                   Interactive before/after gallery.
  CONTACT_SHEET/contact_sheet.png      Visual overview of all eight scenes.
  README.txt                           This file.
  VALIDATION_REPORT.txt                Sources, tests, results and limitations.
  assets/                              The 8 source scene images (simulated).
  scripts/                             Reproducible build/render/validate code.


CREDITS & SOURCES (summary)
---------------------------
Technical specifications implemented and cross-checked:
  - Apple Log / Apple Log 2 transfer function — Apple Inc. "Apple Log Profile
    White Paper" (2023) and "Apple Log 2 White Paper" (2025); constants
    cross-checked against colour-science and the ACES IDT transform.
  - Apple Wide Gamut primaries — Apple Log 2 White Paper; cross-checked against
    ASWF OpenColorIO PR #2343 and OpenColorIO-Config-ACES PR #179.
  - Apple developer docs, AVCaptureColorSpace (appleLog / appleLog2).
  - Rec.709 primaries and gamma 2.4 (standard).
  - .cube format — Adobe "Cube LUT Specification 1.0" (red-fastest ordering).
  - Blackmagic Camera iOS .cube support — App Store / Apple support docs.

The preview source images are PROCEDURALLY GENERATED and the Apple Log 2 input
is a DOCUMENTED SIMULATION (the exact inverse of the LUT decode stage). They
are NOT iPhone sensor footage. See VALIDATION_REPORT.txt for full detail.

No physical iPhone or Blackmagic Camera testing was performed in building this
LUT. See VALIDATION_REPORT.txt for all tests performed and limitations.
================================================================================
