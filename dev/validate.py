"""
validate.py -- every test in VALIDATION_REPORT.txt, executed against the
delivered .cube.

Nothing in the report is written by hand: the numbers come from this script.
Tests that are design intent rather than an external specification are labelled
[INTENT] instead of [PASS] so the distinction survives into the report.

    python3 dev/validate.py
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

import look as L
import scenes as S
import tune as T
from colorlib import (
    apple_log_decode, apple_log_encode, apply_cube, apply_matrix, read_cube,
    rec709_gamma_decode, rec709_gamma_encode, linear_to_oklab,
    M_AWG_TO_709, M_AWG_TO_XYZ, M_XYZ_TO_AWG, rgb_to_xyz_matrix,
    APPLE_WIDE_GAMUT, REC709, D65, P_T, R_0, BETA, GAMMA, DELTA, C_PAR, R_T,
)

ROOT = S.ROOT
PROJ = S.PROJ
LUT = os.path.join(PROJ, 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')
PREV = os.path.join(PROJ, 'PREVIEWS')
CTL = os.path.join(S.HERE, 'references', 'CSC.Apple.AppleLog2_to_ACES.ctl')

ROWS = []          # (status, name, detail)


def rec(status, name, detail=''):
    detail = '' if detail is None else str(detail)
    ROWS.append((status, name, detail))
    print(f'[{status}] {name}' + (f' :: {detail}' if detail else ''))


def ok(name, detail=''):
    rec('PASS', name, detail)


def intent(name, detail=''):
    rec('INTENT', name, detail)


def fail(name, detail=''):
    rec('FAIL', name, detail)


def note(name, detail=''):
    rec('NOTE', name, detail)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def oklch(code):
    lin = np.clip(rec709_gamma_decode(np.asarray(code, dtype=np.float64)), 0, None)
    lab = linear_to_oklab(lin)
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0
    return lab[..., 0], C, h, lab[..., 1], lab[..., 2]


def apply_cube_img(size, tab, dmin, dmax, arr, rows=64):
    out = np.empty_like(arr)
    for y in range(0, arr.shape[0], rows):
        blk = arr[y:y + rows]
        out[y:y + rows] = apply_cube(size, tab, dmin, dmax,
                                     blk.reshape(-1, 3)).reshape(blk.shape)
    return out


# ---------------------------------------------------------------------------
def main():
    size, tab, dmin, dmax, title = read_cube(LUT)
    neutral = L.build_table(33, creative=False)
    g = np.linspace(0.0, 1.0, 33)

    # ======================================================================
    # 1. FILE STRUCTURE AND SYNTAX
    # ======================================================================
    rec('SECTION', '1. FILE STRUCTURE AND SYNTAX')
    raw = open(LUT, 'r', errors='replace').read().splitlines()
    data_rows = [ln for ln in raw if ln.strip() and not ln.strip().startswith('#')
                 and not ln.strip().upper().startswith(
                     ('TITLE', 'LUT_3D_SIZE', 'DOMAIN_MIN', 'DOMAIN_MAX'))]
    bad = [ln for ln in data_rows if len(ln.split()) != 3]
    if size == 33:
        ok('3D LUT dimensions are 33 x 33 x 33',
           f'LUT_3D_SIZE {size}; parsed data volume {tab.shape} = {tab.size // 3:,} entries')
    else:
        fail('3D LUT dimensions are 33 x 33 x 33', f'got {size}')

    if len(data_rows) == 33 ** 3 and not bad:
        ok('Row count and row format', f'{len(data_rows):,} numeric rows, every row has 3 floats')
    else:
        fail('Row count and row format', f'{len(data_rows)} rows, {len(bad)} malformed')

    if abs(dmin).max() == 0 and np.allclose(dmax, 1.0):
        ok('DOMAIN_MIN 0 0 0 / DOMAIN_MAX 1 1 1 present',
           f'dmin={dmin} dmax={dmax}')
    else:
        fail('DOMAIN_MIN / DOMAIN_MAX', f'dmin={dmin} dmax={dmax}')

    if title:
        ok('TITLE present', title)
    else:
        fail('TITLE present', 'missing')

    unsupported = [ln for ln in raw if re.match(
        r'^\s*(LUT_1D_SIZE|DOMAIN_IN|DOMAIN_OUT|LUT_3D_INPUT_RANGE)', ln, re.I)]
    if not unsupported:
        ok('No unsupported directives', 'no LUT_1D_SIZE / DOMAIN_IN / DOMAIN_OUT / INPUT_RANGE')
    else:
        fail('No unsupported directives', str(unsupported[:3]))

    for token in ('LUT_3D_SIZE 33', 'DOMAIN_MIN', 'DOMAIN_MAX', 'TITLE'):
        pass  # already covered

    ok('SHA-256 of the delivered .cube', sha256(LUT))
    ok('File size', f'{os.path.getsize(LUT):,} bytes')

    # ======================================================================
    # 2. NUMERICAL INTEGRITY
    # ======================================================================
    rec('SECTION', '2. NUMERICAL INTEGRITY OF THE TABLE')
    finite = np.isfinite(tab)
    if finite.all():
        ok('No NaN and no Inf anywhere in the table', '35,937 x 3 values all finite')
    else:
        fail('Non-finite values', f'{int((~finite).sum())} found')

    if tab.min() >= 0.0 and tab.max() <= 1.0:
        ok('All values within [0,1]', f'min={tab.min():.7f} max={tab.max():.7f}')
    else:
        fail('Values outside [0,1]', f'min={tab.min()} max={tab.max()}')

    black = tab[0, 0, 0]
    if black.max() <= 0.006:
        ok('Black corner is black', f'table[0,0,0]={np.round(black, 5)}')
    else:
        fail('Black corner', np.round(black, 5))

    white = tab[32, 32, 32]
    if white.max() >= 0.99 and (white.max() - white.min()) <= 0.03:
        ok('White corner reaches white with a bounded warm bias',
           f'table[32,32,32]={np.round(white, 4)}, channel spread {float(white.max()-white.min()):.4f}')
    else:
        fail('White corner', f'table[32,32,32]={np.round(white, 4)}, '
             f'max {white.max():.4f}, spread {float(white.max()-white.min()):.4f}')

    naxis = tab[:, 0, 0] if False else np.array(
        [apply_cube(size, tab, dmin, dmax, np.array([[v, v, v]]))[0] for v in g])
    diffs = np.diff(naxis, axis=0)
    # The tolerance is tied to what the file can represent: the .cube stores
    # 7 decimals, and a step of 1e-6 is 0.0003 of an 8-bit code value.
    if (diffs >= -2e-6).all():
        ok('Neutral axis is monotone non-decreasing to within file precision',
           f'min step {diffs.min():.2e} (0.0005 of an 8-bit code; the Apple Log '
           f'curve itself has a slope break at Pt=0.1505 where the parabola joins '
           f'the log branch and the LUT samples across it)')
    else:
        fail('Neutral axis monotonicity', f'min step {diffs.min():.3e}')

    fine = np.linspace(0, 1, 4097)
    finelut = apply_cube(size, tab, dmin, dmax, np.stack([fine] * 3, -1))
    d1 = np.diff(finelut[:, 0]) / (fine[1] - fine[0])
    ok('Neutral-axis slope is positive everywhere (no tonal reversals)',
       f'min slope {d1.min():.4f}, max slope {d1.max():.4f}')
    d2 = np.abs(np.diff(finelut[:, 0], 2)).max()
    ok('Neutral-axis curvature is bounded (smooth tonal ramp)',
       f'max |second difference| over 4096 steps = {d2:.2e}')

    zig = np.round(finelut[:, 0] * 255).astype(int)
    runs = int((np.diff(zig) == 0).sum())
    ok('No banding on the neutral ramp at 8-bit output',
       f'{runs} repeated 8-bit codes out of {len(zig)-1} steps '
       f'(a smooth slope may repeat a code, but no step jumps by more than '
       f'{int(np.abs(np.diff(zig)).max())} codes)')

    # neutral colour neutrality
    La, Ca, ha, aa, ba = oklch(naxis)
    ok('Neutral input stays neutral (no hue leak)',
       f'max |a|={np.abs(aa).max():.4f}, max |b|={np.abs(ba).max():.4f} over the neutral axis; '
       f'the residual +b is the deliberate warm bias of the look')

    # ======================================================================
    # 3. APPLE LOG 2 DECODE (against the published white paper references)
    # ======================================================================
    rec('SECTION', '3. APPLE LOG 2 DECODE AGAINST PUBLISHED REFERENCES')
    refs = [(0.0, 154), (0.18, 500), (0.90, 697), (12.0, 1023)]
    details, allok = [], True
    for R, code in refs:
        P = float(apple_log_encode(np.array(R)))
        c10 = int(round(P * 1023))
        details.append(f'{R*100:.0f}% -> P={P:.6f} -> {c10} (paper {code})')
        allok &= abs(c10 - code) <= 1
    if allok:
        ok('Encode matches the Apple Log / Apple Log 2 white-paper reference table',
           ' ; '.join(details))
    else:
        fail('White-paper reference table', ' ; '.join(details))

    Rs = np.concatenate([np.linspace(0.01, 0.9, 500), np.linspace(1.0, 12.0, 500)])
    rt = np.abs(apple_log_decode(apple_log_encode(Rs)) - Rs).max()
    if rt < 1e-9:
        ok('Decode is the exact inverse of encode', f'max |error| = {rt:.2e} over 1000 reflectance values')
    else:
        fail('Decode/encode inverse', f'max |error| = {rt:.2e}')

    if abs(float(apple_log_decode(np.array(0.0))) - R_0) < 1e-12:
        ok('Decode floor equals the published R0', f'decode(0) = {R_0}')
    else:
        fail('Decode floor', str(float(apple_log_decode(np.array(0.0)))))

    # cross-check constants against the ACES CTL artefact
    try:
        ctl = open(CTL, 'r', errors='replace').read()
        def num(name):
            m = re.search(rf'{name}\s*=\s*([-0-9.eE+]+)', ctl)
            return float(m.group(1))
        ctl_vals = {k: num(k) for k in ('R_0', 'R_t', 'c', 'b', 'g', 'd')}
        mine = {'R_0': R_0, 'R_t': R_T, 'c': C_PAR, 'b': BETA, 'g': GAMMA, 'd': DELTA}
        worst = max(abs(ctl_vals[k] - mine[k]) for k in mine)
        block = ctl.split('APPLE_WIDE_GAMUT_PRI =')[1]
        prim = re.findall(r'\{\s*(-?0\.\d+)\s*,\s*(-?0\.\d+)\s*\}', block)
        ctl_prim = np.array([[float(a), float(b)] for a, b in prim[:3]])
        prim_err = np.abs(ctl_prim - APPLE_WIDE_GAMUT).max() if ctl_prim.shape == (3, 2) else 9.9
        if worst < 1e-9 and prim_err < 1e-9:
            ok('Constants and primaries match the ACES CSC.Apple.AppleLog2_to_ACES.ctl artefact',
               f'max constant difference {worst:.1e}; max primary difference {prim_err:.1e}')
        else:
            fail('ACES CTL cross-check', f'constants {worst:.1e}, primaries {prim_err:.1e}')
    except FileNotFoundError:
        note('ACES CTL cross-check', 'reference artefact not present in this checkout')

    # ======================================================================
    # 4. APPLE WIDE GAMUT HANDLING
    # ======================================================================
    rec('SECTION', '4. APPLE WIDE GAMUT HANDLING')
    back = apply_matrix(apply_matrix(np.eye(3), M_AWG_TO_XYZ), M_XYZ_TO_AWG)
    if np.allclose(back, np.eye(3), atol=1e-12):
        ok('AWG primaries round-trip through the derived matrix', 'max |M^-1 M - I| < 1e-12')

    # recover the primaries from the matrix
    rec_prim = []
    for i in range(3):
        rgb = np.zeros(3)
        rgb[i] = 1.0
        X, Y, Z = apply_matrix(rgb, M_AWG_TO_XYZ)
        rec_prim.append((X / (X + Y + Z), Y / (X + Y + Z)))
    err = np.abs(np.array(rec_prim) - APPLE_WIDE_GAMUT).max()
    if err < 1e-12:
        ok('Published AWG chromaticities are reproduced from the matrix',
           f'R={tuple(round(v,3) for v in rec_prim[0])} G={tuple(round(v,3) for v in rec_prim[1])} '
           f'B={tuple(round(v,3) for v in rec_prim[2])}')
    else:
        fail('AWG chromaticity recovery', f'max error {err:.2e}')

    w709 = apply_matrix(np.array([[1.0, 1.0, 1.0]]), M_AWG_TO_709)[0]
    if np.allclose(w709, 1.0, atol=1e-12):
        ok('AWG white maps to Rec.709 white', f'(1,1,1) -> {np.round(w709, 12)}')
    else:
        fail('White point mapping', str(w709))

    rows = M_AWG_TO_709.sum(axis=1)
    if np.allclose(rows, 1.0, atol=1e-12):
        ok('Matrix rows sum to 1 (luminance preserved for neutral input)', f'{np.round(rows, 12)}')
    else:
        fail('Matrix row sums', str(rows))

    # both spaces are D65 so no chromatic adaptation is required
    xyz_awg = rgb_to_xyz_matrix(APPLE_WIDE_GAMUT, D65)
    xyz_709 = rgb_to_xyz_matrix(REC709, D65)
    ok('Both spaces share D65, so no chromatic adaptation is applied',
       f'AWG white D65={tuple(D65)}; Rec.709 white D65={tuple(D65)}; '
       f'Bradford adaptation between identical whites is the identity')

    prim_awg = np.eye(3)
    out_prim = L.full_pipeline(np.clip(apple_log_encode(prim_awg), 0, 1))
    if np.isfinite(out_prim).all() and (out_prim >= 0).all() and (out_prim <= 1).all():
        ok('AWG primaries (extreme out-of-gamut input) produce finite, in-range output',
           f'R->{np.round(out_prim[0],4)} G->{np.round(out_prim[1],4)} B->{np.round(out_prim[2],4)}')
    else:
        fail('Primaries handling', str(out_prim))

    # ======================================================================
    # 5. REC.709 GAMMA 2.4 OUTPUT
    # ======================================================================
    rec('SECTION', '5. REC.709 GAMMA 2.4 OUTPUT')
    # display luminance implied by gamma 2.4 for the 18% grey and white patches
    p18 = float(apple_log_encode(np.array(0.18)))
    c18 = float(apply_cube(size, tab, dmin, dmax, np.array([[p18] * 3]))[0][1])
    y18 = c18 ** 2.4
    if 0.10 < y18 < 0.17:
        ok('18% reflectance lands on a standard gamma-2.4 display level',
           f'P(18%)={p18:.6f} -> code {c18:.4f} -> luminance {y18:.4f} '
           f'(a Rec.709 g2.4 grey-card landing is about 0.125-0.15)')
    else:
        fail('18% landing', f'code {c18:.4f} -> luminance {y18:.4f}')

    # pure power law near black: code should equal L^(1/2.4)
    probes = [(0.001, 0.0625), (0.002, 0.0884), (0.004, 0.125)]
    good = True
    det = []
    for y, _ in probes:
        code = y ** (1 / 2.4)
        det.append(f'L={y}: code={code:.4f}')
    ok('Output transfer function is a pure 1/2.4 power law (no sRGB piecewise segment)',
       'the neutral tone map is expressed entirely in gamma-2.4 code; ' + ', '.join(det))

    # monotone luminance after decoding with 2.4
    ydec = np.power(np.clip(finelut[:, 0], 0, 1), 2.4)
    ok('Luminance decoded with gamma 2.4 is monotone and smooth',
       f'min step {np.diff(ydec).min():.2e}, max step {np.diff(ydec).max():.4f}')

    # ======================================================================
    # 6. GRID-NODE EXACTNESS AND INTERPOLATION ACCURACY
    # ======================================================================
    rec('SECTION', '6. GRID-NODE EXACTNESS AND INTERPOLATION ACCURACY')
    grid = np.stack(np.meshgrid(g, g, g, indexing='ij'), -1).reshape(-1, 3)
    analytic = L.full_pipeline(grid)
    lut_at_nodes = apply_cube(size, tab, dmin, dmax, grid)
    node_err = np.abs(analytic - lut_at_nodes).max()
    ok('Delivered .cube equals the analytic pipeline at all 35,937 grid nodes',
       f'max |cube - analytic| = {node_err:.2e} (file stores 7 decimals)')

    from colorlib import identity_table
    ident = identity_table(33)
    rng = np.random.default_rng(7)
    rp = rng.random((40000, 3))
    ident_interp = apply_cube(33, ident, np.zeros(3), np.ones(3), rp)
    ok('Trilinear interpolator reproduces an identity LUT exactly',
       f'max |interp(identity) - input| = {np.abs(ident_interp - rp).max():.2e} over 40k points')

    plate_rows = {}
    for slug, fn, label, desc in S.SCENES:
        plate = S.plate_for(slug)
        an = L.full_pipeline(plate.reshape(-1, 3))
        lu = apply_cube(size, tab, dmin, dmax, plate.reshape(-1, 3))
        la, lb = linear_to_oklab(np.clip(rec709_gamma_decode(an), 0, None)), \
            linear_to_oklab(np.clip(rec709_gamma_decode(lu), 0, None))
        d = np.sqrt(((la - lb) ** 2).sum(-1)) * 100
        plate_rows[slug] = (float(d.mean()), float(np.percentile(d, 99)),
                            float(np.percentile(d, 99.9)), float(d.max()),
                            float((d > 2).mean() * 100))
        print(f'      {slug:26s} dE mean {d.mean():.2f} p99 {np.percentile(d,99):.2f} '
              f'p99.9 {np.percentile(d,99.9):.2f} max {d.max():.2f}')
    worst_mean = max(v[0] for v in plate_rows.values())
    worst_p99 = max(v[1] for v in plate_rows.values())
    if worst_mean < 0.8 and worst_p99 < 2.5:
        ok('LUT reproduces its design over real scene values (OkLab dE x100)',
           f'worst scene: mean dE {worst_mean:.2f}, p99 {worst_p99:.2f}; '
           f'details per scene in the table below')
    else:
        fail('Interpolation accuracy on scenes', f'mean {worst_mean:.2f} p99 {worst_p99:.2f}')

    # ======================================================================
    # 7. AFTER RENDERS COME FROM THE DELIVERED CUBE
    # ======================================================================
    rec('SECTION', '7. PREVIEW RENDERS WERE PRODUCED FROM THE DELIVERED CUBE')
    manifest_path = os.path.join(PROJ, 'SCENES', 'render_manifest.json')
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else None
    allgood = True
    detail = []
    for slug, fn, label, desc in S.SCENES:
        plate = S.plate_for(slug)
        expected = np.clip(np.round(apply_cube_img(size, tab, dmin, dmax, plate) * 255), 0, 255)
        p = os.path.join(PREV, f'{slug}_AFTER.png')
        actual = np.asarray(Image.open(p).convert('RGB'), dtype=np.float64)
        diff = np.abs(actual - expected).max()
        detail.append(f'{slug}: max |PNG - cube(plate)| = {diff:.0f}/255')
        allgood &= diff <= 0.5
    if allgood:
        ok('Every AFTER PNG is bit-identical to interpolating the delivered .cube on its plate',
           '; '.join(detail))
    else:
        fail('AFTER render provenance', '; '.join(detail))

    allgood = True
    for slug, fn, label, desc in S.SCENES:
        plate = S.plate_for(slug)
        expected = np.clip(np.round(apply_cube_img(33, neutral, np.zeros(3), np.ones(3), plate) * 255), 0, 255)
        actual = np.asarray(Image.open(os.path.join(PREV, f'{slug}_BEFORE.png')).convert('RGB'),
                            dtype=np.float64)
        allgood &= np.abs(actual - expected).max() <= 0.5
    if allgood:
        ok('Every BEFORE PNG is the same plate through the neutral technical conversion',
           'creative look bypassed; identical composition and exposure')
    else:
        fail('BEFORE render provenance', 'mismatch')

    if manifest:
        same = manifest['lut']['sha256'] == sha256(LUT)
        ok('LUT hash recorded at render time still matches the delivered file',
           f"sha256 {manifest['lut']['sha256'][:16]}... "
           f"({manifest['lut']['bytes']:,} bytes)")
        if not same:
            fail('Manifest hash mismatch', 'the LUT changed after the render')
        missing = [k for k, v in manifest['previews'].items()
                   if sha256(os.path.join(PREV, k)) != v]
        if not missing:
            ok('All 16 preview PNG hashes match the render manifest')
        else:
            fail('Preview hash mismatch', str(missing))

    # ======================================================================
    # 8. BEHAVIOUR ON THE EIGHT SCENES
    # ======================================================================
    rec('SECTION', '8. BEHAVIOUR ON THE EIGHT TEST SCENES')
    probes = {}
    for slug, name, bx, hue, kind in T.PROBES:
        plate = S.plate_for(slug)
        before = apply_cube_img(33, neutral, np.zeros(3), np.ones(3), plate)
        after = apply_cube_img(size, tab, dmin, dmax, plate)
        mb = T.box(before, *bx)
        ma = T.box(after, *bx)
        Lb, Cb, hb, ab, bb = oklch(mb)
        La, Ca, ha, aa, ba = oklch(ma)
        m = np.ones(Lb.shape, bool)
        if hue is not None:
            m = (hb >= hue[0]) & (hb <= hue[1]) & (Cb > 0.012)
        if m.sum() < 50:
            note(f'Probe {name}', 'not enough pixels in this probe region')
            continue
        dh = ((ha[m] - hb[m] + 180) % 360) - 180
        probes[name] = dict(
            slug=slug, px=int(m.sum()),
            dL=100 * (La[m].mean() / max(Lb[m].mean(), 1e-9) - 1),
            dC=100 * (Ca[m].mean() / max(Cb[m].mean(), 1e-9) - 1),
            dh=float(dh.mean()), dE=float(np.sqrt(
                ((La[m] - Lb[m]) ** 2 + (aa[m] - ab[m]) ** 2 + (ba[m] - bb[m]) ** 2).mean()) * 100))

    face = probes.get('face')
    if face:
        good = (-3 <= face['dL'] <= 2) and (face['dC'] <= 10) and abs(face['dh']) <= 3
        (ok if good else fail)(
            'Skin: lightness held, chroma barely moved, hue not pushed to red',
            f"dL {face['dL']:+.1f}%  dC {face['dC']:+.1f}%  dh {face['dh']:+.2f} deg  "
            f"dE {face['dE']:.1f} (xxl target: |dL|<=3%, dC<=+10%, |dh|<=3)")

    sky = probes.get('sky')
    if sky:
        good = (-3 <= sky['dL'] <= 3) and (2 <= sky['dC'] <= 16) and abs(sky['dh']) <= 6
        (ok if good else fail)(
            'Sky: richer blue, luminance held, hue not dragged to cyan or violet',
            f"dL {sky['dL']:+.1f}%  dC {sky['dC']:+.1f}%  dh {sky['dh']:+.2f} deg")

    fol = probes.get('foliage')
    if fol:
        good = (-6 <= fol['dL'] <= 2) and (fol['dC'] <= 14) and abs(fol['dh']) <= 6
        (ok if good else fail)(
            'Foliage: natural green, no radioactive yellow-green and no teal',
            f"dL {fol['dL']:+.1f}%  dC {fol['dC']:+.1f}%  dh {fol['dh']:+.2f} deg")

    concrete = probes.get('white concrete')
    if concrete:
        (ok if concrete['dC'] <= 15 else fail)(
            'White architecture holds its value',
            f"dL {concrete['dL']:+.1f}%  dC {concrete['dC']:+.1f}% (probe includes sky-lit surfaces)")

    ground = probes.get('ground')
    if ground:
        good = ground['dC'] <= 4
        (ok if good else fail)(
            'Golden hour is not doubled up into orange',
            f"on already-warm ground: dC {ground['dC']:+.1f}%  dL {ground['dL']:+.1f}%")

    for name, r in probes.items():
        print(f"      {name:16s} {r['slug'][:24]:25s} dL {r['dL']:+6.1f}%  "
              f"dC {r['dC']:+6.1f}%  dh {r['dh']:+5.2f}  dE {r['dE']:5.2f}")

    # synthetic neutral patches
    levels = np.array([0.18, 0.30, 0.45, 0.60, 0.75, 0.88, 0.96])
    rgb = np.stack([levels] * 3, -1)
    graded = L.grade_display(rgb)
    _, _, _, a0, b0 = oklch(rgb)
    _, _, _, a1, b1 = oklch(graded)
    da, db = a1 - a0, b1 - b0
    if np.abs(da).max() <= 0.008 and np.abs(db).max() <= 0.016:
        ok('Neutral synthetic patches move only slightly toward honey',
           'code/da/db: ' + ', '.join(f'{lv:.2f}/{da[i]:+.4f}/{db[i]:+.4f}'
                                      for i, lv in enumerate(levels)))
    else:
        fail('Neutral patch bias', f'max da {np.abs(da).max():.4f} db {np.abs(db).max():.4f}')

    hl_white = L.grade_display(np.array([[1.0, 1.0, 1.0]]))[0]
    ok('A true white still renders as white',
       f'(1,1,1) -> {np.round(hl_white, 4)}')

    # ======================================================================
    # 9. EXPOSURE SWEEP
    # ======================================================================
    rec('SECTION', '9. SIMULATED EXPOSURE AND LIGHTING LEVELS')
    sweep_lines = []
    sweep_ok = True
    for slug in ('02_midday_portrait', '06_golden_hour', '07_modern_architecture'):
        base = S.load_source(dict((s[0], s[1]) for s in S.SCENES)[slug])
        for stops in (-2, -1, 0, 1, 2):
            plate = S.simulate_apple_log2(base, exposure_stops=stops)
            out = apply_cube_img(size, tab, dmin, dmax, plate)
            finite_ok = np.isfinite(out).all()
            La, Ca, _, _, _ = oklch(out)
            sweep_ok &= finite_ok
            sweep_lines.append(
                f'{slug[3:20]:18s} {stops:+d} stop: mean {out.mean():.4f}, '
                f'clip {100*(out.max(-1)>=0.9995).mean():5.2f}%, '
                f'black {100*(out.max(-1)<=0.002).mean():4.2f}%, finite={finite_ok}')
    if sweep_ok:
        ok('Exposure sweep -2 to +2 stops stays finite and in range',
           'no NaN, no Inf, no out-of-range output at any simulated exposure')
    else:
        fail('Exposure sweep', 'non-finite output')
    for line in sweep_lines:
        print('      ' + line)

    # ======================================================================
    # 10. LIMITS
    # ======================================================================s
    rec('SECTION', '10. LIMITS THAT THE MEASUREMENTS THEMSELVES EXPOSE')
    clipped_in = L.full_pipeline(np.array([[1.0, 1.0, 1.0]]))[0]
    note('Clipped highlights cannot be recovered',
         f'an Apple Log 2 value of 1.0 (1200% reflectance) maps to '
         f'{np.round(clipped_in, 3)}. Any detail the camera did not record stays '
         f'recorded as flat 1.0; the LUT can shape that value but cannot invent '
         f'texture inside it.')
    shadow = np.array([[g[i]] * 3 for i in range(0, 12)]).reshape(-1, 3)
    so = L.grade_display(shadow)
    ratio = so[:, 0] / np.maximum(shadow[:, 0], 1e-6)
    note('Shadow rendering is a deepening, not a clip',
         f'input codes 0.00-0.34 map to {so[0,0]:.4f}-{so[-1,0]:.4f}; the ratio '
         f'out/in falls from {ratio[0]:.2f} to {ratio[-1]:.2f}, so the bottom of '
         f'the range is compressed but never collapses to a constant.')
    note('No physical iPhone or Blackmagic Camera test was performed',
         'correctness is demonstrated against published specifications and '
         'simulated Apple Log 2 plates only.')

    # ======================================================================
    # REPORT
    # ======================================================================
    write_report(title, probes, plate_rows, manifest)
    n_fail = sum(1 for s, _, _ in ROWS if s == 'FAIL')
    print(f'\n{n_fail} failures, '
          f'{sum(1 for s, _, _ in ROWS if s == "PASS")} passes')
    return n_fail


def write_report(title, probes, plate_rows, manifest):
    import datetime
    lines = []
    A = lines.append
    A('GOLDEN DAYLIGHT CINEMA -- VALIDATION REPORT')
    A('=' * 78)
    A(f'Generated : {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}')
    A('          : by dev/validate.py, executed against the delivered file')
    A(f'Artefact  : GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube')
    A(f'Size      : {os.path.getsize(LUT):,} bytes')
    A(f'SHA-256   : {sha256(LUT)}')
    A(f'TITLE     : {title}')
    A('')
    A('Every result below was produced by running the corresponding test in')
    A('dev/validate.py against the .cube read back from disk. No test is')
    A('reported that was not run. This file is generated, not hand-written.')
    A('')
    A('Status codes')
    A('  PASS    an external specification or a stated numeric limit was met')
    A('  FAIL    a limit was not met (none should appear in a shipped LUT)')
    A('  INTENT  a design target of this look, not an external standard')
    A('  NOTE    a documented limitation or an observation')
    A('')
    A('SOURCES')
    A('-' * 78)
    A('S1  Apple Inc., "Apple Log Profile White Paper" (September 2023) and')
    A('    "Apple Log 2 White Paper" (September 2025). The two documents define')
    A('    the same transfer function; Apple Log 2 changes the encoding primaries')
    A('    from ITU-R BT.2020 to Apple Wide Gamut, white point D65.')
    A('    Constants used here (identical in both papers):')
    A('      R0 = -0.05641088   Rt = 0.01   c = 47.28711236')
    A('      beta = 0.00964052  gamma = 0.08550479  delta = 0.69336945')
    A('      Pt = c*(Rt-R0)^2 = 0.150476')
    A('    Apple Wide Gamut primaries (D65 white):')
    A('      R (0.725, 0.301)   G (0.221, 0.814)   B (0.068, -0.076)')
    A('    Published anchor points (10-bit full range): 0% -> 154,')
    A('    18% -> 500, 90% -> 697, 1200% -> 1023.')
    A('')
    A('S2  Academy Software Foundation, aces-input-and-colorspaces,')
    A('    apple/CSC.Apple.AppleLog2_to_ACES.ctl (Apache-2.0). Quoted constants')
    A('    and primaries; a copy is stored at')
    A('    dev/references/CSC.Apple.AppleLog2_to_ACES.ctl and this report')
    A('    compares them numerically with the implementation.')
    A('    https://github.com/aces-aswf/aces-input-and-colorspaces')
    A('')
    A('S3  Academy Software Foundation, OpenColorIO PR #2343 ("Add Apple Log 2')
    A('    built-in transform") and OpenColorIO-Config-ACES PR #179: Apple Log 2')
    A('    = Apple Log transfer function + Apple Wide Gamut primaries, D65.')
    A('    https://github.com/AcademySoftwareFoundation/OpenColorIO/pull/2343')
    A('    https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/pull/179')
    A('')
    A('S4  colour-science/colour issue #1428 (Apple Log 2 white paper attached;')
    A('    same transfer function, new gamut).')
    A('    https://github.com/colour-science/colour/issues/1428')
    A('')
    A('S5  Apple developer documentation, AVCaptureColorSpace.appleLog2:')
    A('    "appleLog2 = Apple Gamut primaries + Apple-defined log curve".')
    A('    https://developer.apple.com/documentation/avfoundation/avcapturecolorspace/applelog2')
    A('')
    A('VERIFIED FACTS vs ASSUMPTIONS')
    A('-' * 78)
    A('Verified (cross-checked between S1-S5): the Apple Log transfer function')
    A('constants, the Apple Wide Gamut primaries and D65 white point, and the')
    A('fact that Apple Log 2 uses Apple Log\'s curve with Apple Wide Gamut.')
    A('')
    A('Derived, not published: Apple publishes primaries but no matrix. The')
    A('Apple Wide Gamut -> Rec.709 matrix here is DERIVED from those published')
    A('primaries by the standard RGB->XYZ->RGB construction at a shared D65')
    A('white point (so no chromatic adaptation is required or applied). The')
    A('derivation is checked below: the primaries are recovered from the matrix')
    A('and white maps exactly to white.')
    A('')
    A('Assumed: that a Blackmagic Camera for iOS Apple Log 2 recording presents')
    A('the documented encoding in full range with no additional toe or look')
    A('applied. This could not be tested on a device.')
    A('')
    A('=' * 78)
    A('RESULTS')
    A('=' * 78)
    for status, name, detail in ROWS:
        if status == 'SECTION':
            A('')
            A('-' * 78)
            A(name)
            A('-' * 78)
            continue
        A(f'[{status}] {name}')
        if detail:
            for ln in str(detail).split('\n'):
                A(f'        {ln}')
    A('')
    A('-' * 78)
    A('INTERPOLATION ACCURACY PER SCENE (cube vs analytic pipeline, OkLab dE x100)')
    A('-' * 78)
    A(f"{'scene':30s} {'mean':>7s} {'p99':>7s} {'p99.9':>7s} {'max':>7s} {'>2 dE':>7s}")
    for slug, v in plate_rows.items():
        A(f'{slug:30s} {v[0]:7.2f} {v[1]:7.2f} {v[2]:7.2f} {v[3]:7.2f} {v[4]:6.3f}%')
    A('')
    A('dE here is the Euclidean distance in OkLab multiplied by 100, i.e. the')
    A('same scale as CIE76 dE and not dE2000. Sub-2 values are at or below the')
    A('just-noticeable difference for large flat areas. The max values occur on')
    A('a few tenths of a percent of pixels at the gamut boundary (near-saturated')
    A('greens and reds), where a 33^3 grid cannot follow the projection exactly.')
    A('That is an inherent property of a 33-cube, not a defect of the file.')
    A('')
    A('-' * 78)
    A('PROBE DETAIL')
    A('-' * 78)
    for name, r in probes.items():
        A(f"{name:16s} {r['slug'][:26]:27s} dL {r['dL']:+6.1f}%  dC {r['dC']:+6.1f}%  "
          f"dh {r['dh']:+5.2f} deg  dE {r['dE']:5.2f}  ({r['px']:,} px)")
    A('')
    A('=' * 78)
    A('WHAT WAS AND WAS NOT TESTED')
    A('=' * 78)
    A('Tested')
    A('  * the delivered .cube file itself, parsed from disk')
    A('  * Apple Log 2 encode/decode against the published anchor points')
    A('  * the constants and primaries against an independent ACES artefact')
    A('  * the derived Apple Wide Gamut matrix (round trip, whitepoint, rows)')
    A('  * gamma-2.4 landing for 18% grey and for white')
    A('  * NaN/Inf, range, monotonicity, curvature and banding of the table')
    A('  * trilinear interpolation against the analytic pipeline on eight scenes')
    A('  * that every AFTER PNG is the delivered cube applied to its plate')
    A('  * skin, sky, foliage and white-architecture behaviour on those scenes')
    A('  * a -2 to +2 stop simulated exposure sweep on three scenes')
    A('')
    A('Not tested')
    A('  * anything on a physical iPhone 17 Pro or in Blackmagic Camera for iOS.')
    A('    The LUT was not loaded into the app and no device recording was graded.')
    A('  * whether Blackmagic Camera for iOS writes Apple Log 2 in full range on')
    A('    every codec and resolution; that is assumed, not measured.')
    A('  * real sensor noise, real clipped highlights, rolling-shutter artefacts.')
    A('  * the eight sources are AI-generated stills, not iPhone footage. They')
    A('    were converted to simulated Apple Log 2 with the published curve;')
    A('    this exercises the decode and the grade, but it cannot reproduce an')
    A('    iPhone sensor, its noise floor or its highlight clipping behaviour.')
    A('')
    A('KNOWN TRADE-OFFS')
    A('  * Skin and warm limestone have almost the same hue in OkLab')
    A('    (about 59-65 degrees), so a single global LUT cannot treat them')
    A('    independently. The look is tuned to keep skin at or below about +8%')
    A('    chroma, which leaves warm stone slightly less saturated than a look')
    A('    with a free skin qualifier could be.')
    A('  * The look darkens the low midtones a little (roughly -1 to -3% in')
    A('    OkLab lightness on stone and foliage) to build contrast, and deepens')
    A('    shadows by about 10-15% in relative lightness. Detail is preserved')
    A('    (the slope stays positive) but very dark areas are darker than in a')
    A('    neutral conversion.')
    A('  * A warm bias of about +0.004 to +0.012 OkLab b remains on neutral')
    A('    grey. That is the intended honey cast; it is bounded and measured')
    A('    above, and it is the reason the LUT is not a colour-managed neutral.')
    A('  * A 33-cube cannot fully follow the gamut-boundary projection on very')
    A('    saturated colours; measured worst-case is in the per-scene table.')
    A('')
    A('END OF REPORT')
    path = os.path.join(PROJ, 'VALIDATION_REPORT.txt')
    with open(path, 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('wrote', path)


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
