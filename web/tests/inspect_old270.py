"""Read-only native269 inventory of OLD's mixed Clare casement batch.

Run main() in Blender. No native save, geometry edit or material mutation.
The output preserves all source face/UV records and identifies real connected
members before a bounded lower-casement grid candidate is considered.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/old270/native-inspection.json"
SOURCE = "OLD_D5_clare87_casements"
sys.path.insert(0, str(ROOT / "web/tools"))


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def connected_vertices(mesh):
    links = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        links[a].add(b)
        links[b].add(a)
    remaining = set(range(len(links)))
    result = []
    while remaining:
        first = min(remaining)
        remaining.remove(first)
        seen = {first}
        todo = [first]
        while todo:
            for other in links[todo.pop()]:
                if other in remaining:
                    remaining.remove(other)
                    seen.add(other)
                    todo.append(other)
        result.append(sorted(seen))
    return result


def main():
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_portsmouth_exterior207 import material_fingerprint

    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    source = bpy.data.objects[SOURCE]
    assert source.type == "MESH" and not source.hide_render
    assert sorted(c.name for c in source.users_collection) == ["OLD_EXTERIOR"]
    before = object_fingerprint(source)
    old = json.loads(
        (ROOT / "result/blender/stage87/old-clare-casement-audit.json").read_text()
    )
    origin, right, outward = [
        Vector(old["frame"][name]) for name in ("origin", "right", "outward")
    ]

    def local(point):
        d = point - origin
        return [d.dot(right), d.dot(outward), point.z]

    groups = connected_vertices(source.data)
    records = []
    for index, vertices in enumerate(groups):
        points = [
            local(source.matrix_world @ source.data.vertices[i].co) for i in vertices
        ]
        lo = [min(p[i] for p in points) for i in range(3)]
        hi = [max(p[i] for p in points) for i in range(3)]
        selected = set(vertices)
        records.append(
            {
                "component": index,
                "vertices": vertices,
                "faces": [
                    f.index for f in source.data.polygons if set(f.vertices) <= selected
                ],
                "localMinimum": lo,
                "localMaximum": hi,
                "localCentre": [(a + b) / 2 for a, b in zip(lo, hi, strict=True)],
                "localSize": [b - a for a, b in zip(lo, hi, strict=True)],
            }
        )
    lower = [w for w in old["windows"] if w["family"] == "lower"]
    assert len(lower) == 4
    roi = [
        min(w["x"] - w["w"] / 2 for w in lower) - 0.15,
        max(w["x"] + w["w"] / 2 for w in lower) + 0.15,
        -0.45,
        0.35,
        0.60,
        5.30,
    ]
    neighbours = []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(
        bpy.data.collections["OLD_EXTERIOR"].all_objects, key=lambda o: o.name
    ):
        if obj.name == SOURCE or obj.type != "MESH" or obj.hide_render:
            continue
        corners = [local(obj.matrix_world @ Vector(p)) for p in obj.bound_box]
        lo = [min(p[i] for p in corners) for i in range(3)]
        hi = [max(p[i] for p in corners) for i in range(3)]
        if (
            hi[0] < roi[0]
            or lo[0] > roi[1]
            or hi[1] < roi[2]
            or lo[1] > roi[3]
            or hi[2] < roi[4]
            or lo[2] > roi[5]
        ):
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles = []
        for face in mesh.loop_triangles:
            world = [
                evaluated.matrix_world @ mesh.vertices[i].co for i in face.vertices
            ]
            points = [local(p) for p in world]
            lo = [min(p[i] for p in points) for i in range(3)]
            hi = [max(p[i] for p in points) for i in range(3)]
            if (
                hi[0] < roi[0]
                or lo[0] > roi[1]
                or hi[1] < roi[2]
                or lo[1] > roi[3]
                or hi[2] < roi[4]
                or lo[2] > roi[5]
            ):
                continue
            material = mesh.materials[face.material_index] if mesh.materials else None
            triangles.append(
                {
                    "world": [list(p) for p in world],
                    "local": points,
                    "material": material.name if material else None,
                }
            )
        evaluated.to_mesh_clear()
        if triangles:
            neighbours.append(
                {
                    "name": obj.name,
                    "fingerprint": object_fingerprint(obj),
                    "triangles": triangles,
                }
            )
    result = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "readOnly": True,
        "nativeSaved": False,
        "originalObjects": len(bpy.data.objects),
        "originalMaterials": len(bpy.data.materials),
        "sourceObject": SOURCE,
        "sourceFingerprint": before,
        "sourceOwners": sorted(c.name for c in source.users_collection),
        "matrixWorld": [list(row) for row in source.matrix_world],
        "verticesLocal": [list(v.co) for v in source.data.vertices],
        "verticesWorld": [
            list(source.matrix_world @ v.co) for v in source.data.vertices
        ],
        "faces": [
            {
                "index": f.index,
                "vertices": list(f.vertices),
                "materialIndex": f.material_index,
                "smooth": f.use_smooth,
                "uvs": {
                    uv.name: [list(uv.data[i].uv) for i in f.loop_indices]
                    for uv in source.data.uv_layers
                },
            }
            for f in source.data.polygons
        ],
        "materials": [m.name for m in source.data.materials],
        "materialGraphs": {
            m.name: material_fingerprint(m) for m in source.data.materials
        },
        "modifiers": [{"name": m.name, "type": m.type} for m in source.modifiers],
        "components": records,
        "frame": old["frame"],
        "legacyWindows": old["windows"],
        "legacyTransoms": [m for m in old["members"] if m["kind"] == "horizontal"],
        "nearbyActualTriangles": neighbours,
    }
    assert object_fingerprint(source) == before and sha(BASE) == SHA
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("OLD270_NATIVE_READ_ONLY", len(groups), len(neighbours), flush=True)


if __name__ == "__main__":
    main()
