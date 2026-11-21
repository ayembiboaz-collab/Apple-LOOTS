#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GOLDEN DAYLIGHT CINEMA - core colour pipeline (scene-referred)
==============================================================

Pipeline implemented by this module (identical for image rendering and LUT baking):

    input  : Apple Log 2 code values, Apple Wide Gamut (AWG), D65, full range [0,1]
    step 1 : Apple Log 2 transfer-function decode   -> scene-linear RGB (AWG primaries)
    step 2 : 3x3 gamut transform  AWG -> Rec.709    (D65 white, no adaptation needed)
    step 3 : creative grade (filmic tone curve + colour operations)
             -> display-linear Rec.709
    step 4 : inverse gamma 2.4 encode               -> Rec.709 SDR code values [0,1]

Verified technical references
-----------------------------
* Apple Inc., "Apple Log 2 White Paper", September 2025 (Part 028-00834, Version 1.1):
    - transfer function constants (R0, Rt, c, beta, gamma, delta)
    - anchor points: 0% -> 0.150477, 18% -> 0.488272, 90% -> 0.681686, 1200% -> 1.0
    - Apple Wide Gamut chromaticities: R(0.725, 0.301) G(0.221, 0.814) B(0.068, -0.076),
      white D65 (0.3127, 0.3290)
* OpenColorIO (github.com/AcademySoftwareFoundation/OpenColorIO),
    src/OpenColorIO/transforms/builtins/AppleCameras.cpp : identical constants; its
    Apple Wide Gamut -> ACES2065-1 matrix is used here as an independent cross-check.
* ITU-R BT.709-6 : Rec.709 primaries.  ITU-R BT.1886 : reference display EOTF (gamma 2.4).
"""

import numpy as np

# ----------------------------------------------------------------------------
# 1. Apple Log 2 transfer function (official white paper constants)
# ----------------------------------------------------------------------------
AL2_R0    = -0.05641088
AL2_RT    = 0.01
AL2_C     = 47.28711236
AL2_BETA  = 0.00964052
AL2_GAMMA = 0.08550479
AL2_DELTA = 0.69336945
AL2_PT    = AL2_C * (AL2_RT - AL2_R0) ** 2   # 0.20855531595464202


def al2_decode(P):
    """Apple Log 2 code value(s) -> scene-linear reflectance R (white paper eq.)."""
    P = np.asarray(P, dtype=np.float64)
    R = np.empty_like(P)
    m_log = P >= AL2_PT
    m_par = (~m_log) & (P >= 0.0)
    m_neg = P < 0.0
    R[m_log] = np.power(2.0, (P[m_log] - AL2_DELTA) / AL2_GAMMA) - AL2_BETA
    R[m_par] = np.sqrt(P[m_par] / AL2_C) + AL2_R0
    R[m_neg] = AL2_R0
    return R


def al2_encode(R):
    """Scene-linear reflectance R -> Apple Log 2 code value(s) (white paper eq.)."""
    R = np.asarray(R, dtype=np.float64)
    P = np.empty_like(R)
    m_log = R >= AL2_RT
    m_par = (~m_log) & (R >= AL2_R0)
    m_neg = R < AL2_R0
    P[m_log] = AL2_GAMMA * np.log2(R[m_log] + AL2_BETA) + AL2_DELTA
    P[m_par] = AL2_C * (R[m_par] - AL2_R0) ** 2
    P[m_neg] = 0.0
    return P


# ----------------------------------------------------------------------------
# 2. Gamut matrices (derived from chromaticities; cross-checked vs OpenColorIO)
# ----------------------------------------------------------------------------
AWG_PRIMARIES = ((0.725, 0.301), (0.221, 0.814), (0.068, -0.076))  # Apple Wide Gamut
BT709_PRIMARIES = ((0.640, 0.330), (0.300, 0.600), (0.150, 0.060))  # ITU-R BT.709
D65 = (0.3127, 0.3290)
AP0_PRIMARIES = ((0.73470, 0.26530), (0.00000, 1.00000), (0.00010, -0.07700))
AP0_WHITE = (0.32168, 0.33767)  # ACES2065-1 white, as used by OpenColorIO


def rgb_to_xyz_matrix(primaries, white):
    """3x3 RGB->XYZ matrix from CIE xy chromaticities of primaries + white point."""
    (xr, yr), (xg, yg), (xb, yb) = primaries
    (xw, yw) = white
    M = np.array([
        [xr / yr, xg / yg, xb / yb],
        [1.0,     1.0,     1.0],
        [(1 - xr - yr) / yr, (1 - xg - yg) / yg, (1 - xb - yb) / yb],
    ])
    W = np.array([xw / yw, 1.0, (1 - xw - yw) / yw])
    S = np.linalg.solve(M, W)
    return M * S  # scales columns


M_AWG_TO_XYZ  = rgb_to_xyz_matrix(AWG_PRIMARIES, D65)
M_709_TO_XYZ  = rgb_to_xyz_matrix(BT709_PRIMARIES, D65)
M_XYZ_TO_709  = np.linalg.inv(M_709_TO_XYZ)
M_XYZ_TO_AWG  = np.linalg.inv(M_AWG_TO_XYZ)
M_AWG_TO_709  = M_XYZ_TO_709 @ M_AWG_TO_XYZ
M_709_TO_AWG  = M_XYZ_TO_AWG @ M_709_TO_XYZ

# Rec.709 luma weights (linear light)
LUMA_709 = np.array([0.2126, 0.7152, 0.0722])

GAMMA_OUT = 2.4  # ITU-R BT.1886 reference EOTF exponent


def gamma24_encode(x):
    """display-linear -> display code value (inverse gamma 2.4, clamped to [0,1])."""
    return np.clip(x, 0.0, 1.0) ** (1.0 / GAMMA_OUT)


def luma709(rgb):
    return rgb @ LUMA_709


def apply_matrix(M, rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return rgb @ M.T  # row vectors


# ----------------------------------------------------------------------------
# 3. Monotone cubic (Fritsch-Carlson PCHIP) interpolation
# ----------------------------------------------------------------------------
class PCHIP:
    """Monotone piecewise-cubic Hermite interpolant (no overshoot / no banding)."""

    def __init__(self, x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        self.x, self.y = x, y
        h = np.diff(x)
        d = np.diff(y) / h
        n = len(x)
        m = np.zeros(n)
        # interior: weighted harmonic mean
        for i in range(1, n - 1):
            if d[i - 1] * d[i] > 0:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
            else:
                m[i] = 0.0
        # endpoints (PCHIP standard)
        m[0] = self._end(h[0], h[1], d[0], d[1])
        m[-1] = self._end(h[-1], h[-2], d[-1], d[-2])
        self.m = m
        self.h = h
        self.d = d

    @staticmethod
    def _end(h0, h1, d0, d1):
        if d0 * d1 <= 0 or (h0 == 0 or h1 == 0):
            return 0.0
        e = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(e) != np.sign(d0):
            return 0.0
        if np.sign(d0) != np.sign(d1) and abs(e) > 3 * abs(d0):
            return 3 * d0
        return e

    def eval(self, xq):
        xq = np.asarray(xq, float)
        i = np.clip(np.searchsorted(self.x, xq, side='right') - 1, 0, len(self.x) - 2)
        x0 = self.x[i]; h = self.h[i]
        t = (xq - x0) / h
        t2 = t * t; t3 = t2 * t
        y0, y1 = self.y[i], self.y[i + 1]
        m0, m1 = self.m[i], self.m[i + 1]
        return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * h * m0 + \
               (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * h * m1


# ----------------------------------------------------------------------------
# 4. The GOLDEN DAYLIGHT CINEMA grade
# ----------------------------------------------------------------------------
# Filmic tone curve: scene-linear Rec.709 -> display-linear Rec.709 (per channel).
# Knots are placed at whole stops around 18% grey. Anchored so that nothing above
# mid grey becomes brighter than the neutral conversion (highlight protection),
# shadows deepen smoothly with no crush, highlights roll off with a long shoulder.
TONE_X = [0.0, 0.00035, 0.0007, 0.00141, 0.0028, 0.005625, 0.01125, 0.0225,
          0.045, 0.09, 0.18, 0.36, 0.72, 1.44, 2.88, 5.76, 11.52, 23.04,
          46.1, 92.2, 368.6, 1000.0]
TONE_Y = [0.0, 0.000012, 0.00003, 0.00007, 0.00017, 0.00042, 0.0011, 0.0032,
          0.011, 0.040, 0.128, 0.300, 0.475, 0.625, 0.752, 0.845, 0.915, 0.955,
          0.978, 0.990, 0.9985, 1.0]

_TONE = PCHIP(TONE_X, TONE_Y)
_TONE_SLOPE0 = _TONE.eval(0.001) / 0.001  # toe slope for negative extension


def tone_curve(x):
    """Filmic tone curve, extended linearly for negative (out-of-gamut) values."""
    x = np.asarray(x, float)
    out = np.empty_like(x)
    pos = x >= 0
    out[pos] = _TONE.eval(x[pos])
    out[~pos] = x[~pos] * _TONE_SLOPE0
    return out


# Grade parameters (tuned iteratively across the eight test scenes) -----------------
PARAMS = dict(
    # saturation multiplier vs display luma (rich mids, protected whites & blacks)
    sat_l=[0.0, 0.02, 0.06, 0.15, 0.35, 0.7, 1.0],
    sat_m=[1.00, 1.03, 1.10, 1.14, 1.11, 1.04, 1.00],
    # vibrance damping: already-saturated colours receive less boost
    vib_k=1.1,
    # sky: rich natural blue, controlled cyan, cloud whites protected
    sky_hue=224.0, sky_sigma=33.0, sky_sat=1.17, sky_deepen=0.035,
    sky_s_lo=0.10, sky_s_hi=0.28,          # only colours at least this saturated
    sky_l_hi=0.75, sky_l_max=0.98,         # do not touch near-white cloud luminance
    # foliage: natural, slightly warm greens; never radioactive or teal
    fol_hue=105.0, fol_sigma=34.0, fol_sat=0.93, fol_shift=6.0,
    # cyan control (water/sky edge): pull toward blue, hold saturation
    cy_hue=196.0, cy_sigma=20.0, cy_sat=0.99, cy_shift=5.0,
    # skin: natural, subtly warm; no orange/red/yellow drift, no extra saturation
    skin_hue=28.0, skin_sigma=17.0, skin_sat=0.965,
    skin_s_lo=0.06, skin_s_hi=0.16, skin_s_top=0.55, skin_s_max=0.80,
    # golden warmth: honey/amber in sunlit mids, whites stay believable
    warm_r=0.085, warm_g=0.024, warm_b=-0.075, warm_lum_comp=0.013,
    warm_gate_k=0.055,                     # saturation gate (neutrals barely shift)
    warm_l=[0.0, 0.03, 0.10, 0.28, 0.55, 0.80, 1.0],
    warm_w=[0.00, 0.35, 0.90, 1.00, 0.90, 0.55, 0.35],
    # already-warm colours (golden hour) receive attenuated warmth
    warm_att_hue=45.0, warm_att_sigma=26.0,
    warm_att_s_lo=0.32, warm_att_s_hi=0.60, warm_att_amt=0.50,
    # cool shade separation (subtle blue, only in desaturated deep shadows)
    cool_r=-0.028, cool_g=-0.010, cool_b=0.032,
    cool_l_lo=0.015, cool_l_hi=0.09, cool_gate_k=0.12,
    # final highlight desaturation for clean whites
    hi_desat_l=0.85, hi_desat_amt=0.08,
)

_SATM = None
_WARMW = None


def _curves():
    global _SATM, _WARMW
    if _SATM is None:
        _SATM = PCHIP(PARAMS['sat_l'], PARAMS['sat_m'])
        _WARMW = PCHIP(PARAMS['warm_l'], PARAMS['warm_w'])
    return _SATM, _WARMW


def smoothstep(x, e0, e1):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hue_gauss(H, center, sigma):
    """Circular gaussian weight of HSV hue (degrees) around `center`."""
    d = np.radians(H - center)
    d = np.angle(np.exp(1j * d))  # wrap to [-pi, pi]
    return np.exp(-0.5 * (d / np.radians(sigma)) ** 2)


def rgb_to_hsv(rgb):
    """RGB (any scale >= 0 after clamp) -> HSV; H in degrees, S and V in [0,1]."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    c = mx - mn
    H = np.zeros_like(mx)
    m = c > 1e-12
    idx = m & (mx == r)
    H[idx] = 60.0 * (((g[idx] - b[idx]) / c[idx]) % 6.0)
    idx = m & (mx == g) & (mx != r)
    H[idx] = 60.0 * ((b[idx] - r[idx]) / c[idx] + 2.0)
    idx = m & (mx == b) & (mx != r) & (mx != g)
    H[idx] = 60.0 * ((r[idx] - g[idx]) / c[idx] + 4.0)
    S = np.where(mx > 1e-12, c / np.maximum(mx, 1e-12), 0.0)
    return H, S, mx


def hsv_to_rgb(H, S, V):
    """HSV (H degrees) -> RGB (V scale)."""
    C = V * S
    Hp = (H % 360.0) / 60.0
    X = C * (1 - np.abs(Hp % 2 - 1))
    Z = np.zeros_like(C)
    r = np.select([Hp < 1, Hp < 2, Hp < 3, Hp < 4, Hp < 5, Hp >= 5],
                  [C, X, Z, Z, X, C])
    g = np.select([Hp < 1, Hp < 2, Hp < 3, Hp < 4, Hp < 5, Hp >= 5],
                  [X, C, C, X, Z, Z])
    b = np.select([Hp < 1, Hp < 2, Hp < 3, Hp < 4, Hp < 5, Hp >= 5],
                  [Z, Z, X, C, C, X])
    m = V - C
    return np.stack([r + m, g + m, b + m], axis=-1)


def grade(lin709):
    """Scene-linear Rec.709 (..., 3) -> display-linear Rec.709 (..., 3)."""
    SATM, WARMW = _curves()
    # --- tone curve (per channel, filmic) ---
    disp = tone_curve(lin709)

    # --- masks on the toned image ---
    L = luma709(disp)
    rgbc = np.clip(disp, 0.0, None)
    H, S, V = rgb_to_hsv(rgbc)

    # hue weights
    w_sky = hue_gauss(H, PARAMS['sky_hue'], PARAMS['sky_sigma'])
    w_fol = hue_gauss(H, PARAMS['fol_hue'], PARAMS['fol_sigma'])
    w_cy  = hue_gauss(H, PARAMS['cy_hue'],  PARAMS['cy_sigma'])
    w_skin = hue_gauss(H, PARAMS['skin_hue'], PARAMS['skin_sigma'])
    w_att = hue_gauss(H, PARAMS['warm_att_hue'], PARAMS['warm_att_sigma'])

    # saturation gates
    g_sky = smoothstep(S, PARAMS['sky_s_lo'], PARAMS['sky_s_hi']) * \
            (1.0 - smoothstep(L, PARAMS['sky_l_hi'], PARAMS['sky_l_max']))
    g_skin = smoothstep(S, PARAMS['skin_s_lo'], PARAMS['skin_s_hi']) * \
             (1.0 - smoothstep(S, PARAMS['skin_s_top'], PARAMS['skin_s_max']))
    g_att = smoothstep(S, PARAMS['warm_att_s_lo'], PARAMS['warm_att_s_hi'])

    # --- sky: deepen very slightly, enrich saturation ---
    V = V * (1.0 - PARAMS['sky_deepen'] * w_sky * g_sky)

    # --- saturation: luma curve * vibrance * hue adjustments ---
    m = SATM.eval(np.clip(L, 0.0, 1.0))
    vib = 1.0 / (1.0 + PARAMS['vib_k'] * S)
    m = 1.0 + (m - 1.0) * vib
    m = m * (1.0 + (PARAMS['sky_sat'] - 1.0) * w_sky * g_sky)
    m = m * (1.0 + (PARAMS['fol_sat'] - 1.0) * w_fol)
    m = m * (1.0 + (PARAMS['cy_sat'] - 1.0) * w_cy)
    m = m * (1.0 + (PARAMS['skin_sat'] - 1.0) * w_skin * g_skin)
    # clean whites: gentle desaturation near the top end
    m = m * (1.0 - PARAMS['hi_desat_amt'] * smoothstep(L, PARAMS['hi_desat_l'], 1.05))
    S = np.clip(S * m, 0.0, 1.0)

    # --- hue shifts ---
    H = H + PARAMS['fol_shift'] * w_fol + PARAMS['cy_shift'] * w_cy * g_sky

    disp = hsv_to_rgb(H, S, V)

    # --- golden warmth (sunlit mids; whites and neutrals protected) ---
    gate = S / (S + PARAMS['warm_gate_k'])
    wL = WARMW.eval(np.clip(L, 0.0, 1.0))
    atten = 1.0 - PARAMS['warm_att_amt'] * w_att * g_att
    w = wL * gate * atten
    disp = disp * np.stack([1.0 + PARAMS['warm_r'] * w,
                            1.0 + PARAMS['warm_g'] * w,
                            1.0 + PARAMS['warm_b'] * w], axis=-1)
    disp = disp * (1.0 - PARAMS['warm_lum_comp'] * w)[..., None]

    # --- cool shade separation (desaturated deep shadows only) ---
    wc = (1.0 - smoothstep(L, PARAMS['cool_l_lo'], PARAMS['cool_l_hi'])) * \
         (1.0 - S / (S + PARAMS['cool_gate_k']))
    disp = disp * np.stack([1.0 + PARAMS['cool_r'] * wc,
                            1.0 + PARAMS['cool_g'] * wc,
                            1.0 + PARAMS['cool_b'] * wc], axis=-1)
    return disp


def pipeline_neutral(al2_code):
    """Neutral technical conversion (no creative grade):
    Apple Log 2 -> Rec.709 linear -> gamma 2.4 code. Used for BEFORE renders."""
    lin_awg = al2_decode(al2_code)
    lin709 = apply_matrix(M_AWG_TO_709, lin_awg)
    return gamma24_encode(lin709)


def pipeline_creative(al2_code):
    """Full standalone pipeline (what the .cube bakes):
    Apple Log 2 decode -> AWG->709 -> GOLDEN DAYLIGHT CINEMA grade -> gamma 2.4."""
    lin_awg = al2_decode(al2_code)
    lin709 = apply_matrix(M_AWG_TO_709, lin_awg)
    disp = grade(lin709)
    return gamma24_encode(disp)


# ----------------------------------------------------------------------------
# 5. Simulation of Apple Log 2 footage from sRGB stills (documented assumption)
# ----------------------------------------------------------------------------
def srgb_decode(c):
    """sRGB code [0,1] -> display-linear (IEC 61966-2-1)."""
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb_encode(x):
    x = np.asarray(x, float)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.clip(x, 0, None) ** (1 / 2.4) - 0.055)


def simulate_apple_log2(img_srgb01, exposure_stops=0.0):
    """Simulate Apple Log 2 / Apple Wide Gamut footage from an sRGB still.

    Documented assumptions (see VALIDATION_REPORT.txt):
      * the sRGB still, decoded to linear light, is treated as a scene-linear
        Rec.709 proxy of the scene (system gamma 1.0), then converted to
        Apple Wide Gamut primaries and encoded with the official Apple Log 2
        transfer function;
      * values are quantised to 10-bit full range, matching ProRes capture;
      * this is NOT iPhone sensor footage: an SDR still cannot reconstruct the
        full dynamic range of a real Log 2 capture (highlights above ~2.5 stops
        over 18% grey do not exist in the source).
    """
    lin709 = srgb_decode(img_srgb01) * (2.0 ** exposure_stops)
    lin_awg = apply_matrix(M_709_TO_AWG, lin709)
    code = al2_encode(np.clip(lin_awg, AL2_R0, None))
    code10 = np.round(np.clip(code, 0.0, 1.0) * 1023.0) / 1023.0  # 10-bit full range
    return code10


# ----------------------------------------------------------------------------
# 6. Self tests
# ----------------------------------------------------------------------------
def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"  [{status}] {name} {detail}")

    print("Apple Log 2 transfer function (vs white paper anchor table):")
    check("0%   -> 0.150477", abs(al2_encode(0.0) - 0.150477) < 5e-6, f"got {al2_encode(0.0):.6f}")
    check("18%  -> 0.488272", abs(al2_encode(0.18) - 0.488272) < 5e-6, f"got {al2_encode(0.18):.6f}")
    check("90%  -> 0.681686", abs(al2_encode(0.9) - 0.681686) < 5e-6, f"got {al2_encode(0.9):.6f}")
    # the published constants are rounded to 8 decimals, so code 1.0 decodes to
    # 12.000002 rather than exactly 12 (1200% of reference white)
    check("1200%-> 1.0     ", abs(al2_decode(1.0) - 12.0) < 5e-5, f"code 1.0 -> {al2_decode(1.0):.6f}")
    r = np.linspace(AL2_R0, 20.0, 20001)  # below R0 the white paper encodes 0 by definition
    check("encode/decode roundtrip", np.max(np.abs(al2_decode(al2_encode(r)) - r)) < 1e-9)
    p = np.linspace(-0.1, 1.0, 20001)
    rr = al2_decode(p)
    check("decode/encode roundtrip", np.max(np.abs(al2_encode(rr) - np.clip(p, 0, None))) < 1e-9)

    print("Apple Wide Gamut matrix (cross-check vs OpenColorIO AWG->ACES2065-1):")
    # OCIO: src/OpenColorIO/builtinconfigs/configs/studio-config-v5.0.0_aces-v2.1_ocio-v2.6.ocio
    OCIO_AWG_TO_AP0 = np.array([
        [0.694961049318096, 0.241405268785364, 0.06363368189654],
        [0.0473627464149326, 1.00429592505428, -0.0516586714692157],
        [-0.021989789359883, -0.0289891049714743, 1.05097889433136]])
    M_AP0_TO_XYZ = rgb_to_xyz_matrix(AP0_PRIMARIES, AP0_WHITE)
    MBR = np.array([[0.8951, 0.2664, -0.1614],
                    [-0.7502, 1.7135, 0.0367],
                    [0.0389, -0.0685, 1.0296]])
    w_s = MBR @ (M_AWG_TO_XYZ @ np.array([1, 1, 1]))       # AWG white (D65) in cone space
    w_d = MBR @ (M_AP0_TO_XYZ @ np.array([1, 1, 1]))       # AP0 white in cone space
    M_CAT = np.linalg.inv(MBR) @ np.diag(w_d / w_s) @ MBR  # Bradford D65 -> AP0 white
    mine = np.linalg.inv(M_AP0_TO_XYZ) @ M_CAT @ M_AWG_TO_XYZ  # AWG RGB -> AP0 RGB
    err = np.max(np.abs(mine - OCIO_AWG_TO_AP0))
    check("AWG->AP0 matrix matches OCIO", err < 1e-9, f"max abs diff {err:.2e}")

    print("Tone curve:")
    xs = np.linspace(0, 12, 200001)
    ys = tone_curve(xs)
    check("monotonic", np.all(np.diff(ys) >= -1e-12))
    check("never brightens above midgrey", np.all(ys[xs >= 0.18] <= xs[xs >= 0.18] + 1e-9))
    check("18% grey mapped", abs(_TONE.eval(0.18) - 0.128) < 1e-9)

    print("Neutrality / sanity:")
    g = np.linspace(0, 1, 101)
    out = pipeline_creative(np.stack([g, g, g], -1))
    d = np.max(np.abs(out - out[..., :1])) * 255.0  # max channel deviation, 8-bit codes
    # the grade keeps the grey axis exactly neutral above the deep-shadow zone;
    # below it a deliberate, very subtle cool split-tone is applied (see report)
    check("neutral axis deviation <= 1.5 codes (8-bit)", d <= 1.5, f"max dev {d:.3f}/255")
    hi = g[g > 0.60]  # above the cool-shadow zone (AL2 code ~0.46 and up)
    outh = pipeline_creative(np.stack([hi, hi, hi], -1))
    check("whites/highlights exactly neutral (float eps)",
          np.max(np.abs(outh - outh[..., :1])) < 1e-12)
    out = pipeline_creative(np.random.RandomState(0).rand(20000, 3))
    check("no NaN / inf in creative pipeline", np.all(np.isfinite(out)))
    check("output within [0,1]", out.min() >= 0.0 and out.max() <= 1.0)
    print("ALL SELF TESTS PASSED" if ok else "SELF TEST FAILURES - see above")
    return ok


if __name__ == "__main__":
    import sys
    sys.exit(0 if self_test() else 1)
