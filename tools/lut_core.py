"""
GOLDEN DAYLIGHT CINEMA - core colour math.

Shared by build_lut.py, render_previews.py and validate_lut.py so the
delivered .cube and every rendered comparison are produced by the same code path.

Verified references
-------------------
Apple Log 2 transfer function (identical to Apple Log):
  Apple "Apple Log Profile White Paper" (Sept 2023) and
  Apple "Apple Log 2 White Paper" (Sept 2025) - same curve, same constants.
  Cross-checked against OpenColorIO 2.6 source, file
  src/OpenColorIO/transforms/builtins/AppleCameras.cpp (constants match exactly).

Apple Wide Gamut primaries (from the Apple Log 2 white paper, re-published in
OpenColorIO AppleCameras.cpp):
  R (0.725,  0.301)
  G (0.221,  0.814)
  B (0.068, -0.076)   <- imaginary blue primary (like ACES AP0)
  W D65 (0.3127, 0.3290)

Rec.709 primaries: ITU-R BT.709 / IEC 61966-2-1, D65.
Output encoding: pure gamma 2.4 (BT.1886-style power law, as specified),
Rec.709 primaries, SDR.
"""

import numpy as np

# ---------------------------------------------------------------- Apple Log --
# Apple Log 2 white paper (Sept 2025) / Apple Log white paper (Sept 2023).
R_0 = -0.05641088
R_t = 0.01
C_LOG = 47.28711236
BETA = 0.00964052
GAMMA_LOG = 0.08550479
DELTA = 0.69336945
P_t = C_LOG * (R_t - R_0) ** 2  # ~0.00957209


def apple_log2_decode(p):
    """Apple Log 2 encoded signal p in [0,1] -> linear scene reflectance."""
    p = np.asarray(p, dtype=np.float64)
    lin = np.empty_like(p)
    m_hi = p >= P_t
    m_mid = (p >= 0.0) & (p < P_t)
    m_lo = p < 0.0
    lin[m_hi] = np.exp2((p[m_hi] - DELTA) / GAMMA_LOG) - BETA
    lin[m_mid] = np.sqrt(p[m_mid] / C_LOG) + R_0
    lin[m_lo] = R_0
    return lin


def apple_log2_encode(lin):
    """Linear scene reflectance -> Apple Log 2 encoded signal in [0,1]."""
    lin = np.asarray(lin, dtype=np.float64)
    p = np.empty_like(lin)
    m_hi = lin >= R_t
    m_mid = (lin >= R_0) & (lin < R_t)
    m_lo = lin < R_0
    p[m_hi] = GAMMA_LOG * np.log2(lin[m_hi] + BETA) + DELTA
    p[m_mid] = C_LOG * (lin[m_mid] - R_0) ** 2
    p[m_lo] = 0.0
    return np.clip(p, 0.0, 1.0)


# ------------------------------------------------------------- primaries ----
def xy_to_XYZ(xy):
    x, y = xy
    return np.array([x / y, 1.0, (1.0 - x - y) / y])


def primaries_to_RGB_to_XYZ(r, g, b, w):
    """Build the RGB->XYZ matrix for the given primaries and white point."""
    M = np.column_stack([xy_to_XYZ(r), xy_to_XYZ(g), xy_to_XYZ(b)])
    W = xy_to_XYZ(w)
    S = np.linalg.solve(M, W)
    return M * S


AWG_PRIM = ((0.725, 0.301), (0.221, 0.814), (0.068, -0.076))
R709_PRIM = ((0.64, 0.33), (0.30, 0.60), (0.15, 0.06))
D65 = (0.3127, 0.3290)

M_AWG_TO_XYZ = primaries_to_RGB_to_XYZ(*AWG_PRIM, D65)
M_R709_TO_XYZ = primaries_to_RGB_to_XYZ(*R709_PRIM, D65)
M_XYZ_TO_R709 = np.linalg.inv(M_R709_TO_XYZ)
M_AWG_TO_R709 = M_XYZ_TO_R709 @ M_AWG_TO_XYZ
M_R709_TO_AWG = np.linalg.inv(M_AWG_TO_R709)

REC709_LUMA = np.array([0.2126, 0.7152, 0.0722])

# sRGB EOTF pieces (IEC 61966-2-1) - used only to decode sRGB/JPEG *sources*
# for preview rendering, not part of the LUT itself.
def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(lin):
    lin = np.clip(np.asarray(lin, dtype=np.float64), 0.0, None)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
