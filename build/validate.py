#!/usr/bin/env python3
"""
Validation of the DELIVERED GOLDEN_DAYLIGHT_CINEMA.cube.

Everything here reads the .cube file from disk; nothing trusts the generator.
Results are written to build/validation_results.json and printed as text.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

import apple_log2 as al
import grade
import lut_io
import simulate
import render_previews as rp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
CUBE = os.path.join(PROJ, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
OUT_JSON = os.path.join(ROOT, "build", "validation_results.json")

RES = {}


def j(k, v):
    RES[k] = v
    print(f"{k}: {v}")


# ---------------------------------------------------------------------------
# 1. .cube syntax / integrity
# ---------------------------------------------------------------------------
def test_cube_file():
    raw = open(CUBE, "r", encoding="ascii", errors="strict").read()
    lines = raw.splitlines()
    header = {}
    rows = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        up = s.upper()
        if up.startswith("TITLE"):
            header["title"] = s
        elif up.startswith("LUT_3D_SIZE"):
            header["size"] = int(s.split()[1])
        elif up.startswith("DOMAIN_"):
            header[up.split()[0].lower()] = [float(x) for x in s.split()[1:]]
        elif up.startswith("LUT_1D_SIZE"):
            raise AssertionError("unexpected 1D LUT directive")
        else:
            parts = s.split()
            assert len(parts) == 3, f"row is not 3 numbers: {s!r}"
            rows.append([float(p) for p in parts])
    data = np.array(rows, dtype=np.float64)
    j("cube_title", header.get("title", "MISSING"))
    j("cube_lut_3d_size", header.get("size"))
    j("cube_domain_min", header.get("domain_min"))
    j("cube_domain_max", header.get("domain_max"))
    j("cube_data_rows", int(data.shape[0]))
    j("cube_expected_rows", header["size"] ** 3)
    j("cube_rows_ok", data.shape[0] == header["size"] ** 3)
    j("cube_nan_count", int(np.isnan(data).sum()))
    j("cube_inf_count", int(np.isinf(data).sum()))
    j("cube_min_value", float(data.min()))
    j("cube_max_value", float(data.max()))
    j("cube_out_of_range_count", int(((data < 0.0) | (data > 1.0)).sum()))
    j("cube_file_bytes", len(raw))
    j("cube_ascii_clean", True)
    return lut_io.read_cube(CUBE)


# ---------------------------------------------------------------------------
# 2. Apple Log 2 curve vs the white paper
# ---------------------------------------------------------------------------
def test_curve():
    rows = []
    for refl, (p_pub, c10) in al.WP_ENCODED_SIGNAL.items():
        p = float(al.encode(refl))
        rows.append(dict(reflectance=refl, code=p, published=p_pub, abs_err=abs(p - p_pub),
                         ten_bit=round(p * 1023), published_ten_bit=c10))
    j("curve_signal_table", rows)
    j("curve_signal_max_abs_err", max(r["abs_err"] for r in rows))

    stops = []
    for s, pub in al.WP_STOPS_TABLE.items():
        p = float(al.encode(0.18 * 2.0 ** s))
        stops.append(dict(stops=s, code=p, published=pub, abs_err=abs(p - pub)))
    j("curve_stops_table", stops)
    j("curve_stops_max_abs_err", max(r["abs_err"] for r in stops))

    grid = np.linspace(0.0, 1.0, 100001)
    rt = float(np.max(np.abs(al.encode(al.decode(grid)) - grid)))
    j("curve_roundtrip_max_err", rt)
    j("curve_pt", float(al.PT))
    j("curve_18pct_code", float(al.encode(0.18)))
    j("curve_zero_reflectance_code", float(al.encode(0.0)))


# ---------------------------------------------------------------------------
# 3. Apple Wide Gamut -> Rec.709
# ---------------------------------------------------------------------------
def test_gamut():
    M = al.AWG_TO_709
    j("gamut_matrix", M.tolist())
    j("gamut_row_sums", M.sum(axis=1).tolist())
    j("gamut_row_sum_max_dev", float(np.abs(M.sum(axis=1) - 1).max()))
    j("gamut_neutral_error", float(np.abs(M @ np.ones(3) - np.ones(3)).max()))
    j("gamut_inverse_max_err", float(np.abs(M @ np.linalg.inv(M) - np.eye(3)).max()))
    brad = al.bradford(al.APPLE_WIDE_GAMUT["white"], al.REC709["white"])
    j("bradford_d65_identity_max_dev", float(np.abs(brad - np.eye(3)).max()))
    # independent adaptation (CAT02) must give the same result for D65->D65
    cat02 = np.array([[0.7328, 0.4296, -0.1624], [-0.7036, 1.6975, 0.0061],
                      [0.0030, 0.0136, 0.9834]])
    ws = al.xy_to_XYZ(al.APPLE_WIDE_GAMUT["white"])
    wd = al.xy_to_XYZ(al.REC709["white"])
    cat02_m = np.linalg.inv(cat02) @ np.diag((cat02 @ wd) / (cat02 @ ws)) @ cat02
    j("cat02_vs_bradford_max_dev", float(np.abs(cat02_m - brad).max()))
    j("gamut_awg_to_aces_ap0", al.AWG_TO_AP0.tolist())
    # primaries land on their own XYZ coordinates
    prim_rows = []
    for i, name in enumerate(("R", "G", "B")):
        rgb = np.zeros(3)
        rgb[i] = 1.0
        xyz = rgb @ al.APPLEWG_TO_XYZ.T
        xy = xyz[:2] / xyz.sum()
        target = al.APPLE_WIDE_GAMUT[{"R": "red", "G": "green", "B": "blue"}[name]]
        prim_rows.append(dict(primary=name, xy=xy.tolist(), published=list(target),
                              max_err=float(np.abs(xy - np.array(target)).max())))
    j("gamut_primary_check", prim_rows)
    # clipping risk: how many LUT nodes are exactly 0/1
    lut = lut_io.read_cube(CUBE)
    j("lut_exact_zero_values", int((lut <= 0.0).sum()))
    j("lut_exact_one_values", int((lut >= 1.0).sum()))


# ---------------------------------------------------------------------------
# 4. Rec.709 gamma 2.4 output encoding
# ---------------------------------------------------------------------------
def test_output_encoding(lut):
    v = np.linspace(0, 1, 1001)
    neutral = np.stack([v, v, v], -1)
    out = lut_io.apply_lut(lut, neutral)
    # display-linear reached by the LUT must equal the analytic display values
    _, stages = grade.transform(neutral, return_stages=True)
    lin_from_lut = out ** 2.4
    err_lin = float(np.abs(lin_from_lut - stages["display"]).max())
    err_code = float(np.abs(out - grade.transform(neutral)).max())
    # at the 33 nodes the LUT must be exactly design_display ** (1/2.4)
    n = lut.shape[0]
    nv = np.linspace(0, 1, n)
    nneutral = np.stack([nv] * 3, -1)
    node_out = lut_io.apply_lut(lut, nneutral)
    _, node_st = grade.transform(nneutral, return_stages=True)
    j("output_gamma24_node_max_lin_err", float(np.abs(node_out ** 2.4 - node_st["display"]).max()))
    j("output_gamma24_max_lin_err", err_lin)
    j("output_neutral_ramp_max_code_err_vs_design", err_code)
    j("output_white_code_for_log1", float(out[-1].mean()))
    j("output_black_code_for_log0", float(out[0].mean()))
    j("output_gamma", 2.4)
    # exponent test: code^k for k=2.4 must linearise, k=2.2 must not
    mid = neutral[500]
    j("encoding_exponent_check", {
        "code": float(out[500].mean()),
        "linear_2.4": float(out[500].mean() ** 2.4),
        "linear_2.2": float(out[500].mean() ** 2.2),
    })


# ---------------------------------------------------------------------------
# 5. Neutral behaviour, monotonicity and smoothness
# ---------------------------------------------------------------------------
def test_neutral_smooth(lut):
    n = lut.shape[0]
    neutral = lut[np.arange(n), np.arange(n), np.arange(n)]
    mono = np.diff(neutral, axis=0)
    j("neutral_monotonic_all_channels", bool((mono >= -1e-9).all()))
    j("neutral_min_step_per_channel", float(np.min(mono)))
    j("neutral_backstep_count", int((mono < 0).sum()))
    steps = np.abs(mono).max(axis=1)
    j("neutral_max_step", float(steps.max()))
    j("neutral_step_max_index", int(steps.argmax()))
    d2 = np.abs(np.diff(neutral, 2, axis=0)).max(axis=1)
    j("neutral_max_second_difference", float(d2.max()))
    # colour drift of the neutral axis (how far from grey the LUT's greys are)
    dev = (neutral.max(axis=1) - neutral.min(axis=1))
    j("neutral_max_channel_spread", float(dev.max()))
    j("neutral_channel_spread_at_midgrey", float(dev[16]))
    j("neutral_ramp_sample", [[round(float(x), 5) for x in neutral[i]]
                              for i in (0, 4, 8, 12, 16, 20, 24, 28, 32)])
    # flat regions (plateaus) along the neutral axis
    flat = np.where(steps < 1e-6)[0]
    j("neutral_flat_steps_count", int(len(flat)))
    j("neutral_flat_steps_indices", flat.tolist())
    # per-axis monotonicity of the dominant channel
    viol = 0
    for axis in range(3):
        d = np.diff(lut, axis=axis)
        viol += int((d[..., axis] < -5e-4).sum())
    j("channel_monotonicity_violations", viol)
    j("channel_monotonicity_violations_frac", viol / (3 * 32 * n * n))


# ---------------------------------------------------------------------------
# 6. LUT fidelity vs the analytic transform on real scene pixels
# ---------------------------------------------------------------------------
def test_fidelity(lut):
    rows = []
    for num, slug, title, fname in rp.SCENES:
        rgb = np.asarray(Image.open(os.path.join(rp.SRC, fname)).convert("RGB"))
        code, _ = simulate.simulate_apple_log2(rgb)
        flat = code.reshape(-1, 3)
        d = np.abs(lut_io.apply_lut(lut, flat) - grade.transform(flat)).max(axis=1)
        rows.append(dict(scene=slug, max=float(d.max()), p999=float(np.percentile(d, 99.9)),
                         p99=float(np.percentile(d, 99)), mean=float(d.mean())))
    j("fidelity_scene_table", rows)
    j("fidelity_overall_mean", float(np.mean([r["mean"] for r in rows])))


# ---------------------------------------------------------------------------
# 7. AFTER renders really come from the delivered cube
# ---------------------------------------------------------------------------
def test_renders_from_cube(lut):
    rows = []
    worst = 0.0
    for num, slug, title, fname in rp.SCENES:
        rgb = np.asarray(Image.open(os.path.join(rp.SRC, fname)).convert("RGB"))
        code, _ = simulate.simulate_apple_log2(rgb)
        expect_img = rp.to_img(lut_io.apply_lut(lut, code))
        factor = min(2.0, rp.TARGET_W / rgb.shape[1])
        expect_img = rp.upscale(expect_img, factor)
        expect = np.asarray(expect_img).astype(np.int16)
        path = os.path.join(PROJ, "PREVIEWS", "AFTER", f"AFTER_{num}_{slug}.png")
        got = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
        diff = np.abs(got - expect)
        p999 = float(np.percentile(diff, 99.9))
        worst = max(worst, p999)
        rows.append(dict(scene=slug, preview_size=list(Image.open(path).size),
                         max_abs_diff_8bit=int(diff.max()), p999_8bit=p999,
                         mean_abs_diff_8bit=float(diff.mean())))
    j("renders_from_cube_table", rows)
    j("renders_from_cube_worst_p999_8bit", worst)


# ---------------------------------------------------------------------------
# 8. Perceptual behaviour on skin / sky / foliage / stone
# ---------------------------------------------------------------------------
REGIONS = {
    "01_harsh-midday-city": {"sky": (0.00, 0.02, 0.55, 0.25), "glass": (0.35, 0.35, 0.80, 0.70)},
    "02_midday-portrait": {"skin": (0.35, 0.22, 0.62, 0.42), "sky": (0.02, 0.02, 0.45, 0.20)},
    "03_mediterranean-street": {"stone": (0.55, 0.25, 0.95, 0.50), "blue railing": (0.62, 0.10, 0.85, 0.35)},
    "04_beach-daylight": {"sky": (0.10, 0.02, 0.90, 0.28), "water": (0.10, 0.45, 0.90, 0.62),
                          "sand": (0.20, 0.90, 0.90, 0.99)},
    "05_landscape-greenery": {"sky": (0.10, 0.02, 0.90, 0.22), "foliage": (0.05, 0.48, 0.95, 0.80)},
    "06_golden-hour": {"warm sky": (0.05, 0.30, 0.95, 0.50), "foliage": (0.02, 0.78, 0.50, 0.99)},
    "07_modern-architecture": {"concrete": (0.35, 0.35, 0.62, 0.60)},
    "08_travel-street": {"buildings": (0.00, 0.20, 0.35, 0.50), "sky": (0.42, 0.00, 0.62, 0.09)},
}


def region_stats(img, box):
    a = np.asarray(img.convert("RGB"), dtype=np.float64) / 255.0
    H, W = a.shape[:2]
    x = a[int(box[1] * H):int(box[3] * H), int(box[0] * W):int(box[2] * W)].reshape(-1, 3)
    lin = al.srgb_to_linear(x)
    lab = al.linear_rec709_to_oklab(lin + 1e-9)
    L, C, h = al.oklab_chroma_hue(lab)
    w = C + 1e-9
    hm = float(np.degrees(np.arctan2((np.sin(h) * w).sum(), (np.cos(h) * w).sum())) % 360)
    return dict(L=float(L.mean()), C=float(C.mean()), hue=hm, code=float(x.mean()))


def test_regions():
    rows = []
    for num, slug, title, fname in rp.SCENES:
        b = Image.open(os.path.join(PROJ, "PREVIEWS", "BEFORE", f"BEFORE_{num}_{slug}.png"))
        a = Image.open(os.path.join(PROJ, "PREVIEWS", "AFTER", f"AFTER_{num}_{slug}.png"))
        for name, box in REGIONS.get(f"{num}_{slug}", {}).items():
            sb = region_stats(b, box)
            sa = region_stats(a, box)
            dh = (sa["hue"] - sb["hue"] + 180) % 360 - 180
            rows.append(dict(scene=f"{num} {slug}", region=name,
                             L=[round(sb["L"], 3), round(sa["L"], 3)],
                             chroma=[round(sb["C"], 4), round(sa["C"], 4)],
                             chroma_pct=round(100 * (sa["C"] / sb["C"] - 1), 1) if sb["C"] > 1e-5 else None,
                             rel_chroma=[round(sb["C"] / max(sb["L"], 1e-6), 4), round(sa["C"] / max(sa["L"], 1e-6), 4)],
                             rel_chroma_pct=round(100 * ((sa["C"] / max(sa["L"], 1e-6)) /
                                                        (sb["C"] / max(sb["L"], 1e-6)) - 1), 1),
                             hue=[round(sb["hue"], 1), round(sa["hue"], 1)], hue_shift=round(dh, 1)))
    j("region_table", rows)
    skin = [r for r in rows if "skin" in r["region"]]
    sky = [r for r in rows if r["region"] in ("sky", "water")]
    fol = [r for r in rows if "foliage" in r["region"]]
    if skin:
        j("skin_hue_shift_max_deg", max(abs(r["hue_shift"]) for r in skin))
        j("skin_chroma_change_pct", [r["chroma_pct"] for r in skin])
    j("sky_chroma_change_pct", [r["chroma_pct"] for r in sky])
    j("foliage_chroma_change_pct", [r["chroma_pct"] for r in fol])


# ---------------------------------------------------------------------------
# 9. Exposure variants
# ---------------------------------------------------------------------------
def test_exposure(lut):
    os.makedirs(os.path.join(PROJ, "PREVIEWS", "EXPOSURE_TESTS"), exist_ok=True)
    rows = []
    fname = "03_mediterranean_street.jpg"
    rgb = np.asarray(Image.open(os.path.join(rp.SRC, fname)).convert("RGB"))
    scene = al.srgb_to_linear(rgb.astype(np.float64) / 255.0)
    for label, stops in (("-1_stop", -1.0), ("normal", 0.0), ("+1_stop", 1.0)):
        s = scene * (2.0 ** stops)
        code = np.clip(al.encode(simulate.scene709_to_applewidegamut(s)), 0, 1)
        out = lut_io.apply_lut(lut, code)
        rows.append(dict(exposure=label,
                         log_code_mean=float(code.mean()),
                         out_mean=float(out.mean()),
                         out_p01=float(np.percentile(out, 1)),
                         out_p99=float(np.percentile(out, 99)),
                         frac_clipped_high=float((out >= 0.995).all(axis=-1).mean()),
                         frac_clipped_low=float((out <= 0.02).all(axis=-1).mean()),
                         mean_oklab_L=float(np.mean(al.linear_rec709_to_oklab(al.rec709_gamma24_decode(np.clip(out, 1e-6, 1)))[..., 0]))))
        img = Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
        img.save(os.path.join(PROJ, "PREVIEWS", "EXPOSURE_TESTS", f"AFTER_03_mediterranean_{label}.jpg"),
                 quality=90, optimize=True, progressive=True)
    j("exposure_table", rows)


# ---------------------------------------------------------------------------
# 10. Golden-hour double-warmth test
# ---------------------------------------------------------------------------
def test_golden_hour(lut):
    rgb = np.asarray(Image.open(os.path.join(rp.SRC, "06_golden_hour.jpg")).convert("RGB"))
    code, scene = simulate.simulate_apple_log2(rgb)
    out = lut_io.apply_lut(lut, code)
    before = simulate.neutral_render(scene)
    rows = []
    for label, img in (("before", before), ("after", out)):
        lab = al.linear_rec709_to_oklab(al.rec709_gamma24_decode(np.clip(img, 1e-6, 1)))
        L, C, h = al.oklab_chroma_hue(lab)
        # warm/cool balance: mean b* sign in CIELAB is expensive; use R-B ratio
        warm = float(np.mean((img[..., 0] - img[..., 2]) / np.maximum(img.mean(axis=-1), 1e-6)))
        rows.append(dict(state=label, mean_chroma=float(C.mean()), hue_mean=float(np.degrees(np.arctan2(
            np.sin(h).sum(), np.cos(h).sum())) % 360), warm_ratio=warm))
    j("golden_hour_table", rows)


def test_luma_monotonic(lut):
    """Luminance response of the LUT.

    The LUT stores display-referred (Rec.709 gamma 2.4) code values, so luma is
    measured on the decoded linear values.  Axis steps are only meaningful for
    input colours that are inside the Rec.709 gamut, i.e. the colours real
    footage can contain; out-of-gamut inputs are compressed by design.
    """
    n = lut.shape[0]
    lin = al.rec709_gamma24_decode(lut)
    grids = np.stack(np.meshgrid(*[np.arange(n)] * 3, indexing="ij"), -1)
    neutral = np.arange(n) / (n - 1)
    nl = np.stack([neutral] * 3, -1)
    nl_out = lut_io.apply_lut(lut, nl)
    n_luma = (al.rec709_gamma24_decode(nl_out) @ al.LUMA_REC709)
    j("neutral_luma_monotonic", bool(np.all(np.diff(n_luma) >= 0)))
    j("neutral_luma_min_step", float(np.diff(n_luma).min()))
    j("neutral_code_flat_steps", int((np.abs(np.diff(nl_out, axis=0)).max(axis=1) < 1e-6).sum()))

    worst = (9.0, None)
    fracs = []
    for axis in range(3):
        for i in range(n - 1):
            d = (np.take(lin, i + 1, axis=axis) - np.take(lin, i, axis=axis)) @ al.LUMA_REC709
            code = (np.take(grids, i, axis=axis) / (n - 1)).astype(float)
            scene = al.decode(code) @ al.AWG_TO_709.T
            m = (scene >= -0.002).all(-1) & (scene <= 1.002).all(-1)
            if not m.any():
                continue
            fracs.append(float((d[m] < -0.005).mean()))
            if d[m].min() < worst[0]:
                flat = np.argwhere(m)[int(np.argmin(d[m]))]
                loc = [int(flat[0]), int(flat[1])]
                loc.insert(axis, i)
                worst = (float(d[m].min()), [round(c / (n - 1), 4) for c in loc])
    j("ingamut_luma_min_step", worst[0])
    j("ingamut_luma_decrease_frac_gt_0_005", float(np.mean(fracs)))
    j("ingamut_luma_min_step_at_input_code", worst[1])


def test_shadow_detail(lut):
    rgb = np.asarray(Image.open(os.path.join(rp.SRC, "02_portrait_midday.jpg")).convert("RGB"))
    code, scene = simulate.simulate_apple_log2(rgb)
    out = lut_io.apply_lut(lut, code)
    before = simulate.neutral_render(scene)
    H, W = before.shape[:2]
    box = (0, int(0.72 * H), int(0.75 * W), H)
    b = np.asarray(Image.fromarray((np.clip(before, 0, 1) * 255).astype(np.uint8)).convert("L"),
                   dtype=np.float64)[box[1]:box[3], box[0]:box[2]] / 255.0
    a = np.asarray(Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert("L"),
                   dtype=np.float64)[box[1]:box[3], box[0]:box[2]] / 255.0
    j("shadow_detail_test", dict(region="portrait black garment", before_p5=float(np.percentile(b, 5)),
                                 before_p50=float(np.percentile(b, 50)), before_p95=float(np.percentile(b, 95)),
                                 after_p5=float(np.percentile(a, 5)), after_p50=float(np.percentile(a, 50)),
                                 after_p95=float(np.percentile(a, 95)),
                                 contrast_retained=float(a.std() / b.std()),
                                 before_std=float(b.std()), after_std=float(a.std())))


def main():
    lut = test_cube_file()
    test_curve()
    test_gamut()
    test_output_encoding(lut)
    test_neutral_smooth(lut)
    test_fidelity(lut)
    test_renders_from_cube(lut)
    test_regions()
    test_exposure(lut)
    test_golden_hour(lut)
    test_luma_monotonic(lut)
    test_shadow_detail(lut)
    with open(OUT_JSON, "w") as fh:
        json.dump(RES, fh, indent=2)
    print(f"\nwrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
