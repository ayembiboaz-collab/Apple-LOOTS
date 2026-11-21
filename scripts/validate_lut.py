#!/usr/bin/env python3
"""
Validate GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube
and write GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt
"""

import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from build_lut import (
    M_AWG_TO_709,
    apple_log_to_linear,
    linear_to_apple_log,
    load_cube_lut,
    apply_3d_lut_trilinear,
    simulate_apple_log2_from_srgb,
    SCENES,
)


def main():
    cube_path = "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
    lut, size = load_cube_lut(cube_path)

    lines = []
    lines.append("=================================================================")
    lines.append("GOLDEN DAYLIGHT CINEMA — VALIDATION REPORT")
    lines.append("=================================================================\n")

    # 1. Syntax & Numerical Integrity
    expected_entries = 33 ** 3
    actual_entries = lut.size // 3
    has_nan = bool(np.isnan(lut).any())
    has_inf = bool(np.isinf(lut).any())
    min_val = float(lut.min())
    max_val = float(lut.max())

    lines.append("1. CUBE SYNTAX & NUMERICAL INTEGRITY")
    lines.append(f"   - File: {cube_path}")
    lines.append(f"   - LUT_3D_SIZE: {size} (expected 33) -> {'PASS' if size == 33 else 'FAIL'}")
    lines.append(f"   - Entry count: {actual_entries} (expected {expected_entries}) -> {'PASS' if actual_entries == expected_entries else 'FAIL'}")
    lines.append(f"   - NaN values: {has_nan} -> {'PASS' if not has_nan else 'FAIL'}")
    lines.append(f"   - Inf values: {has_inf} -> {'PASS' if not has_inf else 'FAIL'}")
    lines.append(f"   - Value range: [{min_val:.6f}, {max_val:.6f}] (within [0, 1]) -> {'PASS' if min_val >= 0.0 and max_val <= 1.0 else 'FAIL'}\n")

    # 2. Apple Log 2 & Apple Wide Gamut Verification
    row_sums = M_AWG_TO_709.sum(axis=1)
    gray_18_log = float(linear_to_apple_log(np.array([0.18]))[0])
    gray_18_dec = float(apple_log_to_linear(np.array([gray_18_log]))[0])

    lines.append("2. APPLE LOG 2 & APPLE WIDE GAMUT VERIFICATION")
    lines.append("   - Transfer function: Apple Log Profile White Paper (Sept 2023) / Apple Log 2 White Paper (Sept 2025)")
    lines.append(f"   - 18% middle grey (0.18 linear) -> Apple Log 2 code: {gray_18_log:.6f} (10-bit: {gray_18_log*1023:.1f})")
    lines.append(f"   - Round-trip decode of 18% grey: {gray_18_dec:.6f} (error: {abs(gray_18_dec - 0.18):.2e})")
    lines.append("   - Apple Wide Gamut primaries (OCIO PR #2343 / Apple Log 2 White Paper): R(0.725,0.301), G(0.221,0.814), B(0.068,-0.076), D65")
    lines.append(f"   - AWG->Rec.709 matrix row sums: [{row_sums[0]:.6f}, {row_sums[1]:.6f}, {row_sums[2]:.6f}] (D65 neutral preservation)\n")

    # 3. Neutral Ramp Smoothness & Monotonicity
    ramp = np.linspace(0.0, 1.0, 256)
    ramp_rgb = np.stack([ramp, ramp, ramp], axis=-1)[:, np.newaxis, :]
    ramp_out = apply_3d_lut_trilinear(ramp_rgb, lut, size)[:, 0, :]
    luma_out = 0.2126 * ramp_out[:, 0] + 0.7152 * ramp_out[:, 1] + 0.0722 * ramp_out[:, 2]
    diffs = np.diff(luma_out)
    monotonic = bool((diffs >= -1e-6).all())
    black_out = luma_out[0]
    white_out = luma_out[-1]

    lines.append("3. NEUTRAL RAMP & TONAL SMOOTHNESS")
    lines.append(f"   - Monotonicity across 256-step neutral ramp: {'PASS' if monotonic else 'FAIL'} (min step: {diffs.min():.6f})")
    lines.append(f"   - Black point output luma (input 0.0): {black_out:.6f} (detail-preserving toe > 0)")
    lines.append(f"   - White point output luma (input 1.0): {white_out:.6f}\n")

    # 4. Simulated Exposure Sweep (-1 EV, 0 EV, +1 EV)
    lines.append("4. SIMULATED EXPOSURE SWEEP (18% GREY ANCHOR)")
    for ev in (-1.0, 0.0, 1.0):
        lin_val = 0.18 * (2.0 ** ev)
        log_val = linear_to_apple_log(np.array([lin_val]))[0]
        px = np.array([[[log_val, log_val, log_val]]], dtype=np.float64)
        out_px = apply_3d_lut_trilinear(px, lut, size)[0, 0]
        lines.append(f"   - {ev:+.0f} EV (linear {lin_val:.3f}, Log2 {log_val:.4f}) -> Rec.709 RGB: ({out_px[0]:.4f}, {out_px[1]:.4f}, {out_px[2]:.4f})")
    lines.append("")

    # 5. Scene-by-Scene Clipping & Colorimetry Summary
    lines.append("5. SCENE-BY-SCENE RENDERING & CLIPPING CHECK (ACTUAL .CUBE APPLIED)")
    for name, src_path in SCENES:
        after_path = f"GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/{name}_AFTER.png"
        arr = np.asarray(Image.open(after_path).convert("RGB"), dtype=np.float64) / 255.0
        pct_black_clip = float((arr <= 0.004).mean() * 100.0)
        pct_white_clip = float((arr >= 0.996).mean() * 100.0)
        mean_luma = float((0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]).mean())
        lines.append(f"   - {name}: mean_luma={mean_luma:.3f}, near_black={pct_black_clip:.2f}%, near_white={pct_white_clip:.2f}%")
    lines.append("")

    # 6. Limitations & Testing Scope
    lines.append("6. LIMITATIONS & TESTING SCOPE")
    lines.append("   - Physical iPhone 17 Pro / Blackmagic Camera for iOS testing was NOT performed in this sandbox.")
    lines.append("   - Test scenes use documented simulated Apple Log 2 derived from sRGB/Rec.709 reference images (capped at 1.0 linear).")
    lines.append("   - A 3D LUT cannot recover highlights that were already clipped in the camera sensor or source file.")
    lines.append("   - Image sources: Pexels (scenes 01, 02), iStock/Stockcake/FabulousNaturePhotos/Dreamstime (scenes 03-08).\n")

    report_path = "GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Saved validation report to {report_path}")


if __name__ == "__main__":
    main()
