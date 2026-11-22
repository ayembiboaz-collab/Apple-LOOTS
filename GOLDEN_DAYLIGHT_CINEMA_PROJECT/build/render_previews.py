"""Independent .cube reader (trilinear interpolation) and previews renderer.

IMPORTANT for the deliverable: BEFORE previews are rendered through the
official/verified neutral Apple Log 2 -> Rec.709 reference transform
(pipeline.neutral_reference).  AFTER previews are rendered by THIS script's
independent .cube parser applied to the SHIPPED .cube file — no grading
function, no analytic pipeline code is reused for AFTER renders.

Each scene produces two PNGs (before/after) at the source resolution, plus a
combined side-by-side comparison image.

Usage:
  python render_previews.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs
import pipeline as pl

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
SRC = PROJECT / 'source_images'
SIM = PROJECT / 'simulated_log'
OUT = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'PREVIEWS'
CUBE = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'LUT' / 'GOLDEN_DAYLIGHT_CINEMA.cube'


def load_cube(path):
    """Minimal, independent .cube parser."""
    with open(path) as f:
        lines = f.read().splitlines()
    size = None
    data = []
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith('#'):
            continue
        parts = ln.split()
        if parts[0].upper() == 'LUT_3D_SIZE':
            size = int(parts[1])
            continue
        if parts[0].upper() in ('DOMAIN_MIN', 'DOMAIN_MAX'):
            continue
        vals = [float(x) for x in parts]
        if len(vals) == 3:
            data.append(vals)
        elif len(vals) == 1:
            continue  # ignore stray scalars
    data = np.asarray(data, dtype=np.float64)
    if size is None:
        size = int(round(data.shape[0] ** (1.0 / 3.0)))
    if data.shape[0] != size ** 3:
        raise ValueError(f'cube has {data.shape[0]} rows, expected {size**3} for {size}^3')
    # .cube convention: RED varies fastest, then GREEN, then BLUE.
    # reshape so that the fastest flat axis (red) is the last cube index.
    data = data.reshape(size, size, size, 3)  # (blue, green, red, channel)
    data = data.transpose(2, 1, 0, 3)         # (red, green, blue, channel)
    return size, data


def read_cube_at(data, size, r, g, b):
    """Trilinear sample of the (red-fastest) .cube data.

    data[i, j, k] = output for grid point (R=i, G=j, B=k); i = red index.
    """
    # Position in grid units (0..size-1); axes are (red, green, blue).
    x = r * (size - 1)
    y = g * (size - 1)
    z = b * (size - 1)

    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    z0 = np.floor(z).astype(np.int32)
    x1 = np.minimum(x0 + 1, size - 1)
    y1 = np.minimum(y0 + 1, size - 1)
    z1 = np.minimum(z0 + 1, size - 1)
    fx = x - x0
    fy = y - y0
    fz = z - z0

    out = np.zeros((r.shape[0], r.shape[1], 3), dtype=np.float64)
    out[..., 0] = (
        data[x0, y0, z0, 0] * (1 - fx) * (1 - fy) * (1 - fz)
        + data[x0, y0, z1, 0] * (1 - fx) * (1 - fy) * fz
        + data[x0, y1, z0, 0] * (1 - fx) * fy * (1 - fz)
        + data[x0, y1, z1, 0] * (1 - fx) * fy * fz
        + data[x1, y0, z0, 0] * fx * (1 - fy) * (1 - fz)
        + data[x1, y0, z1, 0] * fx * (1 - fy) * fz
        + data[x1, y1, z0, 0] * fx * fy * (1 - fz)
        + data[x1, y1, z1, 0] * fx * fy * fz
    )
    out[..., 1] = (
        data[x0, y0, z0, 1] * (1 - fx) * (1 - fy) * (1 - fz)
        + data[x0, y0, z1, 1] * (1 - fx) * (1 - fy) * fz
        + data[x0, y1, z0, 1] * (1 - fx) * fy * (1 - fz)
        + data[x0, y1, z1, 1] * (1 - fx) * fy * fz
        + data[x1, y0, z0, 1] * fx * (1 - fy) * (1 - fz)
        + data[x1, y0, z1, 1] * fx * (1 - fy) * fz
        + data[x1, y1, z0, 1] * fx * fy * (1 - fz)
        + data[x1, y1, z1, 1] * fx * fy * fz
    )
    out[..., 2] = (
        data[x0, y0, z0, 2] * (1 - fx) * (1 - fy) * (1 - fz)
        + data[x0, y0, z1, 2] * (1 - fx) * (1 - fy) * fz
        + data[x0, y1, z0, 2] * (1 - fx) * fy * (1 - fz)
        + data[x0, y1, z1, 2] * (1 - fx) * fy * fz
        + data[x1, y0, z0, 2] * fx * (1 - fy) * (1 - fz)
        + data[x1, y0, z1, 2] * fx * (1 - fy) * fz
        + data[x1, y1, z0, 2] * fx * fy * (1 - fz)
        + data[x1, y1, z1, 2] * fx * fy * fz
    )
    return out


def apply_cube(img, data, size):
    """Apply the shipped .cube to a (H, W, 3) float image via trilinear interpolation."""
    r = img[..., 0]
    g = img[..., 1]
    b = img[..., 2]
    out = read_cube_at(data, size, r, g, b)
    return out


def load_png(path):
    return np.asarray(Image.open(path).convert('RGB'), dtype=np.float64) / 255.0


def save_png(arr, path):
    arr = np.clip(arr, 0.0, 1.0)
    Image.fromarray(np.rint(arr * 255).astype(np.uint8), mode='RGB').save(path)


def side_by_side(before, after, title, out_path):
    # pad images to same height, side by side with 6px divider
    h = max(before.shape[0], after.shape[0])
    def resize_height(a, hh):
        from PIL import Image as _I
        scale = hh / a.shape[0]
        w = int(round(a.shape[1] * scale))
        return _I.fromarray(np.rint(a * 255).astype(np.uint8)).resize((w, hh), _I.LANCZOS)
    b = resize_height(before, h)
    a = resize_height(after, h)
    w_b, w_a = b.size[0], a.size[0]
    canvas = Image.new('RGB', (w_b + w_a + 8, h), (24, 24, 24))
    canvas.paste(b, (0, 0))
    canvas.paste(a, (w_b + 8, 0))
    canvas.save(out_path)


MAX_W = 1600


def maybe_resize(arr):
    """Downsample to max-width for repository-friendly preview files."""
    h, w = arr.shape[:2]
    if w <= MAX_W:
        return arr
    scale = MAX_W / w
    from PIL import Image as _I
    pil = _I.fromarray(np.rint(np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8))
    pil = pil.resize((int(round(w * scale)), int(round(h * scale))), _I.LANCZOS)
    return np.asarray(pil, dtype=np.float64) / 255.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    size, cube_data = load_cube(CUBE)
    print(f'Loaded .cube: {size}^3, {cube_data.shape}')
    print(f'Cube: {CUBE} ({CUBE.stat().st_size} bytes)')

    sims = sorted(SIM.glob('*.png'))
    print(f'Found {len(sims)} simulated inputs')

    for sim in sims:
        stem = sim.name.replace('_SIMULATED_APPLE_LOG2.png', '')
        img = load_png(sim)
        print(f'{sim.name}: {img.shape[1]}x{img.shape[0]}')

        # BEFORE: official neutral Apple Log 2 -> Rec.709 reference transform
        before = pl.neutral_reference(img)
        before = maybe_resize(before)
        save_png(before, OUT / (stem + '_BEFORE_NEUTRAL.png'))

        # AFTER: independent .cube application
        after = apply_cube(img, cube_data, size)
        after = maybe_resize(after)
        save_png(after, OUT / (stem + '_AFTER_GOLDEN_DAYLIGHT.png'))

        # side-by-side for quick review
        side_by_side(before, after, stem, OUT / (stem + '_COMPARISON.png'))

    print('Done.')


if __name__ == '__main__':
    main()
