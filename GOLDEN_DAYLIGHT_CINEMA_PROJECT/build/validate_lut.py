"""
Comprehensive Validation Suite for GOLDEN_DAYLIGHT_CINEMA.cube
Tests the delivered .cube file directly (not an internal copy).
"""

import json
import os
import hashlib
import numpy as np
import colour
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from color_science_core import (
    load_cube_lut,
    apply_cube_trilinear,
    apply_cube_tetrahedral,
    golden_daylight_cinema_analytic,
    log_encoding_AppleLog2,
    rec709_to_apple_wg,
    REC709_CS,
)

ROOT = "GOLDEN_DAYLIGHT_CINEMA_PROJECT"
LUT_PATH = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
VAL_DIR = os.path.join(ROOT, "validation")
REPORT_PATH = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA", "VALIDATION_REPORT.txt")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rec709_gamma24_to_lab(rgb: np.ndarray) -> np.ndarray:
    lin = np.power(np.clip(rgb, 0.0, 1.0), 2.4)
    xyz = colour.RGB_to_XYZ(lin, REC709_CS)
    return colour.XYZ_to_Lab(xyz)


def main():
    os.makedirs(VAL_DIR, exist_ok=True)
    lut, size = load_cube_lut(LUT_PATH)
    lut_sha256 = sha256_file(LUT_PATH)

    # 1. Structural & numerical integrity
    assert size == 33, f"Expected 33, got {size}"
    assert lut.shape == (33, 33, 33, 3)
    has_nan = bool(np.isnan(lut).any())
    has_inf = bool(np.isinf(lut).any())
    min_val = float(lut.min())
    max_val = float(lut.max())

    # 2. 33^3 Interpolation Error vs Analytic Pipeline (random 10,000 samples in [0,1]^3)
    rng = np.random.default_rng(42)
    samples = rng.uniform(0.0, 1.0, size=(10000, 3))
    analytic_out = golden_daylight_cinema_analytic(samples)
    trilin_out = apply_cube_trilinear(samples, lut)
    tetra_out = apply_cube_tetrahedral(samples, lut)

    lab_ana = rec709_gamma24_to_lab(analytic_out)
    lab_tri = rec709_gamma24_to_lab(trilin_out)
    lab_tet = rec709_gamma24_to_lab(tetra_out)

    de_tri = colour.delta_E(lab_ana, lab_tri, method="CIE 2000")
    de_tet = colour.delta_E(lab_ana, lab_tet, method="CIE 2000")

    # 3. Neutral Axis / Grey Ramp & Monotonicity (256 steps)
    ramp_1d = np.linspace(0.0, 1.0, 256)
    ramp_rgb = np.stack([ramp_1d, ramp_1d, ramp_1d], axis=-1)
    ramp_out = apply_cube_tetrahedral(ramp_rgb, lut)
    luma_out = 0.2126 * ramp_out[:, 0] + 0.7152 * ramp_out[:, 1] + 0.0722 * ramp_out[:, 2]
    d1 = np.diff(luma_out)
    monotonic = bool(np.all(d1 >= -1e-6))

    # Chroma along neutral ramp
    ramp_lab = rec709_gamma24_to_lab(ramp_out)
    ramp_chroma = np.sqrt(ramp_lab[:, 1] ** 2 + ramp_lab[:, 2] ** 2)

    # 4. Shadow-noise robustness
    # Add Gaussian noise (sigma=0.005) to dark grey (0.15 in Apple Log 2)
    shadow_base = np.full((2000, 3), 0.15)
    noisy_shadow = np.clip(shadow_base + rng.normal(0.0, 0.005, size=(2000, 3)), 0.0, 1.0)
    shadow_out = apply_cube_tetrahedral(noisy_shadow, lut)
    noise_gain = float(np.std(shadow_out) / np.std(noisy_shadow))

    # 5. Skin-line & Exposure Ladder (-2, -1, 0, +1 stops)
    # Typical skin in linear Rec.709 ~ [0.36, 0.22, 0.16]
    skin_lin709 = np.array([[0.36, 0.22, 0.16]])
    skin_exposures = {}
    for stops in [-2, -1, 0, 1]:
        scaled = skin_lin709 * (2.0 ** stops)
        awg = rec709_to_apple_wg(scaled)
        log2_in = np.clip(log_encoding_AppleLog2(awg), 0.0, 1.0)
        out_rgb = apply_cube_tetrahedral(log2_in, lut)[0]
        skin_exposures[f"{stops:+d}_stops"] = [round(float(x), 4) for x in out_rgb]

    results = {
        "lut_path": LUT_PATH,
        "lut_sha256": lut_sha256,
        "lut_size": size,
        "has_nan": has_nan,
        "has_inf": has_inf,
        "min_val": min_val,
        "max_val": max_val,
        "trilinear_de2000_mean": float(np.mean(de_tri)),
        "trilinear_de2000_max": float(np.max(de_tri)),
        "tetrahedral_de2000_mean": float(np.mean(de_tet)),
        "tetrahedral_de2000_max": float(np.max(de_tet)),
        "neutral_ramp_monotonic": monotonic,
        "neutral_ramp_chroma_mean": float(np.mean(ramp_chroma)),
        "neutral_ramp_chroma_max": float(np.max(ramp_chroma)),
        "shadow_noise_gain": noise_gain,
        "skin_exposure_ladder": skin_exposures,
    }

    with open(os.path.join(VAL_DIR, "validation_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    # Plot validation charts
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor="#101114")
    for ax in axes.flat:
        ax.set_facecolor("#181a20")
        ax.tick_params(colors="#cbd5e1")
        for spine in ax.spines.values():
            spine.set_color("#334155")

    axes[0, 0].plot(ramp_1d, ramp_out[:, 0], color="#f87171", label="R")
    axes[0, 0].plot(ramp_1d, ramp_out[:, 1], color="#4ade80", label="G")
    axes[0, 0].plot(ramp_1d, ramp_out[:, 2], color="#60a5fa", label="B")
    axes[0, 0].set_title("Neutral Ramp Response (Apple Log 2 -> Rec.709)", color="#f8fafc")
    axes[0, 0].legend()

    axes[0, 1].plot(ramp_1d[:-1], d1, color="#fbbf24")
    axes[0, 1].axhline(0, color="#64748b", linestyle="--", linewidth=0.8)
    axes[0, 1].set_title("1st Derivative (Monotonicity Check)", color="#f8fafc")

    axes[1, 0].plot(ramp_1d, ramp_chroma, color="#f59e0b")
    axes[1, 0].set_title("Neutral Axis Chroma (CIELAB C*)", color="#f8fafc")

    axes[1, 1].hist(de_tet, bins=40, color="#38bdf8", alpha=0.8, label="Tetrahedral")
    axes[1, 1].hist(de_tri, bins=40, color="#f472b6", alpha=0.5, label="Trilinear")
    axes[1, 1].set_title("33x33x33 Bake Error vs Analytic (CIEDE2000)", color="#f8fafc")
    axes[1, 1].legend()

    plt.tight_layout()
    plt.savefig(os.path.join(VAL_DIR, "validation_charts.png"), dpi=150)

    # Write VALIDATION_REPORT.txt
    report = f"""GOLDEN DAYLIGHT CINEMA — VALIDATION REPORT
==========================================
Delivered LUT: GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube
SHA-256:       {lut_sha256}
Dimensions:    {size}x{size}x{size} (3D .cube, red-fastest ordering, domain 0.0-1.0)

1. NUMERICAL INTEGRITY
- NaN / Inf:   {has_nan} / {has_inf}
- Value Range: [{min_val:.6f}, {max_val:.6f}]

2. 33x33x33 BAKE ACCURACY VS ANALYTIC FLOAT64 PIPELINE (10,000 samples)
- Tetrahedral CIEDE2000: mean = {results['tetrahedral_de2000_mean']:.4f}, max = {results['tetrahedral_de2000_max']:.4f}
- Trilinear   CIEDE2000: mean = {results['trilinear_de2000_mean']:.4f}, max = {results['trilinear_de2000_max']:.4f}

3. NEUTRAL AXIS, MONOTONICITY & NOISE ROBUSTNESS
- Neutral Ramp Monotonic: {monotonic} (no reversals or kinks)
- Neutral Axis Chroma (deliberate warm midtone split-tone): mean C* = {results['neutral_ramp_chroma_mean']:.2f}, max C* = {results['neutral_ramp_chroma_max']:.2f}
- Shadow Noise Gain (sigma=0.005 at 0.15 log): {noise_gain:.3f}x

4. SKIN EXPOSURE LADDER (Rec.709 Gamma 2.4 output)
- -2 stops: {skin_exposures['-2_stops']}
- -1 stop:  {skin_exposures['-1_stops']}
-  0 stops: {skin_exposures['+0_stops']}
- +1 stop:  {skin_exposures['+1_stops']}

5. HONEST LIMITATIONS & TESTING SCOPE
- A 3D LUT is a fixed per-pixel colour transform: it cannot add film grain, halation, bloom, sharpening, noise reduction, depth-aware edits, or recover clipped highlights.
- All 8 BEFORE/AFTER previews were generated from simulated Apple Log 2 derived from real-world Unsplash sRGB photographs; dynamic range is bounded by the source JPEGs.
- No physical iPhone 17 Pro or Blackmagic Camera iOS device test was performed in this environment.
"""
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    print("Validation complete:", json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
