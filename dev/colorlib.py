"""
colorlib.py -- Colour science core for GOLDEN DAYLIGHT CINEMA
==============================================================

Authoritative references used for the Apple Log 2 pipeline (all cross-checked
against each other during development):

1. Apple Inc., "Apple Log Profile White Paper", September 2023 (Part 028-00768).
   Defines the Apple Log transfer function exactly:

       Encode  P = f(R) = gamma*log2(R + beta) + delta      if R >= R_t
                        = c*(R - R_0)^2                     if R_0 <= R < R_t
                        = 0                                 if R < R_0

       Decode  R = f^-1(P) = 2^((P - delta)/gamma) - beta   if P >= P_t
                           = sqrt(P/c) + R_0                 if 0 <= P < P_t
                           = R_0                             if P < 0

               R_0 = -0.05641088   R_t = 0.01   c = 47.28711236
               beta = 0.00964052   gamma = 0.08550479   delta = 0.69336945
               P_t = c * (R_t - R_0)^2

   Reference points (10-bit full range):
       0%    reflectance -> P = 0.150477 -> code  154
       18%   reflectance -> P = 0.488272 -> code  500
       90%   reflectance -> P = 0.681686 -> code  697
       1200% reflectance -> P = 1.000000 -> code 1023

2. OpenColorIO, src/OpenColorIO/transforms/builtins/AppleCameras.cpp
   (Academy Software Foundation). States explicitly:
       "Apple Wide Gamut primaries from the Apple Log 2 white paper."
       "Apple Log 2 uses the same transfer function as Apple Log, but with the
        wider Apple Wide Gamut primaries rather than Rec.2020."
   Apple Wide Gamut chromaticities:
       R = (0.725, 0.301)   G = (0.221, 0.814)   B = (0.068, -0.076)
       W = D65 (0.3127, 0.3290)

3. ACES / ASWF "aces-input-and-colorspaces", apple/CSC.Apple.AppleLog2_to_ACES.ctl
   -- identical Apple Wide Gamut primaries and identical transfer-function
   constants. Independent confirmation of #2.

4. colour-science, colour/models/rgb/transfer_functions/apple_log_profile.py
   -- "the Apple Log Profile log encoding, also used by Apple Log 2", same
   constants, cites both the 2023 and the 2025 Apple white papers.

=> Apple Log 2 = Apple Log transfer function + Apple Wide Gamut primaries (D65).
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------
# Apple Log / Apple Log 2 transfer function constants
# --------------------------------------------------------------------------
R_0 = -0.05641088
R_T = 0.01
C_PAR = 47.28711236
BETA = 0.00964052
GAMMA = 0.08550479
DELTA = 0.69336945
P_T = C_PAR * (R_T - R_0) ** 2          # = 0.150477...

MIDDLE_GREY_REFLECTANCE = 0.18          # 18% grey card
MAX_REFLECTANCE = 12.0                  # P = 1.0 -> 1200% reflectance


def apple_log_decode(P):
    """Apple Log / Apple Log 2 code value P in [0,1] -> linear scene reflectance R.

    R = 0.18 corresponds to an 18% reflectance grey card.
    R = 1.0  corresponds to a 100% diffuse white.
    R = 12.0 corresponds to the top of the encoding (P = 1.0, +6.06 stops over grey).
    """
    P = np.asarray(P, dtype=np.float64)
    out = np.empty_like(P)
    hi = P >= P_T
    mid = (~hi) & (P >= 0.0)
    lo = ~(hi | mid)
    out[hi] = np.power(2.0, (P[hi] - DELTA) / GAMMA) - BETA
    out[mid] = np.sqrt(P[mid] / C_PAR) + R_0
    out[lo] = R_0
    return out


def apple_log_encode(R):
    """Linear scene reflectance R -> Apple Log / Apple Log 2 code value P in [0,1]."""
    R = np.asarray(R, dtype=np.float64)
    out = np.empty_like(R)
    hi = R >= R_T
    mid = (~hi) & (R >= R_0)
    lo = ~(hi | mid)
    out[hi] = GAMMA * np.log2(R[hi] + BETA) + DELTA
    out[mid] = C_PAR * (R[mid] - R_0) ** 2
    out[lo] = 0.0
    return out


# --------------------------------------------------------------------------
# Chromaticity -> matrix machinery
# --------------------------------------------------------------------------
def xy_to_XYZ(xy):
    x, y = float(xy[0]), float(xy[1])
    return np.array([x / y, 1.0, (1.0 - x - y) / y])


def rgb_to_xyz_matrix(primaries, white):
    """Build the RGB->XYZ matrix (D65-relative, Y scaled so white Y = 1)."""
    Xr, Yr, Zr = xy_to_XYZ(primaries[0])
    Xg, Yg, Zg = xy_to_XYZ(primaries[1])
    Xb, Yb, Zb = xy_to_XYZ(primaries[2])
    M = np.array([[Xr, Xg, Xb],
                  [Yr, Yg, Yb],
                  [Zr, Zg, Zb]], dtype=np.float64)
    W = xy_to_XYZ(white)
    S = np.linalg.solve(M, W)
    return M * S[np.newaxis, :]


# Primary sets ----------------------------------------------------------------
# Apple Wide Gamut -- from the Apple Log 2 white paper (via OCIO / ACES CTL)
APPLE_WIDE_GAMUT = np.array([[0.725, 0.301],
                             [0.221, 0.814],
                             [0.068, -0.076]])
D65 = np.array([0.3127, 0.3290])
D65_PRECISE = np.array([0.31271396, 0.32903127])

# BT.2020 -- used by Apple Log v1 (per the 2023 Apple white paper)
BT2020 = np.array([[0.708, 0.292],
                   [0.170, 0.797],
                   [0.131, 0.046]])

# Rec.709 / sRGB primaries
REC709 = np.array([[0.640, 0.330],
                   [0.300, 0.600],
                   [0.150, 0.060]])

M_AWG_TO_XYZ = rgb_to_xyz_matrix(APPLE_WIDE_GAMUT, D65)
M_XYZ_TO_AWG = np.linalg.inv(M_AWG_TO_XYZ)
M_709_TO_XYZ = rgb_to_xyz_matrix(REC709, D65)
M_XYZ_TO_709 = np.linalg.inv(M_709_TO_XYZ)
M_2020_TO_XYZ = rgb_to_xyz_matrix(BT2020, D65)
M_XYZ_TO_2020 = np.linalg.inv(M_2020_TO_XYZ)

# Both AWG and Rec.709 use D65, so no chromatic adaptation is required
# (a Bradford adaptation between identical white points is the identity).
M_AWG_TO_709 = M_XYZ_TO_709 @ M_AWG_TO_XYZ
M_709_TO_AWG = np.linalg.inv(M_AWG_TO_709)
M_AWG_TO_2020 = M_XYZ_TO_2020 @ M_AWG_TO_XYZ
M_2020_TO_709 = M_XYZ_TO_709 @ M_2020_TO_XYZ

# Rec.709 luminance coefficients (linear light)
LUMA_709 = np.array([0.2126, 0.7152, 0.0722])
LUMA_2020 = np.array([0.2627, 0.6780, 0.0593])


def apply_matrix(rgb, M):
    """rgb: (..., 3) -> (..., 3). Rows of M are applied as out = rgb @ M.T"""
    return np.einsum('...i,ji->...j', np.asarray(rgb, dtype=np.float64), M)


# --------------------------------------------------------------------------
# Rec.709 display transfer functions
# --------------------------------------------------------------------------
def rec709_gamma_encode(linear, gamma=2.4):
    """Pure power-law gamma 2.4 encode (broadcast Rec.709 / BT.1886 style)."""
    linear = np.asarray(linear, dtype=np.float64)
    x = np.clip(linear, 0.0, None)
    return np.power(x, 1.0 / gamma)


def rec709_gamma_decode(code, gamma=2.4):
    code = np.asarray(code, dtype=np.float64)
    x = np.clip(code, 0.0, None)
    return np.power(x, gamma)


# --------------------------------------------------------------------------
# OkLab / OkLCh  (used for hue-aware, perceptually smooth creative grading)
# --------------------------------------------------------------------------
_OKLAB_M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005],
])
_OKLAB_M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660],
])
_OKLAB_M1_INV = np.linalg.inv(_OKLAB_M1)
_OKLAB_M2_INV = np.linalg.inv(_OKLAB_M2)


def linear_to_oklab(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    lms = np.einsum('...i,ji->...j', rgb, _OKLAB_M1)
    lms_ = np.cbrt(lms)
    return np.einsum('...i,ji->...j', lms_, _OKLAB_M2)


def oklab_to_linear(lab):
    lab = np.asarray(lab, dtype=np.float64)
    lms_ = np.einsum('...i,ji->...j', lab, _OKLAB_M2_INV)
    lms = lms_ ** 3
    return np.einsum('...i,ji->...j', lms, _OKLAB_M1_INV)


def oklab_to_oklch(lab):
    L = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]
    C = np.sqrt(a * a + b * b)
    h = np.arctan2(b, a) % (2.0 * np.pi)
    return np.stack([L, C, h], axis=-1)


def oklch_to_oklab(lch):
    L, C, h = lch[..., 0], lch[..., 1], lch[..., 2]
    return np.stack([L, C * np.cos(h), C * np.sin(h)], axis=-1)


# --------------------------------------------------------------------------
# .cube file I/O and 3D LUT application (trilinear)
# --------------------------------------------------------------------------
def read_cube(path):
    """Parse a .cube 3D LUT. Returns (size, data[N*N*N,3], domain_min, domain_max)."""
    size = None
    dmin = np.zeros(3)
    dmax = np.ones(3)
    rows = []
    title = None
    with open(path, 'r', errors='replace') as fh:
        for raw in fh:
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            key = parts[0].upper()
            if key == 'TITLE':
                title = line[5:].strip().strip('"')
                continue
            if key == 'LUT_3D_SIZE':
                size = int(parts[1])
                continue
            if key == 'DOMAIN_MIN':
                dmin = np.array([float(v) for v in parts[1:4]])
                continue
            if key == 'DOMAIN_MAX':
                dmax = np.array([float(v) for v in parts[1:4]])
                continue
            if key in ('LUT_1D_SIZE', 'DOMAIN_IN', 'DOMAIN_OUT'):
                raise ValueError(f'Unsupported directive {key}')
            vals = [float(v) for v in parts]
            if len(vals) != 3:
                raise ValueError(f'Bad row: {line!r}')
            rows.append(vals)
    if size is None:
        raise ValueError('Missing LUT_3D_SIZE')
    data = np.asarray(rows, dtype=np.float64)
    if data.shape != (size ** 3, 3):
        raise ValueError(f'Expected {size ** 3} rows, got {data.shape[0]}')
    return size, data.reshape(size, size, size, 3), dmin, dmax, title


def apply_cube(size, table, dmin, dmax, rgb):
    """Trilinear interpolation of a 3D LUT over an (..., 3) array in [dmin, dmax]."""
    rgb = np.asarray(rgb, dtype=np.float64)
    norm = (rgb - dmin) / (dmax - dmin)
    norm = np.clip(norm, 0.0, 1.0) * (size - 1.0)
    i0 = np.clip(np.floor(norm).astype(np.int64), 0, size - 2)
    frac = norm - i0
    i1 = i0 + 1
    out = np.empty_like(rgb)
    # .cube layout: the RED index varies fastest, so a C-order reshape gives
    # table[blue, green, red, channel]. Index accordingly.
    ir0, ig0, ib0 = i0[..., 0], i0[..., 1], i0[..., 2]
    ir1, ig1, ib1 = i1[..., 0], i1[..., 1], i1[..., 2]
    for c in range(3):
        c000 = table[ib0, ig0, ir0, c]
        c100 = table[ib0, ig0, ir1, c]
        c010 = table[ib0, ig1, ir0, c]
        c110 = table[ib0, ig1, ir1, c]
        c001 = table[ib1, ig0, ir0, c]
        c101 = table[ib1, ig0, ir1, c]
        c011 = table[ib1, ig1, ir0, c]
        c111 = table[ib1, ig1, ir1, c]
        fr, fg, fb = frac[..., 0], frac[..., 1], frac[..., 2]
        c00 = c000 * (1 - fr) + c100 * fr
        c10 = c010 * (1 - fr) + c110 * fr
        c01 = c001 * (1 - fr) + c101 * fr
        c11 = c011 * (1 - fr) + c111 * fr
        c0 = c00 * (1 - fg) + c10 * fg
        c1 = c01 * (1 - fg) + c11 * fg
        out[..., c] = c0 * (1 - fb) + c1 * fb
    return out


def write_cube(path, size, table, title=None, comment=None, decimals=7):
    """Write a 3D LUT in Adobe/Iridas .cube format (red index varies fastest)."""
    with open(path, 'w') as fh:
        if title:
            fh.write(f'TITLE "{title}"\n')
        if comment:
            for line in comment.strip('\n').split('\n'):
                fh.write(f'# {line}\n')
        fh.write(f'LUT_3D_SIZE {size}\n')
        fh.write('DOMAIN_MIN 0.0 0.0 0.0\n')
        fh.write('DOMAIN_MAX 1.0 1.0 1.0\n')
        fmt = f'%.{decimals}f'
        flat = np.ascontiguousarray(table.reshape(-1, 3))
        lines = []
        for i in range(0, flat.shape[0], 2048):
            block = flat[i:i + 2048]
            lines.append('\n'.join(
                ' '.join(fmt % v for v in row) for row in block))
        fh.write('\n'.join(lines))
        fh.write('\n')
    return path


def identity_table(size):
    g = np.linspace(0.0, 1.0, size)
    b, gr, r = np.meshgrid(g, g, g, indexing='ij')   # blue slowest, red fastest
    return np.stack([r, gr, b], axis=-1)


# --------------------------------------------------------------------------
# Utility: smooth ramps / windows used by the creative grade
# --------------------------------------------------------------------------
def smoothstep(edge0, edge1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0 + 1e-12), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def raised_cosine_window(h, centre, width):
    """Smooth periodic window in hue (radians) -> 1.0 at centre, 0.0 outside."""
    d = np.mod(np.asarray(h, dtype=np.float64) - centre + np.pi, 2 * np.pi) - np.pi
    w = width * 0.5
    x = np.clip(np.abs(d) / (w + 1e-12), 0.0, 1.0)
    return 0.5 * (1.0 + np.cos(np.pi * x))


def soft_clip_positive(x, limit=1.0, knee=0.6):
    """Smoothly compress values above `knee*limit` into `limit` (monotone, C1)."""
    x = np.asarray(x, dtype=np.float64)
    k = knee * limit
    out = np.where(x <= k, x, np.nan)
    hi = x > k
    # exponential shoulder with matching value+slope at the knee
    slope = 1.0
    out = np.where(hi, limit - (limit - k) * np.exp(-(x - k) * slope / (limit - k)), x)
    return np.minimum(out, limit)


def luminance_preserving_gamut_compress(rgb, primaries_luma=LUMA_709):
    """Compress out-of-gamut colours by reducing chroma around the luminance axis.

    Keeps luminance and hue constant, so saturated blue skies and greens land
    inside Rec.709 without hue rotation or channel-by-channel hard clipping.
    Negative channels (very common when converting AWG -> Rec.709) are handled
    with a soft knee so that the transition is smooth rather than a hard fold.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    Y = rgb @ primaries_luma
    minc = rgb.min(axis=-1)
    maxc = rgb.max(axis=-1)

    # How far outside the [0, ...] box are we?
    under = np.clip(-minc, 0.0, None)
    # Chroma scale needed to bring the most negative channel up to 0
    denom = (Y - minc)
    scale_lo = np.where(denom > 1e-9, np.clip(Y / denom, 0.0, 1.0), 1.0)
    out = Y[..., None] + (rgb - Y[..., None]) * scale_lo[..., None]

    # Soft knee: start easing a little before the boundary so there is no
    # visible saturation discontinuity on smooth gradients (e.g. sky).
    knee = 0.06
    need = smoothstep(0.0, knee, under)
    out = rgb * (1.0 - need[..., None]) + out * need[..., None]

    # Highlight side: keep >1 values (they are needed for the shoulder) but
    # soften extreme excursions so single-channel spikes do not hue-shift.
    over = np.clip(maxc - 1.6, 0.0, None)
    hi_scale = 1.0 / (1.0 + over)
    Yh = Y.copy()
    out = np.where(over[..., None] > 0,
                   Yh[..., None] + (out - Yh[..., None]) * hi_scale[..., None],
                   out)
    return out
