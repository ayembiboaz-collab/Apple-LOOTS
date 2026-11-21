# Project sources and provenance

Eight scene source images in `source_images/` are AI-generated for this project using Arena's image generation tool, 2026-11-21; they are synthetic images, not photographs of real people or iPhone captures. Their pixels are committed so the test set can be rebuilt without regenerating them. They are treated as display-referred sRGB; no camera characterization is implied.

Technical references:
- Apple AVFoundation: https://developer.apple.com/documentation/avfoundation/avcapturecolorspace/applelog2 (Log 2 uses Apple Gamut and an Apple-defined Log curve).
- Apple, *Apple Log 2 White Paper*, September 2025: https://developer.apple.com/download/all/?q=Apple%20Log%202 (developer access may be required). Not directly read in this sandbox; exact constants and primaries cross-checked against sources below.
- Colour Science Apple Log implementation and examples: https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/apple_log_profile.py
- OpenColorIO Apple Log 2 transform and primaries: https://github.com/AcademySoftwareFoundation/OpenColorIO/pull/2343
- CineD independent published description: https://www.cined.com/log-cam-and-raw-cam-bring-open-gate-raw-and-log-video-to-older-iphones-a-skeptical-look/
- ITU-R BT.1886 reference EOTF: https://www.itu.int/rec/R-REC-BT.1886
- Practical Blackmagic Camera LUT importing: https://lumadune.com/guides/how-to-use-apple-log-lut-blackmagic-camera (third-party; menu names can vary).
