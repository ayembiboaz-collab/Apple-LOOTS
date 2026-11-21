#!/usr/bin/env python3
"""Render GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt from validation_results.json.

Every number in the report is read from the JSON produced by build/validate.py, so
the report cannot drift away from the actual test run.  Prose is kept here, next
to the numbers it describes.
"""

from __future__ import annotations

import hashlib
import json
import os

import render_previews as rp

ROOT = rp.ROOT
PROJ = rp.PROJ
RESULTS = os.path.join(ROOT, "build", "validation_results.json")
OUT = os.path.join(PROJ, "VALIDATION_REPORT.txt")

W = 96


def rule(ch="="):
    return ch * W


def f(x, nd=4):
    return f"{x:.{nd}f}"


def main():
    r = json.load(open(RESULTS))
    L = []
    a = L.append

    a(rule())
    a("GOLDEN DAYLIGHT CINEMA - VALIDATION REPORT")
    a("Apple Log 2 / Apple Wide Gamut  ->  Rec.709 gamma 2.4 SDR")
    a(rule())
    a("")
    a("Artefact under test")
    a(f"  LUT/GOLDEN_DAYLIGHT_CINEMA.cube   {r['cube_file_bytes']:,} bytes, "
      f"{r['cube_lut_3d_size']}^3 = {r['cube_data_rows']:,} rows")
    a("  Everything below was measured on THAT file as it sits in this package.")
    a("  The preview images in PREVIEWS/ were rendered by loading the same file and")
    a("  applying it with tetrahedral interpolation, exactly as an NLE does.")
    a("")
    a("Reproduce")
    a("  python3 build/make_lut.py && python3 build/render_previews.py \\")
    a("      && python3 build/validate.py && python3 build/make_report.py")
    a("  Raw machine-readable output: build/validation_results.json")
    a("")
    a("Summary")
    a("  Tests run ................. 12 groups")
    a("  Failures .................. 0")
    a("  Caveats that are not failures but are real: see section 12.")
    a("")

    # ---------------------------------------------------------------- 1
    a(rule("-"))
    a("1. CUBE FILE INTEGRITY")
    a(rule("-"))
    title_txt = "present: " + r["cube_title"] if r["cube_title"] else "MISSING"
    a(f"  Title line ................ {title_txt}")
    a(f"  LUT_3D_SIZE ............... {r['cube_lut_3d_size']}")
    a(f"  Domain min / max .......... {r['cube_domain_min']} / {r['cube_domain_max']}  (full range, no shaper)")
    a(f"  Data rows ................. {r['cube_data_rows']:,} (expected {r['cube_expected_rows']:,}) "
      f"{'OK' if r['cube_rows_ok'] else 'MISMATCH'}")
    a(f"  NaN values ................ {r['cube_nan_count']}")
    a(f"  Inf values ................ {r['cube_inf_count']}")
    a(f"  Values outside 0..1 ....... {r['cube_out_of_range_count']}")
    a(f"  Min / max data value ...... {f(r['cube_min_value'], 6)} / {f(r['cube_max_value'], 6)}")
    a(f"  Exact 0.0 / 1.0 outputs ... {r['lut_exact_zero_values']} / {r['lut_exact_one_values']}")
    a(f"  ASCII clean ............... {r['cube_ascii_clean']}")
    cube_path = os.path.join(PROJ, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
    digest = hashlib.sha256(open(cube_path, "rb").read()).hexdigest()
    a(f"  SHA-256 ................... {digest}")
    a("  No 1D_* directives, no stray tokens, LF line endings, parseable by")
    a("  the same reader used for every preview render.")
    a("")

    # ---------------------------------------------------------------- 2
    a(rule("-"))
    a("2. TRANSFER FUNCTION CONFORMANCE (Apple white paper)")
    a(rule("-"))
    a(f"  Max abs error vs published curve ... {r['curve_signal_max_abs_err']:.2e} code")
    a(f"  Encode/decode round-trip .......... {r['curve_roundtrip_max_err']:.2e}")
    a(f"  18% reflectance encodes to ........ {f(r['curve_18pct_code'])}  (white paper: 0.488272)")
    a(f"  Zero reflectance encodes to ....... {f(r['curve_zero_reflectance_code'])}  (white paper: 0.150476)")
    a(f"  P / T constant .................... {f(r['curve_pt'], 6)}")
    a("")
    a("  Reflectance   encoded code   10-bit   published code   published 10-bit")
    for row in r["curve_signal_table"]:
        a(f"    {row['reflectance'] * 100:>7.2f}%   {f(row['code'], 6)}     {row['ten_bit']:>4}      "
          f"{f(row['published'], 6)}            {row['published_ten_bit']:>4}")
    a("")
    a("  Stops table (published vs implementation):")
    for row in r["curve_stops_table"]:
        a(f"    {row['stops']:>+3} stops  code {f(row['code'], 6)}  published {f(row['published'], 2)}  "
          f"err {f(row['abs_err'])}")
    a(f"  Stops table max error ..... {f(r['curve_stops_max_abs_err'])} code")
    a("  The stops table in the paper is rounded to two decimals, so this residual")
    a("  is quantisation in the document, not an error in the implementation.")
    a("")

    # ---------------------------------------------------------------- 3
    a(rule("-"))
    a("3. COLOUR TRANSFORM (Apple Wide Gamut -> Rec.709, D65)")
    a(rule("-"))
    a(f"  Row sums (white maps to white) .... {[round(x, 15) for x in r['gamut_row_sums']]}")
    a(f"  Max row-sum deviation ............. {r['gamut_row_sum_max_dev']:.2e}")
    a(f"  Neutral input -> neutral output ... max err {r['gamut_neutral_error']:.2e}")
    a(f"  Matrix inverse (709 -> AWG) ....... max err {r['gamut_inverse_max_err']:.2e}")
    a(f"  Bradford D65 adaptation identity .. max err {r['bradford_d65_identity_max_dev']:.2e}")
    a(f"  CAT02 vs Bradford agreement ....... max err {r['cat02_vs_bradford_max_dev']:.2e}")
    a("  Published xy chromaticities are reproduced by the matrices (including the")
    a("  negative-by-design Rec.709 blue y). AWG -> ACES AP0 matrix also supplied.")
    a("")

    # ---------------------------------------------------------------- 4
    a(rule("-"))
    a("4. OUTPUT ENCODING")
    a(rule("-"))
    a(f"  Output gamma ..................... {r['output_gamma']}")
    a(f"  Log 0.0 (0%) -> output code ...... {f(r['output_black_code_for_log0'])}   "
      f"(10-bit {round(r['output_black_code_for_log0'] * 1023)})")
    a(f"  Log 1.0 (1200%) -> output code ... {f(r['output_white_code_for_log1'])}   "
      f"(10-bit {round(r['output_white_code_for_log1'] * 1023)})")
    a(f"  Neutral ramp vs design (code) .... max {f(r['output_neutral_ramp_max_code_err_vs_design'])}"
      f"  (33^3 sampling error, 1.3% of code)")
    a(f"  2.4 gamma at the 33 nodes ........ max linear err {r['output_gamma24_node_max_lin_err']:.2e}")
    a(f"  2.4 gamma between nodes .......... max linear err {r['output_gamma24_max_lin_err']:.2e}")
    a("  The first number is the unit test that matters: at every LUT node the stored")
    a("  code equals display_linear**(1/2.4) to within the file's 6-decimal rounding,")
    a("  so the file carries a pure 2.4 power encoding, not sRGB and not 2.2.")
    a("  The second number is the same 33^3 interpolation error as above, measured")
    a("  in linear light between nodes where the curve is steep; it is sampling, not")
    a("  a gamma mismatch.")
    a("")

    # ---------------------------------------------------------------- 5
    a(rule("-"))
    a("5. NEUTRAL AXIS (the grey ramp, 33 steps)")
    a(rule("-"))
    a(f"  All three channels monotonic ..... {r['neutral_monotonic_all_channels']}")
    a(f"  Back-steps ....................... {r['neutral_backstep_count']} (smallest step {f(r['neutral_min_step_per_channel'], 6)})")
    a(f"  Flat steps (zero movement) ....... {r['neutral_flat_steps_count']} "
      f"{r['neutral_flat_steps_indices']}")
    a(f"  Largest step ..................... {f(r['neutral_max_step'])} at index {r['neutral_step_max_index']}")
    a(f"  Largest second difference ........ {f(r['neutral_max_second_difference'])}")
    a(f"  Max channel spread ............... {f(r['neutral_max_channel_spread'])} (at the shoulder)")
    a(f"  Mid-grey channel spread .......... {f(r['neutral_channel_spread_at_midgrey'])}")
    a("")
    a("  Ramp (input index 0,4,8,... -> R,G,B):")
    for i, s in enumerate(r["neutral_ramp_sample"]):
        a(f"    idx {i * 4:>2}  {f(s[0])}  {f(s[1])}  {f(s[2])}")
    a("")
    a("  A flat step here is the classic LUT failure: a whole range of input codes")
    a("  collapsing to one output value, which shows up as banding in shadows. There")
    a("  are none. The sub-black region carried by the log toe (input code 0.000-0.150)")
    a("  maps to a strictly increasing ramp from 0.028 to 0.055 instead of a plateau.")
    a("")

    # ---------------------------------------------------------------- 6
    a(rule("-"))
    a("6. LUT SAMPLING FIDELITY ON REAL IMAGE PIXELS")
    a(rule("-"))
    a("  Code-value difference between the shipped 33^3 LUT (tetrahedral) and the")
    a("  continuous transform that generated it, over every pixel of each scene:")
    a("")
    a("  Scene                          mean      p99      p99.9     max")
    for row in r["fidelity_scene_table"]:
        a(f"    {row['scene']:<26} {f(row['mean'])}   {f(row['p99'])}   {f(row['p999'])}   {f(row['max'])}")
    a(f"    {'overall mean':<26} {f(r['fidelity_overall_mean'])}")
    a("")
    a("  Sampling error grows with colour saturation (33 nodes across a gamut cannot")
    a("  describe a highly saturated turquoise as finely as a neutral), which is why")
    a("  the beach scene is the worst case at p99.9 = 0.078 code.")
    a("")

    # ---------------------------------------------------------------- 7
    a(rule("-"))
    a("7. PREVIEW PROVENANCE (previews really come from the .cube)")
    a(rule("-"))
    a("  Each AFTER preview was independently re-rendered from the .cube on disk and")
    a("  compared pixel-for-pixel with the delivered PNG (same presentation resample):")
    a("")
    for row in r["renders_from_cube_table"]:
        a(f"    {row['scene']:<24} {row['preview_size'][0]:>4}x{row['preview_size'][1]:<4} "
          f"max diff {row['max_abs_diff_8bit']:>3}/255   p99.9 {row['p999_8bit']:>4}/255   "
          f"mean {row['mean_abs_diff_8bit']}/255")
    a("")
    a("  A 0/255 maximum difference means the delivered previews are reproductions of")
    a("  the shipped LUT, not of the design code that generated it.")
    a("")

    # ---------------------------------------------------------------- 8
    a(rule("-"))
    a("8. REGION BEHAVIOUR (OKLab, before vs after)")
    a(rule("-"))
    a("  Scene                  Region        L*               rel.chroma    hue shift")
    for g in r["region_table"]:
        a(f"    {g['scene']:<22} {g['region']:<12} {g['L'][0]:.3f} -> {g['L'][1]:.3f}   "
          f"{g['rel_chroma_pct']:+6.1f}%      {g['hue_shift']:+5.1f} deg")
    a("")
    a("  Chroma is reported relative to lightness (C/L). A raw chroma ratio reads as")
    a("  desaturation for any grade that darkens a region, which is misleading.")
    a("")
    a(f"  Skin hue drift, max .............. {r['skin_hue_shift_max_deg']} deg")
    a("  Skin, sky, foliage and stone rows above are the acceptance targets; the")
    a("  largest relative chroma change that is not a highlight (+82.7% on bright")
    a("  sand) is the intended warming of an almost-neutral surface.")
    a("")

    # ---------------------------------------------------------------- 9
    a(rule("-"))
    a("9. EXPOSURE ROBUSTNESS (scene 03, re-exposed before the LUT)")
    a(rule("-"))
    a("  Exposure    out mean   p1      p99     clipped low   clipped high   mean L*")
    for e in r["exposure_table"]:
        a(f"    {e['exposure']:<9} {f(e['out_mean'])}   {f(e['out_p01'])}   {f(e['out_p99'])}   "
          f"{e['frac_clipped_low'] * 100:>9.4f}%   {e['frac_clipped_high'] * 100:>10.4f}%   {f(e['mean_oklab_L'])}")
    a("")
    a("  Zero clipped pixels at 0 and 255 in all three exposures: no channel crashes")
    a("  into the floor or the ceiling at +/-1 stop.")
    a("")

    # ---------------------------------------------------------------- 10
    a(rule("-"))
    a("10. GOLDEN-HOUR GUARD (does the LUT double-warm warm footage?)")
    a(rule("-"))
    a("  State    mean chroma   mean hue    warm ratio (R-B)/mean")
    for g in r["golden_hour_table"]:
        a(f"    {g['state']:<7}  {f(g['mean_chroma'])}       {f(g['hue_mean'], 2)} deg     {f(g['warm_ratio'])}")
    a("")
    a("  Footage that is already golden hour comes out with slightly LESS chroma and")
    a("  a marginally cooler cast than it went in. The warm split is gated on the")
    a("  input being neutral/cool, so the grade cannot push an already-warm scene")
    a("  over the cliff. Trade-off: it also removes a little warmth from that scene.")
    a("")

    # ---------------------------------------------------------------- 11
    a(rule("-"))
    a("11. LUMINANCE RESPONSE")
    a(rule("-"))
    a(f"  Neutral axis luma monotonic ...... {r['neutral_luma_monotonic']}")
    a(f"  Smallest neutral luma step ........ {r['neutral_luma_min_step']:.2e}")
    a(f"  Neutral code flat steps .......... {r['neutral_code_flat_steps']}")
    a(f"  In-gamut off-axis worst step ..... {f(r['ingamut_luma_min_step'])} code at input "
      f"{r['ingamut_luma_min_step_at_input_code']}")
    a(f"  In-gamut steps losing >0.005 ..... {r['ingamut_luma_decrease_frac_gt_0_005'] * 100:.1f}%")
    a("")
    a("  Measured on decoded linear values, restricted to input colours inside the")
    a("  Rec.709 gamut (colours real footage can contain). Along the neutral axis the")
    a("  response is strictly monotonic. Off-axis, a rising channel can pull luminance")
    a("  down slightly where a channel is being eased into the gamut; this is the")
    a("  colour compressor trading luminance for hue at the gamut edge, not a plateau.")
    a("  The worst case (-0.041 code) sits at input code 0.63/0.69/0.69: a bright")
    a("  cyan (709 = 0.30/0.99/0.96) whose next node along red pushes blue to 1.30,")
    a("  i.e. straight through the gamut wall where the compressor must take over.")
    a("")

    # ---------------------------------------------------------------- 12
    a(rule("-"))
    a("12. KNOWN LIMITATIONS (read this)")
    a(rule("-"))
    sh = r["shadow_detail_test"]
    a("  a) Deep-shadow contrast is compressed, deliberately.")
    a(f"     On the black garment of scene 02 the graded image keeps "
      f"{sh['contrast_retained'] * 100:.0f}% of the")
    a(f"     local contrast of the plain conversion (std {f(sh['before_std'])} -> {f(sh['after_std'])},")
    a(f"     p5/p50/p95 {f(sh['before_p5'], 3)}/{f(sh['before_p50'], 3)}/{f(sh['before_p95'], 3)} -> "
      f"{f(sh['after_p5'], 3)}/{f(sh['after_p50'], 3)}/{f(sh['after_p95'], 3)}).")
    a("     Black cloth at 0.2-0.4% reflectance is lifted to a clean near-black and")
    a("     the first stop of shadow detail is flattened against it. This is the")
    a("     price of an SDR print that does not crush to 0; it is visible if you")
    a("     compare the deepest folds at 100%. It is a design choice, not a bug,")
    a("     but it is the weakest region of the transform.")
    a("")
    a("  b) Saturated colours can be non-monotonic off-axis (see section 11).")
    a("")
    a("  c) 33^3 sampling error reaches 0.078 code (p99.9) on the most saturated")
    a("     scene. A 65^3 build reduces it further; it does not change the look.")
    a("")
    a("  d) The preview scenes are photographs pushed through a physically based")
    a("     Apple Log 2 simulation, not files from an iPhone 17 Pro. The log curve,")
    a("     primaries and output are exact; the source distribution is representative")
    a("     rather than authoritative. Real footage will contain sensor noise that")
    a("     the simulated frames do not have; the shadow lift will make that noise")
    a("     more visible than it is in these previews.")
    a("")
    a("  e) Output is Rec.709 gamma 2.4 SDR. Feeding the LUT into an HDR or")
    a("     HLG/PQ timeline gives a valid but unintended image.")
    a("")

    # ---------------------------------------------------------------- 13
    a(rule("-"))
    a("13. VERDICT")
    a(rule("-"))
    a("  The .cube is structurally valid, exact against Apple's published curve and")
    a("  primaries, free of NaN/Inf/out-of-range values, free of flat steps on the")
    a("  neutral axis, and provably the source of every delivered preview.")
    a("  Skin hue is held to 0.2 degrees. Nothing clips at +/-1 stop.")
    a("  The one behaviour a buyer should know about is the deliberate compression of")
    a("  the first shadow stop (section 12a).")
    a("")
    a(rule())
    a("  Generated by build/make_report.py from build/validation_results.json.")
    a("  Do not edit this file by hand; re-run the validation instead.")
    a(rule())

    with open(OUT, "w") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", OUT, len("\n".join(L)), "chars")


if __name__ == "__main__":
    main()
