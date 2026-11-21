#!/usr/bin/env python3
"""Reproducible synthetic-scene demo and 33^3 Apple Log 2 display LUT."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'GOLDEN_DAYLIGHT_CINEMA'
for d in ('LUT','PREVIEWS','CONTACT_SHEET','GALLERY'): (OUT/d).mkdir(parents=True,exist_ok=True)
N=33
R0=-0.05641088; RT=0.01; S=47.28711236; B=.00964052; G=.08550479; D=.69336945
PT=S*(RT-R0)**2

def enc(x):
    return np.where(x<RT,S*np.maximum(x-R0,0)**2,G*np.log2(np.maximum(x+B,1e-12))+D)
def dec(p):
    return np.where(p<PT,np.sqrt(np.maximum(p,0)/S)+R0,2**((p-D)/G)-B)
def rgbxyz(prim):
    cols=np.array([[x/y,1,(1-x-y)/y] for x,y in prim]).T
    w=np.array([.3127/.3290,1,(1-.3127-.3290)/.3290])
    return cols*np.linalg.solve(cols,w)
AW=rgbxyz([(.725,.301),(.221,.814),(.068,-.076)])
R709=rgbxyz([(.64,.33),(.30,.60),(.15,.06)])
M=np.linalg.solve(R709,AW)
MI=np.linalg.inv(M)
L=np.array([.2126,.7152,.0722])

def transform(p):
    rgb=dec(p)@M.T
    y=np.maximum(rgb@L,0)
    # Luminance-preserving soft shoulder and gentle film contrast.
    tone=(y*.95/(1+.20*y))
    tone=np.minimum(tone,1)
    rgb=rgb*(tone/np.maximum(y,1e-8))[...,None]
    # Compress out-of-gamut colours toward neutral, preserving hue better than hard channel clipping.
    lum=rgb@L
    diff=rgb-lum[...,None]
    low=np.min(diff,axis=-1); high=np.max(diff,axis=-1)
    fac=np.minimum(1,np.minimum(np.maximum(lum,0)/np.maximum(-low,1e-10),np.maximum(1-lum,0)/np.maximum(high,1e-10)))
    rgb=lum[...,None]+diff*fac[...,None]*.98
    # A restrained sunlit bias, reduced for already warm scenes and highlights.
    warmth=np.clip((rgb[...,0]-rgb[...,2])/(lum+.08),0,1)
    amt=.010*np.exp(-((lum-.30)/.27)**2)*(1-.8*warmth)
    rgb+=amt[...,None]*np.array([1.,.12,-.9])
    return np.clip(rgb,0,1)**(1/2.4)

axis=np.linspace(0,1,N)
b,g,r=np.meshgrid(axis,axis,axis,indexing='ij')
lattice=transform(np.stack([r,g,b],axis=-1)).reshape(-1,3)
cube=OUT/'LUT/GOLDEN_DAYLIGHT_CINEMA.cube'
with cube.open('w') as f:
    f.write('# Apple Log 2 / Apple Wide Gamut to Rec.709 gamma 2.4\nTITLE "GOLDEN DAYLIGHT CINEMA"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
    np.savetxt(f,lattice,fmt='%.8f')

def load_cube(path):
    lines=path.read_text().splitlines(); rows=[]
    for line in lines:
        s=line.strip().split()
        if len(s)==3:
            try: rows.append([float(x) for x in s])
            except ValueError: pass
    return np.array(rows).reshape(N,N,N,3)

def apply(c, p):
    t=np.clip(p,0,1)*(N-1); i=np.minimum(t.astype(int),N-2); f=t-i
    result=np.zeros_like(p)
    for z in (0,1):
        for y in (0,1):
            for x in (0,1):
                w=((f[...,0] if x else 1-f[...,0])*(f[...,1] if y else 1-f[...,1])*(f[...,2] if z else 1-f[...,2]))
                result+=c[i[...,2]+z,i[...,1]+y,i[...,0]+x]*w[...,None]
    return result

def srgb_inverse(x): return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def save(a,p): Image.fromarray(np.round(np.clip(a,0,1)*255).astype('uint8')).save(p,optimize=True)

c=load_cube(cube)
titles=['Harsh midday city','Sunlit portrait','Mediterranean street','Bright beach daylight','Greenery and mountains','Golden-hour landscape','Modern architecture','Travel with people']
thumbs=[]
for n,title in enumerate(titles,1):
    im=Image.open(ROOT/f'source/images/{n:02}.png').convert('RGB'); im.thumbnail((1280,1280),Image.Resampling.LANCZOS)
    a=np.asarray(im,dtype=np.float64)/255
    # SDR sRGB rendered image is treated as a limited scene estimate, not sensor data.
    linear=srgb_inverse(a)
    log=np.clip(enc(linear@MI.T),0,1)
    # Before is a neutral SDR reference of the simulated source, not the flat Log signal.
    save(np.clip(linear,0,1)**(1/2.4),OUT/f'PREVIEWS/{n:02}_BEFORE.png')
    after=apply(c,log)
    save(after,OUT/f'PREVIEWS/{n:02}_AFTER.png')
    small=Image.fromarray(np.uint8(np.round(after*255))); small.thumbnail((400,260)); thumbs.append((small,title))
    print(n,title,'size',im.size,'before mean',round(float(a.mean()),4),'after mean',round(float(after.mean()),4))
sheet=Image.new('RGB',(1600,650),'#11110f'); draw=ImageDraw.Draw(sheet)
for i,(im,title) in enumerate(thumbs):
    x=(i%4)*400; y=(i//4)*325; sheet.paste(im,(x,y)); draw.text((x+12,y+270),f'{i+1:02}  {title.upper()}',fill='#eee9dc')
sheet.save(OUT/'CONTACT_SHEET/CONTACT_SHEET.png',optimize=True)
print('AW to 709 matrix',M)
print('cube rows',len(lattice),'finite',np.isfinite(c).all(),'min max',c.min(),c.max())
# Numerical checks against external anchor values and published primaries.
assert abs(float(enc(np.array(.18)))-.48827)<.00002
assert abs(float(dec(np.array(.48827)))-.18)<.0001
assert np.max(abs(M@np.ones(3)-1))<1e-12
ramp=apply(c,np.repeat(np.linspace(.15,.85,1000)[:,None],3,axis=1)); print('negative ramp steps',np.min(np.diff(ramp.mean(axis=1))))
print('neutral ramp min step',np.min(np.diff(ramp.mean(axis=1))), 'channel spread max',np.max(np.ptp(ramp,axis=1)))
for ev in [-2,-1,0,1,2]:
    p=enc(np.full((1,3),.18*2**ev)); v=apply(c,p)[0]; print('grey EV',ev,'->',np.round(v,5))
