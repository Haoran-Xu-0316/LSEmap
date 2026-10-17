"""Reopen and examine the actual saved CON registration candidate.

This check does not certify the unseen roof as surveyed. The historic opening
layout and current native access/parcel protection are separate evidence gates.
"""

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con-registration244"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def tree(obj):
    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
    )


def face_key(obj, polygon):
    uv = obj.data.uv_layers.active
    return (
        polygon.material_index,
        polygon.use_smooth,
        tuple(
            tuple(
                round(x, 5)
                for x in obj.matrix_world
                @ obj.data.vertices[obj.data.loops[li].vertex_index].co
            )
            + (tuple(round(x, 5) for x in uv.data[li].uv) if uv else (0, 0))
            for li in polygon.loop_indices
        ),
    )


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    registration = json.loads((OUT / "registration-plan.json").read_text())
    source = json.loads((ROOT / registration["sourcePlan"]).read_text())
    component = ROOT / audit["component"]
    assert (
        hashlib.sha256(component.read_bytes()).hexdigest() == audit["componentSha256"]
    )
    baseline = ROOT / registration["baseline"]
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == audit["baselineSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    protected = json.loads(
        (ROOT / "result/blender/stage244/protected-source-state.json").read_text()
    )
    original_materials = {m.name: m for m in bpy.data.materials}
    with bpy.data.libraries.load(str(component), link=False) as (_library, imported):
        imported.collections = ["CON244_REGISTERED_CANDIDATE"]
    collection = imported.collections[0]
    bpy.context.scene.collection.children.link(collection)
    for obj in collection.all_objects:
        for index, identity in enumerate(
            audit["replacementMaterialBindings"][obj.name]
        ):
            if identity in original_materials:
                obj.data.materials[index] = original_materials[identity]
    update_scene()
    assert {o.name for o in collection.all_objects} == set(audit["addedObjects"])
    for name, expected in audit["addedFingerprints"].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
    for name, row in protected["objects"].items():
        assert object_fingerprint(bpy.data.objects[name]) == row["fingerprint"], name
    spec = importlib.util.spec_from_file_location(
        "native_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = audit["baselineSha256"]
    current = helper.capture_source()
    for name, expected in protected["materials"].items():
        assert current["materials"][name] == expected, name
    assert current["rooms"] == protected["rooms"]
    assert current["campusRooms"] == protected["campusRooms"]
    wall = bpy.data.objects["CON244_Houghton_perforated_wall"]
    panes = bpy.data.objects["CON244_Houghton_glazing"]
    back = bpy.data.objects["CON244_Houghton_closed_backing"]
    roof = bpy.data.objects["CON244_closed_roof_slab"]
    glazing = panes.data.materials[0]
    bsdf = glazing.node_tree.nodes.get("Principled BSDF")
    assert abs(bsdf.inputs["Transmission Weight"].default_value - 0.58) < 1e-6
    assert abs(bsdf.inputs["Metallic"].default_value) < 1e-6
    assert abs(glazing["webOpacity"] - 0.44) < 1e-6
    assert not glazing.get("webClosedGlazing")
    volumes = {}
    for obj in [wall, roof]:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        assert all(e.is_manifold for e in bm.edges), obj.name
        volumes[obj.name] = bm.calc_volume(signed=True)
        assert volumes[obj.name] > 0, obj.name
        bm.free()
    wall_tree, pane_tree, back_tree = tree(wall), tree(panes), tree(back)
    controls = [Vector(p) for p in registration["frontage"]]
    lengths = registration["segmentLengthsM"]
    # Look for old opaque fragments in front of the new glass, using the
    # assembled retained facade rather than only checking the new wall alone.
    opaque_trees = []
    candidates = set(bpy.data.collections["CON_EXTERIOR"].all_objects) | set(
        collection.all_objects
    )
    for obj in candidates:
        if (
            obj.type != "MESH"
            or obj.hide_render
            or obj.name in audit["archivedObjects"]
        ):
            continue
        if obj.name == panes.name or any(
            "glaz" in m.name.lower() or "glass" in m.name.lower()
            for m in obj.data.materials
            if m
        ):
            continue
        opaque_trees.append((obj.name, tree(obj)))
    ray_records = []
    for opening in source["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        for fraction in [0.2, 0.5, 0.8]:
            x = x0 + (x1 - x0) * fraction
            y = y0 + (y1 - y0) * fraction
            station = (
                (x - source["sourceOrigin"][0])
                * source["metresPerPoint"]
                * registration["horizontalFit"]
            )
            index = int(station > lengths[0])
            along = station - (lengths[0] if index else 0)
            axis = (controls[index + 1] - controls[index]).normalized()
            inside = Vector((-axis.y, axis.x, 0))
            xy = controls[index] + axis * along
            z = (source["sourceOrigin"][1] - y) * source["metresPerPoint"]
            if opening["role"] == "door":
                bottom = (source["sourceOrigin"][1] - y1) * source["metresPerPoint"]
                head = (source["sourceOrigin"][1] - y0) * source["metresPerPoint"]
                z = head - (head - z) * (head - registration["doorThresholdM"]) / (
                    head - bottom
                )
            origin = Vector((xy.x, xy.y, z)) - inside
            assert wall_tree.ray_cast(origin, inside, 2)[0] is None, opening["id"]
            phit = pane_tree.ray_cast(origin, inside, 2)
            bhit = back_tree.ray_cast(origin, inside, 2)
            assert phit[0] is not None and abs(phit[3] - 1.14) < 0.002, opening["id"]
            assert bhit[0] is not None and abs(bhit[3] - 1.60) < 0.003, opening["id"]
            for identity, opaque_tree in opaque_trees:
                obstructing = opaque_tree.ray_cast(origin, inside, 1.135)
                assert obstructing[0] is None, (opening["id"], identity, obstructing[3])
            expected_material = int(opening["role"] != "window")
            assert panes.data.polygons[phit[2]].material_index == expected_material, (
                opening["id"]
            )
            selected = panes.data.materials[expected_material]
            selected_transmission = (
                selected.node_tree.nodes.get("Principled BSDF")
                .inputs["Transmission Weight"]
                .default_value
            )
            assert (selected_transmission > 0.5) == (opening["role"] == "window")
            ray_records.append(
                {
                    "opening": opening["id"],
                    "fraction": fraction,
                    "glassDistanceM": phit[3],
                    "backingDistanceM": bhit[3],
                }
            )
    assert len(ray_records) == 267
    expected_roof_volume = (
        registration["roofFootprintAreaM2"] * registration["roofSlabThicknessM"]
    )
    assert abs(volumes[roof.name] - expected_roof_volume) < 0.003
    roof_tree = tree(roof)
    roof_checks = 0
    profile = registration["roofProfileStationHeightM"]
    roof_axis = Vector(registration["roofProjectionAxis"])
    for triangle in registration["roofTriangles"]:
        xy = sum((Vector(v) for v in triangle), Vector((0, 0))) / 3
        station = (xy - controls[0]).dot(roof_axis)
        expected = profile[-1][1]
        for index in range(len(profile) - 1):
            left, lower = profile[index]
            right, upper = profile[index + 1]
            if station <= right:
                expected = lower + (upper - lower) * max(0, station - left) / (
                    right - left
                )
                break
        hit = roof_tree.ray_cast(Vector((xy.x, xy.y, 40)), Vector((0, 0, -1)), 20)
        assert hit[0] is not None and abs(hit[0].z - expected) < 1e-4
        roof_checks += 1
    mask = json.loads(
        (
            ROOT / "result/blender/con-frontage243/skin-mask-review/polygon-mask.json"
        ).read_text()
    )
    summary = json.loads(
        (
            ROOT / "result/blender/con-frontage243/skin-mask-review/review-summary.json"
        ).read_text()
    )
    ambiguous = {}
    for case in summary["ambiguousCases"]:
        ambiguous.setdefault(case["object"], set()).update(
            case["requiresFaceClippingPolygonIndices"]
        )
    retained_checks = 0
    for row in mask["objects"]:
        replacement = bpy.data.objects.get("CON244_retained_" + row["name"])
        if not replacement:
            continue
        original = bpy.data.objects[row["name"]]
        omitted = set(row["removePolygonIndices"]) | ambiguous.get(row["name"], set())
        actual = Counter(face_key(replacement, p) for p in replacement.data.polygons)
        for polygon in original.data.polygons:
            if polygon.index not in omitted:
                key = face_key(original, polygon)
                assert actual[key] > 0, (original.name, polygon.index)
                actual[key] -= 1
                retained_checks += 1
    # Only now switch visibility to inspect the assembled candidate. Nothing is
    # saved back into the accepted baseline, including these review settings.
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
    visible = set(bpy.data.collections["CON_EXTERIOR"].all_objects) | set(
        collection.all_objects
    )
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj not in visible:
            obj.hide_render = True
    scene = bpy.context.scene
    world = bpy.data.worlds.new("CON244_REVIEW_WORLD")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.68, 0.74, 0.8, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    scene.world = world
    for obj in scene.objects:
        if obj.type == "LIGHT":
            obj.hide_render = True
    light = bpy.data.objects.new(
        "CON244_REVIEW_SUN", bpy.data.lights.new("CON244_REVIEW_SUN", "SUN")
    )
    scene.collection.objects.link(light)
    light.data.energy = 2
    light.data.angle = 0.2
    light.rotation_euler = (0.5, -0.4, -0.3)
    camera = bpy.data.objects.new(
        "CON244_REVIEW_CAMERA", bpy.data.cameras.new("CON244_REVIEW_CAMERA")
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.clip_end = 500
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    centre = Vector((-13, -113, 16))
    for name, position, size in [
        ("frontage", (65, -102, 17), 41),
        ("oblique", (38, -161, 41), 52),
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
        "componentSha256": audit["componentSha256"],
        "objectsVerified": len(audit["addedObjects"]),
        "sourceOpeningModules": 89,
        "sourceWindowModules": 80,
        "opaqueUnverifiedOrDoorModules": 9,
        "finiteBackedGlazing": {
            "nativeTransmission": 0.58,
            "webOpacity": 0.44,
            "metallic": 0,
            "openSurface": True,
        },
        "clearHoleRayChecks": len(ray_records),
        "assembledOpaqueFragmentRayChecks": len(ray_records),
        "savedRoofVerticalRayChecks": roof_checks,
        "savedRoofFootprintVolumeErrorM3": abs(
            volumes[roof.name] - expected_roof_volume
        ),
        "rayChecks": ray_records,
        "manifoldVolumesM3": volumes,
        "unchangedOtherFacadeFacesAndUVs": retained_checks,
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialGraphsVerified": len(protected["materials"]),
        "protectedRooms": len(protected["rooms"]),
        "nativeCampusUnchanged": True,
        "horizontalCompressionPercent": registration["horizontalCompressionPercent"],
        "nativeIntegrationAccepted": False,
        "pending": [
            "Review full candidate views and roof/other-facade transition; confirm no old pane or corner intersections.",
            "Unseen rear closure remains an estimate and must not be represented as a current survey.",
        ],
        "limitations": registration["limitations"],
    }
    (OUT / "saved-mesh-verification.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == audit["baselineSha256"]
    print(
        "CON244_SAVED_REGISTRATION_VERIFIED",
        len(ray_records),
        retained_checks,
        flush=True,
    )


if __name__ == "__main__":
    main()
