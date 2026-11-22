"""
lut_engine.py -- an independent .cube reader / applier.

This module deliberately imports NOTHING from gdc_grade.py or gdc_bake.py.  It
is a from-scratch, plain-file implementation used to produce every AFTER image
and every delivered validation number, so that the results cannot be an artefact
of re-running the analytic grading code.

It supports trilinear and tetrahedral interpolation, DOMAIN_MIN/DOMAIN_MAX,
comments, TITLE and the standard "red channel varies fastest" ordering.
"""

from __future__ import annotations

import numpy as np


class LUT3D:
    def __init__(self, size: int, table: np.ndarray,
                 domain_min=None, domain_max=None, title: str = ""):
        self.size = int(size)
        self.title = title
        self.domain_min = np.array(domain_min if domain_min is not None else [0.0, 0.0, 0.0], float)
        self.domain_max = np.array(domain_max if domain_max is not None else [1.0, 1.0, 1.0], float)
        t = np.asarray(table, dtype=np.float64)
        if t.shape != (self.size ** 3, 3):
            raise ValueError(f"bad table shape {t.shape} for size {self.size}")
        self.table = t

    # -- construction ------------------------------------------------------
    @classmethod
    def from_cube(cls, path: str) -> "LUT3D":
        size = None
        dmin, dmax = [0.0, 0.0, 0.0], [1.0, 1.0, 1.0]
        vals = []
        title = ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                key = line.split()[0].upper()
                if key == "TITLE":
                    title = line[5:].strip().strip('"')
                elif key == "LUT_3D_SIZE":
                    size = int(line.split()[1])
                elif key == "DOMAIN_MIN":
                    dmin = [float(x) for x in line.split()[1:4]]
                elif key == "DOMAIN_MAX":
                    dmax = [float(x) for x in line.split()[1:4]]
                elif key in ("LUT_1D_SIZE", "LUT_1D_INPUT_RANGE"):
                    raise ValueError("1D LUTs are not supported")
                else:
                    parts = line.split()
                    if len(parts) < 3:
                        raise ValueError(f"bad .cube line: {raw!r}")
                    vals.append((float(parts[0]), float(parts[1]), float(parts[2])))
        if size is None:
            raise ValueError("no LUT_3D_SIZE in file")
        table = np.array(vals, dtype=np.float64)
        if len(table) != size ** 3:
            raise ValueError(f"expected {size**3} entries, found {len(table)}")
        return cls(size, table, dmin, dmax, title)

    # -- helpers -----------------------------------------------------------
    def _node(self, ir, ig, ib):
        s = self.size
        return self.table[(ib * s + ig) * s + ir]

    def to_unit(self, p: np.ndarray) -> np.ndarray:
        return (p - self.domain_min) / (self.domain_max - self.domain_min)

    # -- interpolation -----------------------------------------------------
    def apply(self, p: np.ndarray, method: str = "tetra", chunk: int = 1 << 21) -> np.ndarray:
        p = np.asarray(p, dtype=np.float64)
        shape = p.shape
        flat = self.to_unit(p.reshape(-1, 3))
        out = np.empty_like(flat)
        for s0 in range(0, len(flat), chunk):
            sl = slice(s0, min(s0 + chunk, len(flat)))
            out[sl] = (self._tri(flat[sl]) if method == "tri" else self._tet(flat[sl]))
        return out.reshape(shape)

    def _cell(self, x):
        s = self.size
        v = np.clip(x, 0.0, 1.0) * (s - 1)
        i = np.floor(v).astype(np.int64)
        i = np.clip(i, 0, s - 2)
        f = np.clip(v - i, 0.0, 1.0)
        return i[:, 0], i[:, 1], i[:, 2], f[:, 0], f[:, 1], f[:, 2]

    def _tri(self, x):
        ir, ig, ib, fr, fg, fb = self._cell(x)
        c000 = self._node(ir, ig, ib)
        c100 = self._node(ir + 1, ig, ib)
        c010 = self._node(ir, ig + 1, ib)
        c110 = self._node(ir + 1, ig + 1, ib)
        c001 = self._node(ir, ig, ib + 1)
        c101 = self._node(ir + 1, ig, ib + 1)
        c011 = self._node(ir, ig + 1, ib + 1)
        c111 = self._node(ir + 1, ig + 1, ib + 1)
        fr = fr[:, None]; fg = fg[:, None]; fb = fb[:, None]
        c00 = c000 * (1 - fr) + c100 * fr
        c10 = c010 * (1 - fr) + c110 * fr
        c01 = c001 * (1 - fr) + c101 * fr
        c11 = c011 * (1 - fr) + c111 * fr
        c0 = c00 * (1 - fg) + c10 * fg
        c1 = c01 * (1 - fg) + c11 * fg
        return c0 * (1 - fb) + c1 * fb

    def _tet(self, x):
        ir, ig, ib, fr, fg, fb = self._cell(x)
        c = [self._node(ir, ig, ib), self._node(ir + 1, ig, ib),
             self._node(ir, ig + 1, ib), self._node(ir + 1, ig + 1, ib),
             self._node(ir, ig, ib + 1), self._node(ir + 1, ig, ib + 1),
             self._node(ir, ig + 1, ib + 1), self._node(ir + 1, ig + 1, ib + 1)]
        # c[k] with k = dr + 2*dg + 4*db
        out = np.zeros_like(c[0])
        fv = [fr, fg, fb]                       # 1-D fractions
        bit = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        cases = [
            ((0, 1, 2), (fr >= fg) & (fg >= fb)),
            ((0, 2, 1), (fr >= fb) & (fb > fg)),
            ((1, 0, 2), (fg > fr) & (fr >= fb)),
            ((1, 2, 0), (fg >= fb) & (fb > fr)),
            ((2, 0, 1), (fb > fr) & (fr >= fg)),
            ((2, 1, 0), (fb > fg) & (fg > fr)),
        ]
        for (a, b, cc), mask in cases:
            if not np.any(mask):
                continue
            fa = fv[a][mask][:, None]
            fbb = fv[b][mask][:, None]
            fcc = fv[cc][mask][:, None]
            ea = bit[a]
            eab = tuple(bit[a][j] + bit[b][j] for j in range(3))
            sel = lambda offs: c[offs[0] + 2 * offs[1] + 4 * offs[2]][mask]
            out[mask] = (sel((0, 0, 0)) * (1.0 - fa)
                         + sel(ea) * (fa - fbb)
                         + sel(eab) * (fbb - fcc)
                         + sel((1, 1, 1)) * fcc)
        return out

    # -- introspection -----------------------------------------------------
    def node_value(self, r: int, g: int, b: int) -> np.ndarray:
        return self._node(np.array([r]), np.array([g]), np.array([b]))[0]


def apply_cube_file(path: str, p: np.ndarray, method: str = "tetra") -> np.ndarray:
    lut = LUT3D.from_cube(path)
    return lut.apply(p, method=method)


if __name__ == "__main__":
    # identity LUT sanity check written through gdc_bake's writer
    import sys
    import gdc_bake as B
    n = 5
    ax = np.linspace(0, 1, n)
    bb, gg, rr = np.meshgrid(ax, ax, ax, indexing="ij")
    ident = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], -1)
    B.write_cube("/tmp/identity.cube", ident, n=n, title="identity")
    lut = LUT3D.from_cube("/tmp/identity.cube")
    q = np.random.default_rng(0).random((20000, 3))
    for m in ("tri", "tet"):
        e = np.abs(lut.apply(q, m) - q).max()
        print(f"identity {m}: max err {e:.2e}")
    # interpolation must be exact at the nodes
    nodes = np.stack([rr.ravel(), gg.ravel(), bb.ravel()], -1)
    print("node exactness:", np.abs(lut.apply(nodes, "tet") - nodes).max())
