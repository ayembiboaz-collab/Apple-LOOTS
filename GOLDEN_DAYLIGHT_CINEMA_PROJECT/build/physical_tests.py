"""Test the shipped file with OCIO and nonnegative Rec.709-derived synthetic colours.
These are synthetic colour samples, NOT photographs or camera footage.
"""
from pathlib import Path
import contextlib, io, json, hashlib
import numpy as np
import colour
import PyOpenColorIO as ocio
from pipeline import AWG, REC, encode, grade
with contextlib.redirect_stdout(io.StringIO()):
    from validate import sample, delta
P=Path(__file__).resolve().parent.parent
cube=P/'GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube'
config=ocio.Config.CreateRaw()
builtin=config.getProcessor(ocio.BuiltinTransform(style='APPLE_LOG-APPLEWG_to_ACES2065-1')).getDefaultCPUProcessor()
builtin_result=np.array(builtin.applyRGB([.5,.4,.3]))
from pipeline import decode
w65=colour.xy_to_XYZ([.3127,.3290]); w60=colour.xy_to_XYZ([.32168,.33767])
reference=colour.RGB_COLOURSPACES['ACES2065-1'].matrix_XYZ_to_RGB @ colour.adaptation.matrix_chromatic_adaptation_VonKries(w65,w60,transform='Bradford') @ AWG @ decode([.5,.4,.3])
assert np.max(np.abs(builtin_result-reference)) < 1e-6
def ocio_apply(x, interp):
    proc=config.getProcessor(ocio.FileTransform(src=str(cube),interpolation=interp)).getDefaultCPUProcessor()
    a=np.asarray(x,dtype=np.float32).copy();proc.applyRGB(a);return a.astype(float)
def to_log(rgb709):
    awg=np.asarray(rgb709) @ (np.linalg.solve(AWG,REC)).T
    return encode(awg)
def summary(a):
    return {'mean':float(np.mean(a)), 'p99':float(np.percentile(a,99)), 'max':float(np.max(a))}
rng=np.random.default_rng(147)
# Rec.709 nonnegative scene primaries at distributed exposures from -4 to +4 stops.
scene=rng.uniform(0,1,(50000,3)) * (2.**rng.uniform(-4,2,(50000,1)))
x=to_log(scene); ok=np.all((x>=0)&(x<=1),axis=1);x=x[ok]
anal=grade(x);tri=ocio_apply(x,ocio.INTERP_LINEAR);tet=ocio_apply(x,ocio.INTERP_TETRAHEDRAL)
independent={}
for name,got,t in [('trilinear',tri,False),('tetrahedral',tet,True)]:
    independent[name]={'deltaE00':summary(delta(anal,got)),'ocio_vs_python_max_abs':float(np.max(np.abs(got-sample(x,t))))}
# BabelColor Average xyY values, under its specified illuminant, adapted to D65.
chart=colour.characterisation.CCS_COLOURCHECKERS['BabelColor Average']
source_white=colour.xy_to_XYZ(chart.illuminant); d65=colour.xy_to_XYZ([.3127,.3290]);
adapt=colour.adaptation.matrix_chromatic_adaptation_VonKries(source_white,d65,transform='Bradford')
def angle(rgb):
    y=rgb @ np.array([.2126,.7152,.0722]); cb=(rgb[...,2]-y)/1.8556; cr=(rgb[...,0]-y)/1.5748
    return np.degrees(np.arctan2(cr,cb))
def hue_diff(a,b):return float((a-b+180)%360-180)
patches={}
for name in ['dark skin','light skin','blue sky','foliage']:
    xyz=colour.xyY_to_XYZ(chart.data[name]); rgb=np.linalg.solve(REC,adapt@xyz)
    rows=[]
    for light,mult in [('neutral',[1,1,1]),('warm',[1.12,1,.88]),('cool',[.90,1,1.12])]:
        for stop in [-2,-1,0,1,2]:
            src=np.maximum(rgb*np.array(mult)*2.**stop,0)
            inp=to_log(src); result=ocio_apply(inp[None],ocio.INTERP_TETRAHEDRAL)[0]
            # Neutral tonal baseline only: scalar luminance compression, gamma 2.4.
            Y=src@np.array([.2126,.7152,.0722]); ref=np.clip(src/(1+Y),0,1)**(1/2.4)
            rows.append({'lighting':light,'stops':stop,'reference_rgb':ref.tolist(),'lut_rgb':result.tolist(),'reference_vectorscope_degrees':float(angle(ref)),'lut_vectorscope_degrees':float(angle(result)),'delta_degrees':hue_diff(angle(result),angle(ref))})
    patches[name]=rows
# Synthetic input-independent AWG linear noise at neutral shadow levels. Compare
# average per-channel standard deviations in scene-linear and display-linear.
noise=[]
for level in [.001,.005,.018,.18]:
    pert=rng.normal(0,level*.01,(10000,3)); input_rgb=level+pert
    output=ocio_apply(encode(input_rgb),ocio.INTERP_TETRAHEDRAL)**2.4
    noise.append({'scene_linear':level,'input_sigma':float(pert.std()),'output_linear_sigma':np.std(output,axis=0).tolist(),'linear_sigma_ratio':(np.std(output,axis=0)/np.std(pert,axis=0)).tolist()})
result={'ocio_builtin_apple_log_2_to_aces': builtin_result.tolist(), 'analytic_vs_ocio_builtin_max_abs':float(np.max(np.abs(builtin_result-reference))), 'sha256':hashlib.sha256(cube.read_bytes()).hexdigest(),'samples':len(x),'sample_distribution':'Random Rec.709 linear components in [0,1], scaled by 2^uniform(-4,2), encoded to Apple Log 2 / Apple Wide Gamut. Not a camera gamut or image distribution.','independent_OCIO_results':independent,'patch_method':'BabelColor Average xyY, Bradford D50-like source illuminant to D65, Rec.709; nominal warm/cool channel multipliers are synthetic and not calibrated illuminants. Vectorscope angles use atan2(Cr,Cb) from gamma-2.4 signal, not a claimed universal skin-line standard. Neutral reference uses scalar luminance shoulder and clips out-of-range RGB.','patches':patches,'shadow_noise':noise}
(P/'validation/physical-tests.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'independent_OCIO_results':independent,'shadow_noise':noise,'skin_neutral_zero_stop':{k:[q for q in patches[k] if q['lighting']=='neutral' and q['stops']==0][0] for k in ['dark skin','light skin']},'sha256':result['sha256']},indent=2))
