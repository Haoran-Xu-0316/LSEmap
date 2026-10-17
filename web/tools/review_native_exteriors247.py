"""Read accepted246 COL mesh controls and MAR material values without editing it."""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v246.blend"
SHA = "44f7745ab4c84681b9d9528b6fd5955761cf6eeb769ef6afdc7bbf05c8df0c4d"
OUT = ROOT / "result/blender/stage247"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    spec = importlib.util.spec_from_file_location(
        "capture_native", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    state = helper.capture_source()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "protected-source-state.json").write_text(json.dumps(state, indent=2) + "\n")
    rows = []
    for obj in bpy.data.collections["COL_EXTERIOR"].all_objects:
        if obj.hide_render:
            continue
        row = {
            "name": obj.name,
            "code": "COL",
            "type": obj.type,
            "fingerprint": object_fingerprint(obj),
        }
        if obj.type == "MESH":
            corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
            row.update(
                vertices=[list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                faces=[list(p.vertices) for p in obj.data.polygons],
                materials=[m.name if m else None for m in obj.data.materials],
                materialIndices=[p.material_index for p in obj.data.polygons],
                bounds={
                    "min": [min(v[i] for v in corners) for i in range(3)],
                    "max": [max(v[i] for v in corners) for i in range(3)],
                },
            )
        rows.append(row)
    (OUT / "col-exterior-geometry.json").write_text(
        json.dumps({"baselineSha256": SHA, "objects": rows}, separators=(",", ":"))
        + "\n"
    )
    materials, members = {}, []
    for obj in bpy.data.collections["MAR_EXTERIOR"].all_objects:
        if obj.hide_render or obj.type != "MESH":
            continue
        members.append(
            {"object": obj.name, "materials": [m.name for m in obj.data.materials if m]}
        )
        for material in obj.data.materials:
            if not material or material.name in materials:
                continue
            row = {
                "diffuseColour": list(material.diffuse_color),
                "properties": {
                    k: value
                    for k, value in material.items()
                    if isinstance(value, (str, int, float, bool))
                },
            }
            node = (
                material.node_tree.nodes.get("Principled BSDF")
                if material.use_nodes
                else None
            )
            if node:
                row["principled"] = {
                    key: list(node.inputs[key].default_value)
                    if key == "Base Color"
                    else node.inputs[key].default_value
                    for key in [
                        "Base Color",
                        "Metallic",
                        "Roughness",
                        "Transmission Weight",
                        "IOR",
                        "Alpha",
                    ]
                }
            materials[material.name] = row
    folder = ROOT / "result/blender/mar-review247"
    folder.mkdir(exist_ok=True)
    (folder / "native-materials.json").write_text(
        json.dumps(
            {
                "baselineSha256": SHA,
                "nativeUnchanged": True,
                "materials": materials,
                "members": members,
            },
            indent=2,
        )
        + "\n"
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA
    print(
        "NATIVE247_CAPTURED",
        len(state["objects"]),
        len(rows),
        len(materials),
        flush=True,
    )


if __name__ == "__main__":
    main()
