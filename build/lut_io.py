"""Read/write .cube 3D LUTs and apply them the way a grading app does."""

from __future__ import annotations

import numpy as np

CUBE_INPUT_IS_LOG2_LINE = ("# GOLDEN DAYLIGHT CINEMA — Apple Log 2 (Apple Wide Gamut) -> Rec.709 SDR (gamma 2.4)")


def write_cube(path, lut, title="GOLDEN DAYLIGHT CINEMA", extra_comments=()):
    size = lut.shape[0]
    assert lut.shape == (size, size, size, 3)
    lines = [f'TITLE "{title}"', "# Created by GOLDEN DAYLIGHT CINEMA build (build/make_lut.py)"]
    lines += list(extra_comments)
    lines += [f"LUT_3D_SIZE {size}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0", ""]
    # .cube ordering: red index changes fastest
    flat = lut.transpose(2, 1, 0, 3).reshape(-1, 3)
    body = "\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in flat)
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
        fh.write(body + "\n")


def read_cube(path):
    size = None
    data = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            up = s.upper()
            if up.startswith("TITLE") or up.startswith("DOMAIN_"):
                continue
            if up.startswith("LUT_3D_SIZE"):
                size = int(s.split()[1])
                continue
            if up.startswith("LUT_1D_SIZE"):
                raise ValueError("unexpected 1D LUT")
            parts = s.split()
            if len(parts) != 3:
                raise ValueError(f"malformed LUT row: {s[:80]!r}")
            data.append([float(p) for p in parts])
    data = np.array(data, dtype=np.float64)
    if size is None:
        raise ValueError("missing LUT_3D_SIZE")
    if data.shape[0] != size ** 3:
        raise ValueError(f"expected {size**3} rows, found {data.shape[0]}")
    # red fastest -> [b, g, r] then transpose to [r, g, b]
    lut = data.reshape(size, size, size, 3).transpose(2, 1, 0, 3)
    return lut


def apply_trilinear(lut, code):
    """Apply a 3D LUT with trilinear interpolation. code: (...,3) in 0..1."""
    size = lut.shape[0]
    code = np.clip(np.asarray(code, dtype=np.float64), 0.0, 1.0)
    g = code * (size - 1)
    i0 = np.floor(g).astype(np.int64)
    i0 = np.clip(i0, 0, size - 2)
    f = g - i0
    out = np.zeros(code.shape[:-1] + (3,))
    for dr in (0, 1):
        wr = f[..., 0] if dr else 1 - f[..., 0]
        for dg in (0, 1):
            wg = f[..., 1] if dg else 1 - f[..., 1]
            for db in (0, 1):
                wb = f[..., 2] if db else 1 - f[..., 2]
                w = wr * wg * wb
                out += lut[i0[..., 0] + dr, i0[..., 1] + dg, i0[..., 2] + db] * w[..., None]
    return out


def apply_tetrahedral(lut, code):
    """Tetrahedral interpolation — the standard for 3D LUT application.

    Fewer visible interpolation artefacts than trilinear on saturated edges,
    and it is what Blackmagic/Resolve-class software uses for 3D LUTs.
    """
    size = lut.shape[0]
    code = np.clip(np.asarray(code, dtype=np.float64), 0.0, 1.0)
    g = code * (size - 1)
    i0 = np.clip(np.floor(g).astype(np.int64), 0, size - 2)
    f = g - i0
    fr, fg, fb = f[..., 0], f[..., 1], f[..., 2]
    c = lambda dr, dg, db: lut[i0[..., 0] + dr, i0[..., 1] + dg, i0[..., 2] + db]
    c000 = c(0, 0, 0)
    c100, c010, c001 = c(1, 0, 0), c(0, 1, 0), c(0, 0, 1)
    c110, c101, c011 = c(1, 1, 0), c(1, 0, 1), c(0, 1, 1)
    c111 = c(1, 1, 1)

    # six tetrahedra of the unit cube; masks select the active one per pixel
    m1 = (fr > fg) & (fg > fb)
    m2 = (fr > fg) & ~(fg > fb) & (fr > fb)
    m3 = (fr > fg) & ~(fg > fb) & ~(fr > fb)
    m4 = ~(fr > fg) & (fb > fg)
    m5 = ~(fr > fg) & ~(fb > fg) & (fb > fr)
    m6 = ~(fr > fg) & ~(fb > fg) & ~(fb > fr)

    out = np.zeros(code.shape[:-1] + (3,))
    for mask, expr in (
        (m1, fr[..., None] * (c100 - c000) + fg[..., None] * (c110 - c100) + fb[..., None] * (c111 - c110)),
        (m2, fr[..., None] * (c100 - c000) + fb[..., None] * (c101 - c100) + fg[..., None] * (c111 - c101)),
        (m3, fb[..., None] * (c001 - c000) + fr[..., None] * (c101 - c001) + fg[..., None] * (c111 - c101)),
        (m4, fb[..., None] * (c001 - c000) + fg[..., None] * (c011 - c001) + fr[..., None] * (c111 - c011)),
        (m5, fg[..., None] * (c010 - c000) + fb[..., None] * (c011 - c010) + fr[..., None] * (c111 - c011)),
        (m6, fg[..., None] * (c010 - c000) + fr[..., None] * (c110 - c010) + fb[..., None] * (c111 - c110)),
    ):
        out += np.where(mask[..., None], c000 + expr, 0.0)
    return out


def apply_lut(lut, image_code, method="tetrahedral"):
    f = apply_tetrahedral if method == "tetrahedral" else apply_trilinear
    return np.clip(f(lut, image_code), 0.0, 1.0)
