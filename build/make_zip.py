#!/usr/bin/env python3
"""Package GOLDEN_DAYLIGHT_CINEMA/ as a distributable ZIP and prove it round-trips.

Writes dist/GOLDEN_DAYLIGHT_CINEMA_v1.0.zip (gitignored; attach to a release),
then extracts it to a temporary folder and compares the SHA-256 of every file
against the working tree, plus a byte comparison of the .cube itself.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile

import render_previews as rp

ROOT = rp.ROOT
PROJ = rp.PROJ
NAME = "GOLDEN_DAYLIGHT_CINEMA"
VERSION = "v1.0"
DIST = os.path.join(ROOT, "dist")
ZIP = os.path.join(DIST, f"{NAME}_{VERSION}.zip")


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(DIST, exist_ok=True)
    files = []
    for base, _dirs, names in os.walk(PROJ):
        for n in names:
            files.append(os.path.join(base, n))
    files.sort()

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            rel = os.path.relpath(path, os.path.dirname(PROJ))
            info = zipfile.ZipInfo(rel, date_time=(2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, open(path, "rb").read())

    size = os.path.getsize(ZIP)
    print(f"wrote {ZIP}  ({size / 1e6:.1f} MB, {len(files)} files)")

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(ZIP) as z:
            bad = z.testzip()
            assert bad is None, f"corrupt member {bad}"
            z.extractall(tmp)
        mismatch = []
        for path in files:
            rel = os.path.relpath(path, os.path.dirname(PROJ))
            clone = os.path.join(tmp, rel)
            if not os.path.exists(clone) or sha(clone) != sha(path):
                mismatch.append(rel)
        print(f"members checked: {len(files)}, mismatches: {len(mismatch)}")
        if mismatch:
            for m in mismatch:
                print("  MISMATCH", m)
            raise SystemExit(1)

        cube = os.path.join(tmp, NAME, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")
        a = open(cube, "rb").read()
        b = open(os.path.join(PROJ, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube"), "rb").read()
        print(f"cube byte-identical: {a == b} ({len(b):,} bytes, sha256 {sha(cube)[:16]}...)")

    print("ZIP verified.")


if __name__ == "__main__":
    main()
