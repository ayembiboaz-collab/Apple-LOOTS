from pathlib import Path
import numpy as np
from PIL import Image
import hashlib
base=Path(__file__).resolve().parent.parent/'GOLDEN_DAYLIGHT_CINEMA'
p=base/'LUT/GOLDEN_DAYLIGHT_CINEMA.cube'
lines=p.read_text().splitlines(); assert 'LUT_3D_SIZE 33' in lines and 'DOMAIN_MIN 0.0 0.0 0.0' in lines and 'DOMAIN_MAX 1.0 1.0 1.0' in lines
rows=[]
for l in lines:
 s=l.split()
 if len(s)==3:
  try: rows.append([float(x) for x in s])
  except ValueError: pass
v=np.array(rows); assert v.shape==(33**3,3) and np.isfinite(v).all() and v.min()>=0 and v.max()<=1
print('LUT SHA256',hashlib.sha256(p.read_bytes()).hexdigest()); print('rows',len(v),'finite',np.isfinite(v).all(),'range',v.min(),v.max());print('lattice channel values equal 0, 1',np.sum(v==0),np.sum(v==1),'of',v.size)
for i in range(1,9):
 a=np.asarray(Image.open(base/f'PREVIEWS/{i:02}_BEFORE.png').convert('RGB'))/255
 b=np.asarray(Image.open(base/f'PREVIEWS/{i:02}_AFTER.png').convert('RGB'))/255
 assert a.shape==b.shape
 print(f'{i:02} {a.shape[1]}x{a.shape[0]} mean before {a.mean():.4f} after {b.mean():.4f}; after any-channel black {np.mean(np.min(b,axis=2)==0):.4%}, any-channel white {np.mean(np.max(b,axis=2)==1):.4%}')
