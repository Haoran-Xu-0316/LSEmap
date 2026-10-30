"""MachineLearning verification against the actual2022PDF and279inspection."""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    import pdfplumber
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    plan = json.loads((ROOT / "result/blender/mar283/plan.json").read_text())
    evidence = json.loads(
        (ROOT / "result/blender/mar283/source-evidence.json").read_text()
    )
    assert sha(ROOT / plan["baseline"]) == plan["baselineSha256"]
    assert all(sha(ROOT / p) == h for p, h in plan["sourceHashes"].items())
    assert plan["fullHeightShaftAcceptance"] is False
    source = ROOT / evidence["sourcePath"]
    assert sha(source) == evidence["sourceSha256"]
    with pdfplumber.open(source) as document:
        curves = document.pages[0].curves
        for row in evidence["sourceFills"]:
            curve = curves[int(row["id"].split("-")[1])]
            assert curve["pts"] == [tuple(p) for p in row["pts"]]
            assert curve["fill"] and list(curve["non_stroking_color"]) == row["color"]
            assert curve["stroke"] == row["stroke"]
            assert curve["linewidth"] == row["linewidth"]
            assert list(curve["stroking_color"]) == row["strokingColor"]
    holes = [Polygon(r) for r in plan["holes"]]
    assert len(holes) == 4 and all(p.is_valid and p.area > 3 for p in holes)
    assert sum(p.area for p in holes) - unary_union(holes).area < 1e-9
    assert {r["sourceObject"] for r in plan["objects"] if r["sourceObject"]} == {
        "MAR217_coordinated_acoustic_soffit",
        "MAR217_coordinated_mezzanine_slab",
        "MAR217_ground_service_enclosure",
        "MAR217_ground_sills",
    }
    native = json.loads(
        (ROOT / "result/blender/mar283/native-inspection.json").read_text()
    )
    targets = {r["name"]: r for r in native["targets"]}
    for row in plan["objects"]:
        if row["sourceObject"]:
            assert (
                targets[row["sourceObject"]]["fingerprint"] == row["sourceFingerprint"]
            )
        edges = {}
        for face in row["faceRecords"]:
            points = face["points"]
            assert len(points) >= 3 and all(
                len(uv) == len(points) for uv in face["uvs"].values()
            )
            for a, b in zip(points, points[1:] + points[:1]):
                edge = (face.get("solidIsland", 0), tuple(sorted((tuple(a), tuple(b)))))
                edges[edge] = edges.get(edge, 0) + 1
        assert set(edges.values()) == {2}, row["replacement"]
    result = {
        "status": "passed-original-PDF-and-actual279-plan-check",
        "baselineSha256": plan["baselineSha256"],
        "originalPdfCurvesChecked": len(evidence["sourceFills"]),
        "sourceDoors": len(plan["doors"]),
        "groundShafts": 4,
        "originalNativeRetained": True,
        "replacementMeshesClosedByIndependentEdgeCount": len(plan["objects"]),
        "fullHeightShaftAcceptance": False,
        "higherPlateCut": False,
    }
    (ROOT / "result/blender/mar283/cpu-plan-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("MAR283_CPU_PLAN_VERIFIED", flush=True)


if __name__ == "__main__":
    main()


def ray_review():
    """Check planned meshes against all actual native ROItriangles before build."""
    import numpy as np

    plan = json.loads((ROOT / "result/blender/mar283/plan.json").read_text())
    native = json.loads(
        (ROOT / "result/blender/mar283/native-inspection.json").read_text()
    )
    archived = {r["sourceObject"] for r in plan["objects"] if r["sourceObject"]}
    triangles = []
    owners = []
    for row in native["inventory"]:
        if row["name"] in archived:
            continue
        for face in row.get("roiTriangles", []):
            triangles.append(face["points"])
            owners.append(row["name"])
    for row in plan["objects"]:
        for face in row["faceRecords"]:
            pts = face["points"]
            for i in range(1, len(pts) - 1):
                triangles.append([pts[0], pts[i], pts[i + 1]])
                owners.append(row["replacement"])
    triangles = np.asarray(triangles)
    a = triangles[:, 0]
    e1 = triangles[:, 1] - a
    e2 = triangles[:, 2] - a

    def hits(start, direction, length):
        direction = np.asarray(direction)
        start = np.asarray(start)
        h = np.cross(direction, e2)
        det = np.einsum("ij,ij->i", e1, h)
        valid = abs(det) > 1e-9
        inv = np.divide(1.0, det, out=np.zeros_like(det), where=valid)
        s = start - a
        u = np.einsum("ij,ij->i", s, h) * inv
        q = np.cross(s, e1)
        v = q @ direction * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        ix = np.where(
            valid
            & (u >= -1e-8)
            & (v >= -1e-8)
            & (u + v <= 1 + 1e-8)
            & (t >= 0)
            & (t <= length)
        )[0]
        return [(owners[i], float(t[i])) for i in ix]

    from shapely.geometry import Point, Polygon

    air = 0
    for ring in plan["holes"]:
        shape = Polygon(ring)
        lo = shape.bounds[:2]
        hi = shape.bounds[2:]
        for i in range(1, 10):
            for j in range(1, 10):
                xy = [
                    lo[0] + (hi[0] - lo[0]) * i / 10,
                    lo[1] + (hi[1] - lo[1]) * j / 10,
                ]
                if (
                    not shape.contains(Point(xy))
                    or shape.boundary.distance(Point(xy)) <= 0.025
                ):
                    continue
                found = hits([*xy, 0.2], [0, 0, 1], 7.06)
                assert not found, ("planned-context-shaft-obstruction", xy, found[:6])
                air += 1
    door_rays = 0
    for door in plan["doors"]:
        ring = door["world"]
        centre = np.asarray(Polygon(ring).centroid.coords[0])
        tangent = np.asarray(ring[-1]) - np.asarray(ring[0])
        tangent /= np.linalg.norm(tangent)
        normal = np.asarray([-tangent[1], tangent[0]])
        for offset in [-0.3, 0, 0.3]:
            for height in [0.2, 1.0, 2.0]:
                xy = centre + tangent * offset - normal * 0.45
                found = hits([*xy, plan["groundLow"] + height], [*normal, 0], 0.9)
                assert not found, (
                    "planned-context-door-obstruction",
                    door["id"],
                    offset,
                    height,
                    found[:6],
                )
                door_rays += 1
    result = {
        "status": "passed-planned-full-native-ROI-airspace",
        "actualNativeROITriangles": len(triangles),
        "unobstructedGroundToCeilingRays": air,
        "unobstructedDoorRays": door_rays,
        "zRange": [0.2, 7.26],
        "actualBlenderVerificationStillRequired": True,
    }
    (ROOT / "result/blender/mar283/cpu-airspace-review.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("MAR283_CPU_AIRSPACE_REVIEWED", air, flush=True)
