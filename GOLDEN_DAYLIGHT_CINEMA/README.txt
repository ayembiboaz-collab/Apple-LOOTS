GOLDEN DAYLIGHT CINEMA
======================
A premium cinematic LUT for Apple Log 2 / Apple Wide Gamut footage from the
iPhone 17 Pro, converting to Rec.709 SDR at gamma 2.4.

Version          1.0
LUT              LUT/GOLDEN_DAYLIGHT_CINEMA.cube
Format           3D LUT, 33 x 33 x 33, .cube (Adobe / Resolve / Blackmagic)
Input            Apple Log 2, Apple Wide Gamut
Output           Rec.709 SDR, gamma 2.4
Size on disk     1.19 MB (35,937 entries)


WHAT IT IS
----------
One LUT. It does three jobs at once and needs nothing else in front of it:

  1. decodes the Apple Log transfer function
  2. converts Apple Wide Gamut primaries to Rec.709
  3. applies the creative grade

The result is warm, rich, dimensional midday footage: honeyed sunlight, deep
but detailed shadows, clean sun/shade separation, believed whites, natural blue
sky, natural foliage and natural skin.

It is NOT a warm filter. Warmth is applied in proportion to the colour already
in the frame, so sunlit stone, sand, timber and skin pick up honey while a grey
card, a white shirt and a cloud edge stay neutral. Sky is kept blue rather than
turquoise, foliage goes slightly olive rather than acid yellow-green, and skin
is left alone - no smoothing, no beauty processing, no red shift in deeper tones.

Because the grade is a tonal and chroma reshape rather than a heavy tint, it
also sits correctly on genuine golden-hour footage without doubling the warmth.


WHO IT IS FOR
-------------
iPhone 17 Pro / 17 Pro Max, recording Apple Log 2 - in Blackmagic Camera for
iOS, or in Apple's Final Cut Camera.

NOT for the original Apple Log on iPhone 15 Pro / 16 Pro. That format keeps the
same log curve but uses BT.2020 primaries, so it needs a different decode. Using
this file on Apple Log footage colours will be slightly off.


HOW TO SHOOT FOR IT
-------------------
1. Set the app to Apple Log 2 as the colour space / log format. ProRes or HEVC
   Log both work; ProRes gives you more room to move afterwards.

2. Expose for the highlights. Keep visible texture in the brightest sunlit
   surfaces. A LUT cannot recover clipped highlights - anything already at 100%
   stays white.

3. Don't underexpose to "protect" the grade. This look lifts the toe slightly
   but it does not invent shadow detail that was never recorded.

4. Watch the sky at midday. If a cloud is blown on the sensor, it is blown in
   the grade.


INSTALLING IN BLACKMAGIC CAMERA (iOS)
-------------------------------------
To load it as a monitor LUT in the app:

  1. Get GOLDEN_DAYLIGHT_CINEMA.cube onto the phone:
       - Download it in Safari; it lands in Files > Downloads, or
       - AirDrop it, or
       - Save it into iCloud Drive / On My iPhone from a computer.
  2. Open Blackmagic Camera and go to its LUT settings.
  3. Choose to import / load a LUT and pick GOLDEN_DAYLIGHT_CINEMA.cube from
     the Files picker.
  4. Select it as the monitor LUT so the viewfinder shows the graded look while
     you record. You are still recording Apple Log 2.

On-set note: a monitor LUT is a viewing aid, not a bake. Keep recording log so
you can adjust the grade later. If you prefer a lighter or heavier look on set,
adjust exposure and white balance in the app, not the LUT.

The exact menu wording inside Blackmagic Camera changes between app versions.
The step that matters is the same in every version: load a .cube from the Files
app into the LUT slot. This file was not tested on a physical device (see
"WHAT WAS AND WAS NOT TESTED" below).


APPLYING IT IN POST
-------------------
DaVinci Resolve, Final Cut Pro, Premiere, Avid, or anything that reads .cube:

  - Apply the LUT DIRECTLY to the Apple Log 2 clip.
  - Do NOT add an Apple Log to Rec.709 conversion LUT before it. This file
    already does that conversion; stacking a second one will double the
    contrast and shift the colour.
  - Treat the LUT output as your Rec.709 deliverable. Grade before the LUT for
    exposure and white balance, or after it for taste.

Resolve: apply as a 3D LUT in a node on the log clip, with the clip's input
colour space set to whatever passes the log values through untouched.
Final Cut Pro: apply as a Custom LUT effect on the log clip. If the clip is
tagged as Apple Log 2 and FCP has already converted it, tell it not to, or
disable the automatic log conversion for that clip.

If you export a baked Rec.709 master, this is the only conversion you need.


WHEN IT DOESN'T LOOK RIGHT
--------------------------
Too bright and washed out
  The footage was probably already converted to Rec.709 before the LUT was
  applied. Apply it to log.

Green, flat, or washed-out colour
  You may be on original Apple Log (iPhone 15/16 Pro) rather than Apple Log 2,
  or another camera's log entirely. This is a specific decode, not a generic
  "log" LUT.

Too warm / too cool
  Trim white balance before the LUT. The LUT's warmth is designed to sit on
  correctly balanced daylight; a big WB error in the clip will still show.

Shadows look heavy
  Lift the clip before the LUT (raise exposure or lift the toe), rather than
  fighting the LUT. The toe is deliberately deep so that shade reads as shade.

Muddy or banded sky
  Check the source. Compressing 10-bit log into 8-bit H.264 before grading will
  band. Work from ProRes Log where possible.


FILES
-----
LUT/GOLDEN_DAYLIGHT_CINEMA.cube              the LUT
PREVIEWS/*_BEFORE.png, *_AFTER.png           eight before/after pairs
PREVIEWS/*_LOG2_SIMULATED.png                the simulated Apple Log 2 input
GALLERY/index.html                           interactive preview gallery
CONTACT_SHEET/                               one-page visual overview
VALIDATION/reference_chart.png               patch chart, plain vs graded
VALIDATION/validation_results.json           every measured number
VALIDATION_REPORT.txt                        method, sources, results, limits
BUILD/                                       the scripts that build all of it
SOURCE_PLATES/                               the eight source images


REPRODUCING THE LUT
-------------------
Requires Python 3.9+, numpy and pillow.

  pip install numpy pillow
  cd BUILD
  python3 build_lut.py        # writes ../LUT/GOLDEN_DAYLIGHT_CINEMA.cube
  python3 render.py           # renders the eight before/after pairs
  python3 validate.py         # runs all validation checks
  python3 make_chart_image.py
  python3 make_contact_sheet.py
  python3 make_web_images.py

The look parameters all live in one dictionary at the top of BUILD/grade.py.
BUILD/apple_log2.py holds the colour science with source citations.


WHAT WAS AND WAS NOT TESTED
---------------------------
Tested, on the delivered file:
  - 33x33x33 structure, syntax, 35,937 data rows, domain 0-1
  - no NaN or Inf, all values inside 0-1
  - the Apple Log curve against Apple's published anchor points
  - Apple Wide Gamut primaries against an independent OpenColorIO derivation
  - Rec.709 gamma 2.4 output encoding
  - neutral behaviour, clipping and black behaviour
  - skin, sky and foliage behaviour across all eight scenes
  - nine calibrated skin tones from light to deep
  - simulated exposure from -2 to +2 EV
  - that the AFTER images really do come from this file, re-rendered from disk
  - banding / tonal smoothness against the plain conversion

NOT tested:
  - a physical iPhone 17 Pro, and Blackmagic Camera's LUT slot. No device was
    available.
  - real Apple Log 2 sensor footage. The input images are AI-generated
    photorealistic plates converted to Apple Log 2 by a documented simulation.
    See VALIDATION_REPORT.txt.
  - other apps' implementations of .cube interpolation.

See VALIDATION_REPORT.txt for the full method, the citations, and every
limitation, including what a LUT fundamentally cannot do.
