"""Render fixed-camera OLD270before/after comparisons without rebuilding it.

main('plan') writes the private camera sheet in MachineLearning. main('render')
runs in Blender, appends the frozen component, and writes six private PNGs.
No source/public model, source photograph, material graph or metadata is saved.
"""

import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old273"
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
BASE_SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
COMPONENT_SHA = "b58245f31bb5fc97c39807968f4fb71b549a553a8e36e9b78aa65668e9211d4b"
FRESH_SHA = "9b83b32d69af8e3a0e5a79116a7a5d6098211f96c4ed01fe1797d53c9652a1d2"
SOURCE = "OLD_D5_clare87_casements"
NEW = "OLD270_Clare_lower_six_column_eight_row_casements"
ISOLATED = ("OLD201_CLARE_joinery", "OLD201_CLARE_glazing", SOURCE, NEW)
STAGE = "render"
CAMERAS = (
    {
        "id": "context-front",
        "targetLocal": [0, -0.10, 5.35],
        "cameraLocal": [0, 24, 5.35],
        "orthoScale": 19.3,
        "resolution": [1800, 1200],
        "isolation": False,
        "purpose": "All visible OLD exterior objects. Check door upper light, four ordinary upper windows and surrounding stone; foreground sculpture remains.",
    },
    {
        "id": "lower-bank-isolated",
        "targetLocal": [1.7110738454341495, -0.10, 2.95],
        "cameraLocal": [1.7110738454341495, 20, 2.95],
        "orthoScale": 14.3,
        "resolution": [2560, 1280],
        "isolation": True,
        "purpose": "Four ordinary lower windows only:6columns8rows per window. Original201frame and glazing remain; foreground sculpture, stone and vegetation are excluded for counting.",
    },
    {
        "id": "first-window-isolated",
        "targetLocal": [-3.4221476908683, -0.10, 2.95],
        "cameraLocal": [-3.4221476908683, 12, 2.95],
        "orthoScale": 3.25,
        "resolution": [960, 1500],
        "isolation": True,
        "purpose": "Same first ordinary window as the source annotation. Count five internal vertical boundaries and seven horizontal boundaries; heavy meeting rails count once.",
    },
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit():
    folder = ROOT / "result/blender/old270"
    value = json.loads((folder / "audit.json").read_text())
    fresh = json.loads((folder / "fresh-process-verification.json").read_text())
    assert sha(folder / "fresh-process-verification.json") == FRESH_SHA
    assert value["baselineSha256"] == fresh["baselineSha256"] == BASE_SHA
    assert (
        value["componentSha256"]
        == fresh["componentSha256"]
        == sha(ROOT / value["componentPath"])
        == COMPONENT_SHA
    )
    assert (
        fresh["freshBlenderProcess"] and fresh["status"] == "passed-bounded-candidate"
    )
    return value


def camera_plan():
    native = json.loads(
        (ROOT / "result/blender/old270/native-inspection.json").read_text()
    )
    axes = native["frame"]

    def world(local):
        x, depth, z = local
        return [
            axes["origin"][i]
            + x * axes["right"][i]
            + depth * axes["outward"][i]
            + (z if i == 2 else 0)
            for i in range(3)
        ]

    views = []
    for camera in CAMERAS:
        views.append(
            dict(
                camera,
                cameraWorld=world(camera["cameraLocal"]),
                targetWorld=world(camera["targetLocal"]),
                phaseFiles={
                    phase: f"{phase}-{camera['id']}.png"
                    for phase in ("before", "after")
                },
            )
        )
    return {
        "baselineSha256": BASE_SHA,
        "componentSha256": COMPONENT_SHA,
        "views": views,
        "sameCameraLightingResolutionForBothPhases": True,
        "sensorFit": "HORIZONTAL",
        "isolatedObjects": list(ISOLATED),
        "sourcePhotoCaptureDates": "Unknown",
        "photographicComparison": "Counts and joinery hierarchy are source-observed; metric proportions remain estimates. Reflections are excluded from pane counts.",
        "renderSettings": {
            "engine": "BLENDER_EEVEE",
            "samples": 64,
            "viewTransform": "AgX",
            "exposure": 0,
            "imageFormat": "PNG",
        },
        "rendered": False,
    }


def html_sheet(rendered=False):
    rows = []
    labels = {
        "context-front": "一、完整立面",
        "lower-bank-isolated": "二、四窗隔離檢查",
        "first-window-isolated": "三、同窗特寫",
    }
    for camera in CAMERAS:
        key = camera["id"]
        note = (
            "已移除前景雕塑、石材和植栽，只保留原窗框、玻璃與對照梃件。"
            if camera["isolation"]
            else "保留可見OLD外觀與前景遮擋。"
        )
        rows.append(
            f'<section id="{key}"><h2>{labels[key]}</h2><p>{note}</p><div class="pair"><figure><figcaption>269原生：4列5排</figcaption><img src="before-{key}.png"></figure><figure><figcaption>270組件：6列8排</figcaption><img src="after-{key}.png"></figure></div></section>'
        )
    status = (
        "已生成原生渲染，待逐圖判讀。"
        if rendered
        else "相機方案已準備，實際圖片待root串行渲染。"
    )
    page = f"""<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>OLD窗組對照</title><style>
body{{margin:0;background:#f5f4ef;color:#1b2730;font:16px/1.6 system-ui,sans-serif}}nav{{position:fixed;inset:0 auto 0 0;width:185px;padding:28px 18px;background:#e9e8e2}}nav a{{display:block;color:#234658;margin:12px 0;text-decoration:none}}main{{margin-left:225px;padding:28px;max-width:1800px}}h1{{margin:0 0 12px;font-size:28px}}h2{{font-size:22px;margin-top:32px}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}figure{{margin:0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-weight:600;margin-bottom:8px}}p{{max-width:80ch}}@media(max-width:800px){{nav{{position:static;width:auto}}main{{margin:0}}.pair{{grid-template-columns:1fr}}}}</style><nav><a href="#source">來源</a>{"".join(f'<a href="#{c["id"]}">{labels[c["id"]]}</a>' for c in CAMERAS)}</nav><main><h1>OLD窗組對照</h1><p>{status}</p><p>只修四個普通下窗。門上窗、四個上層普通窗與原玻璃保持；厚會合梃只計一道分界。照片拍攝日期不詳，尺寸沿用估計。</p><section id="source"><h2>來源</h2><p><a href="../../../data/collections/old-clare-reference/front.png">正面原圖</a>、<a href="../../../data/collections/public-realm-2026/user-references/reference-08.png">斜向原圖</a></p><img style="max-width:1100px" src="../old270/clare-window-source-annotation.png" alt="同窗分格與遮擋標註"></section>{"".join(rows)}</main></html>"""
    (OUT / "visual-review.html").write_text(page)


def plan():
    audit()
    OUT.mkdir(parents=True, exist_ok=True)
    value = camera_plan()
    (OUT / "camera-plan.json").write_text(json.dumps(value, indent=2) + "\n")
    html_sheet()
    print("OLD273_CAMERA_PLAN_READY", len(value["views"]), flush=True)


def render():
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_houghton262 import capture

    plan()
    record = audit()
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    with bpy.data.libraries.load(str(ROOT / record["componentPath"]), link=False) as (
        _,
        destination,
    ):
        destination.objects = list(record["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections["OLD_EXTERIOR"].objects.link(obj)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    assert object_fingerprint(bpy.data.objects[NEW]) == record["addedFingerprints"][NEW]
    contextual = [
        o
        for o in bpy.data.collections["OLD_EXTERIOR"].all_objects
        if not o.hide_render and o.type in {"MESH", "FONT", "CURVE", "SURFACE"}
    ]
    if bpy.data.objects[NEW] not in contextual:
        contextual.append(bpy.data.objects[NEW])
    camera_sheet = camera_plan()
    outputs = {}
    for view in camera_sheet["views"]:
        scene = bpy.data.scenes.new("OLD273_private_" + view["id"])
        linked = (
            [bpy.data.objects[n] for n in ISOLATED] if view["isolation"] else contextual
        )
        for obj in linked:
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
        normal = Vector(camera_sheet["views"][0]["cameraWorld"]) - Vector(
            camera_sheet["views"][0]["targetWorld"]
        )
        sun.rotation_euler = (
            (-normal + Vector((0, 0, -8))).to_track_quat("-Z", "Y").to_euler()
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
        camera_data.type, camera_data.ortho_scale = "ORTHO", view["orthoScale"]
        camera_data.sensor_fit = "HORIZONTAL"
        scene.render.engine = "BLENDER_EEVEE"
        scene.eevee.taa_render_samples = 64
        scene.render.resolution_x, scene.render.resolution_y = view["resolution"]
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.exposure = 0
        for layer in scene.view_layers:
            layer.update()
        native = json.loads(
            (ROOT / "result/blender/old270/native-inspection.json").read_text()
        )
        windows = native["legacyWindows"]
        if view["id"] == "lower-bank-isolated":
            windows = [w for w in windows if w["family"] == "lower"]
        elif view["id"] == "first-window-isolated":
            windows = [w for w in windows if w["family"] == "lower"][:1]
        axes = [Vector(native["frame"][n]) for n in ("origin", "right", "outward")]
        corners = [
            camera.matrix_world.inverted()
            @ (
                axes[0]
                + axes[1] * (w["x"] + side * w["w"] / 2)
                - axes[2] * 0.10
                + Vector((0, 0, w["z"] + up * w["h"] / 2))
            )
            for w in windows
            for side in (-1, 1)
            for up in (-1, 1)
        ]
        projection = camera_data.view_frame(scene=scene)
        frame_min = [min(p[i] for p in projection) for i in range(2)]
        frame_max = [max(p[i] for p in projection) for i in range(2)]
        assert all(
            frame_min[i] <= p[i] <= frame_max[i] for p in corners for i in range(2)
        ), ("cropped-window", view["id"])
        view["actualCameraProjection"] = {
            "checkedWindowCorners": len(corners),
            "minimum": frame_min,
            "maximum": frame_max,
            "allTargetWindowsFullyFramed": True,
        }
        for phase in ("before", "after"):
            bpy.data.objects[SOURCE].hide_render = phase == "after"
            bpy.data.objects[NEW].hide_render = phase == "before"
            for layer in scene.view_layers:
                layer.update()
            path = OUT / view["phaseFiles"][phase]
            scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True, scene=scene.name)
            outputs[path.name] = sha(path)
        bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
        bpy.data.scenes.remove(scene)
        bpy.data.objects.remove(camera, do_unlink=True)
        bpy.data.objects.remove(sun, do_unlink=True)
        bpy.data.cameras.remove(camera_data)
        bpy.data.lights.remove(light_data)
        bpy.data.worlds.remove(world)
    bpy.data.objects[SOURCE].hide_render = before["visibility"][SOURCE][0]
    bpy.data.objects[NEW].hide_render = False
    update_scene()
    after = capture()
    for name, state in before["objects"].items():
        assert (
            after["objects"][name] == state
            and after["visibility"][name] == before["visibility"][name]
        ), name
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert set(after["objects"]) == set(before["objects"]) | {NEW}
    assert (
        sha(BASE) == BASE_SHA and sha(ROOT / record["componentPath"]) == COMPONENT_SHA
    )
    camera_sheet["rendered"] = True
    camera_sheet["outputs"] = outputs
    camera_sheet["sourceAndComponentUnchanged"] = True
    camera_sheet["noNativeSaved"] = True
    camera_sheet["rendererScriptSha256"] = sha(Path(__file__))
    (OUT / "render-manifest.json").write_text(json.dumps(camera_sheet, indent=2) + "\n")
    html_sheet(rendered=True)
    print("OLD273_PRIVATE_COMPARISON_READY", len(outputs), flush=True)


def main(stage=STAGE):
    if stage == "plan":
        plan()
    elif stage == "render":
        render()
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    main()
