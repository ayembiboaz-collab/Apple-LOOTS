"""Numerical analysis of the grade on the colour patches (no vision needed)."""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import color_science as cs
from cube_io import read_cube, apply_cube

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

log2 = np.load(os.path.join(ROOT, "assets", "_tune_log2.npy"))
AWG_TO_709 = cs.apple_wide_gamut_to_rec709()

# Recompute patches at known pixel locations (same layout as tune_check.py).
W, H = 1200, 700
patches = {
    "skin_warm":   (0.82, 0.62, 0.48),
    "skin_mid":    (0.78, 0.58, 0.45),
    "sky_blue":    (0.35, 0.55, 0.85),
    "sky_deep":    (0.20, 0.40, 0.75),
    "foliage":     (0.30, 0.55, 0.25),
    "foliage_dark":(0.18, 0.38, 0.16),
    "stone_warm":  (0.72, 0.66, 0.55),
    "concrete":    (0.55, 0.55, 0.55),
    "white":       (0.95, 0.95, 0.93),
    "amber":       (0.90, 0.65, 0.30),
    "cyan":        (0.30, 0.70, 0.75),
    "shadow_neutral": (0.12, 0.12, 0.13),
}
cols, rows = 4, 3
pw = (W // 2) // cols
ph = H // rows

lut = read_cube(os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube"))
after_full = apply_cube(lut, log2)
lin709b = cs.apple_log_to_linear(log2) @ AWG_TO_709.T
before_full = cs.rec709_gamma24(np.clip(lin709b, 0, None))


def to_hsl(rgb):
    r, g, b = rgb
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2.0
    if mx == mn:
        return 0.0, 0.0, l
    d = mx - mn
    s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = (g - b) / d + (6 if g < b else 0)
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60.0, s, l


print(f"{'patch':16} {'src':>22} {'before(h,s,l)':>22} {'after(h,s,l)':>22} {'dE':>6}")
print("-" * 96)
for i, (name, rgb) in enumerate(patches.items()):
    c = i % cols
    r = i // cols
    y, x = r * ph + ph // 2, (W // 2) + c * pw + pw // 2
    before = before_full[y, x]
    after = after_full[y, x]
    bh, bs, bl = to_hsl(before)   # to_hsl returns (hue, sat, light)
    ah, as_, al = to_hsl(after)
    dE = np.sqrt(np.sum((after - before) ** 2))
    print(f"{name:16} {str(tuple(round(v,3) for v in rgb)):>22} "
          f"({bh:6.1f},{bs:.3f},{bl:.3f})   ({ah:6.1f},{as_:.3f},{al:.3f})   {dE:.3f}")
