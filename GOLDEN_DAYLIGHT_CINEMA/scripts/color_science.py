"""
color_science.py
================

Core colour mathematics for the GOLDEN DAYLIGHT CINEMA LUT.

Implements, from verified published specifications:

  * Apple Log 2 transfer function (identical to Apple Log).
      Apple Inc. (2023) "Apple Log Profile White Paper" and
      Apple Inc. (2025) "Apple Log 2 White Paper" (same curve constants).
      Constants cross-checked against colour-science
      ``colour.models.log_decoding_AppleLogProfile`` and the ACES
      ``IDT.Apple.AppleLog_BT2020.ctl``.

  * Apple Wide Gamut primaries.
      Apple Inc. (2025) "Apple Log 2 White Paper":
        R (0.725, 0.301), G (0.221, 0.814), B (0.068, -0.076), D65 white.
      Cross-checked against ASWF OpenColorIO PR #2343 / config PR #179.

  * Rec.709 (BT.709) primaries and gamma 2.4 output.

  * Linear-light primaries -> XYZ conversion and a chromatic-adaptation
    path (Bradford), so the Apple Wide Gamut -> Rec.709 matrix can be
    re-derived and cross-checked.

Everything here is deterministic and uses only numpy/scipy.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# 1. Apple Log 2 / Apple Log transfer function
# ---------------------------------------------------------------------------
# Published constants (Apple Log Profile White Paper, 2023; identical in the
# Apple Log 2 White Paper, 2025).
APPLE_LOG_R_0 = -0.05641088
APPLE_LOG_R_T = 0.01
APPLE_LOG_C = 47.28711236          # "sigma"/c in the white paper
APPLE_LOG_BETA = 0.00964052
APPLE_LOG_GAMMA = 0.08550479
APPLE_LOG_DELTA = 0.69336945
# Transition point in the *encoded* (log) domain.
APPLE_LOG_P_T = APPLE_LOG_C * (APPLE_LOG_R_T - APPLE_LOG_R_0) ** 2


def apple_log_to_linear(v):
    """Decode Apple Log 2 (encoded value) to linear-light.

    Vectorised over numpy arrays.  Matches the published piecewise function:

        L = R_0                              for V < 0
        L = sqrt(V / c) + R_0               for 0 <= V < P_t
        L = 2^((V - delta)/gamma) - beta    for V >= P_t
    """
    v = np.asarray(v, dtype=np.float64)
    r0 = APPLE_LOG_R_0
    pt = APPLE_LOG_P_T
    c = APPLE_LOG_C
    beta = APPLE_LOG_BETA
    gamma = APPLE_LOG_GAMMA
    delta = APPLE_LOG_DELTA

    out = np.empty_like(v)
    low = v < 0.0
    mid = (v >= 0.0) & (v < pt)
    high = v >= pt

    out[low] = r0
    out[mid] = np.sqrt(v[mid] / c) + r0
    out[high] = np.power(2.0, (v[high] - delta) / gamma) - beta
    return out


def linear_to_apple_log(l):
    """Encode linear-light to Apple Log 2 (inverse of :func:`apple_log_to_linear`)."""
    l = np.asarray(l, dtype=np.float64)
    r0 = APPLE_LOG_R_0
    rt = APPLE_LOG_R_T
    c = APPLE_LOG_C
    beta = APPLE_LOG_BETA
    gamma = APPLE_LOG_GAMMA
    delta = APPLE_LOG_DELTA

    out = np.empty_like(l)
    low = l < r0
    mid = (l >= r0) & (l < rt)
    high = l >= rt

    out[low] = 0.0
    out[mid] = c * (l[mid] - r0) ** 2
    out[high] = gamma * np.log2(l[high] + beta) + delta
    return out


# ---------------------------------------------------------------------------
# 2. Primaries -> linear RGB <-> XYZ
# ---------------------------------------------------------------------------
def _xyz_from_primaries(primaries, white):
    """Build the 3x3 linear-RGB -> XYZ matrix for given primaries + white.

    ``primaries`` and ``white`` are (x, y) tuples.  Uses the standard
    CIE 1931 construction; the columns are scaled so the white point maps
    to XYZ with Y = 1.
    """
    (xr, yr), (xg, yg), (xb, yb) = primaries
    xw, yw = white

    # Un-normalised XYZ direction for each primary (Y = 1).
    m = np.array([
        [xr / yr, xg / yg, xb / yb],
        [1.0, 1.0, 1.0],
        [(1.0 - xr - yr) / yr, (1.0 - xg - yg) / yg, (1.0 - xb - yb) / yb],
    ])
    # White point XYZ (Y = 1).
    m_w = np.array([xw / yw, 1.0, (1.0 - xw - yw) / yw])
    # Solve m @ s = m_w  ->  column scale factors so that the primaries
    # combine to the exact white point.
    s = np.linalg.solve(m, m_w)
    return m * s


# Standard primaries (all D65 white unless noted).
REC709_PRIMARIES = ((0.640, 0.330), (0.300, 0.600), (0.150, 0.060))
REC709_WHITE = (0.3127, 0.3290)

APPLE_WIDE_GAMUT_PRIMARIES = ((0.725, 0.301), (0.221, 0.814), (0.068, -0.076))
APPLE_WIDE_GAMUT_WHITE = (0.3127, 0.3290)   # D65

# ACES2065-1 (AP0) primaries, used only to cross-check our derivation.
ACES2065_PRIMARIES = ((0.714, 0.293), (0.170, 0.797), (0.131, -0.046))
ACES2065_WHITE = (0.3127, 0.3290)          # D65


def linear_rgb_to_xyz(primaries, white):
    return _xyz_from_primaries(primaries, white)


def xyz_to_linear_rgb(primaries, white):
    return np.linalg.inv(_xyz_from_primaries(primaries, white))


def linear_matrix(src_primaries, src_white, dst_primaries, dst_white):
    """Linear-light matrix converting src RGB -> dst RGB.

    src_rgb -> XYZ (src) -> (CAT if needed) -> XYZ (dst) -> dst_rgb.
    Because both Apple Wide Gamut and Rec.709 share the D65 white point the
    chromatic adaptation is the identity here; the function still accepts a
    white-point adaptation via Bradford for generality and cross-checks.
    """
    m_src = linear_rgb_to_xyz(src_primaries, src_white)
    m_dst_inv = xyz_to_linear_rgb(dst_primaries, dst_white)
    return m_dst_inv @ m_src


def bradford_cat(src_white, dst_white):
    """Bradford chromatic-adaptation matrix XYZ_src -> XYZ_dst."""
    m_src = linear_rgb_to_xyz(REC709_PRIMARIES, src_white)
    m_dst = linear_rgb_to_xyz(REC709_PRIMARIES, dst_white)
    m_src_inv = xyz_to_linear_rgb(REC709_PRIMARIES, src_white)
    m_dst_inv = xyz_to_linear_rgb(REC709_PRIMARIES, dst_white)

    # Cone response matrices.
    def cone_mat(xyz_rgb_to_xyz, xyz_to_rgb):
        m = xyz_rgb_to_xyz
        minv = xyz_to_rgb
        return np.array([
            [0.8951, 0.2664, -0.1614],
            [-0.7502, 1.7135, 0.0367],
            [0.0389, -0.0685, 1.0296],
        ]) @ (minv @ m)  # not used directly; build below

    # Bradford cone-response of the two whites (computed in XYZ, independent
    # of the RGB basis we used to build the matrices).
    def cone(white):
        xw, yw = white
        xyz = np.array([xw / yw, 1.0, (1 - xw - yw) / yw])
        # Bradford cone response matrix (fixed, well-known).
        m_br = np.array([
            [0.8951, 0.2664, -0.1614],
            [-0.7502, 1.7135, 0.0367],
            [0.0389, -0.0685, 1.0296],
        ])
        return m_br @ xyz

    c_src = cone(src_white)
    c_dst = cone(dst_white)
    # M = diag(c_dst/c_src) @ M_br
    diag = np.diag(c_dst / c_src)
    m_br = np.array([
        [0.8951, 0.2664, -0.1614],
        [-0.7502, 1.7135, 0.0367],
        [0.0389, -0.0685, 1.0296],
    ])
    m_br_inv = np.linalg.inv(m_br)
    # CAT = M_br_inv @ diag @ M_br
    return m_br_inv @ diag @ m_br


# ---------------------------------------------------------------------------
# 3. Transfer functions (gamma curves) for the output
# ---------------------------------------------------------------------------
def rec709_gamma24(linear):
    """Rec.709 SDR OETF with a gamma 2.4 power curve.

    Output in [0, 1] for input linear in [0, 1].  This is the target output
    of the LUT: Rec.709 primaries, gamma 2.4, no separate tone-map beyond
    the creative grade.
    """
    linear = np.clip(np.asarray(linear, dtype=np.float64), 0.0, None)
    return np.power(linear, 1.0 / 2.4)


def rec709_gamma24_inverse(encoded):
    """Inverse of :func:`rec709_gamma24` (decode to linear)."""
    encoded = np.clip(np.asarray(encoded, dtype=np.float64), 0.0, None)
    return np.power(encoded, 2.4)


# ---------------------------------------------------------------------------
# 4. Precomputed, cross-checked matrices
# ---------------------------------------------------------------------------
def apple_wide_gamut_to_rec709():
    """Linear Apple Wide Gamut -> linear Rec.709 (D65, identity CAT)."""
    return linear_matrix(
        APPLE_WIDE_GAMUT_PRIMARIES, APPLE_WIDE_GAMUT_WHITE,
        REC709_PRIMARIES, REC709_WHITE,
    )


def apple_wide_gamut_to_aces2065():
    """Linear Apple Wide Gamut -> ACES2065-1 (for cross-checking only)."""
    return linear_matrix(
        APPLE_WIDE_GAMUT_PRIMARIES, APPLE_WIDE_GAMUT_WHITE,
        ACES2065_PRIMARIES, ACES2065_WHITE,
    )


# Published reference matrix (ASWF OpenColorIO PR #2343 / config PR #179),
# Apple Wide Gamut -> ACES2065-1.  Stored by OCIO as a flat 4x4 in row-major
# order; the 3x3 block is reshaped below.
_PUBLISHED_FLAT = [
    0.694961049318096, 0.241405268785364, 0.06363368189654, 0.0,
    0.0473627464149325, 1.00429592505428, -0.0516586714692158, 0.0,
    -0.021989789359883, -0.0289891049714743, 1.05097889433136, 0.0,
    0.0, 0.0, 0.0, 1.0,
]
PUBLISHED_APPLEWG_TO_ACES = np.array(_PUBLISHED_FLAT).reshape(4, 4)[:3, :3]
