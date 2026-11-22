# Reproducing Golden Daylight Cinema

1. Create a Python 3.11+ virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/requirements.txt
   ```
2. Bake the 33x33x33 `.cube` LUT, generate simulated Apple Log 2 intermediates, render all 8 BEFORE/AFTER PNGs, and build the contact sheet:
   ```bash
   PYTHONPATH=GOLDEN_DAYLIGHT_CINEMA_PROJECT/build .venv/bin/python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/build_and_render.py
   ```
3. Run the validation suite against the delivered `.cube`:
   ```bash
   PYTHONPATH=GOLDEN_DAYLIGHT_CINEMA_PROJECT/build .venv/bin/python GOLDEN_DAYLIGHT_CINEMA_PROJECT/build/validate_lut.py
   ```
