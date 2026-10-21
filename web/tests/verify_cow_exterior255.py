"""Independently reopen Cowdray's corrected cornice and prove exact face retention."""

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    geometry_policy_name,
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha
from refine_cow_exterior255 import (
    BASE,
    COLLECTION,
    HEAD_REPLACEMENT,
    HEAD_SOURCE,
    OUT,
    REPLACEMENT,
    SHA,
    SOURCE,
    capture,
    check_protection,
    evaluated_other_head_records,
    find_short_belt,
    verify_remainder,
    wall_join_rays,
    write,
)
from refine_kgs_surface237 import normal_record


def export_proof():
    """Actual production clone/material functions and Draco20-bit outputs."""
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
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(definitions) == 5
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
    objects = list(bpy.data.collections[COLLECTION].all_objects)
    flags = []
    for obj in objects:
        for modifier in obj.modifiers:
            if modifier.type == "BEVEL":
                flags.append((modifier, modifier.show_viewport, modifier.show_render))
                if not geometry_policy_name(obj).startswith("COW_NEXT_"):
                    modifier.show_viewport = False
                    modifier.show_render = False
    cases = []
    try:
        for detail in [False, True]:
            update_scene()
            namespace["depsgraph"] = bpy.context.evaluated_depsgraph_get()
            namespace["full_detail"] = detail
            scene = bpy.data.scenes.new("COW255_JOIN_EXPORT_PROOF")
            clone, _ = namespace["clone_group"](objects, "COW255_JOIN_EXPORT", scene)
            bpy.context.window.scene = scene
            bpy.ops.object.select_all(action="DESELECT")
            clone.select_set(True)
            bpy.context.view_layer.objects.active = clone
            output = OUT / (
                "join-export-detail.glb" if detail else "join-export-overview.glb"
            )
            bpy.ops.export_scene.gltf(
                filepath=str(output),
                export_format="GLB",
                use_selection=True,
                use_active_scene=True,
                export_extras=True,
                export_animations=False,
                export_draco_mesh_compression_enable=True,
                export_draco_mesh_compression_level=6,
                export_draco_position_quantization=20,
            )
            cases.append(
                {
                    "detail": detail,
                    "path": str(output.relative_to(ROOT)),
                    "sha256": sha(output),
                }
            )
            bpy.data.objects.remove(clone, do_unlink=True)
            bpy.data.scenes.remove(scene)
    finally:
        for modifier, viewport, render in flags:
            modifier.show_viewport = viewport
            modifier.show_render = render
        update_scene()
    return cases


def main():
    record = json.loads((OUT / "audit.json").read_text())
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / record["componentPath"]
    assert sha(BASE) == SHA == record["baselineSha256"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == protected
    source = bpy.data.objects[SOURCE]
    vertices, removed_faces = find_short_belt(source)
    assert sorted(vertices) == record["removedSourceVertices"]
    assert removed_faces == record["removedSourceFaces"]
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [REPLACEMENT, HEAD_REPLACEMENT]
    obj = loaded.objects[0]
    head = loaded.objects[1]
    assert head.name == HEAD_REPLACEMENT
    bpy.data.collections[COLLECTION].objects.link(head)
    for index, name in enumerate(
        record["replacementMaterialBindings"][HEAD_REPLACEMENT]
    ):
        head.data.materials[index] = bpy.data.materials[name]
    head.hide_render = False
    set_layer_hidden(head, False)
    original_head = bpy.data.objects[HEAD_SOURCE]
    original_head.hide_render = True
    set_layer_hidden(original_head, True)
    weights = [value.value for value in head.data.attributes["bevel_weight_edge"].data]
    expected = record["headBevel"]
    assert weights == expected["weights"]
    assert (
        hashlib.sha256(json.dumps(weights).encode()).hexdigest()
        == expected["weightsSha256"]
    )
    assert [index for index, value in enumerate(weights) if value == 0] == record[
        "cancelledInternalBevelEdges"
    ]
    assert len(record["cancelledInternalBevelEdges"]) == 32
    assert all(value in [0, 1] for value in weights)
    assert (
        head.modifiers[0].limit_method == expected["candidateLimitMethod"] == "WEIGHT"
    )
    assert (
        original_head.modifiers[0].limit_method
        == expected["sourceLimitMethod"]
        == "ANGLE"
    )
    assert (
        head.modifiers[0].width == expected["width"] == original_head.modifiers[0].width
    )
    assert (
        head.modifiers[0].segments
        == expected["segments"]
        == original_head.modifiers[0].segments
    )
    assert geometry_policy_name(head) == geometry_policy_name(original_head)
    assert head["webGeometrySource"] == expected["geometryPolicySource"]
    assert mesh_record(head) == mesh_record(original_head)
    assert normal_record(head.data) == normal_record(original_head.data)
    update_scene()
    assert evaluated_other_head_records(head) == evaluated_other_head_records(
        original_head
    )
    assert object_fingerprint(head) == record["addedFingerprints"][HEAD_REPLACEMENT]
    assert obj.name == REPLACEMENT
    bpy.data.collections[COLLECTION].objects.link(obj)
    bindings = record["replacementMaterialBindings"][REPLACEMENT]
    assert len(bindings) == len(obj.data.materials)
    for index, name in enumerate(bindings):
        obj.data.materials[index] = bpy.data.materials[name]
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    assert object_fingerprint(obj) == record["addedFingerprints"][REPLACEMENT]
    assert all(
        material == source.data.materials[index]
        for index, material in enumerate(obj.data.materials)
    )
    remainder = verify_remainder(source, obj, removed_faces)
    assert remainder == record["retainedFaceProof"]
    source.data.calc_loop_triangles()
    obj.data.calc_loop_triangles()
    assert len(source.data.loop_triangles) - len(obj.data.loop_triangles) == 12
    assert len(source.data.vertices) - len(obj.data.vertices) == 8
    try:
        find_short_belt(obj)
    except AssertionError as error:
        assert "Expected one independent short-street belt" in str(error)
    else:
        raise AssertionError("Unsupported belt is still present")
    rays = wall_join_rays()
    assert len(rays) == 105
    check_protection(protected, capture())
    export_cases = export_proof()
    check_protection(protected, capture())
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(protected["objects"]),
            "protectedOriginalMaterials": len(protected["materials"]),
            "protectedRoomStudies": len(protected["rooms"]),
            "allRetainedFaceCoordinatesUVNormalsAndBindingsExact": True,
            "removedIndependentBoxes": 1,
            "removedTriangles": 12,
            "retainedFaceProof": remainder,
            "shortStreetRegistrationVerified": True,
            "savedEvaluatedJoinRays": rays,
            "headBevel": expected,
            "actualProductionExports": export_cases,
            "decodedExportRayVerificationRequired": True,
            "visualReviewRequired": True,
        },
    )
    print("COW255_INDEPENDENT_SHORT_BELT_VERIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
