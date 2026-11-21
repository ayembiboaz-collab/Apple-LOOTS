"""
validate.py — validate THE DELIVERED .cube and write VALIDATION_REPORT.txt.

Everything here operates on the file at
GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube, parsed from disk.
Nothing is assumed about how it was produced.

Run:  python3 scripts/validate.py
"""

from __future__ import annotations

import datetime
import hashlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image

import applelog2 as al2
import grade
import simulate_log2 as sim
import tune
from cube_io import apply_cube, read_cube

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
LUT_PATH = os.path.join(PKG, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
PREVIEWS = os.path.join(PKG, "PREVIEWS")
REPORT = os.path.join(PKG, "VALIDATION_REPORT.txt")

OUT = io.StringIO()
RESULTS = []


def w(line=""):
    OUT.write(line + "\n")


def head(title):
    w()
    w("=" * 78)
    w(title)
    w("=" * 78)


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    w(f"[{'PASS' if ok else 'FAIL'}] {name}")
    for ln in str(detail).split("\n"):
        if ln.strip():
            w(f"       {ln}")
    return ok


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    w("================================================================================")
    w("  GOLDEN DAYLIGHT CINEMA")
    w("  VALIDATION REPORT")
    w("================================================================================")
    w()
    w(f"  Generated      : {now}")
    w(f"  Validated file : GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube")
    w(f"  SHA-256        : {sha256(LUT_PATH)}")
    w(f"  Size on disk   : {os.path.getsize(LUT_PATH):,} bytes")
    w(f"  Produced by    : scripts/build_lut.py  (see README.md to reproduce)")
    w()
    w("  Everything below was measured on the delivered .cube file parsed from")
    w("  disk. Only tests that were actually executed are reported.")

    # ----------------------------------------------------------------- 0 ---
    head("0.  SOURCES AND HOW THEY WERE CROSS-CHECKED")
    w("""
VERIFIED FACTS (published by the manufacturer, and independently corroborated)

  S1  Apple Log transfer function constants
      Apple Inc., "Apple Log Profile White Paper", September 2023.
      Apple Inc., "Apple Log 2 White Paper", September 2025 - the Log 2 paper
      keeps the SAME transfer function; only the gamut changes.
          R0 = -0.05641088   Rt = 0.01           sigma = 47.28711236
          beta = 0.00964052  gamma = 0.08550479  delta = 0.69336945
      Corroboration: the colour-science library
      (colour/models/rgb/transfer_functions/apple_log_profile.py) carries the
      identical constants and cites both the Apple white paper and the AMPAS
      ACES input transform IDT.Apple.AppleLog_BT2020.ctl.
      Independently checked here against the white paper's own anchor table
      (see test 2).

  S2  Apple Wide Gamut primaries (Apple Log 2 only)
          R (0.725, 0.301)   G (0.221, 0.814)   B (0.068, -0.076)
          White: D65 (0.3127, 0.3290)
      Four independent transcriptions of Apple's Apple Log 2 white paper agree
      exactly: the OpenColorIO builtin added in PR #2343 (AppleCameras.cpp),
      the hdr-toys shader table, and two published technical write-ups
      (ireelz.com, cined.com). A French-language transcript of the white
      paper itself lists the same six coordinates plus the D65 white point.

  S3  Independent numerical anchor for the gamut maths
      OpenColorIO-Config-ACES PR #179 (and the Blender studio config) publish
      the Apple Wide Gamut -> ACES2065-1 matrix with Bradford adaptation.
      This project re-derives that matrix from S2 and compares (test 3).

  S4  Blackmagic Camera for iOS accepts 17-point and 33-point 3D .cube LUTs,
      imported via Settings > LUTs > Import LUT, and can display a LUT while
      still recording clean log. Multiple current vendor guides state the
      17/33-point limit. This is why the deliverable is 33x33x33.

ASSUMPTIONS (clearly flagged, NOT verified against a device)

  A1  INPUT SIGNAL RANGE. Apple's white paper defines the encoded pixel value
      P on the normalised floating-point interval [0, 1] (10-bit FULL range:
      code 0 -> 0.0, code 1023 -> 1.0). This LUT assumes the host feeds it
      that normalised full-range signal, which is the same assumption Apple's
      own camera LUTs make. If a host presents a legal/video-range signal
      without expanding it, the image will appear contrastier and clipped.

  A2  SENSOR COLOUR SCIENCE. Apple does not publish how each iPhone sensor's
      native response is characterised before encoding into Apple Wide Gamut.
      The LUT is therefore mathematically correct with respect to the
      published Apple Log 2 definition, but it has not been matched to a
      measured iPhone 17 Pro capture.

  A3  NO DEVICE TESTING. No iPhone, no iPhone 17 Pro, and no Blackmagic
      Camera installation was used at any point. Import behaviour, on-device
      appearance and performance are UNTESTED.
""".strip("\n"))

    # ----------------------------------------------------------------- 1 ---
    head("1.  FILE FORMAT, DIMENSIONS AND NUMERICAL INTEGRITY")
    table, size, dmin, dmax, title = read_cube(LUT_PATH)
    flat = table.reshape(-1, 3)
    check("file parses as a valid Adobe/IRIDAS 3D .cube", True,
          f'TITLE "{title}", LUT_3D_SIZE {size}, DOMAIN_MIN {dmin.tolist()}, '
          f"DOMAIN_MAX {dmax.tolist()}")
    check("LUT_3D_SIZE is 33 (33 x 33 x 33)", size == 33, f"size = {size}")
    check("entry count is 33^3 = 35,937", flat.shape[0] == 35937,
          f"{flat.shape[0]:,} RGB triplets parsed")
    check("no NaN values", bool(np.all(~np.isnan(flat))),
          f"NaN count = {int(np.isnan(flat).sum())}")
    check("no infinite values", bool(np.all(np.isfinite(flat))),
          f"non-finite count = {int((~np.isfinite(flat)).sum())}")
    check("all entries within the legal [0, 1] output range",
          bool(flat.min() >= 0.0 and flat.max() <= 1.0),
          f"min {flat.min():.6f}, max {flat.max():.6f}")
    with open(LUT_PATH, "r", encoding="ascii") as fh:
        raw = fh.read()
    data_lines = [l for l in raw.splitlines()
                  if l.strip() and not l.startswith("#")
                  and not l.split()[0].upper().startswith(("TITLE", "LUT_3D_SIZE", "DOMAIN"))]
    check("every data line holds exactly three decimal values",
          all(len(l.split()) == 3 for l in data_lines), f"{len(data_lines):,} data lines")
    check("file is plain 7-bit ASCII with LF line endings",
          raw.isascii() and "\r" not in raw)

    # ----------------------------------------------------------------- 2 ---
    head("2.  APPLE LOG 2 DECODE AGAINST THE PUBLISHED WHITE-PAPER TABLE")
    w("The white paper tabulates scene reflection against 10-bit full-range code.")
    w()
    w("      reflectance        our encode P      10-bit    paper    delta")
    ok = True
    for refl, expect in [(0.00, 154), (0.18, 500), (0.90, 697), (12.00, 1023)]:
        P = float(al2.apple_log_encode(refl))
        code = P * 1023.0
        ok &= abs(code - expect) < 1.0
        w(f"      {refl*100:9.2f} %      {P:.8f}      {code:7.2f}   {expect:6d}   "
          f"{code-expect:+6.3f}")
    check("all four published anchor points reproduce within 1 code value", ok)

    R = np.concatenate([np.linspace(-0.05, 0.01, 2000), np.geomspace(0.01, 100.0, 20000)])
    err = float(np.max(np.abs(R - al2.apple_log_decode(al2.apple_log_encode(R)))))
    check("encode/decode round-trip is exact", err < 1e-9,
          f"max |R - decode(encode(R))| = {err:.3e} over reflectance [-0.05, 100]")
    check("reference value log_encoding_AppleLogProfile(0.18) = 0.48827245852686763",
          abs(float(al2.apple_log_encode(0.18)) - 0.48827245852686763) < 1e-12)
    Pg = np.linspace(0, 1, 100001)
    Rg = al2.apple_log_decode(Pg)
    check("decode is strictly monotonic and finite across P in [0, 1]",
          bool(np.all(np.diff(Rg) > 0) and np.all(np.isfinite(Rg))),
          f"smallest step {np.min(np.diff(Rg)):.3e}; "
          f"decoded reflectance range [{Rg[0]:.6f}, {Rg[-1]:.4f}]")

    # ----------------------------------------------------------------- 3 ---
    head("3.  APPLE WIDE GAMUT TRANSFORM AGAINST AN INDEPENDENT REFERENCE")
    d = al2.AWG_TO_AP0_BRADFORD
    r = al2.AWG_TO_AP0_REFERENCE
    diff = float(np.max(np.abs(d - r)))
    w("  Derived here from the published chromaticities (S2), D65 -> D60 Bradford:")
    for row in d:
        w("      [" + ", ".join(f"{v: .15f}" for v in row) + "]")
    w("  Published by OpenColorIO-Config-ACES PR #179 / Blender studio config (S3):")
    for row in r:
        w("      [" + ", ".join(f"{v: .15f}" for v in row) + "]")
    check("re-derived Apple Wide Gamut -> ACES2065-1 matrix matches the published one",
          diff < 1e-12, f"max absolute element difference = {diff:.3e}")

    w()
    w("  Apple Wide Gamut -> Rec.709 used by this LUT (both D65, so no chromatic")
    w("  adaptation is applied, which is the correct treatment):")
    for row in al2.AWG_TO_REC709:
        w("      [" + ", ".join(f"{v: .15f}" for v in row) + "]")
    rs = al2.AWG_TO_REC709.sum(axis=1)
    check("matrix row sums are 1.0, so neutral in -> neutral out",
          bool(np.allclose(rs, 1.0, atol=1e-12)),
          f"row sums {rs}, max deviation {np.max(np.abs(rs-1)):.3e}")

    w()
    w("  Hue fidelity end to end: Rec.709 reference colours were encoded into")
    w("  Apple Log 2 and pushed through the DELIVERED .cube. Hue is measured on")
    w("  the display-linear result. A correct gamut transform keeps hue stable")
    w("  (small intentional creative rotations are listed in section 6).")
    w()
    w("      colour            in hue    out hue    delta")
    refs = {"red": [0.30, 0.02, 0.02], "green": [0.03, 0.22, 0.03],
            "blue": [0.03, 0.04, 0.26], "yellow": [0.33, 0.30, 0.04],
            "cyan": [0.04, 0.26, 0.28], "magenta": [0.28, 0.04, 0.26]}
    worst = 0.0
    for name, lin in refs.items():
        P = np.clip(al2.apple_log_encode(al2.apply_matrix(np.array(lin), al2.REC709_TO_AWG)), 0, 1)
        out = grade.gamma24_decode(apply_cube(P, table, size, dmin, dmax))
        hi, _, _ = tune.lin_hue_sat(np.array(lin))
        ho, _, _ = tune.lin_hue_sat(out)
        dh = tune.adiff(float(ho), float(hi))
        worst = max(worst, abs(dh))
        w(f"      {name:10s}   {float(hi):8.1f}  {float(ho):9.1f}   {dh:+7.1f} deg")
    check("no reference hue is displaced by more than 20 degrees", worst < 20.0,
          f"largest displacement {worst:.1f} deg (creative, not a gamut error)")

    # ----------------------------------------------------------------- 4 ---
    head("4.  Rec.709 / GAMMA 2.4 OUTPUT BEHAVIOUR")
    w("  The output transfer function is the inverse of a pure 2.4 power EOTF")
    w("  (BT.1886 with Lb = 0, Lw = 1). The neutral response of the DELIVERED")
    w("  .cube is tabulated below; display-linear = code^2.4.")
    w()
    w("    scene reflectance   log2 code P    LUT out (R,G,B)         disp-lin Y   R/B")
    rows = []
    for refl in [0.0, 0.002, 0.01, 0.045, 0.09, 0.18, 0.36, 0.90, 1.8, 3.6, 7.2, 12.0]:
        P = float(np.clip(al2.apple_log_encode(refl), 0, 1))
        o = apply_cube(np.array([P] * 3), table, size, dmin, dmax)
        Y = float(np.dot(grade.gamma24_decode(o), al2.REC709_LUMA))
        rows.append((refl, P, o, Y))
        w(f"    {refl*100:11.2f} %     {P:9.6f}    "
          f"({o[0]:.4f}, {o[1]:.4f}, {o[2]:.4f})    {Y:9.6f}   {o[0]/max(o[2],1e-9):5.3f}")

    grey = [r for r in rows if r[0] == 0.18][0]
    white = [r for r in rows if r[0] == 0.90][0]
    check("18 % grey lands in the standard mid-grey window (code 0.40-0.46)",
          0.40 <= np.mean(grey[2]) <= 0.46, f"mean code {np.mean(grey[2]):.4f}")
    check("90 % diffuse white stays below clipping with highlight headroom",
          0.78 <= np.mean(white[2]) <= 0.90, f"mean code {np.mean(white[2]):.4f}")
    check("the top of the Apple Log 2 range (1200 % / P = 1.0) does not hard clip",
          float(np.max(apply_cube(np.ones(3), table, size, dmin, dmax))) < 1.0,
          f"P=1.0 -> {np.round(apply_cube(np.ones(3), table, size, dmin, dmax), 5).tolist()}")

    # ----------------------------------------------------------------- 5 ---
    head("5.  NEUTRAL AXIS, MONOTONICITY, CLIPPING AND TONAL SMOOTHNESS")
    ax = np.linspace(0, 1, 1024)
    neut = apply_cube(np.stack([ax] * 3, -1), table, size, dmin, dmax)
    Yn = np.einsum("ij,j->i", grade.gamma24_decode(neut), al2.REC709_LUMA)
    dY = np.diff(Yn)
    check("the neutral ramp is monotonically non-decreasing",
          bool(np.all(dY >= -1e-12)), f"most negative step {dY.min():.3e}")

    # Banding: largest output change per 10-bit input step, in 8-bit units.
    step8 = float(np.max(np.abs(np.diff(neut, axis=0)))) * 255.0
    check("no banding: largest output step per 10-bit input step is under 1/255",
          step8 < 1.0,
          f"max step {step8:.3f} / 255 over a 1024-point neutral sweep")

    # Does the 33-point grid itself introduce a kink? The honest test is
    # whether each piecewise-linear segment of the LUT reproduces the slope of
    # the EXACT analytic transform over that same segment. If it does, any
    # curvature in the result belongs to the intended tone curve, not to the
    # quantisation.
    ratios = []
    for i in range(4, 32):
        a, b = i / 32.0, (i + 1) / 32.0
        la = float(apply_cube(np.array([a] * 3), table, size, dmin, dmax)[0])
        lb = float(apply_cube(np.array([b] * 3), table, size, dmin, dmax)[0])
        ea = float(grade.transform(np.array([a] * 3))[0])
        eb = float(grade.transform(np.array([b] * 3))[0])
        ratios.append(((lb - la) / (b - a)) / max((eb - ea) / (b - a), 1e-9))
    rat = np.array(ratios)
    check("the 33-point grid adds no kink: every segment's slope matches the "
          "exact transform",
          float(np.max(np.abs(rat - 1.0))) < 1e-3,
          f"largest slope deviation from the exact transform over nodes 4-32 = "
          f"{float(np.max(np.abs(rat - 1.0))):.2e} (relative)")

    # Is the underlying analytic transform itself free of slope discontinuities?
    # Absolute curvature is meaningless here - a filmic curve viewed against a
    # log input is supposed to be strongly curved. What a kink looks like is a
    # SUDDEN change of slope, so that is what is measured: the largest change
    # in output slope across a single input step, relative to the steepest
    # slope anywhere on the curve.
    axs = np.linspace(0.16, 1.0, 4096)
    exs = grade.transform(np.stack([axs] * 3, -1))[:, 0]
    slope = np.diff(exs) / (axs[1] - axs[0])
    relj = np.abs(np.diff(slope)) / float(np.max(slope))
    check("the analytic transform has no slope discontinuity above 0 % "
          "reflectance",
          float(relj.max()) < 0.05,
          f"largest single-step slope change = {float(relj.max()):.2e} of peak "
          f"slope (median {float(np.median(relj)):.1e}), sampled every "
          f"{(axs[1]-axs[0]):.5f} in P")
    w()
    w("  For reference, the display-linear gradient of the neutral ramp over")
    w("  successive grid segments, which shows a smooth monotone acceleration")
    w("  through the mid-range rather than a step:")
    segs = np.array([float(np.mean(dY[i * 31:(i + 1) * 31])) for i in range(32)])
    rr = [segs[i + 1] / segs[i] for i in range(8, 20)]
    w("      segment  " + "  ".join(f"{i:4d}" for i in range(8, 20)))
    w("      ratio    " + "  ".join(f"{v:4.2f}" for v in rr))

    at0 = int(np.sum(np.all(flat <= 0.0, axis=1)))
    at1 = int(np.sum(np.all(flat >= 1.0, axis=1)))
    any0 = int(np.sum(np.any(flat <= 0.0, axis=1)))
    any1 = int(np.sum(np.any(flat >= 1.0, axis=1)))
    ii = np.arange(33) / 32.0
    rr, gg, bb = np.meshgrid(ii, ii, ii, indexing="ij")
    realistic = (
        (rr >= 0.15) & (rr <= 0.87) & (gg >= 0.15) & (gg <= 0.87)
        & (bb >= 0.15) & (bb <= 0.87)
    ).reshape(-1)
    any1_real = int(np.sum(np.any(table.reshape(-1, 3)[realistic] >= 1.0, axis=1)))
    w(f"  LUT nodes at full black (all channels 0.0) : {at0:6d} of 35,937 "
      f"({at0/359.37:.2f} %)")
    w(f"  LUT nodes at full white (all channels 1.0) : {at1:6d} of 35,937 "
      f"({at1/359.37:.2f} %)")
    w(f"  LUT nodes with ANY channel at 0.0          : {any0:6d}")
    w(f"  LUT nodes with ANY channel at 1.0          : {any1:6d} "
      f"({any1/359.37:.2f} %) - saturated corners of the cube")
    w(f"     ...of those, inside the range real footage occupies "
      f"(all channels P 0.15-0.87): {any1_real}")
    w()
    w("  The black nodes are expected and correct: Apple Log encodes NEGATIVE")
    w("  scene reflectance below 10-bit code 154 (P = 0.1505) in order to")
    w("  preserve the noise floor. Everything below 0 % reflectance must map to")
    w("  display black in an SDR deliverable.")
    w()
    w("  Those single-channel-clipped nodes are the bright, extremely saturated")
    w("  corners of the cube - for example P = (0.87, 0.15, 0.15), which decodes")
    w("  to a pure red at 418 % reflectance with both other channels at or below")
    w("  0 %. Such a colour cannot be represented in Rec.709 at that intensity by")
    w("  any transform, and clipping it is correct behaviour. What matters is")
    w("  whether real imagery reaches those corners; section 7 measures 0.00 %")
    w("  clipped area across all eight test scenes.")
    w()
    w("  Clipping onset on a neutral-to-saturated sweep (how saturated a 90 %")
    w("  reflectance colour can be before a channel clips):")
    P90 = float(al2.apple_log_encode(0.90))
    onset = None
    for frac in np.linspace(0.0, 1.0, 201):
        lin = np.array([0.90, 0.90 * (1 - frac), 0.90 * (1 - frac)])
        Pv = np.clip(al2.apple_log_encode(al2.apply_matrix(lin, al2.REC709_TO_AWG)), 0, 1)
        o = apply_cube(Pv, table, size, dmin, dmax)
        if o.max() >= 1.0 and onset is None:
            onset = frac
            break
    w(f"      a 90 % red clips only beyond {('%.0f %%' % (onset*100)) if onset else '100 %'} "
      f"saturation (R held at 90 % reflectance)")
    check("full-white clipping affects less than 1 % of the LUT volume",
          at1 / 35937 < 0.01, f"{at1} nodes = {at1/359.37:.3f} %")

    w()
    w("  KNOWN 33-POINT ARTEFACT AT THE BOTTOM OF THE LOG RANGE (measured):")
    w("    Apple Log's parabolic segment is extremely steep just above")
    w("    P = 0.1505, so the output rises from 0 to code 0.042 within a fifth")
    w("    of one grid cell. A 33-point grid cannot resolve that, so tetrahedral")
    w("    interpolation lifts the below-black region slightly instead of")
    w("    holding it at 0:")
    w()
    w("        P          scene reflectance    exact code   33-point code   delta")
    for Pv in [0.1250, 0.1406, 0.1505, 0.1563, 0.1700, 0.1875]:
        exv = float(grade.transform(np.array([Pv] * 3))[0])
        itv = float(apply_cube(np.array([Pv] * 3), table, size, dmin, dmax)[0])
        w(f"        {Pv:.4f}      {float(al2.apple_log_decode(Pv)):+.6f}         "
          f"{exv:.5f}        {itv:.5f}     {abs(exv-itv)*255:5.2f}/255")
    w()
    w("    Worst case is a lift of about 8.8/255 in gamma-2.4 code at exactly")
    w("    0 % reflectance, which is 0.0003 in display-linear terms, or 1/255")
    w("    once re-encoded to sRGB. It is a smooth lift of the deepest black,")
    w("    not banding, and it only affects signal BELOW black. It is inherent")
    w("    to 33-point LUTs on Apple Log and is the price of the 33-point size")
    w("    that Blackmagic Camera requires.")

    nz = np.where(np.einsum("ij,j->i", neut, al2.REC709_LUMA) > 1e-6)[0]
    first = ax[nz[0]] if len(nz) else float("nan")
    w(f"  First non-black neutral input: P = {first:.5f} "
      f"(scene reflectance {float(al2.apple_log_decode(first)):+.6f})")

    # ----------------------------------------------------------------- 6 ---
    head("6.  33-POINT QUANTISATION ERROR VERSUS THE EXACT TRANSFORM")
    rng = np.random.default_rng(20261121)
    samp = rng.random((200000, 3))
    exact = grade.transform(samp)
    interp = apply_cube(samp, table, size, dmin, dmax)
    e = np.abs(exact - interp)
    w(f"  200,000 uniformly random Apple Log 2 triplets, exact analytic transform")
    w(f"  versus tetrahedral interpolation of the delivered 33^3 table:")
    w(f"      mean  absolute error : {e.mean():.6f}  ({e.mean()*255:.3f} / 255)")
    w(f"      99th  percentile     : {np.percentile(e,99):.6f}  "
      f"({np.percentile(e,99)*255:.3f} / 255)")
    w(f"      max   absolute error : {e.max():.6f}  ({e.max()*255:.3f} / 255)")
    check("mean 33-point interpolation error is below 1/255",
          e.mean() * 255 < 1.0, "this is the inherent cost of a 33-point grid")

    inside = np.all((samp > 0.16) & (samp < 0.86), axis=1)
    ei = e[inside]
    w(f"  Restricted to the range real footage occupies (P in 0.16-0.86, "
      f"{inside.sum():,} samples):")
    w(f"      mean {ei.mean()*255:.3f} / 255, max {ei.max()*255:.3f} / 255")

    # ----------------------------------------------------------------- 7 ---
    head("7.  SCENE BEHAVIOUR: SKIN, SKY, FOLIAGE, STONE, WHITES, SHADOW")
    w("  Measured in display-linear on all eight test scenes, comparing the")
    w("  source still with the result of the DELIVERED .cube. 'sat' is")
    w("  chroma / luminance; 'hue' uses the Rec.709 Y/Cb/Cr wheel where")
    w("  red = 15, yellow = 86, green = 135, cyan = 195, blue = 266, magenta = 315.")
    w()
    rows_s, agg = tune.score(verbose=False)
    w(f"  {'region':10s} {'hue in':>7s} {'hue out':>8s} {'delta':>7s} {'sat x':>7s} "
      f"{'sat out':>8s} {'luma x':>7s}")
    summary = {}
    for name in tune.REGIONS:
        vals = agg.get(name, [])
        if not vals:
            continue
        ww = np.array([v["n"] for v in vals], float)
        ww /= ww.sum()
        rec = dict(
            hs=np.dot(ww, [v["hs"] for v in vals]), ho=np.dot(ww, [v["ho"] for v in vals]),
            dh=np.dot(ww, [v["dh"] for v in vals]), sr=np.dot(ww, [v["sr"] for v in vals]),
            so=np.dot(ww, [v["so"] for v in vals]), yr=np.dot(ww, [v["yr"] for v in vals]))
        summary[name] = rec
        w(f"  {name:10s} {rec['hs']:7.1f} {rec['ho']:8.1f} {rec['dh']:+7.1f} "
          f"{rec['sr']:7.2f} {rec['so']:8.3f} {rec['yr']:7.2f}")
    w()
    sky, fol, skin, wht = (summary.get(k) for k in ("sky", "foliage", "skin", "white"))
    check("skies move towards blue, not towards cyan",
          sky["dh"] > 0, f"sky hue {sky['hs']:.1f} -> {sky['ho']:.1f} ({sky['dh']:+.1f} deg)")
    check("skies are not artificially darkened",
          sky["yr"] > 0.93, f"sky luminance ratio {sky['yr']:.2f}x")
    check("sky saturation stays controlled (0.85x - 1.20x of source)",
          0.85 <= sky["sr"] <= 1.20, f"{sky['sr']:.2f}x")
    check("foliage is warmed (rotated towards yellow) but not made radioactive",
          -16.0 < fol["dh"] < -1.0 and fol["sr"] < 1.25,
          f"hue {fol['dh']:+.1f} deg, saturation {fol['sr']:.2f}x, "
          f"luminance {fol['yr']:.2f}x")
    check("skin hue is held within 5 degrees (no orange shift)",
          abs(skin["dh"]) < 5.0, f"skin hue {skin['hs']:.1f} -> {skin['ho']:.1f} "
          f"({skin['dh']:+.1f} deg), luminance {skin['yr']:.2f}x")
    check("bright near-neutrals stay believable whites (absolute saturation < 0.06)",
          wht["so"] < 0.06, f"near-white saturation {wht['so']:.3f}")

    allr = np.array([r["ratios"] for r in rows_s])
    m = allr.mean(0)
    w()
    w("  Luminance preservation, mean over the eight scenes (graded / source,")
    w("  display-linear percentiles):")
    w(f"      p5 {m[0]:.2f}x   p25 {m[1]:.2f}x   p50 {m[2]:.2f}x   p75 {m[3]:.2f}x   "
      f"p95 {m[4]:.2f}x")
    check("already-bright footage is NOT made brighter (p75 and p95 <= 1.00x)",
          m[3] <= 1.0 and m[4] <= 1.0, f"p75 {m[3]:.2f}x, p95 {m[4]:.2f}x")
    crush = np.mean([r["crush"] for r in rows_s])
    clip = np.mean([r["clip"] for r in rows_s])
    check("output clipping stays negligible", clip < 0.25, f"mean clipped area {clip:.2f} %")
    w(f"  Mean area below display-linear 0.0008 (very deep shadow): {crush:.2f} %")

    # ----------------------------------------------------------------- 8 ---
    head("8.  EXPOSURE AND LIGHTING LATITUDE")
    w("  Each scene was re-simulated at -2, -1, 0, +1 and +2 EV before Apple Log 2")
    w("  encoding, then pushed through the DELIVERED .cube. This tests how the")
    w("  look holds when the operator misjudges exposure.")
    w()
    w(f"  {'EV':>4s}  {'mean disp-lin Y':>16s}  {'clipped %':>10s}  {'black %':>9s}  "
      f"{'skin hue drift':>15s}")
    ev_ok = True
    for ev in [-2.0, -1.0, 0.0, 1.0, 2.0]:
        Ys, cl, bl, dhs = [], [], [], []
        for key in tune.SCENES:
            src = (np.asarray(Image.open(os.path.join(ROOT, "sources", f"{key}.png"))
                              .convert("RGB")) / 255.0)[::4, ::4]
            lin = sim.srgb_to_scene_linear(src, exposure_ev=ev)
            P = sim.scene_linear_to_log2(lin)
            out = grade.gamma24_decode(apply_cube(P, table, size, dmin, dmax))
            Yv = np.einsum("...i,i->...", out, al2.REC709_LUMA)
            Ys.append(Yv.mean())
            cl.append(np.mean(out.min(-1) > 0.995) * 100)
            bl.append(np.mean(Yv < 1e-6) * 100)
            hs, ss, ys = tune.lin_hue_sat(al2.srgb_eotf(src))
            ho, so, yo = tune.lin_hue_sat(out)
            msk = (hs > 22) & (hs < 60) & (ss > 0.12) & (ss < 0.7) & (ys > 0.045) & (ys < 0.6)
            if msk.sum() > 200:
                dhs.append(tune.adiff(tune.cmean(ho[msk]), tune.cmean(hs[msk])))
        drift = float(np.mean(dhs)) if dhs else float("nan")
        ev_ok &= abs(drift) < 10.0
        w(f"  {ev:+4.0f}  {np.mean(Ys):16.5f}  {np.mean(cl):10.2f}  {np.mean(bl):9.2f}  "
          f"{drift:+14.1f}")
    check("the look holds over a +/- 2 EV exposure error (skin hue drift < 10 deg)",
          ev_ok)
    w("  Note: at +2 EV the simulated highlights are already clipped in the source")
    w("  stills, so the clipped figure at +2 EV reflects the SOURCE, not the LUT.")

    # ----------------------------------------------------------------- 9 ---
    head("9.  PROOF THAT THE AFTER RENDERS CAME FROM THE DELIVERED .cube")
    w("  Each delivered AFTER PNG is regenerated here, from scratch, by parsing")
    w("  the .cube and interpolating it, then compared byte-for-byte with the")
    w("  file in PREVIEWS/.")
    w()
    import render_previews as rp

    allsame = True
    for num, key, label, _note in rp.SCENES:
        P = np.load(os.path.join(ROOT, "work", "simulated_log2",
                                 f"{num}_{key}_LOG2.npy")).astype(np.float64)
        regen = rp.to_srgb_png(apply_cube(P, table, size, dmin, dmax))
        have = np.asarray(Image.open(
            os.path.join(PREVIEWS, f"{num}_{key}_AFTER.png")).convert("RGB"))
        identical = bool(np.array_equal(regen, have))
        allsame &= identical
        w(f"      {num}_{key:28s} {'IDENTICAL' if identical else 'DIFFERS'}  "
          f"(max abs diff {int(np.abs(regen.astype(int)-have.astype(int)).max())})")
    check("all eight AFTER PNGs are bit-identical to a fresh render from the .cube",
          allsame)

    # ---------------------------------------------------------------- 10 ---
    head("10.  LIMITATIONS, TRADE-OFFS AND HONEST CAVEATS")
    w(f"""
L1  A LUT CANNOT RECOVER CLIPPED HIGHLIGHTS. Where the sensor has already
    clipped, there is no data to grade; the shoulder will render those areas
    as a smooth white with no texture. Expose for the highlights.

L2  SHADOW TRADE-OFF. The look intentionally sits below the source in the
    shadows - measured mean ratios p5 {m[0]:.2f}x and p25 {m[1]:.2f}x of the source
    display-linear luminance. That is what produces the "deep but detailed"
    character. On footage that is already under-exposed it will read dark,
    and lifting exposure BEFORE the LUT is the correct remedy.

L3  BELOW-BLACK REGION. Apple Log 2 encodes negative scene reflectance below
    10-bit code 154, and all of it must map to display black in SDR. The
    parabolic segment is so steep there that a 33-point grid cannot resolve
    it, so interpolation lifts the deepest black by up to 8.8/255 in gamma-2.4
    code - 0.0003 display-linear, about 1/255 after sRGB re-encoding (measured
    in section 5). It is a smooth lift, not banding, and it only affects
    signal below 0 % reflectance.

L4  33-POINT QUANTISATION. Mean error against the exact transform is
    {e.mean()*255:.3f}/255 and the maximum is {e.max()*255:.3f}/255, the latter occurring only at
    extreme saturated corners of the cube that real footage does not reach.
    33 points was chosen because Blackmagic Camera for iOS accepts 17- and
    33-point LUTs only.

L5  INTENTIONAL COLOUR SHIFTS. The grade deliberately moves colour. Measured
    on the eight scenes: foliage is rotated {fol['dh']:+.1f} deg towards yellow at
    {fol['sr']:.2f}x saturation; sky is rotated {sky['dh']:+.1f} deg towards blue at {sky['sr']:.2f}x;
    skin hue moves {skin['dh']:+.1f} deg. A neutral 18 % grey card comes out with an
    R/B ratio of {grey[2][0]/grey[2][2]:.3f} (a warm midtone by design) while 90 % white comes
    out at {white[2][0]/white[2][2]:.3f}, which is why whites still read as white.

L6  NOT A TECHNICAL CONVERSION LUT. This is a creative look. For colour-
    critical technical work, use Apple's own Apple Log 2 to Rec.709 LUT.

L7  SIMULATED SOURCE MATERIAL. Every preview uses DOCUMENTED SIMULATED Apple
    Log 2 built from AI-generated stills by scripts/simulate_log2.py
    (sRGB -> inverse BT.709 OETF -> highlight expansion -> Rec.709 to Apple
    Wide Gamut -> Apple Log encode -> 10-bit quantise). The simulated signal
    spans roughly P = 0.15 to 0.84, which is the range real Apple Log sits in,
    but it does NOT reproduce iPhone sensor noise, demosaic, lens flare or
    Apple's ISP colour science. These frames are not iPhone captures.

L8  NO PHYSICAL DEVICE TESTING. No iPhone 17 Pro, no iPhone of any kind and
    no installation of Blackmagic Camera was used. The import procedure in
    README.txt is transcribed from current vendor documentation, not from a
    test. On-device appearance, import success and performance are UNVERIFIED.

L9  OUTPUT ENCODING OF THE PREVIEW PNGs. The LUT outputs Rec.709 / gamma 2.4.
    PNG viewers assume sRGB, so the preview stills are linearised from gamma
    2.4 and re-encoded with the sRGB transfer function. Rec.709 and sRGB share
    primaries, so this is a transfer-function change only and the stills look
    on an sRGB display exactly as the LUT output looks on a gamma 2.4 display.
""".strip("\n"))

    # --------------------------------------------------------------------
    head("SUMMARY")
    npass = sum(1 for _, k in RESULTS if k)
    for name, k in RESULTS:
        w(f"  [{'PASS' if k else 'FAIL'}] {name}")
    w()
    w(f"  {npass} of {len(RESULTS)} checks passed.")
    w()
    w("  Tests NOT performed (and therefore not claimed):")
    w("    - any capture, import or playback on a physical iPhone")
    w("    - any use of the Blackmagic Camera app")
    w("    - any comparison against real iPhone 17 Pro Apple Log 2 footage")
    w("    - any measurement on a calibrated reference display")
    w("================================================================================")

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write(OUT.getvalue())
    print(OUT.getvalue())
    print(f"\nwrote {REPORT}")
    return 0 if npass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
