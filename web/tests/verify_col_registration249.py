"""Reopen the private COL registration and expose remaining roof conflicts.

A verified frontage component is not approval of its whole-building assembly.
The saved result deliberately keeps roof coordination as a publication gate.
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
OUT = ROOT / "result/blender/col-registration249"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene


def tree(obj):
    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
    )


def face_key(obj, polygon):
    return (
        polygon.material_index,
        polygon.use_smooth,
        tuple(
            tuple(
                round(c, 5)
                for c in obj.matrix_world
                @ obj.data.vertices[obj.data.loops[li].vertex_index].co
            )
            + tuple(
                tuple(round(c, 5) for c in uv.data[li].uv) for uv in obj.data.uv_layers
            )
            for li in polygon.loop_indices
        ),
    )


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    plan = json.loads((OUT / "registration-plan.json").read_text())
    source = json.loads((ROOT / plan["sourcePlan"]).read_text())
    path = ROOT / audit["component"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == audit["componentSha256"]
    baseline = ROOT / plan["baseline"]
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == plan["baselineSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(baseline))
    update_scene()
    protected = json.loads((OUT / "protected-source-state.json").read_text())
    original_materials = {m.name: m for m in bpy.data.materials}
    with bpy.data.libraries.load(str(path), link=False) as (_lib, loaded):
        loaded.collections = ["COL249_REGISTERED_CANDIDATE"]
    collection = loaded.collections[0]
    bpy.context.scene.collection.children.link(collection)
    for obj in collection.all_objects:
        for index, identity in enumerate(
            audit["replacementMaterialBindings"][obj.name]
        ):
            if identity in original_materials:
                obj.data.materials[index] = original_materials[identity]
    update_scene()
    for name, expected in audit["addedFingerprints"].items():
        assert object_fingerprint(bpy.data.objects[name]) == expected, name
    spec = importlib.util.spec_from_file_location(
        "protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = plan["baselineSha256"]
    current = helper.capture_source()
    for name, row in protected["objects"].items():
        assert current["objects"][name] == row, name
    for name, value in protected["materials"].items():
        assert current["materials"][name] == value, name
    assert (
        current["rooms"] == protected["rooms"]
        and current["campusRooms"] == protected["campusRooms"]
    )
    wall = bpy.data.objects["COL249_Houghton_perforated_wall"]
    panes = bpy.data.objects["COL249_Houghton_glazing"]
    infill = bpy.data.objects["COL249_Houghton_opaque_ground_infill"]
    back = bpy.data.objects["COL249_Houghton_closed_backing"]
    assert (
        len(panes.data.polygons) == 64
        and len(infill.data.polygons) == 8
        and len(back.data.polygons) == 72
    )
    shader = panes.data.materials[0].node_tree.nodes.get("Principled BSDF")
    assert (
        shader.inputs["Metallic"].default_value == 0
        and abs(shader.inputs["Transmission Weight"].default_value - 0.58) < 1e-6
    )
    assert (
        infill.data.materials[0]
        .node_tree.nodes.get("Principled BSDF")
        .inputs["Transmission Weight"]
        .default_value
        == 0
    )
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert volume > 0
    wall_tree = tree(wall)
    pane_tree = tree(panes)
    infill_tree = tree(infill)
    back_tree = tree(back)
    n = Vector((*plan["frontageNorthToSouth"][0], 0))
    axis = Vector((*plan["axis"], 0))
    inside = Vector((*plan["inwardNormal"], 0))
    ox, oy = source["sourceOrigin"]
    scale = source["metresPerPoint"]
    fit = plan["horizontalFit"]
    opaque = []
    for obj in list(bpy.data.collections["COL_EXTERIOR"].all_objects) + list(
        collection.all_objects
    ):
        if (
            obj.type != "MESH"
            or obj.name in audit["archivedObjects"]
            or obj.hide_render
        ):
            continue
        if obj.name.startswith("COL249_Houghton_"):
            continue
        if any(
            "glass" in m.name.lower() or "glaz" in m.name.lower()
            for m in obj.data.materials
            if m
        ):
            continue
        opaque.append((obj.name, tree(obj)))
    rays = []
    occlusions = []
    for opening in source["openings"]:
        x0, y0, x1, y1 = opening["sourceBounds"]
        for fraction in [0.2, 0.5, 0.8]:
            x = x0 + (x1 - x0) * fraction
            y = y0 + (y1 - y0) * fraction
            source_x = (x - ox) * scale
            z = (oy - y) * scale
            if opening["role"] == "entrance-material-unverified":
                lower = max(
                    (oy - y1) * scale,
                    source["groundRiseNorthM"]
                    * (1 - source_x / source["sourceWidthM"]),
                )
                head = (oy - y0) * scale
                z = head - (head - z) * (head - plan["flatStreetThresholdM"]) / (
                    head - lower
                )
            xy = n + axis * (source_x * fit)
            origin = Vector((xy.x, xy.y, z)) - inside
            assert wall_tree.ray_cast(origin, inside, 1.135)[0] is None, opening["id"]
            expected = pane_tree if opening["role"] == "regular-window" else infill_tree
            hit = expected.ray_cast(origin, inside, 2)
            bhit = back_tree.ray_cast(origin, inside, 2)
            assert hit[0] is not None and abs(hit[3] - 1.14) < 0.002, opening["id"]
            assert bhit[0] is not None and abs(bhit[3] - 1.60) < 0.003, opening["id"]
            blocked = []
            for name, bvh in opaque:
                intercept = bvh.ray_cast(origin, inside, 1.135)
                if intercept[0] is not None:
                    blocked.append({"object": name, "distanceM": intercept[3]})
            if blocked:
                occlusions.append(
                    {
                        "opening": opening["id"],
                        "fraction": fraction,
                        "intercepts": blocked,
                    }
                )
            rays.append(
                {
                    "opening": opening["id"],
                    "fraction": fraction,
                    "infillDistanceM": hit[3],
                    "backingDistanceM": bhit[3],
                }
            )
    preserved = 0
    for item in audit["cornerClipping"]:
        original = bpy.data.objects[item["original"]]
        retained = bpy.data.objects["COL249_retained_" + original.name]
        keys = Counter(face_key(retained, p) for p in retained.data.polygons)
        for index in item["untouchedSourcePolygonIndices"]:
            key = face_key(original, original.data.polygons[index])
            assert keys[key] > 0, (original.name, index)
            keys[key] -= 1
            preserved += 1
        assert len(retained.data.uv_layers) == len(original.data.uv_layers)
    assert len(rays) == 216
    proof = {
        "componentReopened": True,
        "componentSha256": audit["componentSha256"],
        "savedObjectsVerified": len(audit["addedObjects"]),
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialsVerified": len(protected["materials"]),
        "protectedRooms": len(protected["rooms"]),
        "sourceModules": 72,
        "glassModules": 64,
        "opaqueGroundModules": 8,
        "closedBackingModules": 72,
        "openingAndBackingRays": len(rays),
        "wallManifold": True,
        "wallVolumeM3": volume,
        "unaffectedFaceUVRecordsVerified": preserved,
        "boundedCornerFacesClipped": sum(
            x["boundedFacesClipped"] for x in audit["cornerClipping"]
        ),
        "retainedAssemblyOpaqueOcclusions": occlusions,
        "roofVolumeAccepted": False,
        "status": "registered source frontage verified; whole-building roof remains a separate integration gate",
    }
    (OUT / "saved-verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    # Native comparisons are temporary. Save the component before creating cameras
    # and do not persist any visibility change to the full campus.
    exterior = set(bpy.data.collections["COL_EXTERIOR"].all_objects)
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "FONT", "CURVE"}:
            obj.hide_render = obj.hide_render or obj not in exterior
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    camera_data = bpy.data.cameras.new("COL249_review_camera")
    camera = bpy.data.objects.new("COL249_review_camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    centre = n + axis * (plan["nativeLengthM"] * 0.5)
    target = Vector((centre.x, centre.y, 17))
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 40
    camera.location = target - inside * 75
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    for state in ["before", "after"]:
        for obj in collection.all_objects:
            obj.hide_render = state == "before"
        for name in audit["archivedObjects"]:
            bpy.data.objects[name].hide_render = state == "after"
        scene.render.filepath = str(OUT / f"{state}-registered-frontage.png")
        bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == plan["baselineSha256"]
    print("COL249_SAVED_VERIFIED", len(rays), preserved, len(occlusions), flush=True)


if __name__ == "__main__":
    main()
