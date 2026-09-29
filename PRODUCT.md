# LSEmap

<!-- impeccable:product-schema 1 -->

## Platform

web

## Product Purpose

Build a browser-based model of the LSE campus, with free exploration, individually
inspectable buildings, exterior details and evidence-supported interiors. The
user's goal is the complete campus, not merely a gallery of isolated room samples.
Publish reviewed source and display assets to Haoran-Xu-0316/LSEmap and Cloudflare
when release is requested. Local development and a verified public release are
separate deliverables.

## Users and Interaction

Assumption: people viewing the user's architectural work on desktop or mobile.
Orbit, pan, zoom, select a building, inspect its exterior and switch to available
interior studies. Pair the building code with its name. Preserve free exploration;
do not turn the experience into a mandatory guided sequence.

## Current Verified Baseline

Edition 30 is the local source and release candidate; the last verified public release remains edition 24. It contains 31 catalogue records,
30 exterior models and partial interiors in 25 buildings: five public-space studies
and twenty-four room samples, including independent classrooms in Marshall, CBG
and CKK. Fifteen room samples were added in edition 20, with exterior repairs
to KSW, 50L, 51L and SAR. All 73 website gallery views use the production CampusViewer and exported GLBs.
The build checks renderer, camera-preset and exported-model digests. Native Cycles
renders are retained only for offline comparison.
The viewer approximates Cycles finishes with self-hosted real-time materials.
Detailed geometry loads on demand; the overview retains the exterior construction
but omits sub-centimetre finishing and uses simpler shading.

The previous edition-24 build validates 182 deployable files. All 92 local checks passed for that edition
after updating legacy gallery counts, interior availability and a viewer fixture.
The two online parity checks are opt-in and recorded separately from local tests.
Existing edition-23 model asset hashes are unchanged and
4044 native meshes are preserved. These checks do not establish measured fidelity.
Deployment status is established separately by the hosting receipt and live
release manifest. Compare every referenced asset hash before claiming online parity.

Edition 21 adds OCS's historical retail cutaway and library reading/collection
areas over six relative levels. Section controls isolate a level without modifying
the source model. The highest section stops below the roof deck to expose the
reading area. Six-level attribution follows the library guide; absolute elevations
and plan registration remain estimated. Roboto is served with the site.

Edition 22 adds MAR.1.04 from the matching official room photo and 90-seat plan.
Its estimated dimensions and seat positions remain separate from the Grand Hall;
no measured connection or current full-floor reconstruction is claimed.

Edition 23 adds CBG.1.02 and CKK.1.04 from matched historical room plans and
photographs. CBG uses seven six-seat groups. CKK has 80 seat symbols; floor
height differences are not established, so the room uses a flat-floor study.
Both preserve their buildings' existing atria and carry explicit scope limits.

Edition 24 adds the 2021 reception at 61 Aldwych and the photographed 2014
Denning café corner at SAW. These are isolated historical studies; neither
establishes current use, a whole floor, or measured connections to the shell.

Edition 25 refines MAR upper fins and the northern terrace with photo-guided paving,
guards and three planted containers. Only those two existing mesh geometries change;
4150 original meshes are preserved and nine exterior mesh groups are added.
Terrace heights, paving modules and planting positions remain estimates. The web
viewer uses pale warm concrete and blue-grey glazing under neutral lighting, with
restrained stone grain and differentiated glass/metal finishes across buildings.
These are visual approximations, not calibrated source albedos.

Edition 26 moves the MAR, SAW and CBG exterior palette into native source
materials. CBG uses the user-requested red main blade faces and orange returns.
All 4161 mesh geometries are preserved. Glass opacity is carried explicitly into
web exports; public-space glass inherited from exterior collections may therefore
change appearance, while independent teaching-room geometry remains unchanged.

## Completion Requirements

The user accepts missing interiors when a bounded source search finds no usable
evidence. The delivered scope is an evidence-supported campus study; a fully
measured reconstruction would additionally require evidence for:

- Every campus record's identity, footprint and construction status.
- Each building's exterior proportions, openings, entrances, roof and visible
  elevations, with unresolved or inferred geometry explicitly identified.
- Supported interior coverage beyond isolated room samples, including the spatial
  relationships and levels that available plans and photographs establish.
- Working desktop and mobile exploration, entry links, selection, interior controls,
  resource loading and recovery after failures.
- A consistent native model, web exports, thumbnails, gallery and release manifest.
- A reviewed complete release with verified GitHub inclusion and live asset parity
  when publication is requested.

There is no verified complete interior survey. Missing internal evidence is not
permission to fabricate rooms or label an entire building complete. Conceptual
layouts require a distinct presentation and an explicit user decision.

## Known Gaps

61A is confirmed LSE property; the model boundary and adjoining geometry remain uncalibrated. 35L is a construction-site representation,
not a completed future design. LCH, POR, 50L, 51L and SHF have no published
interior model in edition 24. Existing room samples represent historical or partial
observations, not current floor-by-floor coverage. Unseen elevations, dimensions
and some roof geometry remain estimated. PEA's 108 modelled front seats are not
its total venue capacity. The 49L/50L envelope follows the 2022 architectural block
plan and does not establish current tenancy boundaries.

Use BUILDING_STATUS.md and source manifests to track the actual scope. A successful
load, screenshot or green test alone cannot close an architectural evidence gap.

## Asset and Workflow Constraints

This is an independent architectural study, not an official map or route planner.
Keep original photographs, PDFs, credentials, private local paths and editable
Blender archives out of the public repository and deployment. Preserve the private
research archive and prior model editions. No external API or account is required
at runtime. Host runtime dependencies locally.

The user prioritizes conserving Codex quota. Existing subagent work is integrated
and stopped; do not create further agents for routine research or small changes. Avoid repeated rendering or deployment without
new changes requiring it. When pushing, stage an explicit allowlist and use a
separate descriptive English commit for each included file.

Gallery and live-view parity: thumbnails and enlarged images share content-hashed
URLs. A renderer or model change requires regeneration through `npm run gallery`;
All 27 exterior overview images have foreground-pixel comparisons against the
live canvas. Fixed-name model URLs also use the exported-asset digest, so a
re-export under the same native model cannot silently reuse old cached geometry.

Edition 27 refines SAL brick toward the archived red stock-brick appearance,
reduces OLD stone yellow cast, and distinguishes KGS entrance granite from the
upper stone bays. It preserves all 4161 mesh geometries and all interior assets.
CLM entrance tone was reviewed against the LSE Estates photograph and retained.
These are photo-guided material studies, not calibrated reflectance measurements.

Edition 28 repairs degenerate roof UVs on OLD and SAL and replaces ochre joints
with dark slate joints. Roof massing and tile dimensions remain approximate.
Orbit controls now permit the full polar range in overview, exterior, detail and
interior views, with unrestricted horizontal orbit. This candidate is local only.

Edition 29 restores missing metric UVs on seven KSW brick meshes. The source red
brick palette was already present; the browser had been sampling the mortar alone.
Procedural brick now filters subpixel courses toward an area-weighted average, and
sun-shadow depth bias suppresses broad roof acne. Model geometry is unchanged.
CLM/COL/CON/LRB reference review remains partial; this is not full-campus accuracy acceptance.

Edition 30 separates CON's lower granite from upper limestone on the documented
street facade. The material boundary is estimated at 3.12 m using the door and
fanlight proportions. Lower ashlar grooves are removed; room studies remain
unchanged. This improves the entrance presentation, not a surveyed whole building.

Edition 31 replaces LRB's flat truncated roof light with a curved metal dome and
a north-facing inclined glazed aperture, based on the archived aerial and LSE's
own description. Dimensions and seam spacing remain visual estimates. The
2024/25 Estates report confirms new rooftop heat pumps; their present arrangement
is not inferred from the older aerial. Other exteriors and interior structures are preserved; LRB interior exports
share the updated exterior roof. This local refinement does not establish whole-campus completion.

Edition 32 reconstructs CKK's Lincoln's Inn Fields mansard with two rows of
dormers, slate courses, zinc cheeks, caps and cornice. The existing east roof
block is replaced; all interior structures and unrelated buildings are preserved.
Geometry follows the archived architectural photograph, with estimated dimensions.
The rear roof pavilion and street facade still need work. The 2025/26 Estates
works plan lists Cafe54 refurbishment; the older interior is not claimed as its
post-refurbishment layout. This candidate remains local.

Edition 33 replaces CKK's generic east-facing window grid with the photographed
three-part elevation: three narrow bays at each side and five central bays,
rusticated lower storeys, a semicircular fanlight, paired portal columns and a
projecting dentil cornice. The older front geometry is trimmed, not overlaid.
The model keeps edition 32's mansard and all interior assets. East-facing default
and entrance cameras use the same exterior asset; two gallery views are added.
Dimensions are visual estimates. The rear pavilion, detailed carving, current
signs and post-refurbishment cafe layout are not represented as verified.

Edition 34 cuts the existing 977 pane openings through 29 legacy rectangular
wall sheets in CKK, LRB and CON. Previously the glass backs coincided with solid
wall faces, producing depth interference when viewed from inside the envelope.
A shadow-disabled comparison confirmed this was geometry interference. Window
positions, glazing, frames, palettes and public-interior geometry are preserved.
The 8 mm clearance remains beneath the existing jamb overlap; it is a rendering
repair, not a newly surveyed window dimension.

Edition 35 reconstructs the LRB frontage along the documented John Watkins Plaza
edge with wider multi-pane windows, pale floor bands, a local stone-faced section
and warm brown brick. The previous generic window grid is removed on this edge.
The reference was taken on 23 January 2008 facing approximately 112 degrees;
bay count, dimensions and portal position remain estimates. The 2025 turnstile
replacement plan is recorded without inventing its completed configuration.
Other elevations, the roof and public interiors are preserved. A plaza-facing
default camera and matching exterior gallery image are added.

Single-building geometry reviews now include the production exterior's public
interior objects through `export_review_model.py`. This exposes slab/facade
collisions before the full export; source procedural colours still require the
production material conversion. The LRB facade was offset 0.16 m to separate its
glass backs from the existing slab perimeter, retaining the interior geometry.

Edition 36 removes 20 generic shelf modules from the LRB G-layer study where
the official floor guide identifies learning and service zones. The source PDF
was checked on 2026-09-29 and matches the archived file byte for byte. Existing
plan-derived learning furniture is retained. Absolute floor elevations, atrium
alignment, service counters and enclosed rooms remain incomplete.

Edition 37 places the estimated LRB G floor at Z0.32 and LG at Z-3.68.
Floor plates, ramp, furniture and floor sections move together; continuous
columns and lift guides retain their roof/shaft endpoints. The exterior
export clips only temporary underground interior geometry at Z0; the
interior retains LG. Four-metre floor spacing is an estimate, not a survey.
Horizontal atrium alignment and fifth-floor staff space remain incomplete.

Edition 38 registers the LRB core approximately 5.96m east and 0.73m south
using three official guide floor images and four GIS outline correspondences.
Floor and roof openings are retriangulated with the outer footprint fixed.
The ramp, lifts, supports, landings and dome move together. Eighteen conflicting
legacy shelf modules are removed; guide-derived furniture is retained. The
9.8m circular opening remains an approximation; floor-specific opening outlines
and room boundaries are still incomplete. Registration checks are not a survey.

Edition 39 changes only Clement House exterior glass tint, reducing its blue-green
cast to a restrained neutral grey. The colour is a visual estimate from the
archived daylight portal photo. Existing Portland-stone and bronze-frame
finishes, geometry and all interiors are retained. Rooftop AC/ductwork consent
24/03808/FULL and 24/03809/LBC does not establish the current built arrangement.

Edition 40 corrects Clement House horizontal cornices to follow the convex GIS frontage. Eleven existing profiles use shared miter connections; profile dimensions remain estimated. Interior layouts and other buildings are unchanged.

Edition 41 reduces the unsupported cyan cast in COL and CON exterior glazing, including the legacy CON side bays. Existing geometry and interiors are preserved. Tint is a photographic estimate, not a measured specification.

Edition 42 rebuilds the LCH street facade from a 2025 LSE photograph and the listed-building description: central arched and tripartite windows, canted bays and wider shop glazing. The retained porch and entry view move together. Dimensions, frontage registration and roof remain estimates; no interior is added.

Local edition43 replaces LCH shopfront opaque risers with recessed lower lights, pale splayed frames and metal grids, based on the 2022 Ian Wood photograph. Dimensions remain estimated; interiors are unchanged.

Edition43 also applies a shared glass finish across campus, building and gallery views: modest tint desaturation at constant luminance, dielectric reflections and bounded roughness. Source transparency is preserved; the change does not claim surveyed glazing specifications.
