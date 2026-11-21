"""
grade.py — GOLDEN DAYLIGHT CINEMA creative grade.

The complete, standalone transform:

    Apple Log 2 (Apple Wide Gamut, normalised 0-1)
        -> Apple Log decode  -> linear Apple Wide Gamut
        -> matrix            -> linear Rec.709 (D65, no CAT needed)
        -> gamut compression -> in-gamut linear Rec.709
        -> scene-linear creative stage
        -> filmic tonescale (per-channel + hue restoration)
        -> display-referred creative stage
        -> Rec.709 / gamma 2.4 code values

Everything below operates on (..., 3) float64 arrays. `transform()` is the
single function baked into the delivered .cube.
"""

from __future__ import annotations

import numpy as np

from applelog2 import (
    AWG_TO_REC709,
    REC709_LUMA,
    FilmicSigmoid,
    apple_log_decode,
    apply_matrix,
    gamut_compress,
)

EPS = 1e-10


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def luma(rgb):
    return np.einsum("...i,i->...", rgb, REC709_LUMA)


def hue_bump(h_deg, centre, width):
    """Smooth 0..1 window on the hue circle: 1 at `centre`, 0 at +/- `width`."""
    d = ((h_deg - centre + 180.0) % 360.0) - 180.0
    t = np.clip(np.abs(d) / width, 0.0, 1.0)
    return (1.0 - t * t) ** 2


def to_ych(rgb):
    """RGB -> (luma, Cb', Cr') where Cb' = B - Y, Cr' = R - Y.

    Hue angle = degrees(atan2(-Cb', Cr')) mod 360 puts the primaries at the
    familiar wheel positions:
        red 15 deg, yellow 86 deg, green 135 deg,
        cyan 195 deg, blue 266 deg, magenta 315 deg.
    """
    Y = luma(rgb)
    cb = rgb[..., 2] - Y
    cr = rgb[..., 0] - Y
    return Y, cb, cr


def from_ych(Y, cb, cr):
    """Inverse of to_ych(); exact reconstruction."""
    r = Y + cr
    b = Y + cb
    g = (Y - REC709_LUMA[0] * r - REC709_LUMA[2] * b) / REC709_LUMA[1]
    return np.stack([r, g, b], axis=-1)


def hue_angle(cb, cr):
    return np.degrees(np.arctan2(-cb, cr)) % 360.0


def rotate_hue(cb, cr, degrees):
    """Rotate the chroma vector by `degrees` on the hue circle defined by
    hue_angle(). Positive = towards the next primary (R -> Y -> G -> C -> B -> M).

    hue_angle uses h = atan2(-cb, cr), i.e. (u, v) = (-cb, cr). A rotation by
    +d in that frame is
        v' = v cos d - u sin d  ->  cr' =  cr cos d + cb sin d
        u' = v sin d + u cos d  ->  cb' =  cb cos d - cr sin d
    """
    th = np.radians(degrees)
    c, s = np.cos(th), np.sin(th)
    return cb * c - cr * s, cr * c + cb * s


def gamma24_encode(L):
    return np.clip(L, 0.0, 1.0) ** (1.0 / 2.4)


def gamma24_decode(V):
    return np.clip(V, 0.0, 1.0) ** 2.4


# ---------------------------------------------------------------------------
# Look parameters — the single source of truth for GOLDEN DAYLIGHT CINEMA
# ---------------------------------------------------------------------------

LOOK = dict(
    # ---- scene-linear stage -------------------------------------------------
    # 0 EV: harsh midday footage must NOT be made brighter.
    exposure_ev=0.0,
    # Gentle scene-linear warmth ("the light itself is warm"), energy
    # normalised so the operation does not change exposure.
    sunlight_gain=(1.0180, 0.9995, 0.9640),
    # Pre-tonescale chroma taming of very bright saturated values, so the
    # per-channel shoulder cannot twist hues in the sun.
    bright_chroma_start=0.60,  # scene-linear luma where taming begins
    bright_chroma_end=7.00,
    bright_chroma_amount=0.26,
    # ---- tonescale ----------------------------------------------------------
    ts_y_pivot=0.4050,  # 18 % grey -> this gamma-2.4 code value
    ts_slope=0.2520,  # code value per stop at the pivot (contrast)
    ts_x_max=6.30,  # stops above grey that reach display white
    ts_power_shoulder=1.72,
    ts_x_min=-10.50,  # stops below grey that reach display black
    ts_power_toe=1.14,
    hue_restore=0.46,  # how much of the pre-tonescale hue to restore
    hue_restore_hi_falloff=(0.80, 1.00),  # taper so the sun still blooms white
    # ---- display-referred stage --------------------------------------------
    # Honey / amber warmth, luminance windowed: strong in midtones, weak in
    # deep shadow, released in the highlights so whites stay believable.
    honey_tint=(1.0620, 1.0140, 0.9330),
    honey_amount=0.72,
    honey_window=(0.055, 0.260, 0.600, 0.940),  # in0, in1, out0, out1
    honey_shadow_floor=0.16,  # residual warmth below the window
    honey_highlight_floor=0.17,  # residual warmth above the window
    # Shadows: deep, slightly cool, never crushed. Returns to neutral at the
    # very bottom so blacks do not go blue.
    shade_tint=(0.9840, 0.9975, 1.0260),
    shade_amount=0.40,
    shade_window=(0.012, 0.055, 0.150, 0.360),
    # Explicit white protection: anything that reads as a bright neutral is
    # pulled back towards neutral.
    white_protect_start=0.840,
    white_protect_end=0.995,
    white_protect_amount=0.62,
    white_protect_sat_limit=0.26,
    # ---- hue-selective shaping ---------------------------------------------
    # (centre_deg, width_deg, hue_rotation_deg, saturation_scale, luma_scale)
    hue_ops=(
        ("red", 12.0, 30.0, +2.0, 0.945, 1.000),
        ("skin", 44.0, 30.0, -2.5, 0.910, 1.000),
        ("stone_yellow", 78.0, 34.0, -3.0, 0.955, 1.000),
        ("foliage", 122.0, 40.0, -7.5, 0.880, 0.985),
        ("cyan", 192.0, 34.0, +12.0, 0.760, 1.000),
        ("sky", 243.0, 42.0, +3.5, 1.060, 1.000),
        ("magenta", 318.0, 30.0, -3.0, 0.930, 1.000),
    ),
    # ---- global saturation shaping -----------------------------------------
    sat_global=1.045,
    sat_shadow=(0.00, 0.14, 0.86),  # below lo -> scale, smooth to 1.0 at hi
    sat_highlight=(0.78, 1.00, 0.70),  # above lo -> scale toward this at hi
    # ---- final tonal polish (code space) ------------------------------------
    micro_contrast=0.055,  # small extra S about the pivot
    micro_pivot=0.4050,
    black_point=0.0000,
    white_point=1.0000,
)


# ---------------------------------------------------------------------------
# Stage implementations
# ---------------------------------------------------------------------------


def _energy_normalised_gain(gain):
    g = np.asarray(gain, dtype=np.float64)
    return g / float(np.dot(g, REC709_LUMA))


def scene_linear_stage(lin, p):
    """Exposure, sunlight warmth and pre-tonescale chroma taming."""
    lin = lin * (2.0 ** p["exposure_ev"])
    lin = lin * _energy_normalised_gain(p["sunlight_gain"])

    # Bright-chroma taming: blend very bright saturated values towards their
    # own luminance. Keeps the sun from going neon through the shoulder.
    Y = luma(lin)
    w = smoothstep(p["bright_chroma_start"], p["bright_chroma_end"], Y) * p[
        "bright_chroma_amount"
    ]
    lin = lin + w[..., None] * (Y[..., None] - lin)
    return np.maximum(lin, 0.0)


def tonescale_stage(lin, curve, p):
    """Per-channel filmic sigmoid with partial hue restoration.

    Per-channel curves give film-like highlight desaturation (the sun burns
    cleanly to white) but skew hues; the restoration step rotates the result
    back towards the chroma-preserving hue by `hue_restore`.
    """
    pc = curve.from_linear(lin)  # (..., 3) code values

    # Chroma-preserving reference: input chromaticity at the output luminance.
    Ylin = np.maximum(luma(lin), EPS)
    Ycode = curve.from_linear(Ylin)
    ref_disp = np.clip(gamma24_decode(Ycode)[..., None] * (lin / Ylin[..., None]), 0.0, 1.0)
    ref = gamma24_encode(ref_disp)

    Yp, cb_p, cr_p = to_ych(pc)
    _, cb_r, cr_r = to_ych(ref)

    h_p = hue_angle(cb_p, cr_p)
    h_r = hue_angle(cb_r, cr_r)
    delta = ((h_r - h_p + 180.0) % 360.0) - 180.0

    w = p["hue_restore"] * (
        1.0
        - 0.72 * smoothstep(p["hue_restore_hi_falloff"][0], p["hue_restore_hi_falloff"][1], Yp)
    )
    cb_n, cr_n = rotate_hue(cb_p, cr_p, w * delta)
    return from_ych(Yp, cb_n, cr_n)


def _weighted_tint(code, tint, weight):
    """Luminance-preserving chroma tint, blended by a per-pixel weight."""
    Y0 = luma(code)
    t = code * np.asarray(tint, dtype=np.float64)
    Y1 = luma(t)
    t = t * np.where(Y1 > EPS, Y0 / np.maximum(Y1, EPS), 1.0)[..., None]
    return code + weight[..., None] * (t - code)


def warmth_stage(code, p):
    """Honey midtones, cool-neutral shade, protected whites."""
    Y = luma(code)

    i0, i1, o0, o1 = p["honey_window"]
    w = smoothstep(i0, i1, Y) * (1.0 - smoothstep(o0, o1, Y))
    w = np.maximum(w, p["honey_shadow_floor"] * smoothstep(0.004, i1, Y) * (1.0 - smoothstep(o0, o1, Y)))
    w = np.maximum(w, p["honey_highlight_floor"] * smoothstep(o0, o1, Y))
    w = np.maximum(w, p["honey_shadow_floor"] * smoothstep(0.004, i0, Y))
    code = _weighted_tint(code, p["honey_tint"], w * p["honey_amount"])

    s0, s1, s2, s3 = p["shade_window"]
    ws = smoothstep(s0, s1, Y) * (1.0 - smoothstep(s2, s3, Y))
    code = _weighted_tint(code, p["shade_tint"], ws * p["shade_amount"])
    return code


def white_protect_stage(code, p):
    """Pull bright, low-saturation values back towards neutral so sunlit
    whites, clouds and concrete read as white rather than yellow."""
    Y, cb, cr = to_ych(code)
    chroma = np.sqrt(cb * cb + cr * cr)
    sat = chroma / np.maximum(Y, EPS)

    w = smoothstep(p["white_protect_start"], p["white_protect_end"], Y)
    w = w * (1.0 - smoothstep(0.0, p["white_protect_sat_limit"], sat))
    k = 1.0 - w * p["white_protect_amount"]
    return from_ych(Y, cb * k, cr * k)


def hue_selective_stage(code, p):
    """Sky, foliage, skin, stone, cyan and magenta shaping."""
    Y, cb, cr = to_ych(code)
    chroma = np.sqrt(cb * cb + cr * cr)
    h = hue_angle(cb, cr)

    # Only act where there is actually some chroma, so near-neutrals are safe.
    sat = chroma / np.maximum(Y, EPS)
    active = smoothstep(0.012, 0.075, sat)

    rot = np.zeros_like(h)
    sat_scale = np.ones_like(h)
    luma_scale = np.ones_like(h)
    for _name, centre, width, d_hue, d_sat, d_luma in p["hue_ops"]:
        w = hue_bump(h, centre, width) * active
        rot = rot + w * d_hue
        sat_scale = sat_scale * (1.0 + w * (d_sat - 1.0))
        luma_scale = luma_scale * (1.0 + w * (d_luma - 1.0))

    cb_n, cr_n = rotate_hue(cb, cr, rot)
    return from_ych(Y * luma_scale, cb_n * sat_scale, cr_n * sat_scale)


def saturation_stage(code, p):
    Y, cb, cr = to_ych(code)
    s = np.full_like(Y, p["sat_global"])

    lo, hi, scale = p["sat_shadow"]
    s = s * (1.0 + (scale - 1.0) * (1.0 - smoothstep(lo, hi, Y)))

    lo, hi, scale = p["sat_highlight"]
    s = s * (1.0 + (scale - 1.0) * smoothstep(lo, hi, Y))

    return from_ych(Y, cb * s, cr * s)


def polish_stage(code, p):
    """A small extra S-curve for midtone richness, then black/white points."""
    a = p["micro_contrast"]
    if a != 0.0:
        pv = p["micro_pivot"]
        x = np.clip(code, 0.0, 1.0)
        # Smooth, monotonic, fixed at 0, pivot and 1.
        lo = x / pv
        hi = (x - pv) / (1.0 - pv)
        s_lo = pv * (lo + a * lo * (lo - 1.0) * (lo + 0.5))
        s_hi = pv + (1.0 - pv) * (hi + a * hi * (hi - 1.0) * (hi - 1.5))
        code = np.where(x < pv, s_lo, s_hi)

    bp, wp = p["black_point"], p["white_point"]
    if bp != 0.0 or wp != 1.0:
        code = (code - bp) / (wp - bp)
    return code


# ---------------------------------------------------------------------------
# The complete transform
# ---------------------------------------------------------------------------


def make_curve(p=LOOK):
    return FilmicSigmoid(
        x_pivot=0.0,
        y_pivot=p["ts_y_pivot"],
        slope=p["ts_slope"],
        x_max=p["ts_x_max"],
        y_max=1.0,
        power_shoulder=p["ts_power_shoulder"],
        x_min=p["ts_x_min"],
        y_min=0.0,
        power_toe=p["ts_power_toe"],
    )


def technical_only(P, p=LOOK):
    """Neutral reference: Apple Log 2 -> Rec.709 gamma 2.4 with the project's
    tonescale but NO creative grade. Used only for comparison renders."""
    lin = np.maximum(apple_log_decode(np.clip(P, 0.0, 1.0)), 0.0)
    lin = apply_matrix(lin, AWG_TO_REC709)
    lin = np.maximum(gamut_compress(lin), 0.0)
    curve = make_curve(p)
    code = tonescale_stage(lin, curve, p)
    return np.clip(code, 0.0, 1.0)


def transform(P, p=LOOK):
    """Apple Log 2 normalised code values -> Rec.709 gamma 2.4 code values.

    This is the exact function baked into GOLDEN_DAYLIGHT_CINEMA.cube.
    """
    P = np.clip(np.asarray(P, dtype=np.float64), 0.0, 1.0)

    # --- technical decode ---------------------------------------------------
    lin = apple_log_decode(P)  # linear Apple Wide Gamut, 0.18 = 18 % grey
    lin = np.maximum(lin, 0.0)  # Apple Log encodes below black; SDR starts at 0
    lin = apply_matrix(lin, AWG_TO_REC709)  # both D65, so no CAT
    lin = np.maximum(gamut_compress(lin), 0.0)

    # --- creative ------------------------------------------------------------
    lin = scene_linear_stage(lin, p)
    code = tonescale_stage(lin, make_curve(p), p)
    code = warmth_stage(code, p)
    code = hue_selective_stage(code, p)
    code = white_protect_stage(code, p)
    code = saturation_stage(code, p)
    code = polish_stage(code, p)

    return np.clip(code, 0.0, 1.0)
