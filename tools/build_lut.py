"""Build GOLDEN_DAYLIGHT_CINEMA.cube (33x33x33, Apple Log 2 -> Rec.709 gamma 2.4)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from lut_core import apple_log2_decode, M_AWG_TO_R709
from grade import grade_full

SIZE = 33
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(
    HERE, '..', 'GOLDEN_DAYLIGHT_CINEMA', 'LUT', 'GOLDEN_DAYLIGHT_CINEMA.cube'))

def main():
    axis = np.linspace(0.0, 1.0, SIZE)
    dec = apple_log2_decode(axis)
    # meshgrid: r fastest, then g, then b (red varies fastest in .cube data order)
    B, G, R = np.meshgrid(dec, dec, dec, indexing='ij')  # shapes (33,33,33)
    lin_awg = np.stack([R, G, B], axis=-1).reshape(-1, 3)          # (35937,3)
    lin_709 = lin_awg @ M_AWG_TO_R709.T                             # (35937,3)
    out = grade_full(lin_709)                                       # (35937,3)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('TITLE "GOLDEN_DAYLIGHT_CINEMA"\n')
        f.write('COMMENT "Apple Log 2 (Apple Wide Gamut) -> Rec.709 SDR, gamma 2.4. Standalone."\n')
        f.write('COMMENT "GOLDEN DAYLIGHT CINEMA - warm Mediterranean travel-film grade"\n')
        f.write('LUT_3D_SIZE 33\n')
        f.write('DOMAIN_MIN 0.0 0.0 0.0\n')
        f.write('DOMAIN_MAX 1.0 1.0 1.0\n')
        for o in out:
            f.write(f"{o[0]:.6f} {o[1]:.6f} {o[2]:.6f}\n")
    print(f"Wrote {OUT} ({out.shape[0]} nodes)")

if __name__ == '__main__':
    main()
