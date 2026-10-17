"""Independently reopen the CON source component and test its saved surfaces.

This is a private component check, not approval of native campus registration.
No command-line inputs; use Blender's Text Editor or the fixed authoring workflow.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-frontage243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint


def tree(obj):
    return BVHTree.FromPolygons(
        [v.co for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
    )


def main():
    plan = json.loads((OUT / "geometry-plan.json").read_text())
    record = json.loads((OUT / "component-record.json").read_text())
    path = ROOT / record["component"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["componentSha256"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path), link=False) as (_source, destination):
        destination.collections = ["CON243_HOUGHTON_SOURCE_SCALE_COMPONENT"]
    collection = destination.collections[0]
    scene = bpy.context.scene
    scene.collection.children.link(collection)
    assert set(record["ownedObjects"]) == {o.name for o in collection.all_objects}
    for name, expected in record["objectFingerprints"].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected
    wall = bpy.data.objects["CON243_Houghton_perforated_wall"]
    panes = bpy.data.objects["CON243_Houghton_glazing"]
    backing = bpy.data.objects["CON243_Houghton_closed_backing"]
    wall_tree, pane_tree, back_tree = tree(wall), tree(panes), tree(backing)
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert volume > 0
    assert abs(volume - plan["wallAreaM2"] * 0.32) < 0.002
    wall_front_area = sum(p.area for p in wall.data.polygons if p.normal.y < -0.999)
    assert abs(wall_front_area - plan["wallAreaM2"]) < 0.002
    origin = plan["sourceOrigin"]
    scale = plan["metresPerPoint"]
    checked = 0
    for opening in plan["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        # Test several clear sites inside the saved hole, not only its centre.
        for sx, sy in [(0.2, 0.2), (0.5, 0.5), (0.8, 0.8)]:
            x = x0 + (x1 - x0) * sx
            y = y0 + (y1 - y0) * sy
            point = Vector(((x - origin[0]) * scale, -1, (origin[1] - y) * scale))
            direction = Vector((0, 1, 0))
            assert wall_tree.ray_cast(point, direction, 2)[0] is None, opening["id"]
            hit = pane_tree.ray_cast(point, direction, 2)[0]
            assert hit is not None and abs(hit.y - 0.14) < 1e-5, opening["id"]
            hit = back_tree.ray_cast(point, direction, 2)[0]
            assert hit is not None and abs(hit.y - 0.60) < 1e-5, opening["id"]
            checked += 1
    assert len(plan["openings"]) == 89
    # Negative control: a source pier must remain opaque rather than a facade decal.
    pier = Vector(((277 - origin[0]) * scale, -1, (origin[1] - 240) * scale))
    assert wall_tree.ray_cast(pier, Vector((0, 1, 0)), 2)[0] is not None
    scene.world = bpy.data.worlds.new("CON243_REVIEW_WORLD")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (
        0.68,
        0.74,
        0.8,
        1,
    )
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    sun = bpy.data.objects.new(
        "CON243_REVIEW_SUN", bpy.data.lights.new("CON243_REVIEW_SUN", "SUN")
    )
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = 0.2
    sun.rotation_euler = (0.5, -0.4, -0.3)
    camera = bpy.data.objects.new(
        "CON243_REVIEW_CAMERA", bpy.data.cameras.new("CON243_REVIEW_CAMERA")
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.clip_end = 500
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1120
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    centre = Vector((plan["sourceWidthM"] / 2, 0, 16.7))
    for name, position, size in [
        ("frontage", (plan["sourceWidthM"] / 2, -62, 16.7), 38),
        ("oblique", (43, -55, 25), 40),
    ]:
        camera.location = position
        camera.rotation_euler = (
            (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        camera.data.ortho_scale = size
        scene.render.filepath = str(OUT / (name + "-review.png"))
        bpy.ops.render.render(write_still=True)
    proof = {
        "componentReopened": True,
        "componentSha256": record["componentSha256"],
        "objectsVerified": len(record["ownedObjects"]),
        "sourceOpeningModules": 89,
        "clearHoleRayChecks": checked,
        "everyTestedOpeningHasInsetGlassAndOpaqueBacking": True,
        "wallManifold": True,
        "wallVolumeM3": volume,
        "wallFrontAreaM2": wall_front_area,
        "sourceWallAreaM2": plan["wallAreaM2"],
        "wallAreaToleranceM2": 0.002,
        "nativeCampusUnchanged": True,
        "nativeIntegrationAccepted": False,
        "pending": [
            "Register frontage width and street slope without distorting the source or relocating61A.",
            "Resolve roof depth and rear transitions before full-envelope replacement.",
        ],
        "limitations": plan["limitations"],
    }
    (OUT / "saved-mesh-verification.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    print("CON243_SAVED_MESH_VERIFIED", checked, round(volume, 4), flush=True)


if __name__ == "__main__":
    main()
