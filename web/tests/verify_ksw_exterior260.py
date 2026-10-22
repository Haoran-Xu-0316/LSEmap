"""Reopen KSW two-tread component and verify actual solids and source preservation."""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_ksw_exterior195 import connected_parts
from refine_ksw_exterior260 import (
    BASE,
    COLLECTION,
    NAME,
    OUT,
    SHA,
    capture,
    local,
    sha,
    world,
)


def site_trees(points):
    objects = set()
    for collection_name in ["00_SITE", "03_PUBLIC_REALM"]:
        collection = bpy.data.collections.get(collection_name)
        if collection:
            objects.update(
                o
                for o in collection.all_objects
                if o.type == "MESH" and not o.hide_render
            )
    trees = []
    for obj in objects:
        box = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if not any(
            min(p.x for p in box) - 0.01 <= q.x <= max(p.x for p in box) + 0.01
            and min(p.y for p in box) - 0.01 <= q.y <= max(p.y for p in box) + 0.01
            for q in points
        ):
            continue
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        trees.append(
            (
                obj.name,
                BVHTree.FromPolygons(
                    [evaluated.matrix_world @ v.co for v in mesh.vertices],
                    [tuple(t.vertices) for t in mesh.loop_triangles],
                    all_triangles=True,
                ),
            )
        )
        evaluated.to_mesh_clear()
    assert trees
    return trees


def actual_ground_contact(step_tree, bounds):
    lower = bounds[0]
    centre = sum(lower[0]) / 2
    front = lower[1][1]
    footprint = [
        world(
            (
                lower[0][0] + fx * (lower[0][1] - lower[0][0]),
                lower[1][0] + fy * (lower[1][1] - lower[1][0]),
                1,
            )
        )
        for fx in [0.15, 0.5, 0.85]
        for fy in [0.15, 0.5, 0.85]
    ]
    street = [
        world((centre + dx, front + depth, 1))
        for dx in [-0.4, 0, 0.4]
        for depth in [0.04, 0.15, 0.35]
    ]
    trees = site_trees(footprint + street)
    ground_rows, bottom_rows = [], []
    for index, point in enumerate(footprint + street):
        hits = []
        for name, tree in trees:
            hit = tree.ray_cast(point, Vector((0, 0, -1)), 2)
            if hit[0] is not None:
                hits.append((hit[3], name, hit[0]))
        assert hits
        distance, name, hit = min(hits, key=lambda row: row[0])
        assert abs(hit.z - lower[2][0]) < 1e-5, (name, hit.z, lower[2][0])
        ground_rows.append(
            {
                "origin": list(point),
                "firstObject": name,
                "point": list(hit),
                "distance": distance,
            }
        )
        if index < len(footprint):
            # Start below the independently hit ground, then hit the actual saved
            # step underside. This detects the original50mm hovering geometry.
            start = hit - Vector((0, 0, 0.025))
            step_hit = step_tree.ray_cast(start, Vector((0, 0, 1)), 0.08)
            assert step_hit[0] is not None and abs(step_hit[0].z - hit.z) < 1e-5
            bottom_rows.append(
                {
                    "ground": list(hit),
                    "stepUnderside": list(step_hit[0]),
                    "verticalGap": step_hit[0].z - hit.z,
                }
            )
        else:
            first_rise = lower[2][1] - hit.z
            second_rise = bounds[1][2][1] - lower[2][1]
            assert 0.11 <= first_rise <= 0.17 and abs(first_rise - second_rise) < 1e-5
    return {
        "actualNativeSiteFirstHitRays": ground_rows,
        "actualStepBottomContactRays": bottom_rows,
        "sourceTriangleEvaluation": True,
        "groundPlaneSpread": max(r["point"][2] for r in ground_rows)
        - min(r["point"][2] for r in ground_rows),
    }


def proof_geometry(audit):
    obj = bpy.data.objects[NAME]
    assert not obj.hide_render and not obj.modifiers
    mesh = obj.data
    assert len(mesh.vertices) == 16 and len(mesh.polygons) == 12
    edges = Counter()
    for face in mesh.polygons:
        indices = tuple(face.vertices)
        for a, b in zip(indices, indices[1:] + indices[:1]):
            edges[tuple(sorted((a, b)))] += 1
    assert set(edges.values()) == {2}
    parts = list(connected_parts(mesh))
    assert len(parts) == 2
    mesh.calc_loop_triangles()
    bounds = []
    for part in parts:
        anchor = mesh.vertices[part[0]].co
        triangles = [t for t in mesh.loop_triangles if t.vertices[0] in part]
        volume = sum(
            (mesh.vertices[t.vertices[0]].co - anchor).dot(
                (mesh.vertices[t.vertices[1]].co - anchor).cross(
                    mesh.vertices[t.vertices[2]].co - anchor
                )
            )
            / 6
            for t in triangles
        )
        assert volume > 0
        points = [local(obj.matrix_world @ mesh.vertices[i].co) for i in part]
        bounds.append(
            [[min(p[d] for p in points), max(p[d] for p in points)] for d in range(3)]
        )
    bounds.sort(key=lambda b: b[2][0])
    assert abs(bounds[0][2][1] - bounds[1][2][0]) < 1e-6
    assert bounds[1][1][1] < bounds[0][1][1]
    source = bpy.data.objects[
        next(n for n in audit["archivedObjects"] if "door_threshold" in n)
    ]
    original_top = max((source.matrix_world @ v.co).z for v in source.data.vertices)
    assert abs(bounds[1][2][1] - original_top) < 1e-6
    rises = [b[2][1] - b[2][0] for b in bounds]
    assert all(0.11 <= rise <= 0.17 for rise in rises)
    # The new front is registered to the retained pier base, not to old outer steps.
    pier = bpy.data.objects[audit["layout"]["portalBaseObject"]]
    pier_front = max(local(pier.matrix_world @ v.co).y for v in pier.data.vertices)
    assert abs(bounds[0][1][1] - pier_front) < 1e-5
    for name in audit["layout"]["doorObjects"]:
        assert (
            object_fingerprint(bpy.data.objects[name])
            == audit["geometrySourceFingerprints"][name]
        )
    tree = BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in mesh.vertices],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        all_triangles=True,
    )
    ground_contact = actual_ground_contact(tree, bounds)
    landings, street = [], []
    for index, b in enumerate(bounds):
        exposed_back = bounds[1][1][1] if index == 0 else b[1][0]
        for fraction in [0.2, 0.5, 0.8]:
            x = b[0][0] + fraction * (b[0][1] - b[0][0])
            depth = (exposed_back + b[1][1]) / 2
            start = world((x, depth, b[2][1] + 0.1))
            hit = tree.ray_cast(start, Vector((0, 0, -1)), 0.2)
            assert hit[0] is not None and abs(hit[3] - 0.1) < 1e-5
            landings.append({"tread": index, "point": list(hit[0]), "height": hit[0].z})
            start = world((x, pier_front + 0.04, 0.4))
            assert tree.ray_cast(start, Vector((0, 0, -1)), 0.6)[0] is None
            street.append(list(start))
    assert len(mesh.loop_triangles) == audit["addedTriangles"] == 24
    return {
        "closedPositiveVolumeSolids": 2,
        "everyEdgeTwoFaces": True,
        "risesMetres": rises,
        "actualTreadLandingRays": landings,
        "streetFrontClearanceRays": street,
        "frontAlignedToRetainedPierBase": True,
        "retainedDoorObjectsUnchanged": True,
        "sourceThresholdTopPreserved": True,
        "actualGroundSupport": ground_contact,
        "addedTriangles": 24,
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == SHA == audit["baselineSha256"]
    assert sha(component) == audit["componentSha256"]
    assert sha(OUT / "source-review.json") == audit["sourceReviewSha256"]
    for ref in json.loads((OUT / "source-review.json").read_text())["references"]:
        assert sha(ROOT / ref["path"]) == ref["sha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        obj.hide_render = False
        obj.hide_set(False)
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    update_scene()
    proof = proof_geometry(audit)
    after = capture()
    for name, expected in before["objects"].items():
        expected = dict(expected)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(after["rooms"]) == 35 and sha(BASE) == SHA
    assert set(after["objects"]) - set(before["objects"]) == {NAME}
    (OUT / "verification.json").write_text(
        json.dumps(
            {
                "passed": True,
                "savedComponentReopened": True,
                "componentSha256": sha(component),
                "protectedOriginalObjects": len(before["objects"]),
                "protectedOriginalMaterials": len(before["materials"]),
                "protectedRoomStudies": 35,
                "proof": proof,
            },
            indent=2,
        )
        + "\n"
    )
    print("KSW260_TWO_TREADS_REOPENED_AND_VERIFIED", proof, flush=True)


if __name__ == "__main__":
    main()
