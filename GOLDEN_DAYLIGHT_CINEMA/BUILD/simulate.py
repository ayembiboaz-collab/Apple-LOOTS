"""
simulate.py -- simulated Apple Log 2 plates.

Apple Log 2 footage was NOT available (no iPhone 17 Pro / Blackmagic Camera in
this environment). The BEFORE/AFTER proofs therefore use a documented,
reversible simulation, clearly labelled as such in the gallery and report:

  1. Source plate (AI-generated photorealistic plate, 8-bit sRGB PNG) is treated
     as a display-referred Rec.709 image.
  2. Display code -> scene-linear Rec.709 (`scene_referred_expand`), which
     *re-opens* highlight headroom above reference white so the log curve has
     something to encode. This is the only invented step; the expansion is a
     smooth power curve, documented below and in the report.
  3. Rec.709 scene-linear -> Apple Wide Gamut scene-linear (inverse of the
     published-primaries matrix).
  4. Apple Log 2 transfer function encode -> 0..1 log code (Apple Wide Gamut).

The result is *Apple Log 2-encoded in the correct container*: the delivered LUT
decodes it with the real Apple Log curve and the real Apple Wide Gamut -> Rec.709
matrix. What cannot be simulated is an iPhone sensor's own response into that
space, so these plates must not be read as iPhone footage.
"""
import numpy as np

from apple_log2 import REC709_TO_AWG, apple_log_encode, srgb_decode, srgb_encode

HEADROOM = 3.0            # scene-linear value reached at sRGB white
SHOULDER_KNEE = 0.45      # display-linear value where highlight expansion starts
EXPOSURE_EV = 0.0         # global exposure offset used for the shipped renders


def scene_referred_expand(disp_lin):
    """Display-linear Rec.709 -> scene-linear Rec.709 with highlight headroom.

    Below the knee the signal is passed through unchanged; above it a smooth
    cubic term lifts the top end to HEADROOM x white, so a bright plate still
    has 1.5-3 stops of recoverable texture for the tone curve to work with.
    Inverse-able in closed form for validation (`scene_to_display`).
    """
    d = np.clip(disp_lin, 0.0, 1.0)
    k = SHOULDER_KNEE
    t = np.clip((d - k) / (1.0 - k), 0.0, 1.0)
    lift = (HEADROOM - 1.0) * t ** 3
    return np.where(d <= k, d, d + lift * (1.0 - d * 0.0))


def plate_to_apple_log2(rgb_srgb, exposure_ev=EXPOSURE_EV):
    """sRGB PNG (0..1) -> simulated Apple Log 2 code (0..1), Apple Wide Gamut."""
    disp_lin = srgb_decode(np.asarray(rgb_srgb, dtype=np.float64))
    scene = scene_referred_expand(disp_lin) * (2.0 ** exposure_ev)
    awg = scene @ REC709_TO_AWG.T
    return np.clip(apple_log_encode(awg), 0.0, 1.0)


def apple_log2_to_plate(log_rgb):
    """Rough inverse, only for sanity checks of the simulator."""
    from apple_log2 import AWG_TO_REC709, apple_log_decode
    scene = apple_log_decode(log_rgb) @ AWG_TO_REC709.T
    scene = scene / (2.0 ** EXPOSURE_EV)
    return srgb_encode(scene)
