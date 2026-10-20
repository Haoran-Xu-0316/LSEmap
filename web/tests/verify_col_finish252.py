"""Reopen COL252 uniform stone and verify source protection and real export.

The five copies preserve complete source geometry,normals,UV layers and active
UV selections. Uniform stone is tested with actual exporter functions at both
view scales; two private GLBs must have identical constant colour and no image.
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
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_finish252 import (
    BASE,
    JOINERY,
    OUT,
    SHA,
    SOURCE_STONE,
    STONE,
    STONE_LINEAR_RGB,
    TARGETS,
    capture,
    mesh_record,
    render,
    sha,
    write,
)
from refine_kgs_surface237 import normal_record


def shader(material):
    return next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def uniform_material_proof(material, source):
    node, original = shader(material), shader(source)
    assert not node.inputs["Base Color"].is_linked
    assert (
        max(
            abs(a - b)
            for a, b in zip(
                node.inputs["Base Color"].default_value[:3], STONE_LINEAR_RGB
            )
        )
        < 1e-7
    )
    assert (
        max(abs(a - b) for a, b in zip(material.diffuse_color[:3], STONE_LINEAR_RGB))
        < 1e-7
    )
    for key in ["Roughness", "Metallic"]:
        assert node.inputs[key].default_value == original.inputs[key].default_value
    assert not material.get("webBaseColorMap") and "webBaseColorUV" not in material
    assert not any(n.type in {"TEX_IMAGE", "UVMAP"} for n in material.node_tree.nodes)
    return {
        "linearRGB": list(node.inputs["Base Color"].default_value[:3]),
        "roughness": node.inputs["Roughness"].default_value,
        "metallic": node.inputs["Metallic"].default_value,
        "noTextureNodesOrBaseColorLink": True,
    }


def verify_export_material(objects):
    """Load only trusted function definitions; never run the shared release job."""
    path = ROOT / "web/tools/export_scene.py"
    source = ast.parse(path.read_text())
    names = {
        "source_geometry_name",
        "surface_descriptor",
        "web_material",
        "clip_below_ground",
        "clone_group",
    }
    module = ast.Module(
        body=[
            n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names
        ],
        type_ignores=[],
    )
    assert len(module.body) == 5
    namespace = {
        "bpy": bpy,
        "bmesh": bmesh,
        "Vector": Vector,
        "re": re,
        "material_cache": {},
    }
    exec(compile(module, str(path), "exec"), namespace)  # noqa: S102 - five trusted local functions only
    cases = []
    for full in [False, True]:
        for obj in objects:
            if obj.data.materials[0].name != STONE:
                continue
            update_scene()
            namespace["depsgraph"] = bpy.context.evaluated_depsgraph_get()
            namespace["full_detail"] = full
            scene = bpy.data.scenes.new("COL252_EXPORT_PROBE")
            clone, _bounds = namespace["clone_group"](
                [obj], "COL252_UNIFORM_PROBE", scene
            )
            exported = clone.data.materials[0]
            node = shader(exported)
            assert not node.inputs["Base Color"].is_linked
            assert (
                max(
                    abs(a - b)
                    for a, b in zip(
                        node.inputs["Base Color"].default_value[:3], STONE_LINEAR_RGB
                    )
                )
                < 1e-7
            )
            assert not any(n.type == "TEX_IMAGE" for n in exported.node_tree.nodes)
            glb = None
            if obj.name.endswith("perforated_wall"):
                glb_path = OUT / (
                    "export-uniform-detail.glb"
                    if full
                    else "export-uniform-overview.glb"
                )
                bpy.ops.object.select_all(action="DESELECT")
                clone.select_set(True)
                bpy.context.view_layer.objects.active = clone
                bpy.ops.export_scene.gltf(
                    filepath=str(glb_path),
                    export_format="GLB",
                    use_selection=True,
                    use_active_scene=True,
                    export_animations=False,
                )
                data = glb_path.read_bytes()
                length = struct.unpack_from("<I", data, 12)[0]
                document = json.loads(data[20 : 20 + length])
                assert not document.get("images") and not document.get("textures")
                assert len(document["meshes"]) == 1 and len(document["materials"]) == 1
                pbr = document["materials"][0]["pbrMetallicRoughness"]
                assert "baseColorTexture" not in pbr
                assert (
                    max(
                        abs(a - b)
                        for a, b in zip(pbr["baseColorFactor"][:3], STONE_LINEAR_RGB)
                    )
                    < 1e-7
                )
                assert (
                    abs(
                        pbr.get("roughnessFactor", 1)
                        - node.inputs["Roughness"].default_value
                    )
                    < 1e-7
                )
                assert pbr.get("metallicFactor", 1) == 0
                glb = {
                    "path": str(glb_path.relative_to(ROOT)),
                    "sha256": sha(glb_path),
                    "noImagesOrTextures": True,
                    "baseColorFactor": pbr["baseColorFactor"],
                }
            cases.append(
                {
                    "object": obj.name,
                    "view": "detail" if full else "overview",
                    "constantLinearRGBMatchesNative": True,
                    "noTextureNodes": True,
                    "glb": glb,
                }
            )
            mesh = clone.data
            bpy.data.objects.remove(clone, do_unlink=True)
            bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(scene)
            update_scene()
    assert len(cases) == 8
    return {
        "exporterSha256": sha(path),
        "actualExporterCases": cases,
        "allPassed": True,
    }


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / record["componentPath"]
    assert sha(BASE) == SHA == record["baselineSha256"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == protected
    original_materials = {m.name: m for m in bpy.data.materials}
    with bpy.data.libraries.load(str(component), link=False) as (_lib, loaded):
        loaded.objects = list(record["addedObjects"])
    assert {o.name for o in loaded.objects} == set(record["addedObjects"])
    copies = {o.name: o for o in loaded.objects}
    for obj in loaded.objects:
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            if name in original_materials:
                obj.data.materials[index] = original_materials[name]
            else:
                assert (
                    name in record["newMaterials"]
                    and obj.data.materials[index].name == name
                )
        assert object_fingerprint(obj) == record["addedFingerprints"][obj.name]
        bpy.data.collections["COL_EXTERIOR"].objects.link(obj)
        obj.hide_render = False
        obj.hide_set(False)
    material_proof = uniform_material_proof(
        bpy.data.materials[STONE], original_materials[SOURCE_STONE]
    )
    comparisons = []
    for source_name, material in TARGETS.items():
        source = bpy.data.objects[source_name]
        obj = copies["COL252_FINISH_" + source_name]
        assert mesh_record(obj) == mesh_record(source), obj.name
        assert normal_record(obj.data) == normal_record(source.data), obj.name
        assert obj.data.materials[0].name == material
        if material == JOINERY:
            assert obj.data.materials[0] == original_materials[JOINERY]
        source.hide_render = True
        source.hide_set(True)
        comparisons.append(
            {
                "source": source.name,
                "replacement": obj.name,
                "geometryTopologyNormalsAllUVsAndActiveUVExactlyEqual": True,
                "faces": len(source.data.polygons),
                "corners": len(source.data.loops),
                "material": material,
                "extraUVLayers": [],
            }
        )
    update_scene()
    after = capture()
    for name, row in protected["objects"].items():
        expected = dict(row)
        if name in TARGETS:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    for name, expected in protected["materials"].items():
        assert after["materials"][name] == expected, name
    assert (
        after["rooms"] == protected["rooms"]
        and after["campusRooms"] == protected["campusRooms"]
    )
    assert set(after["objects"]) == set(protected["objects"]) | set(
        record["addedObjects"]
    )
    assert len(protected["rooms"]) == 35
    for name in [
        "COL249_Houghton_glazing",
        "COL249_Houghton_opaque_ground_infill",
        "COL249_Houghton_closed_backing",
        "COL251_closed_source_height_roof",
        "COL251_retained_glazing_outside_source_apertures",
    ]:
        assert after["objects"][name] == protected["objects"][name]
    visible = [
        o
        for o in bpy.data.collections["COL_EXTERIOR"].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    render(visible, "after-front", "front")
    render(visible, "after-oblique", "oblique")
    export_proof = verify_export_material(loaded.objects)
    result = {
        "savedComponentReopened": True,
        "baselineSha256": SHA,
        "componentSha256": sha(component),
        "sourceNativeBytesUnchanged": sha(BASE) == SHA,
        "originalObjectsPreserved": len(protected["objects"]),
        "originalMaterialGraphsPreserved": len(protected["materials"]),
        "protectedRooms": len(protected["rooms"]),
        "protectedRoomObjects": len(
            {n for members in protected["rooms"].values() for n in members}
        ),
        "allOriginalGeometryUVNormalsBindingsTransformsModifiersPropertiesOwnersPreserved": True,
        "unrelatedVisibilityPreserved": True,
        "replacementComparisons": comparisons,
        "originalMetricUVAndUVMapBytesUnchanged": True,
        "allUVLayersAndActiveSelectionsUnchanged": True,
        "uniformStoneMaterialProof": material_proof,
        "actualExporterUniformMaterialProof": export_proof,
        "all72ModulesGlassBackingsAndRoofGeometryUnchanged": True,
        "glassMaterialAndTransmissionUnchanged": True,
        "sameLightingBeforeAfter": True,
        "source251RayAcceptancePreservedByIdenticalPositionsAndTopology": {
            "farOpeningBackingRays": 216,
            "farFirstHitChecks": 72,
            "farEaveAndRoofHoleRays": 96,
            "note": "Geometry equality verified here;prior251 rays inherited,not rerun.",
        },
        "visualFiles": [
            "before-front.png",
            "before-oblique.png",
            "after-front.png",
            "after-oblique.png",
        ],
    }
    write("saved-verification.json", result)
    record.update(
        status="uniform_stone_saved_reopened_all_gates_passed_pending_visual_review",
        savedComponentReopened=True,
    )
    write("audit.json", record)
    print(
        "COL252_UNIFORM_REOPENED",
        len(comparisons),
        len(protected["objects"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
