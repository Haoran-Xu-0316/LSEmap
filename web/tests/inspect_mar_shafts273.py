"""Inspect actual269MAR lift-core meshes without changing or saving the campus.

Run main() inside Blender. Full native faces/UVs are saved only for the five
bounded correction targets; neighbours are evaluated3Dtriangles in the coreROI.
No higher-floor opening is inferred from the2022Second/Third-floor drawings.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/mar273/native-inspection.json"
TARGETS = [
    "MAR269_second_structural_slab_with_source_shafts",
    "MAR269_second_floor_finish_with_source_shafts",
    "MAR269_second_soffit_with_source_shafts",
    "MAR258_third_south_deck_solid",
    "MAR251_third_south_lift_core_walls",
]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import (
    object_fingerprint,
    update_scene,
)
from refine_portsmouth_exterior207 import (
    material_fingerprint,
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def outside(points, roi):
    return any(
        max(p[i] for p in points) < roi[i] or min(p[i] for p in points) > roi[i + 3]
        for i in range(3)
    )


def target_snapshot(obj):
    assert obj.type == "MESH" and not obj.hide_render and not obj.modifiers
    return {
        "name": obj.name,
        "fingerprint": object_fingerprint(obj),
        "owners": sorted(c.name for c in obj.users_collection),
        "matrixWorld": [list(r) for r in obj.matrix_world],
        "verticesLocal": [list(v.co) for v in obj.data.vertices],
        "verticesWorld": [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
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


def main():
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert len(bpy.data.objects) == 8752 and len(bpy.data.materials) == 2355
    evidence = json.loads((ROOT / "result/blender/mar269-evidence.json").read_text())
    holes = [r["cutWorldXY"] for r in evidence["confirmedGap"]["newSecondSourceShafts"]]
    xy = [p for ring in holes for p in ring]
    roi = [
        min(p[0] for p in xy) - 1.0,
        min(p[1] for p in xy) - 1.0,
        0.0,
        max(p[0] for p in xy) + 1.0,
        max(p[1] for p in xy) + 1.0,
        30.0,
    ]
    targets = [target_snapshot(bpy.data.objects[n]) for n in TARGETS]
    objects = set(bpy.data.collections["MAR_PUBLIC_INTERIOR_study"].all_objects)
    objects.update(bpy.data.collections["MAR_EXTERIOR"].all_objects)
    deps = bpy.context.evaluated_depsgraph_get()
    neighbours = []
    for obj in sorted(objects, key=lambda o: o.name):
        if obj.type != "MESH" or obj.hide_render:
            continue
        if outside([obj.matrix_world @ Vector(p) for p in obj.bound_box], roi):
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles = []
        for tri in mesh.loop_triangles:
            points = [
                evaluated.matrix_world @ mesh.vertices[i].co for i in tri.vertices
            ]
            if not outside(points, roi):
                triangles.append(
                    {
                        "points": [list(p) for p in points],
                        "materialIndex": tri.material_index,
                    }
                )
        evaluated.to_mesh_clear()
        if triangles:
            neighbours.append(
                {
                    "name": obj.name,
                    "fingerprint": object_fingerprint(obj),
                    "owners": sorted(c.name for c in obj.users_collection),
                    "materials": [m.name if m else None for m in obj.data.materials],
                    "triangles": triangles,
                }
            )
    names = {r["name"] for r in neighbours}
    assert set(TARGETS) <= names
    vertical = evidence["verticalCoordination"]
    assert (
        object_fingerprint(bpy.data.objects[vertical["existingThirdDeckObject"]])
        == vertical["existingThirdDeckFingerprint"]
    )
    assert (
        object_fingerprint(bpy.data.objects[vertical["existingThirdCoreObject"]])
        == vertical["existingThirdCoreFingerprint"]
    )
    result = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "readOnly": True,
        "nativeSaved": False,
        "originalObjects": len(bpy.data.objects),
        "originalMaterials": len(bpy.data.materials),
        "targets": targets,
        "neighbours": neighbours,
        "roiXYZ": roi,
        "secondSourceShafts": evidence["confirmedGap"]["newSecondSourceShafts"],
        "retainedRelativeRegistrationUncertainty": vertical[
            "relativeControlUncertainty"
        ],
        "targetMaterialGraphs": {
            n: material_fingerprint(bpy.data.materials[n])
            for n in {m for r in targets for m in r["materials"]}
        },
        "limits": "Actual269meshes;allZdatums are inherited estimates. Neighbours aboveThird are diagnostic only: no identified higher-levelXYplan is available.",
    }
    assert all(
        object_fingerprint(bpy.data.objects[r["name"]]) == r["fingerprint"]
        for r in targets
    )
    assert sha(BASE) == SHA
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print("MAR273_READ_ONLY_INSPECTED", len(neighbours), flush=True)


if __name__ == "__main__":
    main()
