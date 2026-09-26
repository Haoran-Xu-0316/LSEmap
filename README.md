# LSEmap

A browser-based exploration of the London School of Economics campus, built from
an independent Blender architectural study.

[Explore the live campus](https://lsemap.xhr0316.workers.dev/)

![Campus architectural model](web/public/images/campus.webp)

Explore the campus by orbiting, panning and zooming. Select a building directly or
search by its name/code. Detail panels open original model renderings, and twenty-nine
interior studies load on demand across twenty-five buildings: five public spaces and twenty-four historical room samples. The interface supports mobile screens,
keyboard navigation, reduced motion, shareable building links and a gallery
fallback when WebGL is unavailable. Thirty building models and twenty-nine interior
views progressively load native bevels and source-derived procedural materials.
The lightweight campus remains available while these assets download.
Fixed-name campus and interior downloads carry the catalogue source revision, so
returning visitors cannot combine a new catalogue with an older cached model.

Edition 08 locates Coopers (49L) and corrects the adjoining 50/50A envelope using
Rock Townsend’s 2022 block plan. A prior 50L footprint occupied the restaurant
corner; the two street studies now have separate, non-overlapping envelopes.
Coordinates are registered to the existing OCS outline and remain approximate.

Edition 07 develops the provisional 61A envelope with stone window bays, tall
pilasters, a recessed corner entrance, roof dormers and a hipped pavilion.
Its independent footprint attribution remains provisional; the reference is an
archived pre-redevelopment photograph, not a proposed LSE redesign.

Edition 06 adds the independently attributed 5LF townhouse, with sash windows,
a rusticated ground floor, entrance steps, forecourt railings and chimney stacks.
The official LSE address-map point falls inside OSM way/1184094775.
Heights and unseen elevations remain estimated.

Edition 05 adds first-pass street facades for COW, KGS, LAK, LCH, 50L, 51L, PAR,
PEA, PEL, POR, SAR, SHF and STC. Brickwork, sash windows, stone courses and
building-specific entrances replace generic envelopes. Cowdray gains a mansard
roof and dormers; Peacock gains its canopy and vertical theatre sign. These thirteen
studies are labeled separately from the fourteen previously detailed buildings.
Heights, window spacing, unseen elevations and roof depth remain approximate.
The LSE mark comes from the existing personal-site vector asset, with no affiliation
or endorsement implied.

Columbia and Connaught also include an **入口细节** camera preset for close inspection.
Isolated views hide other building labels and exclude hidden geometry from selection.

## Edition 24 historical interiors

61 Aldwych gains a separate reception study from three matching photographs in
the 2021 commercial brochure. SAW gains the photographed Denning Learning Café
corner from its 2014 occupants guide. Neither represents a current measured
interior; the café does not invent seating or computers outside the photograph.
Existing campus geometry is preserved.

## Edition 23 classroom extension

CBG.1.02 adds seven six-seat teaching tables, glazing, exposed ducts and acoustic
ceiling panels. CKK.1.04 adds an 80-seat classroom with long desks, red/black chairs
and arched glazing. Both remain separate from the existing public atria. Historical
plans and matching photographs support the studies; unmeasured dimensions and
CKK floor-height differences remain unverified.

## Edition 22 teaching-room extension

Marshall now includes MAR.1.04 as a second selectable interior, preserving Grand
Hall and the public stairs. The 90-seat teaching-room study follows matching LSE
photography and an official plan; dimensions and individual seat positions remain
estimated. Original campus geometry is retained.

## Edition 21 library and retail extension

OCS now includes an independent historical shoe-shop interior based on two
attributed Sanders photographs. The library adds reading and collection areas
across six relative levels, selectable through a floor section control. Original
geometry is preserved; source plans are undimensioned, the library atrium does
not exactly register to those plans, and absolute floor elevations remain
uncalibrated. These are partial architectural studies, not complete surveys.

The interface uses locally hosted Roboto. Public display assets remain separate
from private reference photos and native Blender archives.

## Edition 20 room and facade extension

Fifteen additional interior studies cover historical classrooms, Cowdray's seminar
hall, the Garrick and Coopers dining areas, a computer learning area, an entrance
stair, a media studio, a kitchenette, a staff apartment bedroom and Peacock's stage
with a partial audience area. Room dimensions remain estimated except identified
technical dimensions; no whole-building or current-layout claim is made.

KSW's stone portal, the 50L fanlight, 51L's canted entrance and SAR's arched street
windows replace the earlier conflicting geometry. Each has a close-up camera and
render. Every replacement is explicitly listed and all other native meshes are
checked against edition 19. The building directory can filter interior studies.

Gallery reuse is permitted only when evaluated geometry, materials, cameras and
lighting have matching render fingerprints; both the rendered source edition and
verified current model are recorded. UV values are compared to one-millionth-unit
precision to avoid insignificant reload noise; geometry and normals remain byte-exact.
Changed views are rendered again.
The current source and build target edition 24. Check the live `/release.json`
manifest to verify the deployed version and native source fingerprint.

## Edition 16

Edition 16 is preserved as an earlier release.
Cowdray House now includes detailed sash bars, dentil cornices, pitched dormers,
corner portal and chimney stacks. King's Chambers gains canted stone bays, a
ribbed lead dome and an arched entrance with its green sign. Both have an entrance
camera preset and original close-up rendering. Dimensions remain estimated.
Parish Hall also has a low entrance wing, four window groups, red tiled roof,
dormers, brick arches, gutters and basement railings. Its new entrance close-up
shows the separate portals and inscribed lintel.


## Cloudflare Workers deployment

The static Worker is named `lsemap`. After signing in with Wrangler, `npm run deploy`
builds and validates the site, then uploads `dist` to Cloudflare. Wrangler is pinned
in the project lockfile. The existing Cloudflare Pages settings below remain usable
for a separate Git-connected Pages deployment.

## Local preview

Requires Node.js 22.12 or newer.

```sh
npm ci
npm run dev
```

For the production build:

```sh
npm run build
npm run preview
```

## Cloudflare

The site is static, with no server, API key or external asset CDN. All runtime
models, images and decoders are included in `dist` after building.

**Cloudflare Pages with GitHub integration**

| Setting | Value |
|---|---|
| Repository | `Haoran-Xu-0316/LSEmap` |
| Production branch | `main` |
| Root directory | repository root |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Node version | `22` or newer |

Alternatively, build locally and upload the contents of `dist` through Pages
Direct Upload. Upload the build output, not the repository or the Blender archive.

**Cloudflare Workers static assets**

The included `wrangler.jsonc` points to `dist`. After building, an authenticated
Wrangler installation can deploy that configuration. No deployment is performed
by the build command.

Every asset is checked against Cloudflare Pages’ 25MiB per-file limit:
[Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/).

## Project layout

- `web/index.html`: accessible application shell and project information.
- `web/src/`: rendering, camera interaction, UI state, building copy and styling.
- `web/public/models/`: compressed campus, interior models and building catalogue.
- `web/public/images/`: web-optimized model renderings.
- `web/public/draco/`: self-hosted Draco decoder.
- `web/tools/`: asset checks and optional Blender export/render scripts.
- `web/tests/`: browser acceptance checks.

The existing local research archive remains under `data`, `code` and `result`.
It includes reference photographs, PDFs, the data-index `main.py`, editable Blender
files and intermediate evidence. Those files are intentionally excluded from this
public web repository. A fresh clone can build and run the website without them.
The optional export scripts need that local archive and are run inside Blender's
Text Editor; their source paths are relative to the project root.

## Validation

```sh
npm run check
npm run build
npx playwright install chromium
npm test
```

Tests cover desktop/mobile selection, search and empty results, gallery navigation,
public-interior switching, unknown footprints, deep links, keyboard/reduced-motion
behavior, all thirty-five on-demand assets, shader compilation, stale-response isolation,
bounded-cache disposal and recovery after a model network failure. On macOS the browser tests use
ANGLE Metal; the default headless software renderer may not create a WebGL context.

## Model scope and attribution

The catalogue contains 31 official map-code records, not 31 independent finished
buildings. Fourteen contain developed detail studies and fifteen have initial street-facade
studies; 61A has provisional attribution, and 35L is represented as a construction site.
Most dimensions are photo-based estimates. This is not a measured survey, a live
campus map or a route planner. The project has no official affiliation with LSE.

The campus first displays a lightweight base, then progressively replaces all
thirty available exteriors with the same detailed geometry used in building views.
Those exterior models remain resident across selection changes; public interior
studies retain a bounded cache. Metric UVs preserve brick and slate courses;
browser procedural shading approximates the source materials. Gallery images
use Cycles. The OLD photographic relief reference is excluded from public assets.

Footprints: ©[OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
ODbL 1.0. See [asset credits](web/public/credits.txt) for source institutions,
model limitations and software licenses. Reference photos/PDFs are not redistributed.

St Clement’s local refinement adds recessed window rows, a setback roof storey,
red corner landings and a recessed signed entrance. The corner artwork is
represented by its panel placement only; no source photograph is embedded.

The final three local rounds refine Lincoln Chambers' recessed portal, Lakatos'
street and plaza elevations, and MAR's north entrance/screen. MAR was prioritized
for the third round. The Portsmouth version 14 draft was not used in edition 15. Edition 16 rebuilds
Portsmouth on top of edition 15, preserving MAR and prior local work. No deployment was performed.

Edition 16 completes an exterior finishing pass on all 31 catalogue records.
Each building has a separate manifest entry and source-pane selection. Historic
windows gain putty/rebate beads and sill drips; modern glazing gains seals, metal
sill channels and drainage slots. POR has a rebuilt corner shopfront. 35L gains
indicative hoarding seams and cap rails only. Public interiors are unchanged.
The local research workspace retains per-building geometry audit records.
The published `release.json` and `gallery-manifest.json` identify current assets.

## Edition 16 release alignment

The interactive detailed assets and every gallery rendering derive from the same
version-16 native source. The viewer uses AgX tone mapping; real-time procedural
shading remains an approximation of the Cycles renders. Gallery URLs include the
model revision, and the release manifest records file hashes. The deployment
package includes only currently referenced model variants; local archives remain
untouched. Native regeneration requires the private local Blender research files.


## Edition 17

Edition 17 adds layered joinery to each existing exterior, following the same
opening positions: sash-box linings and parting grooves, stepped masonry jambs
and sill bearings, or folded metal returns and flashing downstands. Construction
profiles and dimensions are interpretive, not surveyed. The 35L construction
boundary gains indicative post feet only. The original geometry is fingerprinted
before and after the pass; interior and primary building geometry are preserved.

The builder is `web/tools/build_exterior_joinery.py`, with explicit per-building
source selectors in `web/tools/exterior-joinery.json`. Local evidence is saved in
`result/blender/stage17/all-buildings-manifest.json`. The edition-17 release packages the matching interactive assets and 45 gallery
images. Both the campus overview and selected views use the refined exteriors.
