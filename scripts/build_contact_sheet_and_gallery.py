#!/usr/bin/env python3
"""
Generate GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET/contact_sheet.png
and GOLDEN_DAYLIGHT_CINEMA/GALLERY/index.html
"""

import os
from PIL import Image, ImageDraw, ImageFont

SCENES = [
    ("01_harsh_midday_city", "01. Harsh Midday City"),
    ("02_midday_portrait", "02. Midday Portrait (Direct Sun)"),
    ("03_mediterranean_street", "03. Mediterranean Street"),
    ("04_bright_beach_daylight", "04. Bright Beach Daylight"),
    ("05_natural_landscape", "05. Natural Landscape & Mountains"),
    ("06_golden_hour_landscape", "06. Golden-Hour Landscape"),
    ("07_modern_architecture", "07. Modern Architecture"),
    ("08_outdoor_travel_scene", "08. Outdoor Travel Scene"),
]


def build_contact_sheet():
    out_dir = "GOLDEN_DAYLIGHT_CINEMA/CONTACT_SHEET"
    os.makedirs(out_dir, exist_ok=True)
    previews_dir = "GOLDEN_DAYLIGHT_CINEMA/PREVIEWS"

    cell_w, cell_h = 480, 320
    pad = 24
    header_h = 90
    cols = 2  # 2 pairs per row? No, 1 pair (BEFORE + AFTER) per row, 2 columns of pairs -> 4 rows x 2 pairs = 8 scenes
    pair_w = cell_w * 2 + 12
    canvas_w = pad * 3 + pair_w * 2
    canvas_h = header_h + pad + (cell_h + 44 + pad) * 4

    canvas = Image.new("RGB", (canvas_w, canvas_h), (14, 14, 16))
    draw = ImageDraw.Draw(canvas)

    draw.text((pad, 24), "GOLDEN DAYLIGHT CINEMA — 8-SCENE CONTACT SHEET", fill=(235, 200, 130))
    draw.text((pad, 50), "Input: Simulated Apple Log 2 (Apple Wide Gamut)  |  Output: Rec.709 Gamma 2.4  |  33x33x33 .cube LUT", fill=(170, 170, 175))

    for idx, (slug, title) in enumerate(SCENES):
        row = idx // 2
        col = idx % 2
        x0 = pad + col * (pair_w + pad)
        y0 = header_h + pad + row * (cell_h + 44 + pad)

        draw.text((x0, y0), f"{title}  (Left: BEFORE  |  Right: AFTER)", fill=(230, 230, 235))

        before_im = Image.open(os.path.join(previews_dir, f"{slug}_BEFORE.png")).convert("RGB")
        after_im = Image.open(os.path.join(previews_dir, f"{slug}_AFTER.png")).convert("RGB")

        before_im.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
        after_im.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)

        bx = x0 + (cell_w - before_im.width) // 2
        by = y0 + 24 + (cell_h - before_im.height) // 2
        ax = x0 + cell_w + 12 + (cell_w - after_im.width) // 2
        ay = y0 + 24 + (cell_h - after_im.height) // 2

        canvas.paste(before_im, (bx, by))
        canvas.paste(after_im, (ax, ay))

    out_path = os.path.join(out_dir, "contact_sheet.png")
    canvas.save(out_path, format="PNG")
    print(f"Saved contact sheet to {out_path} ({canvas_w}x{canvas_h})")


def build_gallery():
    out_dir = "GOLDEN_DAYLIGHT_CINEMA/GALLERY"
    os.makedirs(out_dir, exist_ok=True)

    cards_html = []
    for slug, title in SCENES:
        cards_html.append(f"""
        <article class="scene-card">
          <div class="scene-header">
            <h3>{title}</h3>
            <div class="scene-actions">
              <button class="btn-fs" onclick="openFullscreen('../PREVIEWS/{slug}_BEFORE.png', '../PREVIEWS/{slug}_AFTER.png', '{title}')">Full Screen</button>
            </div>
          </div>
          <div class="ba-slider" data-slug="{slug}">
            <img class="ba-after" src="../PREVIEWS/{slug}_AFTER.png" alt="{title} After" loading="lazy" />
            <div class="ba-before-wrap">
              <img class="ba-before" src="../PREVIEWS/{slug}_BEFORE.png" alt="{title} Before" loading="lazy" />
            </div>
            <div class="ba-handle" aria-label="Comparison slider">
              <div class="ba-line"></div>
              <div class="ba-knob">&#8596;</div>
            </div>
            <span class="badge badge-before">BEFORE (Rec.709 Source)</span>
            <span class="badge badge-after">AFTER (Golden Daylight LUT)</span>
          </div>
        </article>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>GOLDEN DAYLIGHT CINEMA — Apple Log 2 LUT</title>
  <style>
    :root {{
      --bg: #0c0c0e;
      --surface: #151519;
      --border: #27272e;
      --text: #f2f2f5;
      --muted: #9a9aa6;
      --gold: #e5b869;
      --gold-dim: rgba(229, 184, 105, 0.15);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px 18px 64px; }}
    header {{
      border-bottom: 1px solid var(--border);
      padding-bottom: 28px;
      margin-bottom: 32px;
    }}
    .eyebrow {{
      color: var(--gold);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    h1 {{ font-size: clamp(28px, 5vw, 44px); font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; }}
    .lead {{ color: var(--muted); max-width: 760px; font-size: 16px; margin-bottom: 20px; }}
    .cta-row {{ display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
    .btn-primary {{
      display: inline-block;
      background: var(--gold);
      color: #111;
      font-weight: 600;
      text-decoration: none;
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 15px;
    }}
    .btn-secondary {{
      display: inline-block;
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      text-decoration: none;
      padding: 12px 18px;
      border-radius: 10px;
      font-size: 15px;
    }}
    .specs {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin-bottom: 36px;
    }}
    .spec-box {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
    }}
    .spec-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
    .spec-val {{ font-size: 15px; font-weight: 600; margin-top: 4px; color: var(--text); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 24px;
    }}
    .scene-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
    }}
    .scene-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 16px;
      border-bottom: 1px solid var(--border);
    }}
    .scene-header h3 {{ font-size: 15px; font-weight: 600; }}
    .btn-fs {{
      background: var(--gold-dim);
      color: var(--gold);
      border: 1px solid rgba(229, 184, 105, 0.35);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}
    .ba-slider {{
      position: relative;
      width: 100%;
      aspect-ratio: 16 / 10;
      overflow: hidden;
      user-select: none;
      touch-action: pan-y;
      background: #000;
    }}
    .ba-slider img {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      pointer-events: none;
    }}
    .ba-before-wrap {{
      position: absolute;
      inset: 0;
      width: 50%;
      overflow: hidden;
    }}
    .ba-before-wrap img {{
      width: 100%;
      max-width: none;
    }}
    .ba-handle {{
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 40px;
      transform: translateX(-50%);
      cursor: ew-resize;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .ba-line {{
      position: absolute;
      top: 0;
      bottom: 0;
      width: 2px;
      background: rgba(255,255,255,0.9);
      box-shadow: 0 0 8px rgba(0,0,0,0.6);
    }}
    .ba-knob {{
      position: relative;
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: var(--gold);
      color: #111;
      font-weight: 700;
      font-size: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }}
    .badge {{
      position: absolute;
      bottom: 10px;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      background: rgba(0,0,0,0.65);
      color: #fff;
      pointer-events: none;
    }}
    .badge-before {{ left: 10px; }}
    .badge-after {{ right: 10px; color: var(--gold); }}
    .contact-section {{ margin-top: 48px; }}
    .contact-section h2 {{ font-size: 22px; margin-bottom: 12px; }}
    .contact-img {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--border);
      display: block;
    }}
    .note {{
      margin-top: 24px;
      padding: 16px;
      border-radius: 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
    }}
    /* Fullscreen Modal */
    .modal {{
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.94);
      z-index: 999;
      flex-direction: column;
      padding: 16px;
    }}
    .modal.open {{ display: flex; }}
    .modal-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .modal-close {{
      background: #27272e;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 14px;
      cursor: pointer;
    }}
    .modal-body {{
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      min-height: 0;
    }}
    @media (max-width: 768px) {{
      .modal-body {{ grid-template-columns: 1fr; }}
    }}
    .modal-pane {{
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}
    .modal-pane span {{ font-size: 12px; color: var(--gold); margin-bottom: 6px; font-weight: 600; }}
    .modal-pane img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      background: #000;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="eyebrow">iPhone 17 Pro &middot; Blackmagic Camera &middot; Apple Log 2</div>
      <h1>GOLDEN DAYLIGHT CINEMA</h1>
      <p class="lead">
        A standalone 33&times;33&times;33 3D LUT that decodes Apple Log 2 (Apple Wide Gamut) into Rec.709 Gamma 2.4—engineered to transform harsh midday daylight into rich, warm Mediterranean cinema while keeping whites clean, skies natural, and skin tones believable.
      </p>
      <div class="cta-row">
        <a class="btn-primary" href="../LUT/GOLDEN_DAYLIGHT_CINEMA.cube" download>Download .cube LUT</a>
        <a class="btn-secondary" href="../VALIDATION_REPORT.txt">Validation Report</a>
        <a class="btn-secondary" href="../README.txt">iPhone Install Guide</a>
      </div>
    </header>

    <section class="specs">
      <div class="spec-box">
        <div class="spec-label">Input Space</div>
        <div class="spec-val">Apple Log 2 / Apple Wide Gamut</div>
      </div>
      <div class="spec-box">
        <div class="spec-label">Output Space</div>
        <div class="spec-val">Rec.709 SDR, Gamma 2.4</div>
      </div>
      <div class="spec-box">
        <div class="spec-label">LUT Format</div>
        <div class="spec-val">33 &times; 33 &times; 33 (.cube)</div>
      </div>
      <div class="spec-box">
        <div class="spec-label">Test Method</div>
        <div class="spec-val">Simulated Apple Log 2 from sRGB</div>
      </div>
    </section>

    <section class="grid">
      {''.join(cards_html)}
    </section>

    <section class="contact-section">
      <h2>Visual Contact Sheet</h2>
      <img class="contact-img" src="../CONTACT_SHEET/contact_sheet.png" alt="8-Scene Contact Sheet" loading="lazy" />
    </section>

    <div class="note">
      <strong>Simulation &amp; Testing Note:</strong> Genuine iPhone 17 Pro Apple Log 2 sensor footage was not available in this sandbox. All BEFORE/AFTER comparisons were generated by converting documented sRGB/Rec.709 reference images into simulated Apple Log 2 (Apple Wide Gamut) and applying the actual <code>GOLDEN_DAYLIGHT_CINEMA.cube</code> LUT via trilinear interpolation.
    </div>
  </div>

  <div id="fsModal" class="modal" role="dialog" aria-modal="true">
    <div class="modal-top">
      <strong id="fsTitle">Scene Comparison</strong>
      <button class="modal-close" onclick="closeFullscreen()">Close</button>
    </div>
    <div class="modal-body">
      <div class="modal-pane">
        <span>BEFORE (Rec.709 Source)</span>
        <img id="fsBefore" src="" alt="Before" />
      </div>
      <div class="modal-pane">
        <span>AFTER (Golden Daylight Cinema LUT)</span>
        <img id="fsAfter" src="" alt="After" />
      </div>
    </div>
  </div>

  <script>
    document.querySelectorAll('.ba-slider').forEach(slider => {{
      const wrap = slider.querySelector('.ba-before-wrap');
      const handle = slider.querySelector('.ba-handle');
      const beforeImg = wrap.querySelector('img');
      let dragging = false;

      const syncWidth = () => {{
        beforeImg.style.width = slider.clientWidth + 'px';
      }};
      window.addEventListener('resize', syncWidth);
      syncWidth();

      const setPos = (clientX) => {{
        const rect = slider.getBoundingClientRect();
        let pct = ((clientX - rect.left) / rect.width) * 100;
        pct = Math.max(0, Math.min(100, pct));
        wrap.style.width = pct + '%';
        handle.style.left = pct + '%';
      }};

      slider.addEventListener('pointerdown', e => {{
        dragging = true;
        slider.setPointerCapture(e.pointerId);
        setPos(e.clientX);
      }});
      slider.addEventListener('pointermove', e => {{
        if (dragging) setPos(e.clientX);
      }});
      slider.addEventListener('pointerup', () => {{ dragging = false; }});
      slider.addEventListener('pointercancel', () => {{ dragging = false; }});
    }});

    function openFullscreen(beforeSrc, afterSrc, title) {{
      document.getElementById('fsBefore').src = beforeSrc;
      document.getElementById('fsAfter').src = afterSrc;
      document.getElementById('fsTitle').textContent = title;
      document.getElementById('fsModal').classList.add('open');
    }}
    function closeFullscreen() {{
      document.getElementById('fsModal').classList.remove('open');
    }}
  </script>
</body>
</html>
"""
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved gallery to {out_path}")


if __name__ == "__main__":
    build_contact_sheet()
    build_gallery()
