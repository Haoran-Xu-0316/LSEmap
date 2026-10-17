"""Register the historical CON elevation to the retained campus footprint.

The horizontal fit, flat door thresholds and unseen roof closure are explicitly
estimated presentation accommodations. No boundary or current street is moved.
"""

import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import split, triangulate

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-registration244"
SOURCE = ROOT / "result/blender/con-frontage243/geometry-plan.json"
S = (-5.206503105887521, -125.48800989540118)
M = (-7.740307145247294, -107.45306992676488)
N = (-8.962077131447503, -97.0170586434884)


def main():
    source = json.loads(SOURCE.read_text())
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    ring = next(b for b in site["buildings"] if b.get("code") == "CON")["rings"][0]
    lengths = [math.dist(S, M), math.dist(M, N)]
    scale = sum(lengths) / source["sourceWidthM"]
    axis = [(M[i] - S[i]) / lengths[0] for i in range(2)]
    cross = [-axis[1], axis[0]]
    profile = [
        [
            (x - source["sourceOrigin"][0]) * source["metresPerPoint"] * scale,
            (source["sourceOrigin"][1] - y) * source["metresPerPoint"],
        ]
        for x, y in [
            (229.16, 132.40),
            (238.16, 132.40),
            (248.12, 97.12),
            (566.12, 97.12),
        ]
    ]
    polygon = Polygon(ring)
    patches = [polygon]
    for station, _z in profile[1:3]:
        centre = [S[i] + axis[i] * station for i in range(2)]
        line = LineString(
            [
                [centre[i] + cross[i] * distance for i in range(2)]
                for distance in [-100, 100]
            ]
        )
        patches = [part for patch in patches for part in split(patch, line).geoms]
    roof_triangles = []
    boundary_segments = []
    for patch in patches:
        for tri in triangulate(patch):
            if patch.covers(tri):
                roof_triangles.append(list(tri.exterior.coords)[:-1])
        points = list(patch.exterior.coords)
        for a, b in pairwise(points):
            if (
                polygon.boundary.distance(
                    LineString([a, b]).interpolate(0.5, normalized=True)
                )
                < 1e-8
            ):
                boundary_segments.append([a, b])
    assert abs(sum(Polygon(t).area for t in roof_triangles) - polygon.area) < 1e-7
    assert (
        abs(sum(math.dist(a, b) for a, b in boundary_segments) - polygon.length) < 1e-7
    )
    record = {
        "baseline": "result/blender/LSE_campus_detailed_v243.blend",
        "baselineSha256": "cd41b4372b1e690400f351ed8bce228b1b1fa91f9bc161ddbbd91fb3f4349ba8",
        "sourcePlan": str(SOURCE.relative_to(ROOT)),
        "sourcePlanSha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "sourcePdfSha256": source["sourceSha256"],
        "frontage": [S, M, N],
        "segmentLengthsM": lengths,
        "nativeFrontageLengthM": sum(lengths),
        "sourceWidthM": source["sourceWidthM"],
        "horizontalFit": scale,
        "horizontalCompressionPercent": (1 - scale) * 100,
        "sourceHeightsPreserved": True,
        "nativeParcelUnchanged": True,
        "streetAndMainEntranceLevelsUnchanged": True,
        "doorThresholdM": 0.06,
        "doorAccommodations": [
            o["id"] for o in source["openings"] if o["role"] == "door"
        ],
        "roofProfileStationHeightM": profile,
        "roofProjectionAxis": axis,
        "roofFootprint": ring,
        "roofTriangles": roof_triangles,
        "roofBoundarySegments": boundary_segments,
        "roofFootprintAreaM2": polygon.area,
        "roofSlabThicknessM": 0.12,
        "upperRearWallBaseM": 28.95,
        "limitations": [
            "2020 existing elevation supplies opening layout and vertical proportions, not a current2026 survey.",
            "Horizontal-only fit retains the current map parcel; its3.36percent discrepancy remains an estimated registration.",
            "Two side-door lower bounds and the facade foot are adapted to the retained flat street; no historical ground slope is applied.",
            "The unseen rear upper closure and roof depth follow the retained footprint as an estimate, not measured drawings.",
            "Aldwych entrance, all interiors, neighbouring parcels and streets retain the accepted native geometry.",
        ],
        "status": "planned-candidate-requires-saved-mesh-and-visual-review",
    }
    assert len(record["doorAccommodations"]) == 2
    (OUT / "registration-plan.json").write_text(json.dumps(record, indent=2) + "\n")
    print(
        "CON244_REGISTRATION_PLANNED",
        round(scale, 8),
        len(roof_triangles),
        round(polygon.area, 4),
    )


if __name__ == "__main__":
    main()
