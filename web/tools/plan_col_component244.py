"""Plan a private COL source-scale frontage from the reviewed 2020 elevation.

This reuses the accepted 243 module classification. It does not register COL to
campus coordinates, alter road grades, or reconstruct an unseen roof volume.
"""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import pdfplumber
from PIL import Image, ImageDraw
from shapely import Polygon, box, constrained_delaunay_triangles, union_all

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/collections/aldwych-boundary243/col_existing_elevation.pdf"
REVIEW = ROOT / "result/blender/col-frontage243/col-frontage243-review.json"
REGISTRATION = (
    ROOT / "result/blender/col-frontage243/col-native-registration-diagnostic.json"
)
OUT = ROOT / "result/blender/col-component244"
SOURCE_SHA = "cd369000f7053523e3fd2bbc1a0b343c72ca5f61d96d0c66e9b29f5d0eb1d47f"


def ring_points(ring):
    return [[x, y] for x, y in list(ring.coords)[:-1]]


def create_plan():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
    review = json.loads(REVIEW.read_text())
    registration = json.loads(REGISTRATION.read_text())
    assert review["source"]["sha256"] == SOURCE_SHA
    assert review["counts"]["totalFrontageModules"] == 72
    scale = review["coordinateSystem"]["metresPerPointAtPrintedScale"]
    with pdfplumber.open(SOURCE) as document:
        page = document.pages[0]
        assert (page.width, page.height) == (842, 595)
        segments = [(*line["pts"][0], *line["pts"][-1]) for line in page.lines]
        for curve in page.curves:
            segments.extend((*a, *b) for a, b in zip(curve["pts"], curve["pts"][1:]))
    # The projection is included only as an elevation silhouette, with estimated
    # relief thickness. Its function and actual depth remain unknown.
    outline = [
        (273.32, 441.16),
        (569.12, 445.84),
        (569.12, 140.32),
        (563.96, 140.32),
        (558.92, 96.76),
        (482.96, 96.76),
        (482.96, 52.12),
        (447.20, 52.12),
        (447.20, 96.76),
        (290.24, 96.76),
        (278.96, 162.76),
        (273.32, 162.76),
    ]
    silhouette = Polygon(outline)
    assert silhouette.is_valid
    openings = []
    for row in review["rows"]:
        for bay, bounds in enumerate(row["moduleBoundsPt"], 1):
            role = (
                "regular-window"
                if row["id"] != "R9"
                else (
                    "entrance-material-unverified"
                    if bay == 2
                    else "vent-or-panel-material-unverified"
                )
            )
            full = box(*bounds)
            cut = full.intersection(silhouette)
            assert cut.geom_type == "Polygon" and cut.is_valid and cut.area > 0
            left, top, right, bottom = bounds
            lines = set()
            for a, b, c, d in segments:
                if (
                    left + 0.2 <= min(a, c) <= max(a, c) <= right - 0.2
                    and top + 0.2 <= min(b, d) <= max(b, d) <= bottom - 0.2
                    and (
                        (abs(a - c) < 0.015 and abs(b - d) > 2)
                        or (abs(b - d) < 0.015 and abs(a - c) > 2)
                    )
                ):
                    lines.add(tuple(round(v, 3) for v in (a, b, c, d)))
            frame_boxes = [
                (left, top, left + 0.55, bottom),
                (right - 0.55, top, right, bottom),
                (left + 0.55, top, right - 0.55, top + 0.55),
                (left + 0.55, bottom - 0.55, right - 0.55, bottom),
            ]
            frame_boxes.extend(
                (min(a, c) - 0.1, min(b, d) - 0.1, max(a, c) + 0.1, max(b, d) + 0.1)
                for a, b, c, d in sorted(lines)
            )
            frames = []
            for rect in frame_boxes:
                clipped = box(*rect).intersection(cut)
                if not clipped.is_empty and clipped.area > 1e-8:
                    assert clipped.geom_type == "Polygon"
                    frames.append(ring_points(clipped.exterior))
            openings.append(
                {
                    "id": f"{row['id']}-B{bay:02}",
                    "row": row["id"],
                    "bay": bay,
                    "role": role,
                    "sourceBounds": bounds,
                    "cutPolygonPt": ring_points(cut.exterior),
                    "trimmedBelowSourceGroundAreaM2": (full.area - cut.area) * scale**2,
                    "widthM": (right - left) * scale,
                    "heightM": (bottom - top) * scale,
                    "vectorSegments": sorted(lines),
                    "framePolygonsPt": frames,
                }
            )
    holes = [Polygon(item["cutPolygonPt"]) for item in openings]
    merged = union_all(holes)
    assert abs(sum(h.area for h in holes) - merged.area) < 1e-6
    wall = silhouette.difference(merged)
    assert wall.geom_type == "Polygon" and wall.is_valid
    triangles = list(constrained_delaunay_triangles(wall).geoms)
    assert all(wall.covers(t.representative_point()) for t in triangles)
    assert abs(sum(t.area for t in triangles) - wall.area) < 1e-6
    assert sum(o["role"] == "regular-window" for o in openings) == 64
    assert sum(o["role"] == "vent-or-panel-material-unverified" for o in openings) == 7
    assert sum(o["role"] == "entrance-material-unverified" for o in openings) == 1
    ribbons = []
    by_row = {row["id"]: row["moduleBoundsPt"] for row in review["rows"]}
    for upper_id, lower_id in [("R3", "R4"), ("R4", "R5"), ("R5", "R6"), ("R8", "R9")]:
        for upper, lower in zip(by_row[upper_id], by_row[lower_id]):
            for side in (0, 2):
                # The source draws continuous edges around opaque spandrels.
                # Retain those edges without cutting an additional glass hole.
                x0, y0 = upper[side], upper[3]
                x1, y1 = lower[side], lower[1]
                ribbons.append(
                    [
                        [x0 - 0.175, y0],
                        [x0 + 0.175, y0],
                        [x1 + 0.175, y1],
                        [x1 - 0.175, y1],
                    ]
                )
    return {
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": SOURCE_SHA,
        "sourceClassification": str(REVIEW.relative_to(ROOT)),
        "sourceApplication": "20/04703/FULL",
        "published": "2020-08-28",
        "printedScale": "1:250 at A4",
        "metresPerPoint": scale,
        "sourceOrigin": [273.32, 445.84],
        "coordinateSystem": "local X increases north-to-south with PDF x; local Y positive into relief; local Z above southern drawn ground",
        "outline": outline,
        "groundline": review["groundline"]["polylinePt"],
        "groundRiseNorthM": 4.68 * scale,
        "sourceWidthM": 295.8 * scale,
        "continuousRibbonEdgePolygonsPt": ribbons,
        "counts": review["counts"],
        "openings": openings,
        "wallAreaM2": wall.area * scale**2,
        "openingAreaM2": merged.area * scale**2,
        "wallTriangles": [ring_points(t.exterior) for t in triangles],
        "wallBoundaryRings": [ring_points(wall.exterior)]
        + [ring_points(r) for r in wall.interiors],
        "horizontalBandsYpt": review["horizontalBandsYpt"],
        "nativeRegistrationAccepted": False,
        "registrationDiagnostic": registration["lengthComparison"],
        "stage": "private source-scale elevation component plan; no native registration or web export",
        "estimates": {
            "wallDepthM": 0.32,
            "glazingInsetM": 0.14,
            "backingInsetM": 0.60,
            "frameWidthPt": 0.55,
            "vectorLineHalfWidthPt": 0.10,
        },
        "limitations": [
            "Historical2020 existing elevation, not a current2026 survey.",
            "Source LEFT=NORTH, RIGHT=SOUTH. Do not mirror using CON direction.",
            "Native Houghton straight frontage is0.134479m shorter, or0.515484percent. No fitting or borrowing Garrick chamfer is accepted.",
            "The roof and unknown rectangular projection are elevation silhouettes only. Rear mass, roof pitch, depth and function are not reconstructed.",
            "Reveal depths and neutral materials are visual estimates; ground panels and entrance materials remain unverified and use opaque infill.",
            "The source groundline rises0.41275m northward. No native road grade, campus geometry, AOD offset or Garrick entrance is changed.",
            "Bay2 entrance cut is clipped to the drawn groundline where the source rectangle crosses it. The original reviewed module bounds are retained.",
            "Opaque backing closes each opening; this component does not claim an observed interior.",
        ],
    }


def review_image(plan):
    with tempfile.TemporaryDirectory(prefix="col244-review-") as temporary:
        prefix = Path(temporary) / "elevation"
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-singlefile",
                "-scale-to",
                "2526",
                "-png",
                str(SOURCE),
                str(prefix),
            ],
            check=True,
            capture_output=True,
        )
        image = Image.open(prefix.with_suffix(".png")).convert("RGB")
    sx, sy = image.width / 842, image.height / 595
    draw = ImageDraw.Draw(image)
    for opening in plan["openings"]:
        points = [(x * sx, y * sy) for x, y in opening["cutPolygonPt"]]
        draw.line(
            points + [points[0]],
            fill="#1b747d" if opening["role"] == "regular-window" else "#a35c22",
            width=3,
        )
    draw.line(
        [(x * sx, y * sy) for x, y in plan["outline"] + [plan["outline"][0]]],
        fill="#347652",
        width=3,
    )
    draw.line(
        [(x * sx, y * sy) for x, y in plan["groundline"]], fill="#bc312b", width=4
    )
    image.crop(
        (round(255 * sx), round(40 * sy), round(590 * sx), round(460 * sy))
    ).save(OUT / "source-opening-review.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plan = create_plan()
    (OUT / "geometry-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    review_image(plan)
    print(
        "COL244_SOURCE_PLAN",
        len(plan["openings"]),
        "modules",
        len(plan["wallTriangles"]),
        "wall triangles",
        round(plan["wallAreaM2"], 3),
        "m2 wall",
    )


if __name__ == "__main__":
    main()
