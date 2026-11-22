"""Generate the gallery (dark premium) HTML page for the deliverable.

Reads the render previews and writes GALLERY/index.html with:
  - cover hero
  - per-scene BEFORE/AFTER sliders + fullscreen
  - contact sheet strip
  - validation summary
  - credits
  - .cube download link
"""

import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent
PROJECT = BUILD.parent
GALLERY = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'GALLERY'
PREVIEWS = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'PREVIEWS'
REPORT = PROJECT / 'GOLDEN_DAYLIGHT_CINEMA' / 'VALIDATION_REPORT.txt'

SCENES = [
    ('01_midday_city', 'Midday City',
     'Harsh midday city — strong reflections, midtone-saturation squeeze, sky protection.',
     'Pexels · Pixabay',
     'Blue and Gray High Rise Building, Burj Khalifa · Free / CC0'),
    ('02_midday_portrait', 'Midday Portrait',
     'Direct-sunlight portrait — skin protection, warm kicker light.',
     'Pexels · Chuot Anhls',
     'Portrait of a woman in sunlight · Free'),
    ('03_mediterranean_street', 'Mediterranean Street',
     'Warm Tuscan stone, cool shade — stone-hue warmth and cool shadows.',
     'Pexels · Fran Zaina',
     'Charming narrow street in Positano, Italy · Free'),
    ('04_bright_beach', 'Bright Beach Daylight',
     'Overexposed glare and sunlight — highlights roll softly, sand stays warm.',
     'Pexels · Nico Hartnauer',
     'Beautiful sandy beach in Greece · Free'),
    ('05_natural_landscape', 'Natural Landscape',
     'Lake and tree line — greens stay natural, sky keeps its blue.',
     'Wikimedia Commons · Tobias Alt (Tobi 87)',
     'Moraine Lake, Banff NP · GFDL 1.2+ / CC BY-SA 3.0'),
    ('06_golden_hour_landscape', 'Golden Hour Landscape',
     'Warm low light — the golden palette is preserved with a richer, deeper tone.',
     'Pexels · Johannes Plenio',
     'Lake surrounded by mountains during golden hour · Free'),
    ('07_modern_architecture', 'Modern Architecture',
     'Cool neutral architecture, slight warm stone-hue shift.',
     'Pexels · Hilal Bülbül',
     'Modern architectural building exterior · Free'),
    ('08_travel_street', 'Outdoor Travel Scene',
     'People, buildings and street life — golden-hour energy with natural sky.',
     'Unsplash · David Vives',
     'People walking down a street next to tall buildings · Unsplash License'),
]

def main():
    GALLERY.mkdir(parents=True, exist_ok=True)
    gallery_html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Golden Daylight Cinema — Apple Log 2 → Rec.709</title>
<style>
:root {
  --bg: #0d0c0a;
  --panel: #16130f;
  --panel-2: #1e1a14;
  --text: #ece5d8;
  --muted: #a89c88;
  --accent: #f0a64f;
  --accent-2: #d98a2b;
  --line: #2b261d;
}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: 'Georgia', 'Times New Roman', serif; line-height: 1.55; }}
body {{ background:
  radial-gradient(1200px 700px at 80% -10%, #2a1f12 0%, transparent 60%),
  radial-gradient(1000px 600px at -10% 30%, #251a10 0%, transparent 55%),
  var(--bg); }}
a {{ color: var(--accent); }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 0 24px 80px; }}
.hero {{ position: relative; text-align: center; padding: 80px 24px 60px; overflow: hidden; }}
.hero img.mask {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover;
  opacity: 0.22; filter: blur(22px) saturate(1.3); transform: scale(1.1); z-index: 0; }}
.hero > div {{ position: relative; z-index: 1; }}
.eyebrow {{ letter-spacing: 0.32em; text-transform: uppercase; font-size: 11px;
  color: var(--accent); font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; }}
h1 {{ font-size: clamp(44px, 7.5vw, 90px); line-height: 1.02; margin: 18px 0 6px; font-weight: 700;
  letter-spacing: -0.015em; }}
h1 .i {{ font-style: italic; color: var(--accent); }}
.sub {{ font-size: 17px; color: var(--muted); max-width: 640px; margin: 0 auto; }}
.cta {{ display: inline-block; margin-top: 30px; padding: 15px 34px; border-radius: 999px;
  background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: #1b1206;
  font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; font-size: 15px;
  letter-spacing: 0.04em; text-decoration: none; box-shadow: 0 8px 40px rgba(240,166,79,0.35);
  transition: transform 0.18s ease, box-shadow 0.18s ease; }}
.cta:hover {{ transform: translateY(-2px); box-shadow: 0 12px 48px rgba(240,166,79,0.5); }}
.badge {{ display: inline-block; margin-top: 14px; font-size: 12px; color: var(--muted);
  font-family: 'Helvetica Neue', Arial, sans-serif; }}
/* scene sliders */
section.scenes {{ margin-top: 46px; }}
.section-title {{ font-size: 13px; letter-spacing: 0.28em; text-transform: uppercase;
  color: var(--accent); font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700;
  text-align: center; margin: 0 0 34px; }}
.scene {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px;
  margin-bottom: 28px; overflow: hidden; box-shadow: 0 18px 50px rgba(0,0,0,0.4); }}
.scene-head {{ display: flex; align-items: center; justify-content: space-between;
  padding: 18px 24px 14px; gap: 16px; flex-wrap: wrap; }}
.scene-head h2 {{ font-size: 24px; margin: 0; font-weight: 600; }}
.scene-head .tag {{ font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; }}
.scene-head .tools {{ display: flex; gap: 10px; }}
.btn {{ padding: 9px 18px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--panel-2); color: var(--text); cursor: pointer; font-size: 12px;
  letter-spacing: 0.1em; text-transform: uppercase; font-family: 'Helvetica Neue', Arial, sans-serif;
  transition: all 0.15s; }}
.btn:hover {{ border-color: var(--accent); color: var(--accent); }}
.slider-wrap {{ position: relative; overflow: hidden; border-radius: 0; height: min(66vw, 560px); }}
.slider-wrap img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.slider-wrap .after {{ clip-path: inset(0 0 0 var(--reveal, 50%)); }}
.slider-wrap .divider {{ position: absolute; top: 0; bottom: 0; left: var(--reveal, 50%);
  width: 3px; background: linear-gradient(to bottom, var(--accent), var(--accent-2));
  transform: translateX(-50%); z-index: 5; pointer-events: none; box-shadow: 0 0 18px rgba(240,166,79,0.7); }}
.slider-wrap .handle {{ position: absolute; top: 50%; left: var(--reveal, 50%); width: 44px; height: 44px;
  border-radius: 50%; background: white; border: 3px solid var(--accent); transform: translate(-50%, -50%);
  display: flex; align-items: center; justify-content: center; z-index: 6; pointer-events: none;
  color: var(--accent-2); font-size: 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }}
.slider-wrap input[type=range] {{ position: absolute; left: 0; right: 0; bottom: 0; width: 100%;
  height: 44px; margin: 0; opacity: 0; z-index: 7; cursor: ew-resize; }}
.labels {{ display: flex; justify-content: space-between; position: absolute; bottom: 8px; left: 10px; right: 10px;
  z-index: 5; pointer-events: none; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10px;
  letter-spacing: 0.24em; text-transform: uppercase; color: rgba(255,255,255,0.85); text-shadow: 0 1px 4px rgba(0,0,0,0.8); }}
.scene-cap {{ padding: 16px 24px 22px; color: var(--muted); font-size: 15px; }}
.scene-cap b {{ color: var(--text); font-weight: 600; }}
.badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.pill {{ font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted);
  border: 1px solid var(--line); border-radius: 999px; padding: 4px 10px; }}
.pill.accent {{ color: var(--accent); border-color: rgba(240,166,79,0.4); }}
.contact-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }}
.contact-grid figure {{ margin: 0; border-radius: 12px; overflow: hidden; position: relative;
  border: 1px solid var(--line); background: var(--panel-2); }}
.contact-grid img {{ width: 100%; height: 150px; object-fit: cover; display: block; }}
.contact-grid figcaption {{ padding: 8px 10px; font-size: 11px; letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; }}
.contact-grid figcaption b {{ color: var(--text); display: block; letter-spacing: 0.02em; font-size: 13px;
  text-transform: none; margin-top: 3px; font-family: Georgia, serif; font-weight: 600; }}
.credits {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 26px; }}
.credits h3 {{ font-size: 20px; margin: 0 0 16px; }}
.credits table {{ width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Helvetica Neue', Arial, sans-serif; }}
.credits th, .credits td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
.credits th {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.12em; font-size: 10px; font-weight: 700; width: 26%; }}
.credits td a {{ color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--line); }}
.credits tr:last-child td {{ border-bottom: none; }}
.footer {{ margin-top: 54px; text-align: center; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; }}
.footer a {{ color: var(--accent); }}
.footer .small {{ font-size: 11px; opacity: 0.75; margin-top: 10px; }}
.fullscreen-btn, .fs-banner {{ cursor: pointer; }}
figure.fs-banner {{ position: fixed; z-index: 100; inset: 0; background: rgba(13,12,10,0.92);
  display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4vmin;
  opacity: 0; pointer-events: none; transition: opacity 0.2s; }}
figure.fs-banner.open {{ opacity: 1; pointer-events: auto; }}
.fs-banner img {{ max-width: 96vw; max-height: 78vh; object-fit: contain; border-radius: 10px;
  box-shadow: 0 30px 80px rgba(0,0,0,0.8); }}
.fs-banner .row {{ display: flex; gap: 18px; margin-top: 18px; align-items: center; }}
.fs-banner .row button {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--line);
  padding: 12px 26px; border-radius: 999px; cursor: pointer; font-size: 13px; letter-spacing: 0.08em; }}
.fs-banner .row button:hover {{ border-color: var(--accent); color: var(--accent); }}
@media (max-width: 640px) {{ .slider-wrap {{ height: 60vw; }} h1 {{ font-size: 40px; }} }}
</style>
</head>
<body>
<header class="hero">
  <img class="mask" src="../PREVIEWS/04_bright_beach_AFTER_GOLDEN_DAYLIGHT.png" alt="">
  <div>
    <div class="eyebrow">Apple Log 2 &#8594; Rec.709 &middot; 33&times;33&times;33 3D .cube LUT</div>
    <h1>Golden <span class="i">Daylight</span> Cinema</h1>
    <p class="sub">A warm, rich, atmospheric Mediterranean travel &amp; lifestyle grade for iPhone 17 Pro
    footage (Blackmagic Camera for iOS, Apple Log 2). Golden that stays natural — blues, greens and
    skin stay honest, deep shadows stay clean.</p>
    <a class="cta" href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube" download>Download .cube LUT</a>
    <div class="badge">Simulated-log previews from real photographs &middot; see SOURCES.txt &middot; VALIDATION_REPORT.txt</div>
  </div>
</header>

<main class="wrap">
  <section class="scenes" id="scenes">
    <div class="section-title">Before &middot; After</div>
INJECT_SCENES
  </section>

  <section class="scenes">
    <div class="section-title">Contact sheet</div>
    <div class="contact-grid">
INJECT_CONTACT
    </div>
  </section>

  <section id="validation" style="margin-top: 46px;">
    <div class="section-title">Validation summary</div>
    <div class="credits">
      <table>
        <thead><tr><th>Check</th><th>Result</th></tr></thead>
        <tbody>
          <tr><td>33&times;33&times;33 .cube integrity (35937 rows, 0..1, finite)</td><td>PASS</td></tr>
          <tr><td>Interpolation error vs analytic pipeline (image domain)</td><td>PASS &middot; trilinear max &Delta;E 0.05 &middot; tetrahedral max &Delta;E 0.06 &middot; image-mean &Delta;E 0.005</td></tr>
          <tr><td>Neutral axis (warmth, no orange cast)</td><td>PASS</td></tr>
          <tr><td>Monotonicity &amp; smoothness (diagonal)</td><td>PASS &middot; max negative step &asymp; 0.004 (1 8-bit level)</td></tr>
          <tr><td>Quantisation (8-bit &amp; 10-bit)</td><td>PASS &middot; 8-bit max &Delta;E 0.003 &middot; 10-bit max &Delta;E 0.0008</td></tr>
          <tr><td>Clipping percent (AFTER vs BEFORE, aggregate)</td><td>PASS &middot; extreme 2.26% &rarr; 0.18% of pixels</td></tr>
          <tr><td>Shadow-noise gain</td><td>PASS &middot; mean 1.04&times;</td></tr>
          <tr><td>&plusmn;4 stops exposure ladder</td><td>PASS &middot; highlights roll softly, no clipping</td></tr>
        </tbody>
      </table>
      <p style="color: var(--muted); font-size: 13px; margin-bottom: 0; padding-top: 14px; border-top: 1px solid var(--line);">
        Full detail, all charts and checksums: <b>VALIDATION_REPORT.txt</b>.  Simulated-log content:
        inputs were derived from real photographs; no Apple Log 2 recording was captured.
        Behaviour on production footage is not guaranteed.</p>
    </div>
  </section>

  <section id="credits" style="margin-top: 46px;">
    <div class="section-title">Credits &amp; licenses</div>
    <div class="credits">
      <h3>Photographs &amp; their licenses</h3>
      <table>
        <thead><tr><th>Scene</th><th>Photographer &amp; source</th><th>License</th></tr></thead>
        <tbody>
INJECT_CREDITS
        </tbody>
      </table>
      <p style="color: var(--muted); font-size: 13px; margin-bottom: 0;">
        Images were resized and lightly compressed for previews; no AI-generated imagery was used.
        Source images and derived previews remain the work of their respective photographers.
        See <b>SOURCES.txt</b> for the full provenance record.</p>
    </div>
  </section>

  <footer class="footer">
    <div>Golden Daylight Cinema &middot; Apple Log 2 &rarr; Rec.709 gamma 2.4 &middot; .cube 33&times;33&times;33</div>
    <div style="margin-top: 10px;"><a href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube" download>Download .cube LUT</a></div>
    <div class="small">This LUT is a review/demonstration asset, not a certified product.
      &middot; No physical iPhone / Blackmagic Camera validation was performed &middot; all previews are simulated-log-derived.</div>
  </footer>
</main>

<figure class="fs-banner" id="fsBanner">
  <button id="fsClose" aria-label="Close fullscreen">&times;</button>
  <img id="fsImg" src="" alt="">
  <div class="row">
    <button id="fsPrev">&larr; Prev</button>
    <button id="fsNext">Next &rarr;</button>
    <button onclick="closeFs()">Close (ESC)</button>
  </div>
</figure>

<script>
(function () {
  const sliders = document.querySelectorAll('.scene');
  sliders.forEach((scene) => {
    const range = scene.querySelector('input[type=range]');
    const after = scene.querySelector('.after');
    const wrap = scene.querySelector('.slider-wrap');
    const divider = scene.querySelector('.divider');
    const handle = scene.querySelector('.handle');
    const setReveal = (v) => {
      const pct = v;
      wrap.style.setProperty('--reveal', pct + '%');
      after.style.clipPath = 'inset(0 0 0 ' + pct + '%)';
      divider.style.left = pct + '%';
      handle.style.left = pct + '%';
    };
    range.addEventListener('input', () => setReveal(parseFloat(range.value)));
    setReveal(parseFloat(range.value));
  });
  const fsBanner = document.getElementById('fsBanner');
  const fsImg = document.getElementById('fsImg');
  const assetMeta = [];
  document.querySelectorAll('.scene-head .fs-btn').forEach((btn) => {
    assetMeta.push({ before: btn.getAttribute('data-before'), after: btn.getAttribute('data-after'), name: btn.getAttribute('data-name') });
    btn.addEventListener('click', () => openFs(assetMeta.length - 1));
  });
  let fsIndex = 0;
  function openFs(i) {
    fsIndex = i;
    const meta = assetMeta[i];
    fsImg.src = meta.after;
    document.title = meta.name;
    fsBanner.classList.add('open');
    fsBanner.setAttribute('aria-hidden', 'false');
  }
  function closeFs() {
    fsBanner.classList.remove('open');
    fsBanner.setAttribute('aria-hidden', 'true');
    document.title = 'Golden Daylight Cinema — Apple Log 2 → Rec.709';
  }
  window.closeFs = closeFs;
  document.getElementById('fsClose').addEventListener('click', closeFs);
  document.getElementById('fsPrev').addEventListener('click', () => openFs((fsIndex - 1 + assetMeta.length) % assetMeta.length));
  document.getElementById('fsNext').addEventListener('click', () => openFs((fsIndex + 1) % assetMeta.length));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFs();
    if (e.key === 'ArrowRight') openFs((fsIndex + 1) % assetMeta.length);
    if (e.key === 'ArrowLeft') openFs((fsIndex - 1 + assetMeta.length) % assetMeta.length);
  });
  fsBanner.addEventListener('click', (e) => { if (e.target === fsBanner) closeFs(); });
})();
</script>
</body>
</html>'''
    return gallery_html


def render_scenes():
    blocks = []
    for idx, (stem, title, desc, creds, what) in enumerate(SCENES):
        before_png = f'../PREVIEWS/{stem}_BEFORE_NEUTRAL.png'
        after_png = f'../PREVIEWS/{stem}_AFTER_GOLDEN_DAYLIGHT.png'
        blocks.append(f'''    <article class="scene">
      <div class="scene-head">
        <div>
          <div class="tag">Scene {idx+1:02d}</div>
          <h2>{title}</h2>
        </div>
        <div class="tools">
          <button class="btn fs-btn" data-name="{title}" data-before="{before_png}" data-after="{after_png}">Fullscreen</button>
        </div>
      </div>
      <div class="slider-wrap">
        <img class="before" src="{before_png}" alt="{title} — neutral reference">
        <img class="after" src="{after_png}" alt="{title} — Golden Daylight grade">
        <div class="divider"></div>
        <div class="handle">⇄</div>
        <div class="labels"><span>Neutral reference</span><span>Golden Daylight</span></div>
        <input type="range" min="0" max="100" value="50" step="0.5" aria-label="Reveal Golden Daylight grade">
      </div>
      <div class="scene-cap">
        <b>{title}.</b> {desc}
        <div class="badge-row">
          <span class="pill accent">BEFORE = fair neutral reference</span>
          <span class="pill">AFTER = shipped 33³ .cube</span>
          <span class="pill">Simulated-log (real photo)</span>
        </div>
        <div class="badge-row"><span class="pill">{creds}</span></div>
      </div>
    </article>''')
    return '\n'.join(blocks)


def render_contact():
    blocks = []
    for idx, (stem, title, desc, creds, what) in enumerate(SCENES):
        after_png = f'../PREVIEWS/{stem}_AFTER_GOLDEN_DAYLIGHT.png'
        blocks.append(f'''      <figure>
        <img src="{after_png}" alt="{title}">
        <figcaption>{title}<b>BEFORE &middot; AFTER</b></figcaption>
      </figure>''')
    return '\n'.join(blocks)


def render_credits():
    blocks = []
    for idx, (stem, title, desc, creds, what) in enumerate(SCENES):
        blocks.append(f'          <tr><td>{title}</td><td><a href="#">{creds}</a></td><td>{what}</td></tr>')
    return '\n'.join(blocks)


def main():
    scenes_html = render_scenes()
    contact_html = render_contact()
    credits_html = render_credits()
    gallery_html = (Path(BUILD / 'build_gallery.py').read_text().split("    return gallery_html")[0])
    # Simpler: rebuild by calling module-level template
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Golden Daylight Cinema — Apple Log 2 → Rec.709</title>
<style>
:root { --bg: #0d0c0a; --panel: #16130f; --panel-2: #1e1a14; --text: #ece5d8; --muted: #a89c88; --accent: #f0a64f; --accent-2: #d98a2b; --line: #2b261d; }
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text); font-family: 'Georgia', 'Times New Roman', serif; line-height: 1.55; }}
body {{ background: radial-gradient(1200px 700px at 80% -10%, #2a1f12 0%, transparent 60%), radial-gradient(1000px 600px at -10% 30%, #251a10 0%, transparent 55%), var(--bg); }}
a {{ color: var(--accent); }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 0 24px 80px; }}
.hero {{ position: relative; text-align: center; padding: 80px 24px 60px; overflow: hidden; }}
.hero img.mask {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.22; filter: blur(22px) saturate(1.3); transform: scale(1.1); z-index: 0; }}
.hero > div {{ position: relative; z-index: 1; }}
.eyebrow {{ letter-spacing: 0.32em; text-transform: uppercase; font-size: 11px; color: var(--accent); font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; }}
h1 {{ font-size: clamp(44px, 7.5vw, 90px); line-height: 1.02; margin: 18px 0 6px; font-weight: 700; letter-spacing: -0.015em; }}
h1 .i {{ font-style: italic; color: var(--accent); }}
.sub {{ font-size: 17px; color: var(--muted); max-width: 640px; margin: 0 auto; }}
.cta {{ display: inline-block; margin-top: 30px; padding: 15px 34px; border-radius: 999px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); color: #1b1206; font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; font-size: 15px; letter-spacing: 0.04em; text-decoration: none; box-shadow: 0 8px 40px rgba(240,166,79,0.35); transition: transform 0.18s ease, box-shadow 0.18s ease; }}
.cta:hover {{ transform: translateY(-2px); box-shadow: 0 12px 48px rgba(240,166,79,0.5); }}
.badge {{ display: inline-block; margin-top: 14px; font-size: 12px; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; }}
section.scenes {{ margin-top: 46px; }}
.section-title {{ font-size: 13px; letter-spacing: 0.28em; text-transform: uppercase; color: var(--accent); font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 700; text-align: center; margin: 0 0 34px; }}
.scene {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; margin-bottom: 28px; overflow: hidden; box-shadow: 0 18px 50px rgba(0,0,0,0.4); }}
.scene-head {{ display: flex; align-items: center; justify-content: space-between; padding: 18px 24px 14px; gap: 16px; flex-wrap: wrap; }}
.scene-head h2 {{ font-size: 24px; margin: 0; font-weight: 600; }}
.scene-head .tag {{ font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; }}
.scene-head .tools {{ display: flex; gap: 10px; }}
.btn {{ padding: 9px 18px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel-2); color: var(--text); cursor: pointer; font-size: 12px; letter-spacing: 0.1em; text-transform: uppercase; font-family: 'Helvetica Neue', Arial, sans-serif; transition: all 0.15s; }}
.btn:hover {{ border-color: var(--accent); color: var(--accent); }}
.slider-wrap {{ position: relative; overflow: hidden; height: min(66vw, 560px); }}
.slider-wrap img {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
.slider-wrap .after {{ clip-path: inset(0 0 0 50%); }}
.slider-wrap .divider {{ position: absolute; top: 0; bottom: 0; left: 50%; width: 3px; background: linear-gradient(to bottom, var(--accent), var(--accent-2)); transform: translateX(-50%); z-index: 5; pointer-events: none; box-shadow: 0 0 18px rgba(240,166,79,0.7); }}
.slider-wrap .handle {{ position: absolute; top: 50%; left: 50%; width: 44px; height: 44px; border-radius: 50%; background: white; border: 3px solid var(--accent); transform: translate(-50%, -50%); display: flex; align-items: center; justify-content: center; z-index: 6; pointer-events: none; color: var(--accent-2); font-size: 18px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }}
.slider-wrap input[type=range] {{ position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: 44px; margin: 0; opacity: 0; z-index: 7; cursor: ew-resize; }}
.labels {{ display: flex; justify-content: space-between; position: absolute; bottom: 8px; left: 10px; right: 10px; z-index: 5; pointer-events: none; font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; color: rgba(255,255,255,0.85); text-shadow: 0 1px 4px rgba(0,0,0,0.8); }}
.scene-cap {{ padding: 16px 24px 22px; color: var(--muted); font-size: 15px; }}
.scene-cap b {{ color: var(--text); font-weight: 600; }}
.badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.pill {{ font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 4px 10px; }}
.pill.accent {{ color: var(--accent); border-color: rgba(240,166,79,0.4); }}
.contact-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 14px; }}
.contact-grid figure {{ margin: 0; border-radius: 12px; overflow: hidden; position: relative; border: 1px solid var(--line); background: var(--panel-2); }}
.contact-grid img {{ width: 100%; height: 150px; object-fit: cover; display: block; }}
.contact-grid figcaption {{ padding: 8px 10px; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; }}
.contact-grid figcaption b {{ color: var(--text); display: block; letter-spacing: 0.02em; font-size: 13px; text-transform: none; margin-top: 3px; font-family: Georgia, serif; font-weight: 600; }}
.credits {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 26px; }}
.credits h3 {{ font-size: 20px; margin: 0 0 16px; }}
.credits table {{ width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Helvetica Neue', Arial, sans-serif; }}
.credits th, .credits td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
.credits th {{ color: var(--muted); text-transform: uppercase; letter-spacing: 0.12em; font-size: 10px; font-weight: 700; width: 26%; }}
.credits td a {{ color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--line); }}
.credits tr:last-child td {{ border-bottom: none; }}
.footer {{ margin-top: 54px; text-align: center; color: var(--muted); font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 12px; }}
.footer a {{ color: var(--accent); }}
.footer .small {{ font-size: 11px; opacity: 0.75; margin-top: 10px; }}
.fs-banner {{ position: fixed; z-index: 100; inset: 0; background: rgba(13,12,10,0.92); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4vmin; opacity: 0; pointer-events: none; transition: opacity 0.2s; }}
.fs-banner.open {{ opacity: 1; pointer-events: auto; }}
.fs-banner img {{ max-width: 96vw; max-height: 76vh; object-fit: contain; border-radius: 10px; box-shadow: 0 30px 80px rgba(0,0,0,0.8); }}
.fs-banner .row {{ display: flex; gap: 14px; margin-top: 18px; align-items: center; }}
.fs-banner .row button {{ background: var(--panel-2); color: var(--text); border: 1px solid var(--line); padding: 12px 26px; border-radius: 999px; cursor: pointer; font-size: 13px; letter-spacing: 0.08em; }}
.fs-banner .row button:hover {{ border-color: var(--accent); color: var(--accent); }}
.fs-banner #fsClose {{ position: absolute; top: 18px; right: 24px; background: transparent; border: 1px solid var(--line); color: var(--text); font-size: 22px; width: 44px; height: 44px; border-radius: 50%; cursor: pointer; }}
@media (max-width: 640px) {{ .slider-wrap {{ height: 60vw; }} h1 {{ font-size: 40px; }} }}
</style>
</head>
<body>
<header class="hero">
  <img class="mask" src="../PREVIEWS/04_bright_beach_AFTER_GOLDEN_DAYLIGHT.png" alt="">
  <div>
    <div class="eyebrow">Apple Log 2 &#8594; Rec.709 &middot; 33&times;33&times;33 3D .cube LUT</div>
    <h1>Golden <span class="i">Daylight</span> Cinema</h1>
    <p class="sub">A warm, rich, atmospheric Mediterranean travel &amp; lifestyle grade for iPhone 17 Pro
      footage (Blackmagic Camera for iOS, Apple Log 2). Golden that stays natural — blues, greens and
      skin stay honest, deep shadows stay clean.</p>
    <a class="cta" href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube" download>Download .cube LUT</a>
    <div class="badge">Simulated-log previews derived from real photographs &middot; SOURCES.txt &middot; VALIDATION_REPORT.txt</div>
  </div>
</header>

<main class="wrap">
  <section class="scenes" id="scenes">
    <div class="section-title">Before &middot; After</div>
SCENES_PLACEHOLDER
  </section>

  <section class="scenes">
    <div class="section-title">Contact sheet</div>
    <div class="contact-grid">
CONTACT_PLACEHOLDER
    </div>
  </section>

  <section id="validation" style="margin-top: 46px;">
    <div class="section-title">Validation summary</div>
    <div class="credits">
      <table>
        <thead><tr><th>Check</th><th>Result</th></tr></thead>
        <tbody>
          <tr><td>33&times;33&times;33 .cube integrity (35937 rows, 0..1, finite)</td><td>PASS</td></tr>
          <tr><td>Interpolation error vs analytic pipeline (image domain)</td><td>PASS &middot; trilinear max &Delta;E 0.05 &middot; tetrahedral max &Delta;E 0.06 &middot; mean &Delta;E 0.005</td></tr>
          <tr><td>Neutral axis (warmth, no orange cast)</td><td>PASS &middot; max R&minus;G 0.016</td></tr>
          <tr><td>Monotonicity &amp; smoothness (diagonal)</td><td>PASS &middot; max negative step &asymp; 0.004 (1 8-bit level)</td></tr>
          <tr><td>Quantisation (8-bit &amp; 10-bit)</td><td>PASS &middot; 8-bit max &Delta;E 0.003 &middot; 10-bit max &Delta;E 0.0008</td></tr>
          <tr><td>Clipping percent (AFTER vs BEFORE, aggregate)</td><td>PASS &middot; extreme 4.86% &rarr; 0.18%</td></tr>
          <tr><td>Shadow-noise gain</td><td>PASS &middot; mean 1.04&times;</td></tr>
          <tr><td>&plusmn;4 stops exposure ladder</td><td>PASS &middot; highlights roll softly, no clipping</td></tr>
        </tbody>
      </table>
      <p style="color: var(--muted); font-size: 13px; margin-bottom: 0; padding-top: 14px; border-top: 1px solid var(--line);">
        Full detail, all charts and checksums live in <b>VALIDATION_REPORT.txt</b>.
        Simulated-log content: inputs were derived from real photographs; no Apple Log 2 recording was captured.
        Behaviour on production footage is not guaranteed.</p>
    </div>
  </section>

  <section id="credits" style="margin-top: 46px;">
    <div class="section-title">Credits &amp; licenses</div>
    <div class="credits">
      <h3>Photographs</h3>
      <table>
        <thead><tr><th>Scene</th><th>Photographer &middot; source</th><th>License</th></tr></thead>
        <tbody>
CREDITS_PLACEHOLDER
        </tbody>
      </table>
      <p style="color: var(--muted); font-size: 13px; margin-bottom: 0;">
        Images were resized for previews; no AI-generated imagery was used.
        See <b>SOURCES.txt</b> for the full provenance record.</p>
    </div>
  </section>

  <footer class="footer">
    <div>Golden Daylight Cinema &middot; Apple Log 2 &rarr; Rec.709 gamma 2.4 &middot; .cube 33&times;33&times;33</div>
    <div style="margin-top: 10px;"><a href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube" download>Download .cube LUT</a></div>
    <div class="small">This LUT is a review/demonstration asset, not a certified product.
      &middot; No physical iPhone / Blackmagic Camera validation was performed &middot; all previews are simulated-log-derived.</div>
  </footer>
</main>

<figure class="fs-banner" id="fsBanner" aria-hidden="true">
  <button id="fsClose" aria-label="Close fullscreen">&times;</button>
  <img id="fsImg" src="" alt="">
  <div class="row">
    <button id="fsPrev">&larr; Prev</button>
    <button id="fsNext">Next &rarr;</button>
    <button onclick="closeFs()">Close (ESC)</button>
  </div>
</figure>

<script>
(function () {
  const sliders = document.querySelectorAll('.scene');
  sliders.forEach((scene) => {
    const range = scene.querySelector('input[type=range]');
    const after = scene.querySelector('.after');
    const wrap = scene.querySelector('.slider-wrap');
    const divider = scene.querySelector('.divider');
    const handle = scene.querySelector('.handle');
    const setReveal = (v) => {
      const pct = v;
      wrap.style.setProperty('--reveal', pct + '%');
      after.style.clipPath = 'inset(0 0 0 ' + pct + '%)';
      divider.style.left = pct + '%';
      handle.style.left = pct + '%';
    };
    range.addEventListener('input', () => setReveal(parseFloat(range.value)));
    setReveal(parseFloat(range.value));
  });
  const fsBanner = document.getElementById('fsBanner');
  const fsImg = document.getElementById('fsImg');
  const fsButtons = document.querySelectorAll('.fs-btn');
  const meta = [];
  fsButtons.forEach((btn) => {
    meta.push({ before: btn.getAttribute('data-before'), after: btn.getAttribute('data-after'), name: btn.getAttribute('data-name') });
    btn.addEventListener('click', () => openFs(meta.length - 1));
  });
  let fsIndex = 0;
  function openFs(i) {
    fsIndex = i;
    const m = meta[i];
    fsImg.src = m.after;
    document.title = m.name + ' — Golden Daylight Cinema';
    fsBanner.classList.add('open');
    fsBanner.setAttribute('aria-hidden', 'false');
  }
  function closeFs() {
    fsBanner.classList.remove('open');
    fsBanner.setAttribute('aria-hidden', 'true');
    document.title = 'Golden Daylight Cinema — Apple Log 2 → Rec.709';
  }
  window.closeFs = closeFs;
  const prev = document.getElementById('fsPrev');
  const next = document.getElementById('fsNext');
  const close = document.getElementById('fsClose');
  prev.addEventListener('click', () => openFs((fsIndex - 1 + meta.length) % meta.length));
  next.addEventListener('click', () => openFs((fsIndex + 1) % meta.length));
  close.addEventListener('click', closeFs);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFs();
    if (e.key === 'ArrowRight') openFs((fsIndex + 1) % meta.length);
    if (e.key === 'ArrowLeft') openFs((fsIndex - 1 + meta.length) % meta.length);
  });
  fsBanner.addEventListener('click', (e) => { if (e.target === fsBanner) closeFs(); });
})();
</script>
</body>
</html>'''
    html = html.replace('SCENES_PLACEHOLDER', scenes_html)
    html = html.replace('CONTACT_PLACEHOLDER', contact_html)
    html = html.replace('CREDITS_PLACEHOLDER', credits_html)
    out = GALLERY / 'index.html'
    out.write_text(html)
    print(f'wrote {out}  ({len(html)} bytes)')


if __name__ == '__main__':
    main()
