"""Reparse the candidate cube and measure it; not a substitute for visual tests."""
from pathlib import Path
import hashlib, json
import numpy as np
import colour
from pipeline import grade, decode, AWG, encode
P=Path(__file__).resolve().parent
cube=P.parent/'GOLDEN_DAYLIGHT_CINEMA'/'LUT'/'GOLDEN_DAYLIGHT_CINEMA.cube'
lines=cube.read_text().splitlines()
assert 'LUT_3D_SIZE 33' in lines and 'DOMAIN_MIN 0 0 0' in lines and 'DOMAIN_MAX 1 1 1' in lines
v=np.loadtxt(lines[4:]); assert v.shape==(33**3,3) and np.isfinite(v).all() and v.min()>=0 and v.max()<=1
v=v.reshape(33,33,33,3) # b,g,r

def sample(x, tetra=False):
    q=np.clip(np.asarray(x),0,1)*32
    i=np.minimum(np.floor(q).astype(int),31); f=q-i
    def get(d):
        z=i+d
        return v[z[...,2],z[...,1],z[...,0]]
    if tetra:
        order=np.argsort(-f,axis=-1)
        sorted_f=np.take_along_axis(f,order,axis=-1)
        e=np.eye(3,dtype=int)[order]
        c0=get(np.zeros_like(i)); c1=get(e[...,0,:]); c2=get(e[...,0,:]+e[...,1,:]); c3=get(np.ones_like(i))
        return c0+(c1-c0)*sorted_f[...,0,None]+(c2-c1)*sorted_f[...,1,None]+(c3-c2)*sorted_f[...,2,None]
    out=np.zeros_like(q)
    for r in (0,1):
        for g in (0,1):
            for b in (0,1):
                d=np.array([r,g,b]); w=np.prod(np.where(d,f,1-f),axis=-1)
                out += get(d)*w[...,None]
    return out

def delta(a,b):
    # Encoded gamma 2.4 -> linear Rec.709 -> XYZ -> CIELAB D65 -> CIEDE2000.
    cs=colour.RGB_COLOURSPACES['ITU-R BT.709']
    return colour.delta_E(colour.XYZ_to_Lab(colour.RGB_to_XYZ(a**2.4,cs)),colour.XYZ_to_Lab(colour.RGB_to_XYZ(b**2.4,cs)),method='CIE 2000')

# Apple Wide Gamut -> ACES AP0 Bradford against independent OCIO test vector.
white65=colour.xy_to_XYZ([.3127,.3290]); white60=colour.xy_to_XYZ([.32168,.33767])
ap0=colour.RGB_COLOURSPACES['ACES2065-1'].matrix_XYZ_to_RGB
adapt=colour.adaptation.matrix_chromatic_adaptation_VonKries(white65,white60,transform='Bradford')
ref=ap0@adapt@AWG@decode(np.array([.5,.4,.3])); expected=np.array([.160302015,.091223177,.026405713])
assert np.max(np.abs(ref-expected)) < 5e-6, (ref,expected)
assert np.max(np.abs(decode(np.array([.5,.4,.3]))-np.array([.198913991,.083076466024,.0315782763])))<1e-6
rng=np.random.default_rng(1717); p=rng.uniform(0,1,(50000,3)); truth=grade(p)
errors={}
for name,tet in [('trilinear',False),('tetrahedral',True)]:
    d=delta(truth,sample(p,tet));errors[name]={'mean_deltaE00':float(np.mean(d)),'max_deltaE00':float(np.max(d)),'p99_deltaE00':float(np.percentile(d,99))}
ramps={}; t=np.linspace(0,1,4097)
for name,c in {'grey':[1,1,1],'red':[1,0,0],'green':[0,1,0],'blue':[0,0,1],'yellow':[1,1,0],'cyan':[0,1,1],'magenta':[1,0,1]}.items():
    y=sample(t[:,None]*np.array(c)); lum=y**2.4@np.array([.2126,.7152,.0722]); d=np.diff(lum)
    ramps[name]={'luminance_reversals':int((d < -1e-8).sum()),'min_first_difference':float(d.min()),'max_abs_second_difference':float(np.abs(np.diff(d)).max()),'unique_8bit_codes_per_channel':[int(len(np.unique(np.rint(y[:,j]*255)))) for j in range(3)],'unique_10bit_codes_per_channel':[int(len(np.unique(np.rint(y[:,j]*1023)))) for j in range(3)]}
neutral=sample(np.repeat(np.linspace(0,1,17)[:,None],3,axis=1))
# A neutral analytic anchor checks the exact output exponent, independent of cube interpolation.
mid=np.full((1,3),encode(.18)); observed=grade(mid)[0]
expected_gamma=(.18/(1+.18))**(1/2.4)
assert np.max(np.abs(observed-expected_gamma)) < 1e-6
ladder=[]
for stop in range(-4,5):
    linear=.18*2.0**stop; code=float(encode(linear)); out=sample(np.full((1,3),code))[0]
    ladder.append({'stop':stop,'input_linear':linear,'input_log':code,'output_rgb':out.tolist()})
# Independent Gaussian noise in each log channel. Gain is encoded-output std / log-input std,
# not a sensor SNR or a physical iPhone noise measurement.
noise=[]
for linear in [.001,.005,.018,.18]:
    code=float(encode(linear)); noise_in=rng.normal(0,.001,(10000,3)); out=sample(code+noise_in)
    noise.append({'linear_level':linear,'log_level':code,'input_sigma_log':.001,'output_sigma_709':out.std(axis=0).tolist(),'gain':(out.std(axis=0)/.001).tolist()})
result={'lut_sha256':hashlib.sha256(cube.read_bytes()).hexdigest(),'cube_entries':v.size//3,'min':float(v.min()),'max':float(v.max()),'ocio_ap0_reference':ref.tolist(),'ocio_ap0_max_abs_error':float(np.max(np.abs(ref-expected))),'interpolation_random_full_domain_50000':errors,'ramps':ramps,'neutral_17_code_steps_rgb':neutral.tolist(),'gamma_2_4_analytic_midgrey':{'observed':observed.tolist(),'expected':float(expected_gamma)},'exposure_ladder':ladder,'simulated_log_code_noise':noise,'limitations':'Random full cube is not an image distribution. Ramp reversals are luminance only. Quantised code counts do not prove absence of banding. No imagery, skin, scene exposure, lighting, clipping, visual or device tests performed. Noise test is a synthetic code-value perturbation, not sensor noise.'}
(P.parent/'validation'/'lut-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
