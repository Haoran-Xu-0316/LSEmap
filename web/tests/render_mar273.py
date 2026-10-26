"""Fixed-camera MAR269/MAR273 comparison;privatePNGoutputs,no native save.

Second-storey view intentionally hides the upper plate/core to expose the new
source-filled enclosure. Two-floor view retains both actual floor plates and
omits251walls above17.5mto reveal the coordinated apertures. This is a component
review, not a claim to depict unmodelled higher-level interior architecture.
"""

import importlib.util
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
import refine_mar273 as builder
from integrate_exterior_round194 import (
    update_scene,
)

spec = importlib.util.spec_from_file_location(
    "mar273_render_verifier", ROOT / "web/tests/verify_mar273.py"
)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
VIEWS = [
    {
        "id": "second-core",
        "target": [10.7, 54.7, 14.1],
        "offset": [9, -14, 12],
        "scale": 18,
        "includeThirdDeck": False,
    },
    {
        "id": "two-floor",
        "target": [10.7, 54.7, 14.9],
        "offset": [11, -16, 16],
        "scale": 17,
        "includeThirdDeck": True,
    },
]


def main():
    audit = builder.read("result/blender/mar273/audit.json")
    plan = builder.read(audit["sourcePlan"])
    assert (
        builder.sha(builder.BASE) == builder.SHA
        and builder.sha(ROOT / audit["componentPath"]) == audit["componentSha256"]
    )
    outputs = {}
    for phase in ["before", "after"]:
        bpy.ops.wm.open_mainfile(filepath=str(builder.BASE))
        update_scene()
        if phase == "after":
            verifier.apply_component(audit)
        scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.context.window.scene = scene
        camera_data = bpy.data.cameras.new("MAR273_private_review_camera")
        camera = bpy.data.objects.new("MAR273_private_review_camera", camera_data)
        scene.collection.objects.link(camera)
        scene.camera = camera
        camera_data.type = "ORTHO"
        scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 32
        scene.render.resolution_x = 1300
        scene.render.resolution_y = 1100
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.film_transparent = False
        for view in VIEWS:
            visible = set()
            for row in plan["objects"]:
                if row.get("componentRole") == "third-core-extension":
                    continue
                source = row["sourceObject"]
                name = source if phase == "before" else row["replacement"]
                if name is None:
                    continue
                if source == "MAR251_third_south_lift_core_walls":
                    continue
                if (
                    source == "MAR258_third_south_deck_solid"
                    and not view["includeThirdDeck"]
                ):
                    continue
                visible.add(name)
            for obj in scene.objects:
                if obj.type == "LIGHT":
                    continue
                if obj.type == "MESH":
                    obj.hide_render = obj.name not in visible
            target = Vector(view["target"])
            camera.location = target + Vector(view["offset"])
            camera.rotation_euler = (
                (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            )
            camera_data.ortho_scale = view["scale"]
            update_scene()
            name = view["id"] + "-" + phase + ".png"
            scene.render.filepath = str(builder.OUT / name)
            bpy.ops.render.render(write_still=True)
            outputs[view["id"] + "-" + phase] = "mar273/" + name
    builder.write(
        builder.OUT / "review-views.json",
        {
            "baselineSha256": builder.SHA,
            "componentSha256": audit["componentSha256"],
            "fixedCameras": VIEWS,
            "views": outputs,
            "sourceUnchanged": builder.sha(builder.BASE) == builder.SHA,
            "nativeSaved": False,
            "humanAcceptance": False,
            "visibilityPolicy": "Expose only the bounded floor/core components.Upper251walls are hidden in both phases;Second-core additionally hides theThirddeck.",
        },
    )
    print("MAR273_PRIVATE_VIEWS_READY", flush=True)


if __name__ == "__main__":
    main()
