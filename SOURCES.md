# Technical & Visual Sources / Credits

## 1. Color Science & Technical Specifications

1. **Apple Log Profile White Paper** (Apple Inc., September 2023)
   - Defines the Apple Log OETF transfer function constants (`R_0 = -0.05641088`, `R_t = 0.01`, `c = 47.28711236`, `beta = 0.00964052`, `gamma = 0.08550479`, `delta = 0.69336945`) and piecewise log/quadratic decoding equation.
   - Referenced via Apple Developer Downloads (`Apple_Log_Profile_White_Paper.pdf`) and verified against public implementations.

2. **Apple Log 2 White Paper** (Apple Inc., September 2025) & **AcademySoftwareFoundation/OpenColorIO**
   - Apple Log 2 (iPhone 17 Pro / Pro Max and later) retains the identical Apple Log transfer function while encoding in **Apple Wide Gamut** primaries with a **D65** white point:
     - Red: `(0.725, 0.301)`
     - Green: `(0.221, 0.814)`
     - Blue: `(0.068, -0.076)`
     - White (D65): `(0.3127, 0.3290)`
   - Verified directly against:
     - `AcademySoftwareFoundation/OpenColorIO` PR #2343 (`src/OpenColorIO/transforms/builtins/AppleCameras.cpp` and `tests/cpu/transforms/BuiltinTransform_tests.cpp`)
     - `AcademySoftwareFoundation/OpenColorIO-Config-ACES` Issue #163 / PR #179
     - `colour-science/colour` Issue #1428

3. **ITU-R BT.709 & Display Gamma 2.4 (BT.1886)**
   - Rec.709 primaries: Red `(0.640, 0.330)`, Green `(0.300, 0.600)`, Blue `(0.150, 0.060)`, White D65 `(0.3127, 0.3290)`.
   - Output transfer: Display-referred pure Gamma 2.4 (`V = max(L, 0)^(1 / 2.4)`), standard SDR cinema/broadcast grading reference.

4. **Blackmagic Camera for iOS**
   - Supports Apple Log 2 recording (version 3.1+, iPhone 17 Pro / Pro Max and later) and standard 17-point / 33-point `.cube` 3D LUTs (`LUT_3D_SIZE 33`, `DOMAIN_MIN 0.0 0.0 0.0`, `DOMAIN_MAX 1.0 1.0 1.0`) for Display LUT monitoring and optional recording.

## 2. Simulated Apple Log 2 Test Scene Plates

Genuine iPhone 17 Pro Apple Log 2 camera clips were unavailable in this sandboxed build environment. To test the LUT end-to-end across all eight required photographic scenarios without external stock watermarks or low-resolution thumbnails:

- **Source plates (`sources/plates/01_*.png` .. `08_*.png`)**: High-resolution (`1408 x 768`) photorealistic neutral-daylight reference plates generated via Arena.ai's `generate_image` tool using documentary photography prompts without color-grading filters.
- **Simulated Apple Log 2 (`GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/*_BEFORE.png`)**: Derived deterministically by `scripts/color_pipeline.py`:
  1. Decode sRGB EOTF to linear Rec.709.
  2. Apply a smooth inverse display roll-off (shoulder highlight headroom expansion above 0.72 linear and subtle 0.004 scene black floor) to approximate scene-referred linear dynamic range while preserving 18% mid-gray anchoring.
  3. Transform Linear Rec.709 (D65) -> Linear Apple Wide Gamut (D65) via the exact CIE XYZ chromaticity-derived 3x3 matrix.
  4. Encode with the official Apple Log 2 OETF into 16-bit/8-bit Apple Log 2 representation.
- **Important Disclosure**: These BEFORE plates are mathematically documented *simulated* Apple Log 2 inputs derived from SDR reference plates. They do not represent native iPhone 17 Pro sensor RAW/ProRes debayering, Apple Photonic Engine tone mapping, or physical camera noise/highlight clipping behavior.
