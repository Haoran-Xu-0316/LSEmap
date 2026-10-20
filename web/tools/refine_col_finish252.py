"""Unify COL's photographed stone and painted frames without relighting campus.

Fixed-path Blender component builder. Native251 remains read-only; every source
mesh/UV/normal and all original material graphs remain intact. The established
COL195 original tone study is reused, not calibrated photographic colour.
"""

import array
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-finish252"
BASE = ROOT / "result/blender/LSE_campus_detailed_v251.blend"
SHA = "6fa67b6a4640411c1065f9ca5f4d660150bb9075968f8adf881267fe1a39a6e9"
SOURCE_STONE = "COL195_FINISH_STREET_D4_limestone"
STONE = "COL252_photo_guided_uniform_stone"
STONE_LINEAR_RGB = (0.6435385, 0.6400502, 0.5887114)
JOINERY = "COL195_FINISH_STREET_D4_dark_bronze_frames"
TARGETS = {
    "COL249_Houghton_perforated_wall": STONE,
    "COL249_Houghton_reveals": STONE,
    "COL249_Houghton_stone_bands": STONE,
    "COL251_window_avoiding_eave_line": STONE,
    "COL249_Houghton_joinery": JOINERY,
}
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "col252_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def mesh_record(obj):
    """Exact coordinate, topology, face bindings and original UV bytes."""
    mesh = obj.data
    result = {"matrix": [list(row) for row in obj.matrix_world]}
    for label, values, field, kind, count in (
        ("vertices", mesh.vertices, "co", "f", 3),
        ("loops", mesh.loops, "vertex_index", "i", 1),
        ("faceSizes", mesh.polygons, "loop_total", "i", 1),
        ("faceMaterials", mesh.polygons, "material_index", "i", 1),
    ):
        buffer = array.array(kind, [0]) * (len(values) * count)
        values.foreach_get(field, buffer)
        result[label] = hashlib.sha256(buffer.tobytes()).hexdigest()
    result["activeUV"] = mesh.uv_layers.active.name if mesh.uv_layers.active else None
    result["activeRenderUV"] = [uv.name for uv in mesh.uv_layers if uv.active_render]
    result["uv"] = {}
    for uv in mesh.uv_layers:
        buffer = array.array("f", [0]) * (len(uv.data) * 2)
        uv.data.foreach_get("uv", buffer)
        result["uv"][uv.name] = hashlib.sha256(buffer.tobytes()).hexdigest()
    return result


def diagnose():
    registration = json.loads(
        (ROOT / "result/blender/col-registration249/registration-plan.json").read_text()
    )
    outside = -Vector((*registration["inwardNormal"], 0))
    origin = Vector((*registration["frontageNorthToSouth"][0], 0))
    wall = bpy.data.objects["COL249_Houghton_perforated_wall"]
    wall.data.update()
    front = []
    agreements = []
    for face in wall.data.polygons:
        centre = wall.matrix_world @ face.center
        # Real exterior plane; the parallel inward face is intentionally excluded.
        if abs((centre - origin).dot(outside)) < 0.002:
            normal = (wall.matrix_world.to_3x3() @ face.normal).normalized()
            if abs(normal.dot(outside)) > 0.95:
                front.append(normal.dot(outside))
                for li in face.loop_indices:
                    corner = (
                        wall.matrix_world.to_3x3() @ wall.data.corner_normals[li].vector
                    )
                    agreements.append(corner.normalized().dot(normal))
    assert len(front) > 100
    assert min(front) > 0.999, (
        "True front winding is incorrect; stop material-only build"
    )
    assert min(agreements) > 0.999, "Corner normals disagree; stop material-only build"
    suns = []
    for o in bpy.data.scenes["00_CAMPUS_COMPLETE"].objects:
        if o.type == "LIGHT" and o.data.type == "SUN" and not o.hide_render:
            to_sun = (o.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
            suns.append(
                {
                    "name": o.name,
                    "energy": o.data.energy,
                    "frontDirectIncidenceCosine": outside.dot(to_sun),
                    "sunDirectionTowardSource": list(to_sun),
                }
            )
    image = next(
        n.image
        for n in bpy.data.materials[SOURCE_STONE].node_tree.nodes
        if n.type == "TEX_IMAGE" and n.image
    )
    # This archived PNG exposes stored sRGB pixel values; explicitly decode
    # sRGB for a comparable linear-light base-colour diagnostic.
    pixels = list(image.pixels)
    rgb = [[pixels[i + c] for i in range(0, len(pixels), 4)] for c in range(3)]
    means = [sum(values) / len(values) for values in rgb]
    return {
        "trueFrontPlaneFaces": len(front),
        "minimumGeometricNormalOutsideDot": min(front),
        "minimumCornerToGeometricNormalDot": min(agreements),
        "wallHasCustomNormals": wall.data.has_custom_normals,
        "nativeCampusSuns": suns,
        "oldEstimatedStoneLinearBase": list(
            bpy.data.materials["COL249_estimated_neutral_stone"].diffuse_color[:3]
        ),
        "acceptedStonePackedImageStoredSRGBMean": means,
        "acceptedStonePackedImageLinearMean": [
            v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in means
        ],
        "conclusion": "True front normals are correct; source-study warm solid colour and directional shade both contribute. No normal,light,exposure or glass edits.",
        "colourLimit": "Photograph-guided finish family only; neither archive photos nor tone study are colour calibrated.",
    }


def render(objects, label, kind):
    scene = bpy.data.scenes.new("COL252_REVIEW_" + label)
    for obj in objects:
        scene.collection.objects.link(obj)
    world = bpy.data.worlds.new(scene.name)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.8,
        0.82,
        0.85,
        1,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
    scene.world = world
    origin = Vector((3.4640423866, -99.5537499389, 0))
    axis = Vector((0.091211076841, -0.995831581876, 0))
    inward = Vector((0.995831581876, 0.091211076841, 0))
    target = origin + axis * 15 + Vector((0, 0, 17))
    data = bpy.data.cameras.new(scene.name)
    camera = bpy.data.objects.new(scene.name + "_camera", data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    offset = (
        -inward * 70
        if kind == "front"
        else -inward * 65 + axis * 26 + Vector((0, 0, 12))
    )
    camera.location = target + offset
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    data.type = "ORTHO"
    data.ortho_scale = 40
    data.clip_end = 500
    light = bpy.data.lights.new(scene.name, "AREA")
    light.energy = 1800
    light.size = 12
    lamp = bpy.data.objects.new(scene.name + "_light", light)
    scene.collection.objects.link(lamp)
    lamp.location = target - inward * 25 - axis * 10 + Vector((0, 0, 24))
    lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / (label + ".png"))
    bpy.context.window.scene = scene
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for obj in [camera, lamp]:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(light)
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()


def build_component():
    OUT.mkdir(parents=True, exist_ok=True)
    previous_component = OUT / "component.blend"
    if previous_component.exists():
        previous = json.loads((OUT / "audit.json").read_text())
        assert previous["componentSha256"] == sha(previous_component)
        assert (
            previous["componentSha256"]
            == "810e34ab3c12587f9216a27a40fc489e7766fc26b0602c9442be6e7193e5e516"
        )
        write(
            "superseded-frequency-candidate.json",
            {
                "sha256": previous["componentSha256"],
                "reason": "Main-thread actual web review rejected5m diagonal cloud pattern; replaced by uniform mean colour.",
                "previousVisualReview": previous["visualReview"],
            },
        )
        previous_component.unlink()
    assert sha(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    bpy.context.preferences.filepaths.save_version = 0
    before = capture()
    write("protected-source-state.json", before)
    write("normal-light-material-diagnosis.json", diagnose())
    visible = [
        o
        for o in bpy.data.collections["COL_EXTERIOR"].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    render(visible, "before-front", "front")
    render(visible, "before-oblique", "oblique")
    collection = bpy.data.collections.new("COL252_FINISH_CANDIDATE")
    bpy.context.scene.collection.children.link(collection)
    source_stone = bpy.data.materials[SOURCE_STONE]
    stone = source_stone.copy()
    stone.name = STONE
    for key in ["webBaseColorMap", "webBaseColorUV", "webBaseColorTint"]:
        if key in stone:
            del stone[key]
    stone["finishScope"] = (
        "Uniform linear mean of accepted COL195 tone study;no macro texture;colour uncalibrated"
    )
    for node in list(stone.node_tree.nodes):
        if node.type in {"UVMAP", "TEX_IMAGE"}:
            stone.node_tree.nodes.remove(node)
    shader = next(n for n in stone.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*STONE_LINEAR_RGB, 1)
    stone.diffuse_color = (*STONE_LINEAR_RGB, 1)
    added = []
    from refine_kgs_surface237 import normal_record

    for name, material in TARGETS.items():
        source = bpy.data.objects[name]
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = "COL252_FINISH_" + name
        obj["originalObject"] = name
        obj["destinationCollection"] = "COL_EXTERIOR"
        obj["finishScope"] = (
            "Photo-guided pale stone or painted charcoal-green frames; original geometry,UV,normals,glass preserved; colour uncalibrated"
        )
        collection.objects.link(obj)
        assert len(obj.data.materials) == 1
        obj.data.materials[0] = bpy.data.materials[material]
        original = mesh_record(source)
        replacement = mesh_record(obj)
        for key, value in original.items():
            if key == "uv":
                assert all(replacement[key][k] == v for k, v in value.items())
            else:
                assert replacement[key] == value
        assert normal_record(obj.data) == normal_record(source.data)
        obj.hide_render = False
        obj.hide_set(False)
        source.hide_render = True
        source.hide_set(True)
        added.append(obj)
    update_scene()
    after = capture()
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in TARGETS:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    assert after["rooms"] == before["rooms"]
    assert after["campusRooms"] == before["campusRooms"]
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    record = {
        "version": 252,
        "building": "COL",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "component": str(component.relative_to(ROOT)),
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": "COL_EXTERIOR",
        "destinationCollection": "COL_EXTERIOR",
        "addedObjects": [o.name for o in added],
        "archivedObjects": list(TARGETS),
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in added},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in added
        },
        "uvAliases": [],
        "uniformStoneLinearRGB": list(STONE_LINEAR_RGB),
        "newMaterials": [STONE],
        "newMaterialGraphs": {STONE: after["materials"][STONE]},
        "materialSource": SOURCE_STONE,
        "exportMaterialContract": {
            "textureFree": True,
            "linearBaseColor": list(STONE_LINEAR_RGB),
            "sourceUVLayersAndActiveRenderUnchanged": True,
        },
        "status": "saved_awaiting_independent_reopen",
        "sources": json.loads(
            (ROOT / "data/collections/col-exterior234/sources.json").read_text()
        )["sources"][:3],
        "glassChanged": False,
        "roofGeometryChanged": False,
        "lightingChanged": False,
        "sourcePhotosUsedAsTextures": False,
        "limitations": [
            "Photo capture dates unknown; no calibrated colour or current measured condition.",
            "Uniform linear mean of COL195 stone tone study;no new texture or UV layer;original UV bytes/active settings unchanged. No as-built colour claim.",
            "Directional shadows remain physically directional; no global exposure/environment change.",
        ],
    }
    write("audit.json", record)
    assert sha(BASE) == SHA
    print("COL252_FINISH_SAVED", sha(component), len(added), flush=True)


if __name__ == "__main__":
    build_component()
