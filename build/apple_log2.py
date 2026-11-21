"""
Apple Log 2 / Apple Wide Gamut  ->  Rec.709 (gamma 2.4) colour science.

Primary source (verified, official):
  Apple Inc., "Apple Log 2 — White Paper", September 2025, Version 1.1,
  part 028-00834.  Transfer-function constants and Apple Wide Gamut
  chromaticities are transcribed verbatim from that document (section
  "Transfer function" / "Apple Wide Gamut").

Cross-check (independent implementation):
  OpenColorIO PR #2343, "Add Apple Log 2 built-in transform", merged
  2026-09-15, registers APPLE_LOG-APPLEWG_to_ACES2065-1: it uses the Apple
  Log curve unchanged plus the Apple Wide Gamut primaries, converting with
  a Bradford-adapted primary matrix (build_conversion_matrix).  OpenColorIO
  Config ACES PR #179 repeats the same primaries.

Notes
-----
* Apple Log 2 keeps the *Apple Log* transfer function and replaces the
  Rec.2020 gamut of Apple Log with "Apple Wide Gamut".  Everything below is
  therefore curve-identical to Apple Log, gamut-different.
* Both Apple Wide Gamut and Rec.709 are defined against a D65 white point,
  so the gamut conversion needs no chromatic adaptation.  A Bradford
  adaptation matrix is still computed and applied for generality; for these
  two spaces it evaluates to the identity (verified in tests).
* Values are full-range, normalised 0..1 for the encoded signal, as the
  white paper specifies for the captured pixel value P.
"""

from __future__ import annotations

import numpy as np

# ----------------------------------------------------------------------------
# 1. Apple Log transfer function (identical for Apple Log and Apple Log 2)
#    Apple Log 2 White Paper (Sept 2025) v1.1, p.5
# ----------------------------------------------------------------------------
R0 = -0.05641088     # black / parabola join point (scene reflection)
Rt = 0.01            # logarithmic <-> parabolic threshold
C = 47.28711236      # parabola coefficient
BETA = 0.00964052    # log offset
GAMMA = 0.08550479   # log scale
DELTA = 0.69336945   # log offset

PT = C * (Rt - R0) ** 2   # encoded value of the join point (white paper: Pt)

# Documented anchors from the white paper, used by the test-suite.
WP_STOPS_TABLE = {          # stops from 18% grey -> floating point output
    -12: 0.15, -9: 0.15, -6: 0.17, -3: 0.28, 0: 0.49, 3: 0.75, 6: 1.0,
}
WP_REFLECTANCE_TABLE = {    # scene reflection % -> floating point output
    -5: 0.0, 0: 0.150477, 5: 0.345, 10: 0.42, 15: 0.47, 20: 0.5,
}
WP_ENCODED_SIGNAL = {       # scene reflection -> (float, 10-bit full range)
    0.0: (0.150477, 154),
    0.18: (0.488272, 500),
    0.90: (0.681686, 697),
    12.0: (1.0, 1023),
}


def encode(x):
    """Linear scene reflection -> Apple Log 2 code value (float 0..1)."""
    x = np.asarray(x, dtype=np.float64)
    out = np.where(
        x >= Rt,
        GAMMA * np.log2(np.maximum(x + BETA, 1e-12)) + DELTA,
        C * (x - R0) ** 2,
    )
    out = np.where(x >= R0, out, 0.0)
    return out


def decode(p, clip_negative=True):
    """Apple Log 2 code value -> linear scene reflection (Apple Wide Gamut).

    Negative scene values are preserved by the parabola branch: the real
    curve does not clip at black, it carries sensor noise below zero.  Callers
    that need non-negative light should clip *after* the gamut conversion.
    """
    p = np.asarray(p, dtype=np.float64)
    lin = np.where(
        p >= PT,
        np.power(2.0, (p - DELTA) / GAMMA) - BETA,
        np.sqrt(np.maximum(p, 0.0) / C) + R0,
    )
    lin = np.where(p >= 0.0, lin, R0)
    if clip_negative:
        lin = np.maximum(lin, R0)
    return lin


# ----------------------------------------------------------------------------
# 2. Primaries / matrices
# ----------------------------------------------------------------------------
# Apple Wide Gamut chromaticities — Apple Log 2 White Paper (Sept 2025), p.6
APPLE_WIDE_GAMUT = {
    "red":   (0.725, 0.301),
    "green": (0.221, 0.814),
    "blue":  (0.068, -0.076),
    "white": (0.3127, 0.3290),      # D65
}
# ITU-R BT.709 / Rec.709 primaries and D65 white
REC709 = {
    "red":   (0.640, 0.330),
    "green": (0.300, 0.600),
    "blue":  (0.150, 0.060),
    "white": (0.3127, 0.3290),      # D65
}

# CIE 1931 XYZ of D65 (used only for the adaptation matrix)
D65_XYZ = np.array([0.95047, 1.0, 1.08883])

BRADFORD = np.array([[0.8951, 0.2664, -0.1614],
                     [-0.7502, 1.7135, 0.0367],
                     [0.0389, -0.0685, 1.0296]])


def xy_to_XYZ(xy, Y=1.0):
    x, y = xy
    return np.array([x * Y / y, Y, (1.0 - x - y) * Y / y])


def rgb_to_xyz_matrix(prim):
    """RGB -> XYZ matrix from chromaticities (columns scaled to white)."""
    xr, yr = prim["red"]
    xg, yg = prim["green"]
    xb, yb = prim["blue"]
    xw, yw = prim["white"]
    M = np.array([[xr / yr, xg / yg, xb / yb],
                  [1.0, 1.0, 1.0],
                  [(1 - xr - yr) / yr, (1 - xg - yg) / yg, (1 - xb - yb) / yb]])
    white = np.array([xw / yw, 1.0, (1 - xw - yw) / yw])
    S = np.linalg.solve(M, white)
    return M * S[None, :]


def bradford(src_white_xy, dst_white_xy):
    """Bradford chromatic adaptation matrix src white -> dst white."""
    ws = xy_to_XYZ(src_white_xy)
    wd = xy_to_XYZ(dst_white_xy)
    src = BRADFORD @ ws
    dst = BRADFORD @ wd
    return np.linalg.inv(BRADFORD) @ np.diag(dst / src) @ BRADFORD


XYZ_TO_APPLEWG = np.linalg.inv(rgb_to_xyz_matrix(APPLE_WIDE_GAMUT))
APPLEWG_TO_XYZ = rgb_to_xyz_matrix(APPLE_WIDE_GAMUT)
XYZ_TO_REC709 = np.linalg.inv(rgb_to_xyz_matrix(REC709))
REC709_TO_XYZ = rgb_to_xyz_matrix(REC709)

# D65 -> D65: identity in theory; computed to prove it numerically.
AWG_TO_709 = XYZ_TO_REC709 @ bradford(APPLE_WIDE_GAMUT["white"], REC709["white"]) @ APPLEWG_TO_XYZ
# Apple Wide Gamut -> ACES2065-1 (AP0), the matrix OCIO's builtin bakes in.
ACES_AP0 = {
    "red": (0.7347, 0.2653), "green": (0.0, 1.0), "blue": (0.0001, -0.077),
    "white": (0.32168, 0.33767),   # ACES white
}
AWG_TO_AP0 = (np.linalg.inv(rgb_to_xyz_matrix(ACES_AP0))
              @ bradford(APPLE_WIDE_GAMUT["white"], ACES_AP0["white"])
              @ APPLEWG_TO_XYZ)


def applewg_to_rec709(lin_awg):
    return np.asarray(lin_awg) @ AWG_TO_709.T


# ----------------------------------------------------------------------------
# 3. Display encodings
# ----------------------------------------------------------------------------
def rec709_gamma24_encode(x):
    """Linear display light -> Rec.709 SDR code value (pure 1/2.4 gamma)."""
    x = np.maximum(np.asarray(x, dtype=np.float64), 0.0)
    return np.power(x, 1.0 / 2.4)


def rec709_gamma24_decode(v):
    v = np.maximum(np.asarray(v, dtype=np.float64), 0.0)
    return np.power(v, 2.4)


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.maximum(x, 1e-12), 1 / 2.4) - 0.055)


# ----------------------------------------------------------------------------
# 4. OKLab (Björn Ottosson, 2020) — used for hue-selective grading work
# ----------------------------------------------------------------------------
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050, 0.4505937099],
                [0.0259040371, 0.7827717662, -0.8086757660]])


def linear_rec709_to_oklab(rgb):
    lms = np.asarray(rgb) @ _M1.T
    lms = np.cbrt(np.maximum(lms, 1e-12))
    return lms @ _M2.T


def oklab_to_linear_rec709(lab):
    lms = np.asarray(lab) @ np.linalg.inv(_M2).T
    lms = lms ** 3
    return lms @ np.linalg.inv(_M1).T


def oklab_chroma_hue(lab):
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    return L, np.hypot(a, b), np.arctan2(b, a)


def set_oklab_chroma_hue(lab, chroma, hue):
    L = lab[..., 0]
    return np.stack([L, chroma * np.cos(hue), chroma * np.sin(hue)], axis=-1)


LUMA_REC709 = np.array([0.2126, 0.7152, 0.0722])
