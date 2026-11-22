"""Build the distributable zip and verify it matches the deliverable folder.

Produces GOLDEN_DAYLIGHT_CINEMA_PROJECT/GOLDEN_DAYLIGHT_CINEMA.zip
containing the full GOLDEN_DAYLIGHT_CINEMA/ folder.  Then re-extracts into a
temporary directory and verifies: (a) file list matches, (b) SHA256 hashes
match, (c) the .cube is present inside the extracted copy.

Usage:
  python build_zip.py
"""

import hashlib
import sys
import zipfile
from pathlib import Path
import tempfile
import shutil

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
DEL = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA'
ZIP_PATH = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA.zip'


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    assert DEL.exists(), f'deliverable not found: {DEL}'
    files = sorted(p for p in DEL.rglob('*') if p.is_file())
    print(f'Deliverable: {DEL}')
    print(f'Files: {len(files)}')

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in files:
            rel = f.relative_to(PROJECT)
            zf.write(f, rel)

    print(f'Wrote {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes)')

    # verify extraction matches
    tmp = Path(tempfile.mkdtemp(prefix='gd_zip_check_'))
    try:
        with zipfile.ZipFile(ZIP_PATH) as zf:
            zf.extractall(tmp)
        src_hashes = {str(f.relative_to(DEL)): sha256_file(f) for f in files}
        zip_dir = tmp / DEL.name
        if not zip_dir.exists():
            zip_dir = tmp
        zip_files_path = sorted(p for p in zip_dir.rglob('*') if p.is_file())
        problems = []
        zip_hashes = {str(p.relative_to(zip_dir)): sha256_file(p) for p in zip_files_path}
        if set(zip_hashes) != set(src_hashes):
            only_src = set(src_hashes) - set(zip_hashes)
            only_zip = set(zip_hashes) - set(src_hashes)
            if only_src:
                problems.append(f'minissing in zip: {sorted(only_src)}')
            if only_zip:
                problems.append(f'extra in zip: {sorted(only_zip)}')
        else:
            for rel, hz in src_hashes.items():
                if zip_hashes.get(rel) != hz:
                    problems.append(f'hash mismatch: {rel}')
        # .cube present inside extracted copy
        cube_inside = zip_dir / 'LUT' / 'GOLDEN_DAYLIGHT_CINEMA.cube'
        cube_ok = cube_inside.exists()
        # print summary
        print(f'Extracted file count: {len(zip_hashes)}')
        print(f'.cube present inside zip: {cube_ok}')
        if problems:
            for p in problems:
                print(f'PROBLEM: {p}')
            print('VERIFY: FAIL')
            raise SystemExit(1)
        if not cube_ok:
            print('VERIFY: FAIL (missing .cube in zip)')
            raise SystemExit(1)
        print('VERIFY: PASS (file list + SHA256 hashes match)')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
