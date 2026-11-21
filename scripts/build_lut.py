#!/usr/bin/env python3
"""
GOLDEN DAYLIGHT CINEMA — 33x33x33 3D LUT Builder & Scene Renderer
Input:  Apple Log 2 (Apple Log transfer function + Apple Wide Gamut primaries)
Output: Rec.709 SDR, Gamma 2.4
"""

import os
import math
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# 1. Colorimetry: Primaries & Matrices (D65 White Point)
# ---------------------------------------------------------------------------

def primaries_to_xyz_matrix(rx, ry, gx, gy, bx, by, wx=0.3127, wy=0.3290):
    """Derive 3x3 RGB -> CIE XYZ matrix from CIE xy primaries and white point."""
    def xy_to_XYZ(x, y):
        return np.array([x / y, 1.0, (1.0 - x - y) / y], dtype=np.float64)

    Xr, Yr, Zr = xy_to_XYZ(rx, ry)
    Xg, Yg, Zg = xy_to_XYZ(gx, gy)
    Xb, Yb, Zb = xy_to_XYZ(bx, by)
    W = xy_to_XYZ(wx, wy)

    M_prim = np.array([
        [Xr, Xg, Xb],
        [Yr, Yg, Yb],
        [Zr, Zg, Zb],
    ], dtype=np.float64)

    S = np.linalg.solve(M_prim, W)
    return M_prim * S[np.newaxis, :]


# Apple Wide Gamut (Apple Log 2 White Paper, Sept 2025; OpenColorIO PR #2343)
M_AWG_TO_XYZ = primaries_to_xyz_matrix(
    0.725, 0.301,
    0.221, 0.814,
    0.068, -0.076,
    0.3127, 0.3290,
)

# ITU-R BT.709 / sRGB primaries (D65)
M_709_TO_XYZ = primaries_to_xyz_matrix(
    0.640, 0.330,
    0.300, 0.600,
    0.150, 0.060,
    0.3127, 0.3290,
)
M_XYZ_TO_709 = np.linalg.inv(M_709_TO_XYZ)
M_XYZ_TO_AWG = np.linalg.inv(M_AWG_TO_XYZ)

M_AWG_TO_709 = M_XYZ_TO_709 @ M_AWG_TO_XYZ
M_709_TO_AWG = M_XYZ_TO_AWG @ M_709_TO_XYZ


# ---------------------------------------------------------------------------
# 2. Apple Log / Apple Log 2 Transfer Function
# ---------------------------------------------------------------------------
R_0 = -0.05641088
R_T = 0.01
C_CONST = 47.28711236
BETA = 0.00964052
GAMMA = 0.08550479
DELTA = 0.69336945
P_T = C_CONST * ((R_T - R_0) ** 2)


def apple_log_to_linear(v: np.ndarray) -> np.ndarray:
    """Decode Apple Log / Apple Log 2 code values [0, 1] to scene-linear."""
    v = np.asarray(v, dtype=np.float64)
    out = np.empty_like(v)

    mask_high = v >= P_T
    mask_mid = (v >= 0.0) & (v < P_T)
    mask_low = v < 0.0

    out[mask_high] = np.power(2.0, (v[mask_high] - DELTA) / GAMMA) - BETA
    out[mask_mid] = np.sqrt(np.maximum(v[mask_mid], 0.0) / C_CONST) + R_0
    out[mask_low] = R_0
    return out


def linear_to_apple_log(l: np.ndarray) -> np.ndarray:
    """Encode scene-linear reflectance to Apple Log / Apple Log 2 [0, 1]."""
    l = np.asarray(l, dtype=np.float64)
    out = np.empty_like(l)

    mask_high = l >= R_T
    mask_mid = (l >= R_0) & (l < R_T)
    mask_low = l < R_0

    out[mask_high] = GAMMA * np.log2(np.maximum(l[mask_high] + BETA, 1e-12)) + DELTA
    out[mask_mid] = C_CONST * ((l[mask_mid] - R_0) ** 2)
    out[mask_low] = 0.0
    return np.clip(out, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 3. Creative Grade: GOLDEN DAYLIGHT CINEMA
# ---------------------------------------------------------------------------

def rgb_to_hsl_luma_hue(rgb: np.ndarray):
    """Compute Rec.709 luminance, simple saturation, and hue angle [0, 360)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min

    hue = np.zeros_like(delta)
    mask = delta > 1e-6

    r_eq = mask & (c_max == r)
    g_eq = mask & (c_max == g)
    b_eq = mask & (c_max == b)

    hue[r_eq] = 60.0 * (((g[r_eq] - b[r_eq]) / delta[r_eq]) % 6.0)
    hue[g_eq] = 60.0 * (((b[g_eq] - r[g_eq]) / delta[g_eq]) + 2.0)
    hue[b_eq] = 60.0 * (((r[b_eq] - g[b_eq]) / delta[b_eq]) + 4.0)

    sat = np.where(c_max > 1e-6, delta / np.maximum(c_max, 1e-6), 0.0)
    return luma, sat, hue


def hue_weight(hue: np.ndarray, center: float, width: float) -> np.ndarray:
    """Smooth cosine bell weight around a target hue angle."""
    diff = np.abs((hue - center + 180.0) % 360.0 - 180.0)
    w = np.clip(1.0 - diff / width, 0.0, 1.0)
    return 0.5 - 0.5 * np.cos(np.pi * w)


def grade_linear_709(rgb_lin: np.ndarray) -> np.ndarray:
    """
    Apply Golden Daylight Cinema creative grade in Linear Rec.709,
    then tone-map smoothly to [0, 1] SDR display-linear.
    """
    # Clamp negative out-of-gamut excursions gently
    rgb = np.maximum(rgb_lin, 0.0)

    # 1. Subtle exposure anchor: keep midday from blowing out (-0.08 EV)
    rgb = rgb * 0.945

    # 2. Filmic soft-shoulder tone mapping (preserves highlight texture)
    #    Maps 0.18 -> ~0.165, 1.0 -> ~0.68, 4.0 -> ~0.92, inf -> 1.0
    a = 1.15
    b = 0.22
    rgb_tm = (rgb * (a * rgb + b)) / (rgb * (a * rgb + 1.08) + b + 0.02)

    # 3. Compute luma, sat, hue on tone-mapped linear for targeted grading
    luma, sat, hue = rgb_to_hsl_luma_hue(rgb_tm)

    # 4. Sun/Shade Split-Toning:
    #    - Deep shadows: subtle cool slate/teal for architectural depth
    #    - Midtones/lower-highlights: honey & subtle amber warmth
    #    - Top highlights (>0.82): taper warmth back to keep clouds/whites clean
    shadow_w = np.exp(-((luma / 0.14) ** 2))
    warm_w = np.exp(-(((luma - 0.44) / 0.28) ** 2)) * (1.0 - np.clip((luma - 0.78) / 0.22, 0.0, 1.0))

    r = rgb_tm[..., 0]
    g = rgb_tm[..., 1]
    b_ch = rgb_tm[..., 2]

    # Apply split-tone
    r = r + warm_w * 0.022 - shadow_w * 0.004
    g = g + warm_w * 0.008 + shadow_w * 0.001
    b_ch = b_ch - warm_w * 0.024 + shadow_w * 0.006

    # 5. Hue-targeted refinements:
    #    a) Skies (200-235 deg): slightly richer cobalt, tame excessive cyan
    sky_w = hue_weight(hue, 212.0, 38.0) * np.clip(sat * 1.5, 0.0, 1.0) * np.clip(luma * 2.0, 0.0, 1.0)
    r = r - sky_w * 0.012
    g = g - sky_w * 0.014
    b_ch = b_ch + sky_w * 0.010

    #    b) Greenery (95-145 deg): natural Mediterranean olive/sage, tame neon green
    green_w = hue_weight(hue, 118.0, 35.0) * np.clip(sat * 1.4, 0.0, 1.0)
    r = r + green_w * 0.010
    g = g - green_w * 0.012
    b_ch = b_ch - green_w * 0.006

    #    c) Skin tones (15-42 deg): protect from oversaturation / orange cast
    skin_w = hue_weight(hue, 26.0, 22.0) * np.clip(sat * 1.2, 0.0, 1.0)
    # Gently pull back excess chroma in skin
    skin_luma = 0.2126 * r + 0.7152 * g + 0.0722 * b_ch
    r = r - skin_w * 0.10 * (r - skin_luma)
    g = g - skin_w * 0.08 * (g - skin_luma)
    b_ch = b_ch - skin_w * 0.06 * (b_ch - skin_luma)

    graded = np.stack([r, g, b_ch], axis=-1)

    # 6. Gentle midtone contrast S-curve in display-linear
    graded = np.clip(graded, 0.0, 1.0)
    # Lift blacks very slightly (0.003) so shadows remain detailed
    graded = 0.003 + 0.997 * graded
    return np.clip(graded, 0.0, 1.0)


def apple_log2_to_rec709_gamma24(rgb_log2: np.ndarray) -> np.ndarray:
    """Full standalone pipeline: Apple Log 2 (AWG) -> Rec.709 Gamma 2.4."""
    lin_awg = apple_log_to_linear(rgb_log2)
    lin_709 = lin_awg @ M_AWG_TO_709.T
    graded_lin_709 = grade_linear_709(lin_709)
    # Rec.709 Gamma 2.4 OETF
    out = np.power(np.clip(graded_lin_709, 0.0, 1.0), 1.0 / 2.4)
    return np.clip(out, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 4. Build 33x33x33 .cube LUT
# ---------------------------------------------------------------------------

def build_cube_lut(output_path: str, size: int = 33):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    vals = np.linspace(0.0, 1.0, size, dtype=np.float64)
    # .cube standard order: R varies fastest, then G, then B
    b_grid, g_grid, r_grid = np.meshgrid(vals, vals, vals, indexing="ij")
    lut_in = np.stack([r_grid, g_grid, b_grid], axis=-1).reshape(-1, 3)

    lut_out = apple_log2_to_rec709_gamma24(lut_in)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# GOLDEN DAYLIGHT CINEMA\n")
        f.write("# Input:  Apple Log 2 (Apple Wide Gamut)\n")
        f.write("# Output: Rec.709 SDR, Gamma 2.4\n")
        f.write('TITLE "GOLDEN DAYLIGHT CINEMA"\n')
        f.write(f"LUT_3D_SIZE {size}\n")
        f.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        f.write("DOMAIN_MAX 1.0 1.0 1.0\n\n")
        for r, g, b in lut_out:
            f.write(f"{r:.6f} {g:.6f} {b:.6f}\n")

    print(f"Saved {size}x{size}x{size} .cube LUT to {output_path}")


# ---------------------------------------------------------------------------
# 5. Trilinear 3D LUT Application (for rendering actual AFTER proofs)
# ---------------------------------------------------------------------------

def load_cube_lut(cube_path: str):
    size = None
    data = []
    with open(cube_path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("TITLE") or s.startswith("DOMAIN_"):
                continue
            if s.startswith("LUT_3D_SIZE"):
                size = int(s.split()[1])
                continue
            parts = s.split()
            if len(parts) == 3:
                data.append([float(parts[0]), float(parts[1]), float(parts[2])])
    arr = np.array(data, dtype=np.float64).reshape(size, size, size, 3)
    return arr, size


def apply_3d_lut_trilinear(img: np.ndarray, lut: np.ndarray, size: int) -> np.ndarray:
    """Apply 3D LUT (indexed [B, G, R, 3]) to image [H, W, 3] in [0, 1]."""
    img = np.clip(img, 0.0, 1.0)
    scale = size - 1
    r = img[..., 0] * scale
    g = img[..., 1] * scale
    b = img[..., 2] * scale

    r0 = np.floor(r).astype(np.int32)
    g0 = np.floor(g).astype(np.int32)
    b0 = np.floor(b).astype(np.int32)

    r1 = np.minimum(r0 + 1, scale)
    g1 = np.minimum(g0 + 1, scale)
    b1 = np.minimum(b0 + 1, scale)

    dr = (r - r0)[..., np.newaxis]
    dg = (g - g0)[..., np.newaxis]
    db = (b - b0)[..., np.newaxis]

    c000 = lut[b0, g0, r0]
    c001 = lut[b0, g0, r1]
    c010 = lut[b0, g1, r0]
    c011 = lut[b0, g1, r1]
    c100 = lut[b1, g0, r0]
    c101 = lut[b1, g0, r1]
    c110 = lut[b1, g1, r0]
    c111 = lut[b1, g1, r1]

    c00 = c000 * (1.0 - dr) + c001 * dr
    c01 = c010 * (1.0 - dr) + c011 * dr
    c10 = c100 * (1.0 - dr) + c101 * dr
    c11 = c110 * (1.0 - dr) + c111 * dr

    c0 = c00 * (1.0 - dg) + c01 * dg
    c1 = c10 * (1.0 - dg) + c11 * dg

    c = c0 * (1.0 - db) + c1 * db
    return np.clip(c, 0.0, 1.0)


def srgb_to_linear(img: np.ndarray) -> np.ndarray:
    img = np.clip(img, 0.0, 1.0)
    return np.where(img <= 0.04045, img / 12.92, np.power((img + 0.055) / 1.055, 2.4))


def simulate_apple_log2_from_srgb(img_srgb: np.ndarray) -> np.ndarray:
    """
    Documented simulation: sRGB -> Linear Rec.709 -> Linear Apple Wide Gamut -> Apple Log 2.
    Note: Real iPhone 17 Pro sensor footage has wider dynamic range (>1.0 linear);
    sRGB sources are capped at 1.0 linear.
    """
    lin_709 = srgb_to_linear(img_srgb)
    lin_awg = lin_709 @ M_709_TO_AWG.T
    return linear_to_apple_log(lin_awg)


# ---------------------------------------------------------------------------
# 6. Render 8 BEFORE / AFTER Scenes
# ---------------------------------------------------------------------------

SCENES = [
    ("01_harsh_midday_city", "image-search/harsh-midday-city-bright-buildings-blue--1.jpg"),
    ("02_midday_portrait", "image-search/woman-portrait-sunny-day-pexels-unsplash-1.jpg"),
    ("03_mediterranean_street", "image-search/mediterranean-street-sunny-stone-buildin-2.jpg"),
    ("04_bright_beach_daylight", "image-search/bright-beach-daylight-turquoise-water-sa-1.webp"),
    ("05_natural_landscape", "image-search/natural-landscape-greenery-mountains-sun-1.jpg"),
    ("06_golden_hour_landscape", "image-search/golden-hour-landscape-warm-sunset-hills-2.jpg"),
    ("07_modern_architecture", "image-search/modern-architecture-concrete-glass-sunli-1.jpg"),
    ("08_outdoor_travel_scene", "image-search/outdoor-travel-scene-people-buildings-su-1.jpg"),
]


def render_scenes(cube_path: str, previews_dir: str):
    os.makedirs(previews_dir, exist_ok=True)
    lut, size = load_cube_lut(cube_path)

    for name, src_path in SCENES:
        im = Image.open(src_path).convert("RGB")
        # Save BEFORE (original Rec.709/sRGB source)
        before_path = os.path.join(previews_dir, f"{name}_BEFORE.png")
        im.save(before_path, format="PNG")

        # Simulate Apple Log 2 input, then apply the ACTUAL .cube LUT
        arr_srgb = np.asarray(im, dtype=np.float64) / 255.0
        sim_log2 = simulate_apple_log2_from_srgb(arr_srgb)
        after_arr = apply_3d_lut_trilinear(sim_log2, lut, size)

        after_u8 = np.round(np.clip(after_arr, 0.0, 1.0) * 255.0).astype(np.uint8)
        after_path = os.path.join(previews_dir, f"{name}_AFTER.png")
        Image.fromarray(after_u8, mode="RGB").save(after_path, format="PNG")
        print(f"Rendered {name}: BEFORE & AFTER ({im.size[0]}x{im.size[1]})")


if __name__ == "__main__":
    cube_out = "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
    build_cube_lut(cube_out, size=33)
    render_scenes(cube_out, "GOLDEN_DAYLIGHT_CINEMA/PREVIEWS")
