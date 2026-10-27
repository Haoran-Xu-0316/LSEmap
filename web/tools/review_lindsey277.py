"""Render the Lindsey candidate in the actual complete275campus context.

main('plan') is CPU-only. main('render') requires successful build and fresh
proof. It uses00_CAMPUS_COMPLETEwith its current public roofs, terrain, roads,
neighbours and trees; no exterior-only surrogate scene or native save.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/street277"
BASE = ROOT / "result/blender/LSE_campus_detailed_v275.blend"
SHA = "18a60235fd7c71c6c2864690c574f97b66a9d05577e0c584c626dee41829a4f9"
STAGE = "render"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def plan():
    import numpy as np

    facade = json.loads((OUT / "plan.json").read_text())
    points = np.array(facade["frontPolyline"])
    ex = points[-1] - points[0]
    ex /= np.linalg.norm(ex)
    normal = np.array([ex[1], -ex[0]])
    middle = (points[0] + points[-1]) / 2
    joint = points[1]
    views = []
    for name, centre, distance, camera_z, target_z, scale, resolution in [
        ("street-front", middle, 16, 9.5, 8.5, 25, [1800, 1500]),
        ("park-context", middle, 65, 27, 7.5, 48, [1800, 1200]),
        ("principal-bend-detail", joint, 14, 7.8, 7.8, 8, [1200, 1200]),
    ]:
        position = centre + normal * distance
        views.append(
            {
                "id": name,
                "position": [*map(float, position), camera_z],
                "target": [*map(float, centre), target_z],
                "orthoScale": scale,
                "resolution": resolution,
                "files": {p: f"{p}-{name}.png" for p in ("before", "after")},
            }
        )
    result = {
        "baselineSha256": SHA,
        "views": views,
        "scene": "00_CAMPUS_COMPLETE",
        "sameCameraLightingResolutionForBothPhases": True,
        "isolation": False,
        "retainExistingPublicRoofsTerrainRoadsNeighboursAndTrees": True,
        "newGeometryOtherThanCandidate": False,
        "roofObjectUnchanged": facade["roofObject"],
        "nativeHeightEstimateM": 17,
        "sourcePhotoCaptureDate": None,
        "rendered": False,
    }
    (OUT / "camera-plan.json").write_text(json.dumps(result, indent=2) + "\n")
    print("LINDSEY277_CAMERA_PLAN_READY", len(views), flush=True)
    return result


def render():
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_houghton262 import capture

    sheet = plan()
    audit = json.loads((OUT / "audit.json").read_text())
    proof = json.loads((OUT / "fresh-process-verification.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == audit["baselineSha256"] == SHA
    assert sha(component) == audit["componentSha256"] == proof["componentSha256"]
    assert (
        proof["freshBlenderProcess"] and proof["status"] == "passed-bounded-candidate"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[audit["destinationCollection"]].objects.link(obj)
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
    for material in list(bpy.data.materials):
        if (
            material.name not in before["materials"]
            and material.name not in audit["newMaterialGraphs"]
        ):
            assert material.users == 0
            bpy.data.materials.remove(material)
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    saved = {
        "camera": scene.camera,
        "engine": scene.render.engine,
        "taaRenderSamples": scene.eevee.taa_render_samples,
        "resolution": [
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.resolution_percentage,
        ],
        "format": scene.render.image_settings.file_format,
        "filepath": scene.render.filepath,
        "transform": scene.view_settings.view_transform,
        "exposure": scene.view_settings.exposure,
    }
    camera_data = bpy.data.cameras.new("LINDSEY277_private_camera")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    light_data = bpy.data.lights.new("LINDSEY277_private_sun", "SUN")
    light_data.energy, light_data.angle = 1.0, 0.15
    sun = bpy.data.objects.new(light_data.name, light_data)
    scene.collection.objects.link(sun)
    camera_data.type, camera_data.sensor_fit = "ORTHO", "HORIZONTAL"
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.image_settings.file_format = "PNG"
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0
    outputs = {}
    try:
        for view in sheet["views"]:
            camera.location = Vector(view["position"])
            target = Vector(view["target"])
            camera.rotation_euler = (
                (target - camera.location).to_track_quat("-Z", "Y").to_euler()
            )
            camera_data.ortho_scale = view["orthoScale"]
            sun.rotation_euler = (
                (target - camera.location + Vector((0, 0, -15)))
                .to_track_quat("-Z", "Y")
                .to_euler()
            )
            scene.render.resolution_x, scene.render.resolution_y = view["resolution"]
            for phase in ("before", "after"):
                for name in audit["archivedObjects"]:
                    bpy.data.objects[name].hide_render = phase == "after"
                for name in audit["addedObjects"]:
                    bpy.data.objects[name].hide_render = phase == "before"
                update_scene()
                scene.render.filepath = str(OUT / view["files"][phase])
                bpy.ops.render.render(write_still=True, scene=scene.name)
                outputs[view["files"][phase]] = sha(OUT / view["files"][phase])
    finally:
        for name in audit["archivedObjects"]:
            bpy.data.objects[name].hide_render = before["visibility"][name][0]
        for name in audit["addedObjects"]:
            bpy.data.objects[name].hide_render = False
        scene.camera = saved["camera"]
        scene.render.engine = saved["engine"]
        scene.eevee.taa_render_samples = saved["taaRenderSamples"]
        (
            scene.render.resolution_x,
            scene.render.resolution_y,
            scene.render.resolution_percentage,
        ) = saved["resolution"]
        scene.render.image_settings.file_format = saved["format"]
        scene.render.filepath = saved["filepath"]
        scene.view_settings.view_transform = saved["transform"]
        scene.view_settings.exposure = saved["exposure"]
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.lights.remove(light_data)
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        assert (
            after["objects"][name] == value
            and after["visibility"][name] == before["visibility"][name]
        ), name
    assert after["materials"] == before["materials"] | audit["newMaterialGraphs"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert set(after["objects"]) == set(before["objects"]) | set(audit["addedObjects"])
    assert sha(BASE) == SHA and sha(component) == audit["componentSha256"]
    sheet.update(
        rendered=True,
        outputs=outputs,
        componentSha256=audit["componentSha256"],
        noNativeSaved=True,
        allOriginalGeometryMaterialsAndVisibilityRestored=True,
        rendererScriptSha256=sha(Path(__file__)),
    )
    (OUT / "render-manifest.json").write_text(json.dumps(sheet, indent=2) + "\n")
    print("LINDSEY277_COMPLETE_CONTEXT_READY", len(outputs), flush=True)


def main(stage=STAGE):
    if stage == "plan":
        plan()
    elif stage == "render":
        render()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
