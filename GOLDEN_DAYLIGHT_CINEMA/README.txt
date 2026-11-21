GOLDEN DAYLIGHT CINEMA
================================================================================
A standalone 33 x 33 x 33 3D LUT for Apple Log 2 footage recorded on
iPhone 17 Pro / 17 Pro Max with Blackmagic Camera for iOS.

Output: Rec.709 SDR, gamma 2.4.
The LUT decodes Apple Log 2 in Apple Wide Gamut itself. It needs no second
conversion LUT and does not assume the footage is already Rec.709.


WHAT IS IN THIS FOLDER
================================================================================
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube         the LUT (33^3, about 1.05 MB)
  PREVIEWS/                               eight BEFORE and eight AFTER PNGs
  PREVIEWS/SIMULATED_APPLE_LOG2_SOURCES/  the simulated Apple Log 2 plates
  GALLERY/index.html                      interactive gallery (open in Safari)
  CONTACT_SHEET/                          visual overview + look reference chart
  SCENES/source/                          the eight reference stills
  SCENES/prompts.txt                      how each scene was made, and what it tests
  SCENES/render_manifest.json             SHA-256 of the LUT and every preview
  README.txt                              this file
  VALIDATION_REPORT.txt                   sources, tests, results, limitations

The build and validation scripts live in the repository at dev/ (look.py,
colorlib.py, scenes.py, render_previews.py, validate.py, make_gallery.py,
make_contact_sheet.py, package.py). Every file listed above can be regenerated
from them.


INSTALL ON iPHONE (BLACKMAGIC CAMERA FOR iOS)
================================================================================
1. Get the .cube onto the phone in the Files app.
   - From GitHub: open the LUT link in Safari, tap Share, then "Save to Files",
     and save it somewhere you will find again (for example On My iPhone).
   - From a computer: AirDrop the file to the phone, or use iCloud Drive.
   - From this ZIP: unzip it in Files and open LUT/GOLDEN_DAYLIGHT_CINEMA.cube.

2. Set the camera to Apple Log 2.
   In Blackmagic Camera, open Settings (gear icon) > Record > Color Space and
   choose Apple Log 2. Choosing Apple Log HDR/Log (the older Rec.2020 profile)
   is NOT the same thing: this LUT expects Apple Log 2 in Apple Wide Gamut and
   will render colours incorrectly if fed the older Apple Log.

3. Import the LUT.
   Settings > LUT > Manage LUTs (wording varies slightly between versions), then
   add/import and pick GOLDEN_DAYLIGHT_CINEMA.cube from Files. Blackmagic Camera
   accepts .cube LUTs up to 33 points, which is exactly what this is.

4. Select it as the display LUT.
   In the camera screen, tap the LUT button and choose GOLDEN DAYLIGHT CINEMA.
   The preview now shows the graded image while the recording stays Apple Log 2.

5. Record. The LUT is a monitor LUT by default: your file remains Apple Log 2 and
   the look can be changed later. If your version offers "burn in", leaving it
   off is strongly recommended.

IMPORTANT EXPOSURE NOTE
The LUT expects normal exposure for log. It does not add a technical conversion
in front, so do not also enable a built-in Apple Log to Rec.709 conversion in
the app while this LUT is active; you would grade the image twice.

If the image looks washed out and grey, the app is showing raw log without the
LUT. If it looks contrasty but with wrong colours, a second conversion is
probably stacked in front of this one.

USING IT ANYWHERE ELSE
Set the clip's input to Apple Log 2 / Apple Wide Gamut and the output to
Rec.709 gamma 2.4, then apply the LUT. In DaVinci Resolve the input colour space
is Apple Wide Gamut where the version offers it; otherwise use a Colour Space
Transform to Rec.709 and note that colour management differences between
applications will change the result. Final Cut Pro, Premiere, Photoshop and
Affinity Photo all read a 33^3 .cube directly.


HOW THE LOOK IS BUILT
================================================================================
One continuous transform, in this order:

  1  Apple Log / Apple Log 2 decode to scene-linear reflectance
     (R0=-0.05641088, Rt=0.01, c=47.28711236, beta=0.00964052,
      gamma=0.08550479, delta=0.69336945; these are Apple's published
      constants and they are unchanged between Apple Log and Apple Log 2.)
  2  Apple Wide Gamut -> Rec.709 matrix. Both spaces are D65, so no chromatic
     adaptation is applied. The matrix is derived from Apple's published
     primaries: R(0.725,0.301) G(0.221,0.814) B(0.068,-0.076).
  3  Negative-channel compression, because Apple Wide Gamut is much wider than
     Rec.709 and the matrix legitimately produces negative channels.
  4  Neutral filmic tone map to Rec.709 gamma 2.4. This stage on its own, with
     the creative grade bypassed, is the BEFORE image of every pair.
  5  The creative look, in OkLab/OkLCh:
       - a filmic S in lightness with a protected toe (shadows stay detailed)
         and a compressed shoulder (highlight texture survives)
       - a midtone lift so stone and pavement stay luminous rather than muddy
       - chroma shaping by hue and lightness, with skin held back
       - honey warmth that saturates as a surface's own warmth rises, so
         golden-hour footage is not pushed further into orange
       - a tiny cool bias in the shadows for sun/shade separation
       - cyan-leaning sky pulled toward blue, only on bright low-chroma pixels
  6  Gamma 2.4 encode and output gamut fit.

No beauty smoothing, no skin masking, no local operations: every pixel is a
function of its own value, which is what makes a single 3D LUT possible.


COMPATIBILITY, STATED HONESTLY
================================================================================
Built for: iPhone 17 Pro / 17 Pro Max, iOS 26, Apple Log 2 (Apple Wide Gamut),
Blackmagic Camera for iOS, HEVC or ProRes log recording.

Tested on: nothing physical. No iPhone 17 Pro was available, and the LUT was
never loaded into Blackmagic Camera for iOS during this project. Colour
correctness is demonstrated against Apple's published specification and against
the ACES reference transform, and behaviour is measured on simulated Apple Log 2
plates. See VALIDATION_REPORT.txt for exactly what was and was not run.

Not for: Apple Log (v1) in Rec.2020. The gamut is different, so colours will be
wrong. Also not for HLG or any HDR delivery.

Known limits:
  - A LUT cannot recover clipped highlights. Once the sensor writes 1.0, the
    detail is gone; this LUT only shapes what is there.
  - Skin and warm limestone occupy nearly the same hue, so a single global LUT
    cannot treat them independently. This one prioritises skin.
  - Shadows are deliberately deepened by roughly 10-15% in relative lightness.
    Detail is preserved, but dark areas are darker than in a neutral conversion.


IMAGE PROVENANCE
================================================================================
The eight scenes in SCENES/source/ are AI-GENERATED reference photographs. They
are not iPhone footage and are not presented as such. Each was converted into a
SIMULATED Apple Log 2 plate by inverting this project's neutral display curve
back to scene reflectance and encoding that reflectance with the published Apple
Log 2 transfer function in Apple Wide Gamut, quantised to 10 bits.

BEFORE is that plate through the neutral technical conversion. AFTER is the same
plate through the delivered .cube, read back off disk and trilinearly
interpolated, exactly as a video application would. The two frames therefore
share source, composition and exposure by construction.

The simulation exercises the decode and the grade honestly, but it cannot
reproduce an iPhone sensor's noise, its true highlight clipping, or Apple's
upstream colour processing. See SCENES/prompts.txt for the prompt behind each
scene and what that scene is there to test.


SOURCES
================================================================================
S1  Apple Inc., Apple Log Profile White Paper (Sept 2023) and Apple Log 2 White
    Paper (Sept 2025): transfer-function constants and Apple Wide Gamut
    primaries, with the published 10-bit anchor points 0% -> 154,
    18% -> 500, 90% -> 697, 1200% -> 1023.
S2  Academy Software Foundation, aces-input-and-colorspaces,
    apple/CSC.Apple.AppleLog2_to_ACES.ctl (Apache-2.0): quoted constants and
    primaries. A copy is kept at dev/references/ in the repository, and the
    validation report compares it numerically with this implementation.
S3  Academy Software Foundation, OpenColorIO PR #2343 and
    OpenColorIO-Config-ACES PR #179: Apple Log 2 uses the Apple Log transfer
    function with Apple Wide Gamut primaries.
S4  colour-science/colour issue #1428 (Apple Log 2 white paper; same curve,
    new gamut).
S5  Apple developer documentation for AVCaptureColorSpace.appleLog2.

Verified fact: the constants and primaries, cross-checked above.
Derived, not published: the Apple Wide Gamut -> Rec.709 matrix. Apple publishes
primaries but no matrix, so it is derived at a shared D65 white point and
verified by recovering the primaries from it and by mapping white to white.
Assumed: that Blackmagic Camera for iOS writes Apple Log 2 in full range with no
extra toe or look. Unverified.


CREDITS AND LICENCE
================================================================================
LUT, look design, build scripts, renders, gallery and report: produced for this
project. The Apple Log / Apple Log 2 colour science constants and the Apple Wide
Gamut primaries are Apple's published specifications; the ACES CSC file is
Apache-2.0 and is included only as a reference copy under dev/references/.
The scene stills are AI-generated for this project (see SCENES/prompts.txt).

You may use the LUT on your own footage, commercially or otherwise. No warranty
is given; grade-check anything important before a shoot.
