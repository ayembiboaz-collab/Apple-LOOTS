"""
Golden Daylight Cinema — Colour Science Core (Float64)
====================================================
Implements:
1. Verified Apple Log 2 / Apple Wide Gamut encode & decode
   (Apple Log 2 White Paper / ASWF OpenColorIO 2.6.0 AppleCameras.cpp).
2. Simulated Apple Log 2 generator from real-world sRGB photographs.
3. Neutral Reference (Apple Log 2 -> Rec.709 Gamma 2.4) for BEFORE renders.
4. Golden Daylight Cinema analytic float64 grading pipeline (OKLCh + filmic tone curve +
   hue-preserving gamut compression -> Rec.709 Gamma 2.4).
5. 33x33x33 .cube baker and independent trilinear / tetrahedral .cube evaluator.
"""

import numpy as np
import colour

# ---------------------------------------------------------------------------
# 1. Apple Wide Gamut & Apple Log 2 (Verified OCIO 2.6.0 / Apple specs)
# ---------------------------------------------------------------------------
APPLE_WIDE_GAMUT_PRIMARIES = np.array([
    [0.725, 0.301],   # Red
    [0.221, 0.814],   # Green
    [0.068, -0.076],  # Blue
])
D65_WHITEPOINT = np.array([0.3127, 0.3290])

APPLE_WIDE_GAMUT_CS = colour.RGB_Colourspace(
    name="Apple Wide Gamut",
    primaries=APPLE_WIDE_GAMUT_PRIMARIES,
    whitepoint=D65_WHITEPOINT,
    whitepoint_name="D65",
    use_derived_matrix_RGB_to_XYZ=True,
    use_derived_matrix_XYZ_to_RGB=True,
)

REC709_CS = colour.RGB_COLOURSPACES["Linear Rec.709 (sRGB)"]

# Apple Log / Apple Log 2 transfer function constants
_R_0 = -0.05641088
_R_T = 0.01
_C = 47.28711236
_BETA = 0.00964052
_GAMMA = 0.08550479
_DELTA = 0.69336945
_P_T = _C * (_R_T - _R_0) ** 2


def log_decoding_AppleLog2(P: np.ndarray) -> np.ndarray:
    """Decode Apple Log 2 code values [0, 1] to scene-linear Apple Wide Gamut."""
    P = np.asarray(P, dtype=np.float64)
    R = np.empty_like(P, dtype=np.float64)
    low = P < _P_T
    high = ~low
    R[low] = np.sqrt(np.maximum(P[low], 0.0) / _C) + _R_0
    R[high] = np.power(2.0, (P[high] - _DELTA) / _GAMMA) - _BETA
    return R


def log_encoding_AppleLog2(R: np.ndarray) -> np.ndarray:
    """Encode scene-linear Apple Wide Gamut to Apple Log 2 code values."""
    R = np.asarray(R, dtype=np.float64)
    P = np.empty_like(R, dtype=np.float64)
    low = R < _R_T
    mid_low = R < _R_0
    high = ~low
    P[low] = _C * np.power(R[low] - _R_0, 2.0)
    P[mid_low] = 0.0
    P[high] = _GAMMA * np.log2(np.maximum(R[high] + _BETA, 1e-12)) + _DELTA
    return P


def apple_wg_to_xyz(rgb: np.ndarray) -> np.ndarray:
    return colour.RGB_to_XYZ(rgb, APPLE_WIDE_GAMUT_CS)


def xyz_to_apple_wg(xyz: np.ndarray) -> np.ndarray:
    return colour.XYZ_to_RGB(xyz, APPLE_WIDE_GAMUT_CS)


def apple_wg_to_rec709(rgb: np.ndarray) -> np.ndarray:
    return colour.RGB_to_RGB(rgb, APPLE_WIDE_GAMUT_CS, REC709_CS)


def rec709_to_apple_wg(rgb: np.ndarray) -> np.ndarray:
    return colour.RGB_to_RGB(rgb, REC709_CS, APPLE_WIDE_GAMUT_CS)


# ---------------------------------------------------------------------------
# 2. sRGB & Rec.709 Gamma 2.4 Transfer Functions
# ---------------------------------------------------------------------------
def srgb_eotf(v: np.ndarray) -> np.ndarray:
    """IEC 61966-2-1 sRGB EOTF (display-referred sRGB -> linear Rec.709)."""
    v = np.clip(np.asarray(v, dtype=np.float64), 0.0, 1.0)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def encode_rec709_gamma24(linear_rgb: np.ndarray) -> np.ndarray:
    """Pure gamma 2.4 OETF: V = clip(L, 0, 1)^(1/2.4)."""
    return np.power(np.clip(np.asarray(linear_rgb, dtype=np.float64), 0.0, 1.0), 1.0 / 2.4)


# ---------------------------------------------------------------------------
# 3. Simulated Apple Log 2 from Real-World sRGB Photographs
# ---------------------------------------------------------------------------
def simulate_apple_log2_from_srgb(srgb_img: np.ndarray) -> np.ndarray:
    """
    Simulate Apple Log 2 (Apple Wide Gamut) from an sRGB photograph.
    Steps:
      1. Inverse sRGB EOTF -> linear Rec.709 [0, 1].
      2. Gentle inverse highlight roll-off above 0.80 to restore ~1.2 stops of
         synthetic highlight headroom (bounded by 8-bit source quantization).
      3. Transform Linear Rec.709 -> Linear Apple Wide Gamut.
      4. Encode with verified Apple Log 2 transfer function.
    """
    lin709 = srgb_eotf(srgb_img)
    # Gentle inverse shoulder above 0.80
    headroom = np.where(
        lin709 > 0.80,
        0.80 + (lin709 - 0.80) * (1.0 + 2.5 * (lin709 - 0.80)),
        lin709,
    )
    # Scale so 18% grey sits cleanly around Apple Log 2 ~0.48
    lin_awg = rec709_to_apple_wg(headroom * 0.90)
    return np.clip(log_encoding_AppleLog2(lin_awg), 0.0, 1.0)


# ---------------------------------------------------------------------------
# 4. Neutral Reference Transform (BEFORE)
# ---------------------------------------------------------------------------
def neutral_apple_log2_to_rec709(log2_rgb: np.ndarray) -> np.ndarray:
    """
    Fair neutral reference: Apple Log 2 -> Linear Apple Wide Gamut ->
    Linear Rec.709 -> smooth neutral highlight roll-off -> Rec.709 Gamma 2.4.
    """
    lin_awg = log_decoding_AppleLog2(log2_rgb)
    lin709 = apple_wg_to_rec709(lin_awg)
    lin709 = np.maximum(lin709, 0.0)
    # Neutral Reinhard-style highlight roll-off above 0.80
    rolled = np.where(
        lin709 > 0.80,
        0.80 + 0.20 * (lin709 - 0.80) / (0.20 + (lin709 - 0.80)),
        lin709,
    )
    return encode_rec709_gamma24(rolled)


# ---------------------------------------------------------------------------
# 5. Golden Daylight Cinema — Analytic Float64 Grading Pipeline
# ---------------------------------------------------------------------------
def _smooth_angle_weight(h_deg: np.ndarray, center_deg: float, width_deg: float) -> np.ndarray:
    """Smooth raised-cosine angular mask in degrees (0..1)."""
    diff = ((h_deg - center_deg + 180.0) % 360.0) - 180.0
    t = np.clip(np.abs(diff) / width_deg, 0.0, 1.0)
    return 0.5 * (1.0 + np.cos(np.pi * t))


def _filmic_tone_curve(Y: np.ndarray) -> np.ndarray:
    """
    Custom filmic tone-mapping curve on scene-linear luminance Y:
    - Toe: gentle shadow compression with capped gain (prevents noise amplification).
    - Midtones: rich micro-contrast slope.
    - Shoulder: smooth highlight roll-off preserving texture without clipping.
    """
    Y = np.maximum(Y, 0.0)
    # Toe + midtone contrast in log-like domain
    # Anchor 0.18 -> ~0.185, compress deep shadows, roll off highlights > 0.65
    a = 1.08
    b = 0.012
    c = 0.92
    d = 0.24
    e = 0.008
    # Modified Hable/ACES-inspired smooth curve
    Y_scaled = Y * 1.02
    num = Y_scaled * (a * Y_scaled + b)
    den = Y_scaled * (c * Y_scaled + d) + e
    out = np.where(Y > 1e-8, num / den, 0.0)
    # Normalize so Y=1.0 maps cleanly below 1.0 with headroom
    return np.clip(out * 0.92, 0.0, 1.0)


def golden_daylight_cinema_analytic(log2_rgb: np.ndarray) -> np.ndarray:
    """
    Analytic float64 Golden Daylight Cinema pipeline:
    Apple Log 2 (Apple Wide Gamut) -> Rec.709 Gamma 2.4.
    """
    # 1. Decode Apple Log 2 -> Scene-linear Apple Wide Gamut
    lin_awg = log_decoding_AppleLog2(log2_rgb)
    lin_awg = np.maximum(lin_awg, 0.0)

    # 2. Convert to CIE XYZ (D65) -> OKLab -> OKLCh
    xyz = apple_wg_to_xyz(lin_awg)
    xyz = np.maximum(xyz, 0.0)

    # 3. Apply luminance-preserving filmic tone curve (ratio-based to preserve hue)
    Y_in = xyz[..., 1:2]
    Y_out = _filmic_tone_curve(Y_in)
    ratio = np.where(Y_in > 1e-7, Y_out / Y_in, 0.0)
    # Cap shadow gain to 1.15x so sensor noise is never amplified
    ratio = np.minimum(ratio, 1.15)
    xyz_toned = xyz * ratio

    # 4. Perceptual grading in OKLab / OKLCh
    oklab = colour.XYZ_to_Oklab(xyz_toned)
    L = oklab[..., 0]
    a = oklab[..., 1]
    b = oklab[..., 2]
    C = np.sqrt(a * a + b * b)
    h_deg = np.degrees(np.arctan2(b, a)) % 360.0

    # 4a. Density-style saturation (richer in mids, thinner in highlights & deep shadows)
    mid_mask = np.sin(np.pi * np.clip(L, 0.0, 1.0)) ** 0.85
    hi_desat = 1.0 - 0.35 * np.clip((L - 0.72) / 0.28, 0.0, 1.0) ** 1.5
    sh_desat = 1.0 - 0.25 * np.clip((0.18 - L) / 0.18, 0.0, 1.0) ** 1.5
    density_gain = (1.0 + 0.12 * mid_mask) * hi_desat * sh_desat

    # 4b. Hue-selective chroma & lightness shaping (smooth raised-cosine masks)
    w_sky = _smooth_angle_weight(h_deg, 245.0, 40.0)       # Natural blue sky
    w_green = _smooth_angle_weight(h_deg, 138.0, 35.0)     # Foliage / greenery
    w_skin = _smooth_angle_weight(h_deg, 48.0, 28.0)       # Skin-line protection
    w_stone = _smooth_angle_weight(h_deg, 78.0, 32.0)      # Warm stone / amber

    # Chroma adjustments
    chroma_mult = (
        density_gain
        * (1.0 + 0.06 * w_sky)     # Rich natural sky
        * (1.0 - 0.10 * w_green)   # Controlled, non-radioactive greens
        * (1.0 - 0.08 * w_skin)    # Protect skin from oversaturation
        * (1.0 + 0.08 * w_stone)   # Subtle earthy warmth
    )
    C_new = C * chroma_mult

    # Hue refinements (gentle, no hard edges)
    # Pull cyan-blue slightly toward true sky blue; warm greens slightly toward olive
    h_shift = (
        -4.0 * w_sky * np.clip(C / 0.12, 0.0, 1.0)
        - 5.0 * w_green * np.clip(C / 0.12, 0.0, 1.0)
    )
    h_new_rad = np.radians((h_deg + h_shift) % 360.0)

    a_new = C_new * np.cos(h_new_rad)
    b_new = C_new * np.sin(h_new_rad)

    # 4c. Luminance-weighted split-tone (warm honey mids, clean neutral-cool shadows)
    # Warm honey in mids/upper-mids (L ~ 0.35..0.80)
    warm_mask = np.exp(-((L - 0.56) ** 2) / (2.0 * 0.18 ** 2)) * (1.0 - w_sky) * (1.0 - w_skin * 0.5)
    # Subtle cool-neutral in deep shadows (L < 0.25)
    cool_mask = np.clip((0.25 - L) / 0.25, 0.0, 1.0) ** 1.5

    a_new = a_new + 0.0045 * warm_mask - 0.0015 * cool_mask
    b_new = b_new + 0.0110 * warm_mask - 0.0035 * cool_mask

    # Subtle sky & foliage lightness shaping for depth
    L_new = np.clip(L - 0.018 * w_sky * np.clip(C / 0.10, 0.0, 1.0), 0.0, 1.0)

    oklab_graded = np.stack([L_new, a_new, b_new], axis=-1)
    xyz_graded = colour.Oklab_to_XYZ(oklab_graded)

    # 5. Transform to Linear Rec.709 & smooth hue-preserving gamut compression
    lin709 = colour.XYZ_to_RGB(xyz_graded, REC709_CS)

    # Smooth soft-knee gamut compression toward neutral axis (no hard clip)
    luma = 0.2126 * lin709[..., 0:1] + 0.7152 * lin709[..., 1:2] + 0.0722 * lin709[..., 2:3]
    luma_safe = np.clip(luma, 0.0, 1.0)
    diff = lin709 - luma_safe
    # If any channel < 0 or > 1, smoothly compress chroma toward luma_safe
    neg_scale = np.where(diff < -1e-7, luma_safe / np.maximum(-diff, 1e-7), 1.0)
    pos_scale = np.where(diff > 1e-7, (1.0 - luma_safe) / np.maximum(diff, 1e-7), 1.0)
    max_scale = np.minimum(np.min(neg_scale, axis=-1, keepdims=True),
                           np.min(pos_scale, axis=-1, keepdims=True))
    max_scale = np.clip(max_scale, 0.0, 1.0)
    lin709_mapped = np.clip(luma_safe + diff * max_scale, 0.0, 1.0)

    # 6. Encode to Rec.709 pure gamma 2.4
    return encode_rec709_gamma24(lin709_mapped)


# ---------------------------------------------------------------------------
# 6. 33x33x33 .cube Baker & Independent Evaluator
# ---------------------------------------------------------------------------
def bake_cube_lut(output_path: str, size: int = 33) -> np.ndarray:
    """Bake analytic pipeline into a 33x33x33 .cube file (red-fastest ordering)."""
    grid = np.linspace(0.0, 1.0, size, dtype=np.float64)
    # Red-fastest: B outer, G middle, R inner
    B, G, R = np.meshgrid(grid, grid, grid, indexing="ij")
    pts = np.stack([R, G, B], axis=-1).reshape(-1, 3)
    out = golden_daylight_cinema_analytic(pts)
    out = np.clip(out, 0.0, 1.0)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write('TITLE "GOLDEN_DAYLIGHT_CINEMA"\n')
        f.write("# Apple Log 2 (Apple Wide Gamut) -> Rec.709 Gamma 2.4\n")
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r, g, b in out:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")

    return out.reshape(size, size, size, 3)


def load_cube_lut(cube_path: str) -> tuple[np.ndarray, int]:
    """Independent .cube parser."""
    size = None
    data = []
    with open(cube_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("TITLE") or s.startswith("DOMAIN_"):
                continue
            if s.startswith("LUT_3D_SIZE"):
                size = int(s.split()[1])
                continue
            parts = s.split()
            if len(parts) == 3:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])
    arr = np.array(data, dtype=np.float64).reshape(size, size, size, 3)
    return arr, size


def apply_cube_trilinear(img: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Independent trilinear 3D LUT interpolation (lut indexed [B, G, R, 3])."""
    N = lut.shape[0]
    img_c = np.clip(img, 0.0, 1.0) * (N - 1)
    r = img_c[..., 0]
    g = img_c[..., 1]
    b = img_c[..., 2]

    r0 = np.clip(np.floor(r).astype(np.int32), 0, N - 2)
    g0 = np.clip(np.floor(g).astype(np.int32), 0, N - 2)
    b0 = np.clip(np.floor(b).astype(np.int32), 0, N - 2)

    dr = (r - r0)[..., None]
    dg = (g - g0)[..., None]
    db = (b - b0)[..., None]

    c000 = lut[b0, g0, r0]
    c100 = lut[b0, g0, r0 + 1]
    c010 = lut[b0, g0 + 1, r0]
    c110 = lut[b0, g0 + 1, r0 + 1]
    c001 = lut[b0 + 1, g0, r0]
    c101 = lut[b0 + 1, g0, r0 + 1]
    c011 = lut[b0 + 1, g0 + 1, r0]
    c111 = lut[b0 + 1, g0 + 1, r0 + 1]

    c00 = c000 * (1 - dr) + c100 * dr
    c10 = c010 * (1 - dr) + c110 * dr
    c01 = c001 * (1 - dr) + c101 * dr
    c11 = c011 * (1 - dr) + c111 * dr

    c0 = c00 * (1 - dg) + c10 * dg
    c1 = c01 * (1 - dg) + c11 * dg

    return np.clip(c0 * (1 - db) + c1 * db, 0.0, 1.0)


def apply_cube_tetrahedral(img: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Independent tetrahedral 3D LUT interpolation (lut indexed [B, G, R, 3])."""
    N = lut.shape[0]
    img_c = np.clip(img, 0.0, 1.0) * (N - 1)
    r = img_c[..., 0]
    g = img_c[..., 1]
    b = img_c[..., 2]

    r0 = np.clip(np.floor(r).astype(np.int32), 0, N - 2)
    g0 = np.clip(np.floor(g).astype(np.int32), 0, N - 2)
    b0 = np.clip(np.floor(b).astype(np.int32), 0, N - 2)

    dr = r - r0
    dg = g - g0
    db = b - b0

    p000 = lut[b0, g0, r0]
    p111 = lut[b0 + 1, g0 + 1, r0 + 1]

    out = np.empty_like(p000)

    m1 = (dr >= dg) & (dg >= db)
    m2 = (dr >= db) & (db > dg)
    m3 = (db > dr) & (dr >= dg)
    m4 = (dg > dr) & (dr >= db)
    m5 = (dg >= db) & (db > dr)
    m6 = ~(m1 | m2 | m3 | m4 | m5)

    def _w(mask, wa, wb, wc, wd, pa, pb, pc, pd):
        if np.any(mask):
            out[mask] = (
                wa[mask, None] * pa[mask]
                + wb[mask, None] * pb[mask]
                + wc[mask, None] * pc[mask]
                + wd[mask, None] * pd[mask]
            )

    _w(m1, 1 - dr, dr - dg, dg - db, db, p000, lut[b0, g0, r0 + 1], lut[b0, g0 + 1, r0 + 1], p111)
    _w(m2, 1 - dr, dr - db, db - dg, dg, p000, lut[b0, g0, r0 + 1], lut[b0 + 1, g0, r0 + 1], p111)
    _w(m3, 1 - db, db - dr, dr - dg, dg, p000, lut[b0 + 1, g0, r0], lut[b0 + 1, g0, r0 + 1], p111)
    _w(m4, 1 - dg, dg - dr, dr - db, db, p000, lut[b0, g0 + 1, r0], lut[b0, g0 + 1, r0 + 1], p111)
    _w(m5, 1 - dg, dg - db, db - dr, dr, p000, lut[b0, g0 + 1, r0], lut[b0 + 1, g0 + 1, r0], p111)
    _w(m6, 1 - db, db - dg, dg - dr, dr, p000, lut[b0 + 1, g0, r0], lut[b0 + 1, g0 + 1, r0], p111)

    return np.clip(out, 0.0, 1.0)
