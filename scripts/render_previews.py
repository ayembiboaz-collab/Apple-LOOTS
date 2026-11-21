#!/usr/bin/env python3
"""
GOLDEN DAYLIGHT CINEMA — Preview Renderer & Contact Sheet Builder
=================================================================

Renders the 8 BEFORE (Simulated Apple Log 2 / Apple Wide Gamut) and 8 AFTER
(Graded Rec.709 Gamma 2.4 via trilinear evaluation of GOLDEN_DAYLIGHT_CINEMA.cube)
high-resolution 1920x1080 PNGs, plus the comprehensive visual Contact Sheet.

Crucial integrity rule:
Every AFTER image is produced strictly by loading the delivered file
`GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube` from disk and applying
3D trilinear interpolation directly to the corresponding BEFORE PNG pixel buffer.
"""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from scripts.build_lut import (
    apply_cube_lut_trilinear,
    generate_cube_lut,
    load_cube_lut,
    simulate_apple_log2_from_srgb,
    technical_apple_log2_to_rec709,
    LUMA_REC709,
)


ROOT_DIR = Path(__file__).resolve().parent.parent
DELIV_DIR = ROOT_DIR / "GOLDEN_DAYLIGHT_CINEMA"
LUT_PATH = DELIV_DIR / "LUT" / "GOLDEN_DAYLIGHT_CINEMA.cube"
PREVIEWS_DIR = DELIV_DIR / "PREVIEWS"
CONTACT_DIR = DELIV_DIR / "CONTACT_SHEET"
CREDITS_PATH = ROOT_DIR / "sources" / "CREDITS_AND_SOURCES.json"


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()


def render_all_previews() -> list[dict]:
    """
    Ensure the final .cube exists, generate all 8 BEFORE and 8 AFTER 1920x1080 PNGs,
    and return scene telemetry metrics.
    """
    PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    CONTACT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build or load the actual delivered .cube LUT
    generate_cube_lut(LUT_PATH, size=33)
    lut_rgb, lut_meta = load_cube_lut(LUT_PATH)

    credits_data = json.loads(CREDITS_PATH.read_text(encoding="utf-8"))
    scenes = credits_data["scenes"]

    telemetry = []

    for sc in scenes:
        scene_id = sc["id"]
        master_path = ROOT_DIR / sc["master_file"]
        im_src = Image.open(master_path).convert("RGB")
        srgb_norm = np.asarray(im_src, dtype=np.float64) / 255.0

        # Generate Simulated Apple Log 2 / Apple Wide Gamut BEFORE image
        log2_norm = simulate_apple_log2_from_srgb(srgb_norm)
        before_u8 = np.clip(np.round(log2_norm * 255.0), 0, 255).astype(np.uint8)

        before_path = PREVIEWS_DIR / f"{scene_id}_BEFORE.png"
        Image.fromarray(before_u8, mode="RGB").save(before_path, format="PNG", optimize=True)

        # Load the exact saved BEFORE PNG from disk so AFTER is verifiably derived
        # directly from the delivered BEFORE PNG + delivered .cube file
        before_loaded_norm = np.asarray(Image.open(before_path).convert("RGB"), dtype=np.float64) / 255.0
        after_norm = apply_cube_lut_trilinear(before_loaded_norm, lut_rgb)
        after_u8 = np.clip(np.round(after_norm * 255.0), 0, 255).astype(np.uint8)

        after_path = PREVIEWS_DIR / f"{scene_id}_AFTER.png"
        Image.fromarray(after_u8, mode="RGB").save(after_path, format="PNG", optimize=True)

        # Also compute neutral technical Rec.709 decode for telemetry & contact sheet reference
        tech_norm = technical_apple_log2_to_rec709(before_loaded_norm)

        # Compute scene statistics
        y_before = before_loaded_norm @ LUMA_REC709
        y_tech = tech_norm @ LUMA_REC709
        y_after = after_norm @ LUMA_REC709

        # Warmth index (R - B in midtones 0.20 < Y < 0.75)
        mid_mask = (y_after >= 0.20) & (y_after <= 0.75)
        rb_tech_mid = float(np.mean(tech_norm[mid_mask, 0] - tech_norm[mid_mask, 2])) if np.any(mid_mask) else 0.0
        rb_after_mid = float(np.mean(after_norm[mid_mask, 0] - after_norm[mid_mask, 2])) if np.any(mid_mask) else 0.0

        # Highlight & shadow clipping percentages in AFTER
        shadow_clip_pct = float(np.mean(y_after <= 0.004) * 100.0)
        highlight_clip_pct = float(np.mean(y_after >= 0.996) * 100.0)

        stat = {
            "index": sc["index"],
            "id": scene_id,
            "title": sc["title"],
            "subtitle": sc["subtitle"],
            "source_url": sc["source_url"],
            "source_provider": sc["source_provider"],
            "before_file": f"PREVIEWS/{scene_id}_BEFORE.png",
            "after_file": f"PREVIEWS/{scene_id}_AFTER.png",
            "resolution": f"{im_src.width}x{im_src.height}",
            "mean_luma_log2": round(float(np.mean(y_before)), 4),
            "mean_luma_tech709": round(float(np.mean(y_tech)), 4),
            "mean_luma_after": round(float(np.mean(y_after)), 4),
            "contrast_std_log2": round(float(np.std(y_before)), 4),
            "contrast_std_tech709": round(float(np.std(y_tech)), 4),
            "contrast_std_after": round(float(np.std(y_after)), 4),
            "midtone_rb_tech709": round(rb_tech_mid, 4),
            "midtone_rb_after": round(rb_after_mid, 4),
            "midtone_warmth_delta": round(rb_after_mid - rb_tech_mid, 4),
            "shadow_clip_pct": round(shadow_clip_pct, 3),
            "highlight_clip_pct": round(highlight_clip_pct, 3),
        }
        telemetry.append(stat)
        print(
            f"[{sc['index']}/8] {scene_id}: "
            f"Y_tech={stat['mean_luma_tech709']:.3f}->Y_after={stat['mean_luma_after']:.3f} | "
            f"Mid(R-B) {stat['midtone_rb_tech709']:+.3f}->{stat['midtone_rb_after']:+.3f} "
            f"(d={stat['midtone_warmth_delta']:+.3f}) | "
            f"Clip Sh={stat['shadow_clip_pct']:.2f}% Hi={stat['highlight_clip_pct']:.2f}%"
        )

    build_contact_sheet(scenes, telemetry, lut_rgb)
    return telemetry


def build_contact_sheet(scenes: list[dict], telemetry: list[dict], lut_rgb: np.ndarray) -> Path:
    """
    Build a luxury dark-portfolio Contact Sheet (2400 x 3680 PNG) displaying all 8 scenes:
    - Left Column:   BEFORE (Simulated Apple Log 2 / Apple Wide Gamut Input)
    - Center Column: Reference Neutral Decode (Standard Rec.709 Technical Conversion)
    - Right Column:  AFTER (GOLDEN_DAYLIGHT_CINEMA.cube Applied — Rec.709 Gamma 2.4)
    - Telemetry strip per row: Luminance, Contrast, Midtone Honey Warmth shift, Clipping check.
    """
    W = 2400
    header_h = 230
    row_h = 405
    footer_h = 140
    H = header_h + len(scenes) * row_h + footer_h

    canvas = Image.new("RGB", (W, H), (12, 13, 16))
    draw = ImageDraw.Draw(canvas)

    f_title = _get_font(40, bold=True)
    f_sub = _get_font(20, bold=False)
    f_sec = _get_font(22, bold=True)
    f_meta = _get_font(16, bold=False)
    f_badge = _get_font(15, bold=True)

    # Header bar
    draw.rectangle([0, 0, W, header_h - 10], fill=(18, 20, 25))
    draw.line([(0, header_h - 10), (W, header_h - 10)], fill=(198, 154, 88), width=2)

    draw.text((50, 36), "GOLDEN DAYLIGHT CINEMA — VISUAL MASTER CONTACT SHEET", fill=(242, 236, 224), font=f_title)
    draw.text(
        (50, 92),
        "Standalone 33x33x33 3D LUT (.cube)  |  Input: Apple Log 2 / Apple Wide Gamut (D65)  ->  Output: Rec.709 SDR Gamma 2.4",
        fill=(212, 172, 106),
        font=f_sub,
    )
    draw.text(
        (50, 126),
        "Target: iPhone 17 Pro / Pro Max (Blackmagic Camera for iOS)  |  Note: BEFORE inputs are documented Simulated Apple Log 2 encodings derived from credited real photography.",
        fill=(156, 162, 174),
        font=f_meta,
    )

    # Column headers
    col_w = 720
    col_h = 315  # 16:9 thumbnail (560x315) or (720x315) -> let's use 560x315 (exact 16:9!) + telemetry panel
    thumb_w, thumb_h = 560, 315
    col_x = [50, 640, 1230]
    col_labels = [
        "1. BEFORE — SIMULATED APPLE LOG 2 (LUT INPUT)",
        "2. BASELINE — NEUTRAL REC.709 TECHNICAL DECODE",
        "3. AFTER — GOLDEN_DAYLIGHT_CINEMA.cube APPLIED",
    ]
    for cx, lbl in zip(col_x, col_labels):
        draw.text((cx, 174), lbl, fill=(212, 172, 106), font=f_badge)
    draw.text((1820, 174), "4. COLOR & EXPOSURE TELEMETRY", fill=(212, 172, 106), font=f_badge)

    for idx, (sc, stat) in enumerate(zip(scenes, telemetry)):
        y0 = header_h + idx * row_h
        draw.rectangle([36, y0 + 6, W - 36, y0 + row_h - 8], fill=(20, 22, 28), outline=(38, 42, 52), width=1)

        # Scene title bar inside row
        scene_header = f"SCENE 0{sc['index']}  |  {sc['title'].upper()} — {sc['subtitle']}"
        draw.text((50, y0 + 16), scene_header, fill=(240, 235, 225), font=f_sec)

        before_path = PREVIEWS_DIR / f"{sc['id']}_BEFORE.png"
        after_path = PREVIEWS_DIR / f"{sc['id']}_AFTER.png"

        im_before = Image.open(before_path).convert("RGB")
        im_after = Image.open(after_path).convert("RGB")

        # Compute baseline technical Rec.709 image for center column
        before_norm = np.asarray(im_before, dtype=np.float64) / 255.0
        tech_norm = technical_apple_log2_to_rec709(before_norm)
        im_tech = Image.fromarray(np.clip(np.round(tech_norm * 255.0), 0, 255).astype(np.uint8), mode="RGB")

        t_before = im_before.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        t_tech = im_tech.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        t_after = im_after.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)

        img_y = y0 + 54
        canvas.paste(t_before, (col_x[0], img_y))
        canvas.paste(t_tech, (col_x[1], img_y))
        canvas.paste(t_after, (col_x[2], img_y))

        # Subtle borders around thumbnails
        for cx in col_x:
            draw.rectangle([cx, img_y, cx + thumb_w, img_y + thumb_h], outline=(62, 66, 78), width=1)
        draw.rectangle([col_x[2], img_y, col_x[2] + thumb_w, img_y + thumb_h], outline=(198, 154, 88), width=2)

        # Telemetry panel on the right (x=1820..2345)
        tx = 1820
        ty = img_y + 6
        lines = [
            f"Resolution: {stat['resolution']} (16:9 PNG)",
            f"Source: {stat['source_provider']}",
            f"Mean Luma (Log2 In):   {stat['mean_luma_log2']:.4f}",
            f"Mean Luma (Tech 709):  {stat['mean_luma_tech709']:.4f}",
            f"Mean Luma (LUT Out):   {stat['mean_luma_after']:.4f}",
            f"Contrast SD (Log2->Out): {stat['contrast_std_log2']:.3f} -> {stat['contrast_std_after']:.3f}",
            f"Midtone (R-B) Base:    {stat['midtone_rb_tech709']:+.4f}",
            f"Midtone (R-B) Graded:  {stat['midtone_rb_after']:+.4f}",
            f"Honey Warmth Shift:    {stat['midtone_warmth_delta']:+.4f}",
            f"Shadow Clip (<=0.4%):  {stat['shadow_clip_pct']:.2f}%",
            f"Highlight Clip (>=99.6%): {stat['highlight_clip_pct']:.2f}%",
            "LUT Verification: Direct .cube Trilinear",
        ]
        for li, line_str in enumerate(lines):
            color = (212, 172, 106) if "Honey Warmth" in line_str or "LUT Verification" in line_str else (188, 194, 206)
            draw.text((tx, ty + li * 25), line_str, fill=color, font=f_meta)

    # Footer
    fy = H - footer_h + 22
    draw.line([(36, fy - 12), (W - 36, fy - 12)], fill=(52, 56, 68), width=1)
    draw.text(
        (50, fy),
        "DELIVERABLE VERIFICATION: All AFTER renders above were generated strictly by parsing GOLDEN_DAYLIGHT_CINEMA/LUT/GOLDEN_DAYLIGHT_CINEMA.cube (33x33x33) and applying 3D trilinear interpolation to the BEFORE PNGs.",
        fill=(212, 172, 106),
        font=f_meta,
    )
    draw.text(
        (50, fy + 30),
        "SIMULATION DISCLOSURE: BEFORE frames are mathematically simulated Apple Log 2 / Apple Wide Gamut encodings from credited photography (Unsplash & V-Flat World). Not claimed as raw physical iPhone 17 Pro sensor captures.",
        fill=(148, 154, 166),
        font=f_meta,
    )

    out_contact = CONTACT_DIR / "GOLDEN_DAYLIGHT_CINEMA_CONTACT_SHEET.png"
    canvas.save(out_contact, format="PNG", optimize=True)
    print(f"Saved Contact Sheet: {out_contact} ({canvas.size})")
    return out_contact


if __name__ == "__main__":
    render_all_previews()
