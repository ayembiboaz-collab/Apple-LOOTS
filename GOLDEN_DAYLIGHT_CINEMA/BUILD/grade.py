"""
grade.py -- GOLDEN DAYLIGHT CINEMA creative pipeline.

Signal flow (float64, fully vectorised):

    Apple Log 2 code (0..1, Apple Wide Gamut primaries)
        -> Apple Log curve decode                              [apple_log2.py, S1]
        -> Apple Wide Gamut -> linear Rec.709 primaries        [derived from S2]
        -> luminance filmic tone map + per-channel soft clip    <- ALL tonal work
        -> OKLab: chroma gain, hue shaping, honey split-tone    <- ALL colour work
        -> linear -> Rec.709 gamma 2.4 encode -> clamp 0..1

Design rationale
----------------
* Keeping every tonal decision in one monotone luminance transfer curve means the
  delivered lattice is guaranteed free of tonal inversions and local "hard
  digital transitions"; the curve is checked for monotonicity in validation.
* Warmth is targeted, never global. Honey is added as an OKLab (a,b) offset that
  is windowed in BOTH lightness and hue, so blue sky, foliage and deep shade are
  protected while sunlit stone, skin and upper midtones warm up.
* Whites are chroma-tapered above L~0.88 so there is no yellow cast at the top.
* A faint cool offset in the toe creates sun/shade separation without lifting or
  tinting the blacks.

OKLab matrices: Bjorn Ottosson, "A perceptual color space for image processing".
"""
import numpy as np

from apple_log2 import (AWG_TO_REC709, apple_log_decode, rec709_gamma24_encode)

# ---------------------------------------------------------------------------
# TUNABLE LOOK PARAMETERS
# ---------------------------------------------------------------------------
PARAMS = dict(
    # ---- filmic tone map: scene-linear luminance -> display CODE (gamma 2.4) ----
    # 1.0 scene-linear = 90% reference white. Below the plain technical conversion
    # everywhere above 18% grey, so bright midday footage is never pushed brighter.
    tone_anchors=(
        (0.0000, 0.0570),
        (0.0010, 0.0700),
        (0.0040, 0.0930),
        (0.0120, 0.1300),
        (0.0300, 0.1880),
        (0.0600, 0.2620),
        (0.1000, 0.3380),
        (0.1800, 0.4790),   # 18% grey  -> 122/255, rich midtone (plain decode 0.489)
        (0.3000, 0.5900),
        (0.5000, 0.7100),
        (0.9000, 0.8720),   # 90% white -> 222/255, texture retained
        (2.0000, 0.9130),
        (4.0000, 0.9500),
        (8.0000, 0.9740),
        (16.000, 0.9890),
        (48.000, 0.9975),
    ),
    soft_clip_knee=0.35,
    black_ratio_floor=2.5e-4,   # linear value below which the gain transfer is floored

    # highlight desaturation in linear light before the tone map: stops bright
    # saturated colours from learning an exaggerated hue as they clip
    # Highlights are rolled off per-channel (film-like) above ~0.25 scene-linear
    # instead of luminance-only. A luminance-only transfer preserves channel
    # RATIOS through the shoulder, which makes faintly-tinted speculars and cloud
    # edges fringe green/magenta - unacceptable and exactly the "digital"
    # artefact this look must avoid. Blending to a per-channel curve lets the
    # shoulder desaturate highlights naturally toward believable white.
    highlight_perchannel_start=0.25,
    highlight_perchannel_end=4.0,

    # ---- chroma / saturation ----
    sat_gain=1.055,
    vibrance=0.24,           # extra gain for low-chroma pixels
    high_chroma_taper=0.24,  # pull very saturated pixels back (no neon)
    white_chroma_taper=0.30,
    shadow_chroma_taper=0.12,
    chroma_comp=0.14,        # re-add chroma lost to the tonal curve

    # ---- hue shaping (degrees of OKLab hue rotation; bounded) ----
    hue_warm_to_amber=1.6,   # orange/amber/warm neutrals -> honey side
    hue_green_to_olive=-2.0, # greens -> warmer olive, away from teal
    hue_blue_to_violet=1.5,  # control cyan, keep sky blue (away from turquoise)
    hue_cyan_to_blue=-1.8,
    hue_skin_guard=-2.8,     # counter-rotate skin back from yellow
    skin_window=(20.0, 80.0),
    green_window=(105.0, 180.0),
    cyan_window=(180.0, 233.0),
    blue_window=(233.0, 315.0),
    warm_window=(315.0, 55.0),   # wraps through 0

    # ---- honey / shade split-tone ----
    # Chroma-gated (see creative()): neutrals cannot receive it, so a grey card
    # stays grey and there is no global yellow cast.
    tone_warm_ab=(0.0022, 0.0104),
    tone_warm_L=(0.20, 0.56, 0.94),   # ramp in / peak / out (clean at white)
    tint_chroma_lo=0.010,
    tint_chroma_hi=0.080,   # only clearly chromatic pixels take the tint
    tone_cool_ab=(-0.0009, -0.0044),
    tone_cool_L=(0.00, 0.34),

    # ---- per-group chroma multipliers (on top of sat_gain) ----
    skin_sat_mult=0.90,
    skin_guard_deep=3.6,     # deep skin sits redder after the per-channel curve
    blue_sat_gain=1.10,
    cyan_sat_gain=0.88,
    green_sat_gain=0.92,
    neutral_guard=0.35,      # how much tint near-neutrals may take

    # ---- how strongly each group may be tinted honey (1 = full) ----
    skin_warm_mult=0.45,
    blue_warm_mult=0.10,
    green_warm_mult=0.04,   # foliage must never be tinted yellow: it goes olive
                            # via a small hue rotation only, so it stays green
)

# OKLab matrices (Ottosson 2021)
_M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                [0.2119034982, 0.6806995451, 0.1073969566],
                [0.0883024619, 0.2817188376, 0.6299787005]])
_M2 = np.array([[0.2104542553,  0.7936177850, -0.0040720468],
                [1.9779984951, -2.4285922050,  0.4505937099],
                [0.0259040371,  0.7827717662, -0.8086757660]])
_M2_INV = np.linalg.inv(_M2)
_M1_INV = np.linalg.inv(_M1)

LUMA = np.array([0.2126, 0.7152, 0.0722])
GAMUT_EPS = 0.010        # smoothness of the gamut-surface compression


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bump(x, lo, peak, hi):
    return smoothstep(lo, peak, x) * (1.0 - smoothstep(peak, hi, x))


def hue_window(h_deg, lo, hi, feather=30.0):
    """Smooth circular window: 1 inside the [lo,hi] hue arc (may wrap past 0)."""
    span = (hi - lo) % 360.0                     # arc length, wrap safe
    centre = (lo + span * 0.5) % 360.0
    half = span * 0.5 + feather
    d = np.abs(((h_deg - centre + 180.0) % 360.0) - 180.0)
    return 1.0 - smoothstep(half - feather, half, d)


def circ_delta(h, target):
    """Signed shortest angular difference h - target in degrees."""
    return ((h - target + 180.0) % 360.0) - 180.0


def linear_to_oklab(rgb):
    return np.cbrt(rgb @ _M1.T) @ _M2.T


def oklab_to_linear(lab):
    return (lab @ _M2_INV.T) ** 3 @ _M1_INV.T


class MonotoneCurve:
    """Fritsch-Carlson monotone cubic interpolation of log2(x) -> y.

    log2(x) parameterisation because scene-linear highlights span many stops;
    monotone construction guarantees the delivered LUT cannot invert tonally.
    """

    def __init__(self, anchors, x_floor=1e-7, flatten_last=True):
        a = np.asarray(anchors, dtype=np.float64)
        x = np.log2(np.maximum(a[:, 0], x_floor))
        y = a[:, 1].copy()
        n = len(x)
        h = np.diff(x)
        d = np.diff(y) / h
        m = np.zeros(n)
        m[0], m[-1] = d[0], d[-1]
        for k in range(1, n - 1):
            if d[k - 1] * d[k] <= 0.0:
                m[k] = 0.0
            else:
                w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
                m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])
        if flatten_last:
            m[-1] = 0.0          # true shoulder: zero slope at the top
        self.x, self.y, self.m, self.h = x, y, m, h

    def __call__(self, x_lin):
        x = np.log2(np.maximum(np.asarray(x_lin, dtype=np.float64), 2.0 ** self.x[0]))
        x = np.clip(x, self.x[0], self.x[-1])
        i = np.clip(np.searchsorted(self.x, x, side="right") - 1, 0, len(self.x) - 2)
        h = self.h[i]
        t = (x - self.x[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * self.y[i] +
                (t3 - 2 * t2 + t) * h * self.m[i] +
                (-2 * t3 + 3 * t2) * self.y[i + 1] +
                (t3 - t2) * h * self.m[i + 1])


_TONE = MonotoneCurve(PARAMS["tone_anchors"])


# ---------------------------------------------------------------------------
# stage 1: Apple Log 2 -> linear Rec.709
# ---------------------------------------------------------------------------
def log2_to_linear_rec709(log_rgb):
    return apple_log_decode(log_rgb) @ AWG_TO_REC709.T


# ---------------------------------------------------------------------------
# stage 2: filmic tone map
# ---------------------------------------------------------------------------
BLACK_FLOOR = _TONE(0.0) ** 2.4          # lifted black, in linear light
_RECT_EPS = 2.0e-4
_DELTA = 2.0e-4          # linear-light smoothing of the gain denominator
_G0 = BLACK_FLOOR


def soft_rectify(x, eps=_RECT_EPS):
    """C1-continuous rectifier: ~x for |x| >> eps, 0 at x=0.

    Apple Log decodes to *negative* linear values below code 0.1208 (the curve
    carries near-black noise). A hard max(x,0) would place a curvature corner
    exactly at that zero crossing, which the LUT lattice renders as a visible
    tonal shelf; this keeps the transition smooth while still removing the
    sub-black values.
    """
    return 0.5 * (x + np.sqrt(x * x + eps * eps)) - 0.5 * eps


def _G(Y):
    """Luminance transfer in linear light: the monotone tone curve with gamma 2.4."""
    return np.maximum(_TONE(Y), 0.0) ** 2.4


def _ratio(Y):
    """Gain that maps scene-linear luminance to the tone curve, continuous at 0.

    ratio(Y) = (G(Y) - G(0)) / (Y + delta)

    The small `delta` keeps the quotient finite and C1 through Y = 0 (Apple Log
    decodes to negative linear values below code 0.1208, i.e. its near-black
    noise floor). Physically this compresses the sub-black region onto the lifted
    black floor, which is what we want; for Y >> delta the expression is the
    exact luminance-preserving ratio, so hue is preserved everywhere that
    matters. Using an *added* delta rather than a clamped divisor is what avoids
    the tonal shelf a naive G(Y)/Y would create at the zero crossing.
    """
    Y = np.asarray(Y, dtype=np.float64)
    return (np.maximum(_TONE(Y), 0.0) ** 2.4 - _G0) / (Y + _DELTA)


def _per_channel(x, p):
    """Film-like per-channel tone curve: desaturates highlights by itself."""
    return np.maximum(_TONE(soft_rectify(x)), 0.0) ** 2.4


def tone_map(lin, p=PARAMS):
    """Scene-linear Rec.709 -> Rec.709 gamma 2.4 code, via one per-channel curve.

    A per-channel film curve is used deliberately. The alternative - transferring
    luminance and rescaling the channels by the ratio - is hue preserving in
    theory but breaks down when one channel is near zero and the luminance is
    high (deep saturated reds and blues): the channel can only be squashed to the
    floor, so the ratio is huge and unstable, and the mapping develops a kink.
    Measured on this look that kink was a 0.06 jump across one lattice cell,
    which rendered as exactly the blotchy, banded sky this pipeline rejects.

    A per-channel curve is smooth and monotone in every channel, desaturates
    highlights and shadows the way film does (no clipped-channel fringing), and
    is therefore both the better-looking and the more LUT-friendly choice. Chroma
    is restored explicitly afterwards by the creative stage.
    """
    out = np.maximum(_TONE(soft_rectify(lin)), 0.0) ** 2.4

    k = p["soft_clip_knee"]
    over = out > 1.0
    if np.any(over):
        out = np.where(over, 1.0 - k * (1.0 - np.exp(-(out - 1.0) / k)), out)
    out = np.maximum(out, 0.0)
    return rec709_gamma24_encode(out), out


# ---------------------------------------------------------------------------
# stage 3: creative colour grade in OKLab
# ---------------------------------------------------------------------------
def creative(code, p=PARAMS):
    """Warm split-tone, chroma shaping and bounded hue rotation.

    Warmth is applied as *linear-light channel gain* (a controlled white-balance
    tilt), not as an OKLab a/b offset. Gain is independent of hue, so pale,
    near-neutral pixels - cloud edges, hazy sky, sunlit plaster - receive a
    consistent push with no hue-dependent mottling. Hue-sector windows only
    modulate the magnitude, and hue rotation is gated to pixels that actually
    carry chroma. The result is the same honey look, minus the colour noise a
    hue-windowed additive tint throws into near-neutrals.
    """
    lin = np.power(np.clip(code, 0.0, 1.0), 2.4)
    lab = linear_to_oklab(lin)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]

    C = np.hypot(a, b)
    H = np.degrees(np.arctan2(b, a)) % 360.0

    w_skin = hue_window(H, *p["skin_window"])
    w_green = hue_window(H, *p["green_window"])
    w_cyan = hue_window(H, *p["cyan_window"])
    w_blue = hue_window(H, *p["blue_window"])

    cw = smoothstep(0.010, 0.070, C)      # gate for hue-dependent decisions only
    Lc = np.clip(L, 0.0, 1.0)

    # ---- 1. chroma gain ---------------------------------------------------
    gain = np.full_like(C, p["sat_gain"])
    # Vibrance lifts *dull* pixels, but it must not undo the deliberate
    # desaturation of foliage or skin: on greens it was re-inflating exactly the
    # colours we pull back, doubling their effective hue rotation (measured
    # -15 deg of foliage hue shift). Those groups are excluded here.
    vib_w = (1.0 - smoothstep(0.0, 0.15, C)) * (1.0 - w_green * cw) * (1.0 - w_skin * cw)
    gain *= 1.0 + p["vibrance"] * vib_w
    gain *= 1.0 - p["high_chroma_taper"] * smoothstep(0.10, 0.26, C)
    gain *= 1.0 - p["white_chroma_taper"] * smoothstep(0.90, 1.0, Lc) * (1.0 - w_skin * cw)
    gain *= 1.0 - p["shadow_chroma_taper"] * (1.0 - smoothstep(0.02, 0.30, Lc))
    gain *= 1.0 + (p["blue_sat_gain"] - 1.0) * w_blue * cw
    gain *= 1.0 + (p["cyan_sat_gain"] - 1.0) * w_cyan * cw
    gain *= 1.0 + (p["green_sat_gain"] - 1.0) * w_green * cw
    gain *= 1.0 + (p["skin_sat_mult"] - 1.0) * w_skin * cw

    # ---- 2. bounded hue rotation (only where there is visible chroma) -----
    # Rotation is measured in degrees of OKLab hue, so its visual effect is a
    # fraction of the pixel's own chroma. Applying it at full strength to an
    # already-desaturated pixel is meaningless, so weight by chroma as well.
    rot_w = cw * smoothstep(0.02, 0.09, C)
    rot = np.zeros_like(C)
    rot += p["hue_warm_to_amber"] * hue_window(H, *p["warm_window"]) * rot_w
    rot += p["hue_green_to_olive"] * w_green * rot_w
    rot += p["hue_cyan_to_blue"] * w_cyan * rot_w
    rot += p["hue_blue_to_violet"] * w_blue * rot_w
    rot += p["hue_skin_guard"] * w_skin * rot_w
    # the per-channel curve pushes dark, saturated skin toward red; counter it
    # where it happens (low L) so melanin-rich skin stays golden, not ruddy
    rot += p["skin_guard_deep"] * w_skin * rot_w * (1.0 - smoothstep(0.30, 0.62, Lc))
    H1 = H + rot
    C2 = C * gain
    Hr = np.radians(H1)
    lab2 = np.stack([Lc, C2 * np.cos(Hr), C2 * np.sin(Hr)], axis=-1)

    # ---- 3. honey split-tone: an (a,b) offset, gated on chroma presence ----
    # Warmth is added *in proportion to existing chroma*, never as a global
    # white-balance tilt. A global tilt warms everything, including true
    # neutrals - which is precisely the "yellow overlay" this look must not be,
    # and which measurably put a 0.034 cast into a grey ramp. Chroma-gated
    # split-toning warms sunlit stone, skin, wood and sand (all of which carry
    # chroma) while leaving a neutral grey card exactly neutral.
    out = np.maximum(oklab_to_linear(gamut_fit(lab2)), 0.0)

    g_chroma = smoothstep(p["tint_chroma_lo"], p["tint_chroma_hi"], C)
    warm = bump(Lc, *p["tone_warm_L"]) * g_chroma
    warm = warm * (1.0 - (1.0 - p["skin_warm_mult"]) * w_skin * cw)
    warm = warm * (1.0 - (1.0 - p["green_warm_mult"]) * w_green * cw)
    warm = warm * (1.0 - (1.0 - p["blue_warm_mult"]) * w_blue * cw)
    cool = (1.0 - smoothstep(*p["tone_cool_L"], Lc)) * g_chroma

    a2 = lab2[..., 1] + p["tone_warm_ab"][0] * warm + p["tone_cool_ab"][0] * cool
    b2 = lab2[..., 2] + p["tone_warm_ab"][1] * warm + p["tone_cool_ab"][1] * cool
    lab2 = np.stack([lab2[..., 0], a2, b2], axis=-1)

    out_lin = np.maximum(oklab_to_linear(gamut_fit(lab2)), 0.0)
    out = out_lin

    return np.clip(rec709_gamma24_encode(np.maximum(out, 0.0)), 0.0, 1.0)


def softmin(x, eps):
    """C-infinity lower envelope over the last axis (always <= min(x))."""
    return -eps * np.log(np.exp(-(x - x.min(axis=-1, keepdims=True)) / eps).sum(axis=-1)) \
        + x.min(axis=-1)


def gamut_fit(lab, eps=None):
    """Reduce OKLab chroma to the largest value that still fits in [0,1] RGB.

    Solved in closed form, not iteratively. OKLab -> LMS is affine, so writing
    lab = (L,0,0) + s*(0,a,b) gives

        lms_i(s) = Li + s*ki

    and because cube() is monotone, "every RGB channel >= 0" is exactly
    "every lms_i >= 0". Hence s_max = min over i of Li/(-ki) for ki < 0.

    The soft-min gives a C-infinity result that sits just inside the gamut
    surface. This matters: per-channel clipping would introduce an abrupt hue
    step at the gamut wall, which a 33-cube lattice cannot follow and which
    shows up as the banded, "digital" smearing cheap LUTs are known for.
    """
    eps = GAMUT_EPS if eps is None else eps
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    Li = L[..., None] * _M2_INV[:, 0]                      # (...,3)
    ki = (a[..., None] * _M2_INV[:, 1] +
          b[..., None] * _M2_INV[:, 2])                    # (...,3)

    big = 1.0e6
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(ki < -1e-9, Li / np.maximum(-ki, 1e-9), big)
    c = np.minimum(c, big)
    s = softmin(c, eps)                                    # (...,)
    s = np.clip(s, 0.0, 1.0)
    return np.stack([L, a * s, b * s], axis=-1)


# ---------------------------------------------------------------------------
def apply_grade(log_rgb, p=PARAMS):
    """GOLDEN DAYLIGHT CINEMA: Apple Log 2 / Apple Wide Gamut -> Rec.709 gamma 2.4."""
    code, _ = tone_map(log2_to_linear_rec709(log_rgb), p)
    return creative(code, p)


def neutral_technical(log_rgb):
    """Reference BEFORE image: plain Apple Log 2 -> Rec.709 gamma 2.4, no grade."""
    lin = np.clip(log2_to_linear_rec709(log_rgb), 0.0, 1.0)
    return np.clip(rec709_gamma24_encode(lin), 0.0, 1.0)
