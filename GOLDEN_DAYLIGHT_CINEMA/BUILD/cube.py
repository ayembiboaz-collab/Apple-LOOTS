"""
cube.py -- minimal, strict Adobe/Resolve .cube (3D LUT) reader and trilinear
interpolator. Used to (a) write the deliverable and (b) render the AFTER images
*through the delivered file itself*, so the previews cannot drift from the LUT.
"""
import numpy as np


def write_cube(path, table, title="GOLDEN DAYLIGHT CINEMA", comment_lines=()):
    """table: (N,N,N,3) float, indexed [r,g,b] -> output r,g,b in 0..1.

    Written with RED varying fastest, which is what the .cube spec and
    Resolve / Final Cut / Blackmagic Camera expect.
    """
    n = table.shape[0]
    assert table.shape == (n, n, n, 3), table.shape
    lines = [f'TITLE "{title}"']
    for c in comment_lines:
        lines.append(f'# {c}')
    lines += ["# 3D LUT for Apple Log 2 / Apple Wide Gamut -> Rec.709 SDR gamma 2.4",
              "LUT_3D_SIZE %d" % n,
              "DOMAIN_MIN 0.0 0.0 0.0",
              "DOMAIN_MAX 1.0 1.0 1.0",
              ""]
    # r fastest, then g, then b
    flat = table.transpose(2, 1, 0, 3).reshape(-1, 3)
    lines += ["%.8f %.8f %.8f" % tuple(v) for v in flat]
    with open(path, "w", encoding="ascii", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return n ** 3


def read_cube(path):
    """Return (table (N,N,N,3), meta dict). Raises on malformed input."""
    size = None
    dmin, dmax = np.zeros(3), np.ones(3)
    vals, meta = [], {}
    with open(path, "r", encoding="ascii", errors="strict") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            up = line.upper()
            if up.startswith("TITLE"):
                meta["title"] = line.split(None, 1)[1].strip().strip('"')
            elif up.startswith("LUT_3D_SIZE"):
                size = int(line.split()[1])
            elif up.startswith("LUT_1D_SIZE"):
                raise ValueError("1D LUT not supported")
            elif up.startswith("DOMAIN_MIN"):
                dmin = np.array([float(x) for x in line.split()[1:4]])
            elif up.startswith("DOMAIN_MAX"):
                dmax = np.array([float(x) for x in line.split()[1:4]])
            else:
                parts = line.split()
                if len(parts) != 3:
                    raise ValueError(f"malformed data line: {raw!r}")
                vals.append([float(x) for x in parts])
    if size is None:
        raise ValueError("missing LUT_3D_SIZE")
    arr = np.asarray(vals, dtype=np.float64)
    if arr.shape != (size ** 3, 3):
        raise ValueError(f"expected {size**3} rows, got {arr.shape[0]}")
    meta["domain_min"], meta["domain_max"] = dmin, dmax
    # rows are r fastest -> reshape (b,g,r) then transpose to (r,g,b)
    tbl = arr.reshape(size, size, size, 3).transpose(2, 1, 0, 3).copy()
    return tbl, meta


def apply_cube(rgb, table, dmin=(0.0, 0.0, 0.0), dmax=(1.0, 1.0, 1.0),
               clamp_in=True):
    """Trilinear interpolation of `table` at rgb (...,3). Vectorised."""
    n = table.shape[0]
    dmin = np.asarray(dmin, dtype=np.float64)
    dmax = np.asarray(dmax, dtype=np.float64)
    x = (rgb - dmin) / (dmax - dmin)
    if clamp_in:
        x = np.clip(x, 0.0, 1.0)
    p = x * (n - 1)
    i0 = np.clip(np.floor(p).astype(np.int64), 0, n - 2)
    f = p - i0
    out = np.zeros(rgb.shape, dtype=np.float64)
    for dr in (0, 1):
        wr = f[..., 0] if dr else 1.0 - f[..., 0]
        for dg in (0, 1):
            wg = f[..., 1] if dg else 1.0 - f[..., 1]
            for db in (0, 1):
                wb = f[..., 2] if db else 1.0 - f[..., 2]
                w = wr * wg * wb
                out += w[..., None] * table[i0[..., 0] + dr,
                                            i0[..., 1] + dg,
                                            i0[..., 2] + db]
    return out
