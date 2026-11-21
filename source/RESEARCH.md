# Golden Daylight Cinema: research baseline

- Apple documents appleLog2 as Apple Gamut with an Apple-defined log curve: https://developer.apple.com/documentation/avfoundation/avcapturecolorspace/applelog2
- Apple Log 2 white paper: https://developer.apple.com/download/all/?q=Apple%20Log%202 (developer sign-in may be required; not directly accessed in this environment).
- Academy Software Foundation OpenColorIO implementation: https://github.com/AcademySoftwareFoundation/OpenColorIO/pull/2343 . It states Log 2 shares the Apple Log transfer curve and uses Apple Wide Gamut. Primaries R (.725,.301), G (.221,.814), B (.068,-.076), D65. See also https://github.com/AcademySoftwareFoundation/OpenColorIO-Config-ACES/issues/163 .
- Independently documented Apple Log formula and constants: https://github.com/colour-science/colour/blob/develop/colour/models/rgb/transfer_functions/apple_log_profile.py
- Cross-check: https://www.cined.com/log-cam-and-raw-cam-bring-open-gate-raw-and-log-video-to-older-iphones-a-skeptical-look/ reports the same curve and primaries from Apple's papers.

This is a research baseline, not a validation report. No device tests have been performed. An SDR image inverted into Log is a simulation, not an iPhone camera capture.
