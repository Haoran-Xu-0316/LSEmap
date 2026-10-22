"""Reopen OLD window boxes and independently verify geometry and sill bearing."""

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
from refine_old_exterior259 import (
    BASE,
    BINDINGS,
    COLLECTION,
    GLASS,
    OUT,
    SHA,
    STONE,
    capture,
    frame,
    sha,
)


def tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        all_triangles=True,
    )
    evaluated.to_mesh_clear()
    return result


def closed_solids(obj, expected):
    mesh = obj.data
    adjacent = [set() for _ in mesh.vertices]
    edge_faces = Counter()
    for face in mesh.polygons:
        ids = tuple(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edge_faces[tuple(sorted((a, b)))] += 1
            adjacent[a].add(b)
            adjacent[b].add(a)
    assert set(edge_faces.values()) == {2}
    unseen, groups = set(range(len(mesh.vertices))), []
    while unseen:
        seed = unseen.pop()
        found, queue = {seed}, [seed]
        while queue:
            for other in adjacent[queue.pop()] & unseen:
                unseen.remove(other)
                found.add(other)
                queue.append(other)
        groups.append(found)
    assert len(groups) == expected
    mesh.calc_loop_triangles()
    for group in groups:
        anchor = mesh.vertices[min(group)].co
        volume = 0
        for triangle in mesh.loop_triangles:
            if triangle.vertices[0] in group:
                a, b, c = [mesh.vertices[i].co - anchor for i in triangle.vertices]
                volume += a.dot(b.cross(c)) / 6
        assert volume > 0, (obj.name, volume)
    return {
        "connectedClosedSolids": len(groups),
        "everyEdgeTwoFaces": True,
        "eachSolidPositiveVolume": True,
    }


def proof_geometry(audit):
    origin, right, outward = frame()

    def world(point):
        return origin + right * point[0] + outward * point[1] + Vector((0, 0, point[2]))

    source_glass, stone = tree(bpy.data.objects[GLASS]), tree(bpy.data.objects[STONE])
    added_trees = {name: tree(bpy.data.objects[name]) for name in audit["addedObjects"]}
    topology = {
        name: closed_solids(bpy.data.objects[name], count)
        for name, count in zip(BINDINGS, [40, 8, 240])
    }
    bearing, clearance, roots = [], [], []
    assert len(audit["planters"]) == 8
    for row in audit["planters"]:
        x, low, high, width = row["x"], row["low"], row["high"], row["width"]
        assert row["maximumOpeningHeightFraction"] < 0.15
        for point in row["bearingLocalPoints"]:
            start = world(point) + Vector((0, 0, 0.03))
            hit = stone.ray_cast(start, Vector((0, 0, -1)), 0.06)
            assert hit[0] is not None and abs(hit[3] - 0.03) < 2e-5, (
                row["id"],
                point,
                hit[3],
            )
            # Verify actual new box underside has the same top-sill elevation.
            boxhit = added_trees["OLD259_Houghton_window_boxes"].ray_cast(
                world(point) - Vector((0, 0, 0.02)), Vector((0, 0, 1)), 0.04
            )
            assert boxhit[0] is not None and abs(boxhit[3] - 0.02) < 2e-5
            bearing.append(
                {
                    "box": row["id"],
                    "localPoint": point,
                    "stoneGap": hit[3] - 0.03,
                    "boxGap": boxhit[3] - 0.02,
                }
            )
        # Probe clear panes above the low foliage envelope. The checks compare
        # new geometry against the retained real glass, not a bounding box.
        for fraction_x in [1 / 6, 0.5, 5 / 6]:
            for fraction_z in [0.25, 5 / 12, 7 / 12, 0.75, 11 / 12]:
                point = (
                    x - width / 2 + width * fraction_x,
                    0.65,
                    low + (high - low) * fraction_z,
                )
                start = world(point)
                glasshit = source_glass.ray_cast(start, -outward, 1)
                assert glasshit[0] is not None, (row["id"], point)
                assert all(
                    t.ray_cast(start, -outward, glasshit[3])[0] is None
                    for t in added_trees.values()
                ), (row["id"], point)
                clearance.append(
                    {
                        "box": row["id"],
                        "start": list(start),
                        "direction": list(-outward),
                        "glassDistance": glasshit[3],
                    }
                )
        left = x - row["boxWidth"] / 2
        for cluster in range(6):
            root = (
                left + 0.08 + (row["boxWidth"] - 0.16) * cluster / 5,
                0.205 + 0.055 * (cluster % 2),
                low + 0.12,
            )
            # Root is within soil thickness; check finite solid soil above/below.
            down = added_trees["OLD259_Houghton_window_box_soil"].ray_cast(
                world(root), Vector((0, 0, -1)), 0.03
            )
            up = added_trees["OLD259_Houghton_window_box_soil"].ray_cast(
                world(root), Vector((0, 0, 1)), 0.02
            )
            assert down[0] is not None and up[0] is not None
            roots.append(
                {"box": row["id"], "cluster": cluster, "soilRoot": list(world(root))}
            )
    triangles = sum(
        sum(len(p.vertices) - 2 for p in bpy.data.objects[name].data.polygons)
        for name in audit["addedObjects"]
    )
    assert triangles == audit["addedTriangles"] and triangles < 5000
    return {
        "sharedSceneBatches": 3,
        "addedTriangles": triangles,
        "topology": topology,
        "actualSillBearingProbes": bearing,
        "unobstructedUpperPaneRays": clearance,
        "soilRootAttachmentProbes": roots,
        "conservativeMaximumWindowHeightCoverage": max(
            r["maximumOpeningHeightFraction"] for r in audit["planters"]
        ),
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert (
        sha(BASE) == SHA == audit["baselineSha256"]
        and sha(component) == audit["componentSha256"]
    )
    assert sha(OUT / "source-review.json") == audit["sourceReviewSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    update_scene()
    proof = proof_geometry(audit)
    after = capture()
    assert all(after["objects"][name] == row for name, row in before["objects"].items())
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert set(after["objects"]) - set(before["objects"]) == set(audit["addedObjects"])
    assert len(after["rooms"]) == 35 and sha(BASE) == SHA
    (OUT / "verification.json").write_text(
        json.dumps(
            {
                "passed": True,
                "componentSha256": sha(component),
                "protectedOriginalObjects": len(before["objects"]),
                "protectedOriginalMaterials": len(before["materials"]),
                "protectedRoomStudies": 35,
                "savedComponentReopened": True,
                "proof": proof,
                "wholeBuildingCompletionClaimed": False,
            },
            indent=2,
        )
        + "\n"
    )
    print(
        "OLD259_WINDOW_BOXES_REOPEN_VERIFIED",
        len(proof["unobstructedUpperPaneRays"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
