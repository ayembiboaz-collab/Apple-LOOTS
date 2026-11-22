"""Experimental analytic Apple Log 2 -> Rec.709 2.4 look. Float64, no spatial operations.
Not approved for camera use. See RESEARCH.md and BUILD.md.
"""
from pathlib import Path
import numpy as np

R0, RT, C, BETA, GAMMA, DELTA = -0.05641088, .01, 47.28711236, .00964052, .08550479, .69336945
PT = C * (RT-R0)**2

def decode(p):
    p = np.asarray(p, dtype=np.float64)
    return np.where(p >= PT, np.exp2((p-DELTA)/GAMMA)-BETA, np.sqrt(np.maximum(p, 0)/C)+R0)

def encode(r):
    r = np.asarray(r, dtype=np.float64)
    return np.where(r < R0, 0, np.where(r < RT, C*(r-R0)**2, GAMMA*np.log2(np.maximum(r+BETA, 1e-20))+DELTA))

def rgb_to_xyz(prim, white=(.3127,.3290)):
    x,y = np.array(prim, dtype=np.float64).T
    m = np.stack((x/y, np.ones(3), (1-x-y)/y))
    wx,wy = white
    w = np.array([wx/wy,1,(1-wx-wy)/wy])
    return m @ np.diag(np.linalg.solve(m,w))

AWG = rgb_to_xyz([(0.725,0.301),(0.221,0.814),(0.068,-0.076)])
REC = rgb_to_xyz([(.64,.33),(.30,.60),(.15,.06)])
AWG_TO_709 = np.linalg.solve(REC, AWG) # both D65: no chromatic adaptation required
M1 = np.array([[.4122214708,.5363325363,.0514459929],[.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]])
M2 = np.array([[.2104542553,.7936177850,-.0040720468],[1.9779984951,-2.4285922050,.4505937099],[.0259040371,.7827717662,-.8086757660]])
IM1, IM2 = np.linalg.inv(M1), np.linalg.inv(M2)

def lab(rgb):
    return np.cbrt(rgb @ M1.T) @ M2.T

def rgb(lab_):
    return ((lab_ @ IM2.T)**3) @ IM1.T

def gaussian_hue(h, center, width):
    d = np.arctan2(np.sin(h-center), np.cos(h-center))
    return np.exp(-.5*(d/width)**2)

def grade(log_rgb):
    """Candidate: analytic bake, no claims of validated professional suitability."""
    linear = decode(log_rgb) @ AWG_TO_709.T
    # Smoothly compress negative Rec.709 components toward scene luminance before
    # OKLab. This stabilises its cube roots for very wide-gamut/negative inputs.
    # Y below zero is not displayable and maps to black. This is not a claim
    # that every mathematical Apple Wide Gamut triple is physically plausible.
    Y = np.maximum(linear @ np.array([.2126,.7152,.0722]), 0)
    diff = linear - Y[...,None]
    with np.errstate(divide='ignore', invalid='ignore'):
        limits = np.where(diff < 0, Y[...,None] / np.maximum(-diff, 1e-20), np.inf)
    boundary = np.min(limits, axis=-1)
    knee = .8 * boundary
    span = np.maximum(.2 * boundary, 1e-20)
    with np.errstate(invalid='ignore'):
        scale = np.where(knee >= 1, 1, knee + span * (-np.expm1(-np.maximum(1-knee,0)/span)))
    linear = Y[...,None] + np.where(np.isfinite(scale), scale, 1)[...,None] * diff
    ok = lab(linear)
    l, a, b = np.moveaxis(ok, -1, 0)
    # Nonnegative scalar intensity; normalised soft shoulder, never raises linear luminance.
    intensity = np.maximum(l, 0)**3
    target = intensity/(1+intensity)
    target = np.minimum(target, .999999)
    L = np.cbrt(target)
    chroma = np.hypot(a,b)
    hue = np.arctan2(b,a)
    # Smooth relative-density shaping; low chroma neutrals remain neutral.
    sat = 1.0 + .07*np.exp(-((L-.58)/.24)**2) - .08*np.exp(-((L-.95)/.18)**2)
    shadow = np.clip(L/.42,0,1)
    sat *= .35 + .65*shadow*shadow*(3-2*shadow)  # thin colour and chroma noise near black
    sat *= 1-.60*np.clip((L-.72)/.24,0,1)**2*(3-2*np.clip((L-.72)/.24,0,1))  # highlight thinning
    sat *= 1-.12*gaussian_hue(hue, 2.15, .35) # foliage
    sat *= 1-.06*gaussian_hue(hue, .85, .28) # conservative skin/stone
    sat *= 1+.035*gaussian_hue(hue, -1.8, .40) # blue sky
    # Warm dense midtones, with a soft taper on naturally very warm colours.
    warm = .025*np.exp(-((L-.68)/.24)**2) * (1-.75*gaussian_hue(hue,.8,.4))
    a2 = (a + chroma*warm*.30) * sat
    b2 = (b + chroma*warm) * sat
    c = np.hypot(a2,b2)
    ua = np.divide(a2,c,out=np.zeros_like(c),where=c>1e-15)
    ub = np.divide(b2,c,out=np.zeros_like(c),where=c>1e-15)
    # Find the Rec.709 boundary along a fixed OKLab hue ray via bisection.
    lo = np.zeros_like(L); hi = np.full_like(L, 2.)
    for _ in range(20):
        mid=(lo+hi)*.5
        trial=rgb(np.stack((L,ua*mid,ub*mid),axis=-1))
        inside=np.all((trial>=0)&(trial<=1),axis=-1)
        lo=np.where(inside,mid,lo); hi=np.where(inside,hi,mid)
    # Soft knee at 75% of boundary; continuous first derivative.
    bound=lo; knee=bound*.75; span=np.maximum(bound-knee,1e-15)
    mapped=np.where(c<=knee,c,knee+span*(-np.expm1(-np.maximum(c-knee,0)/span)))
    out=rgb(np.stack((L,ua*mapped,ub*mapped),axis=-1))
    # Only guard numerical roundoff; bisection keeps chroma in gamut.
    return np.power(np.clip(out,0,1),1/2.4)

def bake(path, size=33):
    axis=np.linspace(0,1,size)
    # Cube rows: R fastest, then G, then B.
    b,g,r=np.meshgrid(axis,axis,axis,indexing='ij')
    points=np.stack((r,g,b),axis=-1).reshape(-1,3)
    values=grade(points)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w') as f:
        f.write('TITLE "Golden Daylight Cinema"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        np.savetxt(f,values,fmt='%.9f')

if __name__=='__main__':
    bake(Path(__file__).resolve().parents[1]/'GOLDEN_DAYLIGHT_CINEMA'/'LUT'/'GOLDEN_DAYLIGHT_CINEMA.cube')
