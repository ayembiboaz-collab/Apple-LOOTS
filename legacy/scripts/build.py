#!/usr/bin/env python3
"""Build reproducible deliverable from committed scene sources; previews sample the saved cube."""
from pathlib import Path
import hashlib, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from color import *
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'GOLDEN_DAYLIGHT_CINEMA'
for d in ('LUT','PREVIEWS','GALLERY','CONTACT_SHEET'): (OUT/d).mkdir(parents=True,exist_ok=True)
cube=OUT/'LUT/GOLDEN_DAYLIGHT_CINEMA.cube'; write_cube(cube); lut=read_cube(cube)
scenes=[('01_city','Harsh midday city'),('02_portrait','Midday portrait'),('03_street','Mediterranean street'),('04_beach','Bright beach daylight'),('05_landscape','Greenery & mountains'),('06_golden_hour','Golden-hour landscape'),('07_architecture','Modern architecture'),('08_travel','Outdoor travel')]

def png(arr,path): Image.fromarray(np.uint8(np.round(np.clip(arr,0,1)*255)),'RGB').save(path,optimize=True)
def sampled(p):
    # Chunk rows to keep memory bounded.
    return np.concatenate([apply_cube(chunk,lut) for chunk in np.array_split(p,16,axis=0)],axis=0)
def metric(a): return [float(np.mean(a)),float(np.min(a)),float(np.max(a))]
results=[]
for key,title in scenes:
    original=Image.open(ROOT/'source_images'/f'{key}.jpg').convert('RGB').resize((1600,894),Image.Resampling.LANCZOS)
    s=np.asarray(original,dtype=np.float64)/255
    # A pseudo-scene from display image: sRGB linear light assumed as relative scene light.
    scene=srgb_decode(s); awg=scene @ TO_AWG.T; log=np.clip(encode(awg),0,1)
    # BEFORE = normalized neutral Rec.709 / equivalent sRGB display, NOT raw log.
    # AFTER = the saved cube's gamma 2.4 output converted to sRGB for ordinary web displays.
    a=sampled(log); display=srgb_encode(np.clip(a,0,1)**2.4)
    png(s,OUT/'PREVIEWS'/f'{key}_BEFORE.png'); png(display,OUT/'PREVIEWS'/f'{key}_AFTER.png')
    results.append({'scene':title,'before_mean':round(float(s.mean()),5),'after_mean':round(float(display.mean()),5),'after_black_channel_pct':round(float(np.mean(a<=.001)*100),3),'after_white_channel_pct':round(float(np.mean(a>=.999)*100),3),'mean_rgb_shift':[round(float(x),5) for x in (display-s).mean(axis=(0,1))]})
    print(title,results[-1],flush=True)
# Contact sheet uses the actual exported PNGs.
sheet=Image.new('RGB',(1920,4*330),(17,19,20)); draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
for i,(key,title) in enumerate(scenes):
    row=i//2; pair=i%2
    for j,mode in enumerate(('BEFORE','AFTER')):
        x=(pair*2+j)*480; y=row*330
        im=Image.open(OUT/'PREVIEWS'/f'{key}_{mode}.png'); im.thumbnail((466,260)); sheet.paste(im,(x+7,y+5))
        draw.text((x+8,y+274),f'{i+1:02}  {title}  /  {mode}',font=font,fill=(230,224,211))
sheet.save(OUT/'CONTACT_SHEET/CONTACT_SHEET.png',optimize=True)
# Validation and machine-readable measurements from actual cube.
rng=np.random.default_rng(22); points=rng.uniform(.15,.8,(50000,3)); d=np.abs(apply_cube(points,lut)-grade(points))
ns=np.linspace(0,1,10001); neutral=apply_cube(np.stack([ns]*3,-1),lut); dif=np.diff(neutral,axis=0)
# Exposure series on representative synthetic colors, not measured camera data.
colors=np.array([[.18,.18,.18],[.40,.24,.16],[.08,.25,.48],[.09,.26,.08]])
exp=[]
for ev in [-2,-1,0,1,2]:
    inputs=encode((colors*2**ev) @ TO_AWG.T); val=apply_cube(inputs,lut)
    exp.append({'ev':ev,'output_gamma24':np.round(val,5).tolist()})
assert np.isfinite(lut).all() and np.min(lut)>=0 and np.max(lut)<=1
assert abs(float(encode(np.array(.18)))-.4882724585)<1e-8
assert abs(float(decode(np.array(.4882724585)))-.18)<1e-8
assert np.max(np.abs(AWG_TO_709 @ np.ones(3)-1))<1e-12
# Independent published OCIO D65-to-D60 Bradford AWG to ACES AP0 matrix.
reference=np.array([[.694961049318096,.241405268785364,.06363368189654],[.0473627464149325,1.00429592505428,-.0516586714692158],[-.021989789359883,-.0289891049714743,1.05097889433136]])
def white(x,y): return np.array([x/y,1,(1-x-y)/y])
def prim(p,w):
    q=np.array([[x/y,1,(1-x-y)/y] for x,y in p]).T
    return q @ np.diag(np.linalg.solve(q,white(*w)))
ap0=prim([(.7347,.2653),(0,1),(.0001,-.077)],(.32168,.33767))
bradford=np.array([[.8951,.2664,-.1614],[-.7502,1.7135,.0367],[.0389,-.0685,1.0296]])
cat=np.linalg.inv(bradford)@np.diag((bradford@white(.32168,.33767))/(bradford@white(.3127,.329)))@bradford
mat_err=np.max(np.abs(np.linalg.solve(ap0,cat@AWG)-reference))
assert mat_err<1e-12
report={'cube_sha256':hashlib.sha256(cube.read_bytes()).hexdigest(),'matrix_awg_to_709':AWG_TO_709.tolist(),'cube_min':float(lut.min()),'cube_max':float(lut.max()),'ocio_ap0_matrix_max_error':float(mat_err),'neutral_decreasing_channel_steps':int(np.sum(dif<0)),'neutral_min_step':float(dif.min()),'neutral_max_step':float(dif.max()),'neutral_max_channel_spread':float(np.max(np.ptp(neutral,axis=-1))),'analytic_vs_cube_random_mean_abs':float(d.mean()),'analytic_vs_cube_random_max_abs':float(d.max()),'percent_cube_entries_zero':float(np.mean(lut<=0)*100),'percent_cube_entries_one':float(np.mean(lut>=1)*100),'scenes':results,'exposure_samples':exp}
(ROOT/'scripts/measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print('MEASUREMENTS', json.dumps(report,indent=2),flush=True)
