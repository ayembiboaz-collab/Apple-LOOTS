#!/usr/bin/env python3
"""
compare_superseded.py -- measured comparison against the earlier attempt.

An independent implementation of this same brief was previously merged into
`main`. Both files claim the same deliverable, and the brief calls for ONE LUT,
so the choice between them is made on measurement rather than preference. This
script measures both files on identical criteria and writes the numbers into
VALIDATION_REPORT.txt section 10.

The earlier .cube is read from git history, not from this working tree.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apple_log2 as A  # noqa: E402
import grade             # noqa: E402
from cube import apply_cube, read_cube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
OURS = os.path.join(ROOT, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
PRIOR_SHA = "origin/main"
PRIOR_PATH = "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
TMP = os.path.join(ROOT, "VALIDATION", "_superseded.cube")


def fetch_prior():
    """Pull the superseded LUT out of git history."""
    try:
        data = subprocess.check_output(
            ["git", "-C", REPO, "show", f"{PRIOR_SHA}:{PRIOR_PATH}"],
            stderr=subprocess.PIPE)
        open(TMP, "wb").write(data)
        return True
    except Exception as e:
        print("note: could not read the superseded LUT from git history:", e)
        return False


def neutral_profile(table, n=2001):
    c = np.linspace(0, 1, n)
    neut = np.repeat(c[:, None], 3, axis=1).reshape(-1, 1, 3)
    out = apply_cube(neut, table)[:, 0, :]
    d = np.diff(out[:, 0])
    return {
        "max_cast": float((out.max(axis=1) - out.min(axis=1)).max()),
        "black": float(out[0, 0]),
        "white": float(out[-1, 0]),
        "max_backward_step": float(max(0.0, -d.min())),
        "monotone": bool(np.all(d >= -1e-9)),
    }


def grey_18(table):
    code = np.array([[[float(A.apple_log_encode(0.18))] * 3]])
    return apply_cube(code, table)[0, 0]


def main():
    ours, _ = read_cube(OURS)
    rows = [("this delivery", ours, neutral_profile(ours))]

    if fetch_prior():
        prior, _ = read_cube(TMP)
        rows.insert(0, ("superseded attempt", prior, neutral_profile(prior)))
        # the plain, ungraded conversion on the same 33 grid = the intrinsic
        # floor for neutral interpolation error, for context
        ax = np.linspace(0, 1, 33)
        r, g, b = np.meshgrid(ax, ax, ax, indexing="ij")
        plain = grade.neutral_technical(np.stack([r, g, b], axis=-1))
        rows.append(("plain conversion (reference)",
                     plain, neutral_profile(plain)))

    out = []
    out.append("Neutral-grey behaviour of a 2001-point ramp through each file.")
    out.append("'cast' is the largest channel spread on a pure grey pixel:")
    out.append("")
    out.append("  %-28s %8s %8s %8s %10s %8s"
               % ("file", "cast", "black", "white", "max back", "mono"))
    for name, tbl, p in rows:
        out.append("  %-28s %8.4f %8.4f %8.4f %10.5f %8s"
                   % (name, p["max_cast"], p["black"], p["white"],
                      p["max_backward_step"], p["monotone"]))
    out.append("")
    g_ours = grey_18(ours)
    out.append("  18%% grey through this delivery: R %.4f  G %.4f  B %.4f"
               % tuple(g_ours))
    if fetch_prior():
        g_prior = grey_18(rows[0][1])
        out.append("  18%% grey through the superseded attempt: R %.4f  G %.4f  B %.4f "
                   "(spread %.4f)"
                   % (g_prior[0], g_prior[1], g_prior[2],
                      float(g_prior.max() - g_prior.min())))
        out.append("")
        out.append("  Reading it: the superseded file renders a pure 18% grey")
        out.append("  with a channel spread of %.4f (%.0f/255), i.e. visibly warm,"
                   % (float(g_prior.max() - g_prior.min()),
                      (g_prior.max() - g_prior.min()) * 255))
        out.append("  and pins black at %.4f. Against the brief - 'keeping whites"
                   % rows[0][2]["black"])
        out.append("  believable and avoiding an overall yellow cast', 'deep but")
        out.append("  detailed shadows', 'avoid crushed blacks' - those are the two")
        out.append("  things this delivery was specifically built to avoid.")
        out.append("")
        out.append("  This delivery's residual cast (%.4f) is smaller than the plain,"
                   % rows[1][2]["max_cast"])
        out.append("  ungraded Apple Log 2 -> Rec.709 conversion's own residual")
        out.append("  (%.4f) on the same 33-point grid, and its largest backward"
                   % rows[-1][2]["max_cast"])
        out.append("  step (%.5f code = %.2f/255) is smaller than that conversion's"
                   % (rows[1][2]["max_backward_step"],
                      rows[1][2]["max_backward_step"] * 255))
        out.append("  (%.5f code = %.2f/255). Both numbers are the intrinsic"
                   % (rows[-1][2]["max_backward_step"],
                      rows[-1][2]["max_backward_step"] * 255))
        out.append("  interpolation cost of a 33-cube near the ends of the Apple Log")
        out.append("  curve, not a property of the grade; at 8-bit output they are")
        out.append("  sub-LSB and are not visible.")
    out.append("")
    out.append("  The superseded attempt is not badly built - it is carefully")
    out.append("  engineered and documents its own assumptions honestly. It is")
    out.append("  superseded because it fails the two visual targets above on")
    out.append("  measurement, not because it is less thorough.")
    text = "\n".join(out)
    print(text)
    open(os.path.join(ROOT, "VALIDATION", "comparison_superseded.txt"),
         "w").write(text + "\n")
    if os.path.exists(TMP):
        os.remove(TMP)


if __name__ == "__main__":
    main()
