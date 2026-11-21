"""Reconstruct all AFTER PNGs from source and the actual delivered cube; compare bytes of pixels."""
from pathlib import Path
import sys
import numpy as np
from PIL import Image
from color import *
R=Path(__file__).resolve().parents[1]; out=R/'GOLDEN_DAYLIGHT_CINEMA'; table=read_cube(out/'LUT/GOLDEN_DAYLIGHT_CINEMA.cube')
for source in sorted((R/'source_images').glob('*.jpg')):
    s=np.asarray(Image.open(source).convert('RGB').resize((1600,894),Image.Resampling.LANCZOS),dtype=np.float64)/255
    p=np.clip(encode(srgb_decode(s)@TO_AWG.T),0,1)
    a=np.concatenate([apply_cube(chunk,table) for chunk in np.array_split(p,16,axis=0)],axis=0)
    expected=np.uint8(np.round(np.clip(srgb_encode(np.clip(a,0,1)**2.4),0,1)*255))
    actual=np.asarray(Image.open(out/'PREVIEWS'/f'{source.stem}_AFTER.png').convert('RGB'))
    diff=np.abs(expected.astype(int)-actual.astype(int)); print(source.stem,'max absolute difference (8-bit):',diff.max()); assert diff.max()==0
print('PASS: all eight AFTER images exactly reproduce from the delivered cube.')
