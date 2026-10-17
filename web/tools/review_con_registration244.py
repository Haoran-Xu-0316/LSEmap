"""Capture the current CON boundary and full native protection state read-only."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v243.blend"
BASE_SHA = "cd41b4372b1e690400f351ed8bce228b1b1fa91f9bc161ddbbd91fb3f4349ba8"
OUT = ROOT / "result/blender/con-registration244"
PROOF = ROOT / "result/blender/stage244"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    spec = importlib.util.spec_from_file_location(
        "capture_native_state", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = BASE_SHA
    state = helper.capture_source()
    PROOF.mkdir(parents=True, exist_ok=True)
    (PROOF / "protected-source-state.json").write_text(
        json.dumps(state, indent=2) + "\n"
    )
    rows = []
    for obj in bpy.data.collections["CON_EXTERIOR"].all_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        rows.append(
            {
                "name": obj.name,
                "fingerprint": object_fingerprint(obj),
                "bounds": {
                    "min": [min(v[i] for v in corners) for i in range(3)],
                    "max": [max(v[i] for v in corners) for i in range(3)],
                },
                "vertices": [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                "faces": [list(f.vertices) for f in obj.data.polygons],
                "materials": [m.name if m else None for m in obj.data.materials],
                "materialIndices": [f.material_index for f in obj.data.polygons],
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "native-exterior.json").write_text(
        json.dumps({"baselineSha256": BASE_SHA, "objects": rows}, separators=(",", ":"))
        + "\n"
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print("CON244_BASELINE_CAPTURED", len(rows), len(state["objects"]), flush=True)


if __name__ == "__main__":
    main()
