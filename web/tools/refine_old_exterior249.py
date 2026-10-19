"""Restore the photographed two horizontal grille rails above OLD's doors.

The accepted 218 door fields, candidate leaves and materials remain intact.
Rail thickness/depth are photographic estimates; this does not certify door
operation, access clearances or the unresolved upper foyer construction.
Open this fixed-path script in Blender's Text Editor to build the component.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v248.blend"
BASE_SHA = "f43da0940bf835c6f769ae52341376721b3a934d8875160d7f8544e2067bcd50"
OUT = ROOT / "result/blender/old-exterior249"
NAME = "OLD249_two_horizontal_portal_grille_rails"
OWNER = "OLD_EXTERIOR"
MATERIAL = "OLD_NEXT_OLD_NEXT_OLD_V65_frame"
RIGHT = Vector((0.47449132800102234, 0.8802601099014282, 0))
NORMAL = Vector((0.8802601099014282, -0.47449132800102234, 0))
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_old_portal218 import components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "old249_capture", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = BASE_SHA
    return helper.capture_source()


def bounds(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    coords = [(p.dot(RIGHT), p.dot(NORMAL), p.z) for p in points]
    return [
        [min(p[i] for p in coords) for i in range(3)],
        [max(p[i] for p in coords) for i in range(3)],
    ]


def render(label, close=False):
    scene = bpy.data.scenes.new("OLD249_review")
    scene.collection.children.link(bpy.data.collections[OWNER])
    world = bpy.data.worlds.new(scene.name)
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (
        0.82,
        0.85,
        0.88,
        1,
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
    scene.world = world
    light = bpy.data.lights.new(scene.name, "AREA")
    light.energy, light.size = 650, 5
    lamp = bpy.data.objects.new(scene.name + "_light", light)
    scene.collection.objects.link(lamp)
    target = RIGHT * -82.4983 + NORMAL * 35.5 + Vector((0, 0, 3.4 if close else 4.25))
    lamp.location = target + NORMAL * 5 - RIGHT * 3 + Vector((0, 0, 5))
    lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
    data = bpy.data.cameras.new(scene.name)
    camera = bpy.data.objects.new(scene.name + "_camera", data)
    scene.collection.objects.link(camera)
    camera.location = target + NORMAL * 10
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    data.type, data.ortho_scale, data.clip_end = "ORTHO", 5.8 if close else 10.5, 500
    scene.camera = camera
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 400 if close else 1000
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(
        OUT / (label + ("-grille.png" if close else "-entrance.png"))
    )
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for obj in (camera, lamp):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(light)
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()


def verify_mesh(obj, plan):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.free()
    parts = components(obj, RIGHT, NORMAL)
    assert len(parts) == 2
    assert len(obj.data.polygons) == 12 and len(obj.data.vertices) == 16
    for part, z in zip(
        sorted(parts, key=lambda p: p["centre"][2]), plan["railCentreZ"]
    ):
        assert abs(part["centre"][2] - z) < 0.00003
        assert abs(part["dimensions"][2] - 0.018) < 0.00003
        assert part["low"][2] > plan["doorLeafTop"] + 0.08
        assert part["low"][1] > plan["paneDepth"] + 0.10
    return {
        "closedManifoldSolids": len(parts),
        "positiveVolume": volume,
        "vertices": len(obj.data.vertices),
        "triangles": 24,
        "minimumLeafHeadClearance": min(p["low"][2] for p in parts)
        - plan["doorLeafTop"],
        "minimumGlassClearance": min(p["low"][1] for p in parts) - plan["paneDepth"],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    component = OUT / "component.blend"
    assert not component.exists(), "A reviewed component must not be overwritten"
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    frame = bpy.data.objects["OLDPORTAL218_frame"]
    assert not frame.hide_render
    parts = components(frame, RIGHT, NORMAL)
    verticals = sorted(
        [p for p in parts if p["dimensions"][2] > 2.5], key=lambda p: p["centre"][0]
    )
    horizontals = sorted(
        [p for p in parts if p["dimensions"][0] > 5], key=lambda p: p["centre"][2]
    )
    assert len(verticals) == 5 and len(horizontals) == 3
    low_z = horizontals[1]["high"][2]
    high_z = horizontals[2]["low"][2]
    x_low, x_high = verticals[0]["high"][0], verticals[-1]["low"][0]
    glass_bounds = bounds(bpy.data.objects["OLDPORTAL218_glass"])
    plan = {
        "railCount": 2,
        "railCentreZ": [low_z + (high_z - low_z) * i / 3 for i in (1, 2)],
        "nativeTransomOpeningZ": [low_z, high_z],
        "nativeClearWidth": [x_low, x_high],
        "estimatedRailHeight": 0.018,
        "estimatedRailDepth": 0.045,
        "estimatedRailNormalRange": [35.350, 35.395],
        "doorLeafTop": horizontals[1]["low"][2],
        "paneDepth": glass_bounds[1][1],
    }
    write("shape-plan.json", plan)
    render("before", True)
    render("before")
    vertices, faces = [], []
    for z in plan["railCentreZ"]:
        start = len(vertices)
        vertices.extend(
            list(RIGHT * x + NORMAL * d + Vector((0, 0, h)))
            for x in (x_low, x_high)
            for d in (35.350, 35.395)
            for h in (z - 0.009, z + 0.009)
        )
        faces.extend(
            tuple(start + i for i in face)
            for face in [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ]
        )
    mesh = bpy.data.meshes.new(NAME)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(bpy.data.materials[MATERIAL])
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(NAME, mesh)
    bpy.data.collections[OWNER].objects.link(obj)
    obj["scope"] = (
        "Two photographed horizontal rails within the accepted portal transom only"
    )
    obj["presentationEstimated"] = True
    obj["source"] = "Webb Yates OLD project photograph 01; capture date unknown"
    obj["destinationCollection"] = OWNER
    update_scene()
    current = capture()
    assert all(current["objects"][n] == v for n, v in before["objects"].items())
    assert current["materials"] == before["materials"]
    checks = verify_mesh(obj, plan)
    expected = object_fingerprint(obj)
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_available, loaded):
        loaded.objects = [NAME]
    obj = loaded.objects[0]
    obj.data.materials[0] = bpy.data.materials[MATERIAL]
    bpy.data.collections[OWNER].objects.link(obj)
    update_scene()
    assert object_fingerprint(obj) == expected
    after = capture()
    assert all(after["objects"][n] == v for n, v in before["objects"].items())
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert set(after["objects"]) == set(before["objects"]) | {NAME}
    assert verify_mesh(obj, plan) == checks
    render("after", True)
    render("after")
    assert sha(BASE) == BASE_SHA
    refs = []
    for path in [
        "data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg",
        "data/collections/old-exterior-2026/user-references/houghton-entrance-latest.png",
    ]:
        refs.append(
            {
                "path": path,
                "sha256": sha(ROOT / path),
                "captureDate": "unknown",
                "use": "Private visual evidence; not a public texture",
            }
        )
    verification = {
        "savedComponentReopened": True,
        "originalObjectsUnchanged": len(before["objects"]),
        "originalMaterialGraphsUnchanged": len(before["materials"]),
        "protectedRooms": len(before["rooms"]),
        "protectedRoomObjects": len(
            {n for members in before["rooms"].values() for n in members}
        ),
        "originalGeometryUVTransformsModifiersPropertiesOwnersVisibilityUnchanged": True,
        "closedDoorPanesAndLeafHardwareUnchanged": True,
        "baselineBytesUnchanged": True,
        **checks,
    }
    write("verification.json", verification)
    write(
        "audit.json",
        {
            "version": 249,
            "building": "OLD",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": BASE_SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": OWNER,
            "targetCollection": OWNER,
            "addedObjects": [NAME],
            "archivedObjects": [],
            "changedObjects": [],
            "addedFingerprints": {NAME: expected},
            "replacementMaterialBindings": {NAME: [MATERIAL]},
            "verification": verification,
            "references": refs,
            "shapePlan": "shape-plan.json",
            "previews": [
                "before-grille.png",
                "after-grille.png",
                "before-entrance.png",
                "after-entrance.png",
            ],
            "limitations": [
                "Two horizontal grille rails are photographically visible; their 18mm height,45mm depth and exact setback remain estimates.",
                "No new vertical bars, side lights, active/fixed leaf assignments or complete door product reconstruction are inferred.",
                "The upper blue shapes are distant retained rear windows viewed through an incomplete upper foyer. No unsupported opaque backing or deletion conceals them.",
                "All original portal panes, material optics, artwork, stone arch, 239 Clare reliefs and interiors remain unchanged.",
            ],
        },
    )
    print("OLD249_COMPONENT_REOPENED", sha(component), verification, flush=True)


if __name__ == "__main__":
    main()
