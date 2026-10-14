# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition198 contains31 building records,30 detailed exteriors,25 interior views
and15 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v198.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All127 gallery images use the
production viewer and are checked against model and renderer signatures.

The street network now dissolves397 overlapping road strips into one continuous
watertight mesh. This removes6,562.809 square metres of duplicate coplanar
coverage while retaining the original estimated street boundaries and23 holes.
All building and room assets remain byte-identical to edition197.

A clearer CC0 daylight panorama replaces the previous sky, reducing its download
by342,463 bytes. Downward building studies use the neutral background; near-level
street views reveal the sky with a small hysteresis band to prevent switching
flicker. Background and glazing reuse one static PMREM texture.

Asphalt and stone retain the shared512px captured colour/height/roughness maps.
World-metre sampling, mipmaps and distance filtering resolve their fine finish
without adding separate render passes. Optional loading failures retain the
startup environment and procedural road finishes.

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
