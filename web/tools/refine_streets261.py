"""Inspect actual visible gate meshes before selecting one local correction.

Fixed configuration; the parent process runs this inside Blender. Inspection is
read only and writes solely to the private streets261 evidence directory.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
BASE_SHA = "c208a1086482bcc1bf20ec25ccdd9c684a0ea88a4891e5a007439c1076c1eec2"
OUT = ROOT / "result/blender/streets261"
sys.path.insert(0, str(ROOT / "web/tools"))
from refine_park_boundary211 import mapped_boundary


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect():
    assert sha(BASE) == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    from integrate_exterior_round194 import update_scene

    update_scene()
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    ring, gates, source = mapped_boundary()
    collection_hidden = set()

    def visit(collection, hidden=False):
        hidden = hidden or collection.hide_render
        if hidden:
            collection_hidden.update(o.name for o in collection.objects)
        for child in collection.children:
            visit(child, hidden)

    visit(scene.collection)
    trees = []
    evaluated_meshes = []
    deps = bpy.context.evaluated_depsgraph_get()
    inventory = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name in collection_hidden:
            continue
        evaluated = obj.evaluated_get(deps)
        corners = [evaluated.matrix_world @ Vector(p) for p in evaluated.bound_box]
        low = [min(p[i] for p in corners) for i in range(3)]
        high = [max(p[i] for p in corners) for i in range(3)]
        if low[2] > 2.2 or high[2] < -0.5:
            continue
        if any(
            token in obj.name.lower()
            for token in ["road", "footway", "pav", "kerb", "path", "ground", "street"]
        ):
            inventory.append(
                {
                    "name": obj.name,
                    "low": low,
                    "high": high,
                    "vertices": len(obj.data.vertices),
                    "materials": [m.name if m else None for m in obj.data.materials],
                }
            )
        if not any(
            low[0] - 6 < g["centre"][0] < high[0] + 6
            and low[1] - 6 < g["centre"][1] < high[1] + 6
            for g in gates
        ):
            continue
        mesh = evaluated.to_mesh()
        evaluated_meshes.append(evaluated)
        mesh.calc_loop_triangles()
        points = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        if triangles:
            trees.append(
                (
                    obj.name,
                    BVHTree.FromPolygons(points, triangles, all_triangles=True),
                    mesh,
                    low,
                    high,
                )
            )

    def hits(origin, direction, distance):
        rows = []
        for name, tree, mesh, low, high in trees:
            location, normal, index, length = tree.ray_cast(
                Vector(origin), Vector(direction), distance
            )
            if location is not None:
                triangle = mesh.loop_triangles[index]
                material = (
                    mesh.materials[triangle.material_index]
                    if len(mesh.materials)
                    else None
                )
                rows.append(
                    {
                        "object": name,
                        "point": list(location),
                        "normal": list(normal),
                        "distance": length,
                        "triangle": index,
                        "material": material.name if material else None,
                    }
                )
        return sorted(rows, key=lambda r: r["distance"])

    rows = []
    for gate in gates:
        point = Vector(gate["centre"])
        index = gate["index"]
        tangent = (ring[(index + 1) % len(ring)] - ring[index - 1]).normalized()
        normal = Vector((-tangent.y, tangent.x, 0))
        support = []
        for across in [-0.45, 0, 0.45]:
            for along in [-4, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 4]:
                p = point + normal * along + tangent * across * gate["clearWidthMetres"]
                support.append(
                    {
                        "across": across,
                        "along": along,
                        "xy": list(p.xy),
                        "hits": hits((p.x, p.y, 2.05), (0, 0, -1), 2.5),
                    }
                )
        crossings = []
        for across in [-0.45, -0.25, 0, 0.25, 0.45]:
            for height in [0.10, 0.25, 0.8, 1.6]:
                start = (
                    point
                    - normal * 4
                    + tangent * across * gate["clearWidthMetres"]
                    + Vector((0, 0, height))
                )
                crossings.append(
                    {"across": across, "height": height, "hits": hits(start, normal, 8)}
                )
        rows.append(
            {
                "node": gate["node"],
                "centre": gate["centre"],
                "width": gate["clearWidthMetres"],
                "tangent": list(tangent),
                "normal": list(normal),
                "supports": support,
                "crossings": crossings,
            }
        )
    record = {
        "version": 261,
        "mode": "read-only-native-mesh-inspection",
        "baselineSha256": BASE_SHA,
        "source": source,
        "gateChecks": rows,
        "lowSurfaceInventory": inventory,
        "actualMeshTrees": len(trees),
        "meshTreeInventory": [
            {
                "name": t[0],
                "low": t[3],
                "high": t[4],
                "triangles": len(t[2].loop_triangles),
            }
            for t in trees
        ],
        "nativeSaved": False,
        "limits": "Archived mapped gate positions only; actual native triangle probes establish model defects, not surveyed present day gate shape.",
    }
    (OUT / "native-inspection.json").write_text(json.dumps(record, indent=2) + "\n")
    for evaluated in evaluated_meshes:
        evaluated.to_mesh_clear()
    assert sha(BASE) == BASE_SHA
    print("STREETS261_INSPECTED", len(trees), flush=True)


if __name__ == "__main__":
    inspect()
