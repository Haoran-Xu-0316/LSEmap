"""Same-camera before/after Ground/MAR283 and complete-campus views.

Private review images only. Ground cutaway hides the immediate ceiling and
geometry above7.3m; apertures view isolates the two actual ceiling assemblies.
Whole-campus view preserves every ordinary visible mesh and display material.
"""

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
import refine_mar283 as builder
from integrate_exterior_round194 import update_scene

spec = importlib.util.spec_from_file_location(
    "mar283_render_verifier", ROOT / "web/tests/verify_mar283.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
VIEWS = [
    {
        "id": "ground-core",
        "target": [10.7, 54.7, 2.4],
        "offset": [12, -18, 15],
        "scale": 18.5,
        "kind": "cutaway",
    },
    {
        "id": "ground-ceiling",
        "target": [10.7, 54.7, 6.8],
        "offset": [9, -14, 18],
        "scale": 18.5,
        "kind": "ceiling",
    },
    {
        "id": "whole-campus",
        "target": [-8, 15, 12],
        "offset": [130, -165, 135],
        "scale": 280,
        "kind": "full",
    },
]


def main():
    audit = builder.read("result/blender/mar283/audit.json")
    plan = builder.read(audit["sourcePlan"])
    assert builder.sha(builder.BASE) == builder.SHA
    outputs = {}
    for phase in ["before", "after"]:
        bpy.ops.wm.open_mainfile(filepath=str(builder.BASE))
        update_scene()
        if phase == "after":
            verifier.apply_component(audit)
        scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.context.window.scene = scene
        baseline_visibility = {obj.name: obj.hide_render for obj in scene.objects}
        camera_data = bpy.data.cameras.new("MAR283_private_review_camera")
        camera = bpy.data.objects.new(camera_data.name, camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera_data.type = "ORTHO"
        scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 16
        scene.render.resolution_x = 1100
        scene.render.resolution_y = 900
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        for view in VIEWS:
            for name, hidden in baseline_visibility.items():
                bpy.data.objects[name].hide_render = hidden
            camera_data.ortho_scale = view["scale"]
            target = Vector(view["target"])
            camera.location = target + Vector(view["offset"])
            camera.rotation_euler = (
                (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            )
            if view["kind"] == "cutaway":
                for obj in scene.objects:
                    if obj.type != "MESH" or obj.hide_render:
                        continue
                    z = [(obj.matrix_world @ Vector(p)).z for p in obj.bound_box]
                    if (
                        not obj.name.startswith("MAR")
                        or min(z) > 7.3
                        or obj.name
                        in {
                            r[key]
                            for r in plan["objects"]
                            if r["componentRole"] == "ground-ceiling-aperture"
                            for key in ["sourceObject", "replacement"]
                        }
                    ):
                        obj.hide_render = True
            elif view["kind"] == "ceiling":
                visible = {
                    r["sourceObject"] if phase == "before" else r["replacement"]
                    for r in plan["objects"]
                    if r["componentRole"] == "ground-ceiling-aperture"
                }
                for obj in scene.objects:
                    if obj.type == "MESH":
                        obj.hide_render = obj.name not in visible
            update_scene()
            filename = view["id"] + "-" + phase + ".png"
            scene.render.filepath = str(builder.OUT / filename)
            bpy.ops.render.render(write_still=True)
            outputs[view["id"] + "-" + phase] = "mar283/" + filename
    builder.write(
        builder.OUT / "review-views.json",
        {
            "baselineSha256": builder.SHA,
            "componentSha256": audit["componentSha256"],
            "fixedCameras": VIEWS,
            "views": outputs,
            "sourceUnchanged": builder.sha(builder.BASE) == builder.SHA,
            "nativeSaved": False,
            "visibilityPolicy": "Ground cutaway omits immediate ceiling and meshes above7.3m;ceiling view isolates actual two cover assemblies;whole-campus retains normal scene visibility.",
            "humanAcceptance": False,
        },
    )
    print("MAR283_PRIVATE_VIEWS_READY", flush=True)


if __name__ == "__main__":
    main()
