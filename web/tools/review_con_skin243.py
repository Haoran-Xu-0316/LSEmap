"""Audit CON frontage polygon masks without changing native scene geometry.

The source export uses world coordinates. Polygon and island indices are
zero-based. Islands share source vertex indices; coincident unwelded vertices
are deliberately not merged. Run this file directly with the existing Python
MachineLearning environment; all configuration lives here.
"""

import json
from collections import Counter, defaultdict
from hashlib import sha256
from math import hypot
from pathlib import Path

from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "result/blender/stage243/current-exterior-geometry.json"
OUTPUT = ROOT / "result/blender/con-frontage243/skin-mask-review"
SOUTH = (-5.20650310589, -125.4880098954)
MIDDLE = (-7.74030714525, -107.45306992676)
NORTH = (-8.96207713145, -97.01705864349)
SEGMENTS = [(SOUTH, MIDDLE), (MIDDLE, NORTH)]
SEGMENT_NAMES = ["S-M", "M-N"]
NORMAL_LIMIT = 0.4
END_TOLERANCE = 0.00002
ENTRANCE = (-16.178, -130.222)
FRONT_WALLS = {"CON_wall_0_1", "CON_wall_0_2"}
SHARED_BATCHES = {
    "CON_EXTERIOR_Stone_jamb",
    "CON_EXTERIOR_Glazing_bays.001",
    "CON_EXTERIOR_Glazing_bays.002",
    "GLASS181_CON_EXTERIOR_Glazing_bays",
    "CON_EXTERIOR_Cornice_stringcourse",
}


def projection(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    px, py = point[0] - start[0], point[1] - start[1]
    return ((px * dx + py * dy) / length, (px * dy - py * dx) / length, length)


def connected_islands(vertices, faces):
    parent = list(range(len(vertices)))

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for face in faces:
        for index in face[1:]:
            parent[root(index)] = root(face[0])
    groups = defaultdict(list)
    for polygon_index, face in enumerate(faces):
        groups[root(face[0])].append(polygon_index)
    return sorted(groups.values(), key=lambda group: group[0])


def index_ranges(indices):
    ranges = []
    for value in sorted(indices):
        if ranges and ranges[-1][1] + 1 == value:
            ranges[-1][1] = value
        else:
            ranges.append([value, value])
    return ranges


def rounded(values):
    return [round(value, 6) for value in values]


def segment_rectangle(start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = hypot(dx, dy)
    nx, ny = dy / length * NORMAL_LIMIT, -dx / length * NORMAL_LIMIT
    return Polygon(
        [
            (start[0] + nx, start[1] + ny),
            (end[0] + nx, end[1] + ny),
            (end[0] - nx, end[1] - ny),
            (start[0] - nx, start[1] - ny),
        ]
    )


def main():
    source_bytes = SOURCE.read_bytes()
    export = json.loads(source_bytes)
    frontage_strip = unary_union([segment_rectangle(a, b) for a, b in SEGMENTS])
    masks, diagnostics, ambiguous = [], [], []
    all_removed_points = []
    for obj in export["objects"]:
        if obj["code"] != "CON":
            continue
        if obj["type"] != "MESH":
            diagnostics.append(
                {
                    "name": obj["name"],
                    "type": obj["type"],
                    "action": "retain",
                    "reason": "non-mesh; outside polygon mask",
                }
            )
            continue
        name, vertices, faces = obj["name"], obj["vertices"], obj["faces"]
        islands = connected_islands(vertices, faces)
        remove, retain, island_rows = [], [], []
        counts = Counter()
        for island_index, polygon_indices in enumerate(islands):
            vertex_indices = sorted(
                {index for p in polygon_indices for index in faces[p]}
            )
            points = [vertices[index] for index in vertex_indices]
            centroid = [sum(p[axis] for p in points) / len(points) for axis in range(3)]
            bounds = [
                [min(p[axis] for p in points), max(p[axis] for p in points)]
                for axis in range(3)
            ]
            fits, segment_rows = [], []
            for segment_index, (start, end) in enumerate(SEGMENTS):
                local = [projection(p, start, end) for p in points]
                t_range = [min(p[0] for p in local), max(p[0] for p in local)]
                d_range = [min(p[1] for p in local), max(p[1] for p in local)]
                fits_segment = (
                    max(abs(d) for d in d_range) <= NORMAL_LIMIT
                    and t_range[0] >= -END_TOLERANCE
                    and t_range[1] <= local[0][2] + END_TOLERANCE
                )
                if fits_segment:
                    fits.append(SEGMENT_NAMES[segment_index])
                segment_rows.append(
                    {
                        "segment": SEGMENT_NAMES[segment_index],
                        "alongM": rounded(t_range),
                        "signedNormalM": rounded(d_range),
                    }
                )
            action = (
                "remove"
                if name in FRONT_WALLS or (name in SHARED_BATCHES and fits)
                else "retain"
            )
            (remove if action == "remove" else retain).extend(polygon_indices)
            counts[action] += 1
            if action == "remove":
                all_removed_points.extend(points)
            hull = MultiPoint([p[:2] for p in points]).convex_hull
            overlap = hull.intersection(frontage_strip)
            corner_overlap = (
                name in SHARED_BATCHES
                and action == "retain"
                and not overlap.is_empty
                and overlap.area > 1e-8
            )
            if corner_overlap:
                affected_faces, spanning_faces = [], []
                for polygon_index in polygon_indices:
                    face_hull = MultiPoint(
                        [vertices[i][:2] for i in faces[polygon_index]]
                    ).convex_hull
                    intersection = face_hull.intersection(frontage_strip)
                    if not intersection.is_empty and (
                        intersection.area > 1e-8 or intersection.length > 1e-6
                    ):
                        affected_faces.append(polygon_index)
                        if not frontage_strip.buffer(END_TOLERANCE).covers(face_hull):
                            spanning_faces.append(polygon_index)
                ambiguous.append(
                    {
                        "object": name,
                        "island": island_index,
                        "polygonIndexRanges": index_ranges(polygon_indices),
                        "frontageStripOverlapPolygonIndices": affected_faces,
                        "requiresFaceClippingPolygonIndices": spanning_faces,
                        "action": "retain",
                        "reason": "Other-facade island intersects the frontage corner strip. Do not remove its whole island or full spanning polygons. Clip only if a future explicitly bounded corner replacement requires it.",
                    }
                )
            island_rows.append(
                {
                    "island": island_index,
                    "polygonIndexRanges": index_ranges(polygon_indices),
                    "vertexCount": len(vertex_indices),
                    "polygonCount": len(polygon_indices),
                    "centroid": rounded(centroid),
                    "bounds": [rounded(b) for b in bounds],
                    "segments": segment_rows,
                    "fitsWholeIsland": fits,
                    "action": action,
                    "cornerStripOverlap": corner_overlap,
                }
            )
        assert sorted(remove + retain) == list(range(len(faces)))
        assert set(remove).isdisjoint(retain)
        masks.append(
            {
                "name": name,
                "sourceFingerprint": obj["fingerprint"],
                "sourcePolygonCount": len(faces),
                "removeCount": len(remove),
                "retainCount": len(retain),
                "removePolygonIndices": sorted(remove),
                "retainPolygonIndexRanges": index_ranges(retain),
            }
        )
        diagnostics.append(
            {
                "name": name,
                "type": obj["type"],
                "vertexCount": len(vertices),
                "polygonCount": len(faces),
                "islandCount": len(islands),
                "removeIslandCount": counts["remove"],
                "retainIslandCount": counts["retain"],
                "removePolygonCount": len(remove),
                "retainPolygonCount": len(retain),
                "materials": obj["materials"],
                "islands": island_rows,
            }
        )
    roof = next(m for m in masks if m["name"] == "CON_roof")
    assert roof["removeCount"] == 0 and roof["retainCount"] == 50
    entrance_clearance = min(
        hypot(p[0] - ENTRANCE[0], p[1] - ENTRANCE[1]) for p in all_removed_points
    )
    assert entrance_clearance > 8
    shared_counts = [
        {
            key: row[key]
            for key in (
                "name",
                "islandCount",
                "removeIslandCount",
                "retainIslandCount",
                "removePolygonCount",
                "retainPolygonCount",
            )
        }
        for row in diagnostics
        if row["name"] in SHARED_BATCHES
    ]
    manifest = {
        "source": str(SOURCE.relative_to(ROOT)),
        "sourceSha256": sha256(source_bytes).hexdigest(),
        "baselineSha256": export["baselineSha256"],
        "building": "CON",
        "stage": "proposed mask only; no native changes",
        "polygonIndexBase": 0,
        "rangeConvention": "inclusive [first,last]",
        "frontage": [SOUTH, MIDDLE, NORTH],
        "normalLimitM": NORMAL_LIMIT,
        "endpointToleranceM": END_TOLERANCE,
        "rule": "Remove only the two named front walls and shared-batch vertex-connected islands whose complete vertex extent fits one bounded facade plane. Retain all roof polygons, entrance geometry, other facades and corner-spanning islands.",
        "objects": masks,
    }
    summary = {
        "stage": manifest["stage"],
        "sourceSha256": manifest["sourceSha256"],
        "meshObjectCount": len(masks),
        "nonMeshObjectCount": len(diagnostics) - len(masks),
        "removePolygonCount": sum(m["removeCount"] for m in masks),
        "retainPolygonCount": sum(m["retainCount"] for m in masks),
        "sharedBatchCounts": shared_counts,
        "ambiguousCornerIslandCount": len(ambiguous),
        "acceptedEntranceXY": ENTRANCE,
        "removedVertexMinEntranceDistanceM": round(entrance_clearance, 6),
        "roof": {
            "action": "retain all 50 polygons",
            "frontEdgePolygonIndices": [33, 34],
            "reason": "Front roof-edge quads are part of roof geometry, not frontage replacement walls. Whole-roof removal is excluded.",
        },
        "limitations": [
            "The 0.4m plane envelope is a selection tolerance for current skin thickness, not a surveyed replacement depth.",
            "The source-scale component.blend was neither read nor integrated.",
            "Corner overlaps remain retained. Any later corner subtraction must use explicit face clipping rather than this whole-island removal mask.",
            "Polygon indices require the exact source export hash and unchanged source object topology.",
        ],
        "ambiguousCases": ambiguous,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for filename, document in [
        ("polygon-mask.json", manifest),
        ("island-diagnostics.json", diagnostics),
        ("review-summary.json", summary),
    ]:
        (OUTPUT / filename).write_text(
            json.dumps(document, separators=(",", ":")) + "\n"
        )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "meshObjectCount",
                    "removePolygonCount",
                    "retainPolygonCount",
                    "ambiguousCornerIslandCount",
                    "removedVertexMinEntranceDistanceM",
                    "sharedBatchCounts",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
