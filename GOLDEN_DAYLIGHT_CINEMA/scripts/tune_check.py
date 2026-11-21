"""Quick grade tuning: render a colour checker + luminance gradient through
the neutral decode and the LUT, to eyeball skin/sky/foliage/neutral behaviour.
"""
import os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import color_science as cs
import grade
from cube_io import read_cube, apply_cube

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# --- Build a test image: luminance gradient on left, colour patches on right.
W, H = 1200, 700
# Left half: vertical luminance gradient 0..1 (with a warm-ish and cool-ish tint
# in different bands to see tonal behaviour).
yy = np.linspace(0, 1, H)[:, None]
left = np.zeros((H, W // 2, 3))
# gradient from black to white, but tint bands:
band = np.clip(yy, 0, 1)
left[..., 0] = band * 0.9 + 0.05
left[..., 1] = band * 0.95 + 0.04
left[..., 2] = band * 1.0 + 0.03

# Right half: colour patches (sRGB-encoded) in a grid.
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
right = np.zeros((H, W // 2, 3))
cols = 4
rows = 3
pw = (W // 2) // cols
ph = H // rows
for i, (name, rgb) in enumerate(patches.items()):
    c = i % cols
    r = i // cols
    right[r*ph:(r+1)*ph, c*pw:(c+1)*pw] = rgb

img_srgb = np.concatenate([left, right], axis=1)
Image.fromarray((np.clip(img_srgb, 0, 1) * 255).astype(np.uint8)).save(
    os.path.join(ROOT, "assets", "_tune_source_srgb.png"))

# --- Simulate Apple Log 2: sRGB -> linear 709 -> linear AppleWG -> Apple Log 2.
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

lin709 = srgb_to_linear(img_srgb)
# 709 -> AppleWG linear (inverse of AWG->709 matrix)
AWG_TO_709 = cs.apple_wide_gamut_to_rec709()
lin_awg = lin709 @ np.linalg.inv(AWG_TO_709).T
log2 = cs.linear_to_apple_log(lin_awg)
np.save(os.path.join(ROOT, "assets", "_tune_log2.npy"), log2)

# --- BEFORE: neutral decode (decode + gamut + gamma2.4, no grade).
lin709b = cs.apple_log_to_linear(log2) @ AWG_TO_709.T
before = cs.rec709_gamma24(np.clip(lin709b, 0, None))
Image.fromarray((np.clip(before, 0, 1) * 255).astype(np.uint8)).save(
    os.path.join(ROOT, "assets", "_tune_before.png"))

# --- AFTER: apply the delivered .cube.
lut = read_cube(os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube"))
after = apply_cube(lut, log2)
Image.fromarray((np.clip(after, 0, 1) * 255).astype(np.uint8)).save(
    os.path.join(ROOT, "assets", "_tune_after.png"))

print("saved _tune_*.png")
print("log2 range:", log2.min(), log2.max())
