# Build and validate the LUT-only evaluation package

Run in this directory, with Python 3.11:

    python -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python pipeline.py
    .venv/bin/python validate.py
    .venv/bin/python physical_tests.py
    .venv/bin/python package.py

pipeline.py writes the deliverable cube directly. validate.py reparses that file
and writes ../validation/lut-validation.json. physical_tests.py loads it through
OpenColorIO as an independent evaluator and writes ../validation/physical-tests.json.
package.py packages the deliverable folder and verifies every entry and SHA-256.
The document reports are maintained explicitly: update their measurements and
hashes if you change the pipeline. The small difference against source primaries
and the synthetic tests use D65; see the deliverable report for assumptions and
limitations. Older prototype results are preserved in candidate-validation.json.

The package currently contains the LUT and technical documentation ONLY. The
requested real-image gallery, before/afters, contact sheet, real-world visual
refinement and physical device testing are not completed. Do not label it a
reference-grade or fully validated release. No external photos are required to
reproduce the files currently included in this evaluation package.
