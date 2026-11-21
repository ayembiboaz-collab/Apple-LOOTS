"""
Simulated Apple Log 2 source generation.

No genuine iPhone 17 Pro Apple Log 2 footage was available in this
environment, so every "BEFORE" frame in this project is a SIMULATED Apple Log 2
frame derived from a real Rec.709/SDR photograph.  The simulation is fully
documented and reversible:

  1. Decode the photograph with the sRGB/Rec.709 transfer function to linear
     Rec.709 light.  The value is treated as scene reflectance with
     100% reflectance = SDR code 1.0 (this is the documented assumption).
  2. Convert linear Rec.709 -> CIE XYZ (D65) -> linear Apple Wide Gamut, the
     gamut Apple Log 2 records in.
  3. Encode with Apple's published Apple Log 2 encoding function
     (GAMMA*log2(R+BETA)+DELTA above Rt, parabolic toe below).

This produces valid Apple Log 2 code values that decode back to the original
scene light through the published decoding function.  It reproduces the
*encode* side of the camera exactly; it does not reproduce the iPhone sensor,
lens, tone processing, noise or demosaic, and it carries no highlight
information above diffuse white because the SDR source has none.
"""

from __future__ import annotations

import numpy as np

import apple_log2 as al


def srgb_image_to_scene_709(rgb_u8):
    """8-bit sRGB image -> linear Rec.709 scene values (100% white = 1.0)."""
    v = np.asarray(rgb_u8, dtype=np.float64) / 255.0
    return al.srgb_to_linear(v)


def scene709_to_applewidegamut(scene_709):
    xyz = scene_709 @ al.REC709_TO_XYZ.T
    return xyz @ al.XYZ_TO_APPLEWG.T


def simulate_apple_log2(rgb_u8):
    """8-bit sRGB photograph -> (log2 code image, scene linear Rec.709)."""
    scene_709 = srgb_image_to_scene_709(rgb_u8)
    scene_awg = scene709_to_applewidegamut(scene_709)
    code = al.encode(scene_awg)
    return np.clip(code, 0.0, 1.0), scene_709


def neutral_render(scene_709):
    """Neutral Rec.709 gamma 2.4 rendering of the scene (no creative grade)."""
    return al.rec709_gamma24_encode(np.clip(scene_709, 0.0, None))
