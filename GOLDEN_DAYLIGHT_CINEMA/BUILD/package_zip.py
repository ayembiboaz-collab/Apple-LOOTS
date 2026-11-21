#!/usr/bin/env python3
"""
package_zip.py -- build GOLDEN_DAYLIGHT_CINEMA.zip and verify it.

The ZIP contains the complete GOLDEN_DAYLIGHT_CINEMA folder: the LUT, all
preview PNGs, the gallery, the contact sheet, the docs and the build scripts.
Verification (not just creation):
  * the archive opens and every member's CRC checks out (zipfile.testzip)
  * every member's bytes are compared against the file on disk
  * the .cube is present and, once extracted to a temp dir, is byte-identical
  * the extracted .cube still has 33^3 valid entries
"""
import hashlib
import os
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cube import read_cube  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../GOLDEN_DAYLIGHT_CINEMA
PARENT = os.path.dirname(ROOT)
NAME = os.path.basename(ROOT)
ZIP = os.path.join(PARENT, NAME + ".zip")

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints"}

# The simulated LOG2 plates are inputs to the process rather than deliverables,
# and at ~14 MB they are the only thing that would push the archive over
# GitHub's 100 MB per-file limit. They stay in the repository (PREVIEWS/) so the
# input is still inspectable online; everything the brief asks for is in the ZIP.
ZIP_EXCLUDE_SUFFIXES = ("_LOG2_SIMULATED.png",)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.startswith(".") or f.endswith(".pyc"):
                continue
            if f.endswith(ZIP_EXCLUDE_SUFFIXES):
                continue
            files.append(os.path.join(dirpath, f))
    return sorted(files)


def main():
    files = collect()
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            arc = os.path.join(NAME, os.path.relpath(path, ROOT))
            z.write(path, arc)
    print(f"wrote {os.path.basename(ZIP)}  "
          f"({os.path.getsize(ZIP)/1e6:.1f} MB, {len(files)} files)")

    problems = []

    # 1. integrity + parity with disk
    with zipfile.ZipFile(ZIP) as z:
        bad = z.testzip()
        if bad:
            problems.append(f"CRC failure: {bad}")
        names = set(z.namelist())
        for path in files:
            arc = os.path.join(NAME, os.path.relpath(path, ROOT))
            if arc not in names:
                problems.append(f"missing from archive: {arc}")
                continue
            if z.read(arc) != open(path, "rb").read():
                problems.append(f"content differs: {arc}")

        # 2. the .cube specifically
        cube_arc = f"{NAME}/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
        if cube_arc not in names:
            problems.append("the .cube is NOT in the archive")
        else:
            with tempfile.TemporaryDirectory() as td:
                z.extract(cube_arc, td)
                extracted = os.path.join(td, cube_arc)
                if sha(extracted) != sha(os.path.join(ROOT, "LUT",
                                                      "GOLDEN_DAYLIGHT_CINEMA.cube")):
                    problems.append("extracted .cube differs from the source .cube")
                tbl, meta = read_cube(extracted)
                if tbl.shape != (33, 33, 33, 3):
                    problems.append(f"extracted .cube has shape {tbl.shape}")
                else:
                    print(f"extracted .cube verified: {tbl.shape}, "
                          f"sha256 {sha(extracted)[:16]}..., "
                          f"{os.path.getsize(extracted)} bytes")

        # 3. the required deliverable set
        required = [
            f"{NAME}/LUT/GOLDEN_DAYLIGHT_CINEMA.cube",
            f"{NAME}/GALLERY/index.html",
            f"{NAME}/CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png",
            f"{NAME}/README.txt",
            f"{NAME}/VALIDATION_REPORT.txt",
        ] + [f"{NAME}/PREVIEWS/scene{i:02d}_{stem}_{tag}.png"
             for i, stem in [(1, "harsh_midday_city"), (2, "midday_portrait"),
                             (3, "mediterranean_street"), (4, "bright_beach_daylight"),
                             (5, "landscape_greenery_mountains"),
                             (6, "golden_hour_landscape"),
                             (7, "modern_architecture"), (8, "outdoor_travel_people")]
             for tag in ("BEFORE", "AFTER")]
        for r in required:
            if r not in names:
                problems.append(f"required deliverable missing: {r}")

    if problems:
        print("\nZIP VERIFICATION FAILED:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"\nZIP verified: {len(names)} entries, all CRCs valid, all bytes match "
          f"disk, .cube present and re-parsable, 8 BEFORE + 8 AFTER present.")
    print("Not included (by design): PREVIEWS/*_LOG2_SIMULATED.png - the "
          "simulated log inputs, which remain in the repository.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
