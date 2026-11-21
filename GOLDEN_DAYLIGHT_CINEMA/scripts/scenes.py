"""
scenes.py
=========

Procedurally generate the eight representative scenes used for the before/after
comparisons, then simulate Apple Log 2 / Apple Wide Gamut capture from them.

IMPORTANT -- SIMULATION, NOT REAL SENSOR FOOTAGE
------------------------------------------------
Genuine Apple Log 2 footage from an iPhone 17 Pro was not available in this
environment.  The source images are *procedurally generated* (value-noise
textures, gradients and vector shapes) -- they are NOT photographs and NOT
iPhone sensor captures.  The "Apple Log 2" input is a *documented simulation*
produced by:

    sRGB-encoded scene image
      -> decode sRGB to linear Rec.709
      -> convert linear Rec.709 to linear Apple Wide Gamut
         (inverse of the white-preserving AppleWG -> Rec.709 matrix)
      -> encode linear Apple Wide Gamut with Apple's published Apple Log 2
         transfer function (same curve as Apple Log).

This is mathematically the correct inverse of the LUT's decode stage, so it
exercises the real log curve and gamut transform.  It does NOT reproduce an
iPhone 17 Pro sensor's noise, moire, lens characteristics or exact colour
response; treat it as a controlled synthetic test, not representative of real
capture.  This limitation is documented in VALIDATION_REPORT.txt.

Each scene function returns a float32 sRGB-encoded image in [0, 1] (some
specular highlights may sit near 1.0).
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------
def _rand_grid(shape, seed):
    rng = np.random.default_rng(seed)
    return rng.random(shape)


def _smooth_interp(x):
    return x * x * (3.0 - 2.0 * x)


def value_noise(shape, scale, seed):
    """Smooth 2D value noise in [0, 1], shape (h, w)."""
    h, w = shape
    sy, sx = max(1, h // scale), max(1, w // scale)
    grid = _rand_grid((sy + 2, sx + 2), seed)
    gy = np.linspace(0.0, sy, h)
    gx = np.linspace(0.0, sx, w)
    y0 = np.floor(gy).astype(int)
    x0 = np.floor(gx).astype(int)
    ty = _smooth_interp(gy - y0)
    tx = _smooth_interp(gx - x0)
    y0c = np.clip(y0, 0, sy + 1)
    x0c = np.clip(x0, 0, sx + 1)
    y1c = np.clip(y0 + 1, 0, sy + 1)
    x1c = np.clip(x0 + 1, 0, sx + 1)
    a = grid[y0c[:, None], x0c[None, :]]
    b = grid[y0c[:, None], x1c[None, :]]
    c = grid[y1c[:, None], x0c[None, :]]
    d = grid[y1c[:, None], x1c[None, :]]
    top = a * (1 - tx)[None, :] + b * tx[None, :]
    bot = c * (1 - tx)[None, :] + d * tx[None, :]
    return (top * (1 - ty)[:, None] + bot * ty[:, None]).astype(np.float64)


def fbm(shape, scale, octaves, seed):
    """Fractal Brownian motion (sum of value noise octaves) in [0, 1]."""
    out = np.zeros(shape, dtype=np.float64)
    tot = 0.0
    cur = scale
    for o in range(octaves):
        out += value_noise(shape, int(cur), seed + o * 101) * (0.5 ** o)
        tot += 0.5 ** o
        cur *= 2
    return out / tot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t


def sky_gradient(h, w, zenith, horizon, sun_xy=None, sun_color=None,
                 sun_strength=0.0, seed=0):
    """Vertical sky gradient with an optional sun glow."""
    yy = np.linspace(0.0, 1.0, h)[:, None]
    base = np.zeros((h, w, 3), dtype=np.float64)
    for c in range(3):
        base[..., c] = lerp(zenith[c], horizon[c], yy)
    if sun_xy is not None and sun_strength > 0:
        sx, sy = sun_xy
        yy_idx, xx_idx = np.mgrid[0:h, 0:w]
        d = np.sqrt(((xx_idx - sx) / (w * 0.18)) ** 2 +
                    ((yy_idx - sy) / (h * 0.18)) ** 2)
        glow = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * sun_strength
        for c in range(3):
            base[..., c] += glow * sun_color[c]
    return base


def add_clouds(img, seed, coverage=0.5, brightness=1.0, y_top=0.0, y_bot=0.55):
    h, w = img.shape[:2]
    n = fbm((h, w), max(2, w // 90), 5, seed)
    # Shape clouds into horizontal bands.
    band = np.clip((n - 0.45) / 0.55, 0.0, 1.0)
    yy = np.linspace(0, 1, h)[:, None]
    mask = np.clip((y_bot - yy) / max(1e-6, y_bot - y_top), 0.0, 1.0)
    mask = mask * (1.0 - np.clip((yy - y_top) / max(1e-6, y_bot - y_top), 0.0, 1.0))
    cloud = band * mask * coverage
    for c in range(3):
        img[..., c] = lerp(img[..., c], 1.0, cloud * brightness * 0.85)
    return img


def rect(img, x0, y0, x1, y1, color):
    h, w = img.shape[:2]
    x0i, x1i = int(np.clip(x0, 0, w)), int(np.clip(x1, 0, w))
    y0i, y1i = int(np.clip(y0, 0, h)), int(np.clip(y1, 0, h))
    if x1i <= x0i or y1i <= y0i:
        return
    img[y0i:y1i, x0i:x1i] = color


def shade(img, mask, color, gain=1.0):
    m = mask[..., None]
    img[:] = lerp(img, color * gain, m)


# ---------------------------------------------------------------------------
# Scene generators (return sRGB-encoded float images in [0,1])
# ---------------------------------------------------------------------------
W, H = 1600, 1000


def scene1_midday_city():
    """Harsh midday city: bright buildings, blue sky, architectural shadows."""
    img = sky_gradient(H, W, (0.28, 0.52, 0.86), (0.62, 0.74, 0.88),
                       sun_xy=(W * 0.78, H * 0.20), sun_color=(1.0, 0.95, 0.82),
                       sun_strength=0.5)
    add_clouds(img, seed=11, coverage=0.35, y_top=0.02, y_bot=0.40)
    # Ground / street.
    rect(img, 0, H * 0.74, W, H, (0.34, 0.35, 0.37))
    # Buildings: sunlit face (warm concrete) + shaded face (cool) + rooftops.
    rng = np.random.default_rng(21)
    x = 0
    while x < W:
        bw = int(rng.integers(90, 200))
        bh = int(rng.integers(H * 0.30, H * 0.62))
        top = H * 0.74 - bh
        # Sunlit (right-facing) warm concrete.
        sun = np.array([0.72, 0.70, 0.64]) * rng.uniform(0.85, 1.0)
        shade_c = np.array([0.40, 0.43, 0.48]) * rng.uniform(0.8, 0.95)
        roof = (0.55, 0.53, 0.50)
        rect(img, x, top, x + bw, H * 0.74, sun)
        # Shaded side (left face) -- cooler.
        rect(img, x, top, x + int(bw * 0.18), H * 0.74, shade_c)
        rect(img, x, top, x + bw, top + int(bw * 0.10), roof)
        # Windows.
        for wy in range(int(top + 20), int(H * 0.72), 46):
            for wx in range(int(x + 14), int(x + bw - 14), 34):
                if rng.random() < 0.5:
                    col = (0.85, 0.86, 0.82) if rng.random() < 0.4 else (0.30, 0.34, 0.42)
                    rect(img, wx, wy, wx + 18, wy + 26, col)
        # Cast shadow on the street.
        cs = int(bw * 0.5)
        rect(img, x + int(bw * 0.3), H * 0.74, x + int(bw * 0.3) + cs, H,
             (0.16, 0.17, 0.20))
        x += bw + int(rng.integers(6, 24))
    return np.clip(img, 0, 1)


def scene2_midday_portrait():
    """Midday portrait in direct sunlight."""
    img = sky_gradient(H, W, (0.30, 0.55, 0.88), (0.72, 0.80, 0.90),
                       sun_xy=(W * 0.22, H * 0.16), sun_color=(1.0, 0.96, 0.84),
                       sun_strength=0.55)
    add_clouds(img, seed=22, coverage=0.25, y_top=0.0, y_bot=0.45)
    # Blurred bright background (bokeh-ish).
    bg = fbm((H, W), 120, 4, 33)
    for c in range(3):
        img[..., c] = lerp(img[..., c], (0.80, 0.84, 0.86)[c] + bg * 0.15, 0.5)
    # Subject: head and shoulders, direct sun from upper-left.
    cx, cy = W * 0.5, H * 0.46
    skin = (0.86, 0.64, 0.50)
    skin_shade = (0.62, 0.42, 0.32)
    # Shoulders / body.
    rect(img, cx - W * 0.26, cy + H * 0.16, cx + W * 0.26, H, (0.30, 0.36, 0.46))
    # Neck.
    rect(img, cx - W * 0.05, cy + H * 0.02, cx + W * 0.05, cy + H * 0.20, skin_shade)
    # Head (ellipse approximated by stacked rects).
    hw, hh = W * 0.15, H * 0.20
    for dy in range(-int(hh), int(hh), 4):
        wd = hw * np.sqrt(max(0.0, 1 - (dy / hh) ** 2))
        rect(img, cx - wd, cy + dy, cx + wd, cy + dy + 4, skin)
    # Sunlit side (left) brighter, shaded side (right) darker.
    for dy in range(-int(hh), int(hh), 4):
        wd = hw * np.sqrt(max(0.0, 1 - (dy / hh) ** 2))
        rect(img, cx, cy + dy, cx + wd, cy + dy + 4, skin_shade)
    # Hair.
    for dy in range(-int(hh), -int(hh * 0.2), 4):
        wd = hw * np.sqrt(max(0.0, 1 - (dy / hh) ** 2)) * 1.02
        rect(img, cx - wd, cy + dy, cx + wd, cy + dy + 4, (0.22, 0.16, 0.13))
    # Simple eyes + mouth (shaded).
    rect(img, cx - hw * 0.45, cy - hh * 0.05, cx - hw * 0.28, cy + hh * 0.05, (0.20, 0.16, 0.14))
    rect(img, cx + hw * 0.28, cy - hh * 0.05, cx + hw * 0.45, cy + hh * 0.05, (0.20, 0.16, 0.14))
    rect(img, cx - hw * 0.2, cy + hh * 0.42, cx + hw * 0.2, cy + hh * 0.5, (0.45, 0.28, 0.24))
    # Strong cast shadow on the ground.
    rect(img, cx - W * 0.1, cy + H * 0.16, cx + W * 0.35, H, (0.18, 0.19, 0.22))
    return np.clip(img, 0, 1)


def scene3_mediterranean_street():
    """Mediterranean street: warm stone, blue sky, foliage."""
    img = sky_gradient(H, W, (0.27, 0.50, 0.85), (0.66, 0.76, 0.88),
                       sun_xy=(W * 0.7, H * 0.22), sun_color=(1.0, 0.94, 0.80),
                       sun_strength=0.5)
    add_clouds(img, seed=33, coverage=0.3, y_top=0.0, y_bot=0.42)
    # Warm stone buildings on both sides.
    def stone(x0, x1, top, base, tone):
        rect(img, x0, top, x1, base, tone)
        # Window/arch details.
        for wy in range(int(top + 30), int(base - 40), 70):
            rect(img, x0 + 30, wy, x0 + 90, wy + 50, (0.55, 0.50, 0.45))
            rect(img, x1 - 90, wy, x1 - 30, wy + 50, (0.55, 0.50, 0.45))
    stone(0, W * 0.42, H * 0.10, H * 0.72, (0.80, 0.74, 0.62))
    stone(W * 0.58, W, H * 0.14, H * 0.72, (0.76, 0.70, 0.58))
    # Shaded alley centre.
    rect(img, W * 0.42, H * 0.10, W * 0.58, H * 0.72, (0.46, 0.44, 0.42))
    # Street / pavement.
    rect(img, 0, H * 0.72, W, H, (0.66, 0.60, 0.52))
    rect(img, 0, H * 0.72, W, H * 0.78, (0.74, 0.68, 0.58))
    # Foliage (green plants / trees) along the street.
    fol = fbm((H, W), 40, 5, 44)
    for c in range(3):
        img[..., c] = lerp(img[..., c], (0.30, 0.52, 0.26)[c],
                           np.clip((fol - 0.55) * 2.0, 0, 1) *
                           np.clip((H - np.arange(H))[:, None] / H, 0, 1) * 0.9)
    # A warm-lit foreground plant pot.
    rect(img, W * 0.12, H * 0.55, W * 0.22, H * 0.74, (0.34, 0.50, 0.24))
    rect(img, W * 0.10, H * 0.72, W * 0.24, H * 0.80, (0.55, 0.40, 0.30))
    return np.clip(img, 0, 1)


def scene4_beach_daylight():
    """Bright beach daylight: sky, sand, water, a person."""
    img = sky_gradient(H, W, (0.25, 0.52, 0.88), (0.74, 0.82, 0.92),
                       sun_xy=(W * 0.74, H * 0.16), sun_color=(1.0, 0.96, 0.86),
                       sun_strength=0.6)
    add_clouds(img, seed=55, coverage=0.3, y_top=0.0, y_bot=0.40)
    # Sea: horizontal band with wave noise.
    sea_top = H * 0.46
    rect(img, 0, sea_top, W, H * 0.60, (0.20, 0.48, 0.66))
    waves = fbm((int(H * 0.14), W), 30, 4, 66)
    for c in range(3):
        img[int(sea_top):int(H * 0.60), :, c] = lerp(
            img[int(sea_top):int(H * 0.60), :, c],
            (0.30, 0.60, 0.78)[c], (waves - 0.4) * 1.2)
    # Sand.
    rect(img, 0, H * 0.60, W, H, (0.84, 0.78, 0.64))
    sand = fbm((H, W), 60, 4, 77)
    sand_band = sand[int(H * 0.60):, :]
    for c in range(3):
        img[int(H * 0.60):, :, c] = lerp(
            img[int(H * 0.60):, :, c], (0.78, 0.72, 0.58)[c], (sand_band - 0.5) * 0.4)
    # A person (sunlit skin) standing on the sand.
    cx = W * 0.42
    skin = (0.85, 0.63, 0.49)
    rect(img, cx - 26, H * 0.60, cx + 26, H * 0.72, skin)          # legs
    rect(img, cx - 55, H * 0.50, cx + 55, H * 0.62, (0.62, 0.30, 0.26))  # torso
    rect(img, cx - 34, H * 0.42, cx + 34, H * 0.52, skin)           # head
    rect(img, cx - 34, H * 0.40, cx + 34, H * 0.44, (0.22, 0.16, 0.13))  # hair
    return np.clip(img, 0, 1)


def scene5_landscape():
    """Natural landscape: greenery, mountains, sky."""
    img = sky_gradient(H, W, (0.27, 0.50, 0.86), (0.68, 0.78, 0.90),
                       sun_xy=(W * 0.68, H * 0.20), sun_color=(1.0, 0.95, 0.84),
                       sun_strength=0.45)
    add_clouds(img, seed=88, coverage=0.4, y_top=0.0, y_bot=0.45)
    # Distant mountains (atmospheric blue-gray).
    for i, (top, tone) in enumerate([(0.52, (0.55, 0.60, 0.66)),
                                     (0.60, (0.42, 0.48, 0.54)),
                                     (0.68, (0.30, 0.36, 0.42))]):
        ridge = fbm((H, W), 24, 4, 90 + i)
        mask = np.clip((top - ridge * 0.12) / 0.12, 0, 1)
        mask = mask * np.clip((H - np.arange(H))[:, None] / H, 0, 1)
        for c in range(3):
            img[..., c] = lerp(img[..., c], tone[c], mask)
    # Foliage / grass foreground.
    fol = fbm((H, W), 30, 5, 120)
    green = (0.30, 0.52, 0.24)
    for c in range(3):
        img[..., c] = lerp(img[..., c], green[c],
                           np.clip((fol - 0.45) * 1.8, 0, 1) *
                           np.clip((H - np.arange(H))[:, None] / (H * 0.5), 0, 1) * 0.95)
    # A tree trunk + canopy.
    rect(img, W * 0.18, H * 0.35, W * 0.21, H * 0.78, (0.34, 0.24, 0.16))
    canopy = fbm((H, W), 50, 4, 130)
    canopy_mask = (np.clip((canopy - 0.6) * 2.2, 0, 1)
                   * np.clip(1 - np.abs(np.arange(W) - W * 0.195) / (W * 0.12), 0, 1)[None, :]
                   * np.clip((H * 0.45 - np.arange(H)) / H, 0, 1)[:, None] * 0.9)
    for c in range(3):
        img[..., c] = lerp(img[..., c], (0.26, 0.46, 0.20)[c], canopy_mask)
    return np.clip(img, 0, 1)


def scene6_golden_hour():
    """Golden-hour landscape: warm sky, long shadows, warm foliage."""
    img = sky_gradient(H, W, (0.30, 0.40, 0.72), (0.96, 0.74, 0.46),
                       sun_xy=(W * 0.5, H * 0.62), sun_color=(1.0, 0.86, 0.55),
                       sun_strength=0.85)
    add_clouds(img, seed=140, coverage=0.35, y_top=0.0, y_bot=0.5,
               brightness=1.0)
    # Warm ground.
    rect(img, 0, H * 0.62, W, H, (0.55, 0.46, 0.30))
    ground = fbm((H, W), 40, 4, 150)
    ground_band = ground[int(H * 0.62):, :]
    for c in range(3):
        img[int(H * 0.62):, :, c] = lerp(
            img[int(H * 0.62):, :, c], (0.50, 0.42, 0.28)[c], (ground_band - 0.5) * 0.5)
    # Warm-lit distant hills.
    for i, (top, tone) in enumerate([(0.55, (0.60, 0.48, 0.32)),
                                     (0.62, (0.48, 0.38, 0.26))]):
        ridge = fbm((H, W), 24, 4, 160 + i)
        mask = np.clip((top - ridge * 0.10) / 0.10, 0, 1)
        mask = mask * np.clip((H - np.arange(H))[:, None] / H, 0, 1)
        for c in range(3):
            img[..., c] = lerp(img[..., c], tone[c], mask)
    # Warm foliage + long shadows (silhouetted trees).
    fol = fbm((H, W), 30, 5, 170)
    for c in range(3):
        img[..., c] = lerp(img[..., c], (0.40, 0.42, 0.22)[c],
                           np.clip((fol - 0.5) * 1.8, 0, 1) *
                           np.clip((H - np.arange(H))[:, None] / (H * 0.5), 0, 1) * 0.9)
    # Silhouetted tree.
    rect(img, W * 0.74, H * 0.30, W * 0.775, H * 0.75, (0.16, 0.12, 0.10))
    rect(img, W * 0.70, H * 0.34, W * 0.815, H * 0.42, (0.16, 0.12, 0.10))
    return np.clip(img, 0, 1)


def scene7_modern_architecture():
    """Modern architecture: concrete, glass, strong geometry, blue sky."""
    img = sky_gradient(H, W, (0.26, 0.50, 0.85), (0.64, 0.75, 0.88),
                       sun_xy=(W * 0.8, H * 0.18), sun_color=(1.0, 0.95, 0.84),
                       sun_strength=0.5)
    add_clouds(img, seed=180, coverage=0.25, y_top=0.0, y_bot=0.42)
    # A big concrete building with glass facade.
    concrete = (0.62, 0.62, 0.62)
    concrete_shade = (0.42, 0.44, 0.47)
    glass = (0.40, 0.52, 0.62)
    rect(img, 0, H * 0.10, W * 0.6, H * 0.78, concrete)
    rect(img, W * 0.6, H * 0.10, W, H * 0.78, glass)
    # Facade grid + shadow side.
    for wy in range(int(H * 0.14), int(H * 0.76), 70):
        rect(img, 10, wy, W * 0.58, wy + 30, (0.70, 0.70, 0.70))
    rect(img, 0, H * 0.10, W * 0.12, H * 0.78, concrete_shade)
    # Glass reflection streaks.
    refl = fbm((H, W), 60, 4, 190)
    refl_band = refl[int(H * 0.1):int(H * 0.78), int(W * 0.6):]
    for c in range(3):
        img[int(H * 0.1):int(H * 0.78), int(W * 0.6):, c] = lerp(
            img[int(H * 0.1):int(H * 0.78), int(W * 0.6):, c],
            (0.55, 0.68, 0.80)[c], np.clip((refl_band - 0.55) * 1.5, 0, 1) * 0.5)
    # Ground plaza + strong shadow.
    rect(img, 0, H * 0.78, W, H, (0.50, 0.50, 0.52))
    rect(img, W * 0.05, H * 0.78, W * 0.7, H, (0.30, 0.31, 0.34))
    # A second smaller warm-toned element for warmth contrast.
    rect(img, W * 0.66, H * 0.40, W * 0.92, H * 0.78, (0.66, 0.60, 0.54))
    return np.clip(img, 0, 1)


def scene8_travel():
    """Outdoor travel scene with people and buildings."""
    img = sky_gradient(H, W, (0.28, 0.52, 0.86), (0.70, 0.78, 0.90),
                       sun_xy=(W * 0.72, H * 0.20), sun_color=(1.0, 0.95, 0.84),
                       sun_strength=0.5)
    add_clouds(img, seed=200, coverage=0.3, y_top=0.0, y_bot=0.42)
    # Buildings backdrop.
    rect(img, 0, H * 0.30, W * 0.4, H * 0.70, (0.70, 0.66, 0.60))
    rect(img, W * 0.35, H * 0.22, W * 0.72, H * 0.70, (0.62, 0.60, 0.58))
    rect(img, W * 0.68, H * 0.36, W, H * 0.70, (0.66, 0.64, 0.60))
    for bx, bw, top in [(0, 0.4, 0.30), (0.35, 0.37, 0.22), (0.68, 0.32, 0.36)]:
        for wy in range(int(H * top + 20), int(H * 0.68), 60):
            rect(img, int(W * bx) + 16, wy, int(W * bx) + int(W * bw * 0.4), wy + 30,
                 (0.55, 0.56, 0.60))
    # Street / plaza.
    rect(img, 0, H * 0.70, W, H, (0.55, 0.52, 0.48))
    # Foliage.
    fol = fbm((H, W), 40, 4, 210)
    for c in range(3):
        img[..., c] = lerp(img[..., c], (0.32, 0.50, 0.26)[c],
                           np.clip((fol - 0.6) * 2.0, 0, 1) *
                           np.clip((H - np.arange(H))[:, None] / (H * 0.4), 0, 1) * 0.85)
    # Two people (skin tones) walking.
    def person(cx, scale, clothing):
        s = scale
        skin = (0.84, 0.62, 0.48)
        rect(img, cx - 16 * s, H * 0.70, cx + 16 * s, H * 0.86, skin)
        rect(img, cx - 34 * s, H * 0.56, cx + 34 * s, H * 0.72, clothing)
        rect(img, cx - 20 * s, H * 0.46, cx + 20 * s, H * 0.58, skin)
        rect(img, cx - 20 * s, H * 0.43, cx + 20 * s, H * 0.47, (0.22, 0.16, 0.13))
    person(W * 0.40, 1.15, (0.36, 0.44, 0.55))
    person(W * 0.62, 0.95, (0.55, 0.36, 0.30))
    return np.clip(img, 0, 1)


SCENES = {
    "scene1_midday_city": scene1_midday_city,
    "scene2_midday_portrait": scene2_midday_portrait,
    "scene3_mediterranean_street": scene3_mediterranean_street,
    "scene4_beach_daylight": scene4_beach_daylight,
    "scene5_landscape": scene5_landscape,
    "scene6_golden_hour": scene6_golden_hour,
    "scene7_modern_architecture": scene7_modern_architecture,
    "scene8_travel": scene8_travel,
}


# ---------------------------------------------------------------------------
# Apple Log 2 simulation
# ---------------------------------------------------------------------------
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def simulate_apple_log2(srgb_img, exposure=1.0):
    """Simulate Apple Log 2 / Apple Wide Gamut from an sRGB scene image.

    ``exposure`` > 1 over-exposes the simulated capture (brighter highlights,
    used to test highlight behaviour); < 1 under-exposes (deeper shadows).
    """
    import color_science as cs
    lin709 = srgb_to_linear(srgb_img) * exposure
    awg_to_709 = cs.apple_wide_gamut_to_rec709()
    lin_awg = lin709 @ np.linalg.inv(awg_to_709).T
    log2 = cs.linear_to_apple_log(lin_awg)
    return log2
