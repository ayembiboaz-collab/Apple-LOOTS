# Rebuilding and testing

Use Python 3.11, `python -m venv .venv`, `.venv/bin/pip install -r requirements.txt`, then `.venv/bin/python scripts/build.py` and `.venv/bin/python scripts/verify_renders.py`. The scripts use the eight committed synthetic JPEG sources; builds recreate the cube, 16 PNGs, contact sheet, and numeric `scripts/measurements.json`. The static gallery, README and validation report are maintained separately. Pillow and NumPy versions are pinned; contact-sheet font is `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`. See SOURCES.md and the validation report for provenance, assumptions, and exact test conditions.

Gallery smoke test: install jsdom 24 into a temporary directory, then run `node scripts/test_gallery.cjs /path/to/node_modules/jsdom`. This emulates the DOM, not Safari or actual browser layout.

Package from the repository root with `.venv/bin/python scripts/package.py`; the script verifies ZIP integrity and SHA-256 equality with every folder file after extraction.
