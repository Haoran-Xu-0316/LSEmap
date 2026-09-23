# LSEmap

<!-- impeccable:product-schema 1 -->

## Platform

web

## Product Purpose

Present the existing LSE architectural model as a browser-based campus exploration.
The user explicitly chose free exploration over a guided building sequence.
Publish website source and display assets to Haoran-Xu-0316/LSEmap on GitHub.
Deploy the reviewed static website to the user's Cloudflare account.

## Capabilities and Constraints

Orbit, pan, zoom, select buildings and inspect architectural renderings. Existing
public-interior studies are separate views, not a promise of navigable rooms.
Source: the local version 16 Blender campus; the deployment target is the same edition 16. There are 31 map-code records, 14
buildings with developed details, 15 initial street-facade studies, and a provisionally attributed 61A facade. Most dimensions
are estimated. This is an independent study, not an official map or route planner.

Original research photographs, PDFs, credentials, local paths and editable Blender
files are excluded from the public repository. No account or external API needed.
The user authorized Cloudflare deployment after review. Do not delegate to subagents.

## Users

Assumption: people viewing the user's architectural work on desktop or mobile.
Their relationship to LSE is unspecified; navigation should need no prior knowledge.

## Evidence on Hand

Existing version 16 model, building catalogue, OSM footprint provenance and native
Blender renders. The overview uses simplified materials. Thirty on-demand
buildings preserve evaluated bevels, curve resolution and existing internal
structure; five separate public-space views retain deliberate cutaways. Browser
shaders approximate source brick/noise parameters without distributing archival
photographs. Detail images preserve the Cycles finishes. There is no verified complete interior survey.

## Product Principles

The model leads. Building code and full name stay paired. Missing geometry is
explicit. Preserve research assets. Keep the runtime entirely self-hosted.

Edition 05 distinguishes first-pass street facades from developed detail studies.
Do not promote their estimated bay spacing, heights or unobserved backs to surveyed
geometry. 35L remains a construction-site representation. 49L and the 50/50A envelope
are placed using the 2022 architectural block plan, not an assertion of tenancy boundaries. 61A now has a developed
street elevation while retaining its provisional footprint attribution.

The user requested local refinement first, followed by an explicit complete-release deployment.
Publication was explicitly requested for the complete edition 16. Cowdray
and King's Chambers now include additional photographed heritage details and
entrance views; their unmeasured dimensions and unseen elevations stay explicit.

Parish Hall now has a photo-informed stepped entrance wing, four street window
groups and pitched tiled roof with dormers. The previous uniform three-storey
facade was replaced. The original footprint stays fixed; unseen sides remain estimates.

St Clement’s now has distinct Clare Market window rows, a narrow corner panel,
recessed red landings, a setback top floor and an entry close-up. Artwork imagery
is omitted; entry bay, heights and unseen elevations remain approximate.

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
