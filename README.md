# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition201 contains31 building records,30 detailed exteriors,25 interior views
and17 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v201.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All129 gallery images use the
production viewer and are checked against model and renderer signatures.

OLD’s Clare Market Student Services entrance now has the broad recessed blue
portal lining visible in the supplied photograph, surrounding a narrower glazed
entrance. Joinery, pulls and signage move together. The original opening, landing,
ordinary glazed bays and Houghton arch are retained. Proportions and recess depth
remain photographic estimates; blue paint and glass finishes are inherited.

All previous room studies and other building assets retain their checksums.
A separate built-photo review confirms8 major axes and7 bays across CBG’s tower
front; the inherited model has7 axes and6 bays. The structural engineer publishes
a6m×9m grid, corroborating the scaled2016architect drawing. Whole-envelope and
wing-junction registration must be reconciled before this structural correction
or the private roof candidate is released. Thirteen storeys are retained; facade
bands omitted within double-height spaces are not treated as missing floors.

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
