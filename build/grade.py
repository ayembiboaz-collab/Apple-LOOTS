"""
GOLDEN DAYLIGHT CINEMA — creative grade and LUT generation.

Pipeline for every LUT node (input = Apple Log 2 code value, full range):
  1. Apple Log 2 decode            -> linear scene reflection, Apple Wide Gamut
  2. Apple Wide Gamut -> Rec.709   -> linear Rec.709 (D65, no adaptation needed)
  3. in-gamut safety               -> soft desaturation of out-of-709 colours
  4. filmic tone map               -> luminance-shaped S-curve, long shoulder
  5. highlight convergence         -> bright chroma rolls to white, no harsh clips
  6. Golden Daylight grade         -> adaptive honey warmth, shaded-cool separation,
                                      hue-selective sky / foliage / skin control
  7. Rec.709 gamma 2.4 encode      -> display code value, clamped 0..1
"""

from __future__ import annotations

import numpy as np

import apple_log2 as al
from apple_log2 import (AWG_TO_709, LUMA_REC709, linear_rec709_to_oklab,
                        oklab_to_linear_rec709, rec709_gamma24_encode,
                        rec709_gamma24_decode)

# ---------------------------------------------------------------------------
# Tone curve.  Anchors are (stops relative to 18% scene grey, Rec.709 code).
# The shape is a film-print style curve: gently compressed toe that keeps
# shadow texture, strong midtone separation, long soft shoulder.
# 18% grey lands on code 0.405 (a deliberate ~0.2 stop under a "camera
# standard" 0.46) which buys roughly half a stop of extra highlight shoulder
# without lifting the image.
# ---------------------------------------------------------------------------
TONE_STOPS = np.array([-20, -16, -13, -12, -10, -8, -6, -5, -4, -3, -2, -1,
                       -0.5, 0, 0.5, 1, 1.5, 2, 2.32, 3, 3.5, 4, 5, 6.06, 8])
TONE_CODE = np.array([0.0080, 0.0100, 0.0125, 0.0140, 0.0260, 0.0480, 0.0790, 0.1010,
                      0.1400, 0.1880, 0.2450, 0.3250, 0.3730, 0.4280, 0.4920, 0.6200,
                      0.7400, 0.8360, 0.9120, 0.9500, 0.9680, 0.9795, 0.9890, 0.9960, 0.9990])

# ---------------------------------------------------------------------------
# Grade constants (single place to tune).
# ---------------------------------------------------------------------------
P = dict(
    # 1. warmth
    warm_r=0.066, warm_g=0.020, warm_b=-0.072,   # linear gains at full strength
    warm_lift=0.020,                              # small midtone light lift
    warm_band_lo=0.045, warm_band_hi_lo=0.26,      # fade in above shadows
    warm_band_hi=0.80, warm_band_hi_top=0.985,     # fade out before white
    warm_chroma_k=0.16,                           # near-neutral surfaces warm most
    warm_gh_k=1.00,                               # golden-hour double-warm guard
    warm_skin_guard=0.45,                         # keep skin believable
    # 2. cool shadow separation
    shadow_tint_r=-0.022, shadow_tint_g=0.002, shadow_tint_b=0.042,
    shadow_band_top=0.235,
    # 3. chroma
    sat_master=1.055,
    mid_sat_boost=0.095,
    sat_chroma_k=0.13,
    highlight_desat=0.45,      # fraction of chroma removed at pure white
    shadow_desat=0.16,
)

# Hue-selective controls: (hue degrees in OKLab, saturation multiplier,
# hue rotation in degrees).  Interpolated periodically and smoothly.
HUE_POINTS = np.array([0, 20, 35, 50, 65, 80, 95, 110, 130, 150, 170,
                       190, 205, 220, 240, 255, 270, 285, 300, 320, 340, 360])
SAT_CURVE = np.array([1.00, 0.99, 0.985, 1.005, 1.005, 1.02, 1.005, 0.90,
                      0.94, 1.00, 1.01, 0.99, 0.93, 0.97, 1.05, 1.09, 1.07,
                      1.02, 0.99, 0.99, 1.00, 1.00])
HUE_ROT = np.array([0, 0, 0, -0.8, -1.2, -1.4, -1.0, 2.5, 4.0, 1.0, 0,
                    2.0, 5.0, 4.0, 2.0, 0.5, 0, -1.0, -1.0, 0, 0, 0])
SKIN_HUE_WEIGHT = np.array([0.0, 0.1, 0.5, 0.85, 0.55, 0.15, 0.0, 0.0, 0.0, 0.0, 0.0,
                            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])


# ---------------------------------------------------------------------------
# Monotone cubic (PCHIP, Fritsch-Carlson) — smooth, shape preserving.
# ---------------------------------------------------------------------------
class Pchip:
    def __init__(self, x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        h = np.diff(x)
        d = np.diff(y) / h
        m = np.zeros_like(y)
        m[1:-1] = self._slopes(h[:-1], h[1:], d[:-1], d[1:])
        m[0] = self._end(h[0], h[1], d[0], d[1])
        m[-1] = self._end(h[-1], h[-2], d[-1], d[-2])
        self.x, self.y, self.m, self.h = x, y, m, h

    @staticmethod
    def _slopes(h0, h1, d0, d1):
        with np.errstate(divide='ignore', invalid='ignore'):
            return Pchip._slopes_raw(h0, h1, d0, d1)

    @staticmethod
    def _slopes_raw(h0, h1, d0, d1):
        w1 = 2 * h1 + h0
        w2 = h1 + 2 * h0
        same = (np.sign(d0) == np.sign(d1)) & (d0 != 0)
        return np.where(same, (w1 + w2) / (w1 / np.where(d0 == 0, 1e-30, d0)
                                           + w2 / np.where(d1 == 0, 1e-30, d1)), 0.0)

    @staticmethod
    def _end(h0, h1, d0, d1):
        m = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if m * d0 <= 0:
            m = 0.0
        elif d0 * d1 < 0 and abs(m) > abs(3 * d0):
            m = 3 * d0
        return m

    def __call__(self, xq):
        xq = np.clip(np.asarray(xq, float), self.x[0], self.x[-1])
        i = np.searchsorted(self.x, xq, side="right") - 1
        i = np.clip(i, 0, len(self.h) - 1)
        t = (xq - self.x[i]) / self.h[i]
        h00 = (1 + 2 * t) * (1 - t) ** 2
        h10 = t * (1 - t) ** 2
        h01 = t * t * (3 - 2 * t)
        h11 = t * t * (t - 1)
        return (h00 * self.y[i] + h10 * self.h[i] * self.m[i]
                + h01 * self.y[i + 1] + h11 * self.h[i] * self.m[i + 1])


_tone = Pchip(TONE_STOPS, TONE_CODE)

_periodic_sat = Pchip(HUE_POINTS, SAT_CURVE)
_periodic_rot = Pchip(HUE_POINTS, HUE_ROT)
_periodic_skin = Pchip(HUE_POINTS, SKIN_HUE_WEIGHT)


def tone_code(scene_luma):
    """Scene luminance (0..12) -> Rec.709 code value of the filmic curve."""
    s = np.log2(np.maximum(scene_luma, 1e-9) / 0.18)
    return _tone(s)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _hue_lerp_wrap(curve, hue_deg):
    """Evaluate a periodic curve given hue in radians."""
    h = np.degrees(hue_deg) % 360.0
    return curve(h)


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------
def soft_desaturate_to_gamut(rgb, eps=2.2e-3):
    """Pull out-of-gamut (negative) linear Rec.709 colours inside the gamut by
    desaturating toward their luminance.

    The negative excursion is passed through a smooth (C1) max first, so the
    compression factor has no kink at the gamut boundary.  A kink here would be
    magnified into visible interpolation error by a 33^3 LUT.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    Y = rgb @ LUMA_REC709
    mn = rgb.min(axis=-1)
    # smooth MIN(mn, 0): the amount by which the colour falls outside the gamut
    mn_neg = 0.5 * (mn - np.sqrt(mn * mn + eps * eps))
    k = np.clip(Y / np.maximum(Y - mn_neg, 1e-9), 0.0, 1.0)
    return Y[..., None] + (rgb - Y[..., None]) * k[..., None]


def tone_map(scene, p=P):
    """Luminance-driven filmic tone map with a highlight white convergence."""
    Y = np.maximum(scene @ LUMA_REC709, 0.0)
    y_out = rec709_gamma24_decode(tone_code(Y))
    scale = np.where(Y > 1e-7, y_out / np.maximum(Y, 1e-7), 0.0)
    out = soft_floor(scene) * scale[..., None]

    # Smooth per-channel shoulder: a very bright channel is eased to white
    # instead of being hard clipped, which keeps hue direction (a saturated
    # colour stays saturated) and has no derivative break.
    out = soft_clip(out, knee=0.88)

    # Gentle filmic chroma falloff toward white, driven by luminance only and
    # spread over a wide range so bright sky keeps its colour.
    Yd = out @ LUMA_REC709
    w = smoothstep(0.78, 1.0, Yd)
    keep = 1.0 - p["highlight_desat"] * w
    out = Yd[..., None] + (out - Yd[..., None]) * keep[..., None]

    # a touch of chroma removal in the deepest shadows keeps blacks clean
    ws = 1.0 - smoothstep(0.0, 0.10, Yd)
    keep_s = 1.0 - p["shadow_desat"] * ws
    out = Yd[..., None] + (out - Yd[..., None]) * keep_s[..., None]
    return soft_floor(out)


def adaptive_warmth(rgb, p=P):
    """Honey/amber lift applied where it reads as sunlight rather than a filter.

    Weighting:
      * midtone band only (nothing in deep shadow, nothing at white)
      * strongest on near-neutral surfaces (stone, concrete, sunlit skin base)
      * reduced when the pixel is already warm (golden hour must not double up)
      * reduced through the skin hue range
    """
    Y = np.maximum(rgb @ LUMA_REC709, 1e-8)
    band = smoothstep(p["warm_band_lo"], p["warm_band_hi_lo"], Y) * \
        (1.0 - smoothstep(p["warm_band_hi"], p["warm_band_hi_top"], Y))
    chroma = rgb.max(axis=-1) - rgb.min(axis=-1)
    neutral_gate = 1.0 / (1.0 + (chroma / p["warm_chroma_k"]) ** 2)

    lab = linear_rec709_to_oklab(np.clip(rgb, 0, None))
    _, _, hue = al.oklab_chroma_hue(lab)
    skin = _hue_lerp_wrap(_periodic_skin, hue)

    # already-warm guard: (R-B) relative to luminance
    warm_existing = np.clip((rgb[..., 0] - rgb[..., 2]) / Y, 0.0, 2.0)
    gh_guard = 1.0 - p["warm_gh_k"] * smoothstep(0.08, 0.48, warm_existing)

    w = band * neutral_gate * gh_guard * (1.0 - p["warm_skin_guard"] * skin)

    gains = np.array([p["warm_r"], p["warm_g"], p["warm_b"]])
    lit = rgb * (1.0 + w[..., None] * gains[None, :])
    # keep luminance: the warmth is a tint, not an exposure change
    Yn = lit @ LUMA_REC709
    lit = lit * (Y / np.maximum(Yn, 1e-8))[..., None]
    # gentle midtone light lift (deliberately not in the highlights)
    lift = 1.0 + p["warm_lift"] * band * neutral_gate * (1.0 - 0.6 * skin)
    return lit * lift[..., None]


def shadow_separation(rgb, p=P):
    """Very restrained cool bias in the shadows: sun/shade separation."""
    Y = np.maximum(rgb @ LUMA_REC709, 1e-8)
    w = 1.0 - smoothstep(0.0, p["shadow_band_top"], Y)
    gains = np.array([p["shadow_tint_r"], p["shadow_tint_g"], p["shadow_tint_b"]])
    out = rgb * (1.0 + w[..., None] * gains[None, :])
    Yn = out @ LUMA_REC709
    return out * (Y / np.maximum(Yn, 1e-8))[..., None]


def hue_selective(rgb, p=P):
    """OKLab chroma/hue shaping: sky, cyan, foliage, skin, warm stone."""
    lab = linear_rec709_to_oklab(np.clip(rgb, 1e-8, None))
    L, C, h = al.oklab_chroma_hue(lab)
    sat_mult = _hue_lerp_wrap(_periodic_sat, h)
    rot = np.radians(_hue_lerp_wrap(_periodic_rot, h))
    skin = _hue_lerp_wrap(_periodic_skin, h)

    # global saturation plus a midtone-only richness boost
    band = smoothstep(0.05, 0.30, L) * (1.0 - 0.75 * smoothstep(0.75, 1.0, L))
    mult = p["sat_master"] * sat_mult * (1.0 + p["mid_sat_boost"] * band)
    # chroma-limited: the boost fades out on already-vivid colour, so skies and
    # golden-hour light get richer, not radioactive
    mult = 1.0 + (mult - 1.0) / (1.0 + (C / p["sat_chroma_k"]) ** 2)
    mult = 1.0 + (mult - 1.0) * (1.0 - 0.55 * skin)     # skin stays calm

    # chroma has to vanish at black and at white for a clean ramp
    mult = mult * (1.0 - smoothstep(0.93, 1.0, C))       # avoid over-saturated edges
    C2 = C * mult
    lab2 = al.set_oklab_chroma_hue(lab, C2, h + rot * (1.0 - 0.75 * skin))
    return soft_desaturate_to_gamut(oklab_to_linear_rec709(lab2))


def soft_floor(x, eps=2.2e-4):
    """C1 smooth max(x, 0): keeps near-black values from being hard clipped,
    which is what would otherwise put kinks into the 33^3 LUT."""
    x = np.asarray(x, float)
    return 0.5 * (x + np.sqrt(x * x + eps * eps))


def soft_clip(x, knee=0.90):
    """C1-continuous safety shoulder so nothing ever hard-clips."""
    x = np.asarray(x, float)
    over = x > knee
    y = x.copy()
    y[over] = knee + (1.0 - knee) * np.tanh((x[over] - knee) / (1.0 - knee))
    return y


# ---------------------------------------------------------------------------
# The full LUT transform (code value in -> code value out)
# ---------------------------------------------------------------------------
def transform(code_in, params=P, return_stages=False):
    """Apple Log 2 code value (0..1) -> Rec.709 gamma 2.4 code value (0..1)."""
    arr = np.clip(np.asarray(code_in, dtype=np.float64), 0.0, 1.0)
    shape = arr.shape
    code_in = arr.reshape(-1, 3)          # work in a guaranteed (N, 3) layout

    scene_awg = al.decode(code_in)                 # 1. Apple Log 2 decode
    scene_709 = scene_awg @ AWG_TO_709.T           # 2. gamut conversion
    scene_709 = soft_desaturate_to_gamut(scene_709)  # 3. in-gamut safety
    display = tone_map(np.clip(scene_709, 0.0, None), params)  # 4./5.
    display = adaptive_warmth(display, params)     # 6. the look
    display = shadow_separation(display, params)
    display = hue_selective(display, params)
    display = soft_floor(display)
    display = soft_clip(display, knee=0.94)
    code_out = rec709_gamma24_encode(np.clip(display, 0.0, 1.0))  # 7.
    code_out = np.clip(code_out, 0.0, 1.0)
    code_out = code_out.reshape(shape)
    if return_stages:
        return code_out, dict(scene_awg=scene_awg.reshape(shape),
                              scene_709=scene_709.reshape(shape),
                              display=display.reshape(shape))
    return code_out


# ---------------------------------------------------------------------------
# LUT grid
# ---------------------------------------------------------------------------
def build_lut(size=33):
    """Return array (size,size,size,3); index order [R,G,B] -> cube layout."""
    v = np.linspace(0.0, 1.0, size)
    R, G, B = np.meshgrid(v, v, v, indexing="ij")     # R slowest -> B fastest
    grid = np.stack([R, G, B], axis=-1)
    out = transform(grid)
    assert np.isfinite(out).all()
    return out
