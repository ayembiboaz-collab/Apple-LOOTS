"""
verify_colorscience.py — independent verification of the Apple Log 2 maths.

Run:  python3 scripts/verify_colorscience.py

Checks performed
----------------
A. Apple Log transfer function round-trip (encode/decode identity).
B. Apple Log anchor points against the white paper's published table
   (0 %, 18 %, 90 %, 1200 % reflectance -> 10-bit full-range code 154, 500,
   697, 1023).
C. Apple Wide Gamut -> ACES2065-1 (Bradford) matrix re-derived from the
   published chromaticities, compared to the matrix published by
   OpenColorIO-Config-ACES PR #179 / the Blender studio config.
D. Matrix row sums (neutral preservation) for AWG -> Rec.709.
E. Gamut-compression sanity (monotonic, identity near achromatic).
F. Filmic sigmoid monotonicity, C1 continuity at the pivot, endpoints.
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

import applelog2 as al2

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f"\n        {detail}" if detail else ""))
    if not condition:
        FAILURES.append(name)


def main():
    np.set_printoptions(precision=15, suppress=False)

    print("=" * 78)
    print("A. APPLE LOG TRANSFER FUNCTION ROUND-TRIP")
    print("=" * 78)
    R = np.concatenate(
        [
            np.linspace(-0.05, 0.01, 2000),
            np.geomspace(0.01, 100.0, 20000),
        ]
    )
    P = al2.apple_log_encode(R)
    R2 = al2.apple_log_decode(P)
    err = np.max(np.abs(R - R2))
    check(
        "encode -> decode round-trip identity",
        err < 1e-9,
        f"max |R - decode(encode(R))| = {err:.3e} over R in [-0.05, 100]",
    )

    P_grid = np.linspace(0.0, 1.0, 100001)
    R_grid = al2.apple_log_decode(P_grid)
    check(
        "decode is strictly monotonic on P in [0, 1]",
        np.all(np.diff(R_grid) > 0),
        f"min delta = {np.min(np.diff(R_grid)):.3e}",
    )
    check(
        "decode produces no NaN / Inf on P in [0, 1]",
        np.all(np.isfinite(R_grid)),
    )

    print()
    print("=" * 78)
    print("B. APPLE LOG ANCHOR POINTS vs PUBLISHED WHITE-PAPER TABLE")
    print("=" * 78)
    # White paper Table: scene reflection -> 10-bit full range code value
    anchors = [(0.00, 154), (0.18, 500), (0.90, 697), (12.00, 1023)]
    ok = True
    for refl, expected_code in anchors:
        p = float(al2.apple_log_encode(refl))
        code = p * 1023.0
        delta = abs(code - expected_code)
        ok &= delta < 1.0
        print(
            f"        reflectance {refl*100:7.2f} %  ->  P = {p:.8f}  ->  "
            f"10-bit {code:8.3f}   (paper: {expected_code},  delta {delta:.3f})"
        )
    check("all four published anchor points reproduce within 1 code value", ok)

    p18 = float(al2.apple_log_encode(0.18))
    check(
        "colour-science reference value log_encoding_AppleLogProfile(0.18)",
        abs(p18 - 0.48827245852686763) < 1e-12,
        f"ours {p18:.17f}  vs reference 0.48827245852686763",
    )

    print()
    print("=" * 78)
    print("C. APPLE WIDE GAMUT -> ACES2065-1 (BRADFORD) vs PUBLISHED OCIO MATRIX")
    print("=" * 78)
    derived = al2.AWG_TO_AP0_BRADFORD
    ref = al2.AWG_TO_AP0_REFERENCE
    diff = np.max(np.abs(derived - ref))
    print("        derived from published chromaticities:")
    for row in derived:
        print("          [" + ", ".join(f"{v: .15f}" for v in row) + "]")
    print("        OpenColorIO-Config-ACES published reference:")
    for row in ref:
        print("          [" + ", ".join(f"{v: .15f}" for v in row) + "]")
    check(
        "derived AWG->AP0 matrix matches the published OCIO matrix",
        diff < 1e-12,
        f"max absolute element difference = {diff:.3e}",
    )

    print()
    print("=" * 78)
    print("D. NEUTRAL PRESERVATION OF THE GAMUT MATRICES")
    print("=" * 78)
    for label, M in [
        ("Apple Wide Gamut -> Rec.709 (both D65, no CAT)", al2.AWG_TO_REC709),
        ("Apple Wide Gamut -> Rec.2020 (both D65, no CAT)", al2.AWG_TO_REC2020),
        ("Apple Wide Gamut -> ACES AP0 (Bradford D65->D60)", al2.AWG_TO_AP0_BRADFORD),
    ]:
        sums = M.sum(axis=1)
        print(f"        {label}")
        for row in M:
            print("          [" + ", ".join(f"{v: .15f}" for v in row) + "]")
        print(f"          row sums: {sums}")
        check(
            f"row sums are 1.0 (neutral in -> neutral out): {label}",
            np.allclose(sums, 1.0, atol=1e-12),
            f"max |rowsum - 1| = {np.max(np.abs(sums - 1.0)):.3e}",
        )

    # D65 white must map to D65 white
    w = al2.apply_matrix(np.array([1.0, 1.0, 1.0]), al2.AWG_TO_REC709)
    check(
        "AWG (1,1,1) -> Rec.709 (1,1,1)",
        np.allclose(w, 1.0, atol=1e-12),
        f"got {w}",
    )

    print()
    print("=" * 78)
    print("E. GAMUT COMPRESSION SANITY")
    print("=" * 78)
    # Achromatic must be untouched
    neutral = np.stack([np.linspace(0, 4, 200)] * 3, axis=-1)
    gc_neutral = al2.gamut_compress(neutral)
    check(
        "gamut compression is identity on the achromatic axis",
        np.max(np.abs(gc_neutral - neutral)) < 1e-12,
        f"max deviation = {np.max(np.abs(gc_neutral - neutral)):.3e}",
    )

    # Mildly saturated in-gamut colours must be untouched (below threshold)
    mild = np.array([[0.5, 0.45, 0.42], [0.2, 0.3, 0.25], [0.8, 0.7, 0.6]])
    check(
        "gamut compression is identity on mildly saturated in-gamut colours",
        np.max(np.abs(al2.gamut_compress(mild) - mild)) < 1e-12,
    )

    # Extreme AWG primaries -> Rec.709 produce negatives; compression fixes them
    prim = np.eye(3) * 0.18
    r709 = al2.apply_matrix(prim, al2.AWG_TO_REC709)
    comp = al2.gamut_compress(r709)
    print(f"        AWG primaries at 0.18 -> Rec.709 linear:\n          {r709.tolist()}")
    print(f"        after gamut compression:\n          {comp.tolist()}")
    check(
        "gamut compression removes negative channels from the AWG primaries",
        np.min(comp) > -1e-6,
        f"min channel after compression = {np.min(comp):.6f} (was {np.min(r709):.6f})",
    )

    print()
    print("=" * 78)
    print("F. FILMIC SIGMOID PROPERTIES")
    print("=" * 78)
    s = al2.FilmicSigmoid()
    xs = np.linspace(s.x_min, s.x_max, 200001)
    ys = s(xs)
    check("sigmoid is monotonically non-decreasing", np.all(np.diff(ys) >= -1e-15))
    check("sigmoid is finite everywhere", np.all(np.isfinite(ys)))
    check(
        f"sigmoid hits y_min at x_min ({s.x_min} st)",
        abs(float(s(s.x_min)) - s.y_min) < 1e-9,
        f"got {float(s(s.x_min)):.12f}",
    )
    check(
        f"sigmoid hits y_max at x_max ({s.x_max} st)",
        abs(float(s(s.x_max)) - s.y_max) < 1e-9,
        f"got {float(s(s.x_max)):.12f}",
    )
    check(
        "sigmoid passes through the pivot",
        abs(float(s(s.x_pivot)) - s.y_pivot) < 1e-12,
    )
    h = 1e-6
    slope_l = (float(s(-h)) - float(s(-2 * h))) / h
    slope_r = (float(s(2 * h)) - float(s(h))) / h
    check(
        "sigmoid is C1 continuous at the pivot (matching one-sided gradients)",
        abs(slope_l - slope_r) < 1e-4 and abs(slope_l - s.slope) < 1e-4,
        f"left {slope_l:.8f}  right {slope_r:.8f}  target {s.slope}",
    )
    print("        tone curve anchor points:")
    print(s.describe())

    print()
    print("=" * 78)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} CHECK(S) FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
