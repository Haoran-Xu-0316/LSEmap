# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition 195 contains 31 building records,30 detailed exteriors,25 interior views
and 13 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v195.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The first overview and selected-building views use the same authored exterior
objects and finishes, including retained public floors, stairs and atria. All 125 gallery images are captured with the production viewer
and checked against the model and renderer signatures before release.

Edition 194 refined OLD's wall, arch and relief stone with one shared 512px
original finish map. It preserves existing geometry, blue frames and entrance
glazing. CBG's painted structure and red/orange blades use a dielectric coating,
and its neutral glazing reveals more of the retained interior. The red-primary
CBG palette follows the user's choice; contractor photographs predominantly
show pale broad blade faces and orange/gold returns.

Five main pedestrian surfaces receive corrected face orientation. Two existing
walking joins are brought flush over 2.0756m²; this is a local continuity repair,
not a claim that the entire campus road network has been resurveyed. Stone,
paint and louvers inside a historically named GLAZING collection now retain
an explicit opaque material role rather than receiving a glass finish.

Edition 195 refines KSW's brick, stone, painted frames, shopfront and timber
entry, and restores twelve missing upper sash mullions. COL's street-facing
stone, painted joinery, timber and glazing receive separate finishes. MAR was
reviewed without speculative geometry changes. Existing interior studies remain
unchanged.

The viewer uses a self-hosted CC0 sky after the campus is usable. Two shared
512px CC0 ground captures add asphalt wear and stone variation at world scale,
adding 123,528 bytes, no geometry and no extra render pass. Captured maps and
procedural finishes retain separate ownership, so authored stone maps remain
visible. Optional ground-download failures preserve the procedural fallback. Roads, paving
and greenery share distance-filtered finishes. Lossless gzip segments reduce
first-load transfer; a single content-verified browser cache replaces the
previous campus edition and avoids repeated model downloads. Storage or sky
failures retain the normal network and startup-lighting fallbacks.

Geometry, weathering and optical values remain photographic or plan-based
estimates. Many references are historical or undated. Current complete room
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
