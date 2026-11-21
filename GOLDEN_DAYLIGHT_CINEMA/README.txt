GOLDEN DAYLIGHT CINEMA
======================
A daylight colour transform for Apple Log 2 footage from the iPhone 17 Pro
(Apple Wide Gamut), delivering a finished Rec.709 image at display gamma 2.4.

Package contents
----------------
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube     33x33x33 3D LUT, .cube (Resolve/Premiere/FCP)
  PREVIEWS/BEFORE/                    plain Rec.709 conversion of each test frame
  PREVIEWS/AFTER/                     the same frames with the LUT applied
  PREVIEWS/EXPOSURE_TESTS/            scene 03 at -1 / 0 / +1 stop
  CONTACT_SHEET/                      printable contact sheets (A/B scenes, C exposure)
  GALLERY/index.html                  offline gallery: drag to compare every scene
  VALIDATION_REPORT.txt               every measurement, including what is imperfect
  README.txt                          this file


What the LUT expects
--------------------
  Input   : Apple Log 2, Apple Wide Gamut primaries, full range (0-1 code)
  Output  : Rec.709 primaries, gamma 2.4, full range, clamped to 0-1
  Size    : 33^3, tetrahedral interpolation assumed (all NLEs do this by default)

The transform converts Apple Wide Gamut to Rec.709 (Bradford D65 adaptation),
applies a filmic tone curve anchored to Apple's published log curve, adds a
warm-highlight / cool-shadow split, protects skin hue, and compresses saturated
colours into the 709 gamut smoothly instead of clipping them.

Important: the LUT is a complete Log -> Display transform. Apply it ONCE and do
not chain a second "Apple Log to Rec.709" conversion before or after it.


DaVinci Resolve
---------------
  1. Copy GOLDEN_DAYLIGHT_CINEMA.cube into the LUT folder:
       macOS   ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/
       Windows %APPDATA%\Blackmagic Design\DaVinci Resolve\Support\LUT\
       Linux   ~/.local/share/DaVinciResolve/LUT/
     (or use Project Settings > Color Management > Open LUT Folder)
  2. Leave "Color science" on DaVinci YRGB (not DaVinci YRGB Color Managed),
     set Timeline color space to Rec.709 / Gamma 2.4.
  3. On the clip: right-click > LUT > GOLDEN_DAYLIGHT_CINEMA.
  4. If you use Color Management instead, set the clip's Input Color Space to
     "Apple Log 2 / Apple Wide Gamut" (or a Color Space Transform node doing the
     same), then use this LUT in an unmanaged node, and set Output to Rec.709.

Final Cut Pro (10.6.6 or later)
-------------------------------
  1. Copy the .cube into:
       ~/Library/Application Support/ProApps/Custom LUTs/GOLDEN/
  2. Select the clip, open the Effects browser > Color > Custom LUT.
  3. Choose GOLDEN_DAYLIGHT_CINEMA from the Custom LUT > Choose Custom LUT menu.
  4. Set the project to Rec.709 / Standard (gamma 2.4 equivalent).

Adobe Premiere Pro / After Effects
----------------------------------
  1. Lumetri Color > Basic Correction > Input LUT > Browse...
  2. Select GOLDEN_DAYLIGHT_CINEMA.cube.
  3. Sequence settings: Rec.709, 8- or 10-bit, full range.
  4. Keep Lumetri's Input Color Space at "None" (the LUT already does the work).

Other software (Assimilate, Baselight, OBS, FFmpeg, Nuke, Blender)
------------------------------------------------------------------
  .cube is accepted directly. With FFmpeg:
    ffmpeg -i in.mov -vf "lut3d=GOLDEN_DAYLIGHT_CINEMA.cube" -c:v prores_ks out.mov
  With OBS: Filters > Apply LUT, then select the .cube.

GPU shader / engine integration
-------------------------------
  Upload the 33^3 texture as a 3D texture with linear filtering and trilinear or
  tetrahedral interpolation. The cube is stored in the standard .cube order:
  red index changes fastest, then green, then blue; 0.0 domain minimum,
  1.0 domain maximum; no 1D pre-LUT ("shaper") is used.


Working with the LUT
--------------------
* Exposure: the curve is anchored so 18% scene grey lands at Rec.709 code 0.431
  (10-bit 441, about 0.2 stop under a plain 2.4 gamma conversion). Blacks sit at
  code 0.055 (10-bit 57) for 0% reflectance and the white point at 0.949
  (10-bit 971) for 100% reflectance. If the shot is underexposed by a stop, the
  whole image sits lower and looks denser; correct exposure before the LUT
  rather than fighting it afterwards.
* White balance: the transform preserves the ratio of the channels it is given,
  so a wrongly balanced shot stays wrongly balanced. Shoot or balance neutral.
* Highlight headroom: above 100% scene reflectance the curve eases into white
  (200% -> 0.974, 400% -> 0.982, 800% -> 0.985, 1200% -> 0.986). The LUT itself
  never clips and never emits 1.0; anything the camera did not record above
  1200% is gone before the LUT sees it.
* Saturation: the grade boosts midtone colour moderately; it never pushes a
  channel to hard clip, so saturated LEDs and sun glints roll off instead of
  turning into colour blocks.
* Skin: hue is held to within a fraction of a degree through the whole range
  (measured max drift +0.2 degrees on the reference portrait).
* Mixed colour temperature: with tungsten light in frame, the LUT keeps it warm
  and does not neutralise it. That is intentional; correct it upstream.

What it is not
--------------
* Not a "look pack" with a dozen variants. One transform, tuned for daylight.
* Not a fix for poorly exposed or badly white-balanced footage.
* Not an HDR transform. Output is Rec.709 gamma 2.4 SDR only.
* Not a highlight-recovery tool: data the camera did not record cannot come back.


Rebuilding from source
----------------------
Everything in this package is generated, not hand-drawn:

  build/apple_log2.py     Apple Log 2 encode/decode, primaries, Bradford CAT, OKLab
  build/grade.py          the creative grade and the analytic transform
  build/make_lut.py       writes LUT/GOLDEN_DAYLIGHT_CINEMA.cube
  build/lut_io.py         .cube writer/reader and tetrahedral interpolation
  build/simulate.py       synthetic Apple Log 2 frames from SDR sources
  build/render_previews.py renders BEFORE/AFTER previews from the .cube on disk
  build/validate.py       runs every test in VALIDATION_REPORT.txt

  python3 build/make_lut.py
  python3 build/render_previews.py
  python3 build/validate.py
  python3 build/make_contact_sheet.py
  python3 build/make_gallery.py

Requires Python 3.10+ with numpy and Pillow.
