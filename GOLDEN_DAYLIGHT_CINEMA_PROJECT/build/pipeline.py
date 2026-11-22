"""Golden Daylight Cinema — scene-referred grade pipeline.

Single source of truth for the analytic pipeline.  Everything here is
float64 and works in linear/OKLab space.  The same functions are used by the
33^3 cube baker and by the analysis code.  Previews are rendered by an
*independent* .cube reader (see render_previews.py) to avoid re-running the
grading function.

Pipeline stages
---------------
1. Decode Apple Log 2 (transfer function)          -> linear Apple Wide Gamut
2. Apple Wide Gamut -> OKLab                        (via linear XYZ)
3. Filmic tone curve (toe / midtone / shoulder)
4. Density-style saturation (rich mids, thin highlights/shadows)
5. Luminance-weighted split-tone (warm mids, cool shadows)
6. Hue-selective chroma shaping (sky, foliage, stone, skin)
7. Highlight desaturation (whites stay natural)
8. Gamut-map into Rec.709 (chroma compression)
9. Encode -> Rec.709 gamma 2.4
"""

import numpy as np

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs


# ---------------------------------------------------------------------------
# Smooth helpers
# ---------------------------------------------------------------------------

def smoothstep(x, a, b):
    """Smooth S-curve from 0 at x<=a to 1 at x>=b (x, a, b) order."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ss(x, a, b):
    return smoothstep(x, a, b)


def gauss(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def lerp_angle(h0, h1, t):
    """Circular interpolation of hue angle."""
    d = (h1 - h0 + np.pi) % (2 * np.pi) - np.pi
    return (h0 + d * t) % (2 * np.pi)


# ---------------------------------------------------------------------------
# Tunable grade parameters (documented defaults)
# ---------------------------------------------------------------------------

DEFAULTS = dict(
    # Tonal curve
    toe_lift=0.05,
    toe_knee=0.24,
    upper_mid_gain=0.06,
    mid_pivot=0.52,
    mid_slope=1.13,
    shadow_darken=0.06,
    shoulder_knee=0.82,
    shoulder_width=0.34,
    shoulder_depth=0.14,
    whites_soft_knee=0.90,
    whites_soft_depth=0.04,
    # Saturation (density-style)
    sat_mid=0.16,
    sat_hi=-0.15,
    sat_lo=-0.17,
    sat_mid_mu=0.42,
    sat_mid_sigma=0.24,
    sat_hi_knee=0.78,
    sat_lo_knee=0.30,
    # Split-tone (warm mids / cool shadows)
    warm_mid_hue=0.80,
    warm_mid_chroma=0.030,
    warm_mid_mu=0.46,
    warm_mid_sigma=0.26,
    warm_mid_hue_strength=0.42,
    warm_high_hue=0.80,
    warm_high_strength=0.30,
    warm_high_knee=0.64,
    warm_high_chroma=0.022,
    cool_shadow_strength=0.09,
    cool_shadow_knee=0.34,
    cool_shadow_chroma=0.10,
    # Hue-selective shaping
    sky_lo=3.80,
    sky_hi=5.30,
    green_lo=1.90,
    green_hi=3.35,
    stone_lo=0.92,
    stone_hi=1.42,
    skin_lo=0.10,
    skin_hi=1.05,
    skin_hue_target=0.62,
    skin_protection=0.55,
    sky_sat_keep=0.94,
    sky_hue_target=4.42,
    sky_hue_target_strength=0.35,
    green_hue_target=2.62,
    green_hue_target_strength=0.24,
    yellow_green_warn=0.12,
    stone_hue_target=1.05,
    stone_hue_target_strength=0.24,
    stone_chroma_boost=0.07,
    # Highlights
    highlight_desat_knee=0.74,
    highlight_desat_depth=0.20,
    # Skin chroma cap
    skin_chroma_cap=0.135,
    skin_chroma_cap_strength=0.55,
)


# ---------------------------------------------------------------------------
# Analytic pipeline
# ---------------------------------------------------------------------------

def grade_oklab(ok, p=DEFAULTS):
    """Grade OKLab (L, a, b) values with the Golden Daylight Cinema look.

    ok: (..., 3) float array
    Returns: (..., 3) adjusted OKLab
    """
    L = np.maximum(ok[..., 0], 0.0)
    a = ok[..., 1].copy()
    b = ok[..., 2].copy()

    C_orig = np.sqrt(a * a + b * b)
    h = np.arctan2(b, a) % (2 * np.pi)

    # ---- 1. Filmic tone curve ---------------------------------------------
    # Toe: gentle, bounded shadow lift (never amplifies noise more than ~5%).
    toe_w = (1.0 - smoothstep(L, 0.0, p['toe_knee']))
    L = L + p['toe_lift'] * toe_w * np.maximum(p['toe_knee'] - L, 0.0) / p['toe_knee']

    # Slight deepening of deep shadows (contrast separation).
    shadow_darken_w = 1.0 - smoothstep(L, 0.02, 0.25)
    L = L * (1.0 - p['shadow_darken'] * shadow_darken_w)

    # Midtone pivot contrast: keeps the pivot point fixed, deepens shadows,
    # lifts upper-mids — classic filmic slope.  Applied only below the
    # highlight region so highlights stay intact for the shoulder.
    c_mid = p['mid_pivot']
    pivot_w = 1.0 - smoothstep(L, 0.68, 0.82)
    L = (L - c_mid) * (1.0 + (p['mid_slope'] - 1.0) * pivot_w) + c_mid

    # Highlight shoulder: smooth compression above knee.
    shoulder_w = smoothstep(L, p['shoulder_knee'], p['shoulder_knee'] + p['shoulder_width'])
    L = L * (1.0 - p['shoulder_depth'] * shoulder_w)

    # Gentle whites roll.
    white_w = smoothstep(L, p['whites_soft_knee'], p['whites_soft_knee'] + 0.26)
    L = L * (1.0 - p['whites_soft_depth'] * white_w)

    # ---- 2. Density-style saturation --------------------------------------
    # Rich in mids, thins toward whites and deep shadows.
    # Saturated blue skies are protected: richness is kept for sky hue so the
    # look is golden-warm rather than grey-hazy.
    white_w = 1.0 - smoothstep(C_orig, 0.02, 0.06)
    sky_protect0 = smoothstep(np.arctan2(b, a) % (2 * np.pi), p['sky_lo'], p['sky_lo'] + 0.22) * (1.0 - smoothstep(np.arctan2(b, a) % (2 * np.pi), p['sky_hi'] - 0.18, p['sky_hi'] + 0.18))
    sky_protect0 = np.clip(sky_protect0, 0.0, 1.0) * smoothstep(C_orig, 0.06, 0.12)
    mid_w = gauss(L, p['sat_mid_mu'], p['sat_mid_sigma'])
    hi_w = smoothstep(L, p['sat_hi_knee'], p['sat_hi_knee'] + 0.20) * white_w * (1.0 - 0.85 * sky_protect0)
    lo_w = 1.0 - smoothstep(L, 0.02, p['sat_lo_knee'])
    C = C_orig * (1.0 + p['sat_mid'] * mid_w + p['sat_hi'] * hi_w + p['sat_lo'] * lo_w)

    # ---- 3. Sky protection weight (hue-based, computed BEFORE warm shifts)
    sky_w0 = smoothstep(h, p['sky_lo'], p['sky_lo'] + 0.22) * (1.0 - smoothstep(h, p['sky_hi'] - 0.18, p['sky_hi'] + 0.18))
    sky_w0 = np.clip(sky_w0, 0.0, 1.0)
    not_sky = 1.0 - 0.82 * sky_w0

    # ---- 4. Luminance-weighted split-tone balance -------------------------
    # Warm amber shift in midtones/highlights, damped for sky hue so blues
    # stay natural (this is what makes the warmth look golden, not orange).
    warm_mid_w = gauss(L, p['warm_mid_mu'], p['warm_mid_sigma'])
    warm_high_w = smoothstep(L, p['warm_high_knee'], p['warm_high_knee'] + 0.24)
    neutral_damp = 0.35 + 0.65 * smoothstep(C_orig, 0.0, 0.08)
    C = C + (p['warm_mid_chroma'] * warm_mid_w + p['warm_high_chroma'] * warm_high_w) * neutral_damp * not_sky
    h = lerp_angle(h, p['warm_mid_hue'], warm_mid_w * p['warm_mid_hue_strength'] * not_sky)
    h = lerp_angle(h, p['warm_high_hue'], warm_high_w * p['warm_high_strength'] * not_sky)

    shadow_w = 1.0 - smoothstep(L, 0.04, p['cool_shadow_knee'])
    h = lerp_angle(h, 4.6, shadow_w * p['cool_shadow_strength'] * 0.6)
    C = C * (1.0 - p['cool_shadow_chroma'] * shadow_w * 0.5)

    # ---- 5. Hue-selective chroma shaping ----------------------------------
    # Sky / blue-cyan: natural blue, controlled cyan.
    sky_w = sky_w0
    C = C * (1.0 + (p['sky_sat_keep'] - 1.0) * sky_w)
    h = lerp_angle(h, p['sky_hue_target'], sky_w * p['sky_hue_target_strength'] * 0.5)

    # Foliage greens: natural, slightly warm, controlled saturation.
    green_w = smoothstep(h, p['green_lo'], p['green_lo'] + 0.18) * (1.0 - smoothstep(h, p['green_hi'] - 0.18, p['green_hi'] + 0.18))
    green_w = np.clip(green_w, 0.0, 1.0)
    yellow_green_w = smoothstep(h, 1.92, 2.10) * (1.0 - smoothstep(h, 2.42, 2.80))
    green_total = np.clip(green_w + yellow_green_w * 0.7, 0.0, 1.0)
    C = C * (1.0 - p['yellow_green_warn'] * green_total)
    h = lerp_angle(h, p['green_hue_target'], green_w * p['green_hue_target_strength'])

    # Stone / warm architecture: slightly richer, warmer.
    stone_w = smoothstep(h, p['stone_lo'], p['stone_lo'] + 0.18) * (1.0 - smoothstep(h, p['stone_hi'] - 0.15, p['stone_hi'] + 0.15))
    stone_w = np.clip(stone_w, 0.0, 1.0)
    C = C * (1.0 + p['stone_chroma_boost'] * stone_w)
    h = lerp_angle(h, p['stone_hue_target'], stone_w * p['stone_hue_target_strength'])

    # Skin protection: keep skin hues near the vectorscope skin line.
    skin_hue_w = smoothstep(h, p['skin_lo'], p['skin_lo'] + 0.14) * (1.0 - smoothstep(h, p['skin_hi'] - 0.10, p['skin_hi'] + 0.15))
    skin_hue_w = np.clip(skin_hue_w, 0.0, 1.0)
    skin_chroma_w = smoothstep(C, 0.012, 0.05) * (1.0 - smoothstep(C, 0.16, 0.26))
    skin_w = np.clip(skin_hue_w * skin_chroma_w, 0.0, 1.0) * p['skin_protection']
    h = lerp_angle(h, p['skin_hue_target'], skin_w * 0.55)
    # Smooth skin chroma cap: softens above-cap chroma without hard clipping.
    excess = np.maximum(C - p['skin_chroma_cap'], 0.0)
    C = C - excess * skin_w * p['skin_chroma_cap_strength'] * (excess / (p['skin_chroma_cap'] + excess + 1e-9))

    # ---- 5. Highlight desaturation -----------------------------------------
    sky_protect = np.clip(smoothstep(np.arctan2(b, a) % (2 * np.pi), p['sky_lo'], p['sky_lo'] + 0.22) * (1.0 - smoothstep(np.arctan2(b, a) % (2 * np.pi), p['sky_hi'] - 0.18, p['sky_hi'] + 0.18)), 0.0, 1.0) * smoothstep(C, 0.06, 0.12)
    hi_desat_w = smoothstep(L, p['highlight_desat_knee'], p['highlight_desat_knee'] + 0.22) * white_w * (1.0 - sky_protect)
    C = C * (1.0 - p['highlight_desat_depth'] * hi_desat_w)

    # ---- 6. Rebuild ----------------------------------------------------------
    out = cs.oklch_to_oklab(L, C, h)
    return out


def gamut_map_rec709(rgb_709, p=DEFAULTS, niter=34):
    """Smooth chroma compression into the Rec.709 gamut.

    rgb_709: (..., 3) linear Rec.709 values (may be out of gamut).
    Returns: (..., 3) linear Rec.709 values inside the gamut (soft clip).

    Method: hue-preserving chroma compression toward the neutral axis.
    At each pixel's (L, h), the maximum in-gamut chroma C_max is found by
    binary search; chroma beyond 0.85*C_max is then smoothly compressed.
    """
    ok = cs.rec709_linear_to_oklab(rgb_709)
    L = ok[..., 0]
    C = np.sqrt(ok[..., 1] ** 2 + ok[..., 2] ** 2)
    h = np.arctan2(ok[..., 2], ok[..., 1]) % (2 * np.pi)

    L_flat = np.maximum(L, 0.0).ravel()
    L_search = np.clip(L_flat, 0.02, 0.995)  # robust in-gamut root for search
    h_flat = h.ravel()
    C_flat = C.ravel()

    lo = np.zeros_like(C_flat)
    hi = np.full_like(C_flat, 0.45)
    for _ in range(niter):
        mid = (lo + hi) / 2.0
        ok_mid = np.stack([L_search, mid * np.cos(h_flat), mid * np.sin(h_flat)], axis=-1)
        rgb_mid = cs.oklab_to_rec709_linear(ok_mid)
        in_gamut = np.all(rgb_mid >= -1e-9, axis=-1) & np.all(rgb_mid <= 1.0 + 1e-9, axis=-1)
        lo = np.where(in_gamut, mid, lo)
        hi = np.where(in_gamut, hi, mid)
    C_max = np.maximum(lo, 1e-6).reshape(C.shape)

    excess = np.maximum(C - 0.85 * C_max, 0.0)
    C = C - excess * 0.85 / (1.0 + 1.0 * excess / (0.05 * C_max + 1e-6))
    C = np.maximum(C, 0.0)

    out = cs.oklab_to_rec709_linear(
        np.stack([L, C * np.cos(h), C * np.sin(h)], axis=-1)
    )
    return np.clip(out, 0.0, 1.0)


def decode_and_grade(encoded_log2, p=DEFAULTS):
    """Full pipeline: Apple Log 2 encoded input -> Rec.709 gamma 2.4 output.

    encoded_log2: (..., 3) float array in [0, 1]
    Returns: (..., 3) gamma-2.4 Rec.709 output values in [0, 1]
    """
    linear = cs.apple_log2_decode(encoded_log2)
    ok = cs.awg_linear_to_oklab(linear)
    ok = grade_oklab(ok, p)
    awg_lin = cs.oklab_to_awg_linear(ok)
    rec709 = awg_lin @ cs.M_AWG_TO_709.T  # linear Rec.709
    rec709 = gamut_map_rec709(rec709, p)
    return cs.encode_709_2p4(rec709)


def neutral_reference(encoded_log2):
    """Official/verified Apple Log 2 -> Rec.709 reference transform.

    Decode + gamut conversion + gamma 2.4 encode, NO creative grade.
    """
    linear = cs.apple_log2_decode(encoded_log2)
    rec709 = linear @ cs.M_AWG_TO_709.T
    rec709 = np.clip(rec709, 0.0, 1.0)
    return cs.encode_709_2p4(rec709)
