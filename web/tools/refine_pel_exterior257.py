"""Restore only PEL's photographed yellow canopy underside.

The official estate photograph shows a warm yellow soffit between the existing
yellow entry reveals. Reuse that accepted yellow family on the physical lower
face of the existing canopy box. No other face, geometry, UV, glass or material
graph changes. The historical photograph does not calibrate colour or2026state.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v256.blend"
SHA = "31657c42eb77323d2273bc525ad4db3164fbaa644ddbe6af3b66e44c8679efa1"
OUT = ROOT / "result/blender/pel257"
SOURCE = "PEL_D5_entry61_canopy_soffit_dark"
REPLACEMENT = "PEL257_yellow_canopy_lower_face"
YELLOW = "PEL_V61_yellow"
COLLECTION = "PEL_EXTERIOR"
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
        "pel257_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def lower_face(obj):
    """Select the physical bottom in world space, never an assumed face index."""
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    low, high = min(p.z for p in points), max(p.z for p in points)
    assert 0.03 < high - low < 0.04
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    candidates = []
    for face in obj.data.polygons:
        vertices = [points[index] for index in face.vertices]
        normal = (normal_matrix @ face.normal).normalized()
        if all(abs(p.z - low) < 1e-6 for p in vertices):
            assert abs(normal.z) > 0.999999
            candidates.append((face.index, normal))
    assert len(candidates) == 1
    face_index, normal = candidates[0]
    return face_index, {
        "faceIndex": face_index,
        "worldMinimumHeight": low,
        "worldMaximumHeight": high,
        "storedWorldNormal": list(normal),
        "physicalExteriorDirection": [0, 0, -1],
        "selectionPolicy": "All face corners on the box's lowest world Zplane; transformed normal perpendicular to that plane. Original winding/normals retained.",
    }


def verify_geometry(source, obj, index):
    before, after = mesh_record(source), mesh_record(obj)
    assert all(
        before[key] == value for key, value in after.items() if key != "faceMaterials"
    )
    assert normal_record(source.data) == normal_record(obj.data)
    assert len(source.data.vertices) == len(obj.data.vertices) == 8
    assert len(source.data.polygons) == len(obj.data.polygons) == 6
    assert len(source.data.materials) == 1
    assert [m.name for m in obj.data.materials] == [
        source.data.materials[0].name,
        YELLOW,
    ]
    assert all(
        p.material_index
        == (1 if p.index == index else source.data.polygons[p.index].material_index)
        for p in obj.data.polygons
    )
    assert sum(p.material_index == 1 for p in obj.data.polygons) == 1


def check_protection(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    protected = capture()
    write("protected-source-state.json", protected)
    source = bpy.data.objects[SOURCE]
    assert source.type == "MESH" and not source.hide_render
    assert len(source.data.materials) == 1
    assert source.data.materials[0].name == "PEL_V61_dark"
    index, selection = lower_face(source)
    yellow = bpy.data.materials[YELLOW]
    assert (
        yellow
        == bpy.data.objects["PEL_D5_entry61_yellow_reveal_yellow"].data.materials[0]
    )
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = REPLACEMENT
    obj.data.name = REPLACEMENT + "_mesh"
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = source.get("webGeometrySource", SOURCE)
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Only photographed lower canopy face reuses existing yellow entry finish; undated source"
    )
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.data.materials.append(yellow)
    obj.data.polygons[index].material_index = 1
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    verify_geometry(source, obj, index)
    check_protection(protected, capture())
    obj.data.calc_loop_triangles()
    probes = []
    for triangle in obj.data.loop_triangles:
        if triangle.polygon_index != index:
            continue
        point = (
            sum(
                (obj.matrix_world @ obj.data.vertices[i].co for i in triangle.vertices),
                Vector(),
            )
            / 3
        )
        probes.append(
            {
                "origin": list(point + Vector((0, 0, -0.1))),
                "direction": [0, 0, 1],
                "expectedDistanceMetres": 0.1,
                "expectedMaterial": YELLOW,
                "physicalFace": "canopy underside viewed from below",
            }
        )
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    photo = (
        ROOT
        / "data/建筑图片/PEL_Pethick-Lawrence House/01_建筑实拍/exteriors_lse_estate_023.jpg"
    )
    write(
        "audit.json",
        {
            "version": 257,
            "building": "PEL",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "addedObjects": [REPLACEMENT],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {REPLACEMENT: object_fingerprint(obj)},
            "replacementMaterialBindings": {
                REPLACEMENT: [source.data.materials[0].name, YELLOW]
            },
            "newMaterials": [],
            "newMaterialGraphs": {},
            "retainNewMaterials": True,
            "materialFamily": YELLOW,
            "worldFaceSelection": selection,
            "reassignedFaces": [index],
            "faceProbes": probes,
            "sourceRefs": [
                {
                    "path": str(photo.relative_to(ROOT)),
                    "sha256": sha(photo),
                    "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Pethick-Lawrence-web.jpg",
                    "date": "Capture date unknown; historical official estate image, not a2026survey",
                    "supports": "Warm yellow canopy underside continuous with yellow entrance reveals",
                    "crop": "result/blender/pel257/canopy-underside-source-crop.png",
                    "sourceCropBox": [10, 284, 255, 326],
                }
            ],
            "limitations": [
                "Only the lower face changes material. The other five dark faces and all original mesh/UV/normal data stay exact.",
                "Existing yellow material is reused; no new colour, light or optical coefficient is calibrated from the photograph.",
                "Single historical estate photograph supports this local finish; exact capture date/current refurbishment remain unverified.",
                "All glass, upper massing, roof, window cadence and35room studies remain unchanged.",
            ],
        },
    )
    assert sha(BASE) == SHA
    print("PEL257_YELLOW_UNDERSIDE_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
