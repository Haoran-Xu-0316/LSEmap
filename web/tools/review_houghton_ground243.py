"""Capture the accepted Houghton ground and furniture for local grade planning.

Read-only native inspection. Bounded world coordinates avoid copying unrelated
campus mesh data; no topographic registration is accepted by this inventory.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589"
OUT = ROOT / "result/blender/houghton-integration243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from plan_houghton_grade243 import grade_height


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    rows = []
    collections = [
        c
        for c in bpy.data.collections
        if c.name in ["00_SITE", "02_LANDSCAPE"] or c.name.endswith("_LANDSCAPE")
    ]
    names = sorted({o.name for c in collections for o in c.all_objects})
    for name in names:
        obj = bpy.data.objects[name]
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        bounds = {
            "min": [min(v[i] for v in corners) for i in range(3)],
            "max": [max(v[i] for v in corners) for i in range(3)],
        }
        if (
            bounds["max"][0] < -20
            or bounds["min"][0] > 18
            or bounds["max"][1] < -136
            or bounds["min"][1] > -75
            or bounds["min"][2] > 8
        ):
            continue
        rows.append(
            {
                "name": name,
                "fingerprint": object_fingerprint(obj),
                "bounds": bounds,
                "owners": sorted(c.name for c in obj.users_collection),
                "properties": repr(sorted(obj.items())),
                "vertices": [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                "faces": [list(f.vertices) for f in obj.data.polygons],
                "materials": [m.name if m else None for m in obj.data.materials],
                "materialIndices": [f.material_index for f in obj.data.polygons],
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    data = {
        "baselineSha256": BASE_SHA,
        "collections": [c.name for c in collections],
        "roi": [-20, -136, 18, -75],
        "objects": rows,
        "status": "read-only geometry inventory; no grade accepted",
    }
    (OUT / "ground-source-geometry.json").write_text(
        json.dumps(data, separators=(",", ":")) + "\n"
    )
    print(
        "HOUGHTON243_CAPTURE",
        len(rows),
        "objects",
        sum(len(o["faces"]) for o in rows),
        "faces",
        flush=True,
    )
    for row in rows:
        print(
            row["name"],
            len(row["vertices"]),
            row["bounds"],
            row["materials"][:2],
            flush=True,
        )
    # Inspect adjacent entry/furniture contacts separately from ground geometry.
    # Below-grade wall vertices are normal; this list is a review inventory,
    # not an automatic claim that every intersection is a collision.
    contacts = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        if min(v.z for v in corners) > 2 or max(v.z for v in corners) < 0:
            continue
        if max(v.x for v in corners) < -18 or min(v.x for v in corners) > 15:
            continue
        if max(v.y for v in corners) < -126 or min(v.y for v in corners) > -75:
            continue
        samples = []
        for vertex in obj.data.vertices:
            point = obj.matrix_world @ vertex.co
            if point.z > 2:
                continue
            height = grade_height(point.x, point.y)
            if height > 0.001:
                samples.append([*point, height, point.z - height])
        if samples:
            contacts.append(
                {
                    "name": obj.name,
                    "owners": sorted(c.name for c in obj.users_collection),
                    "affectedLowVertices": len(samples),
                    "minimumClearanceM": min(p[4] for p in samples),
                    "maximumGradeM": max(p[3] for p in samples),
                    "bounds": {
                        "min": [min(v[i] for v in corners) for i in range(3)],
                        "max": [max(v[i] for v in corners) for i in range(3)],
                    },
                    "lowSamples": sorted(samples, key=lambda p: p[4])[:8],
                }
            )
    (OUT / "adjacent-contact-review.json").write_text(
        json.dumps(contacts, indent=2) + "\n"
    )
    print("HOUGHTON243_ADJACENT_CONTACT_SUBJECTS", len(contacts), flush=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA


if __name__ == "__main__":
    main()
