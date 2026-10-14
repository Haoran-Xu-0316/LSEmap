# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition199 contains31 building records,30 detailed exteriors,25 interior views
and15 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v199.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All127 gallery images use the
production viewer and are checked against model and renderer signatures.

The landscape refines510 previously coarse crown masses while retaining all522
crown envelopes, centres and tree positions. Earlier Watkins/Houghton refinements
remain intact. One opaque batched canopy adds122,400 triangles, with no new
textures, alpha leaf cards, trees or animation.

Twenty-four surrounding context buildings gain13 wall/roof finishes from
singular archived mapped material/colour attributes. Their existing world faces
remain exact; no windows or facade details are invented. Mixed or absent tags
keep their previous finish. Numeric colours and standard brick coursing are
presentation estimates, not a current photographic survey.

The original park black patch was traced to downward grass faces. Orientation
repair corrects120 ground objects without changing coordinates, coverage or
corner UVs; native before/after renders verify the patch is gone.

Every LSE exterior and interior asset retains its edition198 checksum. The
continuous road network and clearer static daylight remain in place. Nine
archived pedestrian centre lines totalling280.681m were checked against current
paving without finding evidence for a new broad route expansion.

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
