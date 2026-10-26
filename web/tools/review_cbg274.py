"""Fixed-camera before/after images of the frozen upperG4CBG component.

main('plan') is safe in MachineLearning before build. main('render') runs in
Blender after build and fresh proof. Six private PNGs only; no native save,
material changes, public assets, metadata, source photos or generic tools.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/cbg274"
STAGE = "render"
CAMERAS = (
    {
        "id": "whole-context",
        "positionLocal": [-55, -80, 62],
        "targetLocal": [-5, 4, 26],
        "scale": 100,
        "resolution": [1800, 1400],
        "purpose": "Whole visible CBG exterior; other facade rows, red/orange palette, wing and roof stay.",
    },
    {
        "id": "upper-G4-front",
        "positionLocal": [-17, -35, 48.1],
        "targetLocal": [-17, -0.1, 48.1],
        "scale": 14,
        "resolution": [1800, 1600],
        "purpose": "Highest two floors atG4=-18m; complete shade assemblies disappear only on the right ofG4. Both new clear patches are visible.",
    },
    {
        "id": "G4-glass-detail",
        "positionLocal": [-16.5, -14, 46.2],
        "targetLocal": [-16.5, -0.1, 46.2],
        "scale": 4.2,
        "resolution": [1000, 1250],
        "purpose": "Lower of the two repaired modules: existing2mglass, newly clear1mleaf area and removed high vent. Native jambs remain.",
    },
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plan():
    native = json.loads((OUT / "native-inspection.json").read_text())
    assert native["baselineSha256"] == SHA
    axes = native["frame"]

    def world(point):
        x, y, z = point
        return [
            axes["origin_G7_SW_world"][i]
            + x * axes["x_unit_SW"][i]
            + y * axes["y_unit_SE_rear"][i]
            for i in range(2)
        ] + [z]

    cameras = [
        dict(
            c,
            cameraWorld=world(c["positionLocal"]),
            targetWorld=world(c["targetLocal"]),
            files={phase: f"{phase}-{c['id']}.png" for phase in ("before", "after")},
        )
        for c in CAMERAS
    ]
    result = {
        "baselineSha256": SHA,
        "views": cameras,
        "sameCameraLightingResolutionForBothPhases": True,
        "sensorFit": "HORIZONTAL",
        "engine": "BLENDER_EEVEE",
        "samples": 64,
        "sourcePhoto": "data/collections/exteriors/images/cbg_rshp_020.jpg",
        "sourceAxesAnnotation": "result/blender/cbg-built-grid201/rshp020-axis-review.png",
        "rendered": False,
        "noGeometryIsolation": True,
        "limitation": "Viewpoints are native comparison cameras, not a calibrated reconstruction of the undated source-photo camera.",
    }
    (OUT / "camera-plan.json").write_text(json.dumps(result, indent=2) + "\n")
    print("CBG274_CAMERA_PLAN_READY", len(cameras), flush=True)
    return result


def render():
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_houghton262 import capture

    sheet = plan()
    audit = json.loads((OUT / "audit.json").read_text())
    fresh = json.loads((OUT / "fresh-process-verification.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == audit["baselineSha256"] == SHA
    assert sha(component) == audit["componentSha256"] == fresh["componentSha256"]
    assert (
        fresh["freshBlenderProcess"] and fresh["status"] == "passed-bounded-candidate"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections["CBG_EXTERIOR"].objects.link(obj)
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    objects = [
        o
        for o in bpy.data.collections["CBG_EXTERIOR"].all_objects
        if not o.hide_render and o.type in {"MESH", "FONT", "CURVE", "SURFACE"}
    ]
    for name in audit["addedObjects"]:
        if bpy.data.objects[name] not in objects:
            objects.append(bpy.data.objects[name])
    outputs = {}
    for view in sheet["views"]:
        scene = bpy.data.scenes.new("CBG274_private_" + view["id"])
        for obj in objects:
            scene.collection.objects.link(obj)
        world = bpy.data.worlds.new(scene.name + "_world")
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs["Color"].default_value = (
            0.8,
            0.85,
            0.95,
            1,
        )
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
        scene.world = world
        light_data = bpy.data.lights.new(scene.name + "_sun", "SUN")
        light_data.energy, light_data.angle = 1.4, 0.15
        sun = bpy.data.objects.new(light_data.name, light_data)
        scene.collection.objects.link(sun)
        frame = json.loads((OUT / "native-inspection.json").read_text())["frame"]
        front = Vector((*frame["y_unit_SE_rear"], 0))
        sun.rotation_euler = (
            (front + Vector((0, 0, -0.5))).to_track_quat("-Z", "Y").to_euler()
        )
        camera_data = bpy.data.cameras.new(scene.name + "_camera")
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera.location = Vector(view["cameraWorld"])
        camera.rotation_euler = (
            (Vector(view["targetWorld"]) - camera.location)
            .to_track_quat("-Z", "Y")
            .to_euler()
        )
        camera_data.type, camera_data.ortho_scale = "ORTHO", view["scale"]
        camera_data.sensor_fit = "HORIZONTAL"
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 64
        scene.render.resolution_x, scene.render.resolution_y = view["resolution"]
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.exposure = 0
        for phase in ("before", "after"):
            for name in audit["archivedObjects"]:
                bpy.data.objects[name].hide_render = phase == "after"
            for name in audit["addedObjects"]:
                bpy.data.objects[name].hide_render = phase == "before"
            for layer in scene.view_layers:
                layer.update()
            scene.render.filepath = str(OUT / view["files"][phase])
            bpy.ops.render.render(write_still=True, scene=scene.name)
            outputs[view["files"][phase]] = sha(OUT / view["files"][phase])
        bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.lights.remove(light_data)
        bpy.data.worlds.remove(world)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = before["visibility"][name][0]
    for name in audit["addedObjects"]:
        bpy.data.objects[name].hide_render = False
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        assert (
            after["objects"][name] == value
            and after["visibility"][name] == before["visibility"][name]
        ), name
    assert set(after["objects"]) == set(before["objects"]) | set(audit["addedObjects"])
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert sha(BASE) == SHA and sha(component) == audit["componentSha256"]
    sheet.update(
        rendered=True,
        outputs=outputs,
        componentSha256=audit["componentSha256"],
        sourceAndComponentUnchanged=True,
        noNativeSaved=True,
        rendererScriptSha256=sha(Path(__file__)),
    )
    (OUT / "render-manifest.json").write_text(json.dumps(sheet, indent=2) + "\n")
    print("CBG274_COMPARISON_READY", len(outputs), flush=True)


def main(stage=STAGE):
    if stage == "plan":
        plan()
    elif stage == "render":
        render()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
