"""Capture current SAW circulation geometry without changing the accepted native.

Run in Blender's editor. The fixed spatial window includes every visible SAW
mesh that could obstruct the upper main stair. Save source fingerprints beside
actual triangles, rather than relying on the historical rejected candidate.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v241.blend"
BASE_SHA = "3b49385387b8e5c53223a1151762b80b9b3e1e4c2bbfbd474dfa820af4e424b4"
OUT = ROOT / "result/blender/saw-circulation242"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    public = bpy.data.collections["SAW_PUBLIC_INTERIOR_study"]
    public_names = {obj.name for obj in public.all_objects}
    rows = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not (obj.name.startswith(("SAW", "SAWFLOOR")) or obj.name in public_names):
            continue
        vertices = [list(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
        if not vertices:
            continue
        bounds = [
            [min(p[i] for p in vertices), max(p[i] for p in vertices)] for i in range(3)
        ]
        if (
            bounds[0][1] < -76
            or bounds[0][0] > -59
            or bounds[1][1] < -2
            or bounds[1][0] > 18
            or bounds[2][0] > 20.2
            or bounds[2][1] < 0
        ):
            continue
        obj.data.calc_loop_triangles()
        rows.append(
            {
                "name": obj.name,
                "fingerprint": object_fingerprint(obj),
                "vertices": vertices,
                "triangles": [list(t.vertices) for t in obj.data.loop_triangles],
                "faces": [list(p.vertices) for p in obj.data.polygons],
                "bounds": bounds,
                "collections": sorted(c.name for c in obj.users_collection),
            }
        )
    record = {
        "baselineSha256": BASE_SHA,
        "nativeReadOnly": True,
        "objects": rows,
        "scope": "Every visible SAW/public mesh overlapping x[-76,-59],y[-2,18],z[0,20.2]",
    }
    (OUT / "current-surfaces.json").write_text(
        json.dumps(record, separators=(",", ":")) + "\n"
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print(
        "SAW242_CAPTURED",
        len(rows),
        sum(len(row["triangles"]) for row in rows),
        flush=True,
    )


if __name__ == "__main__":
    main()
