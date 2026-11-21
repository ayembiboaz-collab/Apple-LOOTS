# Golden Daylight Cinema — Technical Notes (verified specs)

## Input: Apple Log 2 / Apple Wide Gamut

### Apple Log transfer function (identical for Apple Log and Apple Log 2)
Encoding:
  V = 0                              for L < R0
  V = c*(L-R0)^2                     for R0 <= L < Rt
  V = gamma*log2(L+beta) + delta     for L >= Rt
Decoding (used by the LUT):
  L = R0                             for V < 0
  L = sqrt(V/c) + R0                 for 0 <= V < Pt
  L = 2^((V-delta)/gamma) - beta     for V >= Pt
Constants (Apple "Apple Log Profile" / "Apple Log 2" white papers; reproduced in
ACES CSC.Apple.AppleLog2_to_ACES.ctl):
  R0 = -0.05641088
  Rt = 0.01
  c  = 47.28711236
  beta = 0.00964052
  gamma = 0.08550479
  delta = 0.69336945
  Pt = c*(Rt-R0)^2

### Apple Wide Gamut primaries (Apple Log 2 white paper, Sept 2025)
  Red   (0.725, 0.301)
  Green (0.221, 0.814)
  Blue  (0.068, -0.076)
  White D65 (0.3127, 0.3290)
Sources: Apple Log 2 white paper; ampas/aces-input-and-colorspaces
CSC.Apple.AppleLog2_to_ACES.ctl; AcademySoftwareFoundation/OpenColorIO#2343;
OpenColorIO-Config-ACES issue #163 / PR #179.

### AWG -> Rec.709 linear matrix (derived, D65 white on both sides => no CAT)
  [[ 1.70728038, -0.51901992, -0.18826046],
   [-0.12501075,  1.31466236, -0.18965162],
   [-0.04362433, -0.19121437,  1.23483871]]
White maps to [1,1,1] (verified). Method validated by reproducing the standard
BT.2020->BT.709 linear matrix exactly.

## Output: Rec.709 SDR, gamma 2.4
  V_out = L_out^(1/2.4), with a soft highlight shoulder applied to avoid
  harsh digital clipping. BT.709 primaries, D65 white.

## Sources
- Apple Log Profile white paper (developer.apple.com download: "Apple log profile")
- Apple Log 2 white paper (Sept 2025) — AWG primaries
- ampas/aces-input-and-colorspaces, apple/CSC.Apple.AppleLog2_to_ACES.ctl
- AcademySoftwareFoundation/OpenColorIO PR #2343 (APPLE_LOG-APPLEWG_to_ACES2065-1)
- AcademySoftwareFoundation/OpenColorIO-Config-ACES issue #163 / PR #179
- antlerpost.com/colour-spaces/AppleLog.html (curve constants)
