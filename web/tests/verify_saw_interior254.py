"""Independently reopen the Three Tuns correction and test the real GLB export.

All original native objects/materials and 35 room memberships are checked.
The only room membership addition is its replacement glass. Production export
must emit BLEND with accepted SAW opacity and no transmission extension/images.
"""

import ast
import json
import re
import struct
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha
from refine_kgs_surface237 import normal_record
from refine_saw_interior254 import (
    BASE,
    COLLECTION,
    FAMILY,
    MATERIAL,
    OPACITY,
    OUT,
    REPLACEMENT,
    SHA,
    SOURCE,
    capture,
    check_protection,
    shader,
    write,
)


def export_proof(obj):
    path = ROOT / "web/tools/export_scene.py"
    parsed = ast.parse(path.read_text())
    names = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
    }
    definitions = [
        n for n in parsed.body if isinstance(n, ast.FunctionDef) and n.name in names
    ]
    assert len(definitions) == len(names)
    namespace = {
        "bpy": bpy,
        "bmesh": bmesh,
        "Vector": Vector,
        "re": re,
        "material_cache": {},
    }
    exec(  # noqa: S102 - trusted production functions
        compile(ast.Module(body=definitions, type_ignores=[]), str(path), "exec"),
        namespace,
    )
    cases = []
    for detail in [False, True]:
        namespace["full_detail"] = detail
        namespace["depsgraph"] = bpy.context.evaluated_depsgraph_get()
        scene = bpy.data.scenes.new("SAW254_EXPORT_PROBE")
        clone, _ = namespace["clone_group"]([obj], "SAW254_GLASS_PROBE", scene)
        bpy.context.window.scene = scene
        bpy.ops.object.select_all(action="DESELECT")
        clone.select_set(True)
        bpy.context.view_layer.objects.active = clone
        output = OUT / ("glass-detail.glb" if detail else "glass-overview.glb")
        bpy.ops.export_scene.gltf(
            filepath=str(output),
            export_format="GLB",
            use_selection=True,
            use_active_scene=True,
            export_animations=False,
            export_extras=True,
        )
        raw = output.read_bytes()
        size = struct.unpack_from("<I", raw, 12)[0]
        document = json.loads(raw[20 : 20 + size])
        assert len(document["materials"]) == 1
        material = document["materials"][0]
        pbr = material["pbrMetallicRoughness"]
        assert material["alphaMode"] == "BLEND"
        assert abs(pbr["baseColorFactor"][3] - OPACITY) < 1e-6
        assert pbr["metallicFactor"] == 0
        assert (
            abs(
                pbr["roughnessFactor"]
                - shader(bpy.data.materials[FAMILY]).inputs["Roughness"].default_value
            )
            < 1e-6
        )
        assert "KHR_materials_transmission" not in document.get("extensionsUsed", [])
        assert not document.get("images") and not document.get("textures")
        assert material["extras"]["webSurfaceRole"] == "glazing"
        cases.append(
            {
                "detail": detail,
                "path": str(output.relative_to(ROOT)),
                "sha256": sha(output),
                "material": material,
            }
        )
        mesh = clone.data
        bpy.data.objects.remove(clone, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        bpy.data.scenes.remove(scene)
        update_scene()
    return cases


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == protected
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [REPLACEMENT]
    obj = loaded.objects[0]
    assert obj and obj.name == REPLACEMENT
    assert object_fingerprint(obj) == record["addedFingerprints"][REPLACEMENT]
    assert obj.data.materials[0].name == MATERIAL
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.hide_render = False
    set_layer_hidden(obj, False)
    original = bpy.data.objects[SOURCE]
    assert mesh_record(obj) == mesh_record(original)
    assert normal_record(obj.data) == normal_record(original.data)
    original.hide_render = True
    set_layer_hidden(original, True)
    candidate = shader(obj.data.materials[0])
    family = shader(bpy.data.materials[FAMILY])
    for key in ["Base Color", "Metallic", "Roughness", "Transmission Weight", "Alpha"]:
        value = candidate.inputs[key].default_value
        accepted = family.inputs[key].default_value
        assert (
            (tuple(value) == tuple(accepted))
            if key == "Base Color"
            else value == accepted
        ), key
    assert obj.data.materials[0]["webOpacity"] == OPACITY
    update_scene()
    check_protection(protected, capture(), [REPLACEMENT])
    cases = export_proof(obj)
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(protected["objects"]),
            "protectedOriginalMaterials": len(protected["materials"]),
            "protectedRoomStudies": len(protected["rooms"]),
            "sourceGeometryUVAndNormalsUnchanged": True,
            "onlyGlassMaterialReplacement": True,
            "exporterSha256": sha(ROOT / "web/tools/export_scene.py"),
            "actualExportCases": cases,
            "visualReviewRequired": True,
        },
    )
    print("SAW254_INDEPENDENT_VERIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
