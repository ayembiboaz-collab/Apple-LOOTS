"""
GOLDEN DAYLIGHT CINEMA — Core Color Science & LUT Pipeline

Implements:
1. Official Apple Log / Apple Log 2 transfer function (encoding & decoding).
2. Apple Wide Gamut primaries -> CIE XYZ -> Rec.709 (D65) & ACES2065-1 (AP0, Bradford CAT).
3. Smooth perceptual gamut compression & filmic tone-mapping with golden-daylight
   selective chromatic sculpting.
4. Standard 33x33x33 .cube writer and tetrahedral 3D LUT evaluator.
5. Deterministic SDR -> Simulated Apple Log 2 plate converter for testing.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 1. Verified Apple Log / Apple Log 2 Transfer Function Constants
#    Source: Apple Log Profile White Paper (Sept 2023) &
#            Apple Log 2 White Paper (Sept 2025) via OpenColorIO AppleCameras.cpp
# ---------------------------------------------------------------------------
APPLE_LOG_R0 = -0.05641088
APPLE_LOG_RT = 0.01
APPLE_LOG_C = 47.28711236
APPLE_LOG_BETA = 0.00964052
APPLE_LOG_GAMMA = 0.08550479
APPLE_LOG_DELTA = 0.69336945
APPLE_LOG_PT = APPLE_LOG_C * (APPLE_LOG_RT - APPLE_LOG_R0) ** 2

# ---------------------------------------------------------------------------
# 2. Chromaticity Coordinates (CIE 1931 xy)
# ---------------------------------------------------------------------------
PRIMARIES_APPLE_WIDE_GAMUT = {
    "r": (0.7250, 0.3010),
    "g": (0.2210, 0.8140),
    "b": (0.0680, -0.0760),
    "w": (0.3127, 0.3290),  # D65
}

PRIMARIES_REC709 = {
    "r": (0.6400, 0.3300),
    "g": (0.3000, 0.6000),
    "b": (0.1500, 0.0600),
    "w": (0.3127, 0.3290),  # D65
}

PRIMARIES_ACES_AP0 = {
    "r": (0.7347, 0.2653),
    "g": (0.0000, 1.0000),
    "b": (0.0001, -0.0770),
    "w": (0.32168, 0.33767),  # ACES D60
}

PRIMARIES_ACES_AP1 = {
    "r": (0.713, 0.293),
    "g": (0.165, 0.830),
    "b": (0.128, 0.044),
    "w": (0.32168, 0.33767),  # ACES D60
}

# Bradford Cone Response Matrix
M_BRADFORD = np.array([
    [0.8951000, 0.2664000, -0.1614000],
    [-0.7502000, 1.7135000, 0.0367000],
    [0.0389000, -0.0685000, 1.0296000],
], dtype=np.float64)


def xy_to_XYZ(xy: tuple[float, float]) -> np.ndarray:
    x, y = xy
    return np.array([x / y, 1.0, (1.0 - x - y) / y], dtype=np.float64)


def rgb_to_xyz_matrix(primaries: dict) -> np.ndarray:
    Xr, Yr, Zr = xy_to_XYZ(primaries["r"])
    Xg, Yg, Zg = xy_to_XYZ(primaries["g"])
    Xb, Yb, Zb = xy_to_XYZ(primaries["b"])
    W = xy_to_XYZ(primaries["w"])

    M = np.array([
        [Xr, Xg, Xb],
        [Yr, Yg, Yb],
        [Zr, Zg, Zb],
    ], dtype=np.float64)
    S = np.linalg.solve(M, W)
    return M * S[np.newaxis, :]


def bradford_cat_matrix(src_white_xy: tuple[float, float], dst_white_xy: tuple[float, float]) -> np.ndarray:
    if np.allclose(src_white_xy, dst_white_xy, atol=1e-12):
        return np.eye(3, dtype=np.float64)
    src_W = xy_to_XYZ(src_white_xy)
    dst_W = xy_to_XYZ(dst_white_xy)
    src_cone = M_BRADFORD @ src_W
    dst_cone = M_BRADFORD @ dst_W
    scale = np.diag(dst_cone / src_cone)
    return np.linalg.inv(M_BRADFORD) @ scale @ M_BRADFORD


def build_rgb_to_rgb_matrix(src_primaries: dict, dst_primaries: dict) -> np.ndarray:
    M_src = rgb_to_xyz_matrix(src_primaries)
    M_dst = rgb_to_xyz_matrix(dst_primaries)
    M_cat = bradford_cat_matrix(src_primaries["w"], dst_primaries["w"])
    return np.linalg.inv(M_dst) @ M_cat @ M_src


M_AWG_TO_REC709 = build_rgb_to_rgb_matrix(PRIMARIES_APPLE_WIDE_GAMUT, PRIMARIES_REC709)
M_REC709_TO_AWG = build_rgb_to_rgb_matrix(PRIMARIES_REC709, PRIMARIES_APPLE_WIDE_GAMUT)
M_AWG_TO_AP0 = build_rgb_to_rgb_matrix(PRIMARIES_APPLE_WIDE_GAMUT, PRIMARIES_ACES_AP0)

# Rec.709 luma coefficients (ITU-R BT.709)
LUMA_REC709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


# ---------------------------------------------------------------------------
# 3. Transfer Functions (Apple Log 2, sRGB, Gamma 2.4)
# ---------------------------------------------------------------------------
def apple_log_to_linear(p: np.ndarray) -> np.ndarray:
    """Decode Apple Log / Apple Log 2 signal P to scene-linear reflection R."""
    p = np.asarray(p, dtype=np.float64)
    out = np.empty_like(p)
    high = p >= APPLE_LOG_PT
    mid = (p >= 0.0) & (~high)
    low = p < 0.0
    out[high] = np.power(2.0, (p[high] - APPLE_LOG_DELTA) / APPLE_LOG_GAMMA) - APPLE_LOG_BETA
    out[mid] = np.sqrt(p[mid] / APPLE_LOG_C) + APPLE_LOG_R0
    out[low] = APPLE_LOG_R0
    return out


def linear_to_apple_log(r: np.ndarray) -> np.ndarray:
    """Encode scene-linear reflection R to Apple Log / Apple Log 2 signal P."""
    r = np.asarray(r, dtype=np.float64)
    out = np.empty_like(r)
    high = r >= APPLE_LOG_RT
    mid = (r >= APPLE_LOG_R0) & (~high)
    low = r < APPLE_LOG_R0
    out[high] = APPLE_LOG_GAMMA * np.log2(r[high] + APPLE_LOG_BETA) + APPLE_LOG_DELTA
    out[mid] = APPLE_LOG_C * (r[mid] - APPLE_LOG_R0) ** 2
    out[low] = 0.0
    return out


def srgb_to_linear(v: np.ndarray) -> np.ndarray:
    v = np.clip(np.asarray(v, dtype=np.float64), 0.0, 1.0)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def linear_to_srgb(l: np.ndarray) -> np.ndarray:
    l = np.clip(np.asarray(l, dtype=np.float64), 0.0, 1.0)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * np.power(l, 1.0 / 2.4) - 0.055)


def linear_to_gamma24(l: np.ndarray) -> np.ndarray:
    l = np.clip(np.asarray(l, dtype=np.float64), 0.0, 1.0)
    return np.power(l, 1.0 / 2.4)


def gamma24_to_linear(v: np.ndarray) -> np.ndarray:
    v = np.clip(np.asarray(v, dtype=np.float64), 0.0, 1.0)
    return np.power(v, 2.4)


# ---------------------------------------------------------------------------
# 4. Simulated Apple Log 2 Converter (for SDR reference plates)
# ---------------------------------------------------------------------------
def sdr_srgb_to_simulated_apple_log2(img_srgb_01: np.ndarray) -> np.ndarray:
    """
    Documented simulation: converts an SDR sRGB [0, 1] image into a simulated
    Apple Log 2 [0, 1] signal in Apple Wide Gamut.

    Steps:
      1. Decode sRGB EOTF -> linear Rec.709 display light [0, 1].
      2. Inverse display shoulder above 0.72 linear to restore realistic
         midday highlight headroom (~2.2x scene reflectance at 1.0 SDR white)
         and add subtle 0.003 scene black floor while keeping 0.18 mid-gray intact.
      3. Matrix Linear Rec.709 (D65) -> Linear Apple Wide Gamut (D65).
      4. Encode with official Apple Log 2 OETF.
    """
    lin709 = srgb_to_linear(img_srgb_01)

    # Smooth luminance-preserving inverse shoulder above 0.70 while anchoring 0.18 near 0.18
    # Preserves original hue ratios rather than distorting saturated highlights per-channel.
    lum = np.sum(lin709 * LUMA_REC709, axis=-1, keepdims=True)
    knee = 0.70
    excess = np.maximum(lum - knee, 0.0) / (1.0 - knee)
    lum_expanded = lum + (1.0 - knee) * (4.0 * np.power(excess, 2.1))
    scale = lum_expanded / np.maximum(lum, 1e-6)
    scene_lin709 = np.where(lum > 1e-6, lin709 * scale, lin709) * 0.996 + 0.003

    # Convert Rec.709 linear -> Apple Wide Gamut linear
    awg_lin = scene_lin709 @ M_REC709_TO_AWG.T

    # Encode with Apple Log 2 transfer function
    log2 = linear_to_apple_log(awg_lin)
    return np.clip(log2, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 5. Creative Grade Parameters & Analytic Pipeline
# ---------------------------------------------------------------------------
@dataclass
class GradeParams:
    # Scene-linear exposure multiplier (keeps bright midday controlled)
    exposure_mult: float = 0.90
    # Black floor offset before filmic curve
    black_floor: float = 0.0010
    # Filmic S-curve parameters
    mid_gray_target: float = 0.168     # display linear target for 0.18 scene linear
    contrast: float = 1.22             # rich midtone dimensionality
    shadow_toe_strength: float = 0.28  # deep yet detailed shadows without crush
    highlight_rolloff: float = 0.64    # smooth compression of scene highlights up to ~12.0
    # Highlight filmic desaturation (path-to-white only in true highlights > 0.62 display linear)
    highlight_desat_start: float = 0.62
    highlight_desat_amount: float = 0.65
    # Multiplicative shadow-vs-sunlight color separation (luminance-balanced in linear Rec.709)
    # Shadows: cool slate skylight; Midtones: true honey-gold (hue_ratio ~0.76, zero pink cast)
    shadow_cool_gain: tuple[float, float, float] = (0.948, 0.996, 1.064)
    midtone_warm_gain: tuple[float, float, float] = (1.038, 1.014, 0.908)
    # Selective hue-region sculpting strengths
    sky_blue_sat: float = 1.10
    sky_blue_lum: float = 0.89
    sky_hue_shift_deg: float = 5.5      # pulls cyan-blue gently toward Mediterranean cerulean
    green_sat: float = 0.86
    green_lum: float = 0.93
    green_warm_shift_deg: float = -6.5  # pulls digital green gently toward warm olive/cypress
    warm_sat_knee: float = 0.86         # soft saturation compression for extreme orange/amber (protects golden hour)
    skin_sat_protect: float = 0.95      # keeps skin natural without orange/red saturation spike
    global_sat: float = 1.04            # restrained overall richness


def _rgb_to_hsv_vec(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized HSV from non-negative linear/display RGB (last axis = 3). Hue in [0, 360)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    h = np.zeros_like(cmax)
    mask = delta > 1e-8
    rm = mask & (cmax == r)
    gm = mask & (cmax == g)
    bm = mask & (cmax == b)
    h[rm] = 60.0 * (((g[rm] - b[rm]) / delta[rm]) % 6.0)
    h[gm] = 60.0 * (((b[gm] - r[gm]) / delta[gm]) + 2.0)
    h[bm] = 60.0 * (((r[bm] - g[bm]) / delta[bm]) + 4.0)

    s = np.where(cmax > 1e-8, delta / cmax, 0.0)
    v = cmax
    return h, s, v


def _hsv_to_rgb_vec(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    h = np.mod(h, 360.0)
    c = v * s
    x = c * (1.0 - np.abs(np.mod(h / 60.0, 2.0) - 1.0))
    m = v - c

    rp = np.zeros_like(h)
    gp = np.zeros_like(h)
    bp = np.zeros_like(h)

    i = (h >= 0) & (h < 60)
    rp[i], gp[i], bp[i] = c[i], x[i], 0.0
    i = (h >= 60) & (h < 120)
    rp[i], gp[i], bp[i] = x[i], c[i], 0.0
    i = (h >= 120) & (h < 180)
    rp[i], gp[i], bp[i] = 0.0, c[i], x[i]
    i = (h >= 180) & (h < 240)
    rp[i], gp[i], bp[i] = 0.0, x[i], c[i]
    i = (h >= 240) & (h < 300)
    rp[i], gp[i], bp[i] = x[i], 0.0, c[i]
    i = (h >= 300) & (h < 360)
    rp[i], gp[i], bp[i] = c[i], 0.0, x[i]

    return np.stack([rp + m, gp + m, bp + m], axis=-1)


def _hue_weight(h_deg: np.ndarray, center_deg: float, half_width_deg: float) -> np.ndarray:
    """Smooth raised-cosine hue weight in [0, 1]."""
    diff = np.abs((h_deg - center_deg + 180.0) % 360.0 - 180.0)
    t = np.clip(diff / half_width_deg, 0.0, 1.0)
    return 0.5 * (1.0 + np.cos(np.pi * t))


def soft_gamut_compress_rec709(rgb: np.ndarray, threshold: float = 0.965, limit: float = 1.85) -> np.ndarray:
    """
    Smoothly compresses out-of-gamut (negative) linear Rec.709 colors toward
    the achromatic axis while leaving in-gamut colors untouched.
    Inspired by ACES Reference Gamut Compression (smooth hyperbolic knee).
    """
    achromatic = np.max(rgb, axis=-1, keepdims=True)
    achromatic_safe = np.maximum(achromatic, 1e-5)
    # Distance from achromatic normalized by max component
    dist = (achromatic - rgb) / achromatic_safe
    max_dist = np.max(dist, axis=-1, keepdims=True)

    # Only compress when dist > threshold (note: dist == 1.0 is the Rec.709 boundary!)
    # We start softly at threshold=0.82 and map limit=1.65 -> 1.0
    excess = np.maximum(dist - threshold, 0.0)
    scale = 1.0 - threshold
    # Smooth rational rolloff: maps [0, inf) -> [0, 1 - threshold)
    # Calibrated so dist=limit maps just inside 1.0
    k = (limit - threshold) / (1.0 - threshold) - 1.0
    k = max(k, 0.25)
    compressed_excess = scale * (excess / (excess + scale * k))
    new_dist = np.where(dist > threshold, threshold + compressed_excess, dist)

    # Apply proportional compression to channels based on max_dist
    out = achromatic - new_dist * achromatic_safe
    return np.maximum(out, 0.0)


def filmic_tone_curve(x: np.ndarray, params: GradeParams) -> np.ndarray:
    """
    Smooth, strictly monotonic filmic tone-curve mapping scene-linear [0, ~12]
    to display-linear [0, 1] with detailed shadow toe and silky highlight roll-off.
    """
    x = np.maximum(x, 0.0)
    # Anchor 0.18 scene linear around params.mid_gray_target
    # Use log-domain sigmoid / Michaelis-Menten hybrid
    pivot = 0.18
    # Lift tiny black floor smoothly
    x_adj = x + params.black_floor

    # Smooth power-weighted rational tone curve (Reinhard-extended / AgX-style)
    # y(x) = (x_c)^p / ((x_c)^p + a) * scale
    # Choose p = params.contrast, calibrate a so y(pivot) = mid_gray_target
    # Also ensure highlights at x=12.0 approach ~0.992 cleanly
    p = params.contrast
    # Toe blend: softens very low end so shadows have smooth filmic roll
    toe = params.shadow_toe_strength
    x_toe = np.where(
        x_adj < 0.04,
        x_adj * (1.0 - toe * 0.25 * (1.0 - x_adj / 0.04)),
        x_adj,
    )

    # Dual-slope rational curve for highlight headroom up to 12.0
    # First compress extreme scene highlights smoothly with a log shoulder
    shoulder_pivot = 0.35
    excess_hi = np.maximum(x_toe - shoulder_pivot, 0.0)
    x_comp = np.where(
        x_toe > shoulder_pivot,
        shoulder_pivot + excess_hi / (1.0 + params.highlight_rolloff * np.power(excess_hi / 1.8, 0.85)),
        x_toe,
    )

    # Calibrate rational curve y = u^p / (u^p + c_val)
    # Let max_x = x_comp at x=12.0 -> normalize so y(12.0) ~ 0.995
    def _comp_scalar(v: float) -> float:
        vt = v + params.black_floor
        if vt < 0.04:
            vt = vt * (1.0 - toe * 0.25 * (1.0 - vt / 0.04))
        if vt > shoulder_pivot:
            vt = shoulder_pivot + (vt - shoulder_pivot) / (1.0 + params.highlight_rolloff * ((vt - shoulder_pivot) / 1.8) ** 0.85)
        return vt

    piv_c = _comp_scalar(pivot)
    max_c = _comp_scalar(11.98)

    # Solve for c_val such that piv_c^p / (piv_c^p + c_val) * norm = mid_gray_target
    # First solve with norm=1, then refine norm = 1 / (max_c^p / (max_c^p + c_val))
    c_val = (piv_c ** p) * (1.0 - params.mid_gray_target) / params.mid_gray_target
    for _ in range(5):
        y_max = (max_c ** p) / (max_c ** p + c_val)
        target_raw = params.mid_gray_target * y_max / 0.994
        c_val = (piv_c ** p) * (1.0 - target_raw) / target_raw

    xp = np.power(np.maximum(x_comp, 0.0), p)
    y = (xp / (xp + c_val)) / ((max_c ** p) / (max_c ** p + c_val)) * 0.994

    # Subtract tiny residual at x=0 and renormalize to hit [0, 0.994..1.0]
    y0 = (_comp_scalar(0.0) ** p / (_comp_scalar(0.0) ** p + c_val)) / ((max_c ** p) / (max_c ** p + c_val)) * 0.994
    y = (y - y0 * 0.85) / (1.0 - y0 * 0.85)
    return np.clip(y, 0.0, 1.0)


def apply_golden_daylight_grade(apple_log2_rgb: np.ndarray, params: GradeParams | None = None) -> np.ndarray:
    """
    Full standalone pipeline:
      Apple Log 2 (Apple Wide Gamut) -> Rec.709 SDR Gamma 2.4 [0, 1]
    """
    if params is None:
        params = GradeParams()

    # 1. Decode Apple Log 2 -> Scene Linear Apple Wide Gamut
    awg_lin = apple_log_to_linear(apple_log2_rgb)

    # 2. Convert Linear Apple Wide Gamut (D65) -> Linear Rec.709 (D65)
    rec709_lin = awg_lin @ M_AWG_TO_REC709.T

    # 3. Soft gamut compression for out-of-Rec.709 colors
    rec709_lin = soft_gamut_compress_rec709(rec709_lin)

    # 4. Midday exposure control
    rec709_lin = rec709_lin * params.exposure_mult

    # 5. Scene-linear sun/shade chromatic separation (multiplicative, preserves blacks & hue purity)
    lum = np.sum(rec709_lin * LUMA_REC709, axis=-1, keepdims=True)
    # Shadow mask peaks around lum ~ 0.025, smoothly zero at pure black and above 0.14
    shadow_w = np.exp(-((np.log2(np.maximum(lum, 1e-4)) - np.log2(0.025)) / 1.35) ** 2)
    shadow_w *= np.clip(lum / 0.006, 0.0, 1.0)  # protect pure black neutrality
    # Midtone sunlight mask peaks around lum ~ 0.25, tapers cleanly off in pure highlights
    mid_w = np.exp(-((np.log2(np.maximum(lum, 1e-4)) - np.log2(0.25)) / 1.50) ** 2)
    mid_w *= np.clip(1.0 - (lum - 0.65) / 1.25, 0.10, 1.0)

    s_gain = np.array(params.shadow_cool_gain, dtype=np.float64)
    m_gain = np.array(params.midtone_warm_gain, dtype=np.float64)
    gain = 1.0 + shadow_w * (s_gain - 1.0) + mid_w * (m_gain - 1.0)
    rec709_lin = np.maximum(rec709_lin * gain, 0.0)

    # 6. Filmic Tone Mapping (92% luminance-preserving ratio + 8% per-channel roll)
    #    Keeps warm stone/gold true honey-amber instead of shifting orange/gold toward pink.
    lum_pre = np.maximum(np.sum(rec709_lin * LUMA_REC709, axis=-1, keepdims=True), 1e-7)
    lum_mapped = filmic_tone_curve(lum_pre, params)
    rgb_ch_mapped = filmic_tone_curve(rec709_lin, params)

    rgb_lum_pres = rec709_lin * (lum_mapped / lum_pre)
    disp_lin = 0.92 * rgb_lum_pres + 0.08 * rgb_ch_mapped
    disp_lin = np.clip(disp_lin, 0.0, 1.0)

    # 7. Path-to-White Highlight Desaturation (keeps clouds, white linen, bright sand clean)
    disp_lum = np.sum(disp_lin * LUMA_REC709, axis=-1, keepdims=True)
    hi_t = np.clip((disp_lum - params.highlight_desat_start) / (1.0 - params.highlight_desat_start), 0.0, 1.0)
    hi_desat = params.highlight_desat_amount * (hi_t ** 1.75)
    disp_lin = disp_lin * (1.0 - hi_desat) + disp_lum * hi_desat

    # 8. Selective Hue-Region Sculpting in Display-Linear Space
    #    (Skies, Foliage Greens, Skin & Golden Hour Saturation Knee)
    h, s, v = _rgb_to_hsv_vec(disp_lin)

    # Mask out near-neutrals so whites/grays/concrete stay completely clean!
    sat_gate = np.clip((s - 0.06) / 0.16, 0.0, 1.0)

    # 8a. Sky & Mediterranean Blues (centered ~215 deg, width 42 deg)
    w_sky = _hue_weight(h, 215.0, 42.0) * sat_gate
    sky_bright = np.clip((v - 0.15) / 0.45, 0.0, 1.0)
    w_cyan_sky = _hue_weight(h, 198.0, 24.0) * sat_gate * sky_bright
    h = h + params.sky_hue_shift_deg * w_cyan_sky
    s = s * (1.0 + (params.sky_blue_sat - 1.0) * w_sky * sky_bright)
    v = v * (1.0 + (params.sky_blue_lum - 1.0) * w_sky * sky_bright)

    # 8b. Greenery / Foliage (centered ~108 deg, width 42 deg)
    w_green = _hue_weight(h, 108.0, 42.0) * sat_gate
    h = h + params.green_warm_shift_deg * w_green
    s = s * (1.0 + (params.green_sat - 1.0) * w_green)
    v = v * (1.0 + (params.green_lum - 1.0) * w_green)

    # 8c. Skin & Warm Sunset / Golden-Hour Protection (centered ~28 deg, width 34 deg)
    #     Softly compress extreme saturation (>0.45) so golden hour never turns neon orange,
    #     and protect skin tones from orange/red saturation spikes.
    w_warm = _hue_weight(h, 28.0, 34.0) * sat_gate
    high_sat = np.clip((s - 0.45) / 0.35, 0.0, 1.0)
    s = s * (1.0 - (1.0 - params.warm_sat_knee) * w_warm * high_sat)
    w_skin = _hue_weight(h, 20.0, 15.0) * sat_gate
    s = s * (1.0 - (1.0 - params.skin_sat_protect) * w_skin * (1.0 - 0.4 * high_sat))

    # 8d. Global subtle saturation polish (preserving neutrals)
    s = s * (1.0 + (params.global_sat - 1.0) * sat_gate)
    s = np.clip(s, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    disp_lin = _hsv_to_rgb_vec(h, s, v)
    disp_lin = np.clip(disp_lin, 0.0, 1.0)

    # 9. Encode Rec.709 Gamma 2.4
    return linear_to_gamma24(disp_lin)


# ---------------------------------------------------------------------------
# 6. .cube LUT Generation & Tetrahedral Interpolation Evaluator
# ---------------------------------------------------------------------------
def build_3d_lut(size: int = 33, params: GradeParams | None = None) -> np.ndarray:
    """
    Builds a (size, size, size, 3) 3D LUT array indexed as [r, g, b, channel].
    """
    axis = np.linspace(0.0, 1.0, size, dtype=np.float64)
    rr, gg, bb = np.meshgrid(axis, axis, axis, indexing="ij")
    grid = np.stack([rr, gg, bb], axis=-1)
    lut = apply_golden_daylight_grade(grid, params=params)
    return np.clip(lut, 0.0, 1.0)


def write_cube_file(filepath: str, lut_rgb: np.ndarray, title: str = "GOLDEN_DAYLIGHT_CINEMA") -> None:
    """
    Writes a standard Adobe/Iridas .cube 3D LUT file.
    Per .cube specification: Red varies fastest, then Green, then Blue.
    """
    size = lut_rgb.shape[0]
    assert lut_rgb.shape == (size, size, size, 3)

    lines = [
        f"# Created for iPhone 17 Pro Apple Log 2 (Apple Wide Gamut) -> Rec.709 Gamma 2.4",
        f"# Compatible with Blackmagic Camera for iOS, DaVinci Resolve, Final Cut Pro, Premiere Pro",
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {size}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
        "",
    ]
    # Reorder from [r, g, b, 3] to [b, g, r, 3] so R varies fastest in row-major C order
    ordered = np.transpose(lut_rgb, (2, 1, 0, 3)).reshape(-1, 3)
    for r, g, b in ordered:
        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def read_cube_file(filepath: str) -> tuple[int, np.ndarray, dict]:
    """
    Parses a .cube 3D LUT file and returns (size, lut[r, g, b, 3], metadata).
    """
    size = None
    domain_min = [0.0, 0.0, 0.0]
    domain_max = [1.0, 1.0, 1.0]
    title = ""
    values = []

    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("TITLE"):
                title = line.split(None, 1)[1].strip().strip('"')
            elif line.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
            elif line.startswith("DOMAIN_MIN"):
                domain_min = [float(x) for x in line.split()[1:4]]
            elif line.startswith("DOMAIN_MAX"):
                domain_max = [float(x) for x in line.split()[1:4]]
            else:
                parts = line.split()
                if len(parts) == 3:
                    values.append([float(parts[0]), float(parts[1]), float(parts[2])])

    assert size is not None, "Missing LUT_3D_SIZE"
    arr = np.array(values, dtype=np.float64)
    assert arr.shape == (size ** 3, 3), f"Expected {size**3} rows, got {arr.shape[0]}"
    # File has [b, g, r, 3]; transpose back to [r, g, b, 3]
    lut = np.transpose(arr.reshape(size, size, size, 3), (2, 1, 0, 3)).copy()
    return size, lut, {"title": title, "domain_min": domain_min, "domain_max": domain_max}


def apply_3d_lut_tetrahedral(img_01: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """
    Applies a [N, N, N, 3] 3D LUT to an image (..., 3) in [0, 1] using exact
    tetrahedral interpolation (industry standard in DaVinci Resolve / OCIO).
    """
    N = lut.shape[0]
    img = np.clip(np.asarray(img_01, dtype=np.float64), 0.0, 1.0)
    scaled = img * (N - 1)

    i0 = np.floor(scaled).astype(np.int32)
    i0 = np.minimum(i0, N - 2)
    f = scaled - i0

    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0], f[..., 1], f[..., 2]

    # 8 cube corners (flat helper via advanced indexing)
    c000 = lut[r0, g0, b0]
    c111 = lut[r0 + 1, g0 + 1, b0 + 1]
    c100 = lut[r0 + 1, g0, b0]
    c010 = lut[r0, g0 + 1, b0]
    c001 = lut[r0, g0, b0 + 1]
    c110 = lut[r0 + 1, g0 + 1, b0]
    c101 = lut[r0 + 1, g0, b0 + 1]
    c011 = lut[r0, g0 + 1, b0 + 1]

    out = np.empty_like(img)

    # 6-tetrahedra decomposition
    m1 = (fr >= fg) & (fg >= fb)
    m2 = (fr >= fb) & (fb > fg)
    m3 = (fb > fr) & (fr >= fg)
    m4 = (fg > fr) & (fr >= fb)
    m5 = (fg >= fb) & (fb > fr)
    m6 = (fb > fg) & (fg > fr)

    def _interp(mask, wa, a, wb, b, wc, c):
        if np.any(mask):
            out[mask] = (
                c000[mask]
                + wa[mask, None] * (a[mask] - c000[mask])
                + wb[mask, None] * (b[mask] - a[mask])
                + wc[mask, None] * (c[mask] - b[mask])
            )

    _interp(m1, fr, c100, fg, c110, fb, c111)
    _interp(m2, fr, c100, fb, c101, fg, c111)
    _interp(m3, fb, c001, fr, c101, fg, c111)
    _interp(m4, fg, c010, fr, c110, fb, c111)
    _interp(m5, fg, c010, fb, c011, fr, c111)
    _interp(m6, fb, c001, fg, c011, fr, c111)

    return np.clip(out, 0.0, 1.0)
