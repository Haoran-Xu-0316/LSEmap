"""Reopen and verify the private COL relief without loading campus geometry.

Checks saved wall openings, infill types and backing before rendering identical
source-scale front and oblique review views. Native registration is not approved.
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
OUT = ROOT / "result/blender/col-component244"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint


def tree(obj):
    return BVHTree.FromPolygons(
        [vertex.co for vertex in obj.data.vertices],
        [tuple(polygon.vertices) for polygon in obj.data.polygons],
    )


def main():
    plan_path = OUT / "geometry-plan.json"
    plan = json.loads(plan_path.read_text())
    record = json.loads((OUT / "component-record.json").read_text())
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == record["planSha256"]
    assert (
        hashlib.sha256((ROOT / plan["source"]).read_bytes()).hexdigest()
        == plan["sourceSha256"]
    )
    path = ROOT / record["component"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["componentSha256"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(path), link=False) as (_source, destination):
        destination.collections = ["COL244_HOUGHTON_SOURCE_SCALE_COMPONENT"]
    collection = destination.collections[0]
    scene = bpy.context.scene
    scene.collection.children.link(collection)
    bpy.context.view_layer.update()
    assert set(record["ownedObjects"]) == {obj.name for obj in collection.all_objects}
    for name, expected in record["objectFingerprints"].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected
    wall = bpy.data.objects["COL244_Houghton_perforated_wall"]
    panes = bpy.data.objects["COL244_Houghton_glazing"]
    opaque = bpy.data.objects["COL244_Houghton_opaque_ground_infill"]
    backing = bpy.data.objects["COL244_Houghton_closed_backing"]
    wall_tree, glass_tree, opaque_tree, back_tree = map(
        tree, (wall, panes, opaque, backing)
    )
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert volume > 0 and abs(volume - plan["wallAreaM2"] * 0.32) < 0.002
    wall_front_area = sum(
        face.area for face in wall.data.polygons if face.normal.y < -0.999
    )
    assert abs(wall_front_area - plan["wallAreaM2"]) < 0.002
    assert len(panes.data.polygons) == 64
    assert len(opaque.data.polygons) == 8
    assert len(backing.data.polygons) == 72
    materials = {}
    for obj in collection.all_objects:
        assert len(obj.data.materials) == 1
        material = obj.data.materials[0]
        shader = material.node_tree.nodes.get("Principled BSDF")
        assert shader is not None and material["evidenceStatus"].startswith("estimated")
        transmission = shader.inputs["Transmission Weight"].default_value
        if obj == panes:
            assert 0.57 < transmission < 0.59
        else:
            assert transmission == 0
        assert shader.inputs["Alpha"].default_value == 1
        materials[obj.name] = {
            "name": material.name,
            "transmissionWeight": transmission,
            "baseColour": list(shader.inputs["Base Color"].default_value),
        }
    origin, scale = plan["sourceOrigin"], plan["metresPerPoint"]
    direction = Vector((0, 1, 0))
    checked = 0
    for opening in plan["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        selected, other = (
            (glass_tree, opaque_tree)
            if opening["role"] == "regular-window"
            else (opaque_tree, glass_tree)
        )
        for sx, sy in [(0.2, 0.2), (0.5, 0.5), (0.8, 0.8)]:
            x, y = x0 + (x1 - x0) * sx, y0 + (y1 - y0) * sy
            point = Vector(((x - origin[0]) * scale, -1, (origin[1] - y) * scale))
            assert wall_tree.ray_cast(point, direction, 2)[0] is None, opening["id"]
            hit = selected.ray_cast(point, direction, 2)[0]
            assert hit is not None and abs(hit.y - 0.14) < 1e-5, opening["id"]
            assert other.ray_cast(point, direction, 2)[0] is None, opening["id"]
            hit = back_tree.ray_cast(point, direction, 2)[0]
            assert hit is not None and abs(hit.y - 0.60) < 1e-5, opening["id"]
            checked += 1
    # Independent review coordinates, rather than the builder edge list, prove
    # the saved frame sides continue across the opaque source spandrels.
    classification = json.loads((ROOT / plan["sourceClassification"]).read_text())
    reviewed_rows = {row["id"]: row["moduleBoundsPt"] for row in classification["rows"]}
    joinery_tree = tree(bpy.data.objects["COL244_Houghton_joinery"])
    continuous_edge_checks = 0
    for upper_id, lower_id in [("R3", "R4"), ("R4", "R5"), ("R5", "R6"), ("R8", "R9")]:
        for upper, lower in zip(reviewed_rows[upper_id], reviewed_rows[lower_id]):
            for side in (0, 2):
                x, y = (upper[side] + lower[side]) / 2, (upper[3] + lower[1]) / 2
                point = Vector(((x - origin[0]) * scale, -1, (origin[1] - y) * scale))
                hit = joinery_tree.ray_cast(point, direction, 2)[0]
                assert hit is not None and abs(hit.y + 0.018) < 1e-5
                assert wall_tree.ray_cast(point, direction, 2)[0] is not None
                continuous_edge_checks += 1
    # A source pier is physically opaque, not a flat facade image.
    point = Vector(((321 - origin[0]) * scale, -1, (origin[1] - 240) * scale))
    assert wall_tree.ray_cast(point, direction, 2)[0] is not None
    # The saved elevation follows source X north-to-south. Neither campus ENU
    # placement nor a world AOD offset is introduced by this component.
    coordinates = [vertex.co for vertex in wall.data.vertices]
    assert min(v.x for v in coordinates) > -1e-5
    assert abs(max(v.x for v in coordinates) - plan["sourceWidthM"]) < 1e-5
    north = [v for v in coordinates if abs(v.x) < 1e-5]
    south = [v for v in coordinates if abs(v.x - plan["sourceWidthM"]) < 1e-5]
    north_z, south_z = min(v.z for v in north), min(v.z for v in south)
    assert abs(north_z - plan["groundRiseNorthM"]) < 1e-5 and abs(south_z) < 1e-5
    assert not plan["nativeRegistrationAccepted"] and not record["integrated"]
    scene.world = bpy.data.worlds.new("COL244_REVIEW_WORLD")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.68, 0.74, 0.8, 1)
    background.inputs[1].default_value = 0.7
    sun = bpy.data.objects.new(
        "COL244_REVIEW_SUN", bpy.data.lights.new("COL244_REVIEW_SUN", "SUN")
    )
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = 0.2
    sun.rotation_euler = (0.5, -0.4, -0.3)
    camera = bpy.data.objects.new(
        "COL244_REVIEW_CAMERA", bpy.data.cameras.new("COL244_REVIEW_CAMERA")
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
    centre = Vector((plan["sourceWidthM"] / 2, 0, 17.5))
    for name, position, size in [
        ("frontage", (plan["sourceWidthM"] / 2, -62, 17.5), 39),
        ("oblique", (40, -55, 25), 40),
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
        "sourceOpeningModules": 72,
        "continuousRibbonEdgeRayChecks": continuous_edge_checks,
        "regularGlassWindowFaces": 64,
        "opaqueGroundModuleFaces": 8,
        "opaqueBackingFaces": 72,
        "clearHoleRayChecks": checked,
        "everyTestedOpeningHasCorrectInfillAndOpaqueBacking": True,
        "wallManifold": True,
        "wallVolumeM3": volume,
        "wallFrontAreaM2": wall_front_area,
        "sourceWallAreaM2": plan["wallAreaM2"],
        "wallAreaToleranceM2": 0.002,
        "materialBindings": materials,
        "sourceDirection": "local X increases north-to-south, source LEFT=NORTH",
        "savedNorthGroundZ": north_z,
        "savedSouthGroundZ": south_z,
        "campusLoadedOrModified": False,
        "nativeIntegrationAccepted": False,
        "limitations": plan["limitations"],
    }
    (OUT / "saved-mesh-verification.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    print("COL244_SAVED_MESH_VERIFIED", checked, round(volume, 4), flush=True)


if __name__ == "__main__":
    main()
