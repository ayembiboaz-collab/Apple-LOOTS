# Experimental build checkpoint — NOT a finished deliverable

Run from this directory, with Python 3.11 or later:

    python -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python pipeline.py
    .venv/bin/python validate.py

This produces a candidate.cube and validation output; neither is an approved final deliverable. Sources and known problems are in RESEARCH.md. The float64 analytic pipeline decodes Apple Log 2 using the constants reproduced in OCIO, converts Apple Wide Gamut to linear Rec.709 (both D65), grades in OKLab, compresses chroma towards the neutral axis at constant OKLab lightness and hue, and encodes with pure 1/2.4 power. The toe comes from the log encoding and nonnegative scene-light threshold, and the shoulder is L³/(1+L³), with L in OKLab. This is a prototype, not a verified reference rendering or a film-emulation standard. L³ is a perceptual-lightness proxy, not physical luminance. There is no spatial processing or depth awareness. The 33-grid is sampled analytically on the uniform log input grid; no hidden shaper is used. No resampling of the .cube can add information between grid points.

No camera footage or real-world image renders have been built at this checkpoint. In particular, source images, licences, simulation assumptions, independent AFTER rendering, visual refinement and device tests remain unfinished. The candidate must not be represented as the final LUT until the specified tests have actually been performed and passed or their failures fully disclosed.

The recorded intermediate results are in ../validation/candidate-validation.json and explained in ../validation/STATUS.md. The current candidate demonstrably fails several release checks. Do not publish it as the finished look.
