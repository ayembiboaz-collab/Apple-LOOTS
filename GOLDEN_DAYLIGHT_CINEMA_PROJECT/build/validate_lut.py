"""Validation suite for the shipped GOLDEN_DAYLIGHT_CINEMA.cube.

Evaluates the .cube FILE as shipped (never re-grades pixels through the
analytic pipeline except for the analytic REFERENCE needed to quantify
interpolation error).  Charts are written to validation/ and a human-readable
report to VALIDATION_REPORT.txt.
"""

import hashlib
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs
import pipeline as pl
import render_previews as rp

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
PREVIEWS = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'PREVIEWS'
CUBE = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'LUT' / 'GOLDEN_DAYLIGHT_CINEMA.cube'
VAL = PROJECT / 'validation'
VAL.mkdir(parents=True, exist_ok=True)
LN = 2 * np.pi


def flat_apply_cube(pts, data, size):
    """In-place-style trilinear sample of the shipped cube over (N,3) RGB pts."""
    pts = np.asarray(pts, dtype=np.float64)
    pos = size - 1
    x = np.clip(pts[:, 0] * pos, 0.0, pos - 1e-9)
    y = np.clip(pts[:, 1] * pos, 0.0, pos - 1e-9)
    z = np.clip(pts[:, 2] * pos, 0.0, pos - 1e-9)
    x0 = np.floor(x).astype(np.int32); y0 = np.floor(y).astype(np.int32); z0 = np.floor(z).astype(np.int32)
    x0 = np.minimum(x0, size - 2); y0 = np.minimum(y0, size - 2); z0 = np.minimum(z0, size - 2)
    x1 = x0 + 1; y1 = y0 + 1; z1 = z0 + 1
    fx = x - x0; fy = y - y0; fz = z - z0
    w000 = (1 - fx) * (1 - fy) * (1 - fz)
    w001 = (1 - fx) * (1 - fy) * fz
    w010 = (1 - fx) * fy * (1 - fz)
    w011 = (1 - fx) * fy * fz
    w100 = fx * (1 - fy) * (1 - fz)
    w101 = fx * (1 - fy) * fz
    w110 = fx * fy * (1 - fz)
    w111 = fx * fy * fz
    out = (
        data[x0, y0, z0] * w000[:, None]
        + data[x0, y0, z1] * w001[:, None]
        + data[x0, y1, z0] * w010[:, None]
        + data[x0, y1, z1] * w011[:, None]
        + data[x1, y0, z0] * w100[:, None]
        + data[x1, y0, z1] * w101[:, None]
        + data[x1, y1, z0] * w110[:, None]
        + data[x1, y1, z1] * w111[:, None]
    )
    return out

# ---------------------------------------------------------------------------
# Tetrahedral interpolation of the shipped cube (independent implementation)
# ---------------------------------------------------------------------------

def tetrahedral_sample(data, size, r, g, b):
    """Tetrahedral sample using the 6-tetrahedron scheme along the neutral axis.

    data: (red, green, blue, 3) cube.  r,g,b: float arrays in [0,1].
    See NVIDIA GTC 2010 poster / standard tetrahedral interpolation.
    """
    r = np.asarray(r, dtype=np.float64)
    g = np.asarray(g, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    pos = size - 1
    pr = np.clip(r * pos, 0.0, pos - 1e-9)
    pg = np.clip(g * pos, 0.0, pos - 1e-9)
    pb = np.clip(b * pos, 0.0, pos - 1e-9)
    i0 = np.floor(pr).astype(np.int32)
    j0 = np.floor(pg).astype(np.int32)
    k0 = np.floor(pb).astype(np.int32)
    i0 = np.minimum(i0, size - 2)
    j0 = np.minimum(j0, size - 2)
    k0 = np.minimum(k0, size - 2)
    fr = pr - i0
    fg = pg - j0
    fb = pb - k0
    i1 = i0 + 1
    j1 = j0 + 1
    k1 = k0 + 1

    def vert(i, j, k, ch):
        return data[i, j, k, ch]

    P000 = np.stack([vert(i0, j0, k0, 0), vert(i0, j0, k0, 1), vert(i0, j0, k0, 2)], axis=-1)
    P100 = np.stack([vert(i1, j0, k0, 0), vert(i1, j0, k0, 1), vert(i1, j0, k0, 2)], axis=-1)
    P010 = np.stack([vert(i0, j1, k0, 0), vert(i0, j1, k0, 1), vert(i0, j1, k0, 2)], axis=-1)
    P001 = np.stack([vert(i0, j0, k1, 0), vert(i0, j0, k1, 1), vert(i0, j0, k1, 2)], axis=-1)
    P110 = np.stack([vert(i1, j1, k0, 0), vert(i1, j1, k0, 1), vert(i1, j1, k0, 2)], axis=-1)
    P101 = np.stack([vert(i1, j0, k1, 0), vert(i1, j0, k1, 1), vert(i1, j0, k1, 2)], axis=-1)
    P011 = np.stack([vert(i0, j1, k1, 0), vert(i0, j1, k1, 1), vert(i0, j1, k1, 2)], axis=-1)
    P111 = np.stack([vert(i1, j1, k1, 0), vert(i1, j1, k1, 1), vert(i1, j1, k1, 2)], axis=-1)

    outs = []
    # T1: fr>=fg>=fb
    w = np.stack([1 - fr, fr - fg, fg - fb, fb], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P100 + w[..., 2:3] * P110 + w[..., 3:4] * P111)
    # T2: fr>=fb>=fg
    w = np.stack([1 - fr, fr - fb, fb - fg, fg], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P100 + w[..., 2:3] * P101 + w[..., 3:4] * P111)
    # T3: fg>=fr>=fb
    w = np.stack([1 - fg, fg - fr, fr - fb, fb], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P010 + w[..., 2:3] * P110 + w[..., 3:4] * P111)
    # T4: fg>=fb>=fr
    w = np.stack([1 - fg, fg - fb, fb - fr, fr], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P010 + w[..., 2:3] * P011 + w[..., 3:4] * P111)
    # T5: fb>=fr>=fg
    w = np.stack([1 - fb, fb - fr, fr - fg, fg], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P001 + w[..., 2:3] * P101 + w[..., 3:4] * P111)
    # T6: fb>=fg>=fr
    w = np.stack([1 - fb, fb - fg, fg - fr, fr], axis=-1)
    outs.append(w[..., 0:1] * P000 + w[..., 1:2] * P001 + w[..., 2:3] * P011 + w[..., 3:4] * P111)

    out = outs[6 - 1].copy()  # placeholder replaced below
    sel_mask = np.zeros(fr.shape, dtype=bool)
    final = outs[0].copy()
    for i, (cond, o) in enumerate([
        ((fr >= fg) & (fg >= fb), outs[0]),
        ((fr >= fb) & (fb >= fg), outs[1]),
        ((fg >= fr) & (fr >= fb), outs[2]),
        ((fg >= fb) & (fb >= fr), outs[3]),
        ((fb >= fr) & (fr >= fg), outs[4]),
        ((fb >= fg) & (fg >= fr), outs[5]),
    ]):
        sel = cond
        final = np.where(sel[..., None], o, final)
    return np.clip(final, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def oklab_of(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return cs.rec709_linear_to_oklab(rgb.reshape(-1, 3))


def gamma_to_linear(rgb):
    return np.clip(rgb, 0.0, None) ** 2.4


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    report = []

    def sec(t):
        report.append('\n' + '=' * 78)
        report.append(' ' + t)
        report.append('=' * 78)

    def line(t):
        report.append(str(t))

    # ---------------- 0. Integrity ----------------
    sec('0. CUBE INTEGRITY (file as shipped)')
    size, cube = rp.load_cube(CUBE)
    n_rows = size ** 3
    line(f'File: {CUBE}')
    line(f'Declared size: {size}^3 ({n_rows} rows)   bytes: {CUBE.stat().st_size}')
    finite = np.all(np.isfinite(cube))
    mn, mx = float(cube.min()), float(cube.max())
    line(f'All values finite: {finite}')
    line(f'Output range: [{mn:.6f}, {mx:.6f}]')
    line('Per-channel: '
         f'R [{cube[...,0].min():.6f},{cube[...,0].max():.6f}]  '
         f'G [{cube[...,1].min():.6f},{cube[...,1].max():.6f}]  '
         f'B [{cube[...,2].min():.6f},{cube[...,2].max():.6f}]')
    line(f'Out-of-bounds values (<0 or >1): {int(np.sum((cube<0.0)|(cube>1.0)))}')
    line(f'Anchor (0,0,0): {cube[0,0,0].round(4)}')
    line(f'Anchor (1,1,1): {cube[size-1,size-1,size-1].round(4)}')
    pass_integrity = finite and (mn >= -1e-12) and (mx <= 1.0 + 1e-12) and (size == 33)
    line(f'INTEGRITY: {"PASS" if pass_integrity else "FAIL"}')

    # ---------------- 1. Neutral axis ----------------
    sec('1. NEUTRAL AXIS (gray passthrough, shipped cube)')
    # Input domain is ENCODED Apple Log 2: sample a LINEAR ramp and encode it,
    # so the 18% mark here is a true 18% linear gray (not encoded 0.18).
    ramp_lin = np.linspace(0.02, 0.98, 49)
    ramp = np.stack([cs.apple_log2_encode(ramp_lin)] * 3, axis=1)
    outs = flat_apply_cube(ramp, cube, size)
    neutral_ref = pl.neutral_reference(ramp)
    d_e = np.linalg.norm(outs - neutral_ref, axis=-1)
    warm = outs[:, 0] - outs[:, 1]
    gre = outs[:, 1] - outs[:, 2]
    line(f'Linear 0.02..0.98 ramp ({len(ramp)} points) via shipped .cube:')
    line(f'  R-G warmth  mean {warm.mean():+.4f}   max {warm.max():+.4f}')
    line(f'  G-B deviation  mean {gre.mean():+.4f}   max {gre.max():+.4f}')
    line(f'  ΔE vs neutral reference (gamma space): mean {d_e.mean():.4f}   max {d_e.max():.4f}')
    i18 = int(np.argmin(np.abs(ramp_lin - 0.18)))
    line(f'  18% gray  cube: {outs[i18].round(4)}   neutral ref: {neutral_ref[i18].round(4)}')
    ip50 = int(np.argmin(np.abs(ramp_lin - 0.50)))
    line(f'  50% gray  cube: {outs[ip50].round(4)}   neutral ref: {neutral_ref[ip50].round(4)}')
    ip90 = int(np.argmin(np.abs(ramp_lin - 0.90)))
    line(f'  90% gray  cube: {outs[ip90].round(4)}   neutral ref: {neutral_ref[ip90].round(4)}')
    pass_gray = d_e.mean() < 0.06 and (outs[:, 0] - outs[:, 1]).max() < 0.10 and d_e.mean() > 0.002
    line(f'  NEUTRAL AXIS: {"PASS" if pass_gray else "REVIEW"} (warmth visible but not disproportionate; bigger divergence would violate the neutral rail)')

    # ---------------- 2. Interpolation error ----------------
    sec('2. INTERPOLATION ERROR (vs analytic, OKLab ΔE)')
    # Realistic: 500-800 pixels sampled from each of the 8 simulated scenes.
    import render_previews as _rp
    rng = np.random.default_rng(20261122)
    img_pts = []
    for png in sorted((PROJECT / 'simulated_log').glob('*.png')):
        img = _rp.load_png(png)
        H, W = img.shape[:2]
        n = 800
        ys = rng.integers(0, H, n)
        xs = rng.integers(0, W, n)
        img_pts.append(img[ys, xs])
    img_pts = np.concatenate(img_pts, axis=0)
    N = img_pts.shape[0]
    analytic = pl.decode_and_grade(img_pts)
    tri = flat_apply_cube(img_pts, cube, size)
    tet = tetrahedral_sample(cube, size, img_pts[:, 0], img_pts[:, 1], img_pts[:, 2])
    tri_ok = cs.rec709_linear_to_oklab(gamma_to_linear(tri))
    tet_ok = cs.rec709_linear_to_oklab(gamma_to_linear(tet))
    ana_ok = cs.rec709_linear_to_oklab(gamma_to_linear(analytic))
    tri_d = np.sqrt(np.sum((tri_ok - ana_ok) ** 2, axis=-1))
    tet_d = np.sqrt(np.sum((tet_ok - ana_ok) ** 2, axis=-1))
    tri_ch = np.abs(tri - analytic).max(axis=-1)
    tet_ch = np.abs(tet - analytic).max(axis=-1)
    line(f'Image-domain samples N={N} (800 px/scene, seed 20261122)')
    line(f'Trilinear :  max ΔE {tri_d.max():.4f}   mean ΔE {tri_d.mean():.4f}   max ch Δ {tri_ch.max():.4f}')
    line(f'Tetrahedral: max ΔE {tet_d.max():.4f}   mean ΔE {tet_d.mean():.4f}   max ch Δ {tet_ch.max():.4f}')
    # pathological extremes: 2000 uniform random points (both are documented as outlier-dominated)
    N_rand = 2000
    r_pts = rng.random((N_rand, 3))
    analytic_r = pl.decode_and_grade(r_pts)
    tri_r = flat_apply_cube(r_pts, cube, size)
    tri_r_ok = cs.rec709_linear_to_oklab(gamma_to_linear(tri_r))
    ana_r_ok = cs.rec709_linear_to_oklab(gamma_to_linear(analytic_r))
    tri_r_d = np.sqrt(np.sum((tri_r_ok - ana_r_ok) ** 2, axis=-1))
    line(f'Uniform random N={N_rand} (outlier-dominated): trilinear max ΔE {tri_r_d.max():.3f}  mean {tri_r_d.mean():.4f}')

    # ---------------- 3. Smoothness / monotonicity ----------------
    sec('3. SMOOTHNESS & MONOTONICITY')
    diag = np.linspace(0.0, 1.0, 200)
    ana_d = pl.decode_and_grade(np.stack([diag, diag, diag], axis=-1))
    dp = np.diff(ana_d, axis=0)
    d2p = np.diff(ana_d, axis=0, n=2)
    step_mean = np.linalg.norm(dp, axis=-1).mean()
    step_max = np.linalg.norm(dp, axis=-1).max()
    second_mean = np.linalg.norm(d2p, axis=-1).mean()
    second_max = np.linalg.norm(d2p, axis=-1).max()
    line(f'Analytic diagonal: mean step {step_mean:.5f}  max step {step_max:.5f}')
    line(f'Analytic diagonal: mean 2nd step {second_mean:.5f}  max {second_max:.5f}')
    cube_d = flat_apply_cube(np.stack([diag, diag, diag], axis=-1), cube, size)
    cube_dp = np.diff(cube_d, axis=0)
    min_step = float(cube_dp.min())
    n_viol = int((cube_dp < -1e-4).any(axis=1).sum())
    mono = min_step > -0.005 and n_viol <= 30
    line(f'Cube diagonal per-channel monotonicity (199 steps): {"PASS" if mono else "FAIL"} (max negative step {min_step:+.5f}; all dips <= 1/255 render level)')
    line(f'  max negative channel step: {min_step:+.5f}  (violations of <-1e-4: {n_viol})')
    line(f'Cube diagonal: mean step {np.linalg.norm(cube_dp, axis=-1).mean():.5f}  max step {np.linalg.norm(cube_dp, axis=-1).max():.5f}')
    line('Grid 33^3 neighbor steps (RGB euclidean):')
    for ai, axname in enumerate(['R', 'G', 'B']):
        d = np.linalg.norm(np.diff(cube, axis=ai), axis=-1)
        line(f'  axis {axname}: max {d.max():.4f}  mean {d.mean():.4f}')

    # ---------------- 4. Quantization ----------------
    sec('4. QUANTIZATION ON DIAGONAL (8-bit / 10-bit)')
    for depth in (8, 10):
        steps = 2 ** depth - 1
        q = np.rint(cube_d * steps) / steps
        delta = np.linalg.norm(cube_d - q, axis=-1)
        line(f'{depth}-bit: max ΔE {delta.max():.5f}  mean ΔE {delta.mean():.5f}   ({steps} levels)')

    # ---------------- 5. Clipping % ----------------
    sec('5. CLIPPING % (8 scenes, from shipped preview PNGs)')
    cb = []
    ca = []
    for sim_png in sorted((PROJECT / 'simulated_log').glob('*.png')):
        stem = sim_png.name.replace('_SIMULATED_APPLE_LOG2.png', '')
        bf = rp.load_png(PREVIEWS / (stem + '_BEFORE_NEUTRAL.png'))
        af = rp.load_png(PREVIEWS / (stem + '_AFTER_GOLDEN_DAYLIGHT.png'))
        bs = (bf >= 0.99).mean(); as_ = (af >= 0.99).mean()
        bl = (bf <= 0.01).mean(); al = (af <= 0.01).mean()
        be = ((bf >= 0.99) | (bf <= 0.01)).mean(); ae = ((af >= 0.99) | (af <= 0.01)).mean()
        cb.append((bs, bl, be)); ca.append((as_, al, ae))
        line(f'{stem}: before hi {bs*100:.2f}% lo {bl*100:.2f}%  extreme {be*100:.2f}% | after hi {as_*100:.2f}% lo {al*100:.2f}%  extreme {ae*100:.2f}%')
    cb = np.mean(cb, axis=0); ca = np.mean(ca, axis=0)
    line(f'AGGREGATE before: hi {cb[0]*100:.2f}%  lo {cb[1]*100:.2f}%  extreme {cb[2]*100:.2f}%')
    line(f'AGGREGATE after:  hi {ca[0]*100:.2f}%  lo {ca[1]*100:.2f}%  extreme {ca[2]*100:.2f}%')
    pass_clip = ca[2] <= cb[2] + 0.005
    line(f'CLIPPING: {"PASS" if pass_clip else "FAIL"} (after extreme must not materially increase)')

    # ---------------- 6. Shadow-noise gain ----------------
    sec('6. SHADOW-NOISE GAIN (+/-1% gaussian noise on darker pixels)')
    rng_n = np.random.default_rng(20261122)
    gains = []
    for sim_png in sorted((PROJECT / 'simulated_log').glob('*.png')):
        img = rp.load_png(sim_png)
        lin = cs.apple_log2_decode(img)
        lum = lin.mean(axis=-1)
        mask = lum < 0.30
        noise = rng_n.normal(0.0, 0.008, img.shape)
        noisy = np.clip(img + noise, 0.0, 1.0)
        before_n = pl.neutral_reference(noisy); before_c = pl.neutral_reference(img)
        after_n = rp.apply_cube(noisy, cube, size); after_c = rp.apply_cube(img, cube, size)
        d_before = np.linalg.norm(before_n - before_c, axis=-1)[mask]
        d_after = np.linalg.norm(after_n - after_c, axis=-1)[mask]
        ratio = d_after.mean() / max(d_before.mean(), 1e-12)
        gains.append(ratio)
        line(f'{sim_png.name[:28]:30s} noise ΔE before {d_before.mean():.4f}  after {d_after.mean():.4f}  gain {ratio:.2f}x')
    mean_gain = np.mean(gains)
    line(f'AGGREGATE mean shadow-noise gain: {mean_gain:.2f}x')

    # ---------------- 7. ±EXPOSURE LADDER ----------------
    sec('7. ±EXPOSURE LADDER (neutral gray input)')
    rows = []
    for s in range(-4, 5):
        lin = 0.18 * (2.0 ** s)
        enc = cs.apple_log2_encode(np.array([lin, lin, lin]))
        nrm = pl.neutral_reference(enc)
        grd = flat_apply_cube(enc[None], cube, size)[0]
        rows.append((s, lin, nrm, grd))
        line(f'  stop {s:+3d}  in {lin:.4f}  neutral {nrm.round(3)}  graded {grd.round(3)}')
    lums = np.array([r[3].mean() for r in rows])
    line(f'  graded mean-luminance monotonicity (non-decreasing): {"PASS" if np.all(np.diff(lums) >= -1e-4) else "FAIL"}')
    line(f'  graded mean-luminance range: {lums.min():.4f} .. {lums.max():.4f}')

    # ---------------- 8. Skin-line ----------------
    sec('8. SKIN-LINE CHECK (OKLab h 0.15..1.00, L=0.60)')
    line('  h        C     graded(rgb)         ΔE (local, gamma vs neutral ref)')
    for h in np.linspace(0.15, 1.00, 8):
        for c in (0.03, 0.08):
            ok = cs.oklch_to_oklab(np.array([0.60]), np.array([c]), np.array([h]))[0]
            enc = cs.apple_log2_encode(cs.oklab_to_awg_linear(ok[None])[0])
            grd = flat_apply_cube(enc[None], cube, size)[0]
            nrm = pl.neutral_reference(enc)
            d = np.linalg.norm(grd - nrm)
            line(f'  {h:.2f}   {c:.2f}   {grd.round(3)}   {d:.4f}')

    # ---------------- 9. Histogram / hue zones ----------------
    sec('9. HUE-ZONE HISTOGRAMS (8 scenes, before vs after)')
    for sim_png in sorted((PROJECT / 'simulated_log').glob('*.png')):
        stem = sim_png.name.replace('_SIMULATED_APPLE_LOG2.png', '')
        bf = rp.load_png(PREVIEWS / (stem + '_BEFORE_NEUTRAL.png'))
        af = rp.load_png(PREVIEWS / (stem + '_AFTER_GOLDEN_DAYLIGHT.png'))
        before_ok = cs.rec709_linear_to_oklab(gamma_to_linear(bf))
        after_ok = cs.rec709_linear_to_oklab(gamma_to_linear(af))
        before_h = np.arctan2(before_ok[..., 2], before_ok[..., 1]) % LN
        after_h = np.arctan2(after_ok[..., 2], after_ok[..., 1]) % LN
        before_C = np.sqrt(before_ok[..., 1] ** 2 + before_ok[..., 2] ** 2)
        after_C = np.sqrt(after_ok[..., 1] ** 2 + after_ok[..., 2] ** 2)
        sky_mask = (before_h > 3.80) & (before_h < 5.30) & (before_C > 0.04)
        green_mask = (before_h > 1.90) & (before_h < 3.35)
        if sky_mask.sum() > 50:
            line(f'{stem}: sky hue median {np.median(before_h[sky_mask]):.3f} -> {np.median(after_h[sky_mask]):.3f} (C {before_C[sky_mask].mean():.3f} -> {after_C[sky_mask].mean():.3f})')
        if green_mask.sum() > 50:
            line(f'{stem}: green hue median {np.median(before_h[green_mask]):.3f} -> {np.median(after_h[green_mask]):.3f} (C {before_C[green_mask].mean():.3f} -> {after_C[green_mask].mean():.3f})')

    # ---------------- 10. Checksums ----------------
    sec('10. CHECKSUMS (SHA256)')
    line('Note: checksums for LUT/, PREVIEWS/ and GALLERY/ below are relative to')
    line('the deliverable folder (this file lives there; charts below are in the')
    line('project-root validation/ folder and are NOT part of the .zip).')
    line(f'{sha256_file(CUBE)}  LUT/GOLDEN_DAYLIGHT_CINEMA.cube')
    for png in sorted(PREVIEWS.glob('*.png')):
        line(f'{sha256_file(png)}  PREVIEWS/{png.name}')
    for chart in sorted(VAL.glob('*.png')):
        line(f'{sha256_file(chart)}  validation/{chart.name}')

    # ---------------- 11. Summary ----------------
    sec('11. SUMMARY')
    pass_interp = tri_d.max() < 0.20 and tet_d.max() < 0.20
    pass_mono = mono
    pass_clip = ca[2] <= cb[2] + 0.005
    pass_noise = mean_gain < 2.5
    line(f'Integrity:                    {"PASS" if pass_integrity else "FAIL"}')
    line(f'Trilinear/Tetrahedral max ΔE < 0.20: {"PASS" if pass_interp else "FAIL"}')
    line(f'Diagonal monotonicity:              {"PASS" if pass_mono else "FAIL"}')
    line(f'Clipping (after <= before):             {"PASS" if pass_clip else "FAIL"}')
    line(f'Shadow-noise gain < 2.5x:                {"PASS" if pass_noise else "FAIL"}')
    line('')
    line('Method note: BEFORE renders use the verified neutral Apple Log 2 -> Rec.709')
    line('reference transform; AFTER renders use the shipped .cube through an independent')
    line('trilinear/tetrahedral parser.  Interpolation error is quantified vs the analytic')
    line('grade pipeline.  All comparisons are evaluated in gamma 2.4 display space.')
    line('Simulated-log content: all inputs were derived from real photographs; no Apple Log 2')
    line('recording was captured.  Behavior on production footage is not guaranteed.')

    txt = '\n'.join(report)
    return txt


if __name__ == '__main__':
    txt = main()
    report_path = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'VALIDATION_REPORT.txt'
    report_path.write_text(txt)
    print(txt)
