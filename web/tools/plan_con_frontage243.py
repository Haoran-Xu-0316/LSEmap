"""Classify the historical CON Houghton frontage before native registration.

Fixed source paths and printed drawing scale. This creates a source-scale
component plan, not a surveyed parcel alignment or current-building claim.
"""

import hashlib
import json
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw
from shapely import Polygon, box, constrained_delaunay_triangles, union_all

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-frontage243"
PDF = ROOT / "data/collections/aldwych-boundary243/con_existing_elevation.pdf"
SOURCE_SHA = "f49c9ee992fcf28615002474d79733c0035ef29e9021a1e130d96c10e96222f6"
SCALE = 25.4 / 72 / 1000 * 250
BAYS = [
    (250.76, 270.92),
    (282.56, 309.68),
    (321.68, 341.60),
    (355.88, 369.68),
    (383.96, 403.88),
    (415.88, 435.92),
    (447.80, 467.72),
    (479.60, 499.64),
    (511.52, 531.56),
    (546.08, 552.56),
]


def main():
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == SOURCE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    with pdfplumber.open(PDF) as document:
        page = document.pages[0]
        segments = [(*row["pts"][0], *row["pts"][-1]) for row in page.lines]
        for curve in page.curves:
            segments.extend((*a, *b) for a, b in zip(curve["pts"], curve["pts"][1:]))
    openings = []

    def row(name, band, spans, role="window"):
        for number, (left, right) in enumerate(spans, 1):
            openings.append(
                {
                    "id": f"{name}-{number:02}",
                    "row": name,
                    "role": role,
                    "sourceBounds": [left, band[0], right, band[1]],
                }
            )

    row(
        "roof-upper-south",
        (119.44, 137.44),
        [(255.08, 271.28), (284.60, 315.32), (325.40, 341.48)],
    )
    upper = [
        (362.60, 376.16),
        (387.08, 407.72),
        (418.40, 438.92),
        (449.72, 470.36),
        (481.28, 501.80),
        (513.80, 534.44),
        (545.84, 554.24),
    ]
    row("roof-upper-north", (120.52, 137.44), upper)
    row(
        "roof-lower-south",
        (159.64, 175.48),
        [(254.48, 274.88), (286.16, 313.76), (324.20, 344.24)],
    )
    # The middle southern opening drops below its adjacent sill.
    openings[-2]["sourceBounds"][1:4:2] = [159.64, 183.04]
    row("roof-lower-north", (157.96, 175.48), upper)
    for name, band in [
        ("upper-ribbon", (200.08, 221.08)),
        ("middle-upper", (231.40, 253.60)),
        ("middle-centre", (264.28, 292.12)),
        ("middle-lower", (301.48, 324.04)),
        ("lower-ribbon", (343.00, 367.00)),
    ]:
        row(name, band, BAYS)
    lower = [
        (250.76, 272.48),
        (277.76, 311.96),
        (316.88, 339.20),
        (354.80, 376.76),
        (377.84, 399.32),
        (414.92, 437.60),
        (442.40, 469.28),
        (474.08, 496.88),
        (512.24, 549.80),
    ]
    row("lower-paired", (383.20, 403.72), lower)
    row("street-glazing", (419.56, 456.28), lower[:5], "glazing-or-panel")
    row(
        "street-glazing-east",
        (419.56, 448.60),
        [lower[6], lower[7]],
        "glazing-or-panel",
    )
    row("street-door-transom", (419.56, 430.12), [(414.92, 437.60)])
    row("street-door", (438.88, 468.88), [(418.04, 434.36)], "door")
    row("street-north-portal", (433.36, 466.36), [(512.24, 549.80)], "door")
    # Drawing outline and groundline are independent vector entities. Keep the
    # drawn 0.635m slope; 18.92 is an opening datum, not a flat ground datum.
    outline = [
        (229.16, 473.20),
        (566.12, 466.00),
        (566.12, 94.72),
        (561.08, 94.72),
        (561.08, 97.12),
        (358.52, 97.12),
        (358.52, 94.72),
        (350.48, 94.72),
        (350.48, 97.12),
        (248.12, 97.12),
        (238.16, 132.40),
        (229.16, 132.40),
    ]
    silhouette = Polygon(outline)
    for opening in openings:
        if opening["role"] == "door":
            left, top, right, bottom = opening["sourceBounds"]
            ground = lambda x: 473.20 - (x - 229.16) * 7.2 / (566.12 - 229.16)
            opening["drawnBottomBeforeGroundAlignment"] = bottom
            opening["sourceBounds"][3] = min(bottom, ground(left), ground(right)) - 0.02
    holes = [box(*o["sourceBounds"]) for o in openings]
    assert all(silhouette.covers(hole) for hole in holes), [
        o["id"] for o, h in zip(openings, holes) if not silhouette.covers(h)
    ]
    union = union_all(holes)
    assert abs(sum(h.area for h in holes) - union.area) < 1e-7
    wall = silhouette.difference(union)
    triangles = list(constrained_delaunay_triangles(wall).geoms)
    assert abs(sum(t.area for t in triangles) - wall.area) < 1e-7
    for opening in openings:
        left, top, right, bottom = opening["sourceBounds"]
        opening["widthM"] = (right - left) * SCALE
        opening["heightM"] = (bottom - top) * SCALE
        opening["vectorSegments"] = []
        for a, b, c, d in segments:
            if (
                left + 0.2 <= min(a, c) <= max(a, c) <= right - 0.2
                and top + 0.2 <= min(b, d) <= max(b, d) <= bottom - 0.2
                and (
                    (abs(a - c) < 0.015 and abs(b - d) > 2)
                    or (abs(b - d) < 0.015 and abs(a - c) > 2)
                )
            ):
                opening["vectorSegments"].append([a, b, c, d])
        opening["vectorSegments"] = sorted(
            {tuple(round(v, 3) for v in s) for s in opening["vectorSegments"]}
        )
    plan = {
        "source": str(PDF.relative_to(ROOT)),
        "sourceSha256": SOURCE_SHA,
        "sourceApplication": "20/04703/FULL",
        "published": "2020-08-28",
        "printedScale": "1:250 at A4",
        "metresPerPoint": SCALE,
        "sourceOrigin": [229.16, 473.20],
        "outline": outline,
        "groundline": [[229.16, 473.20], [566.12, 466.00]],
        "groundRiseM": 7.2 * SCALE,
        "sourceWidthM": (566.12 - 229.16) * SCALE,
        "wallAreaM2": wall.area * SCALE**2,
        "openingAreaM2": union.area * SCALE**2,
        "wallTriangles": [list(t.exterior.coords)[:-1] for t in triangles],
        "openings": openings,
        "stage": "source-scale frontage component; native registration not accepted",
        "estimates": {
            "wallDepthM": 0.32,
            "glazingInsetM": 0.14,
            "backingInsetM": 0.60,
            "frameDepthM": 0.085,
            "vectorLineReliefWidthM": 0.018,
        },
        "limitations": [
            "Historical2020 existing elevation, not a2026 survey.",
            "Only the Houghton Street elevation is evidenced. Roof depth, rear mass and unseen elevations are not reconstructed here.",
            "Groundline rises0.635m in the source; native roads are still flat and need separate registration.",
            "CON footprint frontage is about4percent narrower than the printed-scale drawing. Do not silently compress the component or transfer61A boundaries.",
            "Frame divisions follow source vector linework; materials and reveal depths are visual estimates.",
            "Street-level modules include doors and glazing/panel assemblies, not verified complete room interiors.",
        ],
    }
    (OUT / "geometry-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    image = Image.open(
        ROOT / "result/blender/stage243/con-existing-elevation.png"
    ).convert("RGB")
    scale = image.width / 842
    draw = ImageDraw.Draw(image)
    for opening in openings:
        rect = [v * scale for v in opening["sourceBounds"]]
        draw.rectangle(
            rect,
            outline="#277f8a" if opening["role"] == "window" else "#b83f2f",
            width=2,
        )
    draw.line(
        [(x * scale, y * scale) for x, y in plan["groundline"]], fill="#b83f2f", width=4
    )
    image.save(OUT / "source-opening-review.png")
    print(
        "CON243_SOURCE_PLAN",
        len(openings),
        "modules",
        round(plan["wallAreaM2"], 3),
        "m2 wall",
        flush=True,
    )


if __name__ == "__main__":
    main()
