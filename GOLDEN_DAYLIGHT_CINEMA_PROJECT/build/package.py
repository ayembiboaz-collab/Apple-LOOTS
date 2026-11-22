"""Package and verify the *current* deliverable directory, no implicit extras."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, tempfile, shutil
root=Path(__file__).resolve().parent.parent
folder=root/'GOLDEN_DAYLIGHT_CINEMA'
archive=root/'GOLDEN_DAYLIGHT_CINEMA.zip'
(folder/'VALIDATION').mkdir(exist_ok=True)
for name in ('lut-validation.json','physical-tests.json'):
    shutil.copyfile(root/'validation'/name, folder/'VALIDATION'/name)
files=sorted(p for p in folder.rglob('*') if p.is_file())
with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        info=__import__('zipfile').ZipInfo(p.relative_to(root).as_posix(),(2020,1,1,0,0,0))
        info.compress_type=ZIP_DEFLATED; info.external_attr=0o644<<16
        z.writestr(info,p.read_bytes(),compresslevel=9)
with ZipFile(archive) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted(p.relative_to(root).as_posix() for p in files)
    for p in files:
        assert hashlib.sha256(z.read(p.relative_to(root).as_posix())).digest() == hashlib.sha256(p.read_bytes()).digest()
    assert 'GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube' in z.namelist()
    with tempfile.TemporaryDirectory() as t:
        z.extractall(t)
        for p in files:
            extracted=Path(t)/p.relative_to(root)
            assert hashlib.sha256(extracted.read_bytes()).digest() == hashlib.sha256(p.read_bytes()).digest()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'zip_sha256':sha(archive),'files':{p.relative_to(root).as_posix():sha(p) for p in files},'all_extracted_file_hashes_match':True}
(root/'validation'/'package-hashes.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
