from pathlib import Path
import zipfile, hashlib
root=Path(__file__).resolve().parent.parent
folder=root/'GOLDEN_DAYLIGHT_CINEMA'; dest=root/'GOLDEN_DAYLIGHT_CINEMA.zip'
files=sorted(p for p in folder.rglob('*') if p.is_file())
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in files:z.write(p,p.relative_to(root))
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 assert set(z.namelist())=={str(p.relative_to(root)) for p in files}
 for p in files:assert hashlib.sha256(z.read(str(p.relative_to(root)))).digest()==hashlib.sha256(p.read_bytes()).digest()
 assert 'GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube' in z.namelist()
 print('ZIP verified:',len(files),'files, cube included, all extracted bytes match, size',dest.stat().st_size)
