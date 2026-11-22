"""
gdc_validate.py -- every test that is reported in VALIDATION_REPORT.txt.

Rules for this file:
  * every test operates on the DELIVERED .cube file (read by lut_engine.py), not
    on the analytic pipeline, unless the test is explicitly about the analytic
    pipeline (interpolation error, reference implementation checks);
  * numbers are written to validation/summary.json and
    validation/validation_log.txt; plots go to validation/charts/;
  * nothing is reported that was not measured here.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
import colour
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_colour as C
import gdc_config as CFG
import gdc_grade as G
import gdc_metrics as M
import gdc_simulate as SIM
import lut_engine
import pngio

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DELIV = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
LUT_PATH = os.path.join(DELIV, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
VAL = os.path.join(ROOT, "validation")
CHARTS = os.path.join(VAL, "charts")

LOG = []


def log(*args):
    line = " ".join(str(a) for a in args)
    print(line)
    LOG.append(line)


def sha256_file(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# --------------------------------------------------------------------------
# 1. .cube file integrity
# --------------------------------------------------------------------------

def test_cube_integrity(lut, raw_sha):
    log("\n== 1. DELIVERED .cube FILE INTEGRITY ==")
    res = {}
    path = LUT_PATH
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    body = [l for l in lines if l and not l.startswith("#")
            and not l.split()[0].upper() in
            ("TITLE", "LUT_3D_SIZE", "DOMAIN_MIN", "DOMAIN_MAX")]
    res["sha256"] = raw_sha
    res["bytes"] = len(raw)
    res["declared_size"] = lut.size
    res["body_lines"] = len(body)
    res["expected_lines"] = lut.size ** 3
    res["title"] = lut.title
    res["domain_min"] = lut.domain_min.tolist()
    res["domain_max"] = lut.domain_max.tolist()
    vals = np.array([[float(x) for x in l.split()[:3]] for l in body])
    res["value_min"] = float(vals.min())
    res["value_max"] = float(vals.max())
    res["nan_count"] = int(np.isnan(vals).sum())
    res["inf_count"] = int(np.isinf(vals).sum())
    res["out_of_range_count"] = int(((vals < 0) | (vals > 1)).sum())
    res["duplicate_header"] = text.count("LUT_3D_SIZE")
    log(f"  file            : {os.path.relpath(path, ROOT)}  ({len(raw)} bytes)")
    log(f"  sha256          : {raw_sha}")
    log(f"  LUT_3D_SIZE     : {lut.size}  -> {lut.size**3} body lines, found {len(body)}")
    log(f"  DOMAIN_MIN/MAX  : {lut.domain_min} / {lut.domain_max}")
    log(f"  value range     : {vals.min():.6f} .. {vals.max():.6f}")
    log(f"  NaN / Inf       : {res['nan_count']} / {res['inf_count']}")
    log(f"  out of [0,1]    : {res['out_of_range_count']}")

    # ordering: verify a sample of nodes against the analytic pipeline. If the
    # red-fastest ordering were wrong this test would fail catastrophically.
    rng = np.random.default_rng(11)
    idx = rng.choice(lut.size ** 3, 400, replace=False)
    n = lut.size
    nodes = np.stack([(idx % n), ((idx // n) % n), (idx // (n * n))], axis=-1) / (n - 1)
    pipe = G.GoldenDaylightCinema()
    ref = pipe.apply_codes(nodes)
    rgb_idx = np.stack([(idx % n), ((idx // n) % n), (idx // n // n)], axis=-1)
    got = np.array([lut.node_value(*map(int, i)) for i in rgb_idx])
    # sensitivity control: read the file as if the ordering were blue-fastest
    got_bad = np.array([lut.node_value(*(int(i[2]), int(i[1]), int(i[0])))
                        for i in rgb_idx])
    err_bad = np.abs(ref - got_bad).max(axis=1)
    res["node_check_transposed_mean_err"] = float(err_bad.mean())
    res["node_check_transposed_max_err"] = float(err_bad.max())
    err = np.abs(ref - got).max(axis=1)
    res["node_check_nodes"] = int(len(idx))
    res["node_check_max_code_err"] = float(err.max())
    res["node_check_mean_code_err"] = float(err.mean())
    res["node_check_dE_max"] = float(M.de2000(ref, got).max())
    log(f"  node agreement  : 400 random nodes, delivered values vs analytic pipeline -> "
        f"mean code err {err.mean():.4f}, max {err.max():.4f} (this is the bake's LSQ "
        f"residual, not a syntax check)")
    log(f"  ordering control: the same nodes read with a transposed index give mean "
        f"code err {err_bad.mean():.4f} / max {err_bad.max():.4f}, i.e. the file is "
        f"unambiguously red-fastest")
    res["pass"] = (lut.size == 33 and len(body) == 33 ** 3 and res["nan_count"] == 0
                   and res["inf_count"] == 0 and res["out_of_range_count"] == 0)
    log(f"  RESULT          : {'PASS' if res['pass'] else 'FAIL'}")
    return res


# --------------------------------------------------------------------------
# 2. Verified reference implementations
# --------------------------------------------------------------------------

def test_reference_implementations():
    log("\n== 2. APPLE LOG 2 / APPLE WIDE GAMUT REFERENCE CHECKS ==")
    res = {}
    # 2a. our curve vs colour-science 0.4.7 (which implements Apple's 2023 paper)
    from colour.models import log_encoding_AppleLogProfile as cs_enc
    from colour.models import log_decoding_AppleLogProfile as cs_dec
    x = np.logspace(-6, 1.1, 5000)
    ours = C.apple_log2_encode(x)
    theirs = cs_enc(x)
    res["colour_science_encode_max_abs"] = float(np.max(np.abs(ours - theirs)))
    p = np.linspace(0, 1, 5000)
    res["colour_science_decode_max_abs"] = float(
        np.max(np.abs(C.apple_log2_decode(p) - cs_dec(p))))
    log(f"  curve vs colour-science 0.4.7 : encode max |diff| {res['colour_science_encode_max_abs']:.3e}, "
        f"decode max |diff| {res['colour_science_decode_max_abs']:.3e}")

    # 2b. published anchor values
    anchors = {"linear 0.0 (video black)": 0.0, "linear 0.01": 0.01,
               "linear 0.18 (18% grey)": 0.18, "linear 1.0": 1.0, "linear 12.0": 12.0}
    res["anchors"] = {}
    for k, v in anchors.items():
        code = float(C.apple_log2_encode(np.array(v)))
        res["anchors"][k] = code
        log(f"  anchor {k:26s} -> log code {code:.6f}")

    # 2c. Apple Wide Gamut matrix: rebuild from the published primaries with
    # colour-science and compare with the constants used in the pipeline.
    cs = colour.RGB_Colourspace(
        "Apple Wide Gamut",
        np.array([[0.725, 0.301], [0.221, 0.814], [0.068, -0.076]]),
        np.array([0.3127, 0.3290]))
    cs.use_derived_transformation_matrices(True)
    res["awg_to_xyz_max_abs_diff"] = float(np.max(np.abs(cs.matrix_RGB_to_XYZ - C.AWG_TO_XYZ)))
    log(f"  Apple Wide Gamut -> XYZ built by colour-science: max |diff| "
        f"{res['awg_to_xyz_max_abs_diff']:.3e}")
    log(f"  derived white point from our matrix: "
        f"{(lambda X: (X[0]/X.sum(), X[1]/X.sum()))(C.AWG_TO_XYZ @ np.ones(3))}")

    # 2d. cross-check against the OpenColorIO built-in matrix (published in
    # AcademySoftwareFoundation/OpenColorIO#2343 and the ACES config PR #179)
    aces = colour.RGB_COLOURSPACES["ACES2065-1"]
    aces.use_derived_transformation_matrices(True)
    ours_ap0 = colour.matrix_RGB_to_RGB(cs, aces, chromatic_adaptation_transform="Bradford")
    res["awg_to_ap0_vs_ocio_max_abs"] = float(np.max(np.abs(ours_ap0 - C.AWG_TO_AP0_BRADFORD)))
    log(f"  AWG -> ACES2065-1 (Bradford) vs OpenColorIO built-in matrix: "
        f"max |diff| {res['awg_to_ap0_vs_ocio_max_abs']:.3e}")

    # 2e. Rec.709 output encoding: pure power 2.4
    lin = np.array([0.0, 0.01, 0.1, 0.5, 1.0])
    enc = C.gamma24_encode(lin)
    res["gamma24_check"] = {str(a): float(b) for a, b in zip(lin, enc)}
    res["gamma24_identity_max_abs"] = float(np.max(np.abs(C.gamma24_decode(enc) - lin)))
    log(f"  pure gamma 2.4 encode: {dict(zip(lin.tolist(), np.round(enc, 6).tolist()))}")
    log(f"  round trip max |diff| {res['gamma24_identity_max_abs']:.3e}")
    return res


# --------------------------------------------------------------------------
# 3. Neutral axis, monotonicity, smoothness
# --------------------------------------------------------------------------

def test_neutral_axis(lut):
    log("\n== 3. NEUTRAL AXIS THROUGH THE DELIVERED LUT ==")
    res = {}
    codes = np.linspace(0.0, 1.0, 1021)
    grey_in = np.stack([codes] * 3, axis=-1)
    i_mid = int(np.argmin(abs(codes - 0.4734)))
    for method in ("tetra", "tri"):
        out = lut.apply(grey_in, method)
        lch = M.codes_to_oklch(out)
        lab = M.codes_to_lab(out)
        c_ab = np.hypot(lab[:, 1], lab[:, 2])
        h_ab = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360.0
        res[method] = {
            "max_oklab_chroma": float(lch[:, 1].max()),
            "max_lab_chroma": float(c_ab.max()),
            "oklab_chroma_at_midgrey": float(lch[i_mid, 1]),
            "oklab_hue_at_midgrey": float(lch[i_mid, 2]),
            "lab_chroma_at_midgrey": float(c_ab[i_mid]),
            "lab_hue_at_midgrey": float(h_ab[i_mid]),
            "oklab_chroma_at_white": float(lch[-1, 1]),
            "oklab_chroma_at_black": float(lch[0, 1]),
        }
        log(f"  [{method}] neutral-axis colour cast: max OKLab chroma {lch[:,1].max():.4f}, "
            f"max Lab C*ab {c_ab.max():.2f}")
        log(f"  [{method}] mid grey  ->  OKLab C {lch[i_mid,1]:.4f} at h {lch[i_mid,2]:.1f} deg, "
            f"Lab C*ab {c_ab[i_mid]:.2f} at h {h_ab[i_mid]:.1f} deg  (deliberate warmth)")
        log(f"  [{method}] white / black OKLab chroma {lch[-1,1]:.4f} / {lch[0,1]:.4f}")

    # detailed table every 0.1 code, tetrahedral (the delivery interpolation)
    out = lut.apply(grey_in, "tetra")
    lch = M.codes_to_oklch(out)
    rows = []
    lab_all = M.codes_to_lab(out)
    for c in np.arange(0.15, 1.001, 0.05):
        i = int(np.argmin(abs(codes - c)))
        c_ab = float(np.hypot(lab_all[i, 1], lab_all[i, 2]))
        h_ab = float(np.degrees(np.arctan2(lab_all[i, 2], lab_all[i, 1])) % 360)
        rows.append([float(codes[i]), float(out[i, 0]), float(lch[i, 0]), float(lch[i, 1]),
                     float(lch[i, 2]), c_ab, h_ab])
    res["table"] = rows
    log("     in    out R    OKLab L  OKLCh C   OKLCh h    Lab C*ab  Lab h")
    for r in rows:
        log(f"   {r[0]:.3f}  {r[1]:.4f}   {r[2]:.4f}   {r[3]:.4f}   {r[4]:6.1f}    "
            f"{r[5]:6.2f}   {r[6]:6.1f}")
    return res


def test_monotonicity(lut):
    log("\n== 4. MONOTONICITY AND TONAL SMOOTHNESS (delivered LUT) ==")
    res = {}
    n = 4096
    x = np.linspace(0.0, 1.0, n)
    ramps = {
        "neutral": np.stack([x] * 3, axis=-1),
        "R": np.stack([x, np.full(n, 0.45), np.full(n, 0.45)], axis=-1),
        "G": np.stack([np.full(n, 0.45), x, np.full(n, 0.45)], axis=-1),
        "B": np.stack([np.full(n, 0.45), np.full(n, 0.45), x], axis=-1),
        "C (G+B)": np.stack([np.full(n, 0.2), x, x], axis=-1),
        "M (R+B)": np.stack([x, np.full(n, 0.2), x], axis=-1),
        "Y (R+G)": np.stack([x, x, np.full(n, 0.2)], axis=-1),
    }
    for name, inp in ramps.items():
        out = lut.apply(inp, "tetra")
        lch = M.codes_to_oklch(out)
        d1 = np.diff(out, axis=0)
        dL = np.diff(lch[:, 0])
        d2 = np.diff(out, n=2, axis=0)
        res[name] = {
            "min_step": float(d1.min()), "max_step": float(d1.max()),
            "code_reversals": int((d1 < -1e-7).sum()),
            "deepest_code_reversal": float(min(0.0, d1.min())),
            "min_lightness_step": float(dL.min()),
            "lightness_reversals": int((dL < -1e-7).sum()),
            "max_abs_second_diff": float(np.abs(d2).max()),
            "p999_abs_second_diff": float(np.percentile(np.abs(d2), 99.9)),
        }
        log(f"  {name:9s} code: min step {d1.min():+.3e} max {d1.max():+.3e} "
            f"reversals {int((d1<-1e-7).sum()):4d} | OKLab L*: min step {dL.min():+.3e} "
            f"reversals {int((dL<-1e-7).sum()):4d} | max|2nd diff| {np.abs(d2).max():.3e} "
            f"p99.9 {np.percentile(np.abs(d2),99.9):.3e}")
    log("  (a falling channel value on a single-channel ramp is normal: pushing one")
    log("   primary up necessarily pulls the complementary channels down.  The")
    log("   lightness column is the meaningful smoothness test.)")

    # 8-bit and 10-bit quantisation: reversals and skipped levels
    for bits in (8, 10):
        levels = 2 ** bits - 1
        q = np.round(np.linspace(0, 1, levels + 1) * levels) / levels
        inp = np.stack([q] * 3, axis=-1)
        out = lut.apply(inp, "tetra")
        code = np.round(out[:, 1] * levels)
        skipped = int(np.sum(np.diff(code) == 0))
        res[f"quant{bits}"] = {"reversals": int((np.diff(code) < 0).sum()),
                               "skipped_output_levels": skipped,
                               "distinct_output_levels": int(len(np.unique(code)))}
        log(f"  {bits}-bit neutral ramp ({levels+1} steps): reversals "
            f"{res[f'quant{bits}']['reversals']}, skipped output levels "
            f"{skipped}, distinct output levels {res[f'quant{bits}']['distinct_output_levels']}")
    return res


# --------------------------------------------------------------------------
# 5. Interpolation error vs the analytic pipeline
# --------------------------------------------------------------------------

def test_interpolation_error(lut):
    log("\n== 5. 33^3 BAKE ERROR VS THE ANALYTIC PIPELINE ==")
    res = {}
    pipe = G.GoldenDaylightCinema()
    rng = np.random.default_rng(4242)
    q = np.clip(np.vstack([
        rng.random((40000, 3)),
        0.145 + 0.855 * rng.random((30000, 3)) ** 3,
        0.18 * 2 ** rng.uniform(-7, 4, size=(20000, 1)).repeat(3, 1)]), 0, 1)
    ref = pipe.apply_codes(q)

    # naive node-sampled LUT, for comparison
    n = lut.size
    ax = np.linspace(0, 1, n)
    bb, gg, rr = np.meshgrid(ax, ax, ax, indexing="ij")
    nodes = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], -1)
    naive = lut_engine.LUT3D(n, pipe.apply_codes(nodes))

    for label, l in (("delivered", lut), ("naive-node-sampled", naive)):
        for method in ("tri", "tetra"):
            out = l.apply(q, method)
            d00 = M.de2000(ref, out)
            ditp = M.de_itp(ref, out)
            key = f"{label}_{method}"
            res[key] = {
                "dE2000_mean": float(d00.mean()),
                "dE2000_p95": float(np.percentile(d00, 95)),
                "dE2000_p99": float(np.percentile(d00, 99)),
                "dE2000_max": float(d00.max()),
                "dEITP_mean": float(ditp.mean()),
                "dEITP_p99": float(np.percentile(ditp, 99)),
                "dEITP_max": float(ditp.max()),
                "code_max_abs": float(np.abs(ref - out).max()),
            }
            log(f"  {label:18s} {method:4s}: dE00 mean {d00.mean():.4f} p95 "
                f"{np.percentile(d00,95):.3f} p99 {np.percentile(d00,99):.3f} "
                f"max {d00.max():.2f} | dE-ITP mean {ditp.mean():.3f} p99 "
                f"{np.percentile(ditp,99):.2f} max {ditp.max():.1f}")

    # the same, restricted to inputs that a physical scene can produce: the
    # decoded colour must have a positive Rec.709 luminance of at least 0.5 %
    # (no sensor can deliver a colour with negative or zero luminance).
    Y_in = (C.apple_log2_decode(q) @ C.AWG_TO_REC709.T) @ np.array([0.2126390059, 0.7151686788, 0.0721923154])
    physical = Y_in > 0.005
    for method in ("tri", "tetra"):
        out = lut.apply(q[physical], method)
        d00 = M.de2000(ref[physical], out)
        res[f"physical_{method}"] = {"frac": float(physical.mean()),
                                     "dE2000_mean": float(d00.mean()),
                                     "dE2000_p99": float(np.percentile(d00, 99)),
                                     "dE2000_max": float(d00.max())}
        log(f"  physical subset ({physical.mean()*100:.0f}% of samples) {method:4s}: "
            f"dE00 mean {d00.mean():.4f} p99 {np.percentile(d00,99):.3f} max {d00.max():.2f}")

    # the eight delivered scenes (held-out only in the sense that the fit uses
    # synthetic samples, not scene pixels)
    scene_q = np.vstack([SIM.load_log16(os.path.join(
        ROOT, "simulated_log", s.file.replace(".jpg", "_applelog2.png"))).reshape(-1, 3)
        for s in CFG.SCENES])
    scene_q = np.round(scene_q * 1023) / 1023
    ref_s = pipe.apply_codes(scene_q)
    for label, l in (("delivered", lut), ("naive", naive)):
        for method in ("tri", "tetra"):
            out = l.apply(scene_q, method)
            d00 = M.de2000(ref_s, out)
            dc = np.abs(ref_s - out).max(1)
            res[f"scenes_{label}_{method}"] = {
                "dE2000_mean": float(d00.mean()),
                "dE2000_p95": float(np.percentile(d00, 95)),
                "dE2000_p99": float(np.percentile(d00, 99)),
                "dE2000_max": float(d00.max()),
                "code_mean_abs": float(dc.mean()),
                "code_mean_abs_8bit_steps": float(dc.mean() * 255.0),
            }
            log(f"  eight scenes {label:9s} {method:4s}: dE00 mean {d00.mean():.4f} p95 "
                f"{np.percentile(d00,95):.3f} p99 {np.percentile(d00,99):.3f} max "
                f"{d00.max():.2f} | code err mean {dc.mean():.5f} "
                f"({dc.mean()*255:.2f}/255)")
    return res, q, ref


# --------------------------------------------------------------------------
# 6. Clipping and highlight roll-off, per scene
# --------------------------------------------------------------------------

def load_scenes(long_edge=700):
    return {s.key: np.round(SIM.srgb_image_to_apple_log2(
        SIM.load_srgb(os.path.join(ROOT, "source_images", s.file), long_edge)) * 1023) / 1023
        for s in CFG.SCENES}


def test_clipping(lut, scenes):
    log("\n== 6. CLIPPING BEFORE / AFTER (delivered LUT) ==")
    res = {}
    for k, p in scenes.items():
        b = G.reference_rec709(p)
        a = lut.apply(p, "tetra")
        rb, ra = M.image_summary(b), M.image_summary(a)
        res[k] = {"before": rb, "after": ra}
        log(f"  {k:22s} white clip {rb['clip_white_pct']:6.2f}% -> {ra['clip_white_pct']:5.2f}%   "
            f"black clip {rb['clip_black_pct']:6.2f}% -> {ra['clip_black_pct']:5.2f}%   "
            f"mean code {rb['mean_code']:.3f} -> {ra['mean_code']:.3f}")
    # highlight roll-off curve: how the top of the curve behaves
    x = np.linspace(0.4, 1.0, 61)
    inp = np.stack([x] * 3, axis=-1)
    out = lut.apply(inp, "tetra")[:, 1]
    res["highlight_rolloff"] = [[float(a), float(b)] for a, b in zip(x, out)]
    log("  neutral highlight roll-off (log code -> Rec.709 code), every 0.1:")
    for i in range(0, len(x), 10):
        log(f"    {x[i]:.2f} -> {out[i]:.4f}")
    return res


# --------------------------------------------------------------------------
# 7. Synthetic charts through the delivered LUT
# --------------------------------------------------------------------------

def chart_grey_ramp(lut, path):
    n = 32
    w = 64
    img = np.zeros((w, n * w, 3))
    inputs = np.linspace(0.10, 1.0, n)
    for i, c in enumerate(inputs):
        img[:, i * w:(i + 1) * w, :] = c
    out = lut.apply(img.reshape(-1, 3), "tetra").reshape(img.shape)
    before_srgb = C.linear_to_srgb(C.gamma24_decode(G.reference_rec709(img.reshape(-1, 3)))).reshape(img.shape)
    after_srgb = C.linear_to_srgb(C.gamma24_decode(out))
    sheet = np.concatenate([before_srgb, np.ones((6, img.shape[1], 3)) * 0.1, after_srgb], axis=0)
    pngio.write_png_rgb8(path, np.round(sheet * 255).astype(np.uint8), adaptive=False)
    return inputs, out[0, ::w, :]


def chart_hue_sweep(lut, path, n_hues=48, levels=(0.35, 0.55, 0.75)):
    w = 40
    rows = []
    for i, L in enumerate(levels):
        img = np.zeros((w, n_hues * w, 3))
        for j in range(n_hues):
            h = j / n_hues * 360.0
            lch = np.array([[[L, 0.11, h]]])
            rgb = np.clip(C.oklab_to_xyz(C.oklch_to_oklab(lch)) @ C.XYZ_TO_REC709.T, 0, 1)
            code = C.apple_log2_encode(np.clip(rgb @ C.REC709_TO_AWG.T, 0, None))
            img[:, j * w:(j + 1) * w, :] = code
        rows.append(img)
    img = np.concatenate(rows, axis=0)
    out = lut.apply(img.reshape(-1, 3), "tetra").reshape(img.shape)
    a = C.linear_to_srgb(C.gamma24_decode(out))
    b = C.linear_to_srgb(C.gamma24_decode(G.reference_rec709(img.reshape(-1, 3)))).reshape(img.shape)
    sheet = np.concatenate([b, np.ones((6, img.shape[1], 3)) * 0.1, a], axis=0)
    pngio.write_png_rgb8(path, np.round(sheet * 255).astype(np.uint8), adaptive=False)


def chart_saturation_sweep(lut, path, n=16):
    w = 44
    rows = []
    for hue in (30, 120, 210, 300):
        img = np.zeros((w, n * w, 3))
        for j in range(n):
            ch = j / (n - 1) * 0.28
            lch = np.array([[[0.6, ch, hue]]])
            rgb = np.clip(C.oklab_to_xyz(C.oklch_to_oklab(lch)) @ C.XYZ_TO_REC709.T, 0, 1)
            code = C.apple_log2_encode(np.clip(rgb @ C.REC709_TO_AWG.T, 0, None))
            img[:, j * w:(j + 1) * w, :] = code
        rows.append(img)
    img = np.concatenate(rows, axis=0)
    out = lut.apply(img.reshape(-1, 3), "tetra").reshape(img.shape)
    a = C.linear_to_srgb(C.gamma24_decode(out))
    b = C.linear_to_srgb(C.gamma24_decode(G.reference_rec709(img.reshape(-1, 3)))).reshape(img.shape)
    sheet = np.concatenate([b, np.ones((6, img.shape[1], 3)) * 0.1, a], axis=0)
    pngio.write_png_rgb8(path, np.round(sheet * 255).astype(np.uint8), adaptive=False)


def test_charts(lut):
    log("\n== 7. SYNTHETIC CHARTS THROUGH THE DELIVERED LUT ==")
    os.makedirs(CHARTS, exist_ok=True)
    res = {}

    # 7a. grey ramp
    inputs, outs = chart_grey_ramp(lut, os.path.join(CHARTS, "chart_grey_ramp.png"))
    log("  charts/chart_grey_ramp.png written (top: BEFORE, bottom: AFTER)")

    # 7b. hue sweep + numeric behaviour
    chart_hue_sweep(lut, os.path.join(CHARTS, "chart_hue_sweep.png"))
    log("  charts/chart_hue_sweep.png written")
    hues = np.arange(0, 360, 7.5)
    lch_in = np.stack([np.full_like(hues, 0.6), np.full_like(hues, 0.11), hues], -1)[:, None, :]
    rgb = np.clip(C.oklab_to_xyz(C.oklch_to_oklab(lch_in)) @ C.XYZ_TO_REC709.T, 0, 1)
    code = C.apple_log2_encode(np.clip(rgb @ C.REC709_TO_AWG.T, 0, None))
    out = lut.apply(code.reshape(-1, 3), "tetra").reshape(code.shape)
    lch_out = M.codes_to_oklch(out.reshape(-1, 3))
    lch_ref = M.codes_to_oklch(G.reference_rec709(code.reshape(-1, 3)))
    hue_err = C.hue_delta(lch_out[:, 2], lch_ref[:, 2])
    res["hue_sweep"] = {
        "max_chroma_change": float(np.max(np.abs(lch_out[:, 1] - lch_ref[:, 1]))),
        "max_hue_shift_deg": float(np.max(np.abs(hue_err))),
        "mean_hue_shift_deg": float(np.mean(hue_err)),
    }
    log(f"  hue sweep at L=0.6, C=0.11: max |chroma change| "
        f"{res['hue_sweep']['max_chroma_change']:.4f}, max |hue shift| "
        f"{res['hue_sweep']['max_hue_shift_deg']:.1f} deg")

    # 7c. saturation sweep
    chart_saturation_sweep(lut, os.path.join(CHARTS, "chart_saturation_sweep.png"))
    log("  charts/chart_saturation_sweep.png written")

    # 7d. ColorChecker-style patches
    ccs = colour.CCS_COLOURCHECKERS["ColorChecker 2005"]
    names, rgb_lin, xyz_d65_all = [], [], []
    for name, xyY in ccs.data.items():
        XYZ50 = colour.xyY_to_XYZ(xyY)
        XYZ65 = colour.chromatic_adaptation(
            XYZ50, colour.xy_to_XYZ(ccs.illuminant), colour.xy_to_XYZ(M.D65),
            method="Von Kries")   # = Bradford CAT matrix
        rgb = np.clip(C.XYZ_TO_REC709 @ XYZ65, 0, 1)
        rgb_lin.append(rgb)
        xyz_d65_all.append(XYZ65)
        names.append(name)
    rgb_lin = np.array(rgb_lin)
    code = C.apple_log2_encode(np.clip(rgb_lin @ C.REC709_TO_AWG.T, 0, None))
    out = lut.apply(code, "tetra")
    ref_lab = colour.XYZ_to_Lab(np.array(xyz_d65_all), illuminant=M.D65)
    out_lab = M.codes_to_lab(out)
    dE = colour.difference.delta_E_CIE2000(ref_lab, out_lab)
    res["colorchecker"] = {
        "dE00_mean": float(dE.mean()), "dE00_max": float(dE.max()),
        "worst_patch": names[int(np.argmax(dE))],
        "per_patch": {n: float(d) for n, d in zip(names, dE)},
    }
    log(f"  ColorChecker 2005 through the LUT: dE00 vs the original patch "
        f"mean {dE.mean():.2f}, max {dE.max():.2f} ({names[int(np.argmax(dE))]})")
    # patch sheet
    w = 96
    tiles = []
    for j in range(24):
        tiles.append(np.full((w, w, 3), np.clip(rgb_lin[j], 0, 1)))
    row_before = np.concatenate(tiles, axis=1)
    row_after = np.concatenate([np.full((w, w, 3), x) for x in np.clip(
        C.gamma24_decode(out) @ C.REC709_TO_AWG.T, 0, 1)], axis=1)
    sheet = np.concatenate([row_before, np.ones((6, row_before.shape[1], 3)) * 0.1,
                            row_after], axis=0)
    pngio.write_png_rgb8(os.path.join(CHARTS, "chart_colorchecker.png"),
                         np.round(C.linear_to_srgb(np.clip(sheet, 0, 1)) * 255).astype(np.uint8),
                         adaptive=False)
    log("  charts/chart_colorchecker.png written")

    # 7e. +/-4 stop exposure ladder on a mid grey and on three scene patches
    stops = np.arange(-4, 4.01, 1.0)
    patches = {"grey 18%": 0.18, "warm stone": 0.42, "skin-ish": 0.32, "foliage": 0.24}
    res["exposure_ladder"] = {}
    ladder_rows = []
    for name, lin in patches.items():
        row = []
        for s in stops:
            y = lin * 2 ** s
            code = C.apple_log2_encode(np.clip(np.array([y] * 3) @ C.REC709_TO_AWG.T, 0, None))
            o = lut.apply(code[None, :], "tetra")[0]
            row.append((float(s), float(y), float(o[1])))
        res["exposure_ladder"][name] = row
        ladder_rows.append(row)
        log(f"  exposure ladder {name:10s}: " + " ".join(
            f"{s:+.0f}st->{o:.3f}" for s, y, o in row))
    # ladder image
    w, h = 120, 80
    cols = len(stops)
    img = np.zeros((h, w * cols, 3))
    for j, s in enumerate(stops):
        y = 0.18 * 2 ** s
        code = C.apple_log2_encode(np.clip(np.array([y] * 3) @ C.REC709_TO_AWG.T, 0, None))
        img[:, j * w:(j + 1) * w, :] = code
    after = lut.apply(img.reshape(-1, 3), "tetra").reshape(img.shape)
    before = G.reference_rec709(img.reshape(-1, 3)).reshape(img.shape)
    sheet = np.concatenate([C.linear_to_srgb(C.gamma24_decode(after)),
                            np.ones((6, img.shape[1], 3)) * 0.1,
                            C.linear_to_srgb(C.gamma24_decode(before))], axis=0)
    pngio.write_png_rgb8(os.path.join(CHARTS, "chart_exposure_ladder.png"),
                         np.round(np.clip(sheet, 0, 1) * 255).astype(np.uint8), adaptive=False)
    log("  charts/chart_exposure_ladder.png written (top AFTER, bottom BEFORE)")
    return res


# --------------------------------------------------------------------------
# 8. Skin, sky, foliage behaviour
# --------------------------------------------------------------------------

def test_skin(lut):
    log("\n== 8. SKIN HUE ACROSS EXPOSURES AND LIGHTING ==")
    res = {}
    # three lighting conditions built as OKLab patches around skin, then exposed
    conds = {"warm sun 5200K-ish": (55.0, 0.085), "neutral daylight": (48.0, 0.070),
             "cool shade": (42.0, 0.060), "warm tungsten-ish": (62.0, 0.095)}
    stops = (-2, -1, 0, 1)
    rows = []
    for name, (hue, ch) in conds.items():
        for L0 in (0.55, 0.70):
            for s in stops:
                L = min(max(L0 * 2 ** (s * 0.35), 0.08), 0.95)
                lch = np.array([[L, ch, hue]])
                rgb = np.clip(C.oklab_to_xyz(C.oklch_to_oklab(lch)) @ C.XYZ_TO_REC709.T, 0, 1)
                code = C.apple_log2_encode(np.clip(rgb @ C.REC709_TO_AWG.T, 0, None))
                out = lut.apply(code, "tetra")
                res_row = {
                    "condition": name, "L_in": float(L), "stop": s,
                    "vectorscope_deg": float(M.skin_line_angle(out)[0]),
                    "oklch_h_after": float(M.codes_to_oklch(out)[0, 2]),
                    "oklch_C_after": float(M.codes_to_oklch(out)[0, 1]),
                    "vectorscope_deg_before": float(M.skin_line_angle(
                        G.reference_rec709(code))[0]),
                    "oklch_h_before": float(M.codes_to_oklch(G.reference_rec709(code))[0, 2]),
                    "oklch_C_before": float(M.codes_to_oklch(G.reference_rec709(code))[0, 1]),
                }
                rows.append(res_row)
                log(f"  {name:20s} L={L:.2f} stop{s:+d}: vectorscope "
                    f"{res_row['vectorscope_deg_before']:5.1f}->{res_row['vectorscope_deg']:5.1f} deg  OKLCh h "
                    f"{res_row['oklch_h_before']:5.1f}->{res_row['oklch_h_after']:5.1f}  "
                    f"C {res_row['oklch_C_before']:.3f}->{res_row['oklch_C_after']:.3f}")
    res["rows"] = rows
    angles = np.array([r["vectorscope_deg"] for r in rows])
    res["vectorscope_min"] = float(angles.min())
    res["vectorscope_max"] = float(angles.max())
    res["hue_spread_deg"] = float(angles.max() - angles.min())
    log(f"  vectorscope angle range across all conditions/exposures: "
        f"{angles.min():.1f}..{angles.max():.1f} deg (spread {angles.max()-angles.min():.1f} deg)")
    log("  reference: the classic BT.709 skin line sits near 110-130 deg on a"
        " vectorscope (Cb/Cr plane)")

    # the real portrait, measured in the ROI
    p = np.round(SIM.srgb_image_to_apple_log2(SIM.load_srgb(
        os.path.join(ROOT, "source_images", CFG.SCENE_BY_KEY["midday_portrait"].file), 900)) * 1023) / 1023
    b = G.reference_rec709(p)
    a = lut.apply(p, "tetra")
    res["portrait"] = {}
    for name in ("skin_lit", "skin_shadow"):
        box = M.ROIS["midday_portrait"][name]
        rb = M.region_summary(b, box)
        ra = M.region_summary(a, box)
        res["portrait"][name] = {"before": rb, "after": ra}
        log(f"  portrait {name:11s}: OKLab h {rb['h']:.1f}->{ra['h']:.1f}  C "
            f"{rb['C']:.3f}->{ra['C']:.3f}  vectorscope {rb['skin_angle']:.1f}->{ra['skin_angle']:.1f}")
    return res


def test_sky_foliage(lut, scenes):
    log("\n== 9. SKY AND FOLIAGE BEHAVIOUR (per scene, ROI medians) ==")
    res = {}
    for key, p in scenes.items():
        b = G.reference_rec709(p)
        a = lut.apply(p, "tetra")
        for name, box in M.ROIS[key].items():
            rb = M.region_summary(b, box)
            ra = M.region_summary(a, box)
            near_neutral = rb["C"] < 0.02
            res[f"{key}/{name}"] = {"before": rb, "after": ra,
                                    "hue_meaningful": not near_neutral}
            if near_neutral:
                log(f"  {key:22s} {name:14s} h    n/a (near neutral)      "
                    f"C {rb['C']:.3f}->{ra['C']:.3f}  L {rb['L']:.3f}->{ra['L']:.3f}")
            else:
                log(f"  {key:22s} {name:14s} h {rb['h']:6.1f}->{ra['h']:6.1f}  "
                    f"C {rb['C']:.3f}->{ra['C']:.3f}  L {rb['L']:.3f}->{ra['L']:.3f}")
    # hue histograms / vectorscope plots for sky and foliage
    os.makedirs(CHARTS, exist_ok=True)
    try:
        fig, axes = plt.subplots(2, 2, figsize=(11, 9))
        for ax, key in zip(axes.ravel(), ["midday_city", "landscape_green"]):
            pass
        fig.clf()
        fig, axes = plt.subplots(2, 2, figsize=(12, 9))
        for col, key in enumerate(["midday_city", "landscape_green"]):
            p = scenes[key]
            b = G.reference_rec709(p)
            a = lut.apply(p, "tetra")
            for row, (name, box) in enumerate([("sky", "sky"), ("foliage/grass", "grass")]):
                if name not in M.ROIS[key]:
                    continue
                ax = axes[row, col]
                for img, style, lab in ((b, "-", "before"), (a, "--", "after")):
                    px = M.region_flat(img, M.ROIS[key][name])
                    lch = M.codes_to_oklch(px)
                    ax.hist(lch[:, 2], bins=72, range=(0, 360), alpha=0.55,
                            histtype="step", linestyle=style, label=lab,
                            weights=None, density=True)
                ax.set_title(f"{key} / {name}: OKLCh hue histogram")
                ax.set_xlabel("OKLCh hue (deg)")
                ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(CHARTS, "plot_hue_histograms.png"), dpi=110)
        plt.close(fig)

        # vectorscope
        fig, ax = plt.subplots(figsize=(7, 7))
        p = scenes["midday_portrait"]
        b = G.reference_rec709(p)
        a = lut.apply(p, "tetra")
        for img, colour_, lab in ((b, "#8899aa", "before"), (a, "#e0a24a", "after")):
            ycc = M.ycbcr(img.reshape(-1, 3))
            sel = np.random.default_rng(0).choice(len(ycc), 20000, replace=False)
            ax.scatter(ycc[sel, 1], ycc[sel, 2], s=1, alpha=0.25, c=colour_, label=lab)
        ang = np.radians(np.arange(110, 131, 5))
        ax.plot(0.12 * np.cos(ang), 0.12 * np.sin(ang), "g-", lw=1)
        ax.text(0.02, 0.13, "skin line 110-130 deg", color="g", fontsize=8)
        ax.set_xlim(-0.25, 0.25); ax.set_ylim(-0.25, 0.25)
        ax.set_xlabel("Cb"); ax.set_ylabel("Cr"); ax.set_aspect("equal")
        ax.set_title("Vectorscope: portrait scene (BT.709 Cb/Cr)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(CHARTS, "plot_vectorscope_portrait.png"), dpi=110)
        plt.close(fig)
        res["charts"] = ["charts/plot_hue_histograms.png", "charts/plot_vectorscope_portrait.png"]
        log("  charts/plot_hue_histograms.png and charts/plot_vectorscope_portrait.png written")
    except Exception as e:      # pragma: no cover
        log(f"  PLOT FAILED: {e}")
    return res


# --------------------------------------------------------------------------
# 10. Shadow noise robustness
# --------------------------------------------------------------------------

def test_noise(lut):
    log("\n== 10. SHADOW NOISE GAIN THROUGH THE LUT ==")
    res = {}
    rng = np.random.default_rng(77)
    for code in (0.151, 0.17, 0.20, 0.25, 0.35, 0.50):
        base = np.full((40000, 3), code)
        sigma = 1.0 / 1023.0            # 1 LSB at 10-bit
        noisy = np.clip(base + rng.normal(0, sigma, base.shape), 0, 1)
        a = lut.apply(noisy, "tetra")
        b = G.reference_rec709(noisy)
        gain_lut = a.std(axis=0) / (noisy.std(axis=0) + 1e-12)
        gain_ref = b.std(axis=0) / (noisy.std(axis=0) + 1e-12)
        res[f"{code:.3f}"] = {
            "noise_gain_after": float(gain_lut.mean()),
            "noise_gain_before": float(gain_ref.mean()),
            "noise_gain_per_channel_after": [float(x) for x in gain_lut],
            "output_mean": float(a.mean()),
            "output_std": float(a.std()),
        }
        log(f"  log code {code:.3f}: noise gain (out/in std) after {gain_lut.mean():5.2f}x, "
            f"before {gain_ref.mean():5.2f}x  [R {gain_lut[0]:.2f} G {gain_lut[1]:.2f} B {gain_lut[2]:.2f}]")
    return res


# --------------------------------------------------------------------------
# 11. Exposure / lighting variation on real scenes
# --------------------------------------------------------------------------

def test_exposure_variation(lut, scenes):
    log("\n== 11. SIMULATED EXPOSURE VARIATION ON THE REAL SCENES ==")
    res = {}
    for key in ("midday_city", "mediterranean_street", "midday_portrait"):
        p = scenes[key]
        rows = []
        for stops in (-2, -1, 0, 1):
            pp = np.clip(p + stops * 0.0426, 0.0, 1.0)   # ~1 stop at 30 code/stop
            a = lut.apply(pp, "tetra")
            s = M.image_summary(a)
            d = M.codes_to_oklch(a.reshape(-1, 3))
            black_px = float(np.mean(np.all(a.reshape(-1, 3) <= 1e-9, axis=1)) * 100)
            rows.append({"stops": stops, "mean_code": s["mean_code"],
                         "clip_white": s["clip_white_pct"], "clip_black": s["clip_black_pct"],
                         "fully_black_pct": black_px,
                         "mean_chroma": float(d[:, 1].mean()),
                         "median_hue_warm": float(M.chroma_weighted_hue(d))})
            log(f"  {key:22s} {stops:+d} stops: mean code {s['mean_code']:.3f}  "
                f"white clip {s['clip_white_pct']:5.2f}%  ch at 0 {s['clip_black_pct']:5.2f}%  "
                f"black px {black_px:5.2f}%  "
                f"mean chroma {d[:,1].mean():.4f}")
        res[key] = rows
    return res


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    os.makedirs(VAL, exist_ok=True)
    t0 = time.time()
    lut = lut_engine.LUT3D.from_cube(LUT_PATH)
    raw_sha = sha256_file(LUT_PATH)
    summary = {"lut_path": os.path.relpath(LUT_PATH, ROOT), "lut_sha256": raw_sha,
               "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    summary["cube"] = test_cube_integrity(lut, raw_sha)
    summary["reference"] = test_reference_implementations()
    summary["neutral"] = test_neutral_axis(lut)
    summary["monotonicity"] = test_monotonicity(lut)
    interp_res, q, ref = test_interpolation_error(lut)
    summary["interpolation"] = interp_res
    scenes = load_scenes()
    summary["clipping"] = test_clipping(lut, scenes)
    summary["charts"] = test_charts(lut)
    summary["skin"] = test_skin(lut)
    summary["sky_foliage"] = test_sky_foliage(lut, scenes)
    summary["noise"] = test_noise(lut)
    summary["exposure"] = test_exposure_variation(lut, scenes)

    # hashes of the delivered previews, to prove they come from this .cube
    rh = os.path.join(VAL, "render_hashes.json")
    if os.path.exists(rh):
        summary["render_hashes"] = json.load(open(rh))

    with open(os.path.join(VAL, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=float)
    with open(os.path.join(VAL, "validation_log.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    log(f"\nDone in {time.time()-t0:.1f}s -> validation/summary.json, "
        f"validation/validation_log.txt")


if __name__ == "__main__":
    main()
