"""Capture the accepted Aldwych exteriors for independent drawing comparison.

The public release and native remain read-only. This is source registration,
not permission to transfer ownership or move either building from a site plan.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589"
OUT = ROOT / "result/blender/stage243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    OUT.mkdir(exist_ok=True)
    spec = importlib.util.spec_from_file_location(
        "protected_source", ROOT / "web/tests/verify_campus241.py"
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    verifier.BASE_SHA = BASE_SHA
    state = verifier.capture_source()
    (OUT / "protected-source-state.json").write_text(json.dumps(state, indent=2) + "\n")
    rows = []
    for code in ["61A", "CON"]:
        for obj in bpy.data.collections[code + "_EXTERIOR"].all_objects:
            if obj.hide_render:
                continue
            corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
            row = {
                "code": code,
                "name": obj.name,
                "type": obj.type,
                "fingerprint": object_fingerprint(obj),
                "bounds": {
                    "min": [min(c[i] for c in corners) for i in range(3)],
                    "max": [max(c[i] for c in corners) for i in range(3)],
                },
            }
            if obj.type == "MESH":
                row.update(
                    vertices=[list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                    faces=[list(f.vertices) for f in obj.data.polygons],
                    materials=[m.name if m else None for m in obj.data.materials],
                    materialIndices=[f.material_index for f in obj.data.polygons],
                )
            rows.append(row)
    (OUT / "current-exterior-geometry.json").write_text(
        json.dumps({"baselineSha256": BASE_SHA, "objects": rows}, separators=(",", ":"))
        + "\n"
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print(
        "ALDWYCH243_READONLY_CAPTURE",
        len(state["objects"]),
        len(rows),
        sum(len(r.get("faces", [])) for r in rows),
        flush=True,
    )


if __name__ == "__main__":
    main()
