"""Independently reopen MAR250 and verify exact floor scope and clear shafts.

Run in Blender for saved/native checks, then in project Python for full planar
coverage comparison. This does not save or alter the complete249 model.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar-third250"
BASE = ROOT / "result/blender/LSE_campus_detailed_v249.blend"
BASE_SHA = "cad99a189122994fd484794fb617a9223c31e90fd506fb434ef22d9e87e30e24"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_saved_native():
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_mar_third250 import capture_source

    plan = json.loads((OUT / "plan.json").read_text())
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(component) == audit["componentSha256"] and sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(component))
    saved = bpy.data.objects[plan["ownedObject"]]
    assert object_fingerprint(saved) == audit["addedFingerprints"][saved.name]
    assert len(saved.data.polygons) == 24
    exported = {
        "positions": [list(saved.matrix_world @ v.co) for v in saved.data.vertices],
        "faces": [list(p.vertices) for p in saved.data.polygons],
    }
    (OUT / "saved-mesh.json").write_text(json.dumps(exported) + "\n")
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture_source() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(audit["addedObjects"])
    replacement = loaded.objects[0]
    bpy.data.collections[plan["targetCollection"]].objects.link(replacement)
    for i, name in enumerate(audit["replacementMaterialBindings"][replacement.name]):
        replacement.data.materials[i] = bpy.data.materials[name]
    source = bpy.data.objects[plan["sourceObject"]]
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    after = capture_source()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name == source.name:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert set(after["objects"]) == set(before["objects"]) | {replacement.name}
    assert (
        object_fingerprint(replacement) == audit["addedFingerprints"][replacement.name]
    )

    def tree(obj):
        return BVHTree.FromPolygons(
            [obj.matrix_world @ v.co for v in obj.data.vertices],
            [list(p.vertices) for p in obj.data.polygons],
        )

    old_tree, new_tree = tree(source), tree(replacement)
    floor = plan["floorDatum"]
    voids, bearings = [], []
    for hole in plan["holes"]:
        ring = [Vector(p) for p in hole["world"]]
        # Bilinear interior grid is independent of the builder's triangulation.
        for i in range(1, 10):
            for j in range(1, 10):
                a = ring[0].lerp(ring[1], i / 10)
                b = ring[3].lerp(ring[2], i / 10)
                point = a.lerp(b, j / 10)
                origin = Vector((*point, floor + 0.2))
                assert old_tree.ray_cast(origin, Vector((0, 0, -1)), 0.4)[0] is not None
                assert new_tree.ray_cast(origin, Vector((0, 0, -1)), 0.4)[0] is None, (
                    hole["id"],
                    list(point),
                )
                voids.append({"shaft": hole["id"], "point": list(point)})
        area = sum(a.x * b.y - b.x * a.y for a, b in zip(ring, ring[1:] + ring[:1])) / 2
        for a, b in zip(ring, ring[1:] + ring[:1]):
            tangent = b - a
            outward = Vector((tangent.y, -tangent.x)).normalized() * (
                1 if area > 0 else -1
            )
            for j in range(1, 10):
                point = a.lerp(b, j / 10) + outward * 0.035
                hit = new_tree.ray_cast(
                    Vector((*point, floor + 0.2)), Vector((0, 0, -1)), 0.4
                )[0]
                assert hit is not None and abs(hit.z - floor) < 2e-5, (
                    hole["id"],
                    list(point),
                )
                bearings.append(
                    {"shaft": hole["id"], "point": list(point), "offsetMetres": 0.035}
                )
    # Preserve the strips between shafts and the central access corridor.
    centres = [
        sum([Vector(p) for p in hole["world"]], Vector((0, 0))) / 4
        for hole in plan["holes"]
    ]
    access = [(centres[0] + centres[1]) / 2, (centres[0] + centres[2]) / 2]
    for point in access:
        assert (
            new_tree.ray_cast(Vector((*point, floor + 0.2)), Vector((0, 0, -1)), 0.4)[0]
            is not None
        )
    uv_proof = []
    records = json.loads((OUT / "uv-interpolation.json").read_text())["faceRecords"]
    for face, record in zip(replacement.data.polygons, records):
        old_face = source.data.polygons[record["sourceFace"]]
        coords = [
            source.matrix_world @ source.data.vertices[i].co for i in old_face.vertices
        ]
        a, b, c = coords
        det = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)
        old_normal = (b - a).cross(c - a).normalized()
        actual = [
            replacement.matrix_world @ replacement.data.vertices[i].co
            for i in face.vertices
        ]
        new_normal = (actual[1] - actual[0]).cross(actual[2] - actual[0]).normalized()
        assert old_normal.dot(new_normal) > 0.999999
        for li, point in zip(face.loop_indices, actual):
            wb = ((point.x - a.x) * (c.y - a.y) - (c.x - a.x) * (point.y - a.y)) / det
            wc = ((b.x - a.x) * (point.y - a.y) - (point.x - a.x) * (b.y - a.y)) / det
            weights = [1 - wb - wc, wb, wc]
            for old_layer, new_layer in zip(
                source.data.uv_layers, replacement.data.uv_layers
            ):
                expected = sum(
                    [
                        old_layer.data[i].uv * w
                        for i, w in zip(old_face.loop_indices, weights)
                    ],
                    Vector((0, 0)),
                )
                error = (expected - new_layer.data[li].uv).length
                assert error < 0.00002, (face.index, new_layer.name, error)
                uv_proof.append(error)
    proof = {
        "savedComponentReopened": True,
        "baselineSha256": BASE_SHA,
        "componentSha256": sha(component),
        "protectedObjects": len(before["objects"]),
        "protectedMaterials": len(before["materials"]),
        "protectedRooms": len(before["rooms"]),
        "roomMembers": sum(len(x) for x in before["rooms"].values()),
        "originalFloorGeometryRetainedAsArchive": True,
        "allOtherFloorsAndRoomsPreserved": True,
        "oldFloorVisibleBefore": True,
        "oldFloorHiddenAfter": True,
        "shafts": len(plan["holes"]),
        "oldFilledToNewOpenRayCount": len(voids),
        "retainedBearingRayCount": len(bearings),
        "interShaftAndAccessStripProbes": len(access),
        "uvSamples": len(uv_proof),
        "maximumUvError": max(uv_proof, default=0),
        "normalsPreserved": True,
        "wholeNativeSaved": False,
        "sourceNativeUnchanged": sha(BASE) == BASE_SHA,
    }
    (OUT / "saved-verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    (OUT / "ray-probes.json").write_text(
        json.dumps(
            {"voids": voids, "bearings": bearings, "access": [list(p) for p in access]}
        )
        + "\n"
    )
    print("MAR250_SAVED_VERIFIED", len(voids), len(bearings), flush=True)
    bpy.ops.wm.quit_blender()


def verify_planar_coverage():
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union

    plan = json.loads((OUT / "plan.json").read_text())
    assert sha(ROOT / plan["sourcePdf"]) == plan["sourcePdfSha256"]
    vectors = {
        row["id"]: row
        for row in json.loads((OUT / "core-wall-vectors.json").read_text())
    }
    edge_errors = []
    for hole in plan["holes"]:
        lines = unary_union(
            [LineString(vectors[name]["pts"]) for name in hole["vectors"]]
        )
        errors = [lines.distance(Point(point)) for point in hole["pdf"]]
        assert max(errors) < 0.015, (hole["id"], errors)
        edge_errors.extend(errors)
    data = json.loads((OUT / "saved-mesh.json").read_text())
    old = unary_union(
        [
            Polygon([p[:2] for p in row["sourcePoints"]])
            for row in plan["sourceFacePlans"]
        ]
    )
    holes = unary_union([Polygon(hole["world"]) for hole in plan["holes"]])
    actual = unary_union(
        [Polygon([data["positions"][i][:2] for i in face]) for face in data["faces"]]
    )
    residual = actual.symmetric_difference(old.difference(holes)).area
    assert residual < 0.0002, residual
    assert len(actual.interiors) == 3
    assert abs(actual.area - plan["retainedAreaSquareMetres"]) < 0.0002
    assert actual.intersection(holes).area < 0.0001
    assert abs(Polygon(actual.exterior).area - Polygon(old.exterior).area) < 0.0002
    assert actual.exterior.hausdorff_distance(old.exterior) < 0.00002
    result = {
        "actualSavedMeshAreaSquareMetres": actual.area,
        "expectedAreaSquareMetres": plan["retainedAreaSquareMetres"],
        "symmetricDifferenceSquareMetres": residual,
        "actualShaftHoles": len(actual.interiors),
        "outerDeckBoundaryPreserved": True,
        "sourceShaftCornersCheckedAgainstRetainedVectors": len(edge_errors),
        "maximumCornerToSourceEdgePdfPoints": max(edge_errors),
        "actualRemovedAreaSquareMetres": old.area - actual.area,
    }
    (OUT / "planar-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print("MAR250_PLANAR_VERIFIED", residual)


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ModuleNotFoundError:
        verify_planar_coverage()
    else:
        verify_saved_native()
