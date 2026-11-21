# Source image credits and provenance

All eight source stills in this folder were **generated for this project** with the
image-generation tool available in the Arena agent workspace. They are **not**
third-party photographs, and they are **not** iPhone captures.

* **Origin:** AI image generation, created 2026-11-21 specifically for
  GOLDEN DAYLIGHT CINEMA.
* **Why synthetic sources:** they give unambiguous provenance (no third-party
  licensing), and they let each of the eight required test conditions be hit
  exactly (harsh midday, direct-sun portrait, Mediterranean street, bright
  beach, greenery + mountains, golden hour, modern architecture, travel scene
  with mixed skin tones).
* **Prompting intent:** every prompt asked for a photorealistic, *ungraded,
  unfiltered, neutral* "straight out of camera" rendering with no colour
  grading, no filter and retained texture in highlights and shadows, so that
  the LUT — and not the source — is responsible for the look.
* **What they are not:** they are not photographs of real places or real
  people, they carry no real camera metadata, and they do not reproduce any
  real sensor's colour response.

| File | Scene |
|---|---|
| `01_midday_city.png` | Harsh midday city: bright limestone, blue sky, hard architectural shadows |
| `02_midday_portrait.png` | Midday portrait in direct sunlight, olive skin, white linen |
| `03_mediterranean_street.png` | Mediterranean old-town street, sun and open shade |
| `04_bright_beach.png` | Bright beach daylight, specular glare on water |
| `05_landscape_greenery.png` | Natural landscape, greenery and mountains |
| `06_golden_hour_landscape.png` | Golden-hour landscape (over-warming test) |
| `07_modern_architecture.png` | Modern concrete and glass (colour-cast test) |
| `08_travel_people_buildings.png` | Outdoor travel scene, mixed skin tones, warm stone |

All are 1376 × 768 px, 8-bit RGB PNG, interpreted as sRGB (IEC 61966-2-1) by
`scripts/simulate_log2.py`.
