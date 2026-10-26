"""Check real Blender append dependencies without opening the campus source."""

import json
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import discard_unused_component_materials
from refine_portsmouth_exterior207 import material_fingerprint


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    retained = bpy.data.materials.new("MATERIAL269_retained")
    retained.use_nodes = True
    retained.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (
        0.12,
        0.34,
        0.56,
        1,
    )
    original_fingerprint = material_fingerprint(retained)
    original_pointer = retained.as_pointer()
    baseline_unowned = bpy.data.materials.new("MATERIAL269_baseline_unowned")
    assert baseline_unowned.users == 0
    mesh = bpy.data.meshes.new("MATERIAL269_component_mesh")
    mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
    mesh.materials.append(retained)
    obj = bpy.data.objects.new("MATERIAL269_component", mesh)
    with tempfile.TemporaryDirectory(prefix="lsemap-material269-") as folder:
        component = Path(folder) / "component.blend"
        bpy.data.libraries.write(str(component), {obj}, fake_user=False)
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        before = set(bpy.data.materials.keys())
        with bpy.data.libraries.load(str(component), link=False) as (_, destination):
            destination.objects = ["MATERIAL269_component"]
        appended = destination.objects[0]
        imported = appended.data.materials[0]
        assert imported.name not in before and imported is not retained
        appended.data.materials[0] = retained
        declared = bpy.data.materials.new("MATERIAL269_declared_unused")
        used = bpy.data.materials.new("MATERIAL269_new_used")
        appended.data.materials.append(used)
        report = {
            "newMaterialGraphs": {declared.name: "declared"},
            "addedMaterialFingerprints": {},
        }
        removed = discard_unused_component_materials(before, report)
        assert len(removed) == 1 and removed[0].startswith("MATERIAL269_retained.")
        assert (
            retained.as_pointer() == original_pointer
            and material_fingerprint(retained) == original_fingerprint
        )
        assert set(bpy.data.materials.keys()) == before | {declared.name, used.name}
        assert (
            baseline_unowned.name in bpy.data.materials
            and baseline_unowned.users == 0
            and used.users == 1
        )
        assert (
            discard_unused_component_materials(set(bpy.data.materials.keys()), report)
            == []
        )
    output = ROOT / "result/blender/stage269"
    output.mkdir(parents=True, exist_ok=True)
    (output / "append-material-verification.json").write_text(
        json.dumps(
            {
                "passed": True,
                "realBlenderLibraryAppend": True,
                "baselineMaterialIdentityAndGraphPreserved": True,
                "baselineUnusedMaterialPreserved": True,
                "declaredUnusedMaterialPreserved": True,
                "newUsedMaterialPreserved": True,
                "discardedUnusedImportedCopies": removed,
                "idempotent": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("COMPONENT269_MATERIAL_DEPENDENCIES_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
