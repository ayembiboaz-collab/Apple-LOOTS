"""
gdc_config.py -- scenes, sources, credits.

Every image is a real-world photograph (no AI generation, no upscaling).
Source metadata was read from Unsplash's public photo API on 2026-11-22
(photographer, camera EXIF, premium flag) and is reproduced in SOURCES.txt.

Licence: Unsplash License (https://unsplash.com/license).  It grants the right
to download, copy, modify, distribute and use the photos for free, including
commercially, without permission or attribution.  It forbids selling unmodified
copies and building a competing photo service; neither applies here.  We credit
every photographer anyway.

`prompt` fields are only used for image-search provenance notes.
"""

from __future__ import annotations

from dataclasses import dataclass

REPO_RAW_BASE = "https://raw.githubusercontent.com/ayembiboaz-collab/Apple-LOOTS/arena/482cfc1a-apple-loots"
REPO_BLOB_BASE = ("https://github.com/ayembiboaz-collab/Apple-LOOTS/blob/arena/482cfc1a-apple-loots")
PROJECT_DIR = "GOLDEN_DAYLIGHT_CINEMA_PROJECT"


@dataclass
class Scene:
    key: str
    number: int
    title: str
    subtitle: str
    description: str
    file: str                 # file name inside source_images/
    unsplash_url: str
    unsplash_id: str
    photographer: str
    photographer_url: str
    location: str
    camera: str
    exif: str
    published: str
    licence: str = "Unsplash License"
    licence_url: str = "https://unsplash.com/license"
    download: str = ""
    modifications: str = ""
    exposure_note: str = ""


SCENES: list[Scene] = [
    Scene(
        key="midday_city", number=1,
        title="Harsh midday city",
        subtitle="Blue sky, hard shadows, bright façades",
        description=("Downtown Oklahoma City at midday: a saturated blue sky, sunlit "
                     "glass and concrete, and deep architectural shadows in the "
                     "street. The test is whether the sky stays natural while the "
                     "sunlit stone gets honey warmth and the shadows keep detail."),
        file="01_midday_city.jpg",
        unsplash_url="https://unsplash.com/photos/city-buildings-under-blue-sky-during-daytime-QGP7ncFD0LA",
        unsplash_id="QGP7ncFD0LA",
        photographer="Justin Prine",
        photographer_url="https://unsplash.com/@justinp3",
        location="Oklahoma City, United States",
        camera="DJI FC3170",
        exif="1/800 s, f/2.8, ISO 100, 4.5 mm",
        published="2020-07-11",
        download="https://images.unsplash.com/photo-1594480355356-8b9833059231?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Bright daylight, clipped specular sky highlights in the source.",
    ),
    Scene(
        key="midday_portrait", number=2,
        title="Midday portrait in direct sun",
        subtitle="Hard light on skin, deep shade beside it",
        description=("A portrait made at f/1.8 in direct midday sun, 1/6400 s at ISO 125. "
                     "Half the face sits in the hard shadow of a wall. This is the "
                     "hardest skin test in the set: the lit side must stay natural, "
                     "not orange, and the shadow side must not go muddy or cyan."),
        file="02_midday_portrait.jpg",
        unsplash_url="https://unsplash.com/photos/a-woman-with-a-shadow-on-her-face-qSYohksKbiI",
        unsplash_id="qSYohksKbiI",
        photographer="Elle Cartier",
        photographer_url="https://unsplash.com/@ellecartier",
        location="Bellingham, WA, United States",
        camera="Sony ILCE-7M3",
        exif="1/6400 s, f/1.8, ISO 125, 24 mm",
        published="2024-11-21",
        download="https://images.unsplash.com/photo-1732129606581-e887b3651a20?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Direct sun on skin plus a two-stop shadow side: real exposure variety.",
    ),
    Scene(
        key="mediterranean_street", number=3,
        title="Mediterranean street",
        subtitle="Whitewash, bougainvillea, blue railings",
        description=("A Mykonos alley shot on an iPhone 11 Pro: whitewashed walls in "
                     "sun and shade, bougainvillea, painted blue woodwork. Whites must "
                     "stay believable while the stone picks up warmth and the shade "
                     "stays clean and slightly cool."),
        file="03_mediterranean_street.jpg",
        unsplash_url="https://unsplash.com/photos/a-narrow-street-with-white-buildings-and-blue-balconies-SvS4pQBjJKQ",
        unsplash_id="SvS4pQBjJKQ",
        photographer="Julien Gaillard",
        photographer_url="https://unsplash.com/@juuxx",
        location="Mykonos, Greece",
        camera="Apple iPhone 11 Pro",
        exif="1/858 s, f/1.8, ISO 32, 4.2 mm",
        published="2022-06-04",
        download="https://images.unsplash.com/photo-1654349203022-b940af6f4df3?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Portrait orientation kept; hard sun and deep shade in one frame.",
    ),
    Scene(
        key="beach_daylight", number=4,
        title="Bright beach daylight",
        subtitle="Sand, turquoise sea, white surf",
        description=("Mid-morning beach with a bright sky and a shallow turquoise "
                     "shallows. The look must not turn the sea cyan-turquoise, must "
                     "keep the sand warm rather than yellow, and must not blow the "
                     "surf detail that survives in the source."),
        file="04_beach_daylight.jpg",
        unsplash_url="https://unsplash.com/photos/a-sandy-beach-with-clear-blue-water-on-a-sunny-day-6BzelJ-qVe0",
        unsplash_id="6BzelJ-qVe0",
        photographer="Francesco Ungaro",
        photographer_url="https://unsplash.com/@francesco_ungaro",
        location="not recorded by the photographer",
        camera="Fujifilm X-T4",
        exif="1/4000 s, f/4.5, ISO 400, 9.6 mm",
        published="2023-06-27",
        download="https://images.unsplash.com/photo-1687875423812-41b0143bcff2?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Bright, high-key daylight; surf detail is at the top of the source range.",
    ),
    Scene(
        key="landscape_green", number=5,
        title="Green valley and mountains",
        subtitle="Foliage, pasture, alpine rock",
        description=("An alpine valley with saturated pasture, dark conifers and a "
                     "limestone ridge under a blue sky with cumulus. Foliage must stay "
                     "green (not radioactive yellow-green, not teal) and the distant "
                     "ridge must not turn muddy."),
        file="05_landscape_green.jpg",
        unsplash_url="https://unsplash.com/photos/a-green-valley-with-trees-and-mountains-in-the-background-S_kzomYltgo",
        unsplash_id="S_kzomYltgo",
        photographer="Francesco Ungaro",
        photographer_url="https://unsplash.com/@francesco_ungaro",
        location="not recorded by the photographer",
        camera="DJI FC3170",
        exif="1/730 s, f/2.8, ISO 100, 4.5 mm",
        published="2024-07-24",
        download="https://images.unsplash.com/photo-1721834193014-540c249888c2?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Balanced daylight with both deep conifer shadow and bright cloud.",
    ),
    Scene(
        key="golden_hour", number=6,
        title="Golden hour landscape",
        subtitle="Low sun through a gap in the cloud",
        description=("A Czech valley five minutes before the sun leaves it, shot at "
                     "0.5 s, f/22, ISO 100. Already extremely warm. This is the test "
                     "that the look does not double-warm an image that is already "
                     "golden: the split tone has to back off as the source gets warm."),
        file="06_golden_hour.jpg",
        unsplash_url="https://unsplash.com/photos/mountains-and-tree-range-during-golden-hour-8c6eS43iq1o",
        unsplash_id="8c6eS43iq1o",
        photographer="Artem Sapegin",
        photographer_url="https://unsplash.com/@sapegin",
        location="Hřensko, Czechia",
        camera="Canon EOS 6D",
        exif="0.5 s, f/22, ISO 100, 39 mm",
        published="2017-03-28",
        download="https://images.unsplash.com/photo-1490682143684-14369e18dce8?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Intrinsically warm, backlit, very high dynamic range.",
    ),
    Scene(
        key="modern_architecture", number=7,
        title="Modern architecture",
        subtitle="Brutalist grid, concrete and glass",
        description=("A rhythmic concrete façade in Tirana, lit hard from one side. "
                     "Concrete must stay concrete: warm grey with earth in it, not "
                     "beige-yellow, and the deep window recesses must hold detail."),
        file="07_modern_architecture.jpg",
        unsplash_url="https://unsplash.com/photos/modern-building-with-geometric-facade-and-blue-windows-w-nBFVS928I",
        unsplash_id="w-nBFVS928I",
        photographer="Aldo Vukaj",
        photographer_url="https://unsplash.com/@mystical1",
        location="Tirana, Albania",
        camera="Nikon D5300",
        exif="1/500 s, f/5.6, ISO 250, 55 mm",
        published="2026-03-23",
        download="https://images.unsplash.com/photo-1774276982082-629a21fc321e?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Mostly neutral, low-chroma subject: the hardest test for a warm tint.",
    ),
    Scene(
        key="travel_people", number=8,
        title="Travel street with people",
        subtitle="Dubrovnik, late afternoon",
        description=("A pedestrian street in Dubrovnik with people walking towards the "
                     "camera, warm stone on the right, blue shade on the left. Skin at "
                     "small scale, stone at large scale, all in one frame."),
        file="08_travel_people.jpg",
        unsplash_url="https://unsplash.com/photos/a-group-of-people-walking-down-a-street-next-to-tall-buildings-TZuigM9Cs9I",
        unsplash_id="TZuigM9Cs9I",
        photographer="Kevin Charit",
        photographer_url="https://unsplash.com/@kevin_charit",
        location="Dubrovnik, Croatia",
        camera="Fujifilm X-E3",
        exif="1/800 s, f/8, ISO 400, 18 mm",
        published="2021-09-20",
        download="https://images.unsplash.com/photo-1632154613105-f2f151eec778?fm=jpg&q=85&w=3000",
        modifications="Resized to 2048 px long edge (Lanczos), no crop.",
        exposure_note="Mixed sun and shade, small skin areas, large stone areas.",
    ),
]

SCENE_BY_KEY = {s.key: s for s in SCENES}

#: the eight scenes in gallery order
ORDER = [s.key for s in SCENES]

#: resolution of the deliverable previews (long edge, px)
PREVIEW_LONG_EDGE = 2048
#: resolution used for the numerically heavy validation work
ANALYSIS_LONG_EDGE = 1024
