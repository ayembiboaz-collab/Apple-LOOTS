#!/usr/bin/env python3
"""
Validate the delivered GOLDEN_DAYLIGHT_CINEMA.cube.
All checks run against the actual .cube file (parsed + trilinearly evaluated).
Prints a structured report to stdout.
"""
import os, sys, glob
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import golden_daylight as gd
from cube_reader import CubeLUT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUBE = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

print("=" * 70)
print("GOLDEN DAYLIGHT CINEMA — LUT VALIDATION")
print("=" * 70)

# ---- 1. File / syntax / numerical integrity -----------------------------
print("\n[1] File, syntax, numerical integrity")
size = None
entries = []
with open(CUBE) as f:
    for line in f:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if p[0] == "LUT_3D_SIZE":
            size = int(p[1])
        elif p[0] == "TITLE":
            print(f"    TITLE: {p[1].strip(chr(34))}")
        elif len(p) == 3:
            entries.append((float(p[0]), float(p[1]), float(p[2])))
data = np.array(entries)
print(f"    LUT_3D_SIZE = {size}   expected entries = {size**3}   found = {len(entries)}")
print(f"    OK dimensions: {size}x{size}x{size}" if size == 33 and len(entries) == 33**3 else "    FAIL dimensions")
print(f"    NaN present: {bool(np.isnan(data).any())}   Inf present: {bool(np.isinf(data).any())}")
print(f"    value range: min={data.min():.6f} max={data.max():.6f}")
print(f"    all finite: {bool(np.isfinite(data).all())}")
print(f"    all within [0,1]: {bool((data>=0).all() and (data<=1).all())}")

lut = CubeLUT(CUBE)
print(f"    parsed cube shape: {lut.data.shape}  size={lut.size}")

# ---- 2. Neutral behaviour ---------------------------------------------
print("\n[2] Neutral behaviour (gray ramp)")
grays = np.linspace(0.0, 1.0, 11)
out_gray = np.array([lut(np.array([g, g, g])) for g in grays])
for g, o in zip(grays, out_gray):
    spread = o.max() - o.min()
    print(f"    in={g:.2f} -> out=[{o[0]:.4f} {o[1]:.4f} {o[2]:.4f}]  channel spread={spread:.4f}")
print("    (small spread = no strong colour cast on neutrals)")

# 18% grey code value check
log18 = gd.apple_log2_encode(np.array([0.18, 0.18, 0.18]))
out18 = lut(log18)
print(f"    18% grey Apple Log 2 code={log18[0]:.4f} -> out=[{out18[0]:.4f} {out18[1]:.4f} {out18[2]:.4f}]")

# ---- 3. Highlight roll-off ---------------------------------------------
print("\n[3] Highlight roll-off")
hi = np.linspace(0.7, 1.0, 7)
for h in hi:
    o = lut(np.array([h, h, h]))
    print(f"    in={h:.2f} -> out={o[0]:.4f}  (delta={o[0]-h:+.4f})")

# ---- 4. Exposure invariance --------------------------------------------
print("\n[4] Exposure invariance (simulated +1, 0, -1 stop)")
for stem in ["scene1_midday_city", "scene2_midday_portrait", "scene5_landscape_greenery"]:
    im = Image.open(os.path.join(ROOT, "SOURCES", f"{stem}.png")).convert("RGB")
    src = np.asarray(im, float) / 255.0
    lin709 = gd.rec709_gamma24_decode(src)
    print(f"  -- {stem}")
    for stop, factor in [("+1 stop", 2.0), ("0 stop", 1.0), ("-1 stop", 0.5)]:
        lin = np.clip(lin709 * factor, 0, None)
        log = gd.apple_log2_encode(gd.rec709_linear_to_awg_linear(lin))
        out = np.clip(lut(log), 0, 1)
        lum = gd._luma(out)
        print(f"     {stop}: out lum mean={lum.mean():.3f} p1={np.percentile(lum,1):.3f} "
              f"p99={np.percentile(lum,99):.3f} clipped_frac={(out>=0.999).mean():.4f}")

# ---- 5. Skin / sky / foliage across scenes ------------------------------
print("\n[5] Skin / sky / foliage behaviour (delivered cube)")
def region(rgb, hue_lo, hue_hi, sat_lo=0.0, sat_hi=1.01, lum_lo=0.0, lum_hi=1.01):
    lum = gd._luma(rgb); hue, sat = gd._hue_sat(rgb)
    return ((hue > hue_lo) & (hue < hue_hi) & (sat > sat_lo) & (sat < sat_hi)
            & (lum > lum_lo) & (lum < lum_hi))
def rstat(rgb, m):
    if m.sum() == 0:
        return None
    sub = rgb[m]; h, s = gd._hue_sat(sub)
    return f"n={int(m.sum())} hue={np.median(h):.0f} sat={s.mean():.3f} lum={gd._luma(sub).mean():.3f}"

for stem in sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "SOURCES", "scene*.png"))):
    im = Image.open(os.path.join(ROOT, "SOURCES", f"{stem}.png")).convert("RGB")
    src = np.asarray(im, float) / 255.0
    log = gd.simulate_apple_log2_from_rec709(src)
    out = np.clip(lut(log), 0, 1)
    sky = region(src, 195, 250, lum_lo=0.30)
    fol = region(src, 70, 170, sat_lo=0.12)
    skin = region(src, 10, 50, sat_lo=0.10, sat_hi=0.55, lum_lo=0.15, lum_hi=0.85)
    print(f"  -- {stem}")
    print(f"     sky   : {rstat(out, sky)}")
    print(f"     foliage: {rstat(out, fol)}")
    print(f"     skin  : {rstat(out, skin)}")

# ---- 6. Direct vs cube (interpolation fidelity) ------------------------
print("\n[6] Interpolation fidelity: in-memory grade vs delivered cube")
maxerr = 0.0
for stem in sorted(os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "SOURCES", "scene*.png"))):
    im = Image.open(os.path.join(ROOT, "SOURCES", f"{stem}.png")).convert("RGB")
    src = np.asarray(im, float) / 255.0
    log = gd.simulate_apple_log2_from_rec709(src)
    direct = gd.lut_apply(log)
    cube = np.clip(lut(log), 0, 1)
    e = np.abs(direct - cube).mean()
    maxerr = max(maxerr, e)
    print(f"     {stem}: mean abs error = {e:.4f}")
print(f"     max mean abs error across scenes = {maxerr:.4f}")

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)
