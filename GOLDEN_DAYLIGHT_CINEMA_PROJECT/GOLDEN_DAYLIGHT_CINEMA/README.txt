GOLDEN DAYLIGHT CINEMA — STANDALONE LUT, EVALUATION BUILD

This download contains ONE 33-point .cube. It is a functioning, independently
parsed LUT, but is NOT yet a visually reviewed, reference-grade flagship release.
The complete requested gallery, photographic comparisons and contact sheet are
not included. Read VALIDATION_REPORT.txt before relying on it.

INPUT: Apple Log 2 / Apple Wide Gamut (not the original Apple Log/Rec.2020,
not ordinary Rec.709, and not already converted footage).
OUTPUT: SDR Rec.709 primaries, D65; pure display encoding power 1/2.4.
LUT/GOLDEN_DAYLIGHT_CINEMA.cube is standalone: it includes the log decode,
gamut conversion, grade and SDR encoding. Do not apply another log-to-709
conversion before or after it. Apply it once.

BLACKMAGIC CAMERA ON IPHONE (not tested on a physical phone):
1. Download and save the .cube to Files; or extract the ZIP and find the .cube.
2. Set the recording colour space to Apple Log 2 on a supported iPhone. Keep
   capture codec/other settings appropriate to your workflow.
3. Open the app's LUT settings, import the .cube via Files, select it and enable
   display LUT for monitoring. Menu names can differ between app versions.
4. Prefer monitor-only; leave recording/baking the LUT into the clip disabled if
   you want to retain log for post. If baking is enabled, do not apply it twice.
Blackmagic says its iOS camera supports 17- and 33-point 3D LUTs. Actual import,
monitoring colour management, playback and phone downloads have not been tested.

EXPOSURE AND LIMITS
Expose carefully for important highlights and avoid underexposing noisy shadows.
Lock or adjust white balance to suit the scene; this LUT cannot compensate for
unknown light or exposure. Apple Log middle grey 0.18 is approximately code
0.4883 on a normalised full-range RGB signal. This is not a camera IRE target
or a substitute for false colour, camera-specific metering or on-device tests.

A LUT is pixel-only. It cannot measure depth, create halation, bloom or grain,
sharpen, denoise, smooth skin, or reconstruct clipped highlights. The available
colour depth is bounded by the input and a 33-point grid. The extensive visual
and device validation originally requested remains outstanding. In particular,
the current numerical tests expose interpolation errors, an extreme yellow
ramp reversal and some shadow-noise amplification; see the report. This package
is deliberately offered for evaluation rather than represented as completed
reference-grade proof.
