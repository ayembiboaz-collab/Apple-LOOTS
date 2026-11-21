"""Build downscaled web derivatives for GALLERY/img (fast on iPhone)."""
import os
import sys
import json
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
PREVIEWS = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'PREVIEWS')
IMG = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'GALLERY', 'img')
CONTACT = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA', 'CONTACT_SHEET', 'GOLDEN_DAYLIGHT_CINEMA_contact_sheet.png')
MAX_SIDE = 1600
os.makedirs(IMG, exist_ok=True)

manifest = json.load(open(os.path.join(PREVIEWS, 'manifest.json')))
for item in manifest:
    for kind in ('before', 'after'):
        src = os.path.join(PREVIEWS, item[kind])
        dst = os.path.join(IMG, item['scene'] + '_' + kind + '.jpg')
        im = Image.open(src).convert('RGB')
        w, h = im.size
        s = min(1.0, MAX_SIDE / max(w, h))
        if s < 1.0:
            im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
        im.save(dst, 'JPEG', quality=86, optimize=True, progressive=True)
        print(os.path.basename(dst), im.size, os.path.getsize(dst) // 1024, 'KB')
cs = Image.open(CONTACT).convert('RGB')
cs.save(os.path.join(IMG, 'contact_sheet.jpg'), 'JPEG', quality=88, optimize=True, progressive=True)
print('contact_sheet.jpg', cs.size, os.path.getsize(os.path.join(IMG, 'contact_sheet.jpg')) // 1024, 'KB')
