"""
applelog2.py — Apple Log 2 / Apple Wide Gamut colour-science core.

GOLDEN DAYLIGHT CINEMA — standalone Apple Log 2 -> Rec.709 (gamma 2.4) LUT project.

SOURCES (see VALIDATION_REPORT.txt for the full citation list)
--------------------------------------------------------------
Transfer function (shared by Apple Log and Apple Log 2):
  Apple Inc., "Apple Log Profile White Paper", September 2023, and
  Apple Inc., "Apple Log 2 White Paper", September 2025.
  Constants reproduced in colour-science
  (colour/models/rgb/transfer_functions/apple_log_profile.py), which cites the
  Apple white paper and the AMPAS ACES IDT IDT.Apple.AppleLog_BT2020.ctl.

    R_0   = -0.05641088
    R_t   =  0.01
    sigma = 47.28711236
    beta  =  0.00964052
    gamma =  0.08550479
    delta =  0.69336945
    P_t   = sigma * (R_t - R_0)^2

Apple Wide Gamut primaries (Apple Log 2 only):
    R  (0.725,  0.301)
    G  (0.221,  0.814)
    B  (0.068, -0.076)
    W  D65 (0.3127, 0.3290)
  Cross-checked against four independent transcriptions of Apple's Apple Log 2
  white paper (OpenColorIO PR #2343 AppleCameras.cpp, hdr-toys clip.glsl,
  ireelz.com, cined.com) — all agree exactly.

INDEPENDENT VERIFICATION ANCHOR
-------------------------------
OpenColorIO-Config-ACES PR #179 / the Blender studio config publish the
Apple Wide Gamut -> ACES2065-1 (AP0) matrix with Bradford adaptation:

    [ 0.694961049318096 ,  0.241405268785364 ,  0.06363368189654   ]
    [ 0.0473627464149325,  1.00429592505428  , -0.0516586714692158 ]
    [-0.021989789359883 , -0.0289891049714743,  1.05097889433136   ]

verify_colorscience.py re-derives that matrix from the published chromaticities
and compares. If the derivation matches, our gamut maths is correct.

NOTE ON INPUT RANGE
-------------------
The Apple Log white paper defines the encoded pixel value P on the normalised
floating-point interval [0, 1] (10-bit FULL range: 0 -> 0.0, 1023 -> 1.0).
This module, and the delivered .cube, assume the LUT input is that normalised
full-range P. This is the same assumption Apple's own camera LUTs make.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# 1. Apple Log transfer function (identical in Apple Log and Apple Log 2)
# ---------------------------------------------------------------------------

APPLE_LOG = dict(
    R_0=-0.05641088,
    R_t=0.01,
    sigma=47.28711236,
    beta=0.00964052,
    gamma=0.08550479,
    delta=0.69336945,
)
APPLE_LOG["P_t"] = APPLE_LOG["sigma"] * (APPLE_LOG["R_t"] - APPLE_LOG["R_0"]) ** 2


def apple_log_encode(R):
    """Linear scene reflection R  ->  Apple Log encoded signal P in [0, 1].

    R = 0.18 is an 18 % reflectance reference grey chart.
    """
    R = np.asarray(R, dtype=np.float64)
    c = APPLE_LOG
    log_branch = c["gamma"] * np.log2(np.maximum(R + c["beta"], 1e-12)) + c["delta"]
    par_branch = c["sigma"] * (R - c["R_0"]) ** 2
    return np.select(
        [R >= c["R_t"], (R >= c["R_0"]) & (R < c["R_t"])],
        [log_branch, par_branch],
        default=0.0,
    )


def apple_log_decode(P):
    """Apple Log encoded signal P in [0, 1]  ->  linear scene reflection R."""
    P = np.asarray(P, dtype=np.float64)
    c = APPLE_LOG
    log_branch = 2.0 ** ((P - c["delta"]) / c["gamma"]) - c["beta"]
    par_branch = np.sqrt(np.maximum(P, 0.0) / c["sigma"]) + c["R_0"]
    return np.select(
        [P >= c["P_t"], (P >= 0.0) & (P < c["P_t"])],
        [log_branch, par_branch],
        default=c["R_0"],
    )


# ---------------------------------------------------------------------------
# 2. Chromaticities and RGB <-> XYZ matrices
# ---------------------------------------------------------------------------

D65 = (0.3127, 0.3290)
D60_ACES = (0.32168, 0.33767)

APPLE_WIDE_GAMUT_PRIMARIES = ((0.725, 0.301), (0.221, 0.814), (0.068, -0.076))
REC709_PRIMARIES = ((0.640, 0.330), (0.300, 0.600), (0.150, 0.060))
REC2020_PRIMARIES = ((0.708, 0.292), (0.170, 0.797), (0.131, 0.046))
AP0_PRIMARIES = ((0.7347, 0.2653), (0.0000, 1.0000), (0.0001, -0.0770))

# Bradford cone response matrix (Lam 1985) — the CAT used by OpenColorIO and
# OpenColorIO-Config-ACES for the Apple Wide Gamut -> AP0 matrix.
BRADFORD = np.array(
    [
        [0.8951, 0.2664, -0.1614],
        [-0.7502, 1.7135, 0.0367],
        [0.0389, -0.0685, 1.0296],
    ]
)


def xy_to_XYZ(xy, Y=1.0):
    x, y = xy
    return np.array([Y * x / y, Y, Y * (1.0 - x - y) / y])


def rgb_to_xyz_matrix(primaries, white_xy):
    """Build the 3x3 RGB -> CIE XYZ matrix from chromaticities (Y of white = 1)."""
    (rx, ry), (gx, gy), (bx, by) = primaries
    M = np.array(
        [
            [rx, gx, bx],
            [ry, gy, by],
            [1.0 - rx - ry, 1.0 - gx - gy, 1.0 - bx - by],
        ]
    )
    W = xy_to_XYZ(white_xy, 1.0)
    gains = np.linalg.solve(M, W)
    return M * gains[np.newaxis, :]


def bradford_adaptation(src_white_xy, dst_white_xy):
    """von Kries style chromatic adaptation matrix in XYZ using Bradford cones."""
    src = xy_to_XYZ(src_white_xy, 1.0)
    dst = xy_to_XYZ(dst_white_xy, 1.0)
    src_lms = BRADFORD @ src
    dst_lms = BRADFORD @ dst
    scale = np.diag(dst_lms / src_lms)
    return np.linalg.inv(BRADFORD) @ scale @ BRADFORD


# Working matrices -----------------------------------------------------------

AWG_TO_XYZ_D65 = rgb_to_xyz_matrix(APPLE_WIDE_GAMUT_PRIMARIES, D65)
XYZ_D65_TO_AWG = np.linalg.inv(AWG_TO_XYZ_D65)

REC709_TO_XYZ_D65 = rgb_to_xyz_matrix(REC709_PRIMARIES, D65)
XYZ_D65_TO_REC709 = np.linalg.inv(REC709_TO_XYZ_D65)

REC2020_TO_XYZ_D65 = rgb_to_xyz_matrix(REC2020_PRIMARIES, D65)
XYZ_D65_TO_REC2020 = np.linalg.inv(REC2020_TO_XYZ_D65)

AP0_TO_XYZ_D60 = rgb_to_xyz_matrix(AP0_PRIMARIES, D60_ACES)
XYZ_D60_TO_AP0 = np.linalg.inv(AP0_TO_XYZ_D60)

# Both Apple Wide Gamut and Rec.709 are D65 -> NO chromatic adaptation required.
AWG_TO_REC709 = XYZ_D65_TO_REC709 @ AWG_TO_XYZ_D65
AWG_TO_REC2020 = XYZ_D65_TO_REC2020 @ AWG_TO_XYZ_D65
REC709_TO_AWG = np.linalg.inv(AWG_TO_REC709)

# Verification target: Apple Wide Gamut -> ACES2065-1 with Bradford adaptation.
AWG_TO_AP0_BRADFORD = (
    XYZ_D60_TO_AP0 @ bradford_adaptation(D65, D60_ACES) @ AWG_TO_XYZ_D65
)

# Published reference (OpenColorIO-Config-ACES PR #179 / Blender studio config).
AWG_TO_AP0_REFERENCE = np.array(
    [
        [0.694961049318096, 0.241405268785364, 0.06363368189654],
        [0.0473627464149325, 1.00429592505428, -0.0516586714692158],
        [-0.021989789359883, -0.0289891049714743, 1.05097889433136],
    ]
)

# Rec.709 luminance weights (BT.709 Y'
REC709_LUMA = np.array([0.2126, 0.7152, 0.0722])


def apply_matrix(rgb, M):
    """Apply a 3x3 matrix to an (..., 3) array."""
    return np.einsum("ij,...j->...i", M, rgb)


# ---------------------------------------------------------------------------
# 3. Rec.709 / gamma 2.4 display encoding
# ---------------------------------------------------------------------------


def gamma24_encode(L):
    """Display-linear [0,1] -> gamma 2.4 encoded code value.

    This is the inverse of the pure 2.4 power EOTF (BT.1886 with Lb = 0,
    Lw = 1), which is the project's specified output transfer function.
    """
    L = np.clip(np.asarray(L, dtype=np.float64), 0.0, 1.0)
    return L ** (1.0 / 2.4)


def gamma24_decode(V):
    """Gamma 2.4 encoded code value -> display-linear [0,1]."""
    V = np.clip(np.asarray(V, dtype=np.float64), 0.0, 1.0)
    return V**2.4


def srgb_eotf(V):
    """sRGB (IEC 61966-2-1) code value -> display-linear. Used for sources."""
    V = np.asarray(V, dtype=np.float64)
    return np.where(V <= 0.04045, V / 12.92, ((np.maximum(V, 0.0) + 0.055) / 1.055) ** 2.4)


def srgb_inverse_eotf(L):
    """Display-linear -> sRGB code value."""
    L = np.clip(np.asarray(L, dtype=np.float64), 0.0, 1.0)
    return np.where(L <= 0.0031308, L * 12.92, 1.055 * L ** (1 / 2.4) - 0.055)


# ---------------------------------------------------------------------------
# 4. ACES-style reference gamut compression
# ---------------------------------------------------------------------------


def _compress_distance(dist, limit, threshold, power):
    """Power(p) compression function from the ACES 1.3 Reference Gamut Compress.

    Maps distance `limit` exactly to 1.0 and asymptotes above it; identity
    below `threshold`.
    """
    dist = np.asarray(dist, dtype=np.float64)
    denom = ((1.0 - threshold) / (limit - threshold)) ** (-power) - 1.0
    scale = (limit - threshold) / (denom ** (1.0 / power))
    nd = np.maximum((dist - threshold) / scale, 0.0)
    compressed = threshold + scale * nd / ((1.0 + nd**power) ** (1.0 / power))
    return np.where(dist < threshold, dist, compressed)


def gamut_compress(rgb, limits=(1.70, 1.30, 1.25), threshold=(0.80, 0.80, 0.80), power=1.2):
    """Pull out-of-gamut (negative) channels back inside the gamut.

    Operates on the distance of each channel from the achromatic axis, so hue
    and luminance are largely preserved. Applied after the Apple Wide Gamut ->
    Rec.709 matrix, where very saturated captures produce negative channels.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    ach = np.max(rgb, axis=-1, keepdims=True)
    ach_safe = np.where(np.abs(ach) < 1e-9, 1e-9, ach)
    dist = np.where(ach == 0.0, 0.0, (ach - rgb) / np.abs(ach_safe))

    out = np.empty_like(dist)
    for i in range(3):
        out[..., i] = _compress_distance(dist[..., i], limits[i], threshold[i], power)
    return ach - out * np.abs(ach_safe)


# ---------------------------------------------------------------------------
# 5. Parametric filmic sigmoid (log2 stops -> display code value)
# ---------------------------------------------------------------------------


def _sigmoid_scale(delta_x, delta_y, slope, power):
    """Scale so the asymptotic power curve passes exactly through (dx, dy)."""
    md = slope * delta_x
    if md <= delta_y:
        raise ValueError(
            f"slope*dx ({md:.4f}) must exceed dy ({delta_y:.4f}) for a valid sigmoid"
        )
    return md / (((md / delta_y) ** power - 1.0) ** (1.0 / power))


def _unit_curve(v, power):
    """f(v) = v / (1 + v^p)^(1/p); f(0)=0, f'(0)=1, f(inf)=1."""
    return v / ((1.0 + v**power) ** (1.0 / power))


class FilmicSigmoid:
    """Two-sided asymptotic power sigmoid mapping log2 stops to display code.

    x : log2(L / 0.18)  — stops relative to an 18 % grey card
    y : display code value in the output (gamma 2.4) encoding

    Continuous and C1 at the pivot (both halves have gradient `slope` there),
    strictly monotonic, and exactly reaches y_min at x_min and y_max at x_max.
    """

    def __init__(
        self,
        x_pivot=0.0,
        y_pivot=0.405,
        slope=0.250,
        x_max=6.30,
        y_max=1.0,
        power_shoulder=1.70,
        x_min=-10.50,
        y_min=0.0,
        power_toe=1.15,
    ):
        self.x_pivot, self.y_pivot, self.slope = x_pivot, y_pivot, slope
        self.x_max, self.y_max, self.power_shoulder = x_max, y_max, power_shoulder
        self.x_min, self.y_min, self.power_toe = x_min, y_min, power_toe

        self.scale_shoulder = _sigmoid_scale(
            x_max - x_pivot, y_max - y_pivot, slope, power_shoulder
        )
        self.scale_toe = _sigmoid_scale(
            x_pivot - x_min, y_pivot - y_min, slope, power_toe
        )

    def __call__(self, x):
        x = np.asarray(x, dtype=np.float64)
        dx = x - self.x_pivot

        up = self.y_pivot + self.scale_shoulder * _unit_curve(
            np.maximum(self.slope * dx, 0.0) / self.scale_shoulder, self.power_shoulder
        )
        dn = self.y_pivot - self.scale_toe * _unit_curve(
            np.maximum(-self.slope * dx, 0.0) / self.scale_toe, self.power_toe
        )
        y = np.where(dx >= 0.0, up, dn)
        return np.clip(y, 0.0, 1.0)

    def from_linear(self, L, eps=1e-10):
        """Scene-linear (0.18 = grey) -> display code value."""
        L = np.asarray(L, dtype=np.float64)
        x = np.log2(np.maximum(L, eps) / 0.18)
        y = self(x)
        return np.where(L <= eps, self.y_min, y)

    def describe(self):
        pts = {
            "0.1% refl  (-7.5 st)": 0.0018,
            "1% refl    (-4.2 st)": 0.01,
            "2.25%      (-3.0 st)": 0.0225,
            "4.5%       (-2.0 st)": 0.045,
            "9%         (-1.0 st)": 0.09,
            "18% GREY   ( 0.0 st)": 0.18,
            "36%        (+1.0 st)": 0.36,
            "90% WHITE  (+2.3 st)": 0.90,
            "180%       (+3.3 st)": 1.80,
            "360%       (+4.3 st)": 3.60,
            "1200% clip (+6.1 st)": 12.0,
        }
        lines = []
        for k, v in pts.items():
            code = float(self.from_linear(v))
            lines.append(f"    {k}: linear {v:9.5f} -> code {code:7.5f}  (disp-lin {code**2.4:7.5f})")
        return "\n".join(lines)
