"""Reopen the enclosure and exact native, then verify support and clear access."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/court-enclosure248"
BASE = ROOT / "result/blender/LSE_campus_detailed_v246.blend"
FULL = ROOT / "result/blender/LSE_campus_detailed_v248.blend"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def tree(objects):
    vertices, faces = [], []
    for obj in objects:
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend([offset + i for i in p.vertices] for p in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces)


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    plan = json.loads((OUT / "plan.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert (
        hashlib.sha256(component.read_bytes()).hexdigest() == audit["componentSha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(component))
    for name, fingerprint in audit["addedFingerprints"].items():
        assert object_fingerprint(bpy.data.objects[name]) == fingerprint, name
    post = bpy.data.objects["COURT248_mapped_enclosure_posts"]
    bm = bmesh.new()
    bm.from_mesh(post.data)
    assert all(edge.is_manifold for edge in bm.edges)
    assert bm.calc_volume(signed=True) > 0
    volume = bm.calc_volume(signed=True)
    bm.free()
    grid = bpy.data.objects["COURT248_mapped_perforated_wire_panels"]
    assert len(grid.data.polygons) == 5 and len(grid.data.uv_layers) == 1
    material = grid.data.materials[0]
    assert material["webWireGrid"] and tuple(material["webWirePitch"]) == (0.075, 0.15)
    assert abs(material["webWireWidth"] - 0.0025) < 1e-8
    assert len(post.data.polygons) == len(plan["supports"]) * 6
    assert len(grid.data.vertices) == 20
    # Compare saved UV metres to actual panel edges, not just a material flag.
    for polygon in grid.data.polygons:
        coords = [grid.data.vertices[i].co for i in polygon.vertices]
        uv = [grid.data.uv_layers[0].data[i].uv for i in polygon.loop_indices]
        assert abs((coords[1] - coords[0]).length - uv[1].x) < 2e-5
        assert abs(uv[2].y - 3) < 1e-7
    bpy.ops.wm.open_mainfile(filepath=str(FULL if FULL.exists() else BASE))
    update_scene()
    if not FULL.exists():
        with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
            loaded.objects = list(audit["addedObjects"])
        for obj in loaded.objects:
            bpy.data.collections["03_PUBLIC_REALM"].objects.link(obj)
        update_scene()
    spec = importlib.util.spec_from_file_location(
        "protected_native", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = audit["baselineSha256"]
    current = helper.capture_source()
    assert set(current["objects"]) == set(before["objects"]) | set(
        audit["addedObjects"]
    ), {
        "extra": sorted(
            set(current["objects"])
            - set(before["objects"])
            - set(audit["addedObjects"])
        ),
        "missing": sorted(
            (set(before["objects"]) | set(audit["addedObjects"]))
            - set(current["objects"])
        ),
    }
    assert all(current["objects"][n] == value for n, value in before["objects"].items())
    assert all(
        current["materials"][n] == value for n, value in before["materials"].items()
    )
    assert (
        current["rooms"] == before["rooms"]
        and current["campusRooms"] == before["campusRooms"]
    )
    fence = tree([bpy.data.objects[n] for n in audit["addedObjects"]])
    gate = Vector(plan["plan"]["entranceConservativeReservation"]["mappedCentre"])
    inward = (Vector((-13, 132)) - gate).normalized()
    across = Vector((-inward.y, inward.x))
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    clear = []
    for height in [0.25, 0.8, 1.5, 2.2, 2.9]:
        for offset in [-0.3, 0, 0.3]:
            xy = gate - inward * 2 + across * offset
            origin = Vector((xy.x, xy.y, height))
            direction = Vector((inward.x, inward.y, 0))
            assert fence.ray_cast(origin, direction, 6)[0] is None
            hit = scene.ray_cast(depsgraph, origin, direction, distance=6)
            assert not hit[0], (
                "Existing entry obstruction",
                height,
                offset,
                hit[4].name,
            )
            clear.append([height, offset])

    # Clip actual saved face polygons against the complete 0.6m wide corridor
    # from outside to inside. This covers the space between the sampled rays.
    def corridor_fragment(points):
        polygon = []
        for p in points:
            delta = Vector((p.x, p.y)) - gate
            polygon.append(Vector((delta.dot(inward), delta.dot(across), p.z)))
        for axis, limit, sign in [
            (0, -2, 1),
            (0, 4, -1),
            (1, -0.3, 1),
            (1, 0.3, -1),
            (2, 0.2, 1),
            (2, 2.1, -1),
        ]:
            result = []
            if not polygon:
                break
            for a, b in zip(polygon, polygon[1:] + polygon[:1]):
                da, db = sign * (a[axis] - limit), sign * (b[axis] - limit)
                if da >= 0:
                    result.append(a)
                if (da >= 0) != (db >= 0):
                    result.append(a + (b - a) * (da / (da - db)))
            polygon = result
        if len(polygon) < 3:
            return 0
        return (
            sum(
                (a.cross(b) for a, b in zip(polygon, polygon[1:] + polygon[:1])),
                Vector(),
            ).length
            * 0.5
        )

    corridor_faces = 0
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        bounds = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        local = [Vector((p.x, p.y)) - gate for p in bounds]
        if max(p.z for p in bounds) < 0.2 or min(p.z for p in bounds) > 2.1:
            continue
        if (
            max(p.dot(inward) for p in local) < -2
            or min(p.dot(inward) for p in local) > 4
        ):
            continue
        if (
            max(p.dot(across) for p in local) < -0.3
            or min(p.dot(across) for p in local) > 0.3
        ):
            continue
        for face in obj.data.polygons:
            points = [obj.matrix_world @ obj.data.vertices[i].co for i in face.vertices]
            if max(p.z for p in points) < 0.2 or min(p.z for p in points) > 2.1:
                continue
            corridor_faces += 1
            assert corridor_fragment(points) < 1e-10, (
                "Full entry corridor obstruction",
                obj.name,
                face.index,
            )
    # Actual nearby retained solids must not intersect any new post. Leaf mass
    # overlap is normal at a park fence and is not a reason to move mapped trees.
    posts = tree([bpy.data.objects["COURT248_mapped_enclosure_posts"]])
    tested = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name in audit["addedObjects"]:
            continue
        points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if max(p.z for p in points) < 0.08 or min(p.z for p in points) > 3.06:
            continue
        if (
            min(p.x for p in points) > 14.1
            or max(p.x for p in points) < -41.9
            or min(p.y for p in points) > 156.1
            or max(p.y for p in points) < 107.3
        ):
            continue
        if all(
            m and ("foliage" in m.name.lower() or "grass" in m.name.lower())
            for m in obj.data.materials
        ):
            continue
        overlaps = posts.overlap(tree([obj]))
        assert not overlaps, (
            "Post collides with retained fixture",
            obj.name,
            len(overlaps),
        )
        tested.append(obj.name)
    proof = {
        "componentSha256": audit["componentSha256"],
        "componentReopened": True,
        "completeNativeReopened": FULL.exists(),
        "originalObjectsVerified": len(before["objects"]),
        "originalMaterialGraphsVerified": len(before["materials"]),
        "protectedRooms": len(before["rooms"]),
        "protectedRoomMembers": sum(map(len, before["rooms"].values())),
        "closedPostSolids": len(plan["supports"]),
        "postVolumeM3": volume,
        "metricUvPanels": 5,
        "entryBodyWidthM": 0.6,
        "clearEntrySceneRayChecks": len(clear),
        "fullEntryCorridorSavedFacesChecked": corridor_faces,
        "fullEntryCorridorSizeM": [6, 0.6, 1.9],
        "postCollisionFixtures": tested,
        "oldObjectsMaterialsOwnersVisibilityNormalsUvsAndRoomsUnchanged": True,
    }
    (
        OUT
        / (
            "full-native-verification.json"
            if FULL.exists()
            else "saved-verification.json"
        )
    ).write_text(json.dumps(proof, indent=2) + "\n")
    print(
        "COURT248_VERIFIED",
        len(clear),
        "entry rays",
        len(tested),
        "fixtures",
        flush=True,
    )


if __name__ == "__main__":
    main()
