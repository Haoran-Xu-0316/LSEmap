# LSEmap

A browser-based architectural study of the London School of Economics campus.

[Explore the live campus](https://lsemap.xhr0316.workers.dev/)

![Campus model](web/public/images/campus.webp)

## Current version

Edition156 is the final snapshot for this refinement round. Five Old Building
lower mansard window crowns now follow the engineer’s built photograph:
horizontal blue caps and paired supports replace proposal-derived triangular
stone pediments. The obscured sixth crown, glazing, roof and existing entrance
corrections are retained. Earlier SAW pierced-window bands, CBG rear louvres,
Plaza Café, CKK fanlight and MAR high-wing roof corrections remain included.

MAR rear-wing/topband registration and FAW independent upper elevations remain
unverified after bounded whole-building reviews. No speculative replacements
were added. Most dimensions and colours are photographic estimates. The project
is not a measured full-campus or complete room-by-room reconstruction.

## Explore

Orbit, pan and zoom freely. Select a building on the map or search its name/code.
Shareable building links, keyboard controls, mobile layouts, reduced motion and
an image-gallery fallback are included. Thirty exterior assets and thirty-three
interior studies load on demand. The catalogue contains31 map-code records;
35L is represented as a construction site and61A attribution remains provisional.

Overview and close-up models use matching accepted geometry, metric UVs and PBR
finishes. Gallery images use the same production CampusViewer. Desktop distant
movement uses depth-reprojected antialiasing with one scene sample per frame.
After drag and damping finish, one four-sample frame restores the sharp desktop
still and demand rendering stops. Canvas resolution remains fixed through gestures;
interiors use the same motion budget and narrow-screen views retain one sample.
Background exterior attachment waits for a quiet navigation frame, and holding
the pointer still does not keep redrawing the scene. Mapped paving, foliage,
asphalt and bench timber use filtered procedural finishes without extra meshes;
their original positions, colours and source geometry remain unchanged.

## Run and build

Requires Node.js22.12 or newer.

```sh
npm ci
npm run dev
npm run check
npm run build
npm run preview
```

Models, images, Roboto and Draco are self-hosted. A fresh clone builds the website
without the private research archive. After changing models, viewer rendering or
gallery cameras, run `npm run gallery` before building. The build rejects stale
gallery/model signatures and checks every runtime asset reference.

## Publish

```sh
npm run deploy
```

This builds and validates the release, then uploads only its verified assets to
the existing Cloudflare Worker `lsemap`. It needs an authenticated Wrangler
session. Pushing GitHub and deploying are separate checks. The online
`/release.json` identifies the production source hash and asset checksums.
See [deployment instructions](DEPLOYMENT.md).

## Source layout

- `web/src/`: rendering, controls, interface and building content.
- `web/public/`: current models, gallery images, fonts and decoder.
- `web/tools/`: source metadata, Blender authoring/export and release validation.
- `web/tests/`: browser and local authoring acceptance checks.
- `data/`: private reference photographs, maps and documents.
- `result/`: private latest native model, required component and verification records.

The local editable source is `result/blender/LSE_campus_detailed_v156.blend`.
The latest accepted component is `result/blender/old_exterior156/old-exterior156-component.blend`.
Native sources, reference photos and local verification output remain outside
GitHub. Historical authoring checks may require their original local evidence;
current local source acceptance is `web/tests/exterior-alignment156.spec.js`.
Obsolete backups, private previews and render caches are deleted after verification.

## Attribution

This independent project has no official affiliation with LSE. Reference
photographs and PDFs are not redistributed. Footprints: ©[OpenStreetMap
contributors](https://www.openstreetmap.org/copyright), ODbL1.0. The globe uses
public-domain Natural Earth geometry and photograph-estimated colouring rather
than the artwork’s original cartography. CBG’s red/orange shades reflect the
requested design preference rather than calibrated photographic colour.

See [asset credits](web/public/credits.txt) for source institutions, software and
font licenses. Public assets do not include the OLD photographic relief reference.
