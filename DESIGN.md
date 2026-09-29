---
name: LSE Campus Explorer
description: A daylight architectural model table for free exploration.
colors:
  canvas: "#e9e8e3"
  surface: "#ffffff"
  ink: "#172c38"
  muted: "#526671"
  accent: "#a92332"
  line: "#d4dde2"
typography:
  body:
    fontFamily: "Roboto, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "14px"
    lineHeight: 1.5
rounded:
  control: "6px"
spacing:
  small: "8px"
  medium: "16px"
  large: "24px"
---

## Overview

Experience mode. The user chose free campus exploration. The artifact fills the
first viewport, with a narrow retractable building index and contextual details.
This is a digital architectural model table, not a promotional landing page.

## Colors

Warm neutral canvas and white control surfaces. Blue-black text, muted slate
secondary text. Deep red marks current selection and the primary action.

## Typography

Compact neutral sans-serif interface; 38px index heading, 24px building names,
14px controls, 12px captions. Codes are navigation labels, not decorative numbers.

## Layout

Desktop: 64px masthead, 292px left index, remaining space for the scene. Closing
the index expands the model. Mobile: 56px masthead, full-width scene; the index
opens over the map and building detail uses a compact bottom sheet. No page scroll
or horizontal overflow; the index itself scrolls.

## Elevation & Depth

The model supplies depth. Controls use white surfaces and one subtle offset shadow.
No decorative blur, gradients, card grids or marketing metrics.

## Shapes

Rectangular index rows, thin separators and 6px control corners. Labels sit near
building roofs and are culled when overlapping. The selected code stays visible.

## Components

The masthead uses the original square LSE vector mark at its native aspect ratio.
The full lockup appears in the project information dialog, alongside the independent
project attribution. Preserve the supplied logo artwork and its original red.

Searchable building list. Selection panel with model render and plain-language
scope. Exterior/interior toggle appears only when an interior study exists. Selection
opens an isolated building view, with a toolbar action to restore its surroundings.
A quiet status line reports detail loading and offers retry on failure; the base
model stays interactive during loading. Desktop caches at most three detailed
models and mobile at most two. Bottom
map toolbar controls camera, labels and surrounding context. Native dialogs hold
large render images and concise usage/about content. Keyboard actions and visible
focus remain available when canvas interaction is unavailable.

## Do's and Don'ts

Use source-derived model assets. Respect reduced motion. Allow inspection without
an autoplay tour. Keep missing footprints and estimated dimensions explicit. Do
not imply official affiliation, live campus conditions or complete rooms.

## Interactive model presentation

Neutral tone mapping retains brick and stone colour separation. A restrained
fill light and a shadow camera fitted to the selected building reveal facade
relief. Isolated exteriors use a neutral shadow-receiving ground; the campus
view retains the geographic site. This is illustrative lighting, not a solar study.
Wheel zoom follows the pointer. Button presses accumulate over a short transition;
close inspection permits a 0.15–0.25m orbit radius and campus zoom extends to 2400m.

## Surface finishes

Keep each source material's base colour unless a building-specific photo review documents a correction. Separate glass, warm metals and lead
with material-specific roughness and reflection strength. Stone gets restrained
procedural grain where no source surface descriptor exists. Brick joints receive
a subtle relief treatment; fine grain fades below pixel resolution in the overview.
These browser finish adjustments are artistic approximations, not measured
weathering or a change to the archived Blender geometry.

MAR's exterior palette is separately corrected against the archived Nick Kane
north-elevation photographs, MAR_mar_kane_01 and MAR_mar_kane_02. Use a lighter
neutral precast-concrete tone and deeper blue-grey window panes; these visual
estimates do not imply calibrated reflectance or alter the separate interior model.
Reference: https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/

Exterior shadow maps use a 0.04m normal bias and -0.0002 depth bias.
MAR roof review at desktop and phone sizes confirmed this removes self-shadow
striping while retaining facade recess and ground shadows.

## Edition 26 exterior palette

CBG follows the user's explicit red-dominant, orange-secondary direction. Broad
solar-blade faces are red; narrow returns are orange. Pale structural members
and glass retain distinct finishes. This palette is stored in the native model
and exported into both campus and detailed assets, not applied only on selection.
MAR warm concrete and blue-grey glazing, and SAW restrained red brick with
neutral mortar, are now stored in source materials as photo-guided visual estimates.
Reference photos: MAR Kane 01/02; SAW Photography909 01/02. No measured colour
calibration or complete architectural reconstruction is claimed.

## Gallery consistency

Website stills are captured from CampusViewer with the same exported models,
lighting, tone mapping, shadows and material shaders as the interactive scene.
The native Cycles gallery is an offline reference only. The renderer signature
includes camera presets and shared shader code; the model signature includes the
catalogue and base campus. Build rejects either mismatch. Thumbnail and enlarged
image URLs use each image's own content digest, including renderer-only changes.
