# Legacy / superseded material

Nothing in this folder is part of the deliverable. It is kept only so that
earlier work is not lost.

This repository was built across several separate working sessions. Earlier
sessions each produced their own build pipeline and their own version of the
LUT. The final, shipped work is the one in the repository root:

* `GOLDEN_DAYLIGHT_CINEMA/` — the deliverable
* `GOLDEN_DAYLIGHT_CINEMA.zip` — the packaged deliverable
* `scripts/` — the pipeline that produced it

When the final branch was merged, the older material was moved here rather
than deleted.

## What is in here

| Path | What it was |
|---|---|
| `scripts/` | The earlier build pipeline (`build.py`, `color.py`, `color_pipeline.py`, `validate_lut.py`, `verify_renders.py`, and friends). Superseded by the root `scripts/`. |
| `source/` | An earlier session's self-contained build and validation folder, including its own research notes. |
| `source_images/` | JPEG source stills used by an earlier pipeline. |
| `source_plates/` | PNG source plates used by an earlier pipeline. Previously `sources/plates/`. |
| `BUILDING.md` | Build instructions for the earlier pipeline. |
| `previews_superseded/` | Eight BEFORE/AFTER PNGs rendered with an **earlier version of the LUT**. |

## Why `previews_superseded/` had to be moved out of the deliverable

Those eight pairs were rendered by a `.cube` that is no longer shipped. Leaving
them inside `GOLDEN_DAYLIGHT_CINEMA/PREVIEWS/` would have broken a hard
requirement of this project: **every AFTER image in the deliverable must be
produced by the delivered `.cube`.** They survived the merge only because their
filenames differ from the current scene names, for example
`01_harsh_midday_city_*` versus the current `01_midday_city_*`.

Validation re-renders all eight current AFTER previews from the shipped `.cube`
and confirms they are bit-identical; see `GOLDEN_DAYLIGHT_CINEMA/VALIDATION_REPORT.txt`,
section 9.

## Source material

The current pipeline uses the eight plates in `sources/` with provenance in
`sources/CREDITS.md`. The images in `source_images/` and `source_plates/` here
are earlier, differently-named sets for the same eight scene briefs.
