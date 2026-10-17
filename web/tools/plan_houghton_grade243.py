"""Plan a bounded Houghton grade study from two historical relative elevations.

The shared southern datum and northward transition are authored assumptions,
not an absolute/current topographic survey. Original parcel boundaries stay fixed.
"""

import itertools
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/houghton-integration243"
CON = [
    (-5.206503105887521, -125.48800989540118),
    (-7.740307145247294, -107.45306992676488),
    (-8.962077131447503, -97.0170586434884),
]
COL = [(5.831283376451804, -125.39900274397166), (3.46404238662079, -99.55374993886971)]
CON_LENGTH = sum(math.dist(a, b) for a, b in itertools.pairwise(CON))


def smooth(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def side_at_y(points, y, rise):
    if y <= points[0][1]:
        return points[0][0], 0
    length = sum(math.dist(a, b) for a, b in itertools.pairwise(points))
    if y >= points[-1][1]:
        return points[-1][0], rise
    traversed = 0
    for a, b in itertools.pairwise(points):
        distance = math.dist(a, b)
        if y <= b[1]:
            fraction = (y - a[1]) / (b[1] - a[1])
            return a[0] + fraction * (b[0] - a[0]), rise * (
                traversed + fraction * distance
            ) / length
        traversed += distance
    raise AssertionError("Missing frontage segment")


def grade_height(x, y):
    if y < CON[0][1] or y >= -75:
        return 0.0
    west, west_height = side_at_y(CON, y, 0.635)
    east, east_height = side_at_y(COL, y, 0.41275)
    fraction = max(0, min(1, (x - west) / (east - west)))
    height = west_height + (east_height - west_height) * fraction
    # This collar joins the retained flat campus. It is deliberately recorded
    # as an estimated transition, not extrapolated historical spot levels.
    north = 1 - smooth((y - CON[-1][1]) / (-75 - CON[-1][1]))
    edge = smooth((x - (west - 8)) / 8) * smooth(((east + 8) - x) / 8)
    return height * north * edge


def plan_paving_repair(inventory):
    from shapely import (
        Polygon,
        STRtree,
        box,
        constrained_delaunay_triangles,
        make_valid,
        unary_union,
    )

    source = next(
        r
        for r in inventory["objects"]
        if r["name"] == "SITE194_SITE167_Houghton_paving_with_cover_openings"
    )
    region = box(-9, -135, 7, -97)
    tops = []
    for index, face in enumerate(source["faces"]):
        points = [source["vertices"][v] for v in face]
        if not all(abs(p[2] - 0.05) < 1e-6 for p in points):
            continue
        geometry = make_valid(Polygon([p[:2] for p in points]))
        if geometry.area < 1e-10:
            continue
        material = source["materials"][source["materialIndices"][index]]
        tops.append(
            {
                "face": index,
                "geometry": geometry,
                "material": material,
                "selected": "edge_" in material and geometry.intersects(region),
            }
        )
    tree = STRtree([r["geometry"] for r in tops])
    repairs, removed_area = [], 0
    for index, row in enumerate(tops):
        if not row["selected"]:
            continue
        priority = (row["material"], row["face"])
        blockers = [
            tops[j]["geometry"]
            for j in tree.query(row["geometry"], predicate="intersects")
            if j != index
            and (
                not tops[j]["selected"]
                or (tops[j]["material"], tops[j]["face"]) < priority
            )
        ]
        occupied = unary_union(blockers)
        raw = row["geometry"].difference(occupied)
        if row["geometry"].area - raw.area <= 1e-10:
            continue
        # Native coordinates are float32 (about8micrometres at this street).
        # Leave a20micrometre clipping clearance so quantized new vertices
        # cannot cross the retained higher-priority boundary again.
        clipped = row["geometry"].difference(occupied.buffer(0.00002)).buffer(-0.00002)
        loss = row["geometry"].area - clipped.area
        if loss <= 1e-10:
            continue
        triangles = [
            list(t.exterior.coords)[:-1]
            for t in constrained_delaunay_triangles(clipped).geoms
            if t.area > 1e-12
        ]
        repairs.append(
            {
                "sourceFace": row["face"],
                "materialIndex": source["materialIndices"][row["face"]],
                "originalAreaM2": row["geometry"].area,
                "remainingAreaM2": clipped.area,
                "trianglesXY": triangles,
            }
        )
        removed_area += loss
    assert len(repairs) >= 266 and 1.52 < removed_area < 1.54
    return {
        "source": source["name"],
        "removedOverlapAreaM2": removed_area,
        "clipClearanceM": 0.00002,
        "nativeBorderInsetM": 0.00002,
        "repairs": repairs,
        "priority": "Retained slabs and nonlocal edges first, then edge material name and original face index",
        "scope": "Clip only overlapping coplanar Houghton edge tops; preserve source height, UV interpolation and all unlisted faces",
    }


def main():
    from shapely import Polygon, box, constrained_delaunay_triangles

    OUT.mkdir(parents=True, exist_ok=True)
    core = Polygon(CON + list(reversed(COL)))
    triangles = []
    for ix in range(math.floor(core.bounds[0]), math.ceil(core.bounds[2])):
        for iy in range(math.floor(core.bounds[1]), math.ceil(core.bounds[3])):
            cell = core.intersection(box(ix, iy, ix + 1, iy + 1))
            if cell.is_empty or cell.area < 1e-10:
                continue
            for triangle in constrained_delaunay_triangles(cell).geoms:
                triangles.append(
                    [
                        [x, y, grade_height(x, y) + 0.018]
                        for x, y in list(triangle.exterior.coords)[:-1]
                    ]
                )
    # The level support may extend to the existing southern road fragment. Its
    # footprint is an authored gap closure, independent of the rejected grade.
    inventory = json.loads((OUT / "ground-source-geometry.json").read_text())
    road = next(
        r
        for r in inventory["objects"]
        if r["name"] == "GROUND199_Road_Houghton Street.003"
    )
    south_y = road["bounds"]["min"][1]

    def extend(points):
        a, b = points[:2]
        return (a[0] + (south_y - a[1]) * (b[0] - a[0]) / (b[1] - a[1]), south_y)

    support = Polygon([extend(CON)] + CON + list(reversed(COL)) + [extend(COL)])
    support_triangles = []
    for ix in range(math.floor(support.bounds[0]), math.ceil(support.bounds[2])):
        for iy in range(math.floor(support.bounds[1]), math.ceil(support.bounds[3])):
            cell = support.intersection(box(ix, iy, ix + 1, iy + 1))
            if cell.is_empty or cell.area < 1e-10:
                continue
            support_triangles.extend(
                [
                    list(t.exterior.coords)[:-1]
                    for t in constrained_delaunay_triangles(cell).geoms
                ]
            )
    checks = []
    for points, rise in [(CON, 0.635), (COL, 0.41275)]:
        length = sum(math.dist(a, b) for a, b in itertools.pairwise(points))
        travelled = 0
        for a, b in itertools.pairwise(points):
            segment = math.dist(a, b)
            for i in range(11):
                t = i / 10
                x = a[0] + t * (b[0] - a[0])
                y = a[1] + t * (b[1] - a[1])
                expected = rise * (travelled + t * segment) / length
                actual = grade_height(x, y)
                # The COL north endpoint lies within the proven CON extent;
                # neither frontage is damped by the authored north transition.
                assert abs(actual - expected) < 1e-8, (x, y, actual, expected)
                checks.append([x, y, actual])
            travelled += segment
    result = {
        "baselineSha256": "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589",
        "gradeSource": "Historical2020 Houghton elevations, printed scale; relative rises only",
        "sourceReferences": [
            "data/collections/aldwych-boundary243/con_existing_elevation.pdf",
            "data/collections/aldwych-boundary243/col_existing_elevation.pdf",
        ],
        "CONRiseM": 0.635,
        "COLRiseM": 0.41275,
        "CONFrontage": CON,
        "COLFrontage": COL,
        "contactSamples": checks,
        "pavingRepair": plan_paving_repair(inventory),
        "levelSupport": {
            "areaM2": support.area,
            "trianglesXY": support_triangles,
            "southernExistingRoadObject": road["name"],
            "southY": south_y,
            "scope": "Estimated level support under existing paving, including the southern inherited edge gap; no grade or parcel transfer",
        },
        "coreAreaM2": core.area,
        "coreTriangles": triangles,
        "coreBedTopAboveGradeM": 0.018,
        "coreBedThicknessM": 0.05,
        "sourceControlStatus": "relative facade profiles retained; shared south datum and north transition estimated",
        "estimatedNorthTransitionY": [-97.0170586434884, -75],
        "estimatedLateralFeatherM": 8,
        "parcelBoundariesChanged": False,
        "limitations": [
            "No shared absoluteAOD datum or current2026 street survey is established.",
            "The southern zero level is an authored common datum selected to retain the existing Aldwych entrances.",
            "The north collar blends to the retained flat campus and is not a verified real-world grade.",
            "Width registration remains estimated; this component does not certify accessibility or complete terrain accuracy.",
        ],
    }
    (OUT / "grade-plan.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        "HOUGHTON243_GRADE_PLAN",
        len(triangles),
        round(core.area, 3),
        len(checks),
        flush=True,
    )


if __name__ == "__main__":
    main()
