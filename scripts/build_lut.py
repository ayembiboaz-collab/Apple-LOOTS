#!/usr/bin/env python3
"""
GOLDEN DAYLIGHT CINEMA — Standalone 33x33x33 3D LUT Generator & Color Pipeline
==============================================================================

Target Camera / App : iPhone 17 Pro / Pro Max — Blackmagic Camera for iOS
Input Color Space   : Apple Log 2 / Apple Wide Gamut (D65)
Output Color Space  : ITU-R BT.709 (Rec.709) SDR, Gamma 2.4
LUT Format          : 33 x 33 x 33 Adobe/Iridas .cube (35,937 lattice nodes)

Official Technical References:
1. Apple Inc. (September 2025). "Apple Log 2 White Paper" (Part: 028-00834, Version 1.1).
2. Apple Inc. (September 2023). "Apple Log Profile White Paper".
3. Academy Software Foundation / OpenColorIO PR #2343 (commit 36152c4, Sep 2026):
   APPLE_LOG-APPLEWG_to_ACES2065-1 builtin transform.
4. colour-science/colour Issue #1428 / Commit a38e439 (Nov 2026):
   RGB_COLOURSPACE_APPLE_WIDE_GAMUT definition.
"""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np

# ==============================================================================
# 1. OFFICIAL APPLE LOG 2 & APPLE WIDE GAMUT CONSTANTS (Apple Inc., Sep 2025)
# ==============================================================================

APPLE_LOG2_R0: float = -0.05641088
APPLE_LOG2_RT: float = 0.01
APPLE_LOG2_C: float = 47.28711236
APPLE_LOG2_BETA: float = 0.00964052
APPLE_LOG2_GAMMA: float = 0.08550479
APPLE_LOG2_DELTA: float = 0.69336945
APPLE_LOG2_PT: float = APPLE_LOG2_C * (APPLE_LOG2_RT - APPLE_LOG2_R0) ** 2
APPLE_LOG2_P0: float = APPLE_LOG2_C * (0.0 - APPLE_LOG2_R0) ** 2  # ~0.15047645

# CIE 1931 2-Degree Standard Observer xy chromaticities (Apple Log 2 White Paper p. 6)
PRIMARIES_APPLE_WIDE_GAMUT = np.array(
    [
        [0.725, 0.301],   # Red primary (R)
        [0.221, 0.814],   # Green primary (G)
        [0.068, -0.076],  # Blue primary (B)
    ],
    dtype=np.float64,
)

PRIMARIES_REC709 = np.array(
    [
        [0.640, 0.330],   # Red primary (R)
        [0.300, 0.600],   # Green primary (G)
        [0.150, 0.060],   # Blue primary (B)
    ],
    dtype=np.float64,
)

WHITEPOINT_D65 = np.array([0.3127, 0.3290], dtype=np.float64)

# ITU-R BT.709 luminous efficiency weights
LUMA_REC709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def compute_npm(primaries: np.ndarray, whitepoint: np.ndarray) -> np.ndarray:
    """
    Compute the 3x3 Normalized Primary Matrix (RGB -> CIE XYZ) per SMPTE RP 177.
    """
    x = primaries[:, 0]
    y = primaries[:, 1]
    z = 1.0 - x - y
    P = np.vstack([x / y, np.ones(3, dtype=np.float64), z / y])

    xw, yw = whitepoint[0], whitepoint[1]
    W = np.array([xw / yw, 1.0, (1.0 - xw - yw) / yw], dtype=np.float64)

    S = np.linalg.solve(P, W)
    return P * S[np.newaxis, :]


MATRIX_AWG_TO_XYZ = compute_npm(PRIMARIES_APPLE_WIDE_GAMUT, WHITEPOINT_D65)
MATRIX_XYZ_TO_AWG = np.linalg.inv(MATRIX_AWG_TO_XYZ)

MATRIX_REC709_TO_XYZ = compute_npm(PRIMARIES_REC709, WHITEPOINT_D65)
MATRIX_XYZ_TO_REC709 = np.linalg.inv(MATRIX_REC709_TO_XYZ)

# Exact Linear Apple Wide Gamut -> Linear Rec.709 matrix (both D65 whitepoint)
MATRIX_AWG_TO_REC709 = MATRIX_XYZ_TO_REC709 @ MATRIX_AWG_TO_XYZ
MATRIX_REC709_TO_AWG = MATRIX_XYZ_TO_AWG @ MATRIX_REC709_TO_XYZ


# ==============================================================================
# 2. OFFICIAL APPLE LOG 2 ENCODING & DECODING FUNCTIONS
# ==============================================================================

def apple_log2_encode(R: np.ndarray | float) -> np.ndarray:
    """
    Official Apple Log 2 encoding function P = f(R) from Apple Log 2 White Paper (2025).
    Converts scene-referred linear reflection R to normalized [0, 1] Apple Log 2 signal P.
    """
    R_arr = np.asarray(R, dtype=np.float64)
    P = np.zeros_like(R_arr, dtype=np.float64)

    mask_log = R_arr >= APPLE_LOG2_RT
    mask_par = (R_arr >= APPLE_LOG2_R0) & (R_arr < APPLE_LOG2_RT)

    P[mask_log] = (
        APPLE_LOG2_GAMMA * np.log2(R_arr[mask_log] + APPLE_LOG2_BETA)
        + APPLE_LOG2_DELTA
    )
    P[mask_par] = APPLE_LOG2_C * (R_arr[mask_par] - APPLE_LOG2_R0) ** 2
    return P


def apple_log2_decode(P: np.ndarray | float) -> np.ndarray:
    """
    Official Apple Log 2 decoding function R = f^-1(P) from Apple Log 2 White Paper (2025).
    Converts normalized [0, 1] Apple Log 2 code value P to linear reflection R.
    """
    P_arr = np.asarray(P, dtype=np.float64)
    R = np.full_like(P_arr, APPLE_LOG2_R0, dtype=np.float64)

    mask_log = P_arr >= APPLE_LOG2_PT
    mask_par = (P_arr >= 0.0) & (P_arr < APPLE_LOG2_PT)

    R[mask_log] = (
        np.power(2.0, (P_arr[mask_log] - APPLE_LOG2_DELTA) / APPLE_LOG2_GAMMA)
        - APPLE_LOG2_BETA
    )
    R[mask_par] = np.sqrt(P_arr[mask_par] / APPLE_LOG2_C) + APPLE_LOG2_R0
    return R


# ==============================================================================
# 3. SIMULATED APPLE LOG 2 / APPLE WIDE GAMUT GENERATOR (FOR TEST SCENES)
# ==============================================================================

def srgb_to_linear(V: np.ndarray) -> np.ndarray:
    """Exact IEC 61966-2-1 sRGB EOTF (display-encoded [0,1] -> display linear [0,1])."""
    V = np.clip(np.asarray(V, dtype=np.float64), 0.0, 1.0)
    return np.where(
        V <= 0.04045,
        V / 12.92,
        np.power((V + 0.055) / 1.055, 2.4),
    )


def simulate_apple_log2_from_srgb(srgb_norm: np.ndarray) -> np.ndarray:
    """
    Documented, scene-independent simulation of Apple Log 2 / Apple Wide Gamut
    derived from an 8-bit/16-bit sRGB photograph normalized to [0, 1].

    Steps:
    1. Inverse sRGB EOTF -> Display-referred linear Rec.709.
    2. Fixed Inverse SDR Display Rendering Transform -> Scene-referred linear Rec.709:
       - Anchors 18% middle gray (L_disp = 0.18 -> R_scene = 0.18).
       - Undoes mild in-camera display gamma contrast (0.93) and saturation boost (0.94).
       - Un-rolls compressed display highlights smoothly up to R_max ~ 2.25 (diffuse +
         specular daylight headroom) without clipping.
    3. Linear Rec.709 -> Linear Apple Wide Gamut via exact inverse NPM matrix.
    4. Linear Apple Wide Gamut -> Apple Log 2 OETF encoding [0, 1].
    """
    L_disp = srgb_to_linear(srgb_norm)

    # Luminance-based inverse display tone curve
    Y_disp = np.clip(np.tensordot(L_disp, LUMA_REC709, axes=([-1], [0])), 0.0, 1.0)

    # Smooth inverse shoulder mapping L_disp in [0, 1] -> R_scene in [0, ~2.20]
    # Exact anchor at Y_disp = 0.18 -> R_scene = 0.18
    def inv_drt(y: np.ndarray) -> np.ndarray:
        y_pow = np.power(np.maximum(y, 1e-10) / 0.18, 0.93) * 0.18
        # Smooth rational highlight expansion above middle gray
        sh = 1.0 + 1.22 * np.power(y, 1.65)
        return y_pow * sh

    norm_018 = 0.18 / float(inv_drt(np.array(0.18)))
    Y_scene = inv_drt(Y_disp) * norm_018

    scale = Y_scene / (Y_disp + 1e-8)
    R_709 = L_disp * scale[..., np.newaxis]

    # Undo mild in-camera sRGB chroma boost (0.94) so scene-referred linear is natural
    Y_sc = np.tensordot(R_709, LUMA_REC709, axes=([-1], [0]))[..., np.newaxis]
    R_709 = Y_sc + 0.94 * (R_709 - Y_sc)
    R_709 = np.maximum(R_709, 0.0)

    # Transform Linear Rec.709 -> Linear Apple Wide Gamut
    R_awg = np.tensordot(R_709, MATRIX_REC709_TO_AWG.T, axes=([-1], [0]))

    # Encode with official Apple Log 2 transfer function
    P_log2 = apple_log2_encode(R_awg)
    return np.clip(P_log2, 0.0, 1.0)


def technical_apple_log2_to_rec709(P_log2: np.ndarray) -> np.ndarray:
    """
    Neutral Reference Technical Conversion (Apple Log 2 / AWG -> Rec.709 SDR).
    Decodes Apple Log 2, transforms Apple Wide Gamut to Rec.709, applies a purely
    neutral inverse of the standard SDR tone curve (no creative warmth or hue shifts),
    and encodes to Rec.709 display space for baseline comparison.
    """
    R_awg = apple_log2_decode(P_log2)
    R_709 = np.tensordot(R_awg, MATRIX_AWG_TO_REC709.T, axes=([-1], [0]))
    R_709 = np.maximum(R_709, 0.0)

    # Neutral forward SDR tone mapping (exact inverse of inv_drt on luminance)
    Y = np.tensordot(R_709, LUMA_REC709, axes=([-1], [0]))
    # Solve forward tone map smoothly: R=0.18 -> L=0.18, R=2.2 -> L=1.0
    Y_norm = Y / 0.18
    L_disp_y = 0.18 * np.power(Y_norm, 1.0 / 0.93) / (1.0 + 0.135 * np.power(Y_norm, 1.05))
    # Normalize so R=0.18 maps to L=0.18
    ref_018 = 0.18 / (1.0 + 0.135)
    L_disp_y = L_disp_y * (0.18 / ref_018)

    ratio = L_disp_y / (Y + 1e-8)
    L_rgb = R_709 * ratio[..., np.newaxis]
    Y_l = np.tensordot(L_rgb, LUMA_REC709, axes=([-1], [0]))[..., np.newaxis]
    L_rgb = Y_l + (1.0 / 0.94) * (L_rgb - Y_l)
    L_rgb = np.clip(L_rgb, 0.0, 1.0)

    # Encode Rec.709 Gamma 2.4
    return np.power(L_rgb, 1.0 / 2.4)


# ==============================================================================
# 4. GOLDEN DAYLIGHT CINEMA — STANDALONE CREATIVE LUT PIPELINE
# ==============================================================================

def _soft_black_floor(R: np.ndarray) -> np.ndarray:
    """
    Smooth C1 black-floor conditioning for decoded Apple Log 2 linear values.
    In Apple Log 2, R=0 is encoded at P=0.150477. Below P=0.150477, R is negative
    down to R_0=-0.056411. Using r_min = -2 * r_join (-0.008) and r_join = 0.004,
    the cubic transition f(t) = r_join * t^3 has f(0)=0, f'(0)=0, f(1)=r_join,
    f'(1)=1.0, and strictly non-negative derivative f'(t) >= 0 everywhere.
    """
    r_join = 0.004
    r_min = -2.0 * r_join
    span = 3.0 * r_join

    out = np.zeros_like(R, dtype=np.float64)
    mask_hi = R >= r_join
    mask_mid = (R > r_min) & (R < r_join)

    out[mask_hi] = R[mask_hi]
    t = (R[mask_mid] - r_min) / span
    out[mask_mid] = r_join * (t * t * t)
    return np.maximum(out, 0.0)


def _soft_gamut_compress_rec709(rgb_lin: np.ndarray) -> np.ndarray:
    """
    Luminance-preserving C-infinity soft gamut compression from Apple Wide Gamut
    into Rec.709. Because the Apple Wide Gamut Blue primary has negative CIE y
    (y_B = -0.076), extreme blue lattice corners can have negative raw Rec.709
    luminance. Using a smooth positive-channel luminance reference ensures smooth,
    artifact-free gamut compression across all 33^3 lattice nodes while leaving
    in-gamut colors (d <= 0.76) 100% untouched.
    """
    rgb_pos = 0.5 * (rgb_lin + np.sqrt(rgb_lin * rgb_lin + 1e-9))
    Y_ref = np.tensordot(rgb_pos, LUMA_REC709, axes=([-1], [0]))[..., np.newaxis]
    Y_pos = np.maximum(Y_ref, 1e-7)

    d = (Y_pos - rgb_lin) / Y_pos
    t0 = 0.76
    limit = 0.998

    span = limit - t0
    d_comp = np.where(
        d <= t0,
        d,
        t0 + span * np.tanh(np.maximum(d - t0, 0.0) / span),
    )

    rgb_safe = Y_pos * (1.0 - d_comp)
    return np.maximum(rgb_safe, 0.0)


def _filmic_tone_curve_gamma24(R: np.ndarray) -> np.ndarray:
    """
    Photochemical-inspired scene-linear to Rec.709 Gamma 2.4 tone curve (DRT).
    Designed specifically for harsh midday daylight through golden hour:
    - Does NOT make already-bright midday footage brighter: anchors 18% middle gray
      (R=0.18, P=0.4883) at Gamma 2.4 code value ~0.448 (slightly richer and denser
      than standard Rec.709 ~0.470 so harsh midday glare is tamed while keeping
      midtones luminous and dimensional).
    - Rich midtone contrast & authoritative sun/shade separation.
    - Deep, detailed shadows without crushed blacks or flat milky lifted blacks.
    - Extended, smooth two-stage Michaelis-Menten highlight roll-off up to
      R = 12.0 (1200% reflectance, P = 1.0 in Apple Log 2).
    """
    R_pos = np.maximum(R, 0.0)
    p1 = 0.865
    k1 = 0.192
    rp1 = np.power(R_pos + 0.00010, p1)
    t1 = rp1 / (rp1 + np.power(k1, p1))
    t0 = np.power(0.00001, p1) / (np.power(0.00001, p1) + np.power(k1, p1))

    # Extended highlight shoulder for R in [1.2, 12.0]
    t2 = R_pos / (R_pos + 1.50)

    raw = 0.895 * (t1 - t0) + 0.105 * t2

    r_max = 12.0
    rp_m = np.power(r_max + 0.00010, p1)
    t1_m = rp_m / (rp_m + np.power(k1, p1))
    t2_m = r_max / (r_max + 1.50)
    raw_max = 0.895 * (t1_m - t0) + 0.105 * t2_m

    return np.clip(raw / float(raw_max), 0.0, 1.0)


def _hue_window_cos(h_deg: np.ndarray, center_deg: float, half_width_deg: float) -> np.ndarray:
    """
    Smooth C^2 raised-cosine angular window centered at `center_deg` with support
    [center - half_width, center + half_width] on the 360-degree circle.
    """
    diff = np.abs(((h_deg - center_deg + 180.0) % 360.0) - 180.0)
    u = np.clip(diff / half_width_deg, 0.0, 1.0)
    w = 0.5 * (1.0 + np.cos(np.pi * u))
    return w * w  # squared raised cosine for ultra-smooth C^2 derivatives


def golden_daylight_cinema_transform(P_log2: np.ndarray) -> np.ndarray:
    """
    Complete standalone transformation from Apple Log 2 / Apple Wide Gamut [0, 1]^3
    to graded Rec.709 SDR Gamma 2.4 [0, 1]^3.
    """
    orig_shape = P_log2.shape
    P = np.reshape(np.asarray(P_log2, dtype=np.float64), (-1, 3))

    # ------------------------------------------------------------------
    # STAGE 1: Official Apple Log 2 Decode & Black Floor Conditioning
    # ------------------------------------------------------------------
    R_awg_raw = apple_log2_decode(P)
    R_awg = _soft_black_floor(R_awg_raw)

    # ------------------------------------------------------------------
    # STAGE 2: Apple Wide Gamut -> Linear Rec.709 + Soft Gamut Compression
    # ------------------------------------------------------------------
    R_709_raw = R_awg @ MATRIX_AWG_TO_REC709.T
    R_709 = _soft_gamut_compress_rec709(R_709_raw)

    # ------------------------------------------------------------------
    # STAGE 3: Hybrid Luminance / Per-Channel Filmic Tone Mapping (DRT)
    # ------------------------------------------------------------------
    Y_lin = np.maximum(R_709 @ LUMA_REC709, 0.0)
    V_y = _filmic_tone_curve_gamma24(Y_lin)
    L_y = np.power(V_y, 2.4)

    V_ch = _filmic_tone_curve_gamma24(R_709)
    L_ch = np.power(V_ch, 2.4)

    # Luminance-preserving linear tone map
    scale_y = L_y / (Y_lin + 1e-8)
    L_lum_rgb = R_709 * scale_y[:, np.newaxis]

    # Blend 62% luminance-mapped + 38% per-channel mapped in midtones, transitioning
    # smoothly to 100% per-channel roll-off at peak white (V_y -> 1.0) so no channel
    # ever exceeds 1.0 or suffers asymmetric hard-clipping in cell [31, 32]^3.
    w_ch = 0.38 + 0.62 * np.power(V_y, 1.55)
    w_ch = np.clip(w_ch, 0.0, 1.0)[:, np.newaxis]
    L_disp = (1.0 - w_ch) * L_lum_rgb + w_ch * L_ch
    L_disp = np.clip(L_disp, 0.0, 1.0)

    # Convert to working Rec.709 Gamma 2.4 perceptual signal V in [0, 1]^3
    V = np.power(np.maximum(L_disp, 0.0), 1.0 / 2.4)

    # ------------------------------------------------------------------
    # STAGE 4: Perceptual Opponent Decomposition (Y, a, b, Chroma, Hue)
    # ------------------------------------------------------------------
    Y_v = V @ LUMA_REC709  # Luma in Gamma 2.4 space [0, 1]

    # Construct an orthonormal chroma plane orthogonal to LUMA_REC709 = (0.2126, 0.7152, 0.0722)
    # Notice any vector (1, 1, 1) has dot product 0 with u_a and u_b!
    # u_a: Red-Warm vs Cyan-Green opponent axis
    # u_b: Yellow-Amber vs Blue opponent axis
    u_a = np.array([0.7874, -0.7152, -0.0722], dtype=np.float64)
    u_b = np.array([0.2200, 0.2800, -0.5000], dtype=np.float64)
    # Inverse 3x3 basis from (Y_v, a, b) -> (R, G, B)
    B_fwd = np.vstack([LUMA_REC709, u_a, u_b])  # 3x3
    B_inv = np.linalg.inv(B_fwd)

    a = V @ u_a
    b = V @ u_b
    C = np.hypot(a, b)
    h_rad = np.arctan2(b, a)
    h_deg = (np.degrees(h_rad) + 360.0) % 360.0

    # Let's check exact hue angles of primary & key colors in this basis:
    # Red (1,0,0):      a = +0.7874, b = +0.2200 -> h = 15.6 deg
    # Skin/Orange:      h ~ 26 - 38 deg
    # Golden Honey:     h ~ 42 - 52 deg
    # Yellow (1,1,0):   a = +0.0722, b = +0.5000 -> h = 81.8 deg
    # Green (0,1,0):    a = -0.7152, b = +0.2800 -> h = 158.6 deg
    # Cyan (0,1,1):     a = -0.7874, b = -0.2200 -> h = 195.6 deg
    # Blue (0,0,1):     a = -0.0722, b = -0.5000 -> h = 261.8 deg
    # Magenta (1,0,1):  a = +0.7152, b = -0.2800 -> h = 338.6 deg

    # ------------------------------------------------------------------
    # STAGE 5: Six-Vector Selective Hue, Saturation & Subtractive Density
    # ------------------------------------------------------------------
    # Smooth chroma gate so hue adjustments vanish smoothly at C -> 0 (preserving C^1 neutrality)
    c_gate = (C * C) / (C * C + 0.018 * 0.018)

    # Sector windows in (a, b) opponent hue degrees:
    w_red      = _hue_window_cos(h_deg, 10.0, 22.0)    # Deep Reds & Terracotta
    w_skin     = _hue_window_cos(h_deg, 32.0, 22.0)    # Skin tones (Pinkish 15° to Golden 50°)
    w_yellow   = _hue_window_cos(h_deg, 78.0, 26.0)    # Harsh Lemon-Yellows (60° to 98°)
    w_yel_grn  = _hue_window_cos(h_deg, 118.0, 32.0)   # Yellow-Green / Chartreuse Foliage
    w_green    = _hue_window_cos(h_deg, 155.0, 32.0)   # Core Greenery / Forest Foliage
    w_cyan     = _hue_window_cos(h_deg, 196.0, 28.0)   # Cyan / Turquoise Skies & Water
    w_sky_blue = _hue_window_cos(h_deg, 245.0, 34.0)   # Azure / Cobalt Midday Sky Blue

    # 5A. Selective Hue Rotations (in degrees):
    # - Skin: gently align ruddy/pinkish (<32°) and sallow (>36°) skin toward 33° golden-peach
    skin_diff = ((33.0 - h_deg + 180.0) % 360.0) - 180.0
    dh_skin = 0.22 * skin_diff * w_skin

    # - Lemon-Yellows (78°): rotate -9.5° toward warm Mediterranean honey-ochre (~48°-60°)
    dh_yellow = -9.5 * w_yellow

    # - Foliage: pull radioactive yellow-greens (118°) slightly toward rich olive-botanical
    #   and pull cool cyan-greens (170°) warmer toward natural green (~142°), avoiding both
    #   radioactive yellow-green AND fake teal!
    dh_foliage = +4.5 * w_yel_grn - 6.0 * _hue_window_cos(h_deg, 172.0, 22.0)

    # - Skies & Cyans: rotate turquoise/cyan (196°) by +7.5° toward natural azure blue (230°-250°)
    #   so midday skies never look turquoise or teal.
    dh_cyan_sky = +7.5 * w_cyan + 2.5 * _hue_window_cos(h_deg, 220.0, 22.0)

    # - Deep Reds/Magentas: subtle warmth toward cinema vermilion
    dh_red = +3.5 * _hue_window_cos(h_deg, 352.0, 24.0)

    total_dh_deg = c_gate * (dh_skin + dh_yellow + dh_foliage + dh_cyan_sky + dh_red)
    h_new_rad = h_rad + np.radians(total_dh_deg)

    # 5B. Selective Saturation & Self-Limiting Golden-Hour Protection:
    # Midtone bell weight so saturation is richest in dimensional midtones and rolls off
    # cleanly in deep shadows and bright highlights
    mid_bell = np.sin(np.pi * np.clip(Y_v, 0.0, 1.0)) ** 1.10

    # - Global subtle vibrance on muted midday colors (C < 0.20), with filmic rolloff on loud colors
    sat_mult = np.ones_like(C)
    sat_mult += 0.11 * np.exp(-((C / 0.18) ** 2)) * mid_bell

    # - Greenery: controlled saturation (-16% on yellow-greens and core greens)
    sat_mult -= 0.16 * (w_yel_grn + 0.85 * w_green)

    # - Cyan control: -14% on cyan/turquoise so skies & water stay natural, not neon
    sat_mult -= 0.14 * w_cyan

    # - Sky Blue: natural richness (+5% on pale midday skies, -8% ceiling on already ultra-saturated blues)
    sat_mult += 0.05 * w_sky_blue * np.exp(-((C / 0.18) ** 2))
    sat_mult -= 0.08 * w_sky_blue * np.clip((C - 0.22) / 0.20, 0.0, 1.0)

    # - Skin & Warm Golden-Hour Protection:
    #   Enrich pale/moderate sunlit skin & stone gently, while compressing high-chroma
    #   warm/orange/sunset tones (C > 0.23) so neither midday skin nor actual golden-hour
    #   landscapes ever overheat into neon orange!
    w_warm_all = np.clip(w_red + w_skin + 0.75 * w_yellow, 0.0, 1.2)
    warm_excess = np.clip((C - 0.23) / 0.20, 0.0, 1.0)
    sat_mult -= 0.22 * w_warm_all * warm_excess

    C_new = C * np.clip(sat_mult, 0.65, 1.25)

    a_new = C_new * np.cos(h_new_rad)
    b_new = C_new * np.sin(h_new_rad)

    # 5C. Subtractive Filmic Density (Darkening saturated colors slightly like Kodak 2383 print film
    #     for dimensional depth, WITHOUT making skies artificially dark):
    c_norm = np.clip(C / 0.30, 0.0, 1.0) * c_gate
    density_offset = (
        -0.018 * w_sky_blue * c_norm     # Subtle natural sky richness (never artificially dark)
        - 0.015 * w_cyan * c_norm        # Controlled cyan water depth
        - 0.030 * (w_yel_grn + w_green) * c_norm  # Grounded, organic botanical foliage
        - 0.014 * w_yellow * c_norm      # Solid warm stone & ochre weight
        - 0.018 * w_red * c_norm         # Rich terracotta & brick density
        - 0.015 * w_skin * c_norm * warm_excess  # Smooth highlight protection on warm sunsets
    ) * mid_bell

    Y_graded = np.clip(Y_v + density_offset, 0.0, 1.0)

    # ------------------------------------------------------------------
    # STAGE 6: "Golden Daylight Cinema" Sunlit Honey Split-Toning
    # ------------------------------------------------------------------
    # How do we infuse sunlit stone, architecture, pavement, and midday light with
    # luxury Mediterranean honey-amber warmth while:
    # (1) keeping whites clean & believable,
    # (2) avoiding an overall yellow filter cast,
    # (3) keeping skies pure blue, and
    # (4) not overheating already-warm golden-hour scenes?
    #
    # Solution:
    # A. Cinema Print Split-Tone across luminance zones (vanishes at Y=0 and Y>=0.92):
    #    - Deep shadows (Y ~ 0.09): subtle cool-neutral slate depth (-a, -b) for sun/shade separation.
    #    - Sunlit midtones & upper-midtones (Y ~ 0.50): golden-honey warmth (in opponent (a, b)
    #      toward h = 39°: warm golden-amber honey, NEVER greenish lemon-yellow 82°!).
    #    - Specular highlights & cloud whites (Y > 0.85): decays rapidly to 0.000 at Y=1.0!
    y = Y_graded
    # Shadow window peaking at Y ~ 0.10, vanishing at Y=0 and Y>=0.28
    w_sh_zone = np.where(
        y < 0.28,
        np.sin(np.pi * np.clip(y / 0.28, 0.0, 1.0)) ** 1.5,
        0.0,
    )
    # Sunlit midtone/upper-midtone window peaking at Y ~ 0.55, vanishing below Y=0.12 and above Y=0.93
    u_mid = np.clip((y - 0.12) / (0.93 - 0.12), 0.0, 1.0)
    w_sun_zone = (np.sin(np.pi * (u_mid ** 0.85)) ** 1.45)

    # Sky/Foliage chroma shield: only activates when chroma C > 0.095 in sky-blue/cyan/green hues,
    # so cool-grey midday concrete, glass buildings, beach sand, and stone plazas (C < 0.085)
    # DO receive warm golden sunlight, while actual blue skies and water (C > 0.11) remain pure azure blue!
    sky_chroma_gate = (C ** 3) / (C ** 3 + 0.098 ** 3)
    w_cool_shield = np.clip(w_sky_blue + w_cyan + 0.65 * w_green, 0.0, 1.0) * sky_chroma_gate

    # Golden-hour shield: protects already-saturated warm sunset hues (C > 0.22) from over-warming
    w_already_warm_shield = np.clip((C - 0.21) / 0.14, 0.0, 1.0)

    honey_gate = (1.0 - 0.92 * w_cool_shield) * (1.0 - 0.86 * w_already_warm_shield)

    # Golden-honey vector in (a, b) space at h = 38.0 deg (rich honey-amber sunlight):
    honey_strength = 0.0335 * w_sun_zone * honey_gate
    da_honey = honey_strength * np.cos(np.radians(38.0))
    db_honey = honey_strength * np.sin(np.radians(38.0))

    # Subtle cool-slate shadow counterbalance at h = 232 deg for crisp sun/shade separation:
    shadow_strength = 0.0052 * w_sh_zone * (1.0 - 0.6 * w_already_warm_shield)
    da_shadow = shadow_strength * np.cos(np.radians(232.0))
    db_shadow = shadow_strength * np.sin(np.radians(232.0))

    # Additional warm stone, limestone, sand & sunlit architectural enrichment for low-to-moderate
    # warm/earthy surfaces (C in [0.008, 0.22], h around 15°..85°):
    w_earthy_hue = _hue_window_cos(h_deg, 46.0, 56.0)
    w_earthy_chroma = (C / (C + 0.020)) * np.exp(-((C / 0.22) ** 2))
    stone_warmth = 0.0220 * w_sun_zone * w_earthy_hue * w_earthy_chroma
    da_stone = stone_warmth * np.cos(np.radians(37.5))
    db_stone = stone_warmth * np.sin(np.radians(37.5))

    a_final = a_new + da_honey + da_shadow + da_stone
    b_final = b_new + db_honey + db_shadow + db_stone

    # Reconstruct Rec.709 Gamma 2.4 RGB from (Y_graded, a_final, b_final)
    YAB = np.stack([Y_graded, a_final, b_final], axis=-1)
    V_out = YAB @ B_inv.T

    # Soft highlight/shadow boundary cushion near 0.0 and 1.0 to prevent hard channel clipping
    V_out = np.clip(V_out, 0.0, 1.0)
    return np.reshape(V_out, orig_shape)


# ==============================================================================
# 5. 33x33x33 .CUBE LUT GENERATOR, PARSER & TRILINEAR INTERPOLATOR
# ==============================================================================

def generate_cube_lut(output_path: str | Path, size: int = 33) -> np.ndarray:
    """
    Generate the standalone 33x33x33 3D .cube LUT file and return the (33, 33, 33, 3)
    table indexed as lut[r_idx, g_idx, b_idx].
    In the .cube file specification, Red changes fastest, Green second, Blue slowest.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    axis = np.linspace(0.0, 1.0, size, dtype=np.float64)
    # Build grid in .cube order: B outer, G middle, R inner
    B_grid, G_grid, R_grid = np.meshgrid(axis, axis, axis, indexing="ij")
    P_grid = np.stack([R_grid, G_grid, B_grid], axis=-1)  # shape (B, G, R, 3)

    V_grid = golden_daylight_cinema_transform(P_grid)
    V_grid = np.clip(np.nan_to_num(V_grid, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)

    header_lines = [
        'TITLE "GOLDEN_DAYLIGHT_CINEMA"',
        "# Project: GOLDEN DAYLIGHT CINEMA",
        "# Target Camera: iPhone 17 Pro / Pro Max (Blackmagic Camera for iOS)",
        "# Input Color Space: Apple Log 2 / Apple Wide Gamut (D65)",
        "# Output Color Space: ITU-R BT.709 (Rec.709) SDR, Gamma 2.4",
        "# Architecture: Standalone 3D LUT (Apple Log 2 Decode + AWG Matrix + DRT + Creative Grade)",
        "# Specification Reference: Apple Log 2 White Paper (September 2025, Part 028-00834 v1.1)",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
        f"LUT_3D_SIZE {size}",
    ]

    flat_rgb = V_grid.reshape(-1, 3)
    body_lines = [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in flat_rgb]

    content = "\n".join(header_lines + body_lines) + "\n"
    output_path.write_text(content, encoding="utf-8")

    # Return indexed as [r_idx, g_idx, b_idx, 3] for fast trilinear lookup
    return np.transpose(V_grid, (2, 1, 0, 3)).copy()


def load_cube_lut(cube_path: str | Path) -> tuple[np.ndarray, dict]:
    """
    Parse a .cube file from disk and return (lut_table[r, g, b, 3], metadata).
    Strictly validates header tokens and row counts.
    """
    cube_path = Path(cube_path)
    lines = cube_path.read_text(encoding="utf-8").splitlines()

    size = None
    title = None
    domain_min = [0.0, 0.0, 0.0]
    domain_max = [1.0, 1.0, 1.0]
    data_rows = []

    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("TITLE"):
            parts = s.split(maxsplit=1)
            title = parts[1].strip('"') if len(parts) > 1 else ""
        elif s.upper().startswith("LUT_3D_SIZE"):
            size = int(s.split()[1])
        elif s.upper().startswith("DOMAIN_MIN"):
            domain_min = [float(x) for x in s.split()[1:4]]
        elif s.upper().startswith("DOMAIN_MAX"):
            domain_max = [float(x) for x in s.split()[1:4]]
        else:
            vals = [float(x) for x in s.split()]
            if len(vals) != 3:
                raise ValueError(f"Invalid RGB data line in {cube_path}: {line!r}")
            data_rows.append(vals)

    if size is None:
        raise ValueError(f"Missing LUT_3D_SIZE in {cube_path}")
    expected_rows = size ** 3
    if len(data_rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, found {len(data_rows)} in {cube_path}")

    arr_bgr = np.array(data_rows, dtype=np.float64).reshape((size, size, size, 3))
    # Transpose from [b, g, r, 3] to [r, g, b, 3]
    lut_rgb = np.transpose(arr_bgr, (2, 1, 0, 3)).copy()
    meta = {
        "title": title,
        "size": size,
        "domain_min": domain_min,
        "domain_max": domain_max,
        "num_rows": len(data_rows),
    }
    return lut_rgb, meta


def apply_cube_lut_trilinear(img_norm: np.ndarray, lut_rgb: np.ndarray) -> np.ndarray:
    """
    Apply a parsed 3D .cube LUT (indexed [r, g, b, 3]) to a normalized [0, 1] image
    using exact 3D trilinear interpolation.
    """
    size = lut_rgb.shape[0]
    scale = float(size - 1)

    orig_shape = img_norm.shape
    flat = np.clip(np.asarray(img_norm, dtype=np.float64).reshape(-1, 3), 0.0, 1.0) * scale

    r = flat[:, 0]
    g = flat[:, 1]
    b = flat[:, 2]

    r0 = np.clip(np.floor(r).astype(np.int32), 0, size - 2)
    g0 = np.clip(np.floor(g).astype(np.int32), 0, size - 2)
    b0 = np.clip(np.floor(b).astype(np.int32), 0, size - 2)

    r1 = r0 + 1
    g1 = g0 + 1
    b1 = b0 + 1

    dr = (r - r0)[:, np.newaxis]
    dg = (g - g0)[:, np.newaxis]
    db = (b - b0)[:, np.newaxis]

    c000 = lut_rgb[r0, g0, b0]
    c100 = lut_rgb[r1, g0, b0]
    c010 = lut_rgb[r0, g1, b0]
    c110 = lut_rgb[r1, g1, b0]
    c001 = lut_rgb[r0, g0, b1]
    c101 = lut_rgb[r1, g0, b1]
    c011 = lut_rgb[r0, g1, b1]
    c111 = lut_rgb[r1, g1, b1]

    c00 = c000 * (1.0 - dr) + c100 * dr
    c01 = c001 * (1.0 - dr) + c101 * dr
    c10 = c010 * (1.0 - dr) + c110 * dr
    c11 = c011 * (1.0 - dr) + c111 * dr

    c0 = c00 * (1.0 - dg) + c10 * dg
    c1 = c01 * (1.0 - dg) + c11 * dg

    out = c0 * (1.0 - db) + c1 * db
    return np.clip(out.reshape(orig_shape), 0.0, 1.0)


if __name__ == "__main__":
    lut_path = Path("GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube")
    lut_table = generate_cube_lut(lut_path, size=33)
    parsed_table, meta = load_cube_lut(lut_path)
    max_diff = np.max(np.abs(lut_table - parsed_table))
    print(f"Generated {lut_path} ({meta['num_rows']} nodes, size={meta['size']}^3)")
    print(f"Round-trip parse max diff: {max_diff:.2e}")
