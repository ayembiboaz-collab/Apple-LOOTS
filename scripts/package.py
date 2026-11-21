from pathlib import Path
import hashlib, tempfile, zipfile
root=Path(__file__).resolve().parents[1]; folder=root/'GOLDEN_DAYLIGHT_CINEMA'; target=root/'GOLDEN_DAYLIGHT_CINEMA.zip'
files=sorted(p for p in folder.rglob('*') if p.is_file())
with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files: z.write(p,p.relative_to(root))
with zipfile.ZipFile(target) as z, tempfile.TemporaryDirectory() as d:
    assert z.testzip() is None
    assert 'GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube' in z.namelist()
    assert set(z.namelist())=={str(p.relative_to(root)) for p in files}
    z.extractall(d)
    def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    for p in files: assert h(p)==h(Path(d)/p.relative_to(root)),p
print('PASS: ZIP integrity, cube present, extracted SHA-256 matches all',len(files),'folder files;',target.stat().st_size,'bytes')
