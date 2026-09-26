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

Edition 24 is the current source and release target. It contains 31 catalogue records,
30 exterior models and partial interiors in 25 buildings: five public-space studies
and twenty-four room samples, including independent classrooms in Marshall, CBG
and CKK. Fifteen room samples were added in edition 20, with exterior repairs
to KSW, 50L, 51L and SAR. All 73 gallery views are tied to the native source hash;
unchanged views may be reused only after comparing evaluated render inputs.
The viewer approximates Cycles finishes with self-hosted real-time materials.
Detailed geometry loads on demand; the overview retains the exterior construction
but omits sub-centimetre finishing and uses simpler shading.

The edition-24 build validates 182 deployable files. All 92 local checks pass
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
