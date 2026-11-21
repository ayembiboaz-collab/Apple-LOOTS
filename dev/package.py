"""
package.py -- build GOLDEN_DAYLIGHT_CINEMA.zip and verify it.

The archive contains the deliverable folder exactly as it exists in the
repository, at the top level, so unzipping gives GOLDEN_DAYLIGHT_CINEMA/.

Verification (all performed, all printed):
  * ZIP opens and every member passes its CRC
  * the member list equals the folder's file list, no missing and no extra
  * every extracted file is byte-identical (SHA-256) to the folder copy
  * the .cube is present inside the archive and its hash matches the one in
    SCENES/render_manifest.json
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile

import scenes as S

FOLDER = S.PROJ
ZIP = os.path.join(S.ROOT, 'GOLDEN_DAYLIGHT_CINEMA.zip')

# Never ship caches or the archive itself.
SKIP_DIRS = {'__pycache__', '.git'}
SKIP_EXT = {'.npy', '.pyc'}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def folder_files():
    out = []
    for root, dirs, files in os.walk(FOLDER):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            if os.path.splitext(f)[1] in SKIP_EXT:
                continue
            p = os.path.join(root, f)
            out.append(os.path.relpath(p, os.path.dirname(FOLDER)))
    return sorted(out)


def main():
    files = folder_files()
    print(f'[1/4] {len(files)} files in {os.path.basename(FOLDER)}/')
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            z.write(os.path.join(os.path.dirname(FOLDER), rel), rel)
    print(f'[2/4] wrote {ZIP} ({os.path.getsize(ZIP):,} bytes)')

    with zipfile.ZipFile(ZIP) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f'CRC failure on {bad}')
        members = sorted(n for n in z.namelist() if not n.endswith('/'))
        print(f'[3/4] CRC check passed on {len(members)} members')

        missing = [f for f in files if f not in members]
        extra = [m for m in members if m not in files]
        if missing or extra:
            raise SystemExit(f'list mismatch: missing={missing} extra={extra}')

        mismatched = []
        for rel in files:
            in_zip = sha256_bytes(z.read(rel))
            on_disk = sha256_bytes(open(os.path.join(os.path.dirname(FOLDER), rel), 'rb').read())
            if in_zip != on_disk:
                mismatched.append(rel)
        if mismatched:
            raise SystemExit(f'hash mismatch: {mismatched}')

        cube = 'GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube'
        if cube not in members:
            raise SystemExit('the .cube is not inside the archive')
        cube_hash = sha256_bytes(z.read(cube))
        manifest = json.load(open(os.path.join(S.PROJ, 'SCENES', 'render_manifest.json')))
        if cube_hash != manifest['lut']['sha256']:
            raise SystemExit('cube hash inside the ZIP differs from the render manifest')

        print(f'[4/4] verified: {len(members)} files, all CRCs valid, all hashes match')
        print(f'      .cube inside the ZIP: {cube}')
        print(f'      sha256 {cube_hash}  ({len(z.read(cube)):,} bytes)')
        total = sum(i.file_size for i in z.infolist())
        print(f'      uncompressed total {total:,} bytes, '
              f'compressed {os.path.getsize(ZIP):,} bytes')


if __name__ == '__main__':
    main()
