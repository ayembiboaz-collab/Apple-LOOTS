#!/usr/bin/env python3
"""
GOLDEN DAYLIGHT CINEMA — Apple Log 2 / Apple Wide Gamut -> Rec.709 gamma 2.4
standalone cinematic 3D LUT.

Pipeline (all in float64):
  1. Decode Apple Log 2 transfer function -> linear scene-referred Apple Wide Gamut.
  2. Convert linear Apple Wide Gamut -> linear Rec.709 (D65, no CAT; both D65).
  3. Apply the GOLDEN DAYLIGHT CINEMA creative grade in linear Rec.709.
  4. Encode Rec.709 gamma 2.4 (with a smooth highlight roll-off).

Verified constants are documented in ../SOURCES/TECHNICAL_NOTES.md.
"""
import numpy as np
from scipy.interpolate import PchipInterpolator

# ----------------------------------------------------------------------------
# Apple Log 2 transfer function (Apple white paper / ACES CSC)
# ----------------------------------------------------------------------------
R0 = -0.05641088
RT = 0.01
C = 47.28711236
BETA = 0.00964052
GAMMA = 0.08550479
DELTA = 0.69336945
PT = C * (RT - R0) ** 2


def apple_log2_decode(v):
    """Apple Log 2 (and Apple Log) decode: code value -> linear scene value."""
    v = np.asarray(v, dtype=np.float64)
    out = np.full_like(v, R0)
    m_toe = (v >= 0.0) & (v < PT)
    m_log = v >= PT
    out[m_toe] = np.sqrt(v[m_toe] / C) + R0
    out[m_log] = np.power(2.0, (v[m_log] - DELTA) / GAMMA) - BETA
    return out


def apple_log2_encode(l):
    """Inverse of decode (used to SIMULATE Apple Log 2 from a reference)."""
    l = np.asarray(l, dtype=np.float64)
    out = np.zeros_like(l)
    m_toe = (l >= R0) & (l < RT)
    m_log = l >= RT
    out[m_toe] = C * (l[m_toe] - R0) ** 2
    out[m_log] = GAMMA * np.log2(l[m_log] + BETA) + DELTA
    return out


# ----------------------------------------------------------------------------
# Apple Wide Gamut -> Rec.709 linear matrix (D65 on both sides, no CAT)
# ----------------------------------------------------------------------------
AWG_TO_REC709 = np.array([
    [1.70728038, -0.51901992, -0.18826046],
    [-0.12501075, 1.31466236, -0.18965162],
    [-0.04362433, -0.19121437, 1.23483871],
])
REC709_TO_AWG = np.linalg.inv(AWG_TO_REC709)


def awg_linear_to_rec709_linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return rgb @ AWG_TO_REC709.T


def rec709_linear_to_awg_linear(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return rgb @ REC709_TO_AWG.T


# ----------------------------------------------------------------------------
# Rec.709 gamma 2.4 output encoding
# ----------------------------------------------------------------------------
OUT_GAMMA = 2.4


def rec709_gamma24_encode(lin, rolloff=True):
    """linear Rec.709 -> Rec.709 gamma 2.4 display code value (0..1).
    A gentle per-channel highlight shoulder keeps speculars in range and
    rolls them off smoothly."""
    lin = np.asarray(lin, dtype=np.float64)
    if rolloff:
        lin = highlight_rolloff(lin)
    return np.power(np.clip(lin, 0.0, None), 1.0 / OUT_GAMMA)


def highlight_rolloff(lin, knee=0.86, softness=0.24):
    """Smooth filmic shoulder so speculars roll off instead of clipping."""
    lin = np.asarray(lin, dtype=np.float64)
    x = lin
    y = np.where(x <= knee, x,
                 knee + (1.0 - knee) * (1.0 - np.exp(-(x - knee) / softness)))
    return y


def rec709_gamma24_decode(code):
    """Inverse of encode (for diagnostics / validation)."""
    return np.power(np.clip(np.asarray(code, dtype=np.float64), 0.0, 1.0), OUT_GAMMA)


# ----------------------------------------------------------------------------
# GOLDEN DAYLIGHT CINEMA creative grade (linear Rec.709 in -> linear Rec.709 out)
# ----------------------------------------------------------------------------
def _tone_curve():
    """Monotonic S-curve with a deep, never-crushed toe, rich midtones and a
    soft highlight shoulder. Extends below 0 and above 1 so log shadows and
    speculars are handled smoothly. Applied to luminance (see _luminance_tone)
    so hue and saturation are preserved."""
    xs = np.array([-0.06, -0.03, 0.0, 0.03, 0.08, 0.15, 0.25, 0.40,
                   0.55, 0.70, 0.80, 0.90, 1.0, 1.4])
    ys = np.array([-0.040, -0.015, 0.0010, 0.0090, 0.035, 0.080, 0.160,
                   0.340, 0.550, 0.760, 0.850, 0.920, 0.950, 0.950])
    pc = PchipInterpolator(xs, ys, extrapolate=True)
    return pc


_TONE = _tone_curve()


def _tone(lin):
    """Tone curve applied to a scalar luminance. Rolls off smoothly above
    ~0.8 linear and saturates at 0.95, giving a gentle highlight roll-off
    without a hard per-channel clip."""
    out = _TONE(lin)
    over = lin > 1.4
    if np.any(over):
        out[over] = 0.950
    return np.clip(out, 0.0, 0.950)


def _luminance_tone(rgb):
    """Apply the tone curve to luminance only, rescaling RGB by L'/L.
    This preserves hue AND saturation while delivering the contrast, deep
    shadows and highlight roll-off. Used in shadows/midtones."""
    L = _luma(rgb)
    Lp = _tone(L)
    s = np.where(L > 1e-6, Lp / np.maximum(L, 1e-6), 0.0)
    return rgb * s[..., None]


def _perchannel_tone(rgb):
    """Apply the tone curve to each channel independently. Separable, so the
    3D function is smooth and trilinear interpolation is well-behaved in the
    highlight region. Used at highlights."""
    return _tone(rgb)


def _tone_map(rgb):
    """Hybrid: luminance tone-map (saturation preserving) in shadows/midtones,
    blending to a per-channel tone-map (separable) in the highlights. The
    blend is smooth in luminance, avoiding highlight interpolation artefacts
    while keeping foliage/skin saturation intact in the mid-tones."""
    L = _luma(rgb)
    w = np.clip((L - 0.55) / 0.20, 0.0, 1.0)
    return _luminance_tone(rgb) * (1.0 - w[..., None]) + _perchannel_tone(rgb) * w[..., None]


def _luma(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def _hue_sat(rgb):
    """Return (hue_deg, sat) computed in a perceptual-ish way from linear rgb."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    delta = mx - mn
    sat = delta / np.maximum(mx, 1e-6)
    # hue
    hue = np.zeros_like(mx)
    d = np.maximum(delta, 1e-9)
    idx = (mx == r) & (delta > 0)
    hue[idx] = (60 * (((g[idx] - b[idx]) / d[idx]) % 6))
    idx = (mx == g) & (delta > 0)
    hue[idx] = (60 * (((b[idx] - r[idx]) / d[idx]) + 2))
    idx = (mx == b) & (delta > 0)
    hue[idx] = (60 * (((r[idx] - g[idx]) / d[idx]) + 4))
    hue = hue % 360.0
    return hue, sat


def _hue_weight(hue):
    """Protect skin and foliage from over-saturation; keep sky controlled."""
    h = hue % 360.0
    w = np.ones_like(h)
    w = w - (1.0 - P_SKIN_VIB_GUARD) * np.exp(-(((h - 30.0) / 14.0) ** 2))
    w = w - 0.18 * np.exp(-(((h - 222.0) / 20.0) ** 2))
    w = w - (1.0 - P_FOL_VIB_GUARD) * np.exp(-(((h - 110.0) / 35.0) ** 2))
    return np.clip(w, 0.2, 1.0)


# Grade parameters (tuned, documented).
P_WARM_AMOUNT = 0.042     # overall amber warmth strength
P_WARM_CENTER = 0.45      # luminance the warmth peaks at (fades in highlights)
P_WARM_WIDTH = 0.27
P_WARM_SHADOW = 0.025     # extra atmospheric warmth deep in shadows
P_VIB_AMOUNT = 0.22       # vibrance strength
P_VIB_CENTER = 0.46
P_VIB_WIDTH = 0.42
P_SKY_DEEPEN = 0.014      # subtle blue enrichment
P_FOLIAGE_WARM = 0.0      # warmth guard handles the slight green warmth
P_SKIN_WARM_GUARD = 0.80  # reduce warmth on skin hues (avoid orange skin)
P_FOL_WARM_GUARD = 0.86   # reduce warmth on foliage hues (avoid yellow-green)
P_SKIN_VIB_GUARD = 0.72   # reduce vibrance on skin hues
P_FOL_VIB_GUARD = 0.72    # reduce vibrance on foliage hues


def grade_linear(rgb):
    """Apply the GOLDEN DAYLIGHT CINEMA grade. rgb: linear Rec.709 (any shape)."""
    rgb = np.asarray(rgb, dtype=np.float64)

    # 1) Tone / contrast — hybrid luminance/per-channel tone-map
    out = _tone_map(rgb)
    L = _luma(out)

    # Hue/saturation used to protect skin from warmth and over-saturation.
    hue, sat = _hue_sat(out)

    # 2) Warmth — honey/amber in midtones & sunlit surfaces, fading in whites.
    #    Multiplicative warm matrix: warms neutrals (stone/concrete) but PRESERVES
    #    the hue of saturated colours, so foliage stays green (no yellow-green
    #    rotation). Guarded off skin & foliage hues to keep them natural.
    warm_w = np.exp(-(((L - P_WARM_CENTER) / P_WARM_WIDTH) ** 2))
    warm_w = warm_w + P_WARM_SHADOW * np.exp(-((L / 0.08) ** 2))
    skin_hue = np.exp(-(((hue - 30.0) / 15.0) ** 2))
    fol_hue = np.exp(-(((hue - 110.0) / 32.0) ** 2))
    warm_mask = warm_w * (1.0 - P_SKIN_WARM_GUARD * skin_hue) \
                        * (1.0 - P_FOL_WARM_GUARD * fol_hue)
    warm_dev = np.array([P_WARM_AMOUNT, P_WARM_AMOUNT * 0.22, -P_WARM_AMOUNT])
    out = out * (1.0 + warm_mask[..., None] * warm_dev)

    # 3) Vibrance — controlled, midtone weighted, skin/sky protected
    hue2, sat2 = _hue_sat(out)
    hw = _hue_weight(hue2)
    vib_w = np.exp(-(((L - P_VIB_CENTER) / P_VIB_WIDTH) ** 2))
    factor = 1.0 + P_VIB_AMOUNT * (1.0 - sat2) * vib_w * hw
    L2 = _luma(out)
    out = L2[..., None] + (out - L2[..., None]) * factor[..., None]

    # 4) Hue-targeted polish: deepen sky blue, warm foliage toward gold
    hue3, _ = _hue_sat(out)
    sky = np.exp(-(((hue3 - 222.0) / 24.0) ** 2))
    fol = np.exp(-(((hue3 - 112.0) / 34.0) ** 2))
    out[..., 0] *= (1.0 - P_SKY_DEEPEN * sky + P_FOLIAGE_WARM * fol)
    out[..., 1] *= (1.0 - 0.5 * P_SKY_DEEPEN * sky - 0.3 * P_FOLIAGE_WARM * fol)
    out[..., 2] *= (1.0 + P_SKY_DEEPEN * sky - 0.6 * P_FOLIAGE_WARM * fol)

    return out


# ----------------------------------------------------------------------------
# Full standalone LUT function: Apple Log 2 code value -> Rec.709 gamma 2.4
# ----------------------------------------------------------------------------
def lut_apply(rgb_log, creative=True):
    """Apply the standalone LUT to Apple Log 2 code values (0..1)."""
    rgb_log = np.asarray(rgb_log, dtype=np.float64)
    lin_awg = apple_log2_decode(rgb_log)
    lin709 = awg_linear_to_rec709_linear(lin_awg)
    if creative:
        lin709 = grade_linear(lin709)
    return rec709_gamma24_encode(lin709)


def lut_apply_neutral(rgb_log):
    """Technical-only path (decode + gamut + gamma 2.4), no creative grade."""
    return lut_apply(rgb_log, creative=False)


# ----------------------------------------------------------------------------
# Simulation of Apple Log 2 from a Rec.709 reference image
# ----------------------------------------------------------------------------
def simulate_apple_log2_from_rec709(rgb_sdr):
    """
    Documented simulation: treat a Rec.709 gamma-2.4 reference image as the
    correctly-exposed, correctly-graded scene, take it to linear Rec.709, convert
    to linear Apple Wide Gamut, and encode with the Apple Log 2 curve.
    Returns Apple Log 2 code values (the 'raw log' the LUT would receive).
    """
    rgb_sdr = np.asarray(rgb_sdr, dtype=np.float64)
    lin709 = rec709_gamma24_decode(rgb_sdr)
    lin_awg = rec709_linear_to_awg_linear(lin709)
    return apple_log2_encode(lin_awg)


def view_log_as_rec709(rgb_log):
    """How raw Apple Log 2 looks when displayed straight through Rec.709
    gamma 2.4 with no conversion (the 'BEFORE' appearance)."""
    return rec709_gamma24_encode(rgb_log, rolloff=False)


# ----------------------------------------------------------------------------
# Build the .cube LUT
# ----------------------------------------------------------------------------
def build_cube(path, size=33, creative=True, title="GOLDEN DAYLIGHT CINEMA"):
    idx = np.linspace(0.0, 1.0, size)
    grid = np.stack(np.meshgrid(idx, idx, idx, indexing="ij"), axis=-1)  # (n,n,n,3)
    flat = grid.reshape(-1, 3)
    out = lut_apply(flat, creative=creative).reshape(grid.shape)

    lines = []
    lines.append(f"TITLE \"{title}\"")
    lines.append(f"LUT_3D_SIZE {size}")
    lines.append("# Input: Apple Log 2 / Apple Wide Gamut")
    lines.append("# Output: Rec.709 SDR, gamma 2.4")
    lines.append("# Generated by golden_daylight.py")
    for i in range(size):
        for j in range(size):
            for k in range(size):
                r, g, b = out[i, j, k]
                lines.append(
                    f"{r:.6f} {g:.6f} {b:.6f}"
                )
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return out


if __name__ == "__main__":
    import sys
    out = build_cube(sys.argv[1] if len(sys.argv) > 1 else "GOLDEN_DAYLIGHT_CINEMA.cube")
    print("built", out.shape)
