"""
scenes.py -- shared scene loading and simulated Apple Log 2 plate creation.

PROVENANCE
==========
The eight scene sources in GOLDEN_DAYLIGHT_CINEMA/SCENES/source/ are
AI-GENERATED reference photographs (image synthesis model, prompts in
SCENES/prompts.txt). They are NOT iPhone footage and are not presented as such.

They are turned into SIMULATED Apple Log 2 plates by inverting this project's
neutral display tone curve back to scene reflectance and then encoding that
reflectance with the documented Apple Log 2 transfer function in Apple Wide
Gamut, quantised to 10 bits. That is the documented simulation; it reproduces
what an Apple Log 2 file carries (a log encoding of scene reflectance), but it
does not reproduce an iPhone 17 Pro sensor's noise, clipping or upstream colour
processing.
"""

from __future__ import annotations

import os
import numpy as np
from PIL import Image

import look as L
from colorlib import apple_log_encode, apply_matrix, M_709_TO_AWG

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROJ = os.path.join(ROOT, 'GOLDEN_DAYLIGHT_CINEMA')
SRC = os.path.join(PROJ, 'SCENES', 'source')

SCENES = [
    ('01_harsh_midday_city', 'src01_harsh_midday_city.jpg',
     'HARSH MIDDAY CITY',
     'Hard 1pm sun down a city avenue: glass and concrete facades, deep awning '
     'shadow on the left, blue sky above the roofline.'),
    ('02_midday_portrait', 'src02_midday_portrait.jpg',
     'MIDDAY PORTRAIT IN DIRECT SUN',
     'Hard midday sun on a face against a sunlit stone wall, shadow side still '
     'open, deep shadow behind the shoulder.'),
    ('03_mediterranean_street', 'src03_mediterranean_street.jpg',
     'MEDITERRANEAN STREET',
     'Narrow street of honey limestone, shuttered doorways, terracotta pots and '
     'a strip of blue sky between the buildings.'),
    ('04_beach_daylight', 'src04_beach_daylight.jpg',
     'BRIGHT BEACH DAYLIGHT',
     'Backlit sea and sand at midday with the sun in frame: specular whites, '
     'spray, turquoise shallows and cloud at the horizon.'),
    ('05_natural_landscape', 'src05_natural_landscape.jpg',
     'NATURAL LANDSCAPE WITH GREENERY AND MOUNTAINS',
     'Mountain ridge, dense green slope, dry grass in the foreground, cumulus '
     'and blue sky.'),
    ('06_golden_hour', 'src06_golden_hour.jpg',
     'GOLDEN-HOUR LANDSCAPE',
     'Low sun over a valley, backlit olive tree, dry ground, warm clouds and '
     'lens flare.'),
    ('07_modern_architecture', 'src07_modern_architecture.jpg',
     'MODERN ARCHITECTURE',
     'White concrete cantilever against a clean blue sky, a large glass wall '
     'reflecting sky and clouds, hard shadow edges.'),
    ('08_travel_cinematography', 'src08_travel_cinematography.jpg',
     'OUTDOOR TRAVEL SCENE WITH PEOPLE AND BUILDINGS',
     'Wide 2.38:1 piazza with a fountain, arcaded buildings, crowds in mixed '
     'clothing colours and strong ground shadows.'),
]


def load_source(fn, width=1600):
    """Load a source still as an (H, W, 3) float array of Rec.709 display code.

    The stills keep their own aspect ratio (16:9 for scenes 01-07, 2.38:1 for
    scene 08) and are only resampled to `width`; nothing is cropped, so the
    composition of every BEFORE/AFTER pair is the source composition.
    """
    im = Image.open(os.path.join(SRC, fn)).convert('RGB')
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return np.asarray(im, dtype=np.float64) / 255.0


def plate_for(slug, width=1600):
    """Deterministic simulated Apple Log 2 plate for a scene slug."""
    fn = dict((s[0], s[1]) for s in SCENES)[slug]
    return simulate_apple_log2(load_source(fn, width))


def simulate_apple_log2(code, exposure_stops=0.0):
    """Rec.709 display code -> simulated Apple Log 2 code in Apple Wide Gamut.

    display code -> scene reflectance (inverse neutral tone curve)
                 -> exposure offset (optional)
                 -> Rec.709 linear -> Apple Wide Gamut linear
                 -> Apple Log / Log 2 encode -> 10-bit quantisation
    """
    R = L.code_to_reflectance(code)
    if exposure_stops:
        R = R * (2.0 ** exposure_stops)
    awg = apply_matrix(R, M_709_TO_AWG)
    # Apple Wide Gamut can encode negative light on the low branch of the
    # curve; clip only what the encoder cannot represent at all.
    P = apple_log_encode(np.maximum(awg, -0.009))
    return np.round(np.clip(P, 0.0, 1.0) * 1023.0) / 1023.0
