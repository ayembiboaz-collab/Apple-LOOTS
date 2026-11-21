"""Region-based analysis of the rendered before/after scenes.

Measures mean RGB / luminance / warmth on selected regions of interest to
verify the grade hits the visual targets on the actual rendered content.
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PREVIEWS = os.path.join(ROOT, "PREVIEWS")


def load(name, kind):
    from PIL import Image
    a = np.asarray(Image.open(os.path.join(PREVIEWS, f"{name}_{kind}.png"))).astype(np.float64) / 255.0
    return a


def stats(arr):
    r, g, b = arr[..., 0].mean(), arr[..., 1].mean(), arr[..., 2].mean()
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return r, g, b, lum


def hsl(rgb):
    r, g, b = rgb
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2.0
    d = mx - mn
    if d == 0:
        return 0.0, 0.0, l
    s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    if mx == r:
        h = (g - b) / d + (6 if g < b else 0)
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60.0, s, l


# (scene, region_name, x0,y0,x1,y1, expectation)
ROIS = [
    ("scene1_midday_city", "sky",       0,   0, 1600, 300, "blue, B>R"),
    ("scene1_midday_city", "building",  200, 400, 500, 600, "warm concrete"),
    ("scene1_midday_city", "shadow",    400, 850, 900, 990, "deep, not crushed"),
    ("scene2_midday_portrait", "skin",  680, 360, 920, 560, "natural warm skin"),
    ("scene3_mediterranean_street", "sky", 0, 0, 1600, 250, "blue"),
    ("scene3_mediterranean_street", "stone", 0, 300, 600, 700, "warm stone"),
    ("scene3_mediterranean_street", "foliage", 190, 550, 360, 740, "natural green"),
    ("scene4_beach_daylight", "sky",    0, 0, 1600, 300, "blue"),
    ("scene4_beach_daylight", "sand",   0, 700, 1600, 1000, "warm sand"),
    ("scene4_beach_daylight", "water",  0, 480, 1600, 620, "blue/cyan"),
    ("scene5_landscape", "sky",        0, 0, 1600, 250, "blue"),
    ("scene5_landscape", "foliage",    0, 470, 1600, 640, "natural green"),
    ("scene5_landscape", "mountain",   0, 420, 1600, 560, "atmospheric blue-gray"),
    ("scene6_golden_hour", "sky",      0, 0, 1600, 300, "golden warm"),
    ("scene6_golden_hour", "foliage",  0, 650, 1600, 1000, "warm-lit green"),
    ("scene7_modern_architecture", "sky", 0, 0, 1600, 250, "blue"),
    ("scene7_modern_architecture", "concrete", 0, 200, 900, 700, "neutral/warm concrete"),
    ("scene7_modern_architecture", "glass", 950, 200, 1550, 700, "blue glass"),
    ("scene8_travel", "sky",          0, 0, 1600, 250, "blue"),
    ("scene8_travel", "buildings",    0, 250, 1600, 650, "warm buildings"),
    ("scene8_travel", "street",       0, 750, 1600, 1000, "warm pavement"),
]


def main():
    print(f"{'scene':28} {'region':10} {'before(R,G,B,lum)':>34} {'after(R,G,B,lum)':>34} {'warmth':>7}")
    print("-" * 130)
    for scene, region, x0, y0, x1, y1, exp in ROIS:
        before = load(scene, "before")[y0:y1, x0:x1]
        after = load(scene, "after")[y0:y1, x0:x1]
        br, bg, bb, blum = stats(before)
        ar, ag, ab, alum = stats(after)
        bh, bs, bl = hsl((br, bg, bb))
        ah, as_, al = hsl((ar, ag, ab))
        print(f"{scene:28} {region:10} "
              f"({br:.3f},{bg:.3f},{bb:.3f},{blum:.3f})  "
              f"({ar:.3f},{ag:.3f},{ab:.3f},{alum:.3f})  "
              f"{ar-ab:+.3f}  [{exp}]")


if __name__ == "__main__":
    main()
