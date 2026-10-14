# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition197 contains31 building records,30 detailed exteriors,25 interior views
and15 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v197.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All127 gallery images use the
production viewer and are checked against model and renderer signatures.

Roads gain captured asphalt and stone height/roughness, packed into two shared
512px lossless data textures totalling463,298 bytes. World-metre sampling aligns
relief with the existing colour finishes; mipmaps and distance filtering reduce
far-view shimmer. No extra road geometry or render passes are added. A missing
relief download retains the usable colour finish. The existing self-hosted CC0
daylight/cloud sky supplies the background and glazing reflections.

STC's documented white walls, painted frames, red-brown stair and grey entrance
receive consistent finishes. Geometry, art panel and glazing opacity remain.
Two isolated historical room studies add FAW.4.01 with30 seats and CLM.5.02
with120 seats, using paired official plans and photographs. These studies do
not appear at the campus origin or claim complete current floor layouts.

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
