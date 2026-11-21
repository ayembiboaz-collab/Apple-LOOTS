"""
cube_io.py
===========

Read / write the 3D .cube LUT format and apply it to images with trilinear
interpolation.

Format facts (verified against the Adobe "Cube LUT Specification 1.0" and
common renderer conventions):

  * ``LUT_3D_SIZE N`` declares an N x N x N grid (N^3 data lines).
  * Data lines are ``red green blue`` with each in [0, 1].
  * Ordering is **red-fastest**: index = r + g*N + b*N*N.  Red changes on
    consecutive lines, green every N lines, blue every N*N lines.
  * ``DOMAIN_MIN`` / ``DOMAIN_MAX`` declare the input range (default 0..1).

The trilinear applier here is used to produce the AFTER renders from the
*delivered* .cube file (not from the in-memory pipeline), so the previews
demonstrate exactly what the shipped LUT does.
"""

from __future__ import annotations

import numpy as np


def write_cube(path, data, size, title="", domain_min=(0.0, 0.0, 0.0),
               domain_max=(1.0, 1.0, 1.0), precision=6):
    """Write a 3D .cube file.

    Parameters
    ----------
    path : str
        Output file path.
    data : array, shape (N, N, N, 3)
        The LUT, indexed ``data[r, g, b]`` = output RGB for input
        (r, g, b) grid coordinates.
    size : int
        N (LUT_3D_SIZE).
    title : str
        TITLE string.
    domain_min, domain_max : tuple
        Input domain.
    precision : int
        Decimal places for the written values.
    """
    data = np.asarray(data, dtype=np.float64)
    assert data.shape == (size, size, size, 3), f"bad shape {data.shape}"

    lines = []
    lines.append(f'TITLE "{title}"')
    lines.append(f"LUT_3D_SIZE {size}")
    lines.append(
        f"DOMAIN_MIN {domain_min[0]:.{precision}f} {domain_min[1]:.{precision}f} "
        f"{domain_min[2]:.{precision}f}"
    )
    lines.append(
        f"DOMAIN_MAX {domain_max[0]:.{precision}f} {domain_max[1]:.{precision}f} "
        f"{domain_max[2]:.{precision}f}"
    )
    lines.append("")

    # Red-fastest ordering: index = r + g*N + b*N*N
    fmt = "{:.%df} {:.%df} {:.%df}" % ((precision,) * 3)
    for b in range(size):
        for g in range(size):
            for r in range(size):
                rv, gv, bv = data[r, g, b]
                lines.append(fmt.format(float(rv), float(gv), float(bv)))

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def read_cube(path):
    """Read a 3D .cube file.

    Returns
    -------
    dict with keys:
        size : int
        domain_min, domain_max : np.ndarray (3,)
        data : np.ndarray (N, N, N, 3), indexed data[r, g, b]
        title : str
    """
    size = None
    domain_min = np.array([0.0, 0.0, 0.0])
    domain_max = np.array([1.0, 1.0, 1.0])
    title = ""
    values = []

    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            kw = parts[0]
            if kw == "TITLE":
                title = line.split('"', 2)[1] if '"' in line else ""
            elif kw == "LUT_3D_SIZE":
                size = int(parts[1])
            elif kw == "DOMAIN_MIN":
                domain_min = np.array([float(x) for x in parts[1:4]])
            elif kw == "DOMAIN_MAX":
                domain_max = np.array([float(x) for x in parts[1:4]])
            elif kw in ("LUT_3D_INPUT", "LUT_3D_OUTPUT"):
                # Legacy IRIDAS-style lines; ignore (we use DOMAIN_MIN/MAX).
                continue
            elif kw == "LUT_1D_SIZE":
                raise ValueError("1D .cube files are not supported")
            else:
                # Data line.
                vals = [float(x) for x in parts[:3]]
                if len(vals) == 3:
                    values.append(vals)

    if size is None:
        raise ValueError("Missing LUT_3D_SIZE")
    n3 = size ** 3
    if len(values) != n3:
        raise ValueError(
            f"Data line count {len(values)} != LUT_3D_SIZE^3 ({n3})"
        )

    arr = np.array(values, dtype=np.float64)  # shape (N^3, 3), red-fastest
    # Reshape to (N, N, N, 3) indexed [r, g, b].
    # Flat index i = r + g*N + b*N*N  ->  b = i//(N*N), g = (i% (N*N))//N, r = i%N
    idx = np.arange(n3)
    r = idx % size
    g = (idx // size) % size
    b = idx // (size * size)
    data = np.empty((size, size, size, 3), dtype=np.float64)
    data[r, g, b, :] = arr
    return {
        "size": size,
        "domain_min": domain_min,
        "domain_max": domain_max,
        "data": data,
        "title": title,
    }


def apply_cube(lut, encoded, trilinear=True):
    """Apply a parsed .cube LUT to encoded RGB values.

    Parameters
    ----------
    lut : dict
        From :func:`read_cube`.
    encoded : array, shape (..., 3)
        Input values (typically 0..1).  Values outside the domain are
        clamped to the domain edges.
    trilinear : bool
        If True use trilinear interpolation; if False use nearest-node.

    Returns
    -------
    array, same shape as ``encoded``
    """
    data = lut["data"]
    size = lut["size"]
    dmin = lut["domain_min"]
    dmax = lut["domain_max"]

    x = np.asarray(encoded, dtype=np.float64)
    # Normalise input to grid coordinates [0, size-1].
    span = dmax - dmin
    span[span == 0] = 1.0
    coords = (x - dmin) / span * (size - 1)
    coords = np.clip(coords, 0.0, size - 1)

    r = coords[..., 0]
    g = coords[..., 1]
    b = coords[..., 2]

    if not trilinear:
        ri = np.round(r).astype(int)
        gi = np.round(g).astype(int)
        bi = np.round(b).astype(int)
        return data[ri, gi, bi]

    ri0 = np.floor(r).astype(int)
    gi0 = np.floor(g).astype(int)
    bi0 = np.floor(b).astype(int)
    ri1 = np.minimum(ri0 + 1, size - 1)
    gi1 = np.minimum(gi0 + 1, size - 1)
    bi1 = np.minimum(bi0 + 1, size - 1)

    dr = (r - ri0)[..., None]
    dg = (g - gi0)[..., None]
    db = (b - bi0)[..., None]

    # 8 corners.
    c000 = data[ri0, gi0, bi0]
    c100 = data[ri1, gi0, bi0]
    c010 = data[ri0, gi1, bi0]
    c110 = data[ri1, gi1, bi0]
    c001 = data[ri0, gi0, bi1]
    c101 = data[ri1, gi0, bi1]
    c011 = data[ri0, gi1, bi1]
    c111 = data[ri1, gi1, bi1]

    c00 = c000 * (1 - dr) + c100 * dr
    c10 = c010 * (1 - dr) + c110 * dr
    c01 = c001 * (1 - dr) + c101 * dr
    c11 = c011 * (1 - dr) + c111 * dr

    c0 = c00 * (1 - dg) + c10 * dg
    c1 = c01 * (1 - dg) + c11 * dg

    out = c0 * (1 - db) + c1 * db
    return np.clip(out, 0.0, 1.0)
