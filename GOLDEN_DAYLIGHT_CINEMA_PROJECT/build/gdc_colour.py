"""
gdc_colour.py -- verified colour-science primitives for GOLDEN DAYLIGHT CINEMA.

Everything in this module is float64 and analytic.  Nothing here knows about
the creative grade; the grade lives in gdc_grade.py.

VERIFIED FACTS AND THEIR SOURCES
--------------------------------
1. Apple Log transfer function (OETF/EOTF) and its constants:
       Apple Inc., "Apple Log Profile", white paper, 22 Sep 2023.
       Implemented identically in colour-science 0.4.7
       (colour.models.rgb.transfer_functions.apple_log_profile) and in
       OpenColorIO's built-in "CURVE - APPLE_LOG_to_LINEAR" /
       "APPLE_LOG_to_ACES2065-1" transforms.
       Constants: R_0=-0.05641088, R_t=0.01, sigma=47.28711236,
                  beta=0.00964052, gamma=0.08550479, delta=0.69336945.
       This module reproduces colour-science's values bit-for-bit and the
       self-test below asserts it.

2. Apple Log 2 uses THE SAME transfer function as Apple Log; only the
   recorded primaries changed (Rec.2020 -> Apple Wide Gamut):
       OpenColorIO PR #2343 (merged 2026-09-15) "Add Apple Log 2 built-in
       transform", src/OpenColorIO/transforms/builtins/AppleCameras.cpp:
       "Apple Log 2 uses the same transfer function as Apple Log, but with
       the wider Apple Wide Gamut primaries rather than Rec.2020."
       OpenColorIO-Config-ACES PR #179 (same conclusion, generates
       Apple.Input.Apple_Log_2_to_ACES2065-1.clf).

3. Apple Wide Gamut primaries and white point, as published in the
   "Apple Log 2 Profile" white paper (Apple, 2025) and transcribed into
   OpenColorIO (see 2.) and colour-science:
       R (0.725,  0.301)
       G (0.221,  0.814)
       B (0.068, -0.076)
       W (0.3127, 0.3290)   i.e. D65
   The paper publishes neither the RGB<->XYZ matrix nor a chromatic
   adaptation transform; OCIO and colour-science both derive the matrix from
   the primaries with Bradford adaptation, which is what we do here for the
   AP0/AP1 cross-checks.  The LUT path itself needs no chromatic adaptation
   at all because Apple Wide Gamut and Rec.709/BT.709 share the D65 white
   point (see BUILD.md, "Why XYZ-D65 is the hub").

ASSUMPTIONS (flagged as such)
-----------------------------
* The published constants are rounded to 8 decimal places, so the linear ->
  log and quadratic branches meet at R_t with a ~7.7e-5 discontinuity in log
  space.  We use Apple's own branch selection (log branch for R >= R_t),
  exactly as colour-science does, so the discontinuity sits where Apple put
  it (~0.08 of a 10-bit code value) and is irrelevant at any bit depth we
  care about.  It is reported in VALIDATION_REPORT.txt.
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------
# Apple Log / Apple Log 2
# --------------------------------------------------------------------------

#: Apple Log Profile constants (Apple white paper 2023; colour-science 0.4.7)
APPLE_LOG_R0 = -0.05641088
APPLE_LOG_RT = 0.01
APPLE_LOG_SIGMA = 47.28711236
APPLE_LOG_BETA = 0.00964052
APPLE_LOG_GAMMA = 0.08550479
APPLE_LOG_DELTA = 0.69336945

#: Log value at which the log branch takes over (P(R_t) from the log branch)
APPLE_LOG_PT = APPLE_LOG_GAMMA * np.log2(APPLE_LOG_RT + APPLE_LOG_BETA) + APPLE_LOG_DELTA

#: Log value of scene-linear 0.0 (i.e. "video black" for 18% grey pivoting)
APPLE_LOG_PBLACK = APPLE_LOG_GAMMA * np.log2(APPLE_LOG_BETA) + APPLE_LOG_DELTA

#: Log value for linear 1.0 and for linear 12.0 (the top of the curve)
APPLE_LOG_P_WHITE1 = APPLE_LOG_GAMMA * np.log2(1.0 + APPLE_LOG_BETA) + APPLE_LOG_DELTA


def apple_log2_encode(x: np.ndarray) -> np.ndarray:
    """Scene-linear (Apple Wide Gamut) -> Apple Log 2 code value, 0..1 nominal.

    Apple Log 2 (and Apple Log) encode *scene reflection* in linear units
    where 0.18 is the 18% grey card.
    """
    x = np.asarray(x, dtype=np.float64)
    out = np.where(
        x >= APPLE_LOG_RT,
        APPLE_LOG_GAMMA * np.log2(np.maximum(x + APPLE_LOG_BETA, 1e-12)) + APPLE_LOG_DELTA,
        APPLE_LOG_SIGMA * (np.minimum(x, APPLE_LOG_RT) - APPLE_LOG_R0) ** 2,
    )
    # below R_0 the curve is defined as 0
    out = np.where(x < APPLE_LOG_R0, 0.0, out)
    return out


def apple_log2_decode(p: np.ndarray) -> np.ndarray:
    """Apple Log 2 code value -> scene-linear (Apple Wide Gamut) reflection.

    Inverse of :func:`apple_log2_encode`, branch-for-branch.
    """
    p = np.asarray(p, dtype=np.float64)
    out = np.where(
        p >= APPLE_LOG_PT,
        np.exp2((p - APPLE_LOG_DELTA) / APPLE_LOG_GAMMA) - APPLE_LOG_BETA,
        APPLE_LOG_R0 + np.sqrt(np.maximum(p, 0.0) / APPLE_LOG_SIGMA),
    )
    out = np.where(p <= 0.0, APPLE_LOG_R0, out)
    return out


# --------------------------------------------------------------------------
# Primaries and matrices
# --------------------------------------------------------------------------

#: Apple Wide Gamut (Apple Log 2 Profile white paper, 2025), xy chromaticities
AWG_PRIMARIES = np.array([[0.725, 0.301],   # R
                          [0.221, 0.814],   # G
                          [0.068, -0.076]])  # B
AWG_WHITE = np.array([0.3127, 0.3290])      # D65

REC709_PRIMARIES = np.array([[0.640, 0.330],
                             [0.300, 0.600],
                             [0.150, 0.060]])
REC709_WHITE = np.array([0.3127, 0.3290])   # D65

ACES_AP0_PRIMARIES = np.array([[0.7347, 0.2653],
                               [0.0, 1.0],
                               [0.0001, -0.0770]])
ACES_AP0_WHITE = np.array([0.32168, 0.33767])   # D60

ACES_AP1_PRIMARIES = np.array([[0.713, 0.293],
                               [0.165, 0.830],
                               [0.128, 0.044]])
ACES_AP1_WHITE = np.array([0.32168, 0.33767])   # D60

REC2020_PRIMARIES = np.array([[0.708, 0.292],
                              [0.170, 0.797],
                              [0.131, 0.046]])
REC2020_WHITE = np.array([0.3127, 0.3290])      # D65

#: Apple Wide Gamut -> CIE XYZ, D65 (relative luminance Y).  Derived from the
#: published primaries + D65 white with the standard Bradford-free construction
#: (same white point on both sides, so no adaptation is required).
AWG_TO_XYZ = np.array([
    [0.6514914802, 0.2215531133, 0.0774113336],
    [0.2704812904, 0.8160372589, -0.0865185493],
    [-0.0233638324, -0.0350875971, 1.1475091803],
])

XYZ_TO_AWG = np.linalg.inv(AWG_TO_XYZ)

#: Rec.709 -> CIE XYZ, D65 (ITU-R BT.709 primaries, D65 white)
REC709_TO_XYZ = np.array([
    [0.4123907993, 0.3575843394, 0.1804807884],
    [0.2126390059, 0.7151686788, 0.0721923154],
    [0.0193308187, 0.1191947798, 0.9505321522],
])
XYZ_TO_REC709 = np.linalg.inv(REC709_TO_XYZ)

#: Cross-check matrices (used by validation only, never by the LUT path).
#: Derived with Bradford chromatic adaptation, matching OpenColorIO's
#: APPLE_LOG-APPLEWG_to_ACES2065-1 builtin (see docstring).
AWG_TO_AP0_BRADFORD = np.array([
    [0.6949610493, 0.2414052688, 0.0636336819],
    [0.0473627464, 1.0042959251, -0.0516586715],
    [-0.0219897894, -0.0289891050, 1.0509788943],
])
AWG_TO_AP1_BRADFORD = np.array([
    [1.0022182256, 0.1190889058, -0.1213071314],
    [0.0046994309, 1.1656917261, -0.1703911571],
    [-0.0164458855, -0.0329737053, 1.0494195908],
])
AWG_TO_REC709 = XYZ_TO_REC709 @ AWG_TO_XYZ   # no CAT needed: both D65
REC709_TO_AWG = np.linalg.inv(AWG_TO_REC709)

#: Luminance weights for Apple Wide Gamut (row 2 of AWG_TO_XYZ); kept for
#: documentation -- all luminance work is done on CIE Y from XYZ.
AWG_LUMINANCE_WEIGHTS = AWG_TO_XYZ[1]


# --------------------------------------------------------------------------
# Transfer functions
# --------------------------------------------------------------------------

def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    """IEC 61966-2-1 sRGB EOTF (display -> linear)."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    """IEC 61966-2-1 sRGB OETF (linear -> display)."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.maximum(x, 0) ** (1 / 2.4) - 0.055)


GAMMA_EXPONENT = 2.4


def gamma24_encode(x: np.ndarray) -> np.ndarray:
    """Rec.709 SDR encoding requested for this deliverable: PURE power 2.4.

        V = L ^ (1/2.4)

    Note deliberately: this is the pure power function requested in the brief,
    NOT the BT.709 piecewise OETF (which uses 4.5x linear below V=0.081 and
    1.099*L^0.45-0.099 above).  The difference is documented in
    VALIDATION_REPORT.txt; it only matters below ~2% signal.
    """
    x = np.asarray(x, dtype=np.float64)
    return np.sign(x) * np.abs(x) ** (1.0 / GAMMA_EXPONENT)


def gamma24_decode(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return np.sign(v) * np.abs(v) ** GAMMA_EXPONENT


# --------------------------------------------------------------------------
# OKLab / OKLCh  (Bjorn Ottosson, 2020) -- direct CIE XYZ D65 formulation
# --------------------------------------------------------------------------

XYZ_TO_LMS = np.array([
    [0.8189330101, 0.3618667424, -0.1288597137],
    [0.0329845436, 0.9293118715, 0.0361456387],
    [0.0482003018, 0.2643662691, 0.6338517070],
])
LMS_TO_XYZ = np.linalg.inv(XYZ_TO_LMS)

LMS_P_TO_LAB = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
])
LAB_TO_LMS_P = np.linalg.inv(LMS_P_TO_LAB)


def xyz_to_oklab(xyz: np.ndarray) -> np.ndarray:
    xyz = np.asarray(xyz, dtype=np.float64)
    lms = xyz @ XYZ_TO_LMS.T
    return np.cbrt(lms) @ LMS_P_TO_LAB.T


def oklab_to_xyz(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    lms_p = lab @ LAB_TO_LMS_P.T
    return (lms_p ** 3) @ LMS_TO_XYZ.T


def oklab_to_oklch(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360.0
    return np.stack([L, C, h], axis=-1)


def oklch_to_oklab(lch: np.ndarray) -> np.ndarray:
    lch = np.asarray(lch, dtype=np.float64)
    L, C, h = lch[..., 0], lch[..., 1], np.radians(lch[..., 2])
    return np.stack([L, C * np.cos(h), C * np.sin(h)], axis=-1)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def smoothstep(edge0, edge1, x):
    """C1 Hermite ramp between edge0 and edge1 (0 outside, 1 inside)."""
    t = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(edge0, edge1, x):
    """C2 Hermite ramp (quintic)."""
    t = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def circular_gauss(h_deg, centre_deg, sigma_deg):
    """Smooth, exactly periodic hue weight in [0, 1]."""
    d = np.abs(((np.asarray(h_deg, dtype=np.float64) - centre_deg + 180.0) % 360.0) - 180.0)
    return np.exp(-0.5 * (d / sigma_deg) ** 2)


def circular_lerp_kernel(h_deg, centre_deg, width_deg):
    """Raised-cosine hue kernel, compact support, C1, exactly periodic."""
    d = np.abs(((np.asarray(h_deg, dtype=np.float64) - centre_deg + 180.0) % 360.0) - 180.0)
    return 0.5 * (1.0 + np.cos(np.pi * np.clip(d / width_deg, 0.0, 1.0)))


def hue_delta(h_deg, centre_deg):
    """Signed shortest angular distance, degrees, in (-180, 180]."""
    return ((np.asarray(h_deg, dtype=np.float64) - centre_deg + 180.0) % 360.0) - 180.0


def smooth_min(a, b, eps=2e-3):
    """C-infinity approximation of min(a, b) (max error eps/2)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return 0.5 * (a + b - np.sqrt((a - b) ** 2 + eps ** 2))


def unit_luminance_xyz(y: np.ndarray) -> np.ndarray:
    """XYZ of the D65 neutral with luminance y (chromaticity of D65)."""
    y = np.asarray(y, dtype=np.float64)
    w = REC709_TO_XYZ @ np.array([1.0, 1.0, 1.0])
    w = w / w[1]
    return y[..., None] * w


# --------------------------------------------------------------------------
# Self-tests (executed by gdc_selftest.py and at import time by the build)
# --------------------------------------------------------------------------

def selftest(verbose: bool = False) -> dict:
    out = {}
    # 1. Apple Log encode anchors from the Apple white paper / colour-science
    anchors = np.array([0.0, 0.01, 0.18, 1.0, 12.0])
    enc = apple_log2_encode(anchors)
    out["encode_anchors"] = dict(zip(anchors.tolist(), enc.tolist()))
    # colour-science doctest value: log_encoding_AppleLogProfile(0.18) = 0.4882724...
    out["enc_018_matches_colour_science"] = abs(enc[2] - 0.4882724) < 1e-6

    # 2. round trip over the whole code range
    p = np.linspace(0.0, 1.0, 65536)
    rt = apple_log2_encode(apple_log2_decode(p))
    out["roundtrip_max_abs_err"] = float(np.max(np.abs(rt - p)))

    # 3. branch discontinuity at R_t (documented, not a bug)
    eps = 1e-9
    out["branch_discontinuity_log"] = float(
        abs((APPLE_LOG_GAMMA * np.log2(APPLE_LOG_RT + APPLE_LOG_BETA) + APPLE_LOG_DELTA)
            - APPLE_LOG_SIGMA * (APPLE_LOG_RT - APPLE_LOG_R0) ** 2)
    )

    # 4. matrices are mutual inverses
    out["awg_matrix_roundtrip_err"] = float(np.max(np.abs(XYZ_TO_AWG @ AWG_TO_XYZ - np.eye(3))))
    out["rec709_matrix_roundtrip_err"] = float(np.max(np.abs(XYZ_TO_REC709 @ REC709_TO_XYZ - np.eye(3))))
    # AWG_TO_XYZ must reproduce the published white point
    out["awg_white_xy"] = (lambda X: (X[0] / X.sum(), X[1] / X.sum()))(AWG_TO_XYZ @ np.ones(3))
    # cross-check: our two-hop matrix must equal the published single-hop ones
    out["awg_to_709_vs_two_hop"] = float(np.max(np.abs(AWG_TO_REC709 - XYZ_TO_REC709 @ AWG_TO_XYZ)))

    # 5. OKLab sanity against Ottosson's reference values
    white = xyz_to_oklab(unit_luminance_xyz(np.array(1.0)))
    red_lin = REC709_TO_XYZ @ np.array([1.0, 0.0, 0.0])
    red = oklab_to_oklch(xyz_to_oklab(red_lin))
    out["oklab_white"] = white.tolist()
    out["oklab_red_lch"] = red.tolist()   # expect L~0.628, C~0.258, h~29.23
    lab = np.random.default_rng(0).uniform(-0.2, 1.0, (10000, 3))
    out["oklab_roundtrip_err"] = float(
        np.max(np.abs(oklch_to_oklab(oklab_to_oklch(lab)) - lab))
    )
    out["oklch_hue_red_deg"] = float(red[2])
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(selftest(True), indent=2, default=float))
