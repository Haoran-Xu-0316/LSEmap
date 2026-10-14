# LSEmap

An interactive architectural study of the London School of Economics campus.

[Explore the campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current model

Edition205 contains31 building records,30 detailed exteriors,25 interior views
and17 independently selectable room studies. The complete editable campus is
kept locally at `result/blender/LSE_campus_detailed_v205.blend`. GitHub contains
the current browser models, presentation assets and authoring/export scripts.

The overview and selected-building views share authored exterior objects,
finishes and public structural elements. All129 gallery images use the
production viewer and are checked against model and renderer signatures.

OLD’s Clare Market Student Services entrance now has the broad recessed blue
portal lining visible in the supplied photograph, surrounding a narrower glazed
entrance. Joinery, pulls and signage move together. The original opening, landing,
ordinary glazed bays and Houghton arch are retained. Proportions and recess depth
remain photographic estimates; blue paint and glass finishes are inherited.

LCH now has the seven-position street elevation visible in the official photograph publishedSeptember2025: two narrow sash columns in each brick field, with a black downpipe
between them. Actual wall openings replace the previous single columns. Central
and projecting bays, entrance and lower white panels are retained.

51L’s opaque glass proxies now use a restrained neutral dielectric finish.
All101pane shapes and the photographed window arrangement are retained; no
verified full interior exists, so transparency remains deliberately limited.

All previous room studies and other building assets retain their checksums.
CBG now uses an independently registered42m tower with8axes and7bays,
its stepped teaching wing and a two-storey amenity podium. Offices follow the
published2m glazing/1m opaque-leaf module. Roof terraces, folded canopies and
28 connected upper stair risers share one exterior/public-structure assembly.
World cameras follow the corrected footprint; four independent room studies
retain their original local spaces. Design-plan/photo dimensions and podium
height remain estimates, rather than a current as-built survey.

Lossless gzip segments reduce first-load transfer; one verified browser cache
replaces the previous campus edition. The outdoor renderer uses a sharp2048px photographic sky alongside independent
HDR reflections. Asphalt uses the source3m scale and shallow2mm presentation
relief; packed roughness/height data removes unnecessary download noise.
These CC0 materials are self-hosted and do not add animated clouds or scene meshes.

Optional asset or storage failures retain
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
