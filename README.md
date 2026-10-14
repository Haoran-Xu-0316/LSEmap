# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition200 contains31 building records,30 detailed exteriors,25 interior views
and17 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v200.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All129 gallery images use the
production viewer and are checked against model and renderer signatures.

Two newly selectable rooms extend the interior collection: OLD.3.21 has four
8-seat groups; MAR.1.07 has16 seats around a U and4 central seats. Both use
paired official historical plans/photos, independently isolated from the campus
scene. Plan arrangements and photographed teaching finishes are retained;
metric scale, hidden construction and some photo-to-plan registration are estimates.

All edition199 campus, building and prior room assets retain their checksums.
The refined landscape, mapped context finishes, continuous road network and
static daylight remain in place. The private CBG roof candidate stays excluded:
a separately scaled2016architect plan shows an approximately6m structural grid,
whereas the inherited model uses about8.17m. Design-stage drawings alone do not
establish current built dimensions or justify silently resizing the campus.

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
