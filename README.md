# LSEmap

A browser-based exploration of the London School of Economics campus, built from
an independent Blender architectural study.

[Explore the live campus](https://lsemap.xhr0316.workers.dev/)

![Campus architectural model](web/public/images/campus.webp)

Explore the campus by orbiting, panning and zooming. Select a building directly or
search by its name/code. Detail panels open original model renderings, and five
public-interior studies load on demand. The interface supports mobile screens,
keyboard navigation, reduced motion, shareable building links and a gallery
fallback when WebGL is unavailable. Thirty building models and five interior
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

The campus overview simplifies small bevels and procedural materials. Selected
buildings load their evaluated native geometry, including existing interior floor
plates and roof slabs. Separate interior views use deliberate cutaways. Metric UVs
preserve brick and slate courses; browser noise approximates the source parameters
for stone, concrete and timber. These shaders are not baked Blender renders.
A bounded cache releases old models, and failed detail downloads can be retried
without losing the base view. High-detail renderings retain the Cycles finishes. The OLD photographic relief reference is
removed from the public model and its public rendering.

Footprints: ©[OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
ODbL 1.0. See [asset credits](web/public/credits.txt) for source institutions,
model limitations and software licenses. Reference photos/PDFs are not redistributed.
