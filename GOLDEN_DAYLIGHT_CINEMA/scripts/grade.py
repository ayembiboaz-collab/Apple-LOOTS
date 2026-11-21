"""
grade.py
=========

The "GOLDEN DAYLIGHT CINEMA" creative grade.

Full standalone pipeline, evaluated per-pixel so it can be baked into a 3D
.cube LUT:

    Apple Log 2 (Apple Wide Gamut, encoded)
      -> decode Apple Log 2            (Apple's published curve)
      -> linear Apple Wide Gamut
      -> linear Rec.709               (white-preserving primaries matrix)
      -> creative grade               (tone curve + split toning + balance
                                       + luminance-weighted saturation)
      -> Rec.709 gamma 2.4            (output OETF)

The grade is intentionally *luminance-driven* for the tone curve so hue and
saturation are preserved through the contrast shape, with the warmth carried
by a luminance-weighted split tone (honey/amber in sunlit midtones and
highlights, neutral-to-slightly-cool shadows) rather than a flat orange
overlay.  Warmth tapers off near the very top so bright highlights and whites
stay believable, and saturation is protected in the highlights so skies, skin
and foliage stay natural.

All constants are tunable via the GRADE_PARAMS dict so the look can be refined
and the LUT rebuilt reproducibly.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

import color_science as cs


# ---------------------------------------------------------------------------
# Tunable parameters
# ---------------------------------------------------------------------------
GRADE_PARAMS = {
    # --- Base colour balance (applied in tone-mapped linear space) --------
    # Subtle warm base: a touch of red up, blue down.  Kept small so it never
    # becomes a global yellow/orange cast.
    "base_gain": np.array([1.015, 1.000, 0.982]),

    # --- Split toning ----------------------------------------------------
    # Warmth, as a Gaussian on tone-mapped luminance.  Peaks in the sunlit
    # midtone region and tapers toward whites/highlights so they stay
    # believable; hue-weighted (see grade_linear) so blue/cyan skies are
    # protected from desaturation.
    "warm_center": 0.50,
    "warm_sigma": 0.160,
    "warm_tint": np.array([0.044, 0.014, -0.045]),   # honey/amber: +R, +G, -B

    # Subtle cool shadow tint for depth/dimensionality.  Weighted as a bump
    # that is zero in the very deepest shadows (so blacks stay neutral, not
    # blue), peaks in the low/mid shadows and fades into the midtones.
    "cool_tint": np.array([-0.0035, 0.0000, 0.0085]),

    # --- Saturation -----------------------------------------------------
    # Luminance-weighted saturation: boost rich midtones, protect deep
    # shadows and highlights.
    "sat_mid_boost": 0.14,          # peak extra saturation in midtones
    "sat_shadow_protect": 0.12,     # luminance below which boost tapers
    "sat_high_protect": 0.62,       # luminance above which boost tapers

    # --- Tone curve control points (input linear luminance -> output) ----
    # Lifted toe (deep, detailed shadows), filmic S in the midtones (rich),
    # smooth asymptotic highlight roll-off (texture preserved, whites
    # believable).  White (1.0) maps to ~0.85 linear -> ~0.93 encoded.
    "tone_curve": [
        (0.00, 0.0008),
        (0.05, 0.0260),
        (0.12, 0.0600),
        (0.20, 0.1050),
        (0.30, 0.1700),
        (0.45, 0.2700),
        (0.60, 0.3850),
        (0.75, 0.5200),
        (0.88, 0.6650),
        (1.00, 0.8500),
        (1.40, 0.9050),
        (1.90, 0.9400),
        (2.60, 0.9600),
        (3.50, 0.9720),
        (5.00, 0.9800),
    ],
    "tone_asymptote": 0.982,   # clamp for luminance beyond the last point
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _smoothstep(edge0, edge1, x):
    x = np.clip((np.asarray(x, dtype=np.float64) - edge0) / (edge1 - edge0), 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def _gaussian(x, center, sigma):
    d = (np.asarray(x, dtype=np.float64) - center) / sigma
    return np.exp(-0.5 * d * d)


def _luminance(rgb):
    """Rec.709 luminance of linear RGB."""
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _hue_sat(rgb):
    """Return (hue_deg, sat) in [0,360) and [0,1] for linear RGB.

    Hue is 0 for neutrals (saturation ~0); the caller weights warmth by
    saturation so neutrals are not strongly tinted.
    """
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = mx - mn
    sat = np.where(mx > 0, d / np.where(mx == 0, 1.0, mx), 0.0)
    hue = np.zeros_like(mx)
    # Only meaningful where there is chroma.
    m = d > 1e-9
    # Red is max.
    mr = m & (r >= g) & (r >= b)
    hue = np.where(mr, ((g - b) / np.where(d == 0, 1.0, d)) % 6.0, hue)
    mg = m & (g >= r) & (g >= b)
    hue = np.where(mg, (b - r) / np.where(d == 0, 1.0, d) + 2.0, hue)
    mb = m & (b >= r) & (b >= g)
    hue = np.where(mb, (r - g) / np.where(d == 0, 1.0, d) + 4.0, hue)
    hue = np.where(m, hue * 60.0, 0.0)
    return hue, sat


# ---------------------------------------------------------------------------
# Tone curve
# ---------------------------------------------------------------------------
def _build_tone_curve(params):
    pts = np.array(params["tone_curve"], dtype=np.float64)
    xs, ys = pts[:, 0], pts[:, 1]
    asym = params["tone_asymptote"]

    def tone(y):
        y = np.asarray(y, dtype=np.float64)
        out = np.empty_like(y)
        # Below first point / above last point -> clamp (asymptote).
        out[y <= xs[0]] = ys[0]
        out[y >= xs[-1]] = asym
        mid = (y > xs[0]) & (y < xs[-1])
        if np.any(mid):
            interp = PchipInterpolator(xs, ys, extrapolate=False)
            out[mid] = interp(y[mid])
        return out

    return tone


# ---------------------------------------------------------------------------
# Core grade (operates on linear Rec.709 RGB)
# ---------------------------------------------------------------------------
def grade_linear(rgb, params=None):
    """Apply the creative grade to linear Rec.709 RGB.

    Parameters
    ----------
    rgb : array_like, shape (..., 3)
        Linear-light Rec.709 values (>= 0).
    params : dict, optional
        Overrides for GRADE_PARAMS.

    Returns
    -------
    array, same shape as ``rgb``
        Graded linear Rec.709 values (not yet gamma-encoded).
    """
    p = dict(GRADE_PARAMS)
    if params:
        p.update(params)

    rgb = np.array(rgb, dtype=np.float64, copy=True)
    tone = _build_tone_curve(p)
    eps = 1e-6

    # 1) Luminance-based filmic tone curve, preserving chromaticity.
    Y = _luminance(rgb)
    Yt = tone(Y)
    scale = Yt / (Y + eps)
    rgb = rgb * scale[..., None]

    # 2) Base colour balance (subtle warm).
    rgb = rgb * p["base_gain"]

    # 3) Split toning.
    Y2 = _luminance(rgb)
    warm_w = _gaussian(Y2, p["warm_center"], p["warm_sigma"])
    hue, sat = _hue_sat(rgb)
    # Hue-aware warmth: full warmth on warm hues (red/orange/yellow/green) --
    # the warmth on greens counteracts the cyan lean that gamma darkening
    # introduces, keeping foliage a natural warm green -- and ~0 across
    # cyan/blue so skies stay a rich natural blue, not desaturated green.
    prot = _smoothstep(170.0, 195.0, hue) * (1.0 - _smoothstep(260.0, 285.0, hue))
    warm_hue_w = 1.0 - np.clip(prot, 0.0, 1.0)
    sat_norm = np.clip(sat / 0.20, 0.0, 1.0)
    warm_mod = warm_hue_w * (0.35 + 0.65 * sat_norm)
    warm = warm_w[..., None] * warm_mod[..., None] * p["warm_tint"]
    # Cool shadow bump: zero in the deepest shadows, peak in low/mid shadows,
    # fading into the midtones.
    cool_w = _smoothstep(0.0, 0.05, Y2) * (1.0 - _smoothstep(0.16, 0.40, Y2))
    cool_w = np.clip(cool_w, 0.0, 1.0)
    rgb = rgb + warm + cool_w[..., None] * p["cool_tint"]

    # 4) Luminance-weighted saturation (protect shadows + highlights).
    Y3 = _luminance(rgb)
    sat = 1.0 + p["sat_mid_boost"] * (
        _smoothstep(0.0, p["sat_shadow_protect"], Y3)
        * (1.0 - _smoothstep(p["sat_high_protect"], 1.0, Y3))
    )
    Y4 = _luminance(rgb)
    rgb = Y4[..., None] + (rgb - Y4[..., None]) * sat[..., None]

    return rgb


# ---------------------------------------------------------------------------
# Full standalone pipeline: Apple Log 2 encoded -> Rec.709 gamma 2.4 encoded
# ---------------------------------------------------------------------------
_AWG_TO_709 = cs.apple_wide_gamut_to_rec709()


def apple_log2_to_rec709_gamma24(encoded, params=None):
    """Full standalone LUT pipeline.

    Parameters
    ----------
    encoded : array_like, shape (..., 3)
        Apple Log 2 / Apple Wide Gamut encoded values.
    params : dict, optional
        Grade overrides.

    Returns
    -------
    array, same shape
        Rec.709 SDR, gamma 2.4 encoded values, clipped to [0, 1].
    """
    encoded = np.asarray(encoded, dtype=np.float64)
    # 1) Decode Apple Log 2 -> linear Apple Wide Gamut.
    linear_awg = cs.apple_log_to_linear(encoded)
    # 2) Apple Wide Gamut -> linear Rec.709.
    linear_709 = linear_awg @ _AWG_TO_709.T
    # 3) Creative grade.
    graded = grade_linear(linear_709, params=params)
    # 4) Rec.709 gamma 2.4 output.
    out = cs.rec709_gamma24(graded)
    return np.clip(out, 0.0, 1.0)
