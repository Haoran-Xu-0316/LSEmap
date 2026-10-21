"""Restore the photographed Three Tuns glass using an accepted SAW material.

This bounded historical entrance sample retains its existing footprint, walls,
lettering and timber. No furniture, opaque backing or current layout is inferred.
The Denning glass family is reused; its alpha approximation is not calibrated.
Run with the fixed project paths in Blender. No release or shared data is changed.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v252.blend"
SHA = "61d1d4cd71c3f1cffc4409d9c304d00bfdb33409ecb1b88c564caaf8678e782e"
OUT = ROOT / "result/blender/saw254"
SOURCE = "SAW_V48_TUNS_glass"
FAMILY = "SAW_V24_DENNING_glass"
MATERIAL = "SAW254_three_tuns_clear_glass"
REPLACEMENT = "SAW254_Three_Tuns_clear_glass"
COLLECTION = "SAW_THREE_TUNS_study"
OPACITY = 0.30
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha
from refine_kgs_surface237 import normal_record


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "saw254_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def shader(material):
    return next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def check_protection(before, after, target_names):
    """Original mesh/material data stay exact; only the old panel is archived."""
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    for room, members in before["rooms"].items():
        expected = sorted(members + target_names) if room == COLLECTION else members
        assert after["rooms"][room] == expected, room
    assert after["campusRooms"] == before["campusRooms"]
    assert len(before["rooms"]) == 35


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Inspect existing candidate before overwriting"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    source = bpy.data.objects[SOURCE]
    assert source.type == "MESH" and len(source.data.materials) == 1
    assert source in bpy.data.collections[COLLECTION].all_objects.values()
    original = source.data.materials[0]
    original_shader = shader(original)
    assert original_shader.inputs["Alpha"].default_value == 1
    assert original_shader.inputs["Transmission Weight"].default_value < 0.1
    accepted = bpy.data.materials[FAMILY]
    assert shader(accepted).inputs["Transmission Weight"].default_value > 0.1
    material = accepted.copy()
    material.name = MATERIAL
    # This trigger is converted by export_scene into lightweight BLEND alpha.
    # It does not add screen-space transmission to the web renderer.
    material["webOpacity"] = OPACITY
    material["referenceScope"] = (
        "Undated official Three Tuns photo; reuse accepted Denning glass family; optical values estimated"
    )
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = REPLACEMENT
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = SOURCE
    obj["destinationCollection"] = COLLECTION
    obj["referenceScope"] = material["referenceScope"]
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.data.materials[0] = material
    obj.hide_render = False
    set_layer_hidden(obj, False)
    assert mesh_record(obj) == mesh_record(source)
    assert normal_record(obj.data) == normal_record(source.data)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    after = capture()
    check_protection(before, after, [REPLACEMENT])
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    photo = ROOT / "data/collections/public-realm-2026/bars/three-tuns-reference.jpg"
    write(
        "audit.json",
        {
            "version": 254,
            "building": "SAW",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "targetCollection": COLLECTION,
            "destinationCollection": COLLECTION,
            "addedObjects": [REPLACEMENT],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {REPLACEMENT: object_fingerprint(obj)},
            "replacementMaterialBindings": {REPLACEMENT: [MATERIAL]},
            "newMaterials": [MATERIAL],
            "newMaterialGraphs": {MATERIAL: after["materials"][MATERIAL]},
            "uvAliases": [],
            "materialFamily": FAMILY,
            "webOpacity": OPACITY,
            "originalMaterial": {
                "name": original.name,
                "linearRGB": list(original_shader.inputs["Base Color"].default_value),
                "metallic": original_shader.inputs["Metallic"].default_value,
                "roughness": original_shader.inputs["Roughness"].default_value,
                "transmission": original_shader.inputs[
                    "Transmission Weight"
                ].default_value,
                "alpha": original_shader.inputs["Alpha"].default_value,
            },
            "sources": [
                {
                    "path": str(photo.relative_to(ROOT)),
                    "sha256": sha(photo),
                    "url": "https://info.lse.ac.uk/current-students/estates-division/Assets/Images/3-Tuns.jpg",
                    "supports": "Transparent pane and pale lettering in timber frame; capture date unknown",
                }
            ],
            "status": "saved_awaiting_independent_reopen",
            "limitations": [
                "Historical independent entrance and 2014 plan sample; not a complete bar interior or current refurbishment reconstruction.",
                "Only glass optics change. Existing source-based plan and four wall segments remain visible behind the pane; no new backing or furniture.",
                "Denning family and alpha .30 are accepted approximate display values, not calibrated photo measurements.",
                "No source photograph is exported as texture; all geometry, lettering, wood and other rooms remain intact.",
            ],
        },
    )
    assert sha(BASE) == SHA
    print("SAW254_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
