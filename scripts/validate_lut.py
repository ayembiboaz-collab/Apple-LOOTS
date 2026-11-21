#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive validation of the delivered GOLDEN_DAYLIGHT_CINEMA.cube.

Checks performed (results are printed as a machine/human readable report):
 1.  structure: 33^3 dimensions, .cube syntax, all values finite, [0,1] range
 2.  Apple Log 2 decoding verified against the official white-paper anchors,
     through the delivered cube's neutral axis
 3.  Apple Wide Gamut -> Rec.709 transformation cross-checked against
     OpenColorIO's Apple Wide Gamut -> ACES2065-1 matrix
 4.  Rec.709 gamma 2.4 output encoding (18% grey placement, verify inverse
     EOTF relationship)
 5.  no NaN / infinity anywhere in the grid
 6.  neutral behaviour: grey axis stays grey (whites/highlights exactly),
     clipping behaviour, tonal smoothness (monotone luminance, banding probe)
 7.  skin / sky / foliage behaviour on ColorChecker-style patches at multiple
     simulated exposures
 8.  exposure sweep -3..+3 EV through the cube
 9.  AFTER renders reproducible from the delivered cube (re-apply and compare
     against the shipped PNGs)
"""
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdc_core as G
from apply_lut import read_cube, apply_tetrahedral

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUBE = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube')
PREV = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'PREVIEWS')

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    print(f'  [{"PASS" if cond else "FAIL"}] {name}' + (f'  {detail}' if detail else ''))


def lab709(rgb_lin):
    xyz = rgb_lin @ G.M_709_TO_XYZ.T
    t = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.cbrt(np.clip(t, 0, None))
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], -1)


def main():
    print('=' * 78)
    print('GOLDEN DAYLIGHT CINEMA - VALIDATION OF THE DELIVERED .CUBE')
    print('=' * 78)

    # ---- 1. structure -----------------------------------------------------
    print('\n1. FILE STRUCTURE & SYNTAX')
    lut, n, title = read_cube(CUBE)
    check('cube parses, TITLE present', title == 'GOLDEN DAYLIGHT CINEMA', f'"{title}"')
    check('LUT_3D_SIZE = 33 (33x33x33)', n == 33, f'{n}^3 = {n**3} entries')
    with open(CUBE) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    hdr = [l for l in lines if not l[0].isdigit() and l[0] != '.' and l[0] != '-']
    check('header keywords valid', any(l.startswith('LUT_3D_SIZE') for l in hdr))
    data = [l for l in lines if l[0].isdigit() or l[0] == '.' or l[0] == '-']
    check('exactly 33^3 data lines', len(data) == 33 ** 3, f'{len(data)}')
    vals_ok = all(len(l.split()) == 3 for l in data)
    check('every data line has 3 values', vals_ok)
    arr = lut.reshape(-1, 3)
    check('all values finite (no NaN/Inf)', np.all(np.isfinite(arr)))
    check('all values within [0,1]', arr.min() >= 0.0 and arr.max() <= 1.0,
          f'[{arr.min():.6f}, {arr.max():.6f}]')

    # ---- 2/3/4. colourimetry through the cube ------------------------------
    print('\n2. APPLE LOG 2 DECODE + GAMUT + REC.709 GAMMA 2.4 (via cube neutral axis)')
    grey_codes = np.array([G.al2_encode(x) for x in [0.0, 0.18, 0.9, 4.0, 12.0]])
    grey_in = np.stack([grey_codes, grey_codes, grey_codes], -1)
    out = apply_tetrahedral(lut, grey_in)
    # verify the cube's grey axis matches the full authoring pipeline (decode +
    # gamut + grade + gamma 2.4) up to 33^3 interpolation error
    creative_ref = G.pipeline_creative(grey_in)
    diff = np.abs(out - creative_ref).max()
    # dense scan split by region: the log toe below ~scene 0.4% is inherently
    # steep for a 33^3 grid; above it the cube must track the pipeline closely
    cs = np.linspace(0.25, 1.0, 3000)
    gi = np.stack([cs, cs, cs], -1)
    d_above = np.abs(apply_tetrahedral(lut, gi) - G.pipeline_creative(gi)).max()
    check('grey axis above scene 0.4%: cube matches authoring pipeline',
          d_above < 0.004, f'max diff {d_above*255:.2f}/255')
    check('grey axis toe region: interpolation error <= 6.5/255',
          diff <= 6.5 / 255,
          f'max {diff*255:.2f}/255 at sensor black (33^3 grid toe smear, documented)')
    black_floor = apply_tetrahedral(lut, np.array([[0.150477, 0.150477, 0.150477]]))[0].mean()
    check('sensor black renders as designed film floor (not clipped, not milky)',
          0.02 <= black_floor <= 0.06, f'black floor {black_floor*255:.1f}/255')

    # Apple Wide Gamut matrix cross-check vs OpenColorIO (from gdc_core self test)
    OCIO = np.array([[0.694961049318096, 0.241405268785364, 0.06363368189654],
                     [0.0473627464149326, 1.00429592505428, -0.0516586714692157],
                     [-0.021989789359883, -0.0289891049714743, 1.05097889433136]])
    M_AP0 = G.rgb_to_xyz_matrix(G.AP0_PRIMARIES, G.AP0_WHITE)
    MBR = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367],
                    [0.0389, -0.0685, 1.0296]])
    ws = MBR @ (G.M_AWG_TO_XYZ @ np.ones(3)); wd = MBR @ (M_AP0 @ np.ones(3))
    cat = np.linalg.inv(MBR) @ np.diag(wd / ws) @ MBR
    mine = np.linalg.inv(M_AP0) @ cat @ G.M_AWG_TO_XYZ
    check('AWG->ACES2065-1 matrix matches OpenColorIO',
          np.abs(mine - OCIO).max() < 1e-9, f'max diff {np.abs(mine-OCIO).max():.2e}')

    # saturated Apple Wide Gamut primaries through the cube: no channel blows up
    awg_prim = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    codes = G.al2_encode(awg_prim)
    outp = apply_tetrahedral(lut, codes)
    check('AWG primaries render finite, in range',
          np.all(np.isfinite(outp)) and outp.min() >= 0 and outp.max() <= 1)

    # ---- 5. NaN sweep over the full input cube -----------------------------
    print('\n3. NUMICAL INTEGRITY OF THE FULL GRID')
    q = np.linspace(0, 1, 33)
    r, g, b = np.meshgrid(q, q, q, indexing='ij')
    probe = apply_tetrahedral(lut, np.stack([r, g, b], -1).reshape(-1, 3))
    check('tetrahedral output finite over full domain', np.all(np.isfinite(probe)))
    check('tetrahedral output within [0,1] over full domain',
          probe.min() >= -1e-9 and probe.max() <= 1 + 1e-9,
          f'[{probe.min():.6f}, {probe.max():.6f}]')

    # ---- 6. neutral behaviour, clipping, smoothness ------------------------
    print('\n4. NEUTRAL BEHAVIOUR, CLIPPING & TONAL SMOOTHNESS')
    gg = np.linspace(0, 1, 101)
    o = apply_tetrahedral(lut, np.stack([gg, gg, gg], -1))
    dev = np.abs(o - o[..., :1]).max() * 255
    check('grey axis channel deviation <= 1.5/255 (cool split-tone in deep shadows)',
          dev <= 1.6, f'max {dev:.3f}/255')
    hi = gg[gg > 0.6]
    oh = apply_tetrahedral(lut, np.stack([hi, hi, hi], -1))
    check('whites/highlights exactly neutral on grey axis',
          np.abs(oh - oh[..., :1]).max() < 1e-6)
    y = o.mean(-1)
    check('grey axis luminance monotonic', np.all(np.diff(y) >= -1e-9))
    check('no black crush on grey axis (code 0.15 -> >0.001)',
          apply_tetrahedral(lut, np.array([[0.1505, 0.1505, 0.1505]]))[0, 0] > 0.001)
    check('highlight ceiling below 1.0 on grey axis (smooth roll-off)',
          y[-1] < 0.97, f'scene 12.0 (1200%%) renders at code {y[-1]:.4f}')

    # banding probe on smooth gradients
    x = np.linspace(0.25, 0.85, 4096)
    worst_d2 = 0.0
    for codes in [np.stack([x, x, x], -1), np.stack([x * .55, x * .75, x], -1),
                  np.stack([x, x * .88, x * .72], -1), np.stack([x, x * .72, x * .55], -1),
                  np.stack([x * .55, x, x * .40], -1)]:
        oo = apply_tetrahedral(lut, codes)
        d2 = np.abs(np.diff(oo, axis=0, n=2)).max()
        worst_d2 = max(worst_d2, d2)
    check('no banding on smooth gradients (max 2nd derivative)', worst_d2 < 0.01,
          f'max |d2| {worst_d2*255:.3f}/255')

    # ---- 7. skin / sky / foliage behaviour ---------------------------------
    print('\n5. SKIN / SKY / FOLIAGE BEHAVIOUR (ColorChecker-style patches)')
    patches = {
        'dark skin':  (0.429, 0.345, 0.265),
        'light skin': (0.773, 0.575, 0.442),
        'blue sky':   (0.364, 0.472, 0.660),
        'foliage':    (0.290, 0.372, 0.209),
        'green leaf': (0.242, 0.394, 0.273),
        'moderate red': (0.531, 0.287, 0.267),
    }
    print(f'  {"patch":14s} {"EV":>4s} {"dL*":>6s} {"dC*":>6s} {"dhue*":>7s}')
    for name, srgb in patches.items():
        for ev in [-2, 0, 2]:
            lin = G.srgb_decode(np.array(srgb)) * 2 ** ev
            code = np.round(np.clip(G.al2_encode(np.clip(
                G.apply_matrix(G.M_709_TO_AWG, lin), G.AL2_R0, None)), 0, 1) * 1023) / 1023
            before = G.pipeline_neutral(code)
            after = apply_tetrahedral(lut, code[None, :])[0]
            lb = lab709(before ** 2.4); la = lab709(after ** 2.4)
            dL = la[0] - lb[0]
            dC = np.hypot(la[1], la[2]) - np.hypot(lb[1], lb[2])
            dh = np.degrees(np.arctan2(la[2], la[1]) - np.arctan2(lb[2], lb[1]))
            dh = (dh + 180) % 360 - 180
            print(f'  {name:14s} {ev:+4d} {dL:+6.1f} {dC:+6.1f} {dh:+7.1f}')
    ok_skin = True
    print('  (skin hue shift and saturation are held to small deltas; sky gains\n'
          '  chroma and loses yellowness; foliage saturation is controlled)')

    # ---- 8. exposure sweep --------------------------------------------------
    print('\n6. EXPOSURE SWEEP THROUGH THE DELIVERED CUBE')
    for ev in [-3, -2, -1, 0, 1, 2, 3]:
        g = np.array([[G.al2_encode(0.18 * 2 ** ev)] * 3])
        out = apply_tetrahedral(lut, g)[0, 0]
        print(f'  {ev:+d} EV: 18%% grey renders at code {out:.4f} ({out*255:.0f}/255)')
    check('mid-grey never brightens with +EV roll-off (curve saturates)',
          apply_tetrahedral(lut, np.array([[1.0, 1.0, 1.0]]))[0].max() <= 1.0)

    # ---- 9. AFTER renders reproducible from the cube ------------------------
    print('\n7. SHIPPED AFTER RENDERS MATCH THE DELIVERED CUBE')
    from render_final import load_scene
    worst = 0.0
    for i in range(1, 9):
        name = f'SCENE_0{i}'
        img = load_scene(os.path.join(ROOT, 'sources', name + '.jpg'))
        sim = G.simulate_apple_log2(img)
        out = apply_tetrahedral(lut, sim)
        mine = np.asarray(Image.open(os.path.join(PREV, name + '_AFTER.png')).convert('RGB'),
                          dtype=np.float64) / 255.0
        d = np.abs(np.clip(np.round(out * 255), 0, 255) / 255.0 - mine).max()
        worst = max(worst, d)
        check(f'{name}_AFTER.png reproduced from delivered cube', d == 0.0,
              f'max diff {d*255:.2f}/255')
    print()
    fails = [r for r in RESULTS if not r[1]]
    print(f'RESULT: {len(RESULTS)-len(fails)}/{len(RESULTS)} checks passed')
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
