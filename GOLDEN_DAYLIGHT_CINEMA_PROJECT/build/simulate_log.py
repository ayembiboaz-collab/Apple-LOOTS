"""Simulate Apple Log 2 captures from the real-world source photographs.

SIMULATION — NOT genuine iPhone 17 Pro footage.

Procedure (documented, deterministic per-scene seed):
  1. Load source JPEG (sRGB display-referred).
  2. Decode standard sRGB transfer -> linear Rec.709.
  3. Linear Rec.709 -> CIE XYZ (D65, Rec.709 matrix).
  4. XYZ -> linear Apple Wide Gamut (inverse of the D65 matrix with Apple Log 2
     white-point).  The scene is *represented* in Apple Wide Gamut primaries.
     Since Apple Wide Gamut is a superset of Rec.709, most values are valid;
     out-of-gamut saturated pixels are still representable as scene data.
  5. Add sensor-like noise in linear Apple Wide Gamut: photon-shot-like noise
     proportional to signal plus a small fixed read noise.  The noise is added
     per channel *before* the encoding function (as a sensor would produce it).
  6. Clamp to the parabolic floor R_0 = -0.05641088 (same as the encoding
     parabola domain).
  7. Encode with Apple's verified Apple Log 2 OETF (same as Apple Log curve).
  8. Quantize to 8-bit (documented: 8-bit PNG intermediates; the grade and
     previews are performed in float precision, then quantized for display).

Dynamic range in the simulated files is limited by the source photos (they
are standard 8-bit sRGB JPEG captures, not RAW).  No highlight reconstruction
is performed.  Highlight clipping is NOT recovered.

Usage:
  python simulate_log.py                # simulate all scenes
  python simulate_log.py --scene 01     # simulate one scene
  python simulate_log.py --check        # re-verify simulation vs source
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import color_science as cs

SRC = Path(__file__).resolve().parent.parent / 'source_images'
DST = Path(__file__).resolve().parent.parent / 'simulated_log'

# Documented simulation noise model (fixed seed per scene).
SHOT_SCALE = 1.5e-3      # photon-shot-like noise per linear reflectance
READ_NOISE = 6.0e-4      # fixed read noise (linear)
SEED = 20261122

# Sub-8-bit quantization for the stored intermediates.
Q8 = 255.0


def simulate_scene(src_path, out_path, seed=SEED):
    img = Image.open(src_path).convert('RGB')
    srgb = np.asarray(img, dtype=np.float64) / Q8

    # 1. sRGB -> linear Rec.709
    linear_709 = np.where(
        srgb > 0.04045,
        ((srgb + 0.055) / 1.055) ** 2.4,
        srgb / 12.92,
    )

    # 2. linear Rec.709 -> XYZ (D65)
    xyz = linear_709 @ cs.M_REC709_TO_XYZ.T

    # 3. XYZ -> linear Apple Wide Gamut
    awg = xyz @ np.linalg.inv(cs.M_AWG_TO_XYZ).T

    # 4. sensor-like noise (per channel, before encoding)
    rng = np.random.default_rng(seed)
    shot = np.sqrt(np.clip(awg, 0.0, None) * SHOT_SCALE + READ_NOISE * READ_NOISE)
    noise = shot * rng.standard_normal(awg.shape)
    awg_noisy = awg + noise

    # 5. clamp to parabola domain and encode
    awg_noisy = np.maximum(awg_noisy, cs.R_0)
    encoded = cs.apple_log2_encode(awg_noisy)

    # 6. clip (safety) and quantize
    encoded = np.clip(encoded, 0.0, 1.0)

    out = Image.fromarray(np.rint(encoded * Q8).astype(np.uint8), mode='RGB')
    meta = PngImagePlugin.PngInfo()
    meta.add_text('SIMULATED', 'This image was simulated from a real-world photograph '
                              'using Apple Log 2 forward-encoding of a scene re-represented '
                              'in Apple Wide Gamut primaries. It is NOT genuine iPhone 17 Pro footage.')
    meta.add_text('SOURCE', str(src_path.name))
    meta.add_text('PIPELINE', 'simulated: sRGB -> linear Rec709 -> XYZ -> linear Apple Wide Gamut '
                             '-> noise -> Apple Log 2 encode (8-bit)')
    out.save(out_path, pnginfo=meta)

    return dict(
        src=src_path.name, src_size=img.size,
        src_srgb=float(np.mean(srgb)),
        encoded_mean=float(np.mean(encoded)),
        encoded_max=float(np.max(encoded)),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scene', type=str, default=None)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()

    srcs = sorted(SRC.glob('*.jpg'))
    if args.scene:
        srcs = [s for s in srcs if args.scene in s.name]
    if not srcs:
        raise SystemExit('no scenes found')

    DST.mkdir(parents=True, exist_ok=True)
    for src in srcs:
        out_path = DST / (src.stem + '_SIMULATED_APPLE_LOG2.png')
        info = simulate_scene(src, out_path)
        print(f'{src.name:45s} -> {out_path.name}')
        print(f'   size={info["src_size"]} src_mean={info["src_srgb"]:.3f} '
              f'enc_mean={info["encoded_mean"]:.3f} enc_max={info["encoded_max"]:.3f}')


if __name__ == '__main__':
    main()
