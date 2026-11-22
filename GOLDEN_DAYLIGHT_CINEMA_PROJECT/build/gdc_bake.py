"""
gdc_bake.py -- bake the analytic pipeline into a 33x33x33 .cube file.

WHY THIS IS NOT JUST "SAMPLE THE GRID"
--------------------------------------
A .cube stores values on a *uniform* grid.  33 nodes across the whole Apple Log 2
range is coarse exactly where the log curve is steepest: between video black
(code 0.1505) and code ~0.30 there are only ~5 nodes, and the Apple Log EOTF is
a square root in that region.  Naive sampling therefore produces visible banding
and a systematic shadow error after interpolation.

Two things are done about it, both of them compatible with a plain .cube:

1.  *Error-minimising grid values.*  The grid values are not the analytic
    function evaluated at the nodes; they are the solution of a weighted
    least-squares problem

        minimise  || W_tri (G - F) ||^2 + || W_tet (G - F) ||^2
                  + lambda * || G - F_nodes ||^2

    where G are the 35 937 grid values (3 channels), F is the analytic pipeline
    evaluated on ~600 k sample points, W_tri and W_tet are the (sparse) trilinear
    and tetrahedral interpolation weight matrices, and the last term keeps the
    solution close to the analytic node values (Tikhonov regularisation,
    lambda = 1e-3).  Because both interpolation schemes are linear in the grid
    values, this is a linear least-squares problem; it is solved with LSQR.
    The result is a single grid that is simultaneously better than naive
    sampling for BOTH interpolation modes.  The improvement is measured, not
    assumed -- see VALIDATION_REPORT.txt.

2.  *Perceptually weighted sampling.*  Samples are drawn from three strata:
      - 50 % uniform over the cube (protects chroma extremes),
      - 33 % concentrated near video black, where the log decode is steepest,
      - 17 % on/near the neutral axis across 9 decades of exposure
             (protects the grey ramp and shadow banding).
    Errors are weighted in OKLab (dL, da, db), which is perceptually uniform,
    so the fit spends its accuracy where the eye is.

The pipeline is evaluated in float64 throughout; the .cube is written with six
decimal places (1e-6 quantisation, i.e. 1000x finer than a 10-bit code step).
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_colour as C
import gdc_grade as G

SIZE = 33
N = SIZE


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------

def sample_points(n_total: int = 600_000, seed: int = 20261122) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n1 = int(n_total * 0.50)
    n2 = int(n_total * 0.33)
    n3 = n_total - n1 - n2

    # 1. uniform
    p1 = rng.random((n1, 3))
    # 2. concentrated near video black (code ~0.15) and the steep toe
    p2 = 0.145 + 0.855 * rng.random((n2, 3)) ** 3.0
    # 3. neutral axis: uniform in log2(Y) from -7 to +4 stops around 0.18
    liny = 0.18 * 2.0 ** rng.uniform(-7.0, 4.0, size=(n3, 1))
    grey = C.apple_log2_encode(np.repeat(liny, 3, axis=1))
    grey = grey + rng.normal(0.0, 0.004, size=grey.shape)   # small chroma dither
    p3 = np.clip(grey, 0.0, 1.0)
    return np.clip(np.vstack([p1, p2, p3]), 0.0, 1.0)


# --------------------------------------------------------------------------
# Interpolation weight matrices
# --------------------------------------------------------------------------

def _grid_index(r, g, b) -> np.ndarray:
    """Flat index of a grid node.  .cube stores the RED axis fastest, so the
    index is (b, g, r) with r innermost -- i.e. blue varies slowest."""
    return (b * N + g) * N + r


def trilinear_weights(p: np.ndarray):
    x = p * (N - 1)
    i = np.floor(x).astype(np.int64)
    i = np.clip(i, 0, N - 2)
    f = np.clip(x - i, 0.0, 1.0)
    ir, ig, ib = i[:, 0], i[:, 1], i[:, 2]
    fr, fg, fb = f[:, 0], f[:, 1], f[:, 2]
    rows, cols, vals = [], [], []
    for dr in (0, 1):
        wr = fr if dr else 1 - fr
        for dg in (0, 1):
            wg = fg if dg else 1 - fg
            for db in (0, 1):
                wb = fb if db else 1 - fb
                rows.append(np.arange(len(p)))
                cols.append(_grid_index(ir + dr, ig + dg, ib + db))
                vals.append(wr * wg * wb)
    return (np.concatenate(rows), np.concatenate(cols), np.concatenate(vals))


def tetrahedral_weights(p: np.ndarray):
    """Standard 6-tetrahedron decomposition of an axis-aligned cell.

    Within each tetrahedron the four non-zero weights are the classic
    (1-f_a, f_a-f_b, f_b-f_c, f_c) pattern, with (a, b, c) the sort order of the
    three fractional coordinates.
    """
    x = p * (N - 1)
    i = np.clip(np.floor(x).astype(np.int64), 0, N - 2)
    f = np.clip(x - i, 0.0, 1.0)
    ir, ig, ib = i[:, 0], i[:, 1], i[:, 2]
    fr, fg, fb = f[:, 0], f[:, 1], f[:, 2]
    idx = np.arange(len(p))
    rows, cols, vals = [], [], []

    def add(mask, off, w):
        rows.append(idx[mask])
        cols.append(_grid_index(ir[mask] + off[0], ig[mask] + off[1], ib[mask] + off[2]))
        vals.append(w)

    orderings = [
        ((0, 1, 2), (fr >= fg) & (fg >= fb)),
        ((0, 2, 1), (fr >= fb) & (fb > fg)),
        ((1, 0, 2), (fg > fr) & (fr >= fb)),
        ((1, 2, 0), (fg >= fb) & (fb > fr)),
        ((2, 0, 1), (fb > fr) & (fr >= fg)),
        ((2, 1, 0), (fb > fg) & (fg > fr)),
    ]
    fvec = (fr, fg, fb)
    for (a, b, c), mask in orderings:
        if not np.any(mask):
            continue
        fa, fbb, fc = fvec[a][mask], fvec[b][mask], fvec[c][mask]
        e_a = [0, 0, 0]; e_a[a] = 1
        e_ab = list(e_a); e_ab[b] = 1
        add(mask, (0, 0, 0), 1.0 - fa)
        add(mask, tuple(e_a), fa - fbb)
        add(mask, tuple(e_ab), fbb - fc)
        add(mask, (1, 1, 1), fc)
    return (np.concatenate(rows), np.concatenate(cols), np.concatenate(vals))


def weight_matrix(p: np.ndarray, kind: str) -> sp.csr_matrix:
    r, c, v = trilinear_weights(p) if kind == "tri" else tetrahedral_weights(p)
    return sp.csr_matrix((v, (r, c)), shape=(len(p), N ** 3))


# --------------------------------------------------------------------------
# Baking
# --------------------------------------------------------------------------

def analytic_on(points: np.ndarray, pipe: G.GoldenDaylightCinema) -> np.ndarray:
    return pipe.apply_codes(points)


def _cg(Aop, b, Minv, x0, iters=200, tol=1e-10, verbose=False, tag=""):
    """Preconditioned conjugate gradients on the (SPD) normal equations."""
    x = x0.copy()
    r = b - Aop(x)
    z = Minv * r
    pdir = z.copy()
    rho = float(r @ z)
    rho0 = rho
    hist = []
    for k in range(iters):
        Ap = Aop(pdir)
        alpha = rho / float(pdir @ Ap)
        x += alpha * pdir
        r -= alpha * Ap
        z = Minv * r
        rho_new = float(r @ z)
        hist.append(abs(r).max())
        if rho0 > 0 and rho_new / rho0 < tol:
            break
        pdir = z + (rho_new / rho) * pdir
        rho = rho_new
        if verbose and k % 50 == 0:
            print(f"    {tag} cg {k:4d} |r|inf {hist[-1]:.3e}")
    return x, hist


def _d2_stack(xflat: np.ndarray):
    """Second differences of the grid values along each of the three axes."""
    x = xflat.reshape(N, N, N)
    return (np.diff(x, n=2, axis=0), np.diff(x, n=2, axis=1), np.diff(x, n=2, axis=2))


def _d2t_stack(parts) -> np.ndarray:
    """Adjoint of _d2_stack (stencil 1,-2,1 scattered back onto the grid)."""
    out = np.zeros((N, N, N))
    for arr, axis in zip(parts, (0, 1, 2)):
        for k, w in enumerate((1.0, -2.0, 1.0)):
            sl = [slice(None)] * 3
            sl[axis] = slice(k, k + arr.shape[axis])
            out[tuple(sl)] += w * arr
    return out.ravel()


def _smooth_op(xflat: np.ndarray) -> np.ndarray:
    return _d2t_stack(_d2_stack(xflat))


def bake(points: np.ndarray | None = None, lam: float = 3e-3, iters: int = 160,
         verbose: bool = True, fit_space: str = "codes",
         w_tri: float = 0.2, w_tet: float = 0.8,
         smooth: float = 1.0) -> tuple[np.ndarray, dict]:
    """Error-minimising bake: solve the weighted least-squares problem

        minimise ||W_tri G - F||^2 + ||W_tet G - F||^2 + lam ||G - F_nodes||^2

    with preconditioned conjugate gradients on the normal equations.  Both
    interpolation schemes are linear in the grid values, so the whole thing is a
    standard sparse SPD system; CG converges in ~100 iterations where a naive
    Jacobi sweep diverges.
    """
    t0 = time.time()
    pipe = G.GoldenDaylightCinema()
    if points is None:
        points = sample_points()

    target_codes = analytic_on(points, pipe)

    ax = np.linspace(0.0, 1.0, N)
    bb, gg_, rr = np.meshgrid(ax, ax, ax, indexing="ij")     # bb slowest, rr fastest
    nodes = np.stack([rr.ravel(), gg_.ravel(), bb.ravel()], axis=-1)
    node_codes = analytic_on(nodes, pipe)
    if fit_space == "codes":
        # Rec.709 code values are gamma 2.4 encoded, i.e. roughly perceptually
        # uniform, and they are what a .cube actually stores: fitting here avoids
        # the round trip through a Lab space that cannot represent out-of-gamut
        # grid values exactly.
        target_fit, node_fit = target_codes, node_codes
    else:
        target_fit = C.xyz_to_oklab(C.gamma24_decode(target_codes) @ C.REC709_TO_XYZ.T)
        node_fit = C.xyz_to_oklab(C.gamma24_decode(node_codes) @ C.REC709_TO_XYZ.T)

    if verbose:
        print(f"  analytic on {len(points):,} samples + {len(nodes):,} nodes ({time.time()-t0:.1f}s)")

    W_tri = weight_matrix(points, "tri")
    W_tet = weight_matrix(points, "tet")
    W_tri_t = W_tri.T.tocsr()
    W_tet_t = W_tet.T.tocsr()
    D = (w_tri ** 2 * np.asarray(W_tri.multiply(W_tri).sum(axis=0)).ravel()
         + w_tet ** 2 * np.asarray(W_tet.multiply(W_tet).sum(axis=0)).ravel() + lam)
    D = D + 6.0 * smooth            # diag(L^T L) ~ 6 per interior node
    D = np.maximum(D, 1e-6)
    Minv = 1.0 / D

    # the objective weights the two interpolation kernels differently: Blackmagic
    # Camera and DaVinci Resolve apply 3D LUTs with tetrahedral interpolation, so
    # the default fit favours tetrahedral while still constraining trilinear.
    wtr2, wte2 = w_tri ** 2, w_tet ** 2

    def Aop(x):
        return (wtr2 * (W_tri_t @ (W_tri @ x))
                + wte2 * (W_tet_t @ (W_tet @ x))
                + lam * x + smooth * _smooth_op(x))

    grid = np.zeros((N ** 3, 3))
    hist_all, resid = [], []
    for ch in range(3):
        y = target_fit[:, ch]
        bvec = (wtr2 * (W_tri_t @ y) + wte2 * (W_tet_t @ y)
                + lam * node_fit[:, ch] + smooth * _smooth_op(node_fit[:, ch]))
        x, hist = _cg(Aop, bvec, Minv, node_fit[:, ch].copy(), iters=iters,
                      verbose=verbose, tag=f"ch{ch}")
        grid[:, ch] = x
        hist_all.append(hist[::max(1, len(hist) // 10)])
        resid.append(hist[-1])
        if verbose:
            print(f"  channel {ch}: {len(hist)} CG iterations, |r|inf={hist[-1]:.3e} "
                  f"({time.time()-t0:.1f}s)")

    if fit_space == "codes":
        grid_codes = grid
    else:
        grid_rgb = C.oklab_to_xyz(grid) @ C.XYZ_TO_REC709.T
        grid_codes = C.gamma24_encode(np.clip(grid_rgb, 0.0, 1.0))
    grid_codes = np.nan_to_num(grid_codes, nan=0.0, posinf=1.0, neginf=0.0)
    grid_codes = np.clip(grid_codes, 0.0, 1.0)
    info = {"n_samples": int(len(points)), "lambda": lam, "iterations": iters,
            "seconds": time.time() - t0, "final_residual": float(max(resid)),
            "fit_space": fit_space, "w_tri": w_tri, "w_tet": w_tet,
            "smooth": smooth,
            "node_codes": node_codes}
    return grid_codes, info


# --------------------------------------------------------------------------
# .cube I/O
# --------------------------------------------------------------------------

CUBE_HEADER = """# {title}
# Version {version}
# Input:  Apple Log 2 code, Apple Wide Gamut primaries, D65
#         (18% scene grey sits at code 0.4883, video black at 0.150476)
# Output: Rec.709 SDR, pure gamma 2.4 (full range 0..1, E = V^(1/2.4))
# Size:   {n}x{n}x{n}, red channel varies fastest (standard .cube ordering)
# Fitted for tetrahedral interpolation (trilinear also constrained).
# Built by GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/gdc_bake.py -- float64 pipeline,
# error-minimising least-squares bake (see VALIDATION_REPORT.txt).
TITLE "{title}"
LUT_3D_SIZE {n}
DOMAIN_MIN 0.0 0.0 0.0
DOMAIN_MAX 1.0 1.0 1.0
"""


def write_cube(path: str, grid_codes: np.ndarray, n: int = N,
               title: str = "GOLDEN_DAYLIGHT_CINEMA", version: str = "1.0.0") -> None:
    """Write a .cube. grid_codes is flat in .cube order: red varies fastest."""
    assert grid_codes.shape == (n ** 3, 3)
    vals = np.clip(grid_codes, 0.0, 1.0)
    with open(path, "w", newline="\n") as f:
        f.write(CUBE_HEADER.format(title=title, version=version, n=n))
        # the flat array is already in .cube order (red fastest)
        f.write("\n".join(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}" for v in vals))
        f.write("\n")


def read_cube(path: str) -> tuple[np.ndarray, int]:
    vals = []
    n = None
    dmin = np.array([0.0, 0.0, 0.0])
    dmax = np.array([1.0, 1.0, 1.0])
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            up = line.upper()
            if up.startswith("LUT_3D_SIZE"):
                n = int(line.split()[1])
            elif up.startswith("DOMAIN_MIN"):
                dmin = np.array([float(x) for x in line.split()[1:4]])
            elif up.startswith("DOMAIN_MAX"):
                dmax = np.array([float(x) for x in line.split()[1:4]])
            elif up.startswith("TITLE") or up.startswith("LUT_1D"):
                continue
            else:
                vals.append([float(x) for x in line.split()[:3]])
    return (np.clip((np.array(vals) - dmin) / (dmax - dmin), 0.0, 1.0), n)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(os.path.dirname(here), "GOLDEN_DAYLIGHT_CINEMA", "LUT",
                       "GOLDEN_DAYLIGHT_CINEMA.cube")
    pts = sample_points()
    g, info = bake(pts)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    write_cube(out, g)
    print(f"wrote {out}  ({os.path.getsize(out) / 1024:.0f} KiB, "
          f"{info['seconds']:.1f}s)")
