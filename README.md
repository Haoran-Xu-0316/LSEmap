# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition196 contains31 building records,30 detailed exteriors,25 interior views
and13 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v196.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All125 gallery images use the
production viewer and are checked against model and renderer signatures.

This edition harmonises LRB's brick, mortar and painted frames, corrects its
raised roof enclosure to photograph-supported dark grey, and reduces the
milky glazing tint. CLM's street stone and window frames receive consistent
neutral finishes while existing glazing opacity and geometry are retained.

The registered historical OLD entrance foyer gains stone slab joints, a dark
ribbed entrance mat and pale illuminated disc lamps. Its original steps,
threshold, walls and room registration remain intact. This is a refinement of
the documented2011 layout, not a claim of a new current floor survey.

The viewer uses a self-hosted CC0 sky and two shared512px ground captures.
Road finishes add123,528 bytes without extra geometry or render passes.
Lossless gzip segments reduce first-load transfer; one verified browser cache
replaces the previous campus edition. Optional asset or storage failures retain
the normal lighting, procedural surface and network fallbacks.

Geometry, weathering and optical values remain photographic or plan-based
estimates. Many references are historical or undated. Complete current room
layouts, unseen elevations and full-campus as-built fidelity remain unfinished.

## Project files

`web/src` owns the browser viewer, controls, materials and loading.
`web/tools/building-metadata.json` selects the current native edition and records
building/room identities, camera presets and evidence scope.
`web/tools/export_scene.py` creates the compact browser models without saving
changes to the native source. Only explicitly approved packed maps enter exports.
`web/tools/render_web_gallery.mjs` renders the full gallery with that same viewer.
`web/tools/prepare_release.mjs` and `check-assets.mjs` verify release references,
sizes, hashes and gallery parity. [DEPLOYMENT.md](DEPLOYMENT.md) documents the
verified Cloudflare deployment and live acceptance checks.

Official LSE, architect and user-supplied references stay in the local evidence
archive. The browser does not redistribute those photographs. Asset credits and
self-hosted font licences are included with the release.
