"""Golden Daylight Cinema color pipeline. RGB arrays, full-range normalized values."""
import numpy as np
R0, RT, C, BETA, GAMMA, DELTA = -0.05641088, .01, 47.28711236, .00964052, .08550479, .69336945
PT = C*(RT-R0)**2

def encode(x):
    return np.where(x < R0, 0, np.where(x < RT, C*(x-R0)**2, GAMMA*np.log2(np.maximum(x+BETA,1e-12))+DELTA))

def decode(p):
    return np.where(p < 0, R0, np.where(p < PT, np.sqrt(np.maximum(p,0)/C)+R0, np.exp2((p-DELTA)/GAMMA)-BETA))

def rgb_xyz(primaries):
    xyz=np.array([[x/y, 1, (1-x-y)/y] for x,y in primaries]).T
    white=np.array([.3127/.3290,1,(1-.3127-.3290)/.3290])
    return xyz @ np.diag(np.linalg.solve(xyz,white))
AWG=rgb_xyz([(.725,.301),(.221,.814),(.068,-.076)])
REC=rgb_xyz([(.64,.33),(.30,.60),(.15,.06)])
AWG_TO_709=np.linalg.solve(REC,AWG)
TO_AWG=np.linalg.inv(AWG_TO_709)
LUMA=np.array([.2126,.7152,.0722])

def srgb_decode(x):
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb_encode(x):
    x=np.maximum(x,0)
    return np.where(x<=.0031308,12.92*x,1.055*x**(1/2.4)-.055)

def grade(p):
    # Transform scene-linear Apple Wide Gamut to Rec.709, then luminance-preserving
    # gamut compression of negative components. This is not an Apple rendering transform.
    rgb=decode(p) @ AWG_TO_709.T
    y=rgb @ LUMA
    y=np.maximum(y,0)
    mn=np.min(rgb,axis=-1)
    fac=np.where(mn<0, y/np.maximum(y-mn,1e-12), 1)
    rgb=y[...,None]+(rgb-y[...,None])*fac[...,None]
    # Restrained global contrast and smooth asymptotic highlight shoulder.
    yc=np.maximum(y,1e-12)**1.06
    yt=np.where(yc<=.55,yc,.55+.45*(1-np.exp(-np.maximum(yc-.55,0)/.45)))
    rgb=rgb*(yt/np.maximum(y,1e-12))[...,None]
    # Gentle midtone warmth, reduced for already-warm colours and skin-like hues.
    r,g,b=np.moveaxis(rgb,-1,0)
    already=np.clip((r-b)/(np.maximum(r+g+b,.001)) * 3,0,1)
    window=np.clip(4*yt*(1-yt),0,1)*(1-.8*already)
    rgb=rgb*np.stack([1+.035*window,1+.005*window,1-.035*window],axis=-1)
    # Smooth saturation control: modestly rein in greens and cyan.
    y2=rgb @ LUMA
    r,g,b=np.moveaxis(rgb,-1,0)
    green=np.clip((g-np.maximum(r,b))/np.maximum(y2,.02)*2,0,1)
    cyan=np.clip((np.minimum(g,b)-r)/np.maximum(y2,.02)*1.2,0,1)
    sat=1-.10*green-.055*cyan
    rgb=y2[...,None]+(rgb-y2[...,None])*sat[...,None]
    # Compress toward neutral before hard output clamp, preserving luma where feasible.
    mn=np.min(rgb,axis=-1); mx=np.max(rgb,axis=-1)
    f1=np.where(mn<0,y2/np.maximum(y2-mn,1e-12),1)
    f2=np.where(mx>1,(1-y2)/np.maximum(mx-y2,1e-12),1)
    f=np.clip(np.minimum(f1,f2),0,1)
    rgb=y2[...,None]+(rgb-y2[...,None])*f[...,None]
    return np.clip(rgb,0,1)**(1/2.4)

def write_cube(path):
    # .cube red index changes fastest, then green then blue.
    v=np.linspace(0,1,33); b,g,r=np.meshgrid(v,v,v,indexing='ij')
    a=grade(np.stack([r,g,b],-1)).reshape(-1,3)
    with open(path,'w') as f:
        f.write('TITLE "GOLDEN DAYLIGHT CINEMA - Apple Log 2 to Rec.709 gamma 2.4"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
        np.savetxt(f,a,fmt='%.8f')

def read_cube(path):
    rows=[]; size=None
    for line in open(path):
        x=line.strip().split()
        if not x or x[0].startswith('#'): continue
        if x[0]=='LUT_3D_SIZE': size=int(x[1])
        elif x[0] in ('TITLE','DOMAIN_MIN','DOMAIN_MAX'): continue
        else:
            if len(x)!=3: raise ValueError('invalid cube line')
            rows.append([float(v) for v in x])
    if size!=33 or len(rows)!=33**3: raise ValueError('invalid cube dimensions')
    return np.array(rows).reshape((size,size,size,3))

def apply_cube(p,table):
    # Explicit trilinear interpolation; table axes are B, G, R.
    p=np.clip(p,0,1)*32; lo=np.floor(p).astype(np.int32); hi=np.minimum(lo+1,32); frac=p-lo
    out=np.zeros_like(p,dtype=np.float64)
    for rb in (0,1):
      for gb in (0,1):
       for bb in (0,1):
        rr=hi[...,0] if rb else lo[...,0]; gg=hi[...,1] if gb else lo[...,1]; bbidx=hi[...,2] if bb else lo[...,2]
        w=(frac[...,0] if rb else 1-frac[...,0])*(frac[...,1] if gb else 1-frac[...,1])*(frac[...,2] if bb else 1-frac[...,2])
        out += table[bbidx,gg,rr]*w[...,None]
    return out
