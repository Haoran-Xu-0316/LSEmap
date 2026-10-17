"""Reopen the saved Houghton grade and check actual walking surfaces.

This verifies a bounded relative-grade study, not an absolute/current terrain
survey or accessible-route certification. Original native geometry stays intact.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/houghton-integration243"
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from plan_houghton_grade243 import grade_height
from refine_portsmouth_exterior207 import material_fingerprint


def top_tree(objects):
    vertices = []
    faces = []
    for obj in objects:
        offset = len(vertices)
        vertices.extend([obj.matrix_world @ v.co for v in obj.data.vertices])
        normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
        for polygon in obj.data.polygons:
            if (normal_matrix @ polygon.normal).z > 0.5:
                faces.append(tuple(offset + i for i in polygon.vertices))
    return BVHTree.FromPolygons(vertices, faces)


def main():
    record = json.loads((OUT / "grade-component-record.json").read_text())
    plan = json.loads((OUT / "grade-plan.json").read_text())
    protected = json.loads(
        (ROOT / "result/blender/stage243/protected-source-state.json").read_text()
    )
    path = ROOT / record["component"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["componentSha256"]
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == record["baselineSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = {
        name: object_fingerprint(bpy.data.objects[name])
        for name in protected["objects"]
    }
    assert all(
        before[name] == row["fingerprint"] for name, row in protected["objects"].items()
    )
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.objects = record["ownedObjects"]
    owned = target.objects
    for obj in owned:
        bpy.data.collections["00_SITE"].objects.link(obj)
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == record["objectFingerprints"][obj.name], (
            obj.name
        )
    update_scene()
    for name, expected in protected["materials"].items():
        assert material_fingerprint(bpy.data.materials[name]) == expected, name
    bed = bpy.data.objects["SITE243_Houghton_graded_footway_bed"]
    bm = bmesh.new()
    bm.from_mesh(bed.data)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert volume > 0 and abs(volume - plan["coreAreaM2"] * 0.05) < 0.002
    surface = top_tree(owned)
    # Probe saved support geometry across the entire core, not only the planner's
    # endpoint values. Raised covers must stay within the retained surface stack.
    offsets = []
    positions = []
    for triangle in plan["coreTriangles"]:
        x = sum(v[0] for v in triangle) / 3
        y = sum(v[1] for v in triangle) / 3
        hit = surface.ray_cast(Vector((x, y, 2)), Vector((0, 0, -1)), 4)[0]
        assert hit is not None, (x, y)
        delta = hit.z - grade_height(x, y)
        if not 0.014 <= delta <= 0.085:
            hits = []
            for obj in owned:
                hit_row = top_tree([obj]).ray_cast(
                    Vector((x, y, 2)), Vector((0, 0, -1)), 4
                )
                if hit_row[0] is not None:
                    hits.append(
                        {"object": obj.name, "height": hit_row[0].z, "face": hit_row[2]}
                    )
            (OUT / "surface-conflicts.json").write_text(
                json.dumps(
                    {
                        "point": [x, y],
                        "expectedGrade": grade_height(x, y),
                        "hits": hits,
                    },
                    indent=2,
                )
                + "\n"
            )
        assert 0.014 <= delta <= 0.085, (x, y, hit.z, grade_height(x, y), delta)
        offsets.append(delta)
        positions.append([x, y, hit.z])
    assert len(offsets) == 717
    # The sourceAldwych entrances remain outside the grade field.
    for point in [(-16.178358, -130.222015), (13, -127.3)]:
        assert grade_height(*point) == 0
    direct_source_checks = []
    for x, y, expected in plan["contactSamples"]:
        assert abs(grade_height(x, y) - expected) < 1e-8
        direct_source_checks.append([x, y, expected])
    # Preserve all source vertex/UV anchors even when local cuts are needed.
    # Uncut batches additionally retain their complete topology and face bindings.
    dense = []
    anchor_count = 0
    max_interpolation_error = 0
    for change in record["changes"]:
        source = bpy.data.objects[change["source"]]
        replacement = bpy.data.objects[change["replacement"]]
        if not change.get("locallyRetessellated"):
            assert len(source.data.vertices) == len(replacement.data.vertices)
            assert [tuple(p.vertices) for p in source.data.polygons] == [
                tuple(p.vertices) for p in replacement.data.polygons
            ]
            assert [p.material_index for p in source.data.polygons] == [
                p.material_index for p in replacement.data.polygons
            ]
            for old, new in zip(source.data.uv_layers, replacement.data.uv_layers):
                assert old.name == new.name
                assert [tuple(v.uv) for v in old.data] == [
                    tuple(v.uv) for v in new.data
                ]
            dense.append(source.name)
        kd = KDTree(len(replacement.data.vertices))
        for vertex in replacement.data.vertices:
            kd.insert(replacement.matrix_world @ vertex.co, vertex.index)
        kd.balance()
        uv_sets = []
        for layer in replacement.data.uv_layers:
            by_vertex = [set() for _ in replacement.data.vertices]
            for loop in replacement.data.loops:
                by_vertex[loop.vertex_index].add(
                    tuple(round(v, 5) for v in layer.data[loop.index].uv)
                )
            uv_sets.append(by_vertex)
        source_uv = []
        for layer in source.data.uv_layers:
            by_vertex = [set() for _ in source.data.vertices]
            for loop in source.data.loops:
                by_vertex[loop.vertex_index].add(
                    tuple(round(v, 5) for v in layer.data[loop.index].uv)
                )
            source_uv.append(by_vertex)
        assert len(uv_sets) == len(source_uv)
        for vertex in source.data.vertices:
            point = source.matrix_world @ vertex.co
            point.z += grade_height(point.x, point.y)
            matches = kd.find_range(point, 1e-5)
            assert matches, (source.name, vertex.index, tuple(point))
            for layer_index, by_vertex in enumerate(source_uv):
                actual = set().union(
                    *(uv_sets[layer_index][index] for _, index, _ in matches)
                )
                assert by_vertex[vertex.index] <= actual, (
                    source.name,
                    vertex.index,
                    by_vertex[vertex.index],
                    actual,
                )
            anchor_count += 1
        replacement.data.calc_loop_triangles()
        for triangle in replacement.data.loop_triangles:
            points = [
                replacement.matrix_world @ replacement.data.vertices[i].co
                for i in triangle.vertices
            ]
            x = sum(p.x for p in points) / 3
            y = sum(p.y for p in points) / 3
            if not (-18 <= x <= 15 and -127 <= y <= -74):
                continue
            observed = sum(p.z for p in points) / 3
            source_base = sum(p.z - grade_height(p.x, p.y) for p in points) / 3
            error = abs(observed - source_base - grade_height(x, y))
            max_interpolation_error = max(max_interpolation_error, error)
            assert error <= 0.006, (replacement.name, triangle.index, x, y, error)
    assert all(
        object_fingerprint(bpy.data.objects[n]) == expected
        for n, expected in before.items()
    )
    proof = {
        "componentReopened": True,
        "componentSha256": record["componentSha256"],
        "originalObjectsVerified": len(before),
        "originalMaterialGraphsVerified": len(protected["materials"]),
        "ownedMeshesVerified": len(owned),
        "savedSurfaceRayChecks": len(offsets),
        "relativeProfileControlChecks": len(direct_source_checks),
        "minimumSurfaceAboveGradeM": min(offsets),
        "maximumSurfaceAboveGradeM": max(offsets),
        "coreBedManifold": True,
        "coreBedVolumeM3": volume,
        "uncutTopologyUvBindingsPreserved": dense,
        "sourceVertexUvAnchorsVerified": anchor_count,
        "maximumSavedTriangleGradeInterpolationErrorM": max_interpolation_error,
        "AldwychEntranceGradeUnchanged": True,
        "allOriginalMeshFingerprintsPreserved": True,
        "roomCollectionsUnaffected": len(protected["rooms"]),
        "nativeCampusIntegrated": False,
        "scope": "Relative street-grade study with authored datum and transition collar; not a current terrain or accessibility survey",
        "limitations": plan["limitations"],
    }
    (OUT / "saved-surface-verification.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    (OUT / "saved-contact-samples.json").write_text(
        json.dumps(positions, separators=(",", ":")) + "\n"
    )
    # Native before/after views use identical lights and camera. No preview
    # camera, scene or temporary visibility state is written into the source.
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("HOUGHTON243_REVIEW_WORLD")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (
        0.68,
        0.74,
        0.8,
        1,
    )
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    sun = bpy.data.objects.new(
        "HOUGHTON243_REVIEW_SUN", bpy.data.lights.new("HOUGHTON243_REVIEW_SUN", "SUN")
    )
    scene.collection.objects.link(sun)
    sun.data.energy = 2
    sun.data.angle = 0.2
    sun.rotation_euler = (0.4, -0.4, -0.2)
    camera = bpy.data.objects.new(
        "HOUGHTON243_REVIEW_CAMERA", bpy.data.cameras.new("HOUGHTON243_REVIEW_CAMERA")
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type = "PERSP"
    camera.data.lens = 34
    camera.data.clip_end = 500
    camera.location = (0.3, -142, 6)
    target = Vector((-1.5, -107, 1.6))
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    inventory = json.loads((OUT / "ground-source-geometry.json").read_text())
    context = {r["name"] for r in inventory["objects"]}
    for code in ["CON", "COL", "OLD", "CBG"]:
        context.update(
            o.name
            for o in bpy.data.collections[code + "_EXTERIOR"].all_objects
            if not o.hide_render
        )
    initial_visibility = {o.name: o.hide_render for o in scene.objects}
    for label in ["before", "after"]:
        for obj in scene.objects:
            visible = (
                obj.name in context and not initial_visibility[obj.name]
            ) or obj in [sun, camera]
            if label == "after":
                visible = (
                    (visible and obj.name not in record["archivedObjects"])
                    or obj in owned
                    or obj in [sun, camera]
                )
            obj.hide_render = not visible
            set_layer_hidden(obj, not visible)
        scene.render.filepath = str(OUT / (label + "-street-review.png"))
        bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == record["baselineSha256"]
    print("HOUGHTON243_SAVED_SURFACES_VERIFIED", len(owned), len(offsets), flush=True)


if __name__ == "__main__":
    main()
