"""Independent evaluated-mesh support, collision and pedestrian-channel checks.

Fixed native v261 plus the standalone262component. Tests use saved triangles,
not authoring box parameters, and leave the production native file unchanged.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/sheffield262"
BASE = ROOT / "result/blender/LSE_campus_detailed_v261.blend"
SHA = "9890521a376afabfbb3d6c130d20ce40988315c49b8adea4c00749960a97482a"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_portsmouth_exterior207 import material_fingerprint


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, r):
    p.write_text(json.dumps(r, indent=2) + "\n")


def triangle_rows(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    rows = [
        tuple(evaluated.matrix_world @ mesh.vertices[i].co for i in t.vertices)
        for t in mesh.loop_triangles
    ]
    evaluated.to_mesh_clear()
    return rows


def tree(rows):
    return BVHTree.FromPolygons(
        [p for t in rows for p in t],
        [(i * 3, i * 3 + 1, i * 3 + 2) for i in range(len(rows))],
        all_triangles=True,
    )


def components(obj):
    links = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        a, b = edge.vertices
        links[a].add(b)
        links[b].add(a)
    pending = set(range(len(links)))
    result = []
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
        result.append(part)
    return result


def geometry_proof(audit):
    """Check the current full campus scene without opening/appending any file."""
    update_scene()
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    loaded = [bpy.data.objects[name] for name in audit["addedObjects"]]
    assert all(
        object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
        for obj in loaded
    )
    assert all(
        sorted(c.name for c in obj.users_collection) == [audit["destinationCollection"]]
        for obj in loaded
    )
    old_objects = {
        obj.name for obj in scene.objects if obj.name not in set(audit["addedObjects"])
    }
    # Every real island must be a closed, positive-volume solid. The test discovers
    # connectivity and evaluates signed tetrahedron volume from serialized faces.
    closed = []
    bottom_contacts = []
    islands = []
    paving_rows = []
    for name in audit["supportSurfaceObjects"]:
        obj = bpy.data.objects[name]
        assert not obj.hide_render
        paving_rows.extend(triangle_rows(obj))
    paving_tree = tree(paving_rows)
    for obj in loaded:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(edge.is_manifold for edge in bm.edges)
        bm.free()
        for part in components(obj):
            polygons = [p for p in obj.data.polygons if set(p.vertices) <= part]
            volume = 0.0
            triangles = []
            downward_vertices = set()
            for polygon in polygons:
                points = [
                    obj.matrix_world @ obj.data.vertices[i].co for i in polygon.vertices
                ]
                for j in range(1, len(points) - 1):
                    volume += points[0].dot(points[j].cross(points[j + 1])) / 6
                    triangles.append((points[0], points[j], points[j + 1]))
                if polygon.normal.z < -0.5:
                    downward_vertices.update(
                        i
                        for i in polygon.vertices
                        if (obj.matrix_world @ obj.data.vertices[i].co).z < 0.12
                    )
            assert volume > 1e-7, (obj.name, "nonpositive island", volume)
            vertices = [obj.matrix_world @ obj.data.vertices[i].co for i in part]
            island = {"object": obj.name, "vertices": len(part), "volumeM3": volume}
            closed.append(island)
            contacts = []
            for index in downward_vertices:
                p = obj.matrix_world @ obj.data.vertices[index].co
                hit = paving_tree.ray_cast(
                    Vector((p.x, p.y, 0.2)), Vector((0, 0, -1)), 0.3
                )
                if hit[0] is None:
                    continue
                contacts.append(
                    {
                        "object": obj.name,
                        "point": list(p),
                        "supportZ": hit[0].z,
                        "gapM": p.z - hit[0].z,
                    }
                )
            # A bearing island must actually contact native pavement at all of its bottom
            # vertices. Other pieces must have a real contact path to these bearing feet.
            grounded = (
                bool(contacts)
                and len(contacts) == len(downward_vertices)
                and all(-0.0011 <= row["gapM"] <= 0.0011 for row in contacts)
            )
            if grounded:
                bottom_contacts.extend(contacts)
            islands.append(
                {
                    "index": len(islands),
                    "vertices": vertices,
                    "tree": tree(triangles),
                    "grounded": grounded,
                }
            )
    assert len(bottom_contacts) >= 48, "Missing physical bearing-foot ground contacts"
    # Discover an actual contact graph between saved solid islands. Exact face
    # contacts or surface crossings connect walls, bearing pads, seat supports,
    # open-root baseplates and soil; no authoring labels stand in for load paths.
    graph = {row["index"]: set() for row in islands}
    contact_pairs = []
    for a, first in enumerate(islands):
        for second in islands[a + 1 :]:
            touches = bool(first["tree"].overlap(second["tree"]))
            if not touches:
                for vertex in first["vertices"]:
                    nearest = second["tree"].find_nearest(vertex)
                    if nearest[0] is not None and nearest[3] < 0.0001:
                        touches = True
                        break
            if not touches:
                for vertex in second["vertices"]:
                    nearest = first["tree"].find_nearest(vertex)
                    if nearest[0] is not None and nearest[3] < 0.0001:
                        touches = True
                        break
            if touches:
                i, j = first["index"], second["index"]
                graph[i].add(j)
                graph[j].add(i)
                contact_pairs.append([i, j])
    supported = {row["index"] for row in islands if row["grounded"]}
    todo = list(supported)
    while todo:
        for other in graph[todo.pop()]:
            if other not in supported:
                supported.add(other)
                todo.append(other)
    assert len(supported) == len(islands), (
        "Unsupported structural or soil islands",
        sorted(set(graph) - supported),
    )
    load_paths = {
        "solidIslands": len(islands),
        "groundedBearingIslands": sum(row["grounded"] for row in islands),
        "supportedIslands": len(supported),
        "contactPairs": contact_pairs,
    }
    # Triangle intersections with all original visible nearby geometry above floor
    # contact tolerance. This includes both original benches and both full trunks;
    # actual paving contacts and the retained underground grate are below.075m.
    new_rows = [
        t for obj in loaded for t in triangle_rows(obj) if max(p.z for p in t) > 0.075
    ]
    new_tree = tree(new_rows)
    collisions = []
    nearby = []
    for obj in scene.objects:
        if obj.name not in old_objects or obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if (
            max(p.x for p in corners) < -55
            or min(p.x for p in corners) > -42
            or max(p.y for p in corners) < -8
            or min(p.y for p in corners) > 14
            or min(p.z for p in corners) > 0.85
        ):
            continue
        rows = [
            t
            for t in triangle_rows(obj)
            if min(p.z for p in t) < 0.85 and max(p.z for p in t) > 0.075
        ]
        if not rows:
            continue
        nearby.append(obj.name)
        hits = new_tree.overlap(tree(rows))
        if hits:
            collisions.append(
                {
                    "object": obj.name,
                    "trianglePairs": len(hits),
                    "witness": [
                        {
                            "newTriangle": [list(p) for p in new_rows[a]],
                            "nativeTriangle": [list(p) for p in rows[b]],
                        }
                        for a, b in hits[:2]
                    ],
                }
            )
    assert not collisions, collisions
    # Actual triangle-derived rectangular root apertures leave two real trunks
    # inside the root well; rays at ground through soil must not be obstructed at
    # the trunk perimeter. Root clearance is not inferred from object names alone.
    root_checks = []
    red = next(o for o in loaded if "painted_" in o.name)
    soil = next(o for o in loaded if "soil_" in o.name)
    red_tree = tree(triangle_rows(red))
    soil_tree = tree(triangle_rows(soil))
    for unit in audit["units"]:
        c = Vector(unit["centre"])
        around = []
        for angle in [i * math.tau / 16 for i in range(16)]:
            xy = c + Vector((math.cos(angle) * 0.29, math.sin(angle) * 0.29, 0))
            for label, index in [("painted", red_tree), ("soil", soil_tree)]:
                hit = index.ray_cast(xy + Vector((0, 0, 0.9)), Vector((0, 0, -1)), 0.9)
                assert hit[0] is None, (unit["index"], label, "Root well blocked")
            around.append(list(xy.xy))
        root_checks.append(
            {
                "unit": unit["index"],
                "clearRootApertureProbeRadiusM": 0.29,
                "clearProbes": len(around),
            }
        )
    # Sample the1.8m pedestrian band on the side away from retained benches. All
    # samples must stand on original Sheffield paving and crossing rays must avoid
    # actual native and new triangles at ankle, seat, torso and head heights.
    all_rows = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if (
            max(p.x for p in corners) < -56
            or min(p.x for p in corners) > -39
            or max(p.y for p in corners) < -10
            or min(p.y for p in corners) > 16
            or min(p.z for p in corners) > 2
        ):
            continue
        all_rows.extend(
            t
            for t in triangle_rows(obj)
            if max(p.z for p in t) > 0.075 and min(p.z for p in t) < 2
        )
    street_tree = tree(all_rows)
    corridors = []
    for unit in audit["units"]:
        c = Vector(unit["clearCorridor"]["centre"])
        u = Vector(unit["along"])
        v = Vector(unit["across"])
        walk = []
        clear = []
        for along in [-3, -2.5, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 2.5, 3]:
            for across in [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9]:
                p = c + u * along + v * across
                hit = paving_tree.ray_cast(
                    p + Vector((0, 0, 0.20)), Vector((0, 0, -1)), 0.30
                )
                assert hit[0] is not None, (
                    unit["index"],
                    "Walking band lacks pavement",
                    list(p),
                )
                walk.append({"xy": list(p.xy), "pavingZ": hit[0].z})
        for across in [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9]:
            for height in [0.10, 0.35, 0.8, 1.65]:
                origin = c - u * 3 + v * across + Vector((0, 0, height))
                hit = street_tree.ray_cast(origin, u, 6)
                assert hit[0] is None, (
                    unit["index"],
                    "Walking band obstructed",
                    across,
                    height,
                    list(hit[0]) if hit[0] else None,
                )
                clear.append({"across": across, "height": height, "clear": True})
        corridors.append(
            {
                "unit": unit["index"],
                "widthM": 1.8,
                "lengthM": 6,
                "pavingSupportSamples": walk,
                "clearanceRays": clear,
            }
        )
    return {
        "version": 262,
        "status": "passed",
        "baselineSha256": SHA,
        "evaluatedNativeMeshCollisions": collisions,
        "collisionObjectsChecked": nearby,
        "closedSolidChecks": closed,
        "groundContacts": bottom_contacts,
        "rootApertureChecks": root_checks,
        "pedestrianBands": corridors,
        "structuralContactGraph": load_paths,
        "nativeSaved": False,
        "limits": "Two sampled1.8x6m clear bands and native model contacts; not a site accessibility or furniture survey.",
    }


def verify():
    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert audit["baselineSha256"] == SHA and sha(component) == audit["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    bpy.data.scenes["00_CAMPUS_COMPLETE"]
    old_objects = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    old_materials = {m.name: material_fingerprint(m) for m in bpy.data.materials}
    metadata = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    old_rooms = {
        row["collection"]: sorted(
            o.name for o in bpy.data.collections[row["collection"]].all_objects
        )
        for row in metadata["spaces"]
    }
    assert (
        len(old_objects) == 8735 and len(old_materials) == 2350 and len(old_rooms) == 35
    )
    with bpy.data.libraries.load(str(component), link=False) as (_, target):
        target.objects = list(audit["addedObjects"])
    loaded = target.objects
    for obj in loaded:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[audit["destinationCollection"]].objects.link(obj)
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp
        for n, fp in audit["addedFingerprints"].items()
    )
    result = geometry_proof(audit)
    assert all(
        object_fingerprint(bpy.data.objects[n]) == fp for n, fp in old_objects.items()
    )
    assert all(
        material_fingerprint(bpy.data.materials[n]) == fp
        for n, fp in old_materials.items()
    )
    assert all(
        sorted(o.name for o in bpy.data.collections[n].all_objects) == rows
        for n, rows in old_rooms.items()
    )
    assert sha(BASE) == SHA
    result.update(
        componentSha256=sha(component),
        originalObjectsPreserved=8735,
        originalMaterialsPreserved=2350,
        independentRoomsPreserved=35,
    )
    write(OUT / "independent-geometry-verification.json", result)
    print(
        "SHEFFIELD262_GEOMETRY_PASSED",
        len(result["closedSolidChecks"]),
        len(result["groundContacts"]),
        len(result["collisionObjectsChecked"]),
        flush=True,
    )


if __name__ == "__main__":
    verify()
