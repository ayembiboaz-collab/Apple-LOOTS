"""
simulate_log2.py — build DOCUMENTED SIMULATED Apple Log 2 frames from sRGB
source stills.

!!  IMPORTANT HONESTY NOTE  !!
These frames are SIMULATED. They are NOT iPhone 17 Pro sensor captures and do
not reproduce Apple's upstream sensor characterisation, demosaic, noise
reduction or ISP colour science. They exercise the delivered LUT over a
realistic Apple Log 2 signal range so the grade can be judged; they are not
evidence of how a real iPhone file behaves.

SIMULATION CHAIN (every step is explicit and reproducible)
----------------------------------------------------------
1.  Source 8-bit PNG, interpreted as sRGB (IEC 61966-2-1), -> display-linear.
2.  Inverse camera rendering -> scene-linear, D65 Rec.709 primaries:
      a) the sRGB display-linear value is treated as the output of a standard
         BT.709 camera rendering, inverted analytically via the inverse
         BT.709 OETF applied to the sRGB code value. This anchors
         BT.709 code 0.4137 (sRGB ~0.4167) to 18 % scene reflectance.
      b) a smooth HIGHLIGHT EXPANSION above code `hl_knee` re-spreads the
         compressed top end over `hl_stops` stops of scene-referred
         headroom. This DOES NOT invent texture: areas that are clipped flat
         in the source stay flat. It only places them at a plausible
         scene-referred level so the LUT's shoulder is genuinely exercised.
3.  scene-linear Rec.709 (D65) -> scene-linear Apple Wide Gamut (D65) by the
    inverse of the matrix derived from Apple's published primaries. No
    chromatic adaptation: both spaces are D65.
4.  Apple Log encode (Apple Log Profile White Paper constants) -> P in [0,1].
5.  Quantise to 10 bits full range, which is what Apple Log 2 records in
    ProRes and HEVC, then store as 16-bit PNG.

An `exposure_ev` offset can be applied at step 2 to produce the
under/over-exposed stress variants used in the validation report.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

from applelog2 import (
    REC709_TO_AWG,
    apple_log_encode,
    apply_matrix,
    srgb_eotf,
)

# BT.709 OETF constants (ITU-R BT.709-6)
_A, _B, _C = 1.099, 0.099, 4.5
_CUT = 0.018


def bt709_oetf_inverse(V):
    """BT.709 OETF code value -> scene-linear."""
    V = np.asarray(V, dtype=np.float64)
    lin_seg = V / _C
    log_seg = ((np.maximum(V, 0.0) + _B) / _A) ** (1.0 / 0.45)
    return np.where(V < _C * _CUT, lin_seg, log_seg)


def highlight_expand(lin, knee_lin, stops):
    """Smoothly re-spread the top of a clipped rendering over `stops` of
    scene-referred headroom, starting at `knee_lin`.

    Below the knee the mapping is the identity; at and above it the curve is
    C1-continuous and asymptotes at knee * 2**stops.
    """
    lin = np.asarray(lin, dtype=np.float64)
    top = bt709_oetf_inverse(1.0)  # scene-linear at source code 1.0
    if knee_lin >= top:
        return lin
    target = knee_lin * (2.0**stops)
    span = target - knee_lin
    # x in [0, 1] across the compressed source range above the knee
    x = np.clip((lin - knee_lin) / (top - knee_lin), 0.0, 1.0)
    # Expansion curve: starts with gradient 1 in source units, accelerates.
    k = span / (top - knee_lin)
    shaped = x * (1.0 + (k - 1.0) * x * x * (3.0 - 2.0 * x))
    return np.where(lin <= knee_lin, lin, knee_lin + shaped * (top - knee_lin))


def srgb_to_scene_linear(srgb_code, exposure_ev=0.0, hl_knee_code=0.80, hl_stops=2.35):
    """sRGB code values in [0,1] -> scene-linear Rec.709 (0.18 = 18 % grey)."""
    srgb_code = np.clip(np.asarray(srgb_code, dtype=np.float64), 0.0, 1.0)
    lin = bt709_oetf_inverse(srgb_code)
    knee_lin = float(bt709_oetf_inverse(hl_knee_code))
    lin = highlight_expand(lin, knee_lin, hl_stops)
    return lin * (2.0**exposure_ev)


def scene_linear_to_log2(lin_709, quantise_bits=10):
    """scene-linear Rec.709 (D65) -> Apple Log 2 normalised signal P."""
    lin_awg = apply_matrix(lin_709, REC709_TO_AWG)
    P = apple_log_encode(lin_awg)
    P = np.clip(P, 0.0, 1.0)
    if quantise_bits:
        levels = 2**quantise_bits - 1
        P = np.round(P * levels) / levels
    return P


def simulate_file(src_path, exposure_ev=0.0, quantise_bits=10):
    img = Image.open(src_path).convert("RGB")
    arr = np.asarray(img, dtype=np.float64) / 255.0
    lin = srgb_to_scene_linear(arr, exposure_ev=exposure_ev)
    return scene_linear_to_log2(lin, quantise_bits=quantise_bits), img.size


def save_log2(P, path):
    """Store the simulated Apple Log 2 signal losslessly as float32 .npy.

    PIL cannot write 16-bit-per-channel RGB PNG, and 8 bits would throw away
    the 10-bit precision the simulation models, so the working intermediate is
    kept as raw float. The 8-bit BEFORE previews are rendered from this array.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.save(path, np.clip(P, 0.0, 1.0).astype(np.float32))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_dir = os.path.join(root, "sources")
    out_dir = os.path.join(root, "work", "simulated_log2")
    os.makedirs(out_dir, exist_ok=True)

    names = sorted(f for f in os.listdir(src_dir) if f.lower().endswith(".png"))
    for n in names:
        P, size = simulate_file(os.path.join(src_dir, n))
        out = os.path.join(out_dir, n.replace(".png", "_LOG2.npy"))
        save_log2(P, out)
        print(
            f"{n:34s} {size[0]}x{size[1]}  P range [{P.min():.4f}, {P.max():.4f}]  "
            f"mean {P.mean():.4f}  -> {os.path.relpath(out, root)}"
        )


if __name__ == "__main__":
    main()
