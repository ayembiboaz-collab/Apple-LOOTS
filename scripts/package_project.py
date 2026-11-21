#!/usr/bin/env python3
"""
GOLDEN DAYLIGHT CINEMA — Archive Packager & Extraction Integrity Verifier
=========================================================================

Creates `GOLDEN_DAYLIGHT_CINEMA.zip` containing the complete `GOLDEN_DAYLIGHT_CINEMA/`
deliverable folder (including `LUT/GOLDEN_DAYLIGHT_CINEMA.cube`), then extracts the ZIP
into a temporary verification directory and compares every file byte-for-byte (SHA-256)
against the source folder.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import zipfile


ROOT_DIR = Path(__file__).resolve().parent.parent
FOLDER_NAME = "GOLDEN_DAYLIGHT_CINEMA"
SOURCE_DIR = ROOT_DIR / FOLDER_NAME
ZIP_PATH = ROOT_DIR / "GOLDEN_DAYLIGHT_CINEMA.zip"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_and_verify_zip() -> dict:
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Deliverable folder missing: {SOURCE_DIR}")

    expected_required = [
        "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube",
        "GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html",
        "GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png",
        "GOLDEN_DAYLIGHT_CINEMA/README.txt",
        "GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt",
    ]
    for idx in range(1, 9):
        # Verify all 8 BEFORE and 8 AFTER PNGs exist
        matches_b = list((SOURCE_DIR / "PREVIEWS").glob(f"0{idx}_*_BEFORE.png"))
        matches_a = list((SOURCE_DIR / "PREVIEWS").glob(f"0{idx}_*_AFTER.png"))
        if len(matches_b) != 1 or len(matches_a) != 1:
            raise FileNotFoundError(f"Missing preview pair for scene 0{idx}")

    source_files = sorted([p for p in SOURCE_DIR.rglob("*") if p.is_file()])
    source_hashes: dict[str, tuple[int, str]] = {}

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in source_files:
            rel_arc = file_path.relative_to(ROOT_DIR).as_posix()
            zf.write(file_path, arcname=rel_arc)
            source_hashes[rel_arc] = (file_path.stat().st_size, sha256_file(file_path))

    for req in expected_required:
        if req not in source_hashes:
            raise AssertionError(f"Required file missing from archive: {req}")

    # Test ZIP integrity and extract to temporary directory to confirm 100% match
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            bad_file = zf.testzip()
            if bad_file is not None:
                raise RuntimeError(f"Corrupted member in ZIP archive: {bad_file}")
            zf.extractall(tmp_path)

        extracted_files = sorted([p for p in (tmp_path / FOLDER_NAME).rglob("*") if p.is_file()])
        extracted_hashes: dict[str, tuple[int, str]] = {}
        for ep in extracted_files:
            rel_arc = ep.relative_to(tmp_path).as_posix()
            extracted_hashes[rel_arc] = (ep.stat().st_size, sha256_file(ep))

    if source_hashes != extracted_hashes:
        raise AssertionError("Mismatch between GOLDEN_DAYLIGHT_CINEMA/ folder and extracted ZIP contents!")

    cube_key = "GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube"
    cube_size, cube_sha = source_hashes[cube_key]
    zip_size = ZIP_PATH.stat().st_size
    zip_sha = sha256_file(ZIP_PATH)

    print(f"Created and verified {ZIP_PATH.name}:")
    print(f"  ZIP Size          : {zip_size:,} bytes ({zip_size / (1024*1024):.2f} MB)")
    print(f"  ZIP SHA-256       : {zip_sha}")
    print(f"  Total Files in ZIP: {len(source_hashes)} (100% SHA-256 match on extraction)")
    print(f"  Verified .cube    : {cube_key} ({cube_size:,} bytes, SHA-256={cube_sha[:16]}...)")

    return {
        "zip_size": zip_size,
        "zip_sha256": zip_sha,
        "file_count": len(source_hashes),
        "cube_size": cube_size,
        "cube_sha256": cube_sha,
    }


if __name__ == "__main__":
    build_and_verify_zip()
