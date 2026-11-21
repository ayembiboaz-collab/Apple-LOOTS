"""
apple_log2.py -- Apple Log 2 / Apple Wide Gamut colour science reference module.

Implements, in pure NumPy float64:
  * Apple Log / Apple Log 2 transfer function (encode + decode)
  * Apple Wide Gamut primaries -> XYZ (D65) matrix derived from published chromaticities
  * Apple Wide Gamut -> Rec.709 (linear) matrix
  * Rec.709 / BT.1886 gamma 2.4 encoding
  * sRGB encode/decode helpers used only by the source-plate simulator

SOURCES
  [S1] Apple Inc., "Apple Log Profile White Paper" (September 2023) - curve constants,
       BT.2020 primaries for first-generation Apple Log.
  [S2] Apple Inc., "Apple Log 2 White Paper" (September 2025) - Apple Wide Gamut
       primaries: R(0.725, 0.301) G(0.221, 0.814) B(0.068, -0.076), D65 white.
  [S3] Apple developer documentation, AVCaptureColorSpace.appleLog2 /
       "Apple Gamut" primaries + Apple-defined log curve.
  [S4] AcademySoftwareFoundation/OpenColorIO-Config-ACES issue #163,
       "Add Apple Log 2 color space" - independent published Apple Wide Gamut -> AP0
       matrix used here as a cross-check (matches our derivation to ~1e-15).
"""
import numpy as np

# ---------------------------------------------------------------- Apple Log curve
# [S1] Apple Log Profile White Paper, section "Apple Log transfer function".
R0    = -0.05641088
RT    = 0.01
C     = 47.28711236
BETA  = 0.00964052
GAMMA = 0.08550479
DELTA = 0.69336945
PT    = C * (RT - R0) ** 2          # 0.20855531595464202 (linear/log transition point)


def apple_log_decode(x):
    """Apple Log / Apple Log 2 code value (0..1) -> scene-linear (relative, 1.0 = white)."""
    x = np.asarray(x, dtype=np.float64)
    hi = np.power(2.0, (x - DELTA) / GAMMA) - BETA
    lo = np.sqrt(np.maximum(x, 0.0) / C) + R0
    return np.where(x >= PT, hi, np.where(x >= 0.0, lo, R0))


def apple_log_encode(y):
    """Scene-linear -> Apple Log code value."""
    y = np.asarray(y, dtype=np.float64)
    return GAMMA * np.log2(np.maximum(y + BETA, 1e-12)) + DELTA


# ---------------------------------------------------------------- primaries helpers
def xy_to_XYZ(xy):
    x, y = xy
    return np.array([x / y, 1.0, (1.0 - x - y) / y])


def primaries_to_XYZ(primaries, white):
    """RGB->XYZ matrix from chromaticities + white point (standard derivation)."""
    M = np.array([xy_to_XYZ(primaries[k]) for k in ("R", "G", "B")]).T
    S = np.linalg.solve(M, xy_to_XYZ(white))
    return M * S


APPLE_WIDE_GAMUT = {"R": (0.725, 0.301), "G": (0.221, 0.814), "B": (0.068, -0.076)}  # [S2]
REC709 = {"R": (0.64, 0.33), "G": (0.30, 0.60), "B": (0.15, 0.06)}
D65 = (0.3127, 0.3290)
AP0 = {"R": (0.7347, 0.2653), "G": (0.0, 1.0), "B": (0.0001, -0.0770)}
D60 = (0.32168, 0.33767)

# Both Apple Wide Gamut and Rec.709 are D65, so NO chromatic adaptation is required
# for the primary conversion. (Chromatic adaptation only matters for the ACES
# cross-check below, where AP0 is D60; Bradford is used there because the Log 2
# white paper leaves the adaptation unspecified - same choice as OCIO [S4].)
M_AWG_TO_XYZ = primaries_to_XYZ(APPLE_WIDE_GAMUT, D65)
M_709_TO_XYZ = primaries_to_XYZ(REC709, D65)
M_AP0_TO_XYZ = primaries_to_XYZ(AP0, D60)

AWG_TO_REC709 = np.linalg.inv(M_709_TO_XYZ) @ M_AWG_TO_XYZ     # linear AWG -> linear 709
REC709_TO_AWG = np.linalg.inv(AWG_TO_REC709)


def _bradford():
    return np.array([[0.8951, 0.2664, -0.1614],
                     [-0.7502, 1.7135, 0.0367],
                     [0.0389, -0.0685, 1.0296]])


def chromatic_adaptation(src_white, dst_white, method="bradford"):
    B = _bradford()
    s, d = B @ xy_to_XYZ(src_white), B @ xy_to_XYZ(dst_white)
    return np.linalg.inv(B) @ np.diag(d / s) @ B


# Apple Wide Gamut -> ACES AP0, used only to validate our primaries derivation
# against the independent OpenColorIO value published in [S4].
AWG_TO_AP0 = np.linalg.inv(M_AP0_TO_XYZ) @ chromatic_adaptation(D65, D60) @ M_AWG_TO_XYZ

OCIO_REFERENCE_AWG_TO_AP0 = np.array([
    [0.694961049318096,   0.241405268785364,   0.06363368189654],
    [0.0473627464149325,  1.00429592505428,   -0.0516586714692158],
    [-0.021989789359883, -0.0289891049714743,  1.05097889433136]])


# ---------------------------------------------------------------- display encodings
def rec709_gamma24_encode(v):
    """Linear -> Rec.709 SDR with gamma 2.4 (BT.1886 pure power, no OETF toe).
    This is what 'Rec.709 gamma 2.4' means for a LUT deliverable consumed by
    Resolve / FCP / Blackmagic Camera monitor-LUT slots."""
    v = np.asarray(v, dtype=np.float64)
    return np.sign(v) * np.power(np.abs(v), 1.0 / 2.4)


def rec709_gamma24_decode(v):
    v = np.asarray(v, dtype=np.float64)
    return np.sign(v) * np.power(np.abs(v), 2.4)


def srgb_decode(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))


def srgb_encode(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(np.maximum(v, 0.0), 1 / 2.4) - 0.055)


def reference_report():
    """Self-check of the technical core. Returns dict of measured values."""
    e18 = float(apple_log_encode(0.18))
    e90 = float(apple_log_encode(0.90))
    e12 = float(apple_log_encode(12.0))
    return {
        "PT": PT,
        "apple_log_encode(0.18)": e18,
        "apple_log_encode(0.18)_10bit_full_range": e18 * 1023.0,
        "apple_log_encode(0.90)": e90,
        "apple_log_encode(12.0)": e12,
        "decode_roundtrip_18pct_error": abs(float(apple_log_decode(e18)) - 0.18),
        "AWG_TO_REC709": AWG_TO_REC709,
        "OCIO_AWG_TO_AP0_max_abs_diff": float(np.abs(AWG_TO_AP0 - OCIO_REFERENCE_AWG_TO_AP0).max()),
        "AWG_white_maps_to": AWG_TO_REC709 @ np.ones(3),
    }


if __name__ == "__main__":
    r = reference_report()
    for k, v in r.items():
        print(f"{k}: {v}")
