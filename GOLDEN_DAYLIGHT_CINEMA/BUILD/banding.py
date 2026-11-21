#!/usr/bin/env python3
"""
banding.py -- objective smoothness / banding measurement.

Banding is a *quantisation* artefact: in a smooth gradient the 8-bit output
plateaus and then takes a large step. We measure, over low-texture regions:

  plateau  fraction of horizontal neighbour pairs with identical 8-bit code
  step_p99 99th percentile 8-bit step size between neighbouring pixels
  steps>=2 fraction of neighbours differing by 2 or more codes

A render that introduces banding shows a higher plateau fraction AND larger
steps than its source. Measured on the source plate, the plain technical decode
and the LUT output, so any artefact can be attributed.
"""
import numpy as np


def regions_with_smoothness(img8, thr=3.0, frac=0.35):
    """Pick the smoothest horizontal bands of the image (sky/wall-like areas)."""
    g = img8.astype(np.float64).mean(axis=2)
    h = g.shape[0]
    rows = []
    for y in range(0, h, 16):
        band = g[y:y + 16]
        if band.size == 0:
            continue
        d = np.abs(np.diff(band, axis=1)).mean()
        rows.append((d, y, min(y + 16, h)))
    rows.sort()
    keep = rows[:max(1, int(len(rows) * frac))]
    return [(y0, y1) for _, y0, y1 in keep]


def measure(img_u8, regions):
    out = {"plateau": 0.0, "step_p99": 0.0, "step_ge2": 0.0, "n": 0}
    plateaus = steps = 0
    allsteps = []
    for y0, y1 in regions:
        band = img_u8[y0:y1].astype(np.int16)
        d = np.abs(np.diff(band, axis=1))          # (h, w-1, 3)
        steps_here = d.reshape(-1)
        allsteps.append(steps_here)
        plateaus += int((steps_here == 0).sum())
        steps += steps_here.size
    s = np.concatenate(allsteps)
    out.update(plateau=plateaus / max(steps, 1),
               step_p99=float(np.percentile(s, 99)),
               step_ge2=float((s >= 2).mean()),
               n=int(s.size))
    return out


def compare(src_u8, before_u8, after_u8, smooth_regions):
    return {"source": measure(src_u8, smooth_regions),
            "before": measure(before_u8, smooth_regions),
            "after": measure(after_u8, smooth_regions)}
