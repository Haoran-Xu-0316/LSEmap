"""Broaden OLD's photographed faceted stair corners without changing its levels.

Fixed authoring configuration for Blender's Text Editor. The photo establishes
long chamfered noses, not a circular arc or surveyed dimensions. Original step
strip limits, four rises, threshold and every rail are strictly retained.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v249.blend"
SHA = "cad99a189122994fd484794fb617a9223c31e90fd506fb434ef22d9e87e30e24"
OUT = ROOT / "result/blender/old-approach250"
SOURCE = "OLD_NEXT_ACCESS_external_four_steps"
NAME = "OLD250_long_chamfer_external_four_steps"
OWNER = "OLD_EXTERIOR"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_old_portal218 import components


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "old250_capture", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def tree(objects):
    vertices, faces = [], []
    for obj in objects:
        start = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(start + i for i in p.vertices) for p in obj.data.polygons)
    return BVHTree.FromPolygons(vertices, faces)


def local_part(part):
    return {k: v for k, v in part.items() if k != "indices"}


def render(label, right, normal, centre):
    scene = bpy.data.scenes.new("OLD250_REVIEW")
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
    target = centre.copy()
    target.z = 0.9
    data = bpy.data.cameras.new(scene.name)
    camera = bpy.data.objects.new(scene.name + "_camera", data)
    scene.collection.objects.link(camera)
    camera.location = target + normal * 10 + Vector((0, 0, 6.4))
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    data.type, data.ortho_scale, data.clip_end = "ORTHO", 12.4, 500
    scene.camera = camera
    light = bpy.data.lights.new(scene.name, "AREA")
    light.energy, light.size = 850, 5
    lamp = bpy.data.objects.new(scene.name + "_light", light)
    scene.collection.objects.link(lamp)
    lamp.location = target + normal * 5 - right * 3 + Vector((0, 0, 6))
    lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 64
    scene.render.resolution_x, scene.render.resolution_y = 1200, 760
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / (label + "-approach.png"))
    bpy.ops.render.render(write_still=True, scene=scene.name)
    for obj in (camera, lamp):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.scenes.remove(scene)
    bpy.data.worlds.remove(world)
    bpy.data.cameras.remove(data)
    bpy.data.lights.remove(light)
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()


def verify_geometry(obj, original, right, normal, origin):
    parts = sorted(components(obj, right, normal), key=lambda p: p["high"][2])
    old_parts = sorted(components(original, right, normal), key=lambda p: p["high"][2])
    assert len(parts) == len(old_parts) == 4
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.free()
    assert len(obj.data.vertices) == len(original.data.vertices) == 48
    assert len(obj.data.polygons) == len(original.data.polygons) == 32
    for current, before in zip(parts, old_parts):
        assert (
            max(
                abs(current[side][i] - before[side][i])
                for side in ("low", "high")
                for i in range(3)
            )
            < 0.00004
        )
    assert [round(p["high"][2], 5) for p in parts] == [0.21, 0.37, 0.53, 0.69]
    # Actual unchanged exterior foot bases, including four near-corner samples
    # around every pad, must retain exactly their previous supporting surface.
    landing = bpy.data.objects["OLD_NEXT_ACCESS_threshold_landing"]
    old_tree = tree([original, landing])
    new_tree = tree([obj, landing])
    foot_parts = components(
        bpy.data.objects["OLD_NEXT_ACCESS_rail_feet"], right, normal
    )
    exterior_feet = [
        p for p in foot_parts if 1.0 < p["centre"][1] - origin.dot(normal) < 3.2
    ]
    assert len(exterior_feet) == 4
    supports = []
    for foot in exterior_feet:
        for dx, dd in [
            (0, 0),
            (-0.045, -0.045),
            (-0.045, 0.045),
            (0.045, -0.045),
            (0.045, 0.045),
        ]:
            point = (
                right * (foot["centre"][0] + dx)
                + normal * (foot["centre"][1] + dd)
                + Vector((0, 0, foot["low"][2] + 0.08))
            )
            old_hit, _, _, _ = old_tree.ray_cast(point, Vector((0, 0, -1)), 0.20)
            hit, _, _, _ = new_tree.ray_cast(point, Vector((0, 0, -1)), 0.20)
            assert old_hit is not None and hit is not None
            assert (
                abs(hit.z - old_hit.z) < 0.00002
                and abs(hit.z - foot["low"][2]) < 0.00003
            )
            supports.append(
                {"point": list(point), "oldSupportZ": old_hit.z, "newSupportZ": hit.z}
            )
    # Sample both sides of every retained central tread seam, and the upper
    # tread/threshold seam. The outside triangular cutouts are deliberately not
    # misrepresented as a complete accessible-width survey.
    seams = []
    for index, part in enumerate(parts):
        for x in [-2.0, 0, 2.0]:
            for d in [part["low"][1] + 0.001, part["high"][1] - 0.001]:
                point = (
                    right * (part["centre"][0] + x) + normal * d + Vector((0, 0, 1.0))
                )
                old_hit, _, _, _ = old_tree.ray_cast(point, Vector((0, 0, -1)), 1.1)
                hit, _, _, _ = new_tree.ray_cast(point, Vector((0, 0, -1)), 1.1)
                assert (
                    hit is not None
                    and old_hit is not None
                    and abs(hit.z - old_hit.z) < 0.00003
                )
                seams.append(
                    {"step": index, "offsetX": x, "depth": d, "supportZ": hit.z}
                )
    top = parts[-1]
    for x in [-2.0, 0, 2.0]:
        for d in [top["low"][1] - 0.001, top["low"][1] + 0.001]:
            point = right * (top["centre"][0] + x) + normal * d + Vector((0, 0, 1.0))
            hit, _, _, _ = new_tree.ray_cast(point, Vector((0, 0, -1)), 1.1)
            assert hit is not None and abs(hit.z - 0.69) < 0.00003
            seams.append(
                {"step": "threshold-joint", "offsetX": x, "depth": d, "supportZ": hit.z}
            )
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    update_scene()
    paths = []
    for i, part in enumerate(parts):
        for x in [-2.0, 0, 2.0]:
            point = (
                right * (part["centre"][0] + x)
                + normal * part["centre"][1]
                + Vector((0, 0, part["high"][2] + 0.02))
            )
            hit, _, _, _, owner, _ = scene.ray_cast(
                bpy.context.evaluated_depsgraph_get(),
                point,
                Vector((0, 0, 1)),
                distance=1.9,
            )
            assert not hit, (i, x, owner.name if owner else None)
            paths.append(
                {"step": i, "offsetX": x, "start": list(point), "clearHeight": 1.9}
            )
    return {
        "closedManifoldSolids": 4,
        "positiveVolume": volume,
        "triangles": 80,
        "originalExtremeBoundsAndZRetained": True,
        "footSupportSamples": supports,
        "treadSeamAndThresholdSupportSamples": seams,
        "centralUpwardClearanceRays": paths,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    component = OUT / "component.blend"
    assert not component.exists(), "Do not overwrite a reviewed component"
    assert sha(BASE) == SHA
    plan = json.loads((OUT / "shape-plan.json").read_text())
    source_review = json.loads((OUT / "source-review.json").read_text())
    assert sha(ROOT / source_review["sourcePath"]) == source_review["sha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    visibility = {
        o.name: (o.hide_render, o.hide_viewport, o.hide_get()) for o in bpy.data.objects
    }
    reg = json.loads(
        (ROOT / "result/blender/old_houghton_next/audit.json").read_text()
    )["registration"]
    right, normal, origin = [Vector(reg[k]) for k in ["right", "outward", "origin"]]
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render
    source_parts = sorted(components(source, right, normal), key=lambda p: p["high"][2])
    assert len(source_parts) == 4
    centre = (
        right * source_parts[0]["centre"][0] + normal * source_parts[0]["centre"][1]
    )
    render("before", right, normal, centre)
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = obj.data.name = NAME
    bpy.data.collections[OWNER].objects.link(obj)
    inverse = obj.matrix_world.inverted()
    movements = []
    for part in source_parts:
        assert abs(part["dimensions"][1] - 0.45) < 0.00003
        cut_width = (
            part["dimensions"][0]
            * plan["candidate"]["cornerAlongWidthFractionOfWholeTread"]
        )
        cut_depth = plan["candidate"]["cornerAlongDepthMetres"]
        assert 0.18 < cut_depth < part["dimensions"][1]
        assert 0.18 < cut_width < part["dimensions"][0] / 2
        moved = 0
        for index in part["indices"]:
            point = obj.matrix_world @ obj.data.vertices[index].co
            x, d = point.dot(right), point.dot(normal)
            if abs(d - part["high"][1]) < 0.00003:
                sign = -1 if x < part["centre"][0] else 1
                new_x = part["centre"][0] + sign * (
                    part["dimensions"][0] / 2 - cut_width
                )
                point += right * (new_x - x)
                moved += 1
            elif abs(d - (part["high"][1] - 0.18)) < 0.00003:
                point += normal * (part["high"][1] - cut_depth - d)
                moved += 1
            obj.data.vertices[index].co = inverse @ point
        assert moved == 8
        movements.append(
            {
                "before": local_part(part),
                "newWidthCornerCut": cut_width,
                "newDepthCornerCut": cut_depth,
                "changedVertices": moved,
            }
        )
    obj.data.update()
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    # Replacement alone receives metric planar UVs. Every original layer stays
    # byte-identical in the preserved source data block.
    for uv in obj.data.uv_layers:
        for face in obj.data.polygons:
            normal_world = (
                obj.matrix_world.to_3x3().inverted().transposed() @ face.normal
            ).normalized()
            for loop_index in face.loop_indices:
                point = (
                    obj.matrix_world
                    @ obj.data.vertices[obj.data.loops[loop_index].vertex_index].co
                )
                if abs(normal_world.z) > 0.5:
                    coord = (point.dot(right), point.dot(normal))
                elif abs(normal_world.dot(normal)) > 0.5:
                    coord = (point.dot(right), point.z)
                else:
                    coord = (point.dot(normal), point.z)
                uv.data[loop_index].uv = coord
    obj["originalObject"] = SOURCE
    obj["destinationCollection"] = OWNER
    obj["scope"] = (
        "Photo-guided long faceted noses; original extreme strip bounds,Z,threshold and rails retained"
    )
    obj["presentationEstimated"] = True
    update_scene()
    current = capture()
    assert all(current["objects"][n] == v for n, v in before["objects"].items())
    assert current["materials"] == before["materials"]
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    checks = verify_geometry(obj, source, right, normal, origin)
    expected = object_fingerprint(obj)
    bindings = [m.name for m in obj.data.materials]
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_available, loaded):
        loaded.objects = [NAME]
    obj = loaded.objects[0]
    for index, name in enumerate(bindings):
        obj.data.materials[index] = bpy.data.materials[name]
    bpy.data.collections[OWNER].objects.link(obj)
    source = bpy.data.objects[SOURCE]
    source.hide_render = True
    source.hide_set(True)
    update_scene()
    assert object_fingerprint(obj) == expected
    after = capture()
    for name, value in before["objects"].items():
        expected_state = dict(value)
        if name == SOURCE:
            expected_state["hidden"] = True
        assert after["objects"][name] == expected_state, name
    assert all(after["materials"][n] == v for n, v in before["materials"].items())
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert all(
        (
            bpy.data.objects[n].hide_render,
            bpy.data.objects[n].hide_viewport,
            bpy.data.objects[n].hide_get(),
        )
        == v
        for n, v in visibility.items()
        if n != SOURCE
    )
    saved_checks = verify_geometry(obj, source, right, normal, origin)
    assert saved_checks == checks
    render("after", right, normal, centre)
    assert sha(BASE) == SHA
    write(
        "saved-verification.json",
        {
            "savedComponentReopened": True,
            "originalObjectsPreserved": len(before["objects"]),
            "originalMaterialGraphsPreserved": len(before["materials"]),
            "protectedRooms": len(before["rooms"]),
            "protectedRoomObjects": len(
                {n for a in before["rooms"].values() for n in a}
            ),
            "sourceBytesUnchanged": True,
            "allOriginalGeometryUVNormalBindingsTransformsModifiersPropertiesOwnersUnchanged": True,
            "unrelatedVisibilityUnchanged": True,
            **saved_checks,
        },
    )
    write(
        "audit.json",
        {
            "version": 250,
            "building": "OLD",
            "status": "saved-native-candidate-awaiting-visual-review",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "targetCollection": OWNER,
            "destinationCollection": OWNER,
            "addedObjects": [NAME],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {NAME: expected},
            "replacementMaterialBindings": {NAME: bindings},
            "shapePlan": "shape-plan.json",
            "sourceReview": "source-review.json",
            "geometryChanges": movements,
            "verification": "saved-verification.json",
            "previews": ["before-approach.png", "after-approach.png"],
            "limitations": [
                "Four faceted corner proportions are visually estimated from an uncalibrated photo; they are not circular arcs or as-built measurements.",
                "Original extreme tread bounds and four heights remain estimated inherited construction. No rise/run/accessibility certification is claimed.",
                "Only three central lanes,original foot pads and preserved central seams are verified. This is not a complete building navigation or egress audit.",
                "Glass,Final Sale,Clare entrance,doorway,threshold,rails,street and all interiors remain untouched.",
            ],
        },
    )
    print(
        "OLD250_COMPONENT_REOPENED",
        sha(component),
        len(checks["footSupportSamples"]),
        len(checks["treadSeamAndThresholdSupportSamples"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
