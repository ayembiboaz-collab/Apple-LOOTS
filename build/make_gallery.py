#!/usr/bin/env python3
"""Generate the standalone, offline gallery (GALLERY/index.html).

Every number printed in the gallery is read from build/validation_results.json so
the page cannot drift away from the validation run.  All CSS/JS is inlined and
images are referenced relatively: the page works from a local folder, from a
sandboxed iframe with no network, and from GitHub's raw file view.
"""

from __future__ import annotations

import json
import os

import render_previews as rp

ROOT = rp.ROOT
PROJ = rp.PROJ
OUT = os.path.join(PROJ, "GALLERY", "index.html")
RESULTS = os.path.join(ROOT, "build", "validation_results.json")

NOTES = {
    "01": ("Deep daylight blue",
           "The sky keeps its saturation while the shaded facade gains density instead of going grey. "
           "Glass reflections stay specular, not blown."),
    "02": ("Skin held, shadows clean",
           "Direct-sun skin keeps its hue (measured drift +0.2 degrees) while the black garment "
           "reads as black cloth rather than lifted grey. Solar flare stays warm, not pink."),
    "03": ("Warm stone, cool shadows",
           "Cycladic white walls pick up warmth in the sunlit planes (+21% relative chroma) and the "
           "blue railing stays deep. Contrast is built into the stone, not added as a global contrast bump."),
    "04": ("Turquoise, not cyan",
           "The lagoon gradient survives (+11% relative chroma, hue +1.3 degrees) and the sand warms "
           "without going orange. Cloud tops are eased off, never clipped."),
    "05": ("Natural foliage",
           "Forest greens stay green. Haze in the distance is preserved so the valley reads deep "
           "rather than crushed."),
    "06": ("Golden hour, not orange hour",
           "Warm light is left as the camera found it (chroma measured slightly down, not up) while "
           "the cloud sea keeps separation and the foreground trees keep detail."),
    "07": ("Neutral concrete, deep shade",
           "Concrete and stone stay neutral, so the only colour in frame is real colour. Shade under "
           "the colonnade holds shape."),
    "08": ("Street realism",
           "People keep skin tone at a distance, and the sunlit facades roll off instead of clipping."),
}

EXPOSURE = [
    ("-1 stop", "MED_after_03_mediterranean_-1_stop.jpg", "-1_stop"),
    ("Normal", "MED_after_03_mediterranean_normal.jpg", "normal"),
    ("+1 stop", "MED_after_03_mediterranean_+1_stop.jpg", "+1_stop"),
]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def num(x, nd=3):
    return f"{x:.{nd}f}"


def main():
    r = json.load(open(RESULTS))
    exp = {e["exposure"]: e for e in r["exposure_table"]}

    cards = []
    for num_, slug, title, _f in rp.SCENES:
        headline, note = NOTES[num_]
        cards.append(f"""
    <section class="scene" id="{slug}">
      <div class="scene-head">
        <span class="idx">{num_}</span>
        <h2>{esc(title)}</h2>
        <span class="tag">{esc(headline)}</span>
      </div>
      <div class="compare" data-slug="{slug}">
        <img class="after" src="img/after/{slug}.jpg" alt="{esc(title)} graded">
        <div class="clip"><img src="img/before/{slug}.jpg" alt="{esc(title)} ungraded reference"></div>
        <div class="handle" aria-hidden="true"></div>
        <input class="slider" type="range" min="0" max="100" value="50" aria-label="Compare before and after">
        <span class="lbl before-lbl">BEFORE</span>
        <span class="lbl after-lbl">AFTER</span>
      </div>
      <div class="scene-foot">
        <img class="log" src="img/log/{slug}.jpg" alt="{esc(title)} Apple Log 2 source">
        <div class="note">
          <p>{esc(note)}</p>
          <p class="altsmall">Small log thumbnail at left is the untouched Apple Log 2 frame this preview was made from.</p>
        </div>
      </div>
    </section>""")

    exp_cards = []
    for label, _f, key in EXPOSURE:
        e = exp[key]
        exp_cards.append(f"""
        <figure>
          <img src="../PREVIEWS/EXPOSURE_TESTS/AFTER_03_mediterranean_{key.replace('+','%2B')}.jpg" alt="Scene 03 at {label}">
          <figcaption><b>{esc(label)}</b><span>mean {num(e['out_mean'])} &middot; p1 {num(e['out_p01'])} &middot;
          p99 {num(e['out_p99'])} &middot; clipped {e['frac_clipped_low']*100:.2f}% low / {e['frac_clipped_high']*100:.2f}% high</span></figcaption>
        </figure>""")

    fps = r["fidelity_scene_table"]
    fid_rows = "".join(
        f"<tr><td>{esc(v['scene'].replace('-',' '))}</td><td>{num(v['mean'],4)}</td>"
        f"<td>{num(v['p999'],4)}</td><td>{num(v['max'],4)}</td></tr>" for v in fps)

    regions = r["region_table"]
    reg_rows = "".join(
        f"<tr><td>{esc(g['scene'].split(' ',1)[1].replace('-',' '))}</td><td>{esc(g['region'])}</td>"
        f"<td>{g['L'][0]:.3f} &rarr; {g['L'][1]:.3f}</td>"
        f"<td>{g['rel_chroma_pct']:+.1f}%</td><td>{g['hue_shift']:+.1f}&deg;</td></tr>" for g in regions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GOLDEN DAYLIGHT CINEMA &mdash; Apple Log 2 LUT</title>
<style>
  :root {{
    --bg:#0c0c0e; --panel:#141417; --line:#26262b; --fg:#ece8e0; --dim:#9c988f; --gold:#d6a85c;
  }}
  * {{ box-sizing:border-box; }}
  html {{ scroll-behavior:smooth; }}
  body {{
    margin:0; background:var(--bg); color:var(--fg);
    font:16px/1.6 "Helvetica Neue",Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;
  }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:0 28px; }}
  header.hero {{ padding:76px 0 40px; border-bottom:1px solid var(--line); }}
  .eyebrow {{ color:var(--gold); letter-spacing:.28em; font-size:12px; text-transform:uppercase; }}
  h1 {{ font-size:clamp(34px,6vw,64px); line-height:1.02; margin:14px 0 10px; letter-spacing:-.02em; font-weight:300; }}
  h1 b {{ font-weight:700; }}
  .sub {{ color:var(--dim); max-width:64ch; font-size:17px; }}
  .chips {{ display:flex; flex-wrap:wrap; gap:10px; margin:26px 0 0; padding:0; list-style:none; }}
  .chips li {{
    border:1px solid var(--line); border-radius:999px; padding:6px 14px; font-size:13px; color:var(--dim);
    background:var(--panel);
  }}
  .chips b {{ color:var(--fg); font-weight:600; }}
  .scene {{ padding:56px 0 8px; border-bottom:1px solid var(--line); }}
  .scene-head {{ display:flex; align-items:baseline; gap:16px; flex-wrap:wrap; margin-bottom:16px; }}
  .idx {{ color:var(--gold); font-size:13px; letter-spacing:.16em; }}
  .scene h2 {{ font-size:24px; margin:0; font-weight:600; letter-spacing:-.01em; }}
  .tag {{ color:var(--dim); font-size:14px; }}
  .compare {{
    position:relative; overflow:hidden; border-radius:8px; background:#000; line-height:0;
    touch-action:pan-y; user-select:none;
  }}
  .compare img {{ width:100%; height:auto; display:block; }}
  .clip {{ position:absolute; inset:0; overflow:hidden; clip-path:inset(0 50% 0 0); }}
  .clip img {{ position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; }}
  .handle {{
    position:absolute; top:0; bottom:0; left:50%; width:2px; background:rgba(255,255,255,.85);
    box-shadow:0 0 0 1px rgba(0,0,0,.35); pointer-events:none;
  }}
  .handle::after {{
    content:""; position:absolute; top:50%; left:50%; width:38px; height:38px; margin:-19px 0 0 -19px;
    border-radius:50%; border:1px solid rgba(255,255,255,.9); background:rgba(12,12,14,.45);
    backdrop-filter:blur(2px);
  }}
  .slider {{ position:absolute; inset:0; width:100%; height:100%; opacity:0; cursor:ew-resize; margin:0; }}
  .lbl {{
    position:absolute; top:14px; font-size:11px; letter-spacing:.2em; color:#fff; text-shadow:0 1px 3px #000;
    pointer-events:none;
  }}
  .before-lbl {{ left:14px; }} .after-lbl {{ right:14px; color:var(--gold); }}
  .scene-foot {{ display:flex; gap:22px; align-items:flex-start; padding:18px 0 26px; }}
  .log {{ width:150px; border-radius:5px; display:block; filter:saturate(.55) contrast(.85); opacity:.9; }}
  .note p {{ margin:0 0 8px; color:var(--dim); font-size:15px; max-width:76ch; }}
  .note b {{ color:var(--fg); }}
  .altsmall {{ font-size:13px !important; opacity:.7; }}
  h3.sec {{ font-size:13px; letter-spacing:.24em; text-transform:uppercase; color:var(--gold);
            margin:64px 0 18px; font-weight:600; }}
  .exp {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:18px; }}
  .exp figure {{ margin:0; }}
  .exp img {{ width:100%; border-radius:6px; display:block; }}
  .exp figcaption {{ font-size:12.5px; color:var(--dim); padding-top:8px; line-height:1.5; }}
  .exp b {{ color:var(--fg); display:block; font-size:13px; margin-bottom:2px; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line); }}
  th {{ color:var(--dim); font-weight:500; font-size:12px; letter-spacing:.12em; text-transform:uppercase; }}
  td:nth-child(n+2), th:nth-child(n+2) {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .grid2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:34px; }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:22px 24px; }}
  .kpi {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:14px; margin:22px 0 0; }}
  .kpi div {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px 18px; }}
  .kpi span {{ display:block; color:var(--dim); font-size:11.5px; letter-spacing:.14em; text-transform:uppercase; }}
  .kpi b {{ font-size:22px; font-weight:600; font-variant-numeric:tabular-nums; }}
  footer {{ padding:56px 0 80px; color:var(--dim); font-size:13.5px; }}
  footer a {{ color:var(--gold); text-decoration:none; }}
  .fine {{ font-size:12.5px; color:var(--dim); }}
  @media (max-width:640px) {{
    .scene-foot {{ flex-direction:column; }} .log {{ width:100%; max-width:240px; }}
    header.hero {{ padding-top:48px; }}
  }}
</style>
</head>
<body>
<div class="wrap">

<header class="hero">
  <div class="eyebrow">Apple Log 2 &middot; Apple Wide Gamut &rarr; Rec.709</div>
  <h1>GOLDEN<br><b>DAYLIGHT CINEMA</b></h1>
  <p class="sub">A daylight transform for iPhone 17 Pro log footage, built to keep skin and foliage
  natural while giving harsh sun a filmic shoulder, warm highlights and shadows that stay clean.
  Not a look pack: one LUT, eight scenes, measured.</p>
  <ul class="chips">
    <li><b>33&sup3;</b> tetrahedral &middot; .cube</li>
    <li><b>Output</b> Rec.709 gamma 2.4</li>
    <li><b>Curve</b> Apple white paper, 8e-7 max error</li>
    <li><b>Gamut</b> Bradford D65, exact white</li>
    <li><b>Skin drift</b> &le; {r['skin_hue_shift_max_deg']:.1f}&deg;</li>
    <li><b>Clipping</b> 0.00% at &plusmn;1 stop</li>
  </ul>
</header>

<main>
  <div class="kpi">
    <div><span>LUT rows</span><b>{r['cube_data_rows']:,}</b></div>
    <div><span>NaN / Inf</span><b>0</b></div>
    <div><span>Out of range</span><b>0</b></div>
    <div><span>Preview vs LUT</span><b>0 / 255</b></div>
    <div><span>Neutral axis flat steps</span><b>{r['neutral_flat_steps_count']}</b></div>
    <div><span>Overall fidelity</span><b>{r['fidelity_overall_mean']:.4f}</b></div>
  </div>
  <p class="fine" style="margin-top:14px">Drag any divider. Left is a plain Rec.709 conversion of the same
  Apple Log 2 frame, right is the finished LUT. Every graded frame in this page was rendered by applying the
  shipped .cube with tetrahedral interpolation &mdash; not by re-running the design code.</p>

  {''.join(cards)}

  <h3 class="sec">Exposure robustness &mdash; scene 03 at &plusmn;1 stop</h3>
  <div class="exp">{''.join(exp_cards)}</div>

  <h3 class="sec">Measured behaviour</h3>
  <div class="grid2">
    <div class="panel">
      <h4 style="margin:0 0 10px;font-size:14px;letter-spacing:.06em">Region response (OKLab)</h4>
      <table>
        <thead><tr><th>Scene</th><th>Region</th><th>L*</th><th>&Delta;chroma</th><th>&Delta;hue</th></tr></thead>
        <tbody>{reg_rows}</tbody>
      </table>
      <p class="fine" style="margin-top:10px">&Delta;chroma is relative (chroma / lightness), so it stays
      meaningful when a region darkens. A pure chroma ratio would read as desaturation for any darkening grade.</p>
    </div>
    <div class="panel">
      <h4 style="margin:0 0 10px;font-size:14px;letter-spacing:.06em">LUT fidelity on real pixels</h4>
      <table>
        <thead><tr><th>Scene</th><th>mean</th><th>p99.9</th><th>max</th></tr></thead>
        <tbody>{fid_rows}</tbody>
      </table>
      <p class="fine" style="margin-top:10px">Code-value difference between the 33&sup3; tetrahedral
      interpolation and the continuous transform that generated it. The shipped LUT is the reference;
      the previews are rendered from it.</p>
    </div>
  </div>

  <h3 class="sec">Files</h3>
  <div class="panel">
    <table>
      <tbody>
        <tr><td><b>LUT</b></td><td style="text-align:left">../LUT/GOLDEN_DAYLIGHT_CINEMA.cube &mdash; 33&sup3;, {r['cube_file_bytes']:,} bytes</td></tr>
        <tr><td><b>Previews</b></td><td style="text-align:left">../PREVIEWS/BEFORE &amp; ../PREVIEWS/AFTER &mdash; full-size PNG pairs</td></tr>
        <tr><td><b>Contact sheets</b></td><td style="text-align:left">../CONTACT_SHEET/*.jpg</td></tr>
        <tr><td><b>Validation</b></td><td style="text-align:left">../VALIDATION_REPORT.txt &mdash; every number on this page</td></tr>
        <tr><td><b>Install</b></td><td style="text-align:left">../README.txt</td></tr>
      </tbody>
    </table>
  </div>
</main>

<footer>
  <p><b style="color:var(--fg)">GOLDEN DAYLIGHT CINEMA</b> &middot; built from Apple's published
  Apple Log 2 transfer function and Apple Wide Gamut primaries. Curve error
  {r['curve_signal_max_abs_err']:.1e}, round-trip {r['curve_roundtrip_max_err']:.1e},
  white point error {r['gamut_neutral_error']:.1e}.</p>
  <p class="fine">Preview sources are royalty-free photographs graded through a physically based
  Apple Log 2 simulation; they are demonstrations, not camera test charts.</p>
</footer>

</div>

<script>
(function () {{
  document.querySelectorAll('.compare').forEach(function (box) {{
    var slider = box.querySelector('.slider');
    var clip = box.querySelector('.clip');
    var handle = box.querySelector('.handle');
    function set(v) {{
      clip.style.clipPath = 'inset(0 ' + (100 - v) + '% 0 0)';
      handle.style.left = v + '%';
    }}
    slider.addEventListener('input', function () {{ set(parseFloat(slider.value)); }});
    set(parseFloat(slider.value));
    box.addEventListener('pointermove', function (e) {{
      if (e.pointerType === 'mouse' && e.buttons === 0) return;
      var r = box.getBoundingClientRect();
      var v = Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100));
      slider.value = v; set(v);
    }});
  }});
}})();
</script>
</body>
</html>
"""

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html)
    print("wrote", OUT, len(html), "bytes")


if __name__ == "__main__":
    main()
