================================================================================

                        G O L D E N   D A Y L I G H T
                              C I N E M A

            A standalone cinematic LUT for Apple Log 2 footage from
            iPhone 17 Pro, recorded with Blackmagic Camera for iOS.

================================================================================


WHAT THIS IS
--------------------------------------------------------------------------------

One 33-point 3D LUT that takes harsh, flat midday iPhone footage and turns it
into a warm, dimensional, Mediterranean travel film.

It is STANDALONE. The file does the whole job in a single step:

    Apple Log 2 signal
      -> decode the Apple Log transfer function
      -> Apple Wide Gamut to Rec.709 primaries (both D65)
      -> gamut compression
      -> creative grade
      -> Rec.709, gamma 2.4

You do NOT need a conversion LUT in front of it, and it must NOT be fed
footage that has already been converted to Rec.709. Give it the log signal.


THE FILE
--------------------------------------------------------------------------------

    LUT/GOLDEN_DAYLIGHT_CINEMA.cube

    Format        3D .cube (Adobe / IRIDAS), plain ASCII
    Size          33 x 33 x 33 = 35,937 entries, 971,573 bytes
    SHA-256       22032e6c5d779241328250115901a9501f6419b6bdb048e18e037a90
                  bffc74c2
    Domain        0.0 - 1.0
    Input         Apple Log 2 / Apple Wide Gamut, normalised FULL range
    Output        Rec.709 primaries, D65, gamma 2.4 (BT.1886, Lb = 0)

33 points is deliberate: Blackmagic Camera for iOS accepts 17-point and
33-point 3D .cube LUTs only.


WHAT IS IN THIS FOLDER
--------------------------------------------------------------------------------

    LUT/                        The deliverable. This is the only file you
                                need to install.

    PREVIEWS/                   Eight BEFORE and eight AFTER PNG renders at
                                1376 x 768. Same source, same framing, same
                                exposure within each pair.

    PREVIEWS/REFERENCE/         A neutral Apple Log 2 to Rec.709 conversion of
                                each scene, with no creative grade. Use this to
                                judge what the LOOK is doing as opposed to what
                                the technical conversion is doing.

    GALLERY/index.html          Interactive before/after sliders, built for
                                iPhone Safari. Open this first.

    CONTACT_SHEET/              All eight comparisons on one sheet.

    VALIDATION_REPORT.txt       Every test that was run on the delivered
                                .cube, the measured numbers, and the
                                limitations.

    README.txt                  This file.


INSTALL ON IPHONE (BLACKMAGIC CAMERA FOR IOS)
--------------------------------------------------------------------------------

  1. Get GOLDEN_DAYLIGHT_CINEMA.cube onto the phone, into the Files app.
     AirDrop, iCloud Drive, a download in Safari, or Finder all work.

     A .cube file does NOT need unzipping. If you downloaded the ZIP of the
     whole folder, tap it in Files first to extract it, then go into
     GOLDEN_DAYLIGHT_CINEMA > LUT.

  2. Open Blackmagic Camera.

  3. Settings  >  LUTs  >  Import LUT

     Then pick GOLDEN_DAYLIGHT_CINEMA.cube from Files.

     Alternative: in Files, copy the .cube into
     On My iPhone > Blackmagic Camera > LUTs
     and it will appear in the app's LUT list.

  4. Set the recording colour space to APPLE LOG 2.
     (iPhone 17 Pro and 17 Pro Max only. Apple Log 2 does not exist on
     earlier iPhones.)

  5. Turn the LUT on for MONITORING, so you see the graded image while
     shooting.

  6. Leave "Record LUT to Clip" OFF.

     This is the important one. Off means you record a clean Apple Log 2
     master and keep every option in post, while still framing and exposing
     against the final look. On means the look is burned in permanently
     and cannot be undone.

  7. If the app asks for a LUT colour space tag, choose Rec.709.


HOW TO EXPOSE FOR IT
--------------------------------------------------------------------------------

  Expose for the highlights. A LUT cannot invent detail that the sensor
  already clipped, and this look has a soft shoulder that will render blown
  areas as smooth, textureless white.

  The grade intentionally sits below the source in the shadows, around
  0.82x source luminance in the lower quartile. That is what creates the
  density. It also means under-exposed footage will read dark: fix that with
  exposure BEFORE the LUT, not after.

  Mid-grey behaviour, measured on the delivered file: an 18 % grey card
  arrives at output code 0.424, and 90 % diffuse white at 0.825. There is
  real highlight headroom above that; the top of the Apple Log 2 range
  (1200 % reflectance) lands at 0.995 and does not hard clip.

  The look holds over a +/- 2 EV exposure error. Skin hue drifts less than
  6 degrees across that whole range.


USING IT IN POST
--------------------------------------------------------------------------------

  DaVinci Resolve

    Set the clip's input colour space to Apple Log 2 / Apple Wide Gamut and
    the timeline to Rec.709 Gamma 2.4.

    Apply this LUT on a node with NO colour-management input transform in
    front of it. If you are using Resolve Colour Management, set that node
    or the clip to bypass the input transform, otherwise the log decode
    happens twice and the image will look thin and washed out.

    If the image looks wrong, the usual cause is a double conversion.

  Final Cut Pro

    Do not apply an Apple Log 2 camera LUT or a log conversion effect as
    well. Use this LUT alone, with the library set to Rec.709.

  Premiere Pro

    Apply as an Input LUT in Lumetri, with no other log conversion active.


WHAT THE LOOK DOES
--------------------------------------------------------------------------------

  Warmth that follows the surface, not the brightness.
    The honey tint is steered by chroma and hue rather than by luminance
    alone. Surfaces that are already warm - stone, skin, sand, foliage -
    get richer. Near-neutral surfaces receive only a fraction of the tint,
    so concrete, white linen and cloud stay believable. Measured: an 18 %
    grey card leaves with an R/B ratio of 1.09, and 90 % white at 1.03.

  Skies stay blue.
    Blues and cyans are actively excluded from the warm tint. Across the
    eight test scenes sky hue moves +4.5 degrees TOWARDS blue, at 0.97x the
    source saturation and 0.99x its luminance. No turquoise, and the sky is
    not artificially darkened.

  Skin first.
    Skin hue is held to within 1.3 degrees of the source. No orange push, no
    saturation blowout, and no smoothing of any kind - a 3D LUT cannot and
    does not touch texture.

  Foliage without the radioactive green.
    Greens rotate 10.5 degrees towards yellow at 1.11x saturation, which
    reads as sun-warmed rather than fluorescent, and never teal.

  It will not brighten already-bright footage.
    Upper quartile 0.95x and 95th percentile 0.90x of source luminance.
    Highlight texture is preserved rather than pushed up the curve.

  Golden hour is safe.
    Because the warmth is chroma-aware, light that is already warm is
    enriched instead of doubled. Scene 06 in the previews is that test case.


HONEST LIMITATIONS
--------------------------------------------------------------------------------

  NO IPHONE WAS USED. No iPhone 17 Pro, no iPhone of any kind, and no
  installation of Blackmagic Camera took part in making or testing this.
  The install steps above are transcribed from current vendor documentation,
  not from a device test. On-device import, appearance and performance are
  UNVERIFIED. Check it on your own phone before relying on it for a job.

  THE PREVIEWS ARE SIMULATED. No real Apple Log 2 footage was available.
  The preview frames are AI-generated stills converted into Apple Log 2 by a
  documented chain (inverse BT.709 OETF, highlight expansion, Rec.709 to
  Apple Wide Gamut, Apple Log encode, 10-bit quantise). They are NOT iPhone
  captures and do not reproduce Apple's sensor noise, demosaic or ISP colour
  science. Full method in VALIDATION_REPORT.txt and in the repository's
  sources/CREDITS.md.

  Every AFTER image, however, was produced by applying this exact .cube.
  Validation re-renders all eight from the shipped file and confirms they are
  bit-identical.

  A LUT CANNOT RECOVER CLIPPED HIGHLIGHTS. Nothing can. Expose correctly.

  IT IS A CREATIVE LOOK, NOT A TECHNICAL CONVERSION. It deliberately moves
  colour and deliberately loses some shadow luminance. For colour-critical
  technical work use Apple's own Apple Log 2 to Rec.709 conversion.

  33-POINT QUANTISATION. Mean error against the exact transform is 0.33/255.
  The maximum, 11.7/255, occurs only at extreme saturated corners of the
  colour cube that real footage does not reach.

  FULL-RANGE ASSUMPTION. The LUT expects the normalised full-range Apple
  Log 2 signal (10-bit code 0-1023 mapped to 0.0-1.0), which is how Apple
  defines it. A host that feeds a legal/video-range signal without expanding
  it will produce a contrastier, clipped image.


VALIDATION SUMMARY
--------------------------------------------------------------------------------

  34 of 34 automated checks pass on the delivered file, including:

    - valid 33^3 .cube syntax, 35,937 entries, no NaN, no infinity,
      all values inside [0, 1]
    - Apple Log 2 decode reproduces all four of Apple's published anchor
      points (0 %, 18 %, 90 %, 1200 % reflectance) to within one 10-bit code
    - the Apple Wide Gamut matrix, re-derived from the published
      chromaticities, matches the OpenColorIO reference to 2.4e-15
    - neutral ramp monotonic, no banding, no slope discontinuity
    - skin, sky, foliage, stone, white and shadow behaviour measured on all
      eight scenes
    - the look holds from -2 EV to +2 EV
    - all eight AFTER previews are bit-identical to a fresh render from this
      .cube

  Read VALIDATION_REPORT.txt for the numbers and the caveats.


================================================================================
 One LUT. 33 x 33 x 33. Apple Log 2 to Rec.709 gamma 2.4.
================================================================================
