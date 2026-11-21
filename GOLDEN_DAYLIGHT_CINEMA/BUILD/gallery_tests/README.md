# Gallery tests

The gallery is a single self-contained `GALLERY/index.html` with no framework
and no external requests, so it can be exercised without a network.

A real browser could not be installed in the environment where this was built
(Playwright's Chromium download is blocked), so the gallery is tested against a
DOM implementation instead. That verifies structure and behaviour — element
construction, event wiring, state transitions, ARIA — but **not** pixel
rendering or iOS Safari's own quirks. This limitation is stated in
`VALIDATION_REPORT.txt`.

## Run

```bash
npm install jsdom
node gallery_dom_test.mjs        # 23 checks: cards, images, sliders, ARIA,
                                 # lightbox, contact sheet, download link,
                                 # viewport, touch targets, safe-area
node gallery_lightbox_test.mjs   # 11 checks: iOS scroll lock/unlock, backdrop
                                 # tap closes, image tap does not, notes
```

Both exit non-zero on failure.

## What is deliberately covered

- every `src` in the document resolves to a file that exists
- the divider responds to keyboard input (jsdom has no pointer capture)
- the lightbox opens, renders the AFTER layer, navigates, toggles and closes
- scroll lock is applied and released on every close path, including Escape
- tapping the backdrop closes; tapping the image does not
- all interactive targets are at least 44 px
- `touch-action: pan-y`, reserved aspect ratio, `env(safe-area-inset-*)`
- no duplicate element ids, no external hosts, no external scripts
