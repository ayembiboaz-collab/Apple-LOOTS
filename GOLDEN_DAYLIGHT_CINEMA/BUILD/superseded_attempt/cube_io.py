"""
cube_io.py — write and read Adobe/Iridas .cube 3D LUTs, and apply them with
tetrahedral interpolation.

The AFTER previews are produced by *parsing the delivered .cube file from
disk* and interpolating it — never by calling the grade function directly.
That is what makes the previews honest proof of the shipped LUT.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def write_cube(path, table, size, title, header_lines=(), decimals=6):
    """Write a 3D .cube.

    `table` must be shaped (size**3, 3) in .cube order: RED index varies
    fastest, then GREEN, then BLUE.
    """
    table = np.asarray(table, dtype=np.float64)
    if table.shape != (size**3, 3):
        raise ValueError(f"table shape {table.shape} != {(size ** 3, 3)}")
    if not np.all(np.isfinite(table)):
        raise ValueError("table contains NaN or Inf")

    fmt = f"%.{decimals}f"
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        for line in header_lines:
            for sub in str(line).split("\n"):
                fh.write(f"# {sub}".rstrip() + "\n")
        fh.write(f'TITLE "{title}"\n')
        fh.write("LUT_3D_SIZE %d\n" % size)
        fh.write("DOMAIN_MIN 0.0 0.0 0.0\n")
        fh.write("DOMAIN_MAX 1.0 1.0 1.0\n")
        for r, g, b in table:
            fh.write(f"{fmt % r} {fmt % g} {fmt % b}\n")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def read_cube(path):
    """Parse a 3D .cube. Returns (table_rgb, size, domain_min, domain_max, title).

    `table_rgb` is shaped (size, size, size, 3) indexed [r, g, b].
    Raises on malformed files — this doubles as the syntax validator.
    """
    size = None
    dmin = np.array([0.0, 0.0, 0.0])
    dmax = np.array([1.0, 1.0, 1.0])
    title = None
    rows = []

    with open(path, "r", encoding="ascii") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            up = line.upper()
            if up.startswith("TITLE"):
                title = line.split(None, 1)[1].strip().strip('"')
            elif up.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
            elif up.startswith("LUT_1D_SIZE"):
                raise ValueError(f"{path}: 1D LUT, expected a 3D LUT")
            elif up.startswith("DOMAIN_MIN"):
                dmin = np.array([float(v) for v in line.split()[1:4]])
            elif up.startswith("DOMAIN_MAX"):
                dmax = np.array([float(v) for v in line.split()[1:4]])
            else:
                parts = line.split()
                if len(parts) != 3:
                    raise ValueError(f"{path}:{lineno}: expected 3 floats, got {len(parts)}")
                try:
                    rows.append([float(v) for v in parts])
                except ValueError as exc:
                    raise ValueError(f"{path}:{lineno}: non-numeric entry: {line}") from exc

    if size is None:
        raise ValueError(f"{path}: missing LUT_3D_SIZE")
    if len(rows) != size**3:
        raise ValueError(f"{path}: expected {size ** 3} entries, found {len(rows)}")

    flat = np.asarray(rows, dtype=np.float64)
    # .cube order: red fastest, then green, then blue.
    table = flat.reshape(size, size, size, 3)  # [b, g, r, ch]
    table = np.transpose(table, (2, 1, 0, 3))  # -> [r, g, b, ch]
    return table, size, dmin, dmax, title


# ---------------------------------------------------------------------------
# Applying (tetrahedral interpolation)
# ---------------------------------------------------------------------------


def apply_cube(rgb, table, size, dmin=None, dmax=None):
    """Apply a parsed 3D LUT to an (..., 3) array using tetrahedral
    interpolation — the same scheme DaVinci Resolve and Blackmagic Camera use.
    """
    rgb = np.asarray(rgb, dtype=np.float64)
    dmin = np.zeros(3) if dmin is None else np.asarray(dmin, dtype=np.float64)
    dmax = np.ones(3) if dmax is None else np.asarray(dmax, dtype=np.float64)

    shape = rgb.shape
    x = np.clip((rgb.reshape(-1, 3) - dmin) / (dmax - dmin), 0.0, 1.0) * (size - 1)

    i0 = np.floor(x).astype(np.int64)
    i0 = np.minimum(i0, size - 2)
    f = x - i0
    r0, g0, b0 = i0[:, 0], i0[:, 1], i0[:, 2]
    fr, fg, fb = f[:, 0], f[:, 1], f[:, 2]

    def V(dr, dg, db):
        return table[r0 + dr, g0 + dg, b0 + db]

    c000 = V(0, 0, 0)
    c111 = V(1, 1, 1)

    out = np.empty((x.shape[0], 3), dtype=np.float64)

    # Six tetrahedra of the unit cube, selected by the ordering of fr, fg, fb.
    m1 = (fr > fg) & (fg > fb)
    m2 = (fr > fg) & (fr > fb) & ~m1  # fr > fb >= fg
    m3 = (fr > fg) & ~m1 & ~m2  # fb >= fr > fg
    m4 = (fg >= fr) & (fg > fb) & (fr > fb)  # fg >= fr > fb
    m5 = (fg >= fr) & (fg > fb) & ~m4  # fg > fb >= fr
    m6 = (fg >= fr) & ~m4 & ~m5  # fb >= fg >= fr

    def blend(mask, a, b, c):
        if not np.any(mask):
            return
        w = np.stack([a[mask], b[mask], c[mask]], axis=-1)
        out[mask] = (
            (1.0 - w[:, 0:1]) * c000[mask]
            + (w[:, 0:1] - w[:, 1:2]) * P1[mask]
            + (w[:, 1:2] - w[:, 2:3]) * P2[mask]
            + w[:, 2:3] * c111[mask]
        )

    P1 = V(1, 0, 0)
    P2 = V(1, 1, 0)
    blend(m1, fr, fg, fb)

    P1 = V(1, 0, 0)
    P2 = V(1, 0, 1)
    blend(m2, fr, fb, fg)

    P1 = V(0, 0, 1)
    P2 = V(1, 0, 1)
    blend(m3, fb, fr, fg)

    P1 = V(0, 1, 0)
    P2 = V(1, 1, 0)
    blend(m4, fg, fr, fb)

    P1 = V(0, 1, 0)
    P2 = V(0, 1, 1)
    blend(m5, fg, fb, fr)

    P1 = V(0, 0, 1)
    P2 = V(0, 1, 1)
    blend(m6, fb, fg, fr)

    return out.reshape(shape)
