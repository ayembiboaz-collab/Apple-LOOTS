# Research checkpoint (2026-11-22)

* Apple identifies Apple Log 2 as Apple Gamut primaries with an Apple-defined logarithmic transfer function: https://developer.apple.com/documentation/avfoundation/avcapturecolorspace/applelog2
* OpenColorIO's reviewed Apple Log 2 implementation says it uses the same curve as Apple Log, but Apple Wide Gamut instead of BT.2020: https://github.com/AcademySoftwareFoundation/OpenColorIO/pull/2343
* Apple Log 2 white paper, as linked from a colour-science issue: https://github.com/colour-science/colour/issues/1428 . The attachment could not be retrieved via the available network at this checkpoint; constants must be cross-checked against a traceable implementation.
* Blackmagic's iOS Camera product page explicitly lists industry-standard 17 and 33 point 3D LUTs and monitoring or recording a LUT: https://www.blackmagicdesign.com/products/blackmagiccamera . It does not establish an on-device test of this file.
* This environment restricts direct image-host network access. Images must not be used without individual verified author/licence/provenance. Real Apple Log 2 footage has not yet been obtained; do not imply simulations are camera footage.
