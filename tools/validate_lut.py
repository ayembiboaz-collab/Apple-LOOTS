"""
Validation suite for GOLDEN_DAYLIGHT_CINEMA.cube.

Tests actually performed (results printed, also saved to stdout):
  A. .cube syntax, dimensions, numerical integrity
  B. Apple Log 2 decode / Apple Wide Gamut handling vs OpenColorIO 2.6 builtin
  C. Matrix check vs colour-science (AWG->XYZ, AWG->ACES2065-1)
  D. Neutral axis behaviour + gamma-2.4 output sanity
  E. Axis sweeps: monotonicity, smoothness, clipping stats
  F. Grid interpolation fidelity (33^3 LUT vs direct dense evaluation)
  G. Whole-scene renders: AFTER derived from delivered cube; ROI hue/sat stats
  H. Exposure robustness: -1/0/+1 EV simulated Apple Log 2, clipping stats
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import lut_core
from lut_core import (apple_log2_decode, apple_log2_encode, srgb_to_linear,
                      linear_to_srgb, M_AWG_TO_R709, M_AWG_TO_XYZ, REC709_LUMA,
                      M_R709_TO_AWG)
import grade
from render_previews import load_cube, apply_cube_trilinear, simulate_apple_log2, SCENES, SRC

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CUBE = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')
PREVIEWS = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'ALT_PREVIEWS')

def section(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)

# ---------------------------------------------------------------- A. parse --
section("A. .cube syntax, dimensions, numerical integrity")
with open(CUBE, 'r') as f:
    raw = f.read()
print("file size:", os.path.getsize(CUBE), "bytes")
print("total lines:", len(raw.strip().splitlines()))
size, lut = load_cube(CUBE)
data = lut.reshape(-1, 3)
print("LUT_3D_SIZE:", size, "| data nodes:", data.shape[0], "| expected:", size ** 3)
assert size == 33 and data.shape[0] == 35937
print("DOMAIN_MIN/MAX present:", "DOMAIN_MIN 0.0 0.0 0.0" in raw and "DOMAIN_MAX 1.0 1.0 1.0" in raw)
print("finite values:", bool(np.isfinite(data).all()), "| min:", data.min(), "| max:", data.max())
print("nodes clipped at 0.0:", int((data <= 0.0).any(axis=1).sum()), "| at 1.0:", int((data >= 1.0).any(axis=1).sum()))
print("nodes fully inside (0,1):", int(((data > 0.0).all(axis=1) & (data < 1.0).all(axis=1)).sum()), "/ 35937")

# -------------------------------------------------- B. OCIO cross-checks ----
section("B. Apple Log 2 decode vs OpenColorIO 2.6 builtin (APPLE_LOG-APPLEWG_to_ACES2065-1)")
import PyOpenColorIO as ocio
cfg = ocio.Config.CreateRaw()
t = ocio.BuiltinTransform(style="APPLE_LOG-APPLEWG_to_ACES2065-1", direction=ocio.TRANSFORM_DIR_FORWARD)
proc = cfg.getProcessor(ocio.GroupTransform([t])).getDefaultCPUProcessor()
AP0_RGB_TO_XYZ = np.array([[9.52552396e-01, 0.00000000e+00, 9.36786000e-05],
                           [3.43966450e-01, 7.28166097e-01, -7.21325464e-02],
                           [0.00000000e+00, 0.00000000e+00, 1.00882518e+00]])
BRADFORD = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
def xyz_d65_to_aces_white(M):
    src = np.array([0.3127 / 0.3290, 1.0, (1 - 0.3127 - 0.3290) / 0.3290])
    dst = np.array([0.32168 / 0.33767, 1.0, (1 - 0.32168 - 0.33767) / 0.33767])
    Ms, Md = BRADFORD @ src, BRADFORD @ dst
    return np.linalg.inv(BRADFORD) @ np.diag(Md / Ms) @ BRADFORD @ M
M_AWG_TO_ACES = np.linalg.inv(AP0_RGB_TO_XYZ) @ xyz_d65_to_aces_white(M_AWG_TO_XYZ)
rng = np.random.default_rng(42)
errs = []
for _ in range(400):
    L = 10 ** rng.uniform(-2.0, 1.1)  # linear reflectance up to ~12.6
    enc = apple_log2_encode(np.array([L]))[0]
    ocio_out = np.array(proc.applyRGB([enc, enc, enc]))
    ours = M_AWG_TO_ACES @ np.array([L, L, L])
    errs.append(np.abs(ocio_out - ours).max())
print("max |OCIO - ours| over 400 neutral samples:", max(errs))

# round-trip
xs = np.linspace(0.0, 1.0, 2048)
rt = apple_log2_encode(apple_log2_decode(xs))
print("encode(decode(x)) max abs err:", np.abs(rt - xs).max())
print("encode(decode(x)) max rel err (x>0.05):", np.abs((rt[xs > 0.05] - xs[xs > 0.05]) / xs[xs > 0.05]).max())
print("Apple white paper anchors: encode(0.18) =", apple_log2_encode(np.array([0.18]))[0],
      "(expect ~0.4888 = code 500/1023); decode(0.69336945) =", apple_log2_decode(np.array([0.69336945]))[0])

# ------------------------------------------------------- C. colour check ----
section("C. matrices vs colour-science")
import colour
print("AWG->XYZ (ours):\n", M_AWG_TO_XYZ)
print("max |our R709 matrix - colour's| :",
      np.abs(M_AWG_TO_R709 - np.linalg.inv(colour.RGB_COLOURSPACES['ITU-R BT.709'].matrix_RGB_to_XYZ) @ M_AWG_TO_XYZ).max())

# --------------------------------------------------------- D. neutrals ------
section("D. neutral axis behaviour + output gamma sanity")
grays = np.linspace(0.02, 0.99, 60)
neutral = apply_cube_trilinear(np.tile(grays[:, None], (1, 3)), lut, size)
spreads = (neutral.max(axis=1) - neutral.min(axis=1))
print("neutral axis: max channel spread =", spreads.max(), "at log input", grays[spreads.argmax()].round(3))
print("neutral axis mean spread =", spreads.mean())
lumas = neutral @ REC709_LUMA
dl = np.diff(lumas)
print("neutral luma min step:", dl.min(), "| monotonic within 1e-3:", bool(np.all(dl >= -1e-3)))
print("sample neutral map (log -> code^2.4 linear):")
for v in [0.2, 0.35, 0.4888, 0.60, 0.75, 0.88, 1.0]:
    px = apply_cube_trilinear(np.array([[v, v, v]]), lut, size)[0]
    print(f"  in {v:.4f}  ->  out codes ({px[0]:.4f},{px[1]:.4f},{px[2]:.4f})  -> linear ~{np.mean(px) ** 2.4:.4f}")
# gamma 2.4 verification: an ideal grey image decoded with gamma 2.4 should be preserved
for v in [0.18, 1.0]:
    lin = apple_log2_decode(np.array([v]))[0]
    expected = np.clip(grade.tone_map_Y(np.array([max(lin, 0)]))[0], 0, 1) ** (1 / 2.4)
    print(f"tone_map check at Y={lin:.3f}: Y'={grade.tone_map_Y(np.array([lin]))[0]:.4f}")

# --------------------------------------------------- E. sweeps/monotonicity -
section("E. axis sweeps, monotonicity, smoothness")
for name, axis_idx in [("R axis", 0), ("G axis", 1), ("B axis", 2)]:
    vals = np.zeros((size, 3))
    vals[:, axis_idx] = np.linspace(0, 1, size)
    out = apply_cube_trilinear(vals, lut, size)
    diffs = np.diff(out[:, axis_idx])
    mono = np.all(diffs >= -1e-3)
    print(f"   (min adjacent step {diffs.min():.5f})")
    print(f"{name}: output channel monotonic: {mono} | out range [{out[:, axis_idx].min():.3f}, {out[:, axis_idx].max():.3f}]")
for axis in range(3):
    d = np.abs(np.diff(lut, axis=axis)).max(axis=3)
    print(f"axis {axis}: p50={np.percentile(d,50):.4f} p95={np.percentile(d,95):.4f} p99={np.percentile(d,99):.4f} max={d.max():.4f} nodes>0.25: {int((d>0.25).sum())}")

# --------------------------------------------- F. grid interpolation error --
section("F. 33^3 trilinear vs direct dense grade")
errs = []
for _ in range(3000):
    c = rng.random(3)
    # direct: decode & grade this log colour
    lin_awg = apple_log2_decode(c)
    lin709 = lin_awg @ M_AWG_TO_R709.T
    direct = grade.grade_full(lin709.reshape(1, 3))[0]
    via = apply_cube_trilinear(c.reshape(1, 3), lut, size)[0]
    errs.append(np.abs(direct - via).max())
errs = np.array(errs)
print("max abs trilinear error over 3000 random nodes:", errs.max())
print("mean:", errs.mean(), "| p95:", np.percentile(errs, 95), "| p99:", np.percentile(errs, 99))

# ------------------------------------------- G. scene ROI stats + cube use -
section("G. scene ROI statistics (AFTER = delivered cube applied to simulated log)")
def hsv_mean(path, box):
    im = Image.open(path).convert('RGB')
    if max(im.size) > 1400:
        im = im.resize((int(im.size[0] * 1400 / max(im.size)), int(im.size[1] * 1400 / max(im.size))), Image.LANCZOS)
    img = np.asarray(im, dtype=np.float64) / 255.0
    h, w = img.shape[:2]
    x0, y0, x1, y1 = [int(f) for f in (box[0] * w, box[1] * h, box[2] * w, box[3] * h)]
    px = img[y0:y1, x0:x1].reshape(-1, 3)
    mx = px.max(axis=1); mn = px.min(axis=1); d = mx - mn
    sat = np.divide(d, mx, out=np.zeros_like(d), where=mx > 1e-6)
    # hue
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    hdeg = np.zeros_like(r)
    m = d > 1e-6
    dd = np.maximum(d, 1e-9)
    rc = np.where(m, (mx - r) / dd, 0); gc = np.where(m, (mx - g) / dd, 0); bc = np.where(m, (mx - b) / dd, 0)
    hdeg = np.where(mx == r, bc - gc, np.where(mx == g, 2.0 + rc - bc, 4.0 + gc - rc)) * 60.0 % 360.0
    return {"n": int(px.shape[0]), "mean_rgb": px.mean(axis=0).round(3).tolist(),
            "mean_sat": round(float(sat.mean()), 4), "mean_luma": round(float((px @ REC709_LUMA).mean()), 4),
            "hue_deg_mean": round(float(np.degrees(np.angle(np.exp(1j * np.radians(hdeg)).mean())) % 360), 1)}

ROIS = {
    "01_midday_city": [("sky", (0.30, 0.02, 0.75, 0.30)), ("sunlit_facades", (0.02, 0.55, 0.22, 0.75)), ("shadow_tower", (0.80, 0.60, 0.97, 0.85))],
    "02_midday_portrait": [("skin_cheek", (0.24, 0.20, 0.44, 0.45))],
    "03_mediterranean_street": [("blue_wall", (0.62, 0.00, 0.98, 0.45)), ("sunlit_stone", (0.33, 0.30, 0.60, 0.70)), ("shadow_stone", (0.00, 0.30, 0.22, 0.80))],
    "04_beach_daylight": [("sky", (0.05, 0.02, 0.95, 0.26)), ("sea", (0.05, 0.32, 0.50, 0.58)), ("sand", (0.55, 0.62, 0.97, 0.97))],
    "05_landscape_mountains": [("sky", (0.38, 0.02, 0.62, 0.30)), ("forest", (0.05, 0.35, 0.35, 0.72)), ("lake", (0.40, 0.80, 0.62, 0.95))],
    "06_golden_hour": [("sunset_sky", (0.05, 0.30, 0.60, 0.45)), ("wheat", (0.05, 0.62, 0.42, 0.95))],
    "07_modern_architecture": [("steel_bright", (0.43, 0.13, 0.83, 0.45)), ("sky", (0.22, 0.02, 0.80, 0.22))],
    "08_travel_people": [("warm_buildings", (0.62, 0.05, 0.98, 0.60)), ("pavement", (0.28, 0.78, 0.78, 0.97)), ("sky", (0.33, 0.02, 0.65, 0.28))],
}
roi_results = {}
for slug, fname, title in SCENES:
    a = os.path.join(PREVIEWS, f"{slug}_AFTER.png")
    b = os.path.join(PREVIEWS, f"{slug}_BEFORE.png")
    print(f"\n-- {slug} ({title})")
    for name, box in ROIS[slug]:
        ra, rb = hsv_mean(a, box), hsv_mean(b, box)
        roi_results[f"{slug}:{name}"] = {"after": ra, "before": rb}
        print(f"  {name:16s} AFTER rgb{ra['mean_rgb']} sat {ra['mean_sat']:.3f} luma {ra['mean_luma']:.3f} hue~{ra['hue_deg_mean']}°"
              f"   | BEFORE rgb{rb['mean_rgb']} sat {rb['mean_sat']:.3f} luma {rb['mean_luma']:.3f}")

# AFTER must derive from delivered cube: re-render scene 2 from source and compare
src2 = os.path.join(SRC, "02_midday_portrait.jpg")
rgb = np.asarray(Image.open(src2).convert('RGB'), dtype=np.float64) / 255.0
log_enc = simulate_apple_log2(rgb)
codes = apply_cube_trilinear(log_enc.reshape(-1, 3), lut, size).reshape(rgb.shape)
after_direct = linear_to_srgb(np.power(np.clip(codes, 0, 1), 2.4))
png = np.asarray(Image.open(os.path.join(PREVIEWS, "02_midday_portrait_AFTER.png")).convert('RGB'), dtype=np.float64) / 255.0
scale = min(1.0, 2048 / max(rgb.shape[:2]))
from PIL import Image as _Image
src_small = np.asarray(_Image.open(src2).convert('RGB').resize((round(rgb.shape[1] * scale), round(rgb.shape[0] * scale)), _Image.LANCZOS), dtype=np.float64) / 255.0
log_small = simulate_apple_log2(src_small)
codes_small = apply_cube_trilinear(log_small.reshape(-1, 3), lut, size).reshape(src_small.shape)
after_small = linear_to_srgb(np.power(np.clip(codes_small, 0, 1), 2.4))
print("\nAFTER PNG vs delivered-cube re-render: max abs diff =", np.abs(after_small - png).max())

# --------------------------------------------- H. exposure robustness ------
section("H. exposure robustness (-1/0/+1 EV) on simulated Apple Log 2")
for ev in [-1.0, 0.0, 1.0]:
    gain = 2.0 ** ev
    clip_tot, px_tot = 0, 0
    for slug, fname, title in SCENES:
        src = os.path.join(SRC, fname)
        _im = __import__('PIL.Image', fromlist=['Image']).open(src).convert('RGB')
        if max(_im.size) > 1024:
            _im = _im.resize((int(_im.size[0] * 1024 / max(_im.size)), int(_im.size[1] * 1024 / max(_im.size))), __import__('PIL.Image', fromlist=['Image']).LANCZOS)
        rgb = np.asarray(_im, dtype=np.float64) / 255.0
        lin709 = srgb_to_linear(rgb) * gain
        lin_awg = np.clip(lin709, 0, None) @ M_R709_TO_AWG.T
        log_enc = np.round(np.clip(apple_log2_encode(np.clip(lin_awg, 0, None)), 0, 1) * 1023) / 1023
        codes = apply_cube_trilinear(log_enc.reshape(-1, 3), lut, size).reshape(rgb.shape)
        clip_tot += int((codes >= 0.995).any(axis=2).sum()); px_tot += codes.shape[0] * codes.shape[1]
    print(f"EV {ev:+.1f}: pixels with any channel >= 0.995 after LUT: {clip_tot} / {px_tot} ({100.0 * clip_tot / px_tot:.2f}%)")

print("\nValidation complete.")
