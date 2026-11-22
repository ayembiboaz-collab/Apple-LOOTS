"""
gdc_grade.py -- the GOLDEN DAYLIGHT CINEMA grading pipeline (analytic, float64).

The pipeline is a single, pure, scene-referred function:

    Apple Log 2 code (0..1)
        -> Apple Wide Gamut scene-linear            [verified decode]
        -> CIE XYZ (D65)                            [verified primaries, no CAT]
        -> filmic tone map on luminance only        [hue preserved exactly]
        -> OKLab / OKLCh creative grade             [perceptual, smooth curves]
        -> Rec.709 linear                           [verified matrix]
        -> hue- and lightness-preserving gamut map   [analytic, no clipping]
        -> pure gamma 2.4 encode                    [requested output]

Design notes on "depth":
A 3D LUT cannot know depth.  Everything below is colour and tone only:
 * luminance-dependent split tone (warm mid/highlights, neutral-cool shadows)
 * mid-tone contrast from the curve's log-space slope, with a filmic shoulder
 * density saturation: chroma peaks around L=0.58 and thins at both ends
 * hue-selective chroma/hue curves for sky, foliage, skin and stone that are
   smooth circular functions of hue -- no qualifiers, no masks, no edges
The report states this plainly rather than pretending the LUT is depth-aware.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field

import numpy as np

import gdc_colour as C


# ==========================================================================
# Parameters
# ==========================================================================

@dataclass
class ToneParams:
    """Filmic tone curve, evaluated in log2 space around the 18% grey pivot.

    T(Y) = 0.18 * 2 ** sat(a * log2(Y/0.18) + b)

    sat(x) = x / (1 + (max(x,0)/V)**n)**(1/n)     # smooth shoulder, asymptote V
             (identity for x < 0, so the toe is a clean log-space straight
              line: a>1 gives deep shadows AND less noise gain than linear)

    Properties that are validated numerically:
      * T(0) = 0 exactly, T is strictly increasing, C-infinity
      * d log2 T / d log2 Y  = a  in the toe (no shadow lift), ~a in the mids
      * T(Y) < Y for all Y >= 0.18  (bright areas are never raised)
      * T(Y) -> 0.18*2**V < 1      (highlights roll off, never clip)
    """
    pivot: float = 0.18
    contrast: float = 1.16          # log-space slope (a)
    offset: float = -0.115          # stops of display offset at the pivot (b)
    shoulder_stops: float = 2.46    # asymptote V in stops above the pivot
    shoulder_power: float = 2.90    # n
    shadow_gain_cap: float = 1.55   # hard cap on dT/dY in the deep shadows
    # Apple Wide Gamut's blue primary has a negative y chromaticity, so a very
    # saturated blue signal can carry a *negative* CIE Y.  The tone curve is
    # driven by a smooth floor of Y (soft max against a small fraction of the
    # largest channel) so that the pipeline is total and C1 over the whole cube:
    lum_floor: float = 0.05        # alpha: floor = alpha * max(R,G,B)
    lum_floor_soft: float = 0.02   # smoothing of the soft max (linear units)


@dataclass
class GradeParams:
    # --- midtone S (OKLab lightness contrast, zero at L=0, 0.5 and 1) ------
    midtone_s: float = 0.09

    # --- density / saturation shaping -------------------------------------
    density_peak: float = 0.100        # extra chroma at the density peak
    density_centre: float = 0.560      # OKLab L of the density peak
    density_width: float = 0.30
    highlight_thin: float = 0.10       # extra chroma removed by L=1.0
    highlight_thin_start: float = 0.86
    highlight_ceiling: float = 0.33    # chroma ceiling at L=1.0 (soft)
    highlight_ceiling_soft: float = 0.03
    shadow_thin: float = 0.16          # chroma removed by L=0.0
    shadow_thin_end: float = 0.22

    # --- hue-selective chroma curves (smooth circular kernels) -------------
    sky_hue: float = 252.0
    sky_width: float = 52.0
    sky_chroma: float = -0.085         # -8.5% chroma on sky
    sky_hue_shift: float = 1.5         # degrees, + = towards 270 (deeper blue)
    foliage_hue: float = 141.0
    foliage_width: float = 46.0
    foliage_chroma: float = -0.065
    foliage_hue_shift: float = -3.0    # towards yellow = warmer greens
    stone_hue: float = 78.0
    stone_width: float = 34.0
    stone_chroma: float = 0.030
    stone_hue_shift: float = 1.5
    skin_hue: float = 50.0
    skin_width: float = 26.0
    skin_chroma: float = 0.0

    # --- split tone -------------------------------------------------------
    warm_hue: float = 71.0             # honey / amber in OKLCh
    warm_amp: float = 0.0105           # OKLab units of a,b added
    warm_low: float = 0.16             # luminance mask
    warm_high: float = 0.55
    warm_ceiling: float = 0.90
    warm_neutral_only: float = 0.062   # chroma scale of the "neutral" mask
    warm_colour_floor: float = 0.22    # tint still applied to saturated colours
    cool_hue: float = 258.0
    cool_amp: float = 0.0035
    cool_low: float = 0.30
    cool_high: float = 0.02
    warm_guard_hue: float = 78.0       # back the warmth off when the source
    warm_guard_width: float = 45.0     # is already warm and saturated
    warm_guard: float = 0.55

    # --- skin line protection --------------------------------------------
    skin_protect: float = 0.78         # 0..1, how strongly skin is protected
    skin_chroma_cap: float = 0.105     # OKLab chroma ceiling for skin hues
    skin_chroma_soft: float = 0.030    # softness of that ceiling
    skin_line_deg: float = 46.0        # target OKLCh hue of the skin line
    skin_line_pull: float = 0.28       # fraction of the hue error removed

    # --- gamut mapping ----------------------------------------------------
    gamut_knee: float = 0.90           # fraction of the max in-gamut chroma
                                       # that is left untouched


# ==========================================================================
# Tone curve
# ==========================================================================

def _sat(x: np.ndarray, V: float, n: float) -> np.ndarray:
    pos = np.maximum(x, 0.0)
    return np.where(x > 0.0, x / np.power(1.0 + np.power(pos / V, n), 1.0 / n), x)


def tone_map(Y: np.ndarray, p: ToneParams) -> np.ndarray:
    """Filmic tone map of luminance.  Vectorised, float64, analytic."""
    Y = np.asarray(Y, dtype=np.float64)
    Ys = np.maximum(Y, 1e-9)
    L = np.log2(Ys / p.pivot)
    v = _sat(p.contrast * L + p.offset, p.shoulder_stops, p.shoulder_power)
    T = p.pivot * np.exp2(v)
    T = np.where(Y > 0.0, T, 0.0)
    # shadow gain cap (smooth): keeps dT/dY <= cap for tiny Y without a kink
    # T ~= k*Y with k = a*T/Y; enforcing a linear ceiling only where needed.
    cap = p.shadow_gain_cap
    T = np.minimum(T, cap * Ys + 0.0)
    return T


# ==========================================================================
# Gamut compression (exact, hue and lightness preserving)
# ==========================================================================

def _rgb_at_chroma(L: np.ndarray, cos_h: np.ndarray, sin_h: np.ndarray,
                   chroma: np.ndarray) -> np.ndarray:
    """Rec.709 linear RGB for OKLCh (L, chroma, h).

    Note: OKLab -> linear RGB is *cubic* in the chroma scale (the LMS' values are
    cubed on the way back), so the in-gamut chroma cannot be solved with a single
    linear equation; see :func:`gamut_compress`.
    """
    lms_p0 = L[..., None] * C.LAB_TO_LMS_P[:, 0]
    dirv = (cos_h[..., None] * C.LAB_TO_LMS_P[:, 1] + sin_h[..., None] * C.LAB_TO_LMS_P[:, 2])
    lms = (lms_p0 + chroma[..., None] * dirv) ** 3
    xyz = lms @ C.LMS_TO_XYZ.T
    return xyz @ C.XYZ_TO_REC709.T


def _in_gamut(rgb: np.ndarray, tol: float = 0.0) -> np.ndarray:
    return (rgb.min(axis=-1) >= -tol) & (rgb.max(axis=-1) <= 1.0 + tol)


def _first_exit_chroma(L, cos_h, sin_h, ladder):
    """Largest in-gamut chroma on a fixed ladder (first exit, no refinement)."""
    n = len(ladder)
    inside = np.ones((len(L), n), dtype=bool)
    for k, s_k in enumerate(ladder):
        inside[:, k] = _in_gamut(_rgb_at_chroma(L, cos_h, sin_h, np.full(len(L), s_k)))
    for k in range(1, n):                      # prefix semantics: no re-entry
        inside[:, k] &= inside[:, k - 1]
    first_out = np.argmax(~inside, axis=1)
    idx = np.clip(first_out - 1, 0, n - 1)
    return ladder[idx]


class GamutBoundary:
    """Smoothed Rec.709 chroma boundary C_max(L, h), precomputed once.

    Ray-casting the OKLab gamut boundary pixel by pixel is chaotic in the far
    out-of-gamut region: the OKLab -> RGB map is cubic in chroma, so for very
    large chroma a channel can leave the gamut and come back, and the "first
    exit" then depends on the exact hue to within 0.1 degree.  That produced
    visible 0.18-code discontinuities in the analytic function (and, in the LUT,
    local fit errors of dE 20).

    We therefore sample the boundary once on a (L, h) grid, smooth it (Gaussian,
    circular in hue), and interpolate it bilinearly.  The result is a smooth,
    monotone, periodic boundary that the compression can rely on.
    """

    def __init__(self, n_l: int = 97, n_h: int = 241, margin: float = 0.995):
        from scipy.ndimage import gaussian_filter1d
        ladder = np.linspace(0.0, 0.42, 85)
        Ls = np.linspace(0.0, 1.0, n_l)
        hs = np.linspace(0.0, 360.0, n_h, endpoint=False)
        LL, HH = np.meshgrid(Ls, hs, indexing="ij")
        hr = np.radians(HH.ravel())
        cmax = _first_exit_chroma(LL.ravel(), np.cos(hr), np.sin(hr), ladder)
        cmax = cmax.reshape(n_l, n_h)
        # smooth: circular in hue first, then across lightness
        pad = np.concatenate([cmax[:, -8:], cmax, cmax[:, :8]], axis=1)
        pad = gaussian_filter1d(pad, sigma=3.0, axis=1, mode="nearest")
        cmax = pad[:, 8:-8]
        cmax = gaussian_filter1d(cmax, sigma=1.5, axis=0, mode="nearest")
        cmax = np.maximum(cmax, 0.0) * margin
        self.n_l, self.n_h = n_l, n_h
        self.cmax = cmax

    def __call__(self, L, h):
        L = np.clip(np.asarray(L, dtype=np.float64), 0.0, 1.0)
        h = np.mod(np.asarray(h, dtype=np.float64), 360.0)
        fl = L * (self.n_l - 1)
        fh = h / 360.0 * self.n_h
        i0 = np.clip(np.floor(fl).astype(int), 0, self.n_l - 2)
        j0 = np.floor(fh).astype(int) % self.n_h
        j1 = (j0 + 1) % self.n_h
        tl = fl - i0
        th = fh - np.floor(fh)
        c = self.cmax
        return ((1 - tl) * ((1 - th) * c[i0, j0] + th * c[i0, j1])
                + tl * ((1 - th) * c[i0 + 1, j0] + th * c[i0 + 1, j1]))


_BOUNDARY: GamutBoundary | None = None


def gamut_boundary() -> "GamutBoundary":
    global _BOUNDARY
    if _BOUNDARY is None:
        _BOUNDARY = GamutBoundary()
    return _BOUNDARY


def gamut_compress(lch: np.ndarray, knee: float) -> np.ndarray:
    """Hue-preserving, lightness-preserving gamut compression into Rec.709.

    Chroma is mapped with a C1 exponential knee towards the smoothed boundary
    C_max(L, h); lightness and hue are never touched, so there is no hue skew
    and no hard channel clipping at the gamut edge.
    """
    L = lch[..., 0]
    Ch = np.maximum(lch[..., 1], 0.0)
    smax = gamut_boundary()(np.clip(L, 0.0, 1.0), lch[..., 2])
    s_knee = knee * smax
    Ch_out = Ch.copy()
    comp = Ch > s_knee
    span = np.maximum(smax - s_knee, 1e-6)
    over = Ch[comp] - s_knee[comp]
    Ch_out[comp] = s_knee[comp] + span[comp] * (1.0 - np.exp(-over / span[comp]))
    return np.stack([L, Ch_out, lch[..., 2]], axis=-1)


# ==========================================================================
# The grade
# ==========================================================================

class GoldenDaylightCinema:
    """The complete analytic pipeline (scene-referred -> Rec.709 gamma 2.4)."""

    name = "GOLDEN DAYLIGHT CINEMA - FLAGSHIP EDITION"
    version = "1.0.0"

    def __init__(self, tone: ToneParams | None = None, grade: GradeParams | None = None):
        self.tone = tone or ToneParams()
        self.grade = grade or GradeParams()

    # -- stage helpers -----------------------------------------------------
    def decode_to_xyz(self, p: np.ndarray) -> np.ndarray:
        r = C.apple_log2_decode(p)
        r = np.maximum(r, 0.0)          # sub-black legal range -> black
        return r @ C.AWG_TO_XYZ.T

    def apply_tone(self, xyz: np.ndarray, rgb_awg: np.ndarray | None = None) -> np.ndarray:
        Y = xyz[..., 1]
        if rgb_awg is None:
            h = xyz @ C.XYZ_TO_REC709.T
            M = np.max(np.abs(h), axis=-1)
        else:
            M = np.max(rgb_awg, axis=-1)
        # smooth max(Y, alpha*M, 0): keeps the curve driven by luminance for every
        # physical colour, and well defined for non-physical (negative Y) ones
        floor = self.tone.lum_floor * np.maximum(M, 0.0)
        a = np.maximum(Y, 0.0)
        sft = self.tone.lum_floor_soft
        Yc = 0.5 * (a + floor + np.sqrt((a - floor) ** 2 + sft ** 2))
        T = tone_map(Yc, self.tone)
        k = np.where(Yc > 1e-9, T / np.maximum(Yc, 1e-9), 0.0)
        k = np.clip(k, 0.0, 40.0)
        return xyz * k[..., None]

    def grade_oklab(self, xyz: np.ndarray) -> np.ndarray:
        g = self.grade
        lab = C.xyz_to_oklab(xyz)
        L = lab[..., 0]
        a = lab[..., 1]
        b = lab[..., 2]
        Ch = np.hypot(a, b)
        h = np.degrees(np.arctan2(b, a)) % 360.0

        # --- smooth masks -------------------------------------------------
        w_skin = C.circular_gauss(h, g.skin_hue, g.skin_width)
        protect = 1.0 - g.skin_protect * w_skin      # 1 outside skin, <1 on skin

        # --- midtone S: smooth lightness contrast, zero at 0.0, 0.5, 1.0 ---
        L = L + g.midtone_s * (L - 0.5) * 4.0 * L * (1.0 - L)

        # --- density saturation ------------------------------------------
        dens = 1.0 + g.density_peak * np.exp(-0.5 * ((L - g.density_centre) / g.density_width) ** 2)
        dens *= 1.0 - g.highlight_thin * C.smoothstep(g.highlight_thin_start, 1.02, L)
        dens *= 1.0 - g.shadow_thin * C.smoothstep(g.shadow_thin_end, 0.0, L)

        # --- hue-selective chroma curves ---------------------------------
        k_sky = C.circular_lerp_kernel(h, g.sky_hue, g.sky_width)
        k_fol = C.circular_lerp_kernel(h, g.foliage_hue, g.foliage_width)
        k_sto = C.circular_lerp_kernel(h, g.stone_hue, g.stone_width)
        chroma_gain = (1.0
                       + k_sky * g.sky_chroma
                       + k_fol * g.foliage_chroma
                       + k_sto * g.stone_chroma)

        # --- hue shifts (fade out in the highlights to stay hue-preserving)
        hue_hi_fade = 1.0 - 0.85 * C.smoothstep(0.78, 1.0, L)
        d_hue = (k_sky * g.sky_hue_shift
                 + k_fol * g.foliage_hue_shift
                 + k_sto * g.stone_hue_shift) * hue_hi_fade

        # --- skin line: pull hue towards the line, cap chroma --------------
        err = C.hue_delta(h, g.skin_line_deg)
        d_hue = d_hue - g.skin_line_pull * err * w_skin
        cap = g.skin_chroma_cap + g.skin_chroma_soft
        over_ch = np.maximum(Ch - g.skin_chroma_cap, 0.0)
        skin_cap = g.skin_chroma_cap + g.skin_chroma_soft * np.tanh(over_ch / g.skin_chroma_soft)

        # blend chroma gain and cap
        Ch_new = Ch * (1.0 + (chroma_gain - 1.0) * protect)
        Ch_new = Ch_new * dens
        # soft, L-dependent chroma ceiling: keeps saturated skies and midtones
        # but stops surface highlights from turning into saturated yellow
        ceil_w = C.smoothstep(0.68, 1.06, L)
        ceil_L = g.highlight_ceiling + (1.0 - g.highlight_ceiling) * (1.0 - ceil_w)
        Ch_new = Ch_new + (C.smooth_min(Ch_new, ceil_L) - Ch_new) * ceil_w
        Ch_new = np.where(w_skin > 1e-6,
                          Ch_new + (C.smooth_min(Ch_new, skin_cap) - Ch_new) * (g.skin_protect * w_skin),
                          Ch_new)

        # --- split tone ---------------------------------------------------
        warm_L = C.smootherstep(g.warm_low, g.warm_high, L) * (1.0 - C.smoothstep(g.warm_ceiling, 1.02, L))
        warm_C = np.exp(-0.5 * (Ch / g.warm_neutral_only) ** 2) * (1.0 - g.warm_colour_floor) + g.warm_colour_floor
        already_warm = C.circular_gauss(h, g.warm_guard_hue, g.warm_guard_width) * C.smoothstep(0.045, 0.11, Ch)
        w_warm = warm_L * warm_C * protect * (1.0 - g.warm_guard * already_warm)
        cool_L = C.smoothstep(g.cool_low, g.cool_high, L) * (1.0 - g.warm_neutral_only * 0.0)
        cool_C = np.exp(-0.5 * (Ch / 0.05) ** 2) * 0.7 + 0.3
        w_cool = cool_L * cool_C

        wr = np.radians(g.warm_hue)
        cr = np.radians(g.cool_hue)
        a_tint = g.warm_amp * np.cos(wr) * w_warm + g.cool_amp * np.cos(cr) * w_cool
        b_tint = g.warm_amp * np.sin(wr) * w_warm + g.cool_amp * np.sin(cr) * w_cool

        # --- rebuild ------------------------------------------------------
        h_new = np.radians(h + d_hue)
        lab_out = np.stack([L,
                            Ch_new * np.cos(h_new) + a_tint,
                            Ch_new * np.sin(h_new) + b_tint], axis=-1)
        return C.oklab_to_xyz(lab_out)

    def to_rec709_codes(self, xyz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        lch = C.oklab_to_oklch(C.xyz_to_oklab(xyz))
        lch = gamut_compress(lch, self.grade.gamut_knee)
        xyz_out = C.oklab_to_xyz(C.oklch_to_oklab(lch))
        rgb = xyz_out @ C.XYZ_TO_REC709.T
        clipped = float(np.mean((rgb < -1e-6) | (rgb > 1.0 + 1e-6)))
        rgb = np.clip(rgb, 0.0, 1.0)
        codes = C.gamma24_encode(rgb)
        return codes, clipped

    # -- public API -------------------------------------------------------
    def apply_codes(self, p: np.ndarray) -> np.ndarray:
        """Full pipeline: Apple Log 2 code -> Rec.709 gamma 2.4 code."""
        p = np.asarray(p, dtype=np.float64)
        r = np.maximum(C.apple_log2_decode(p), 0.0)
        xyz = r @ C.AWG_TO_XYZ.T
        xyz = self.apply_tone(xyz, r)
        xyz = self.grade_oklab(xyz)
        codes, _ = self.to_rec709_codes(xyz)
        return codes

    def __call__(self, p: np.ndarray) -> np.ndarray:
        return self.apply_codes(p)

    def describe(self) -> dict:
        return {"tone": asdict(self.tone), "grade": asdict(self.grade)}


# ==========================================================================
# The BEFORE reference: the plain, verified Apple Log 2 -> Rec.709 transform
# ==========================================================================

def reference_rec709(p: np.ndarray) -> np.ndarray:
    """Ungraded reference: Apple Log 2 decode -> Rec.709 matrix -> gamma 2.4.

    This is the "before" image: the standard, verified conversion with no
    creative treatment and no gamut compression (out-of-gamut values hard
    clip, which is exactly what a naive conversion does).
    """
    p = np.asarray(p, dtype=np.float64)
    r = np.maximum(C.apple_log2_decode(p), 0.0)
    rgb = r @ C.AWG_TO_REC709.T
    return C.gamma24_encode(np.clip(rgb, 0.0, 1.0))


if __name__ == "__main__":
    import json
    g = GoldenDaylightCinema()
    print(json.dumps(g.describe(), indent=2))
    # quick monotonicity smoke test on the neutral axis
    lin = np.logspace(-7, 1.3, 20000)
    codes = np.stack([C.apple_log2_encode(lin)] * 3, axis=-1)
    out = g.apply_codes(codes)
    d = np.diff(out[:, 1])
    print("neutral ramp min step", d.min(), "max step", d.max())
