#!/usr/bin/env python3
"""Package GOLDEN_DAYLIGHT_CINEMA/ into GOLDEN_DAYLIGHT_CINEMA.zip and prove
the archive is correct.

The archive is written deterministically (sorted entries, fixed timestamps),
then re-opened and checked three ways:

  1. the ZIP's own CRC test passes for every member;
  2. the delivered .cube is present inside the archive and its SHA-256
     matches the file on disk;
  3. every extracted file is byte-for-byte identical to the source folder,
     with no file missing and no file extra.

    python3 scripts/package.py

Exits non-zero if any check fails.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
ZIP_PATH = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA.zip")
CUBE_REL = "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
SKIP = {".DS_Store", "Thumbs.db"}
FIXED_DATE = (2026, 1, 1, 0, 0, 0)

REQUIRED = [
    "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube",
    "GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html",
    "GOLDEN_DAYLIGHT_CINEMA/README.txt",
    "GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt",
]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> list[tuple[str, str]]:
    out = []
    for dirpath, dirnames, filenames in os.walk(FOLDER):
        dirnames.sort()
        for name in sorted(filenames):
            if name in SKIP:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            out.append((full, rel))
    return sorted(out, key=lambda t: t[1])


def main() -> int:
    if not os.path.isdir(FOLDER):
        print(f"FAIL  missing folder {FOLDER}")
        return 1

    files = collect()
    if not files:
        print("FAIL  nothing to package")
        return 1

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for full, rel in files:
            info = zipfile.ZipInfo(rel, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, "rb") as fh:
                zf.writestr(info, fh.read())

    size = os.path.getsize(ZIP_PATH)
    print(f"wrote {ZIP_PATH}")
    print(f"  {len(files)} files, {size:,} bytes ({size/1024/1024:.2f} MB)")
    print(f"  SHA-256 {sha256(ZIP_PATH)}")
    print()

    ok = True

    # 1. CRC integrity -------------------------------------------------------
    with zipfile.ZipFile(ZIP_PATH) as zf:
        bad = zf.testzip()
        names = set(zf.namelist())
    if bad is None:
        print("[PASS] archive CRC test: every member reads back cleanly")
    else:
        print(f"[FAIL] archive CRC test: first corrupt member is {bad}")
        ok = False

    # 2. required members ----------------------------------------------------
    missing = [r for r in REQUIRED if r not in names]
    if missing:
        print(f"[FAIL] required members missing from the archive: {missing}")
        ok = False
    else:
        print("[PASS] the .cube, gallery, README and validation report are all "
              "inside the archive")

    # 3. the .cube inside the ZIP is the delivered .cube ---------------------
    disk_sha = sha256(os.path.join(ROOT, CUBE_REL))
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zip_sha = hashlib.sha256(zf.read(CUBE_REL)).hexdigest()
    if disk_sha == zip_sha:
        print(f"[PASS] .cube inside the ZIP matches the delivered file")
        print(f"       SHA-256 {disk_sha}")
    else:
        print(f"[FAIL] .cube SHA mismatch\n       disk {disk_sha}\n       zip  {zip_sha}")
        ok = False

    # 4. full extraction comparison -----------------------------------------
    tmp = tempfile.mkdtemp(prefix="gdc_zip_")
    try:
        with zipfile.ZipFile(ZIP_PATH) as zf:
            zf.extractall(tmp)
        mismatch, absent = [], []
        for full, rel in files:
            ext = os.path.join(tmp, rel)
            if not os.path.exists(ext):
                absent.append(rel)
            elif sha256(ext) != sha256(full):
                mismatch.append(rel)
        extracted = set()
        for dp, _dn, fn in os.walk(tmp):
            for n in fn:
                extracted.add(
                    os.path.relpath(os.path.join(dp, n), tmp).replace(os.sep, "/")
                )
        extra = sorted(extracted - {rel for _f, rel in files})

        if absent or mismatch or extra:
            if absent:
                print(f"[FAIL] {len(absent)} file(s) missing after extraction: {absent[:5]}")
            if mismatch:
                print(f"[FAIL] {len(mismatch)} file(s) differ after extraction: {mismatch[:5]}")
            if extra:
                print(f"[FAIL] {len(extra)} unexpected file(s) after extraction: {extra[:5]}")
            ok = False
        else:
            print(f"[PASS] all {len(files)} extracted files are byte-for-byte "
                  f"identical to the folder, with none missing and none extra")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("PACKAGING VERIFIED" if ok else "PACKAGING FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
