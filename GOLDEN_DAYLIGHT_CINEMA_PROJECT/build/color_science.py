"""Color science library for the Golden Daylight Cinema LUT.

Scene-referred, float64, NumPy-only implementation.

Implements:
  * Apple Log 2 (Apple Log curve, encoding & decoding) per Apple's Apple Log 2
    White Paper (September 2025), verified constants.
  * Apple Wide Gamut -> XYZ -> Rec.709 (D65) conversions.
  * OKLab / OKLCh conversions (linear light, primaries-agnostic via XYZ).
  * Rec.709 ACES-ish filmic math helpers, CIEDE2000 for validation.

All colour math is done in linear light (not gamma-encoded).
"""

import numpy as np

# ---------------------------------------------------------------------------
# Apple Log 2 (Apple Wide Gamut) — Apple Log 2 White Paper, September 2025
# ---------------------------------------------------------------------------

# Transfer function constants (identical for Apple Log and Apple Log 2).
R_0 = -0.05641088   # parabola threshold / lowest representable linear value
R_T = 0.01          # transition point (R_0 <= R < R_T are parabolic)
C_LOG = 47.28711236 # parabola coefficient
BETA_LOG = 0.00964052
GAMMA_LOG = 0.08550479
DELTA_LOG = 0.69336945

P_T = C_LOG * (R_T - R_0) ** 2  # == 0.1... reference transition value

# Apple Wide Gamut primaries and white point (Apple Log 2 White Paper, Sec.5).
AWG_R_XY = np.array([0.725, 0.301])
AWG_G_XY = np.array([0.221, 0.814])
AWG_B_XY = np.array([0.068, -0.076])
AWG_W_XY = np.array([0.3127, 0.3290])  # D65

# Relative RGB matrix to XYZ (linear light, Y_w = 1).
def _matrix_from_primaries(r_xy, g_xy, b_xy, w_xy):
    """Build RGB->XYZ matrix from primaries and white chromaticity.

    Columns are per-primary XYZ representations scaled so that [1,1,1] maps to
    the white point (Y_w = 1). Returns M such that XYZ = M @ RGB (linear).
    """
    def chrom(xy):
        x, y = xy
        return np.array([x / y, 1.0, (1.0 - x - y) / y])

    r = chrom(r_xy)
    g = chrom(g_xy)
    b = chrom(b_xy)
    M0 = np.column_stack([r, g, b])  # per-primary building blocks (Y=1 each)

    x_w, y_w = w_xy
    z_w = 1.0 - x_w - y_w
    target_white = np.array([x_w / y_w, 1.0, z_w / y_w])  # X_w, Y_w=1, Z_w

    # M = M0 @ diag(w);  M @ [1,1,1] = M0 @ w = target_white
    w = np.linalg.solve(M0, target_white)
    M = M0 * w  # scaling columns
    return M


M_AWG_TO_XYZ = _matrix_from_primaries(AWG_R_XY, AWG_G_XY, AWG_B_XY, AWG_W_XY)

# Rec.709 linear RGB -> XYZ (standard ITU-R BT.709 matrix).
M_REC709_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041],
])

M_709_FROM_XYZ = np.linalg.inv(M_REC709_TO_XYZ)

# Apple Wide Gamut (linear) -> Rec.709 (linear).
# Both spaces share the D65 white point, so no chromatic adaptation matrix is
# required: everything is a pure diagonal-free matrix product.
M_AWG_TO_709 = M_709_FROM_XYZ @ M_AWG_TO_XYZ

# ---------------------------------------------------------------------------
# Apple Log 2 transfer function — decode and encode
# ---------------------------------------------------------------------------

def apple_log2_decode(p):
    """Decode Apple Log 2 (encoded 0..1) into linear scene reflection signal.

    Implements the exact inverse of Apple's encoding function.
    """
    p = np.asarray(p, dtype=np.float64)
    out = np.empty_like(p)
    hi = p >= P_T
    out[hi] = np.exp2((p[hi] - DELTA_LOG) / GAMMA_LOG) - BETA_LOG
    mid = (p >= 0.0) & ~hi
    out[mid] = np.sqrt(p[mid] / C_LOG) + R_0
    out[p < 0.0] = R_0
    return out


def apple_log2_encode(r):
    """Encode linear scene reflection signal into Apple Log 2 (0..1)."""
    r = np.asarray(r, dtype=np.float64)
    out = np.zeros_like(r)
    hi = r >= R_T
    out[hi] = GAMMA_LOG * np.log2(r[hi] + BETA_LOG) + DELTA_LOG
    mid = (r >= R_0) & ~hi
    out[mid] = C_LOG * (r[mid] - R_0) ** 2
    out[r < R_0] = 0.0
    return out


# ---------------------------------------------------------------------------
# OKLab / OKLCh (linear light, universal via XYZ)
# ---------------------------------------------------------------------------

# Reference matrices from Ottosson (2020, "A perceptual color space for
# image processing") as implemented by the colour-science library.
M_XYZ_TO_LMS = np.array([
    [0.8189330101, 0.3618667424, -0.1288597137],
    [0.0329845436, 0.9293118715,  0.0361456387],
    [0.0482003018, 0.2643662691,  0.6338517070],
])
M_LMS_TO_XYZ = np.linalg.inv(M_XYZ_TO_LMS)

M_LMS_TO_OKLAB = np.array([
    [0.2104542553,  0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050,  0.4505937099],
    [0.0259040371,  0.7827717662, -0.8086757660],
])
M_OKLAB_FROM_LMS = np.linalg.inv(M_LMS_TO_OKLAB)


def _sign_cbrt(x):
    """Signed cube root: sign(x)*|x|**(1/3)."""
    return np.sign(x) * np.abs(x) ** (1.0 / 3.0)


def _inv_sign_cbrt(x):
    """Apply cube (de-sign-cbrt): x**3."""
    return x ** 3.0


def xyz_to_oklab(xyz):
    """Linear XYZ (D65) -> OKLab (L, a, b)."""
    xyz = np.asarray(xyz)
    lms = xyz @ M_XYZ_TO_LMS.T
    lms_k = _sign_cbrt(lms)
    ok = lms_k @ M_LMS_TO_OKLAB.T
    return ok


def oklab_to_xyz(ok):
    """OKLab (L, a, b) -> linear XYZ (D65)."""
    ok = np.asarray(ok)
    lms_k = ok @ M_OKLAB_FROM_LMS.T
    lms = _inv_sign_cbrt(lms_k)
    return lms @ M_LMS_TO_XYZ.T


def oklab_to_oklch(ok):
    """OKLab -> OKLCh. Returns (L, C, h) with h in [0, 2*pi)."""
    L, a, b = ok[..., 0], ok[..., 1], ok[..., 2]
    C = np.sqrt(a * a + b * b)
    h = np.arctan2(b, a)
    h = np.mod(h, 2 * np.pi)
    return L, C, h


def oklch_to_oklab(L, C, h):
    """OKLCh -> OKLab."""
    a = C * np.cos(h)
    b = C * np.sin(h)
    return np.stack([L, a, b], axis=-1)


# ---------------------------------------------------------------------------
# Rec.709 encode (pure gamma 2.4) and inverse decode
# ---------------------------------------------------------------------------

GAMMA_709 = 2.4


def encode_709_2p4(rgb_linear):
    """Encode linear Rec.709 to gamma 2.4 (user-specified)."""
    return np.clip(np.maximum(rgb_linear, 0.0), 0.0, None) ** (1.0 / GAMMA_709)


def decode_709_2p4(rgb):
    """Decode gamma 2.4 Rec.709 to linear."""
    return np.clip(rgb, 0.0, None) ** GAMMA_709


def rec709_linear_to_oklab(rgb_709_linear):
    xyz = np.asarray(rgb_709_linear) @ M_REC709_TO_XYZ.T
    return xyz_to_oklab(xyz)


def oklab_to_rec709_linear(ok):
    xyz = oklab_to_xyz(ok)
    return xyz @ M_709_FROM_XYZ.T


def awg_linear_to_oklab(rgb_awg_linear):
    xyz = np.asarray(rgb_awg_linear) @ M_AWG_TO_XYZ.T
    return xyz_to_oklab(xyz)


def oklab_to_awg_linear(ok):
    xyz = oklab_to_xyz(ok)
    return xyz @ np.linalg.inv(M_AWG_TO_XYZ).T


# ---------------------------------------------------------------------------
# CIEDE2000 (for validation reporting) on proper CIE L*a*b* (D65)
# ---------------------------------------------------------------------------

def xyz_to_lab(xyz):
    """Linear XYZ (D65) -> CIE L*a*b* (standard, k=8, e=216/24389)."""
    xn, yn, zn = 0.95047, 1.0, 1.08883  # D65 reference
    x, y, z = xyz / np.array([xn, yn, zn])
    def f(t):
        return np.where(t > 216.0 / 24389.0, np.cbrt(t), (24389.0 / 27.0) * t + 16.0 / 116.0)
    fx, fy, fz = f(x), f(y), f(z)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def delta_e2000(lab1, lab2):
    """CIEDE2000 ΔE00 between two CIE L*a*b* points."""
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    L1, a1, b1 = lab1[..., 0], lab1[..., 1], lab1[..., 2]
    L2, a2, b2 = lab2[..., 0], lab2[..., 1], lab2[..., 2]
    LC1 = np.sqrt(a1**2 + b1**2)
    LC2 = np.sqrt(a2**2 + b2**2)
    LC_bar = (LC1 + LC2) / 2.0
    G = 0.5 * (1.0 - np.sqrt(LC_bar**7 / (LC_bar**7 + 25.0**7)))
    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    LC1p = np.sqrt(a1p**2 + b1**2)
    LC2p = np.sqrt(a2p**2 + b2**2)
    h1p = np.arctan2(b1, a1p) % (2 * np.pi)
    h2p = np.arctan2(b2, a2p) % (2 * np.pi)
    dLp = L2 - L1
    dCp = LC2p - LC1p
    dhp = h2p - h1p
    dhp = (dhp + np.pi) % (2 * np.pi) - np.pi
    dhP = 2.0 * np.sqrt(LC1p * LC2p) * np.sin(dhp / 2.0)
    if (LC1p > 0) & (LC2p > 0):
        avg_hp = (h1p + h2p) / 2.0
        if np.abs(h1p - h2p) > np.pi:
            avg_hp = (h1p + h2p + 2 * np.pi) / 2.0 if h1p + h2p < 2 * np.pi else (h1p + h2p - 2 * np.pi) / 2.0
        avg_hp = avg_hp % (2 * np.pi)
    else:
        avg_hp = 0.0

    def T(x):
        return (1.0 - 0.17 * np.cos(x - np.radians(30)) + 0.24 * np.cos(2 * x)
                + 0.32 * np.cos(3 * x + np.radians(6)) - 0.20 * np.cos(4 * x - np.radians(63)))

    T_vals = T(avg_hp)
    dTheta = 30.0 * np.exp(-(((avg_hp - np.radians(275)) ** 2) / (2 * np.radians(30) ** 2)))
    R_theta = -np.sin(2 * np.radians(dTheta))
    kL = kC = kH = 1.0
    return np.sqrt((dLp / kL) ** 2 + (dCp / kC) ** 2 + (dhP / kH * T_vals) ** 2) * (1.0 + R_theta)


def delta_e_oklab(oklab1, oklab2):
    """Euclidean ΔE in OKLab space (conservative, smooth metric for trends)."""
    return float(np.sqrt(np.sum((np.asarray(oklab1) - np.asarray(oklab2)) ** 2)))
