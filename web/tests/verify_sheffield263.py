"""Independent263tube, native support, retained-record and street-clearance tests.

geometry_proof(audit) checks a current full native scene without loading files.
verify() additionally exercises baseline+component append and original protection.
"""

import collections
import hashlib
import json
import sys
from importlib import import_module
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/sheffield263"
BASE = ROOT / "result/blender/LSE_campus_detailed_v262.blend"
SHA = "35547bb32309adcd934df8845c71e672e3dc7b3ca519ad5154ec9a65f143cb75"
sys.path.insert(0, str(ROOT / "web/tools"))
# Blender needs the repository helper path before these runtime imports.
campus_helpers = import_module("integrate_exterior_round194")
object_fingerprint = campus_helpers.object_fingerprint
update_scene = campus_helpers.update_scene
material_fingerprint = import_module(
    "refine_portsmouth_exterior207"
).material_fingerprint


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, r):
    p.write_text(json.dumps(r, indent=2) + "\n")


def triangles(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = [
        tuple(evaluated.matrix_world @ mesh.vertices[i].co for i in t.vertices)
        for t in mesh.loop_triangles
    ]
    evaluated.to_mesh_clear()
    return result


def tree(rows):
    return BVHTree.FromPolygons(
        [p for t in rows for p in t],
        [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(rows))],
        all_triangles=True,
    )


def connected_vertices(obj):
    links = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        links[a].add(b)
        links[b].add(a)
    pending = set(range(len(links)))
    parts = []
    while pending:
        first = pending.pop()
        part = {first}
        todo = [first]
        while todo:
            for other in links[todo.pop()]:
                if other in pending:
                    pending.remove(other)
                    part.add(other)
                    todo.append(other)
        parts.append(part)
    return parts


def exact_face_edges(obj, excluded=frozenset()):
    # Independent edge-record comparison retains face boundaries, per-corner UV
    # associations and material indices even if serialization reorders faces.
    records = []
    for polygon in obj.data.polygons:
        if set(polygon.vertices) & excluded:
            continue
        corners = []
        for index in polygon.loop_indices:
            vertex = obj.data.vertices[obj.data.loops[index].vertex_index]
            corners.append(
                (
                    tuple(vertex.co),
                    tuple(
                        (layer.name, tuple(layer.data[index].uv))
                        for layer in obj.data.uv_layers
                    ),
                )
            )
        edges = tuple(
            sorted(
                tuple(sorted((a, b)))
                for a, b in zip(corners, corners[1:] + corners[:1])
            )
        )
        records.append((polygon.material_index, edges))
    return collections.Counter(records)


def geometry_proof(audit):
    update_scene()
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    retained = bpy.data.objects[
        "SHEFFIELD263_Mapped_furniture_retained_without_single_cycle_stand"
    ]
    bank = bpy.data.objects["SHEFFIELD263_Five_U_cycle_stands"]
    source = bpy.data.objects[audit["originalObject"]]
    assert exact_face_edges(
        source, set(audit["removedVertexIndices"])
    ) == exact_face_edges(retained), (
        "Other native face boundaries, UVs or material indices changed"
    )
    assert retained.matrix_world == source.matrix_world
    assert [m.name for m in retained.data.materials] == audit[
        "originalMaterialBindings"
    ]
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in audit["addedFingerprints"].items()
    )
    assert all(
        sorted(c.name for c in bpy.data.objects[n].users_collection) == [owner]
        for n, owner in audit["objectOwners"].items()
    )
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in audit["verification"]["protected262Planters"].items()
    )
    for row in json.loads((OUT / "source-review.json").read_text())["sources"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    floor = tree(triangles(bpy.data.objects["SITE194_SITE_V47_Sheffield_Street"]))
    bm = bmesh.new()
    bm.from_mesh(bank.data)
    assert all(e.is_manifold for e in bm.edges)
    bm.free()
    parts = connected_vertices(bank)
    assert len(parts) == 5
    bank_rows = triangles(bank)
    all_foot_contacts = []
    solids = []
    stand_trees = []
    for indices in parts:
        polygons = [p for p in bank.data.polygons if set(p.vertices) <= indices]
        volume = 0
        part_triangles = []
        for polygon in polygons:
            points = [
                bank.matrix_world @ bank.data.vertices[i].co for i in polygon.vertices
            ]
            for j in range(1, len(points) - 1):
                volume += points[0].dot(points[j].cross(points[j + 1])) / 6
                part_triangles.append((points[0], points[j], points[j + 1]))
        assert volume > 0.001, "Closed hoop has nonpositive or negligible solid volume"
        # A Ustand must have two actual downward-facing closed end caps. Test every
        # cap vertex and centre against the native stone, without authoring foot data.
        caps = [p for p in polygons if len(p.vertices) > 4 and p.normal.z < -0.99]
        assert len(caps) == 2
        contacts = []
        for cap in caps:
            points = [
                bank.matrix_world @ bank.data.vertices[i].co for i in cap.vertices
            ]
            for p in points + [sum(points, Vector()) / len(points)]:
                hit = floor.ray_cast(Vector((p.x, p.y, 0.20)), Vector((0, 0, -1)), 0.30)
                assert hit[0] is not None, "Cycle leg has no native paving support"
                gap = p.z - hit[0].z
                assert -0.0011 <= gap <= 0.0011, (
                    "Cycle leg floats or penetrates",
                    list(p),
                    gap,
                )
                contacts.append({"point": list(p), "nativeZ": hit[0].z, "gapM": gap})
        all_foot_contacts.extend(contacts)
        solids.append(
            {
                "vertices": len(indices),
                "volumeM3": volume,
                "endCaps": len(caps),
                "footSamples": len(contacts),
            }
        )
        stand_trees.append(tree(part_triangles))
    for i, a in enumerate(stand_trees):
        for b in stand_trees[i + 1 :]:
            assert not a.overlap(b), "Two hoops intersect"
    new_tree = tree(bank_rows)
    collision_objects = []
    collisions = []
    nearby_rows = []
    for obj in scene.objects:
        if (
            obj.type != "MESH"
            or obj.hide_render
            or obj.name in [bank.name, source.name]
        ):
            continue
        corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if (
            max(p.x for p in corners) < -56
            or min(p.x for p in corners) > -49
            or max(p.y for p in corners) < -25
            or min(p.y for p in corners) > -17
            or min(p.z for p in corners) > 2
        ):
            continue
        rows = [
            t
            for t in triangles(obj)
            if max(p.z for p in t) > 0.075 and min(p.z for p in t) < 2
        ]
        nearby_rows.extend(rows)
        if not rows:
            continue
        collision_objects.append(obj.name)
        hits = new_tree.overlap(tree(rows))
        if hits:
            collisions.append(
                {
                    "object": obj.name,
                    "pairs": len(hits),
                    "witness": [
                        {
                            "standTriangle": [list(p) for p in bank_rows[a]],
                            "nativeTriangle": [list(p) for p in rows[b]],
                        }
                        for a, b in hits[:2]
                    ],
                }
            )
    assert not collisions, collisions
    # Ground routes include the existing globe paving/inlays, which sit slightly
    # above Sheffield stone. No new paving or inferred surface area is inserted.
    walk_rows = []
    for name in [
        "SITE194_SITE_V47_Sheffield_Street",
        "SITE_V114_Globe_continuous_paving",
        "SITE_V114_Globe_concentric_inlays",
    ]:
        walk_rows.extend(triangles(bpy.data.objects[name]))
    walk_tree = tree(walk_rows)
    obstacles = tree(nearby_rows + bank_rows)
    route_support = []
    route_clear = []
    for x in [-53.9, -53.6, -53.3, -53.0, -52.7, -52.4, -52.1]:
        for y in [
            -24,
            -23.5,
            -23,
            -22.5,
            -22,
            -21.5,
            -21,
            -20.5,
            -20,
            -19.5,
            -19,
            -18.8,
        ]:
            hit = walk_tree.ray_cast(Vector((x, y, 0.2)), Vector((0, 0, -1)), 0.3)
            assert hit[0] is not None, (
                "Existing globe-side pedestrian band lacks paving"
            )
            route_support.append({"xy": [x, y], "z": hit[0].z})
        for height in [0.10, 0.4, 0.8, 1.65]:
            hit = obstacles.ray_cast(Vector((x, -24, height)), Vector((0, 1, 0)), 5.2)
            assert hit[0] is None, (
                "Globe-side1.8m band blocked",
                x,
                height,
                list(hit[0]) if hit[0] else None,
            )
            route_clear.append({"x": x, "height": height, "clear": True})
    points = [bank.matrix_world @ v.co for v in bank.data.vertices]
    low = [min(p[i] for p in points) for i in range(3)]
    high = [max(p[i] for p in points) for i in range(3)]
    globe = bpy.data.objects["SITE_NEXT_Globe_India_green"]
    globepoints = [globe.matrix_world @ Vector(p) for p in globe.bound_box]
    globe_separation = min(p.x for p in globepoints) - high[0]
    assert globe_separation > 2, "Bike bank occupies the globe approach"
    return {
        "version": 263,
        "status": "passed",
        "solidStands": len(parts),
        "solids": solids,
        "groundContacts": all_foot_contacts,
        "retainedNativeFaceRecords": sum(exact_face_edges(retained).values()),
        "retainedFaceBoundariesUVsMaterialIndicesExact": True,
        "nativeCollisionChecks": collision_objects,
        "collisions": collisions,
        "bankBounds": {
            "low": low,
            "high": high,
            "widthM": high[0] - low[0],
            "lengthM": high[1] - low[1],
        },
        "globeSurfaceXSeparationM": globe_separation,
        "clearPedestrianBand": {
            "widthM": 1.8,
            "lengthM": 5.2,
            "groundSupportSamples": route_support,
            "clearanceRays": route_clear,
        },
        "protected262PlantersVerified": True,
        "limits": "Mapped10-bicycle capacity is represented by five double-sided stands as an explicit modeling inference. Individual layout and dimensions are estimates; same-street photos are not asserted to depict this exact bank.",
    }


def verify():
    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert audit["baselineSha256"] == SHA and sha(component) == audit["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    old_objects = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    old_materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    metadata = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    rooms = {
        r["collection"]: sorted(
            o.name for o in bpy.data.collections[r["collection"]].all_objects
        )
        for r in metadata["spaces"]
    }
    assert len(old_objects) == 8744 and len(old_materials) == 2355 and len(rooms) == 35
    with bpy.data.libraries.load(str(component), link=False) as (_, target):
        target.objects = list(audit["addedObjects"])
    for obj in target.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[audit["objectOwners"][obj.name]].objects.link(obj)
    update_scene()
    result = geometry_proof(audit)
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp for n, fp in old_objects.items()
    )
    assert all(
        material_fingerprint(bpy.data.materials[n]) == fp
        for n, fp in old_materials.items()
    )
    assert all(
        sorted(o.name for o in bpy.data.collections[n].all_objects) == names
        for n, names in rooms.items()
    )
    assert sha(BASE) == SHA
    result.update(
        baselineSha256=SHA,
        componentSha256=sha(component),
        originalObjectsPreserved=8744,
        originalMaterialsPreserved=2355,
        independentRoomsPreserved=35,
        nativeSaved=False,
    )
    write(OUT / "independent-geometry-verification.json", result)
    print(
        "SHEFFIELD263_GEOMETRY_PASSED",
        result["solidStands"],
        len(result["groundContacts"]),
        flush=True,
    )


if __name__ == "__main__":
    verify()
