"""
GOLDEN DAYLIGHT CINEMA - creative grade.

Operates after technical decode/matrix into linear Rec.709.
Everything here is smooth and LUT-friendly (no spatially varying ops).
"""
import numpy as np
from scipy.interpolate import PchipInterpolator

from lut_core import REC709_LUMA

# ---------------------------------------------------------- tone curve ------
# Linear Y (Rec.709 luma of linear-light reflectance, 1.0 = diffuse white,
# up to ~12.0 = Apple Log 2 white clipping at 1200% reflectance)
# -> linear Y' that the output stage encodes with gamma 1/2.4.
XLIN = np.array([0.0, 0.004, 0.02, 0.05, 0.10, 0.18, 0.30, 0.50, 0.75,
                 1.0, 1.5, 2.2, 3.2, 4.7, 6.8, 9.5, 12.0])
YOUT = np.array([0.0, 0.0025, 0.0115, 0.033, 0.076, 0.158, 0.250, 0.385,
                 0.525, 0.720, 0.805, 0.862, 0.905, 0.930, 0.953, 0.975, 1.0])
_tone = PchipInterpolator(XLIN, YOUT, extrapolate=False)


def tone_map_Y(Y):
    Y = np.clip(Y, 0.0, 12.0)
    return _tone(Y)


def tone_ratio(Y):
    """Y'/Y continuous at Y=0 (uses limiting slope), for out-of-gamut saturated colours."""
    eps = 1e-6
    T = tone_map_Y(np.maximum(Y, 0.0))
    Ti0 = _tone(np.array([eps]))[0] / eps  # slope at 0
    return np.where(Y > eps, T / np.maximum(Y, eps), Ti0)


# ------------------------------------------------------- colour tweaks ------
# luminance-based honey bump for upper mids / sunlit surfaces
HONEY_C, HONEY_W = 0.62, 0.30
HONEY_R, HONEY_G, HONEY_B = 0.066, 0.024, -0.066
# subtle cool toe for shadows (depth, not blue cast)
SHADOW_L = 0.34
SHADOW_R, SHADOW_B = -0.034, 0.062  # G solved so the toe is luma-neutral
# highlight whitening (desaturate speculars so whites stay believable)
HILITE_LO = 0.78
HILITE_DESAT = 0.30
# vibrance + global saturation (encoded, chroma around luma)
VIBRANCE = 0.20
GLOBAL_SAT = 1.07
# hue-specific: (center_deg, halfwidth_deg, dh_deg, sat_mult)
GREEN = (115.0, 55.0, -8.0, 0.90)
CYAN = (184.0, 30.0, 13.0, 0.86)
BLUE = (238.0, 36.0, 1.0, 1.06)
SKIN = (23.0, 17.0, 1.5, 0.68)
RED = (356.0, 24.0, 0.0, 0.92)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _hue_weight(h, center, halfwidth):
    d = np.abs((h - center + 180.0) % 360.0 - 180.0)
    w = np.clip(1.0 - d / halfwidth, 0.0, 1.0)
    return w * w * (3.0 - 2.0 * w)


def rgb_to_hsl(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.max(rgb, axis=-1)
    mn = np.min(rgb, axis=-1)
    d = mx - mn
    l = (mx + mn) * 0.5
    s = np.where(d > 1e-9, d / np.maximum(1.0 - np.abs(2.0 * l - 1.0), 1e-6), 0.0)
    h = np.zeros_like(l)
    m = d > 1e-9
    rc = np.divide(np.where(m, mx - r, 0.0), np.maximum(d, 1e-9))
    gc = np.divide(np.where(m, mx - g, 0.0), np.maximum(d, 1e-9))
    bc = np.divide(np.where(m, mx - b, 0.0), np.maximum(d, 1e-9))
    hr = np.where(mx == r, bc - gc, np.where(mx == g, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (hr * 60.0) % 360.0
    h = np.where(m, h, 0.0)
    return h, s, l


def hsl_to_rgb(h, s, l):
    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    hp = (h % 360.0) / 60.0
    x = c * (1.0 - np.abs(hp % 2.0 - 1.0))
    z = np.zeros_like(c)
    seg = np.floor(hp).astype(np.int64) % 6
    r = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [c, x, z, z, x, c])
    g = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [x, c, c, x, z, z])
    b = np.select([seg == 0, seg == 1, seg == 2, seg == 3, seg == 4, seg == 5],
                  [z, z, x, c, c, x])
    m = l - c * 0.5
    return np.stack([r + m, g + m, b + m], axis=-1)


def grade_linear_709(lin):
    """Linear Rec.709 scene values -> graded linear Rec.709 values.

    Tone scale on luma, then a soft gamut compression that continuously pulls
    out-of-gamut chroma back inside the display gamut (no per-channel clipping
    cliffs, no discontinuities at channel crossings).
    """
    lin = np.asarray(lin, dtype=np.float64)
    Y = lin @ REC709_LUMA
    ratio = np.clip(tone_ratio(Y), 0.0, 80.0)
    lin2 = lin * ratio[..., None]
    return lin2


def grade_display(v):
    """v in [0,1]^3 (values already ^(1/2.4) encoded, pre-clamp) -> graded [0,1]."""
    v = np.asarray(v, dtype=np.float64)
    lv = v @ REC709_LUMA

    mx = v.max(axis=-1, keepdims=True)
    mn = v.min(axis=-1, keepdims=True)
    chroma_ratio = (mx - mn) / np.maximum(mx, 1e-6)  # 0..1

    # vibrance (stronger on dull colours) + global saturation
    vg = 1.0 + VIBRANCE * np.power(np.clip(1.0 - chroma_ratio, 0.0, 1.0), 1.25)
    g = GLOBAL_SAT * vg
    v = lv[..., None] + (v - lv[..., None]) * g

    # honey bump on upper mids (sunlit surfaces), fading before white;
    # scaled by saturation so neutral greys stay believable while warm
    # colourful surfaces (stone, sand, foliage in sun) get the full effect
    w = np.exp(-np.square((lv - HONEY_C) / HONEY_W))
    honey_gate = 0.28 + 0.72 * _smoothstep(0.015, 0.22, chroma_ratio[..., 0])
    w = w * honey_gate
    gains = np.stack([1.0 + HONEY_R * w, 1.0 + HONEY_G * w, 1.0 + HONEY_B * w], axis=-1)
    v = v * gains

    # subtle cool shadows, exactly luma-neutral (G solved from Rec.709 luma)
    u = np.power(np.clip((SHADOW_L - lv) / SHADOW_L, 0.0, 1.0), 1.6)
    shadow_g = -(0.2126 * SHADOW_R + 0.0722 * SHADOW_B) / 0.7152
    gains = np.stack([1.0 + SHADOW_R * u, 1.0 + shadow_g * u, 1.0 + SHADOW_B * u], axis=-1)
    v = v * gains

    # highlight whitening: pull near-white chroma down
    hwhite = _smoothstep(HILITE_LO, 0.99, lv)
    lv2 = v @ REC709_LUMA
    v = v * (1.0 - HILITE_DESAT * hwhite[..., None]) + (lv2[..., None] * (HILITE_DESAT * hwhite[..., None]))

    # hue-specific shaping in HSL
    h, s, l = rgb_to_hsl(np.clip(v, 0.0, 1.0))
    mx = v.max(axis=-1); mn = v.min(axis=-1)
    sat_gate = _smoothstep(0.08, 0.22, (mx - mn) / np.maximum(mx, 1e-6))

    dh = np.zeros_like(h)
    s_mul = np.ones_like(h)
    wg = _hue_weight(h, GREEN[0], GREEN[1]); dh += GREEN[2] * wg; s_mul *= (1.0 + (GREEN[3] - 1.0) * wg)
    wc = _hue_weight(h, CYAN[0], CYAN[1]);  dh += CYAN[2] * wc;   s_mul *= (1.0 + (CYAN[3] - 1.0) * wc)
    wb = _hue_weight(h, BLUE[0], BLUE[1]);  dh += BLUE[2] * wb;   s_mul *= (1.0 + (BLUE[3] - 1.0) * wb)
    ws = _hue_weight(h, SKIN[0], SKIN[1]) * sat_gate
    dh += SKIN[2] * ws;                      s_mul *= (1.0 + (SKIN[3] - 1.0) * ws)
    wr = _hue_weight(h, RED[0], RED[1]);    dh += RED[2] * wr;    s_mul *= (1.0 + (RED[3] - 1.0) * wr)

    h = (h + dh) % 360.0
    s = np.clip(s * s_mul, 0.0, 1.0)
    v = hsl_to_rgb(h, s, l)

    return np.clip(v, 0.0, 1.0)


def grade_full(lin_709):
    """Full grade: linear R709 -> output code value in [0,1] (gamma 2.4)."""
    lin2 = grade_linear_709(lin_709)
    v = np.power(np.clip(lin2, 0.0, None), 1.0 / 2.4)
    return grade_display(v)
