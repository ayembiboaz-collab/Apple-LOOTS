"""
gdc_gallery.py -- build GALLERY/ (interactive HTML) and CONTACT_SHEET/ (JPEGs).

The gallery is a single self-contained index.html with inline CSS and JS (no
external requests, no CDN, no fonts to download) so that it works offline, on an
iPhone, and inside a sandboxed preview iframe.  It only references image files
that sit next to it in GALLERY/assets/.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdc_config as CFG

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DELIV = os.path.join(ROOT, "GOLDEN_DAYLIGHT_CINEMA")
PREV = os.path.join(DELIV, "PREVIEWS")
GAL = os.path.join(DELIV, "GALLERY")
ASSETS = os.path.join(GAL, "assets")
SHEET = os.path.join(DELIV, "CONTACT_SHEET")
LUT_PATH = os.path.join(DELIV, "LUT", "GOLDEN_DAYLIGHT_CINEMA.cube")

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(size, bold=False, mono=False):
    path = FONT_BOLD if bold else (FONT_MONO if mono else FONT_REG)
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# --------------------------------------------------------------------------
# asset derivatives
# --------------------------------------------------------------------------

def build_assets(long_edge=1280, thumb_edge=460, quality=86):
    os.makedirs(ASSETS, exist_ok=True)
    info = {}
    for sc in CFG.SCENES:
        num = f"{sc.number:02d}"
        for side in ("BEFORE", "AFTER"):
            src = os.path.join(PREV, f"{num}_{sc.key}_{side}.png")
            im = Image.open(src).convert("RGB")
            big = im.copy()
            big.thumbnail((long_edge, long_edge), Image.LANCZOS)
            big_path = os.path.join(ASSETS, f"{num}_{sc.key}_{side}.jpg")
            big.save(big_path, quality=quality, optimize=True, progressive=True)
            th = im.copy()
            th.thumbnail((thumb_edge, thumb_edge), Image.LANCZOS)
            th_path = os.path.join(ASSETS, f"{num}_{sc.key}_{side}_thumb.jpg")
            th.save(th_path, quality=82, optimize=True, progressive=True)
            info[f"{num}_{sc.key}_{side}"] = {
                "size": [big.width, big.height],
                "bytes": os.path.getsize(big_path),
                "thumb_bytes": os.path.getsize(th_path),
            }
    return info


# --------------------------------------------------------------------------
# contact sheets
# --------------------------------------------------------------------------

def contact_sheet(side: str, cols=4, tile_w=520, tile_h=342, gap=18, margin=40,
                  title=None, out="contact_sheet.jpg"):
    """Fixed-size tiles (letterboxed) so captions line up in every row."""
    tiles = []
    for sc in CFG.SCENES:
        num = f"{sc.number:02d}"
        src = os.path.join(PREV, f"{num}_{sc.key}_{side}.png")
        im = Image.open(src).convert("RGB")
        im.thumbnail((tile_w, tile_h), Image.LANCZOS)
        cell = Image.new("RGB", (tile_w, tile_h), (11, 11, 13))
        cell.paste(im, ((tile_w - im.width) // 2, (tile_h - im.height) // 2))
        tiles.append((sc, cell))
    cap_h = 48
    head_h = 92
    rows = (len(tiles) + cols - 1) // cols
    W = margin * 2 + cols * tile_w + (cols - 1) * gap
    H = head_h + rows * (tile_h + cap_h + gap) - gap + margin
    sheet = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    d.text((margin, 28), title or f"GOLDEN DAYLIGHT CINEMA — {side}",
           font=font(30, bold=True), fill=(238, 230, 214))
    d.text((margin, 66),
           f"{side}: " + ("simulated Apple Log 2 / Apple Wide Gamut through the verified "
                          "neutral Apple Log 2 -> Rec.709 transform" if side == "BEFORE"
                          else "the delivered GOLDEN_DAYLIGHT_CINEMA.cube, tetrahedral "
                               "interpolation, Rec.709 gamma 2.4"),
           font=font(15), fill=(150, 148, 142))
    for i, (sc, cell) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = margin + c * (tile_w + gap)
        y = head_h + r * (tile_h + cap_h + gap)
        sheet.paste(cell, (x, y))
        d.text((x, y + tile_h + 9), f"{sc.number:02d}  {sc.title}",
               font=font(17, bold=True), fill=(235, 228, 212))
        d.text((x, y + tile_h + 30), f"photo: {sc.photographer} · Unsplash License",
               font=font(13), fill=(140, 138, 133))
    path = os.path.join(SHEET, out)
    os.makedirs(SHEET, exist_ok=True)
    sheet.save(path, quality=90, optimize=True, progressive=True)
    return path


def comparison_sheet(cell_w=620, cell_h=408, gap=20, margin=36, quality=88):
    """One row per scene: BEFORE | AFTER, fixed cells so nothing drifts."""
    rows = []
    for sc in CFG.SCENES:
        num = f"{sc.number:02d}"
        pair = []
        for side in ("BEFORE", "AFTER"):
            im = Image.open(os.path.join(PREV, f"{num}_{sc.key}_{side}.png")).convert("RGB")
            im.thumbnail((cell_w, cell_h), Image.LANCZOS)
            cell = Image.new("RGB", (cell_w, cell_h), (11, 11, 13))
            cell.paste(im, ((cell_w - im.width) // 2, (cell_h - im.height) // 2))
            pair.append(cell)
        rows.append((sc, pair))
    title_h, label_h, head_h = 34, 24, 104
    row_h = title_h + label_h + cell_h
    W = margin * 2 + 2 * cell_w + gap
    H = head_h + len(rows) * (row_h + gap)
    sheet = Image.new("RGB", (W, H), (16, 16, 18))
    d = ImageDraw.Draw(sheet)
    d.text((margin, 28), "GOLDEN DAYLIGHT CINEMA — BEFORE / AFTER",
           font=font(30, bold=True), fill=(238, 230, 214))
    d.text((margin, 66), "left: verified neutral Apple Log 2 → Rec.709   ·   right: the "
                         "delivered 33³ .cube (tetrahedral interpolation)",
           font=font(15), fill=(150, 148, 142))
    for i, (sc, (b, a)) in enumerate(rows):
        y = head_h + i * (row_h + gap)
        d.text((margin, y + 4), f"{sc.number:02d}   {sc.title}   —   {sc.photographer}",
               font=font(19, bold=True), fill=(235, 228, 212))
        d.text((margin, y + title_h + 3), "BEFORE   ·   plain verified conversion",
               font=font(13), fill=(150, 148, 142))
        d.text((margin + cell_w + gap, y + title_h + 3), "AFTER   ·   this .cube",
               font=font(13), fill=(226, 184, 119))
        sheet.paste(b, (margin, y + title_h + label_h))
        sheet.paste(a, (margin + cell_w + gap, y + title_h + label_h))
    path = os.path.join(SHEET, "contact_sheet_before_after.jpg")
    os.makedirs(SHEET, exist_ok=True)
    sheet.save(path, quality=quality, optimize=True, progressive=True)
    return path


# --------------------------------------------------------------------------
# html
# --------------------------------------------------------------------------

CSS = """
:root{
  --ink:#f2ece0; --dim:#a9a49a; --bg:#0e0e10; --panel:#16161a; --line:#2a2a30;
  --gold:#e2b877; --gold-deep:#8a6a3a;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-text-size-adjust:100%;}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 96px}
header.hero{padding:56px 0 26px;border-bottom:1px solid var(--line);margin-bottom:34px}
h1{font-size:clamp(27px,5vw,46px);letter-spacing:.14em;font-weight:700;margin:0 0 10px;
  background:linear-gradient(180deg,#f6e7c8,#d8ae6e 65%,#a97f45);
  -webkit-background-clip:text;background-clip:text;color:transparent}
.sub{color:var(--dim);font-size:clamp(13px,1.6vw,16px);line-height:1.6;max-width:70ch}
.meta{display:flex;flex-wrap:wrap;gap:8px 10px;margin-top:18px}
.chip{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;
  color:#d9cfbc;background:#191a1f;border:1px solid var(--line);border-radius:999px;
  padding:5px 11px;letter-spacing:.02em}
h2{font-size:15px;letter-spacing:.16em;text-transform:uppercase;color:var(--gold);
  margin:44px 0 14px;font-weight:600}
p{color:#cfc9be;line-height:1.65;font-size:15px}
a{color:var(--gold)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px}
figure{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:14px;
  overflow:hidden}
.cmp{position:relative;width:100%;background:#000;touch-action:pan-y;
  cursor:ew-resize;user-select:none;-webkit-user-select:none}
.cmp img{display:block;width:100%;height:auto;pointer-events:none;
  -webkit-user-drag:none;user-select:none}
.cmp .after{position:absolute;inset:0;clip-path:inset(0 50% 0 0)}
.cmp .bar{position:absolute;top:0;bottom:0;left:50%;width:2px;background:var(--gold);
  box-shadow:0 0 8px rgba(226,184,119,.55);pointer-events:none}
.cmp .knob{position:absolute;top:50%;left:50%;width:42px;height:42px;margin:-21px 0 0 -21px;
  border-radius:50%;background:rgba(20,20,24,.78);border:1.5px solid var(--gold);
  color:var(--gold);display:flex;align-items:center;justify-content:center;
  font-size:13px;letter-spacing:1px;pointer-events:none}
.cmp .tag{position:absolute;top:10px;font-size:10.5px;letter-spacing:.14em;
  padding:4px 8px;border-radius:6px;background:rgba(10,10,12,.66);
  border:1px solid rgba(255,255,255,.09);color:#e8e2d6;pointer-events:none}
.cmp .tag.b{left:10px} .cmp .tag.a{right:10px}
figcaption{padding:13px 15px 15px;display:flex;justify-content:space-between;
  gap:12px;align-items:baseline}
figcaption b{font-size:14.5px;letter-spacing:.02em}
figcaption span{font-size:11.5px;color:var(--dim);text-align:right}
.expand{background:none;border:1px solid var(--line);color:var(--dim);border-radius:8px;
  padding:5px 9px;font-size:11px;cursor:pointer;letter-spacing:.06em}
.expand:hover{color:var(--gold);border-color:var(--gold-deep)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin-top:6px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);color:#cfc9be}
th{color:var(--dim);font-weight:600;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase}
td.mono{font-family:ui-monospace,Menlo,monospace;font-size:12px}
.lb{position:fixed;inset:0;background:rgba(6,6,8,.97);display:none;z-index:50;
  align-items:center;justify-content:center;flex-direction:column;gap:14px;padding:16px}
.lb.on{display:flex}
.lb .cmp{max-width:96vw;max-height:78vh}
.lb .cmp img{max-width:96vw;max-height:78vh;width:auto;object-fit:contain}
.lb .cap{color:#d8d2c6;font-size:13px;letter-spacing:.05em;text-align:center}
.lb .nav{display:flex;gap:10px}
.lb button{background:#1b1b20;border:1px solid var(--line);color:#ded7c9;border-radius:10px;
  padding:9px 16px;font-size:13px;cursor:pointer}
.lb button:hover{border-color:var(--gold-deep);color:var(--gold)}
footer{margin-top:56px;border-top:1px solid var(--line);padding-top:22px;
  color:#8d8981;font-size:12.5px;line-height:1.7}
code{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:#e0d6c2}
.note{border-left:2px solid var(--gold-deep);padding:2px 0 2px 14px;margin:16px 0;
  color:#b8b2a7;font-size:13.5px}
"""

JS = """
(function(){
  function initCmp(root){
    var after = root.querySelector('.after'), bar = root.querySelector('.bar'),
        knob = root.querySelector('.knob'), drag = false;
    function set(fx){
      var pct = Math.max(0, Math.min(100, fx * 100));
      after.style.clipPath = 'inset(0 ' + (100 - pct) + '% 0 0)';
      bar.style.left = pct + '%'; knob.style.left = pct + '%';
    }
    set(0.5);
    function fromEvent(e){
      var r = root.getBoundingClientRect();
      var x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      set(x / r.width);
    }
    function down(e){ drag = true; fromEvent(e); if(e.cancelable) e.preventDefault(); }
    function move(e){ if(!drag) return; fromEvent(e); if(e.cancelable) e.preventDefault(); }
    function up(){ drag = false; }
    root.addEventListener('mousedown', down);
    root.addEventListener('touchstart', down, {passive:false});
    window.addEventListener('mousemove', move);
    window.addEventListener('touchmove', move, {passive:false});
    window.addEventListener('mouseup', up);
    window.addEventListener('touchend', up);
    root._set = set;
  }
  var cmps = Array.prototype.slice.call(document.querySelectorAll('.cmp'));
  cmps.forEach(initCmp);

  // full screen viewer
  var lb = document.getElementById('lb'),
      lbRoot = lb ? lb.querySelector('.cmp') : null,
      lbImgA = lbRoot ? lbRoot.querySelector('.after img') : null,
      lbImgB = lbRoot ? lbRoot.querySelector('.cmp > img') : null,
      lbCap = lb ? lb.querySelector('.cap') : null,
      idx = 0, data = window.GDC_SCENES || [];

  function show(i){
    if(!data.length) return;
    idx = (i + data.length) % data.length;
    var d = data[idx];
    lbImgB.src = d.before; lbImgA.src = d.after;
    lbCap.textContent = d.title + ' — ' + d.photo + ' · drag to compare';
    lbRoot._set(0.5);
    lb.classList.add('on');
  }
  if(lb){
    document.querySelectorAll('[data-scene]').forEach(function(b){
      b.addEventListener('click', function(){ show(parseInt(b.getAttribute('data-scene'),10)); });
    });
    lb.querySelector('.close').addEventListener('click', function(){ lb.classList.remove('on'); });
    lb.querySelector('.prev').addEventListener('click', function(){ show(idx-1); });
    lb.querySelector('.next').addEventListener('click', function(){ show(idx+1); });
    document.addEventListener('keydown', function(e){
      if(!lb.classList.contains('on')) return;
      if(e.key === 'Escape') lb.classList.remove('on');
      if(e.key === 'ArrowLeft') show(idx-1);
      if(e.key === 'ArrowRight') show(idx+1);
    });
    lb.addEventListener('click', function(e){ if(e.target === lb) lb.classList.remove('on'); });
  }
})();
"""


def build_html(asset_info, lut_sha, lut_bytes):
    scenes_js = []
    cards = []
    for i, sc in enumerate(CFG.SCENES):
        num = f"{sc.number:02d}"
        b = f"assets/{num}_{sc.key}_BEFORE.jpg"
        a = f"assets/{num}_{sc.key}_AFTER.jpg"
        tb = f"assets/{num}_{sc.key}_BEFORE_thumb.jpg"
        ta = f"assets/{num}_{sc.key}_AFTER_thumb.jpg"
        scenes_js.append(
            '{"title":%s,"before":"%s","after":"%s","photo":%s}' % (
                json.dumps(sc.title), b, a, json.dumps(sc.photographer)))
        cards.append(f"""
    <figure>
      <div class="cmp" data-idx="{i}">
        <img src="{tb}" data-thumb="1" alt="{sc.title}, before">
        <div class="after"><img src="{ta}" alt="{sc.title}, after"></div>
        <div class="bar"></div><div class="knob">◀ ▶</div>
        <div class="tag b">BEFORE</div><div class="tag a">AFTER</div>
      </div>
      <figcaption>
        <b>{sc.number:02d} · {sc.title}</b>
        <span>{sc.photographer} · Unsplash<br>
        <button class="expand" data-scene="{i}">full screen</button></span>
      </figcaption>
    </figure>""")

    credits_rows = "\n".join(
        f"<tr><td>{sc.number:02d}</td><td>{sc.title}</td><td>{sc.photographer}</td>"
        f"<td class='mono'><a href='{sc.unsplash_url}'>{sc.unsplash_url}</a></td>"
        f"<td>Unsplash License</td></tr>" for sc in CFG.SCENES)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>GOLDEN DAYLIGHT CINEMA — 33³ LUT for Apple Log 2</title>
<meta name="description" content="Golden Daylight Cinema: a 33³ .cube LUT that turns Apple Log 2 / Apple Wide Gamut into warm, filmic Rec.709 SDR.">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>GOLDEN DAYLIGHT CINEMA</h1>
    <div class="sub">A warm, filmic Rec.709 SDR look for <b>Apple Log 2 / Apple Wide Gamut</b>
      footage — 33³ .cube, one LUT, pure gamma 2.4. Drag any image to compare the plain
      verified Apple&nbsp;Log&nbsp;2 → Rec.709 conversion against the graded result.</div>
    <div class="meta">
      <span class="chip">33 × 33 × 33</span>
      <span class="chip">Rec.709 · gamma 2.4</span>
      <span class="chip">Apple Log 2 → Apple Wide Gamut</span>
      <span class="chip">{lut_bytes//1024} KiB .cube</span>
      <span class="chip">sha256 {lut_sha[:16]}…</span>
    </div>
  </header>

  <h2>Eight scenes · before / after</h2>
  <div class="grid">{''.join(cards)}
  </div>

  <h2>The LUT</h2>
  <p><a href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube"><code>GOLDEN_DAYLIGHT_CINEMA.cube</code></a>
  — 33³, red-fastest, <code>DOMAIN_MIN 0 0 0</code> / <code>DOMAIN_MAX 1 1 1</code>,
  float written to 6 decimals, no NaN/Inf. It is fully self-contained: the file already
  contains the Apple Log 2 decode, the Apple Wide Gamut → Rec.709 matrix, the grade and the
  gamma 2.4 encode, so nothing else needs to be loaded.</p>
  <table>
    <tr><th>Input</th><td>Apple Log 2, Apple Wide Gamut, 0–1 code values (as recorded)</td></tr>
    <tr><th>Output</th><td>Rec.709 primaries, D65, SDR, pure gamma 2.4 code values</td></tr>
    <tr><th>Interpolation</th><td>tetrahedral (the fit also constrains trilinear)</td></tr>
    <tr><th>Black point</th><td>Apple Log 2 video black sits at code 0.1505; everything below it maps to 0</td></tr>
  </table>
  <div class="note">Blackmagic Camera (iOS) accepts 17- and 33-point .cube 3D LUTs:
  Settings → LUTs → LUTs Manager → Import LUT. Choose whether it is a display LUT or baked
  into the recording. DaVinci Resolve: drop it into the LUT folder and apply on a clip node.
  This LUT expects <b>Apple Log 2</b> (iPhone 17 Pro / 18 Pro and later); Apple Log footage
  from iPhone 15/16 Pro uses Rec.2020 primaries and is <b>not</b> the intended input.</div>

  <h2>Credits · photographs</h2>
  <table>
    <tr><th>#</th><th>Scene</th><th>Photographer</th><th>Source</th><th>Licence</th></tr>
    {credits_rows}
  </table>
  <p style="margin-top:14px;font-size:12.5px;color:#8d8981">All eight photographs are real,
  unmodified camera images from Unsplash, used under the Unsplash License (free for
  commercial and non-commercial use, no permission needed). No AI-generated imagery is used
  anywhere in this project. Full provenance, including each file's original URL, resolution
  and the modifications applied (resize only), is in <code>SOURCES.txt</code>.</p>

  <h2>Honest limitations</h2>
  <p>This is a stills-grade LUT, not a camera profile: it has no grain, halation, bloom,
  sharpening, noise reduction or depth awareness, and it cannot recover clipped highlights
  that the camera never recorded. The "after" images are produced by an independent
  implementation that reads this exact .cube file, so what you see is what the LUT does.
  The full measurements — bake error, monotonicity, clipping, skin hue, noise gain — are in
  <code>VALIDATION_REPORT.txt</code>.</p>

  <footer>
    GOLDEN DAYLIGHT CINEMA · built as a scene-referred float64 pipeline and baked to one
    33³ .cube · preview JPEGs are display-encoded copies of the Rec.709 gamma-2.4 renders
    (sRGB transfer applied for browser viewing; the .cube itself is untouched).
  </footer>
</div>

<div class="lb" id="lb">
  <div class="cmp">
    <img src="" alt="before">
    <div class="after"><img src="" alt="after"></div>
    <div class="bar"></div><div class="knob">◀ ▶</div>
    <div class="tag b">BEFORE</div><div class="tag a">AFTER</div>
  </div>
  <div class="cap"></div>
  <div class="nav">
    <button class="prev">←</button>
    <button class="close">close</button>
    <button class="next">→</button>
  </div>
</div>

<script>
window.GDC_SCENES = [{",".join(scenes_js)}];
{JS}
</script>
</body>
</html>
"""
    path = os.path.join(GAL, "index.html")
    with open(path, "w") as f:
        f.write(html)
    return path


def main():
    os.makedirs(GAL, exist_ok=True)
    os.makedirs(SHEET, exist_ok=True)
    lut_sha = hashlib.sha256(open(LUT_PATH, "rb").read()).hexdigest()
    lut_bytes = os.path.getsize(LUT_PATH)
    print("building gallery assets…")
    info = build_assets()
    print(f"  {len(info)} JPEGs, "
          f"{sum(v['bytes'] for v in info.values())/1e6:.2f} MB full + "
          f"{sum(v['thumb_bytes'] for v in info.values())/1e6:.2f} MB thumbs")
    p = build_html(info, lut_sha, lut_bytes)
    print("  wrote", os.path.relpath(p, ROOT))
    print("building contact sheets…")
    for side in ("BEFORE", "AFTER"):
        print("  wrote", os.path.relpath(
            contact_sheet(side, out=f"contact_sheet_{side.lower()}.jpg"), ROOT))
    print("  wrote", os.path.relpath(comparison_sheet(), ROOT))
    with open(os.path.join(ROOT, "validation", "gallery_assets.json"), "w") as f:
        json.dump({"lut_sha256": lut_sha, "assets": info}, f, indent=2)


if __name__ == "__main__":
    main()
