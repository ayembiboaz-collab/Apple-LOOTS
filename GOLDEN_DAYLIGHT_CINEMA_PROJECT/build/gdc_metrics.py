"""
gdc_metrics.py -- measurement helpers used by the validation and the build.

All measurements are made on Rec.709 gamma-2.4 *code values* (what the LUT
actually produces), converted back to linear light before any colour difference
is computed.  Regions of interest (ROIs) are fractional (x0, x1, y0, y1) boxes,
recorded here so that every number in the report is reproducible.
"""

from __future__ import annotations

import numpy as np
import colour

import gdc_colour as C

D65 = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]

#: luminance weights of Rec.709
LUMA709 = np.array([0.2126, 0.7152, 0.0722])


# --------------------------------------------------------------------------
# conversions
# --------------------------------------------------------------------------

def codes_to_xyz(codes: np.ndarray) -> np.ndarray:
    return np.maximum(C.gamma24_decode(codes), 0.0) @ C.REC709_TO_XYZ.T


def codes_to_oklch(codes: np.ndarray) -> np.ndarray:
    return C.oklab_to_oklch(C.xyz_to_oklab(codes_to_xyz(codes)))


def codes_to_lab(codes: np.ndarray) -> np.ndarray:
    return colour.XYZ_to_Lab(codes_to_xyz(codes), illuminant=D65)


def codes_to_ictcp(codes: np.ndarray) -> np.ndarray:
    return colour.XYZ_to_ICtCp(codes_to_xyz(codes) * 100.0)


def de2000(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return colour.difference.delta_E_CIE2000(codes_to_lab(a), codes_to_lab(b))


def de_itp(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return colour.difference.delta_E_ITP(codes_to_ictcp(a), codes_to_ictcp(b))


def luma(codes: np.ndarray) -> np.ndarray:
    return codes_to_xyz(codes)[..., 1]


def ycbcr(codes: np.ndarray) -> np.ndarray:
    """BT.709 non-constant-luminance YCbCr in the 0..1 code domain (as used by
    a vectorscope).  Cb, Cr are returned around 0 by subtracting 0.5."""
    r, g, b = codes[..., 0], codes[..., 1], codes[..., 2]
    y = LUMA709[0] * r + LUMA709[1] * g + LUMA709[2] * b
    cb = (b - y) / 1.8556
    cr = (r - y) / 1.5748
    return np.stack([y, cb, cr], axis=-1)


def skin_line_angle(codes: np.ndarray) -> np.ndarray:
    """Vectorscope hue angle in degrees (0 = +Cb axis, 90 = +Cr axis).

    The classic "skin line" on a vectorscope sits around 110-130 degrees for a
    BT.709/Rec.709 signal; see VALIDATION_REPORT.txt for the reference used.
    """
    ycc = ycbcr(codes)
    return np.degrees(np.arctan2(ycc[..., 2], ycc[..., 1])) % 360.0


# --------------------------------------------------------------------------
# ROIs (fractional x0, x1, y0, y1) -- chosen once, used everywhere
# --------------------------------------------------------------------------

ROIS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "midday_city": {
        "sky": (0.02, 0.12, 0.02, 0.10),
        "sunlit_facade": (0.45, 0.55, 0.30, 0.40),
        "shade_street": (0.55, 0.75, 0.86, 0.96),
    },
    "midday_portrait": {
        "skin_lit": (0.17, 0.27, 0.38, 0.50),
        "skin_shadow": (0.30, 0.42, 0.30, 0.45),
        "red_wall": (0.70, 0.85, 0.30, 0.50),
    },
    "mediterranean_street": {
        "white_wall_sun": (0.05, 0.20, 0.30, 0.50),
        "shade": (0.30, 0.45, 0.75, 0.90),
        "blue_paint": (0.44, 0.56, 0.14, 0.20),
    },
    "beach_daylight": {
        "sky": (0.10, 0.30, 0.02, 0.09),
        "sea": (0.20, 0.45, 0.55, 0.70),
        "sand": (0.55, 0.75, 0.82, 0.94),
    },
    "landscape_green": {
        "sky": (0.30, 0.45, 0.02, 0.08),
        "grass": (0.30, 0.50, 0.65, 0.80),
        "conifers": (0.55, 0.70, 0.30, 0.40),
        "rock": (0.85, 0.95, 0.20, 0.35),
    },
    "golden_hour": {
        "sun": (0.35, 0.55, 0.20, 0.35),
        "shade": (0.10, 0.25, 0.70, 0.85),
    },
    "modern_architecture": {
        "concrete": (0.30, 0.45, 0.30, 0.45),
        "window": (0.55, 0.70, 0.55, 0.70),
    },
    "travel_people": {
        "stone_sun": (0.72, 0.85, 0.35, 0.50),
        "sky": (0.35, 0.45, 0.02, 0.10),
        "shade": (0.05, 0.20, 0.55, 0.70),
    },
}


def crop(a: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    h, w = a.shape[:2]
    x0, x1, y0, y1 = box
    return a[int(y0 * h):max(int(y1 * h), int(y0 * h) + 1),
             int(x0 * w):max(int(x1 * w), int(x0 * w) + 1)]


def region_flat(a: np.ndarray, box) -> np.ndarray:
    return crop(a, box).reshape(-1, a.shape[-1])


# --------------------------------------------------------------------------
# summary stats
# --------------------------------------------------------------------------

def chroma_weighted_hue(lch: np.ndarray) -> float:
    """Chromatically weighted circular mean hue (degrees)."""
    w = lch[:, 1]
    hr = np.radians(lch[:, 2])
    if w.sum() <= 0:
        return float("nan")
    return float(np.degrees(np.arctan2(np.sum(w * np.sin(hr)), np.sum(w * np.cos(hr)))) % 360.0)


def region_summary(codes: np.ndarray, box) -> dict:
    px = region_flat(codes, box)
    lch = codes_to_oklch(px)
    lab = codes_to_lab(px)
    return {
        "L": float(np.median(lch[:, 0])),
        "C": float(np.median(lch[:, 1])),
        "h": chroma_weighted_hue(lch),
        "code_mean": float(px.mean()),
        "Y": float(np.median(luma(px))),
        "skin_angle": float(np.median(skin_line_angle(px))),
        "ab": (float(np.median(lab[:, 1])), float(np.median(lab[:, 2]))),
    }


def image_summary(codes: np.ndarray) -> dict:
    lum = luma(codes)
    return {
        "mean_code": float(codes.mean()),
        "median_code": float(np.median(codes)),
        "p01": float(np.percentile(codes, 1)),
        "p50": float(np.percentile(codes, 50)),
        "p99": float(np.percentile(codes, 99)),
        "mean_Y": float(lum.mean()),
        "clip_white_pct": float(np.mean(codes >= 1.0 - 1e-9) * 100.0),
        "clip_black_pct": float(np.mean(codes <= 1e-9) * 100.0),
        "clip_channels_high_pct": float(np.mean(codes >= 1.0 - 1e-9) * 100.0),
        "below_zero_pct": 0.0,
        "mean_chroma": float(codes_to_oklch(codes.reshape(-1, 3))[:, 1].mean()),
    }
