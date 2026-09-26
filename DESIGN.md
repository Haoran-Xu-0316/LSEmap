---
name: LSE Campus Explorer
description: A daylight architectural model table for free exploration.
colors:
  canvas: "#e7ecef"
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

Cool daylight canvas and white control surfaces. Blue-black text, muted slate
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
