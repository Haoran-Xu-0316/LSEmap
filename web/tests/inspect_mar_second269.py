"""Read-only native263 inspection for source-proven MAR second-floor lift shafts.

Run main() in Blender. Writes one private JSON inventory, never a native file.
Second-floor points come from its own2022architect drawing, not the third plan.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/mar269/native-second-inspection.json"
TARGETS = [
    "MAR223_second_structural_slab",
    "MAR223_second_floor_finish",
    "MAR223_second_soffit",
]
SECOND_SHAFTS = [
    [
        [157.7335, 277.4456],
        [164.6645, 277.4456],
        [164.6726, 286.8640],
        [157.7246, 286.8580],
    ],
    [
        [157.7336, 287.6960],
        [164.6606, 287.6940],
        [164.6746, 297.0960],
        [157.7296, 297.0900],
    ],
    [
        [176.2232, 277.4511],
        [183.1532, 277.4501],
        [183.1602, 286.8701],
        [176.2302, 286.8711],
    ],
]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_world(points):
    geo = json.loads(
        (ROOT / "result/blender/mar-registration217/audit.json").read_text()
    )["geographicRegistration"]
    fit = geo["secondPdfToNativeLocalCandidate"]
    rotation = fit["rotation"]
    angle = math.radians(geo["nativeBasisDegrees"])
    result = []
    for x, y in points:
        u = (
            fit["scale"] * (y * rotation[0][0] + x * rotation[1][0])
            + fit["translation"][0]
        )
        v = (
            fit["scale"] * (y * rotation[0][1] + x * rotation[1][1])
            + fit["translation"][1]
        )
        result.append(
            (
                geo["nativeOrigin"][0] + u * math.cos(angle) - v * math.sin(angle),
                geo["nativeOrigin"][1] + u * math.sin(angle) + v * math.cos(angle),
            )
        )
    return result


def main():
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert len(bpy.data.objects) == 8748 and len(bpy.data.materials) == 2355
    before = {n: object_fingerprint(bpy.data.objects[n]) for n in TARGETS}
    shafts = [source_world(p) for p in SECOND_SHAFTS]
    all_xy = [p for ring in shafts for p in ring]
    roi = [
        min(p[0] for p in all_xy) - 1,
        min(p[1] for p in all_xy) - 1,
        max(p[0] for p in all_xy) + 1,
        max(p[1] for p in all_xy) + 1,
        12.35,
        17.55,
    ]
    targets = []
    for name in TARGETS:
        obj = bpy.data.objects[name]
        assert obj.type == "MESH" and not obj.hide_render
        targets.append(
            {
                "name": name,
                "fingerprint": before[name],
                "owners": sorted(c.name for c in obj.users_collection),
                "matrixWorld": [list(r) for r in obj.matrix_world],
                "verticesLocal": [list(v.co) for v in obj.data.vertices],
                "verticesWorld": [
                    list(obj.matrix_world @ v.co) for v in obj.data.vertices
                ],
                "materials": [m.name if m else None for m in obj.data.materials],
                "properties": dict(obj.items()),
                "faces": [
                    {
                        "index": f.index,
                        "vertices": list(f.vertices),
                        "materialIndex": f.material_index,
                        "smooth": f.use_smooth,
                        "uvs": {
                            uv.name: [list(uv.data[i].uv) for i in f.loop_indices]
                            for uv in obj.data.uv_layers
                        },
                    }
                    for f in obj.data.polygons
                ],
            }
        )
    objects = set(bpy.data.collections["MAR_PUBLIC_INTERIOR_study"].all_objects)
    objects.update(bpy.data.collections["MAR_EXTERIOR"].all_objects)
    neighbours = []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(objects, key=lambda o: o.name):
        if obj.name in TARGETS or obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        if (
            max(p.x for p in corners) < roi[0]
            or min(p.x for p in corners) > roi[2]
            or max(p.y for p in corners) < roi[1]
            or min(p.y for p in corners) > roi[3]
            or max(p.z for p in corners) < roi[4]
            or min(p.z for p in corners) > roi[5]
        ):
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        rows = []
        for tri in mesh.loop_triangles:
            pts = [evaluated.matrix_world @ mesh.vertices[i].co for i in tri.vertices]
            if (
                max(p.x for p in pts) < roi[0]
                or min(p.x for p in pts) > roi[2]
                or max(p.y for p in pts) < roi[1]
                or min(p.y for p in pts) > roi[3]
                or max(p.z for p in pts) < roi[4]
                or min(p.z for p in pts) > roi[5]
            ):
                continue
            rows.append(
                {
                    "points": [list(p) for p in pts],
                    "material": mesh.materials[tri.material_index].name
                    if mesh.materials
                    else None,
                }
            )
        evaluated.to_mesh_clear()
        if rows:
            neighbours.append(
                {
                    "name": obj.name,
                    "fingerprint": object_fingerprint(obj),
                    "owners": sorted(c.name for c in obj.users_collection),
                    "triangles": rows,
                }
            )
    result = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "readOnly": True,
        "targets": targets,
        "secondSourceShaftWorldXY": shafts,
        "roi": roi,
        "neighbours": neighbours,
        "targetMaterialGraphs": {
            n: material_fingerprint(bpy.data.materials[n])
            for n in {m for r in targets for m in r["materials"]}
        },
        "originalObjects": len(bpy.data.objects),
        "originalMaterials": len(bpy.data.materials),
        "roomMembershipCount": len(
            json.loads((ROOT / "web/tools/building-metadata.json").read_text())[
                "spaces"
            ]
        ),
        "nativeSaved": False,
        "limits": "Actual263meshes only; floors7.24/12.8/17.5and slab thickness remain inherited display estimates.",
    }
    assert all(object_fingerprint(bpy.data.objects[n]) == v for n, v in before.items())
    assert sha(BASE) == SHA
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("MAR269_NATIVE_SECOND_INSPECTED", len(neighbours), flush=True)


if __name__ == "__main__":
    main()
