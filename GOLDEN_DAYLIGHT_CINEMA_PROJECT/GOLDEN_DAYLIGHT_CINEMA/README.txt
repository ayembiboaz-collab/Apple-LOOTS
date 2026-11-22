GOLDEN DAYLIGHT CINEMA
======================
A warm, filmic Rec.709 SDR look for Apple Log 2 / Apple Wide Gamut footage.
One 33 x 33 x 33 .cube LUT. Version 1.0, 22 November 2026.


1. WHAT THIS IS
---------------
GOLDEN_DAYLIGHT_CINEMA.cube converts Apple Log 2 (Apple Wide Gamut) to Rec.709
SDR with a pure gamma 2.4 transfer function, and applies a single, deliberate
grade on the way:

  * warm, sunlit highlights and a honey-gold cast in the upper midtones,
  * neutral, slightly cool shadows that never go blue-black or muddy,
  * clear separation between midtones without harsh contrast,
  * rich but controlled colour: no turquoise skies, no neon foliage,
  * skin kept on the correct side of the vectorscope line (no orange or red
    faces), protected across a four-stop exposure range,
  * highlights that roll off smoothly instead of clipping, and no crushed
    blacks.

The LUT is completely standalone. It already contains the Apple Log 2 decode,
the Apple Wide Gamut -> Rec.709 matrix, the whole grade and the gamma 2.4
encode, so nothing else has to be loaded before it. Internally there is exactly
one deliverable LUT (variants such as a trilinear-fit table or a Lab-space fit
were only ever used as experiments and are not shipped).


2. FILES IN THIS FOLDER
-----------------------
  LUT/GOLDEN_DAYLIGHT_CINEMA.cube        the deliverable (33^3, 970,925 bytes)
  PREVIEWS/                              8 x BEFORE and 8 x AFTER PNGs
                                          (1280 px long edge, display-encoded)
  GALLERY/index.html                     interactive before/after sliders,
                                          full-screen view, credits, install
                                          notes - open in any browser, works
                                          offline, works on iPhone
  GALLERY/assets/                        JPEG derivatives used by the gallery
  CONTACT_SHEET/                         contact_sheet_before.jpg,
                                          contact_sheet_after.jpg,
                                          contact_sheet_before_after.jpg
  README.txt                             this file
  VALIDATION_REPORT.txt                  everything that was measured
  SOURCES.txt                            photo provenance + technical citations

Outside this folder:
  ../build/          the complete, reproducible pipeline (Python) + BUILD.md
  ../source_images/  the eight original photographs (resized only)
  ../simulated_log/  the eight frames as simulated Apple Log 2, 16-bit PNG
  ../validation/     machine-readable results, charts, logs, hashes
  ../GOLDEN_DAYLIGHT_CINEMA.zip   the complete folder above, zipped


3. TECHNICAL SPECIFICATION
--------------------------
Input
  Colour space : Apple Wide Gamut (primaries R 0.725/0.301, G 0.221/0.814,
                 B 0.068/-0.076, white D65 0.3127/0.3290)
  Transfer     : Apple Log 2, i.e. the Apple Log transfer function applied to
                 Apple Wide Gamut primaries. Decode, with R = linear scene
                 light normalised so that 1.0 = the Apple Log "1.0" anchor:
                   R >=  0.01 : code = 0.08550479 * log2(R + 0.00964052)
                                        + 0.69336945
                   0 <= R < 0.01 : code = 47.28711236 * (R + 0.05641088)^2
                   (code 0.1504764523 is video black, i.e. R = 0)
  Range        : 0..1 code values, as recorded. Values below 0.15047 are below
                 video black and map to 0.0 output.

Output
  Colour space : Rec.709 primaries, D65 white point, SDR
  Transfer     : PURE gamma 2.4, exactly and only
                   encode: E = V^(1/2.4)
                   decode: V = E^2.4
                 (no sRGB toe, no BT.1886 "black lift", no Display-P3)
  Range        : 0..1 code values, no NaN, no Inf, no negative values

Table
  LUT_3D_SIZE  : 33
  Red index    : fastest (standard .cube ordering)
  DOMAIN_MIN   : 0 0 0        DOMAIN_MAX : 1 1 1
  Precision    : six decimal places (0.000001 = 1/1000 of a 10-bit code step)
  Interpolation: tetrahedral is what the table was fitted for (trilinear is also
                 constrained; see VALIDATION_REPORT.txt, section 5)


4. HOW TO USE IT
----------------
Blackmagic Camera for iPhone (the app this LUT was designed for)
  1. Copy GOLDEN_DAYLIGHT_CINEMA.cube to the phone (Files / AirDrop).
  2. Open Blackmagic Camera > gear icon > LUTs > LUTs Manager > Import LUT,
     and pick the file.
  3. Shoot with Apple Log 2 enabled and choose the LUT either as a monitoring
     (display) LUT or as a LUT baked into the recording - the app keeps those
     two switches separate, so decide before you roll.
  The Blackmagic Camera app accepts 17-point and 33-point .cube 3D LUTs; this is
  a 33-point file.

DaVinci Resolve
  Copy the .cube into the LUT folder (Project Settings > Color Management >
  Lookup Tables, "Open LUT Folder"), then apply it on a Colour page node. Set
  the clip's input to Apple Log 2 / Apple Wide Gamut; the node applies the
  creative grade and the Rec.709 gamma 2.4 output.

Other software
  Any application that reads 33-point .cube files works, provided you set the
  timeline/output to Rec.709 gamma 2.4 and the input to Apple Log 2. If the
  application insists on applying its own output transform after the LUT, the
  result will be double-transformed and look flat - in that case set the LUT as
  a "display" LUT, or apply it in a Rec.709 pipeline with no further transform.


5. WHICH FOOTAGE THIS IS FOR
----------------------------
  * iPhone 17 Pro / 17 Pro Max / 18 Pro and later: Apple Log 2 (Apple Wide
    Gamut). This is the intended input.
  * iPhone 15 Pro / 16 Pro: Apple Log with Rec.2020 primaries. That is a
    different colour space; this LUT is not built for it and will shift colour
    if you use it there.
  * Anything else: not supported. A LUT is only correct for one input space.

  These statements are about Apple's published specifications, not about tests
  on a physical iPhone. No iPhone was used to produce or verify this project.


6. WHAT THE LOOK DOES, IN MEASURED TERMS
----------------------------------------
  * Neutral axis: mid grey sits 3.56 C*ab (CIELAB) off true neutral at hue 77
    degrees - a warm, yellow-leaning cast, deliberately small. The largest cast
    anywhere on the neutral ramp is 3.64 C*ab (OKLab chroma 0.0099); at white
    and at black it falls to OKLab chroma 0.0013 and 0.0003, i.e. neutral.
  * Highlights (neutral ramp, log code -> Rec.709 code):
      0.40 -> 0.317   0.50 -> 0.501   0.60 -> 0.742
      0.70 -> 0.899   0.80 -> 0.956   0.90 -> 0.978   1.00 -> 0.986
    i.e. the top 1.1 stops of the input (log code 0.90 -> 1.00) move the output
    by 0.008 of a code value instead of hitting 1.000 and clipping flat.
  * White clipping on the eight test frames: 0.83 % of channels on the
    whitewashed street before the LUT (0.03-0.08 % on three other frames),
    0.00 % after it on every frame. Black clipping: 0.00 % of channels after the
    LUT on every frame (it was up to 3.74 % before).
  * Skin: the lit face patch moves from 119.6 to 120.8 degrees on the Bt.709
    vectorscope (the classic skin line is 110-130 degrees) while its chroma
    drops 10 % - warmer and less red, not more.
  * Skies: OKLab chroma of the sky region drops on every frame (e.g. the beach
    sky 0.146 -> 0.134); hue is preserved within 1 degree on the large sky
    areas, so blue stays blue instead of sliding towards cyan.
  * Foliage: the sunlit grass region rotates 4.4 degrees towards yellow with its
    chroma held flat (0.056 before and after), while deeper green goes slightly
    quieter - differentiated greens, no "radioactive" look.
  * Shadow noise: the LUT's noise gain at log code 0.17 is 2.04x versus 2.89x
    for the plain conversion; at code 0.151 (video black) 1.11x versus 16.4x,
    because sub-black noise is deliberately mapped to black.
  * Bake accuracy: on the eight delivered frames the difference between the
    LUT and the analytic pipeline is 0.34 dE2000 mean / 1.58 p99 (tetrahedral),
    i.e. 1.1 code values out of 255 on average.


7. HOW THE PREVIEW IMAGES WERE MADE
-----------------------------------
BEFORE  = simulated Apple Log 2 of each photograph, put through the plain,
          verified Apple Log 2 -> Rec.709 conversion: Apple Log 2 decode ->
          Apple Wide Gamut -> Rec.709 matrix (D65) -> clip -> gamma 2.4.
          No creative treatment, no gamut compression, no tone curve.
          This is the direct, neutral transform, so it is the honest baseline.
AFTER   = the very same pixels, put through the delivered
          GOLDEN_DAYLIGHT_CINEMA.cube file, read and applied by an independent
          implementation (tetrahedral interpolation), then encoded to gamma 2.4.

Both sides start from the same 10-bit quantised input (each channel rounded to
1023 levels), because that is what an iPhone records - neither side gets a
precision advantage.

The eight source photographs are much wider in dynamic range than one JPEG can
hold, so they were first treated as scene-referred light (sRGB -> linear ->
Rec.709 -> Apple Wide Gamut -> Apple Log 2) and then handled by the pipeline.
That simulation is labelled as simulation everywhere; it is not raw iPhone
footage, and no iPhone was used.

The PNG previews are display-encoded copies of the Rec.709 gamma-2.4 renders:
the code values were converted with the sRGB transfer function so they look
right in a browser or on an iPhone (a pure 2.4 image displayed as if it were
sRGB looks too dark). The .cube itself is untouched and stays Rec.709 gamma 2.4.


8. LIMITATIONS - PLEASE READ
----------------------------
  * The LUT is a 3D colour transform only. It has no grain, no halation, no
    bloom, no diffusion, no sharpening and no noise reduction. None of those
    effects appear in the AFTER images either.
  * It cannot recover clipped highlights: where the camera clipped, the data is
    gone. The roll-off is smooth but it is not reconstruction.
  * It is not depth-aware. No depth map, portrait-mode matte or monocular depth
    estimate is used anywhere in the delivered images.
  * One LUT, one input space. Apple Log (Rec.2020, iPhone 15/16 Pro) is a
    different input and is out of scope.
  * dE2000 numbers in dark areas are inflated by the metric itself; the report
    gives code-value errors alongside them. See VALIDATION_REPORT.txt,
    section 13, where every caveat is listed with the number that supports it.
  * The photographs are real but they are stills; how the LUT behaves on moving
    skin, flare and rolling shutter was not tested.


9. CREDITS
----------
Eight real photographs, all Unsplash License (free for commercial and
non-commercial use, no permission needed). The files are exactly what the source
delivered (3000 px long edge) - no crop, no retouch, no AI generation anywhere
in this project:

  01 Oklahoma City, USA          Justin Prine        QGP7ncFD0LA
  02 Bellingham, USA             Elle Cartier        qSYohksKbiI
  03 Mykonos, Greece             Julien Gaillard     SvS4pQBjJKQ
  04 beach                       Francesco Ungaro    6BzelJ-qVe0
  05 alpine valley               Francesco Ungaro    S_kzomYltgo
  06 Hřensko, Czechia            Artem Sapegin       8c6eS43iq1o
  07 Tirana, Albania             Aldo Vukaj          w-nBFVS928I
  08 Dubrovnik, Croatia          Kevin Charit        TZuigM9Cs9I

Full URLs, camera EXIF, publication dates and the exact modifications are in
SOURCES.txt, which also lists the technical references (Apple's white paper,
OpenColorIO matrices, colour-science, Blackmagic documentation) and separates
verified facts from assumptions.


10. REBUILDING IT
-----------------
Everything in this package is generated by the scripts in ../build. See
../build/BUILD.md for the pipeline description, the exact parameters and the
commands; it takes about a minute end to end on a laptop CPU.
