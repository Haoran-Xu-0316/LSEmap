"""Capture native269 SAW meshes for offline construction and interface analysis.

The parent runs this once in a fresh Blender process. No model, visibility,
material or scene is changed and no .blend is saved. Plain JSON is the only
output, so later CPU geometry analysis never retains Blender RNA wrappers.
"""
import importlib.util
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw270"
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
EXPECTED = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"


def main():
    spec = importlib.util.spec_from_file_location("saw270_preflight", ROOT / "web/tests/inspect_saw_baseline270.py")
    preflight = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preflight)
    assert preflight.sha(BASE) == EXPECTED
    proof = json.loads((OUT / "baseline-preservation.json").read_text())
    assert proof["comparedObjects"] == 195 and not proof["differences"]
    inspection = json.loads((ROOT / "result/blender/saw269/native-inspection.json").read_text())
    if Path(bpy.data.filepath).resolve() != BASE.resolve():
        bpy.ops.wm.open_mainfile(filepath=str(BASE))
    records = preflight.inventory(inspection)
    assert {name: preflight.digest_json(value) for name, value in records.items()} == proof["fingerprints269"]
    visible = set(inspection["visibleObjects"])
    meshes = []
    for name in sorted(visible):
        obj = bpy.data.objects[name]
        mesh = obj.data
        meshes.append({"name": name, "worldMatrix": [list(row) for row in obj.matrix_world],
            "vertices": [list(vertex.co) for vertex in mesh.vertices],
            "polygons": [list(poly.vertices) for poly in mesh.polygons],
            "materialIndices": [poly.material_index for poly in mesh.polygons],
            "smoothFaces": [poly.use_smooth for poly in mesh.polygons],
            "uvLayers": [{"name": layer.name, "uv": [list(loop.uv) for loop in layer.data]} for layer in mesh.uv_layers],
            "materials": [None if material is None else material.name for material in mesh.materials],
            "owners": [collection.name for collection in obj.users_collection],
            "modifiers": [preflight.rna_scalars(modifier) for modifier in obj.modifiers]})
    payload = {"status": "read-only-native-mesh-capture", "nativeSha256": EXPECTED,
        "objectCount": len(meshes), "objects": meshes, "savedMeshCoordinates": True,
        "modelWritten": False, "materialsChanged": False}
    (OUT / "native-visible-meshes.json").write_text(json.dumps(payload, separators=(",", ":"))+"\n")
    assert preflight.sha(BASE) == EXPECTED
    print("SAW270_MESH_CAPTURE", len(meshes), flush=True)


if __name__ == "__main__":
    main()
