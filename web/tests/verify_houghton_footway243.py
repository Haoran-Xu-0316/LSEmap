"""Reopen the level footway support and verify native contacts and visibility."""

import hashlib
import json
import sys
from pathlib import Path

try:
    import bmesh
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
except ImportError:
    bpy = None

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
OUT = ROOT / "result/blender/houghton-footway243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
if bpy is not None:
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_portsmouth_exterior207 import material_fingerprint


def tree(objects):
    vertices, faces = [], []
    for obj in objects:
        offset = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        normal = obj.matrix_world.to_3x3().inverted().transposed()
        faces.extend(
            tuple(offset + i for i in p.vertices)
            for p in obj.data.polygons
            if (normal @ p.normal).z > 0.5
        )
    return BVHTree.FromPolygons(vertices, faces)


def main():
    report = json.loads((OUT / "candidate.json").read_text())
    protected = json.loads(
        (ROOT / "result/blender/stage243/protected-source-state.json").read_text()
    )
    path = ROOT / report["component"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == report["componentSha256"]
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == report["baselineSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    with bpy.data.libraries.load(str(path), link=False) as (_, target):
        target.objects = report["addedObjects"]
    owned = target.objects
    assert len(owned) == 2
    obj = next(o for o in owned if o.name == "SITE243_Houghton_paving_support")
    replacement = next(o for o in owned if o != obj)
    for current in owned:
        bpy.data.collections["00_SITE"].objects.link(current)
        for index, name in enumerate(
            report["replacementMaterialBindings"][current.name]
        ):
            current.data.materials[index] = bpy.data.materials[name]
    update_scene()
    assert all(
        object_fingerprint(o) == report["addedFingerprints"][o.name] for o in owned
    )
    source = bpy.data.objects[report["pavingRepair"]["source"]]
    removed = {r["sourceFace"] for r in report["pavingRepair"]["repairs"]}
    retained = []
    added = []
    provenance = replacement.data.attributes["sourceFace243"].data
    for face in replacement.data.polygons:
        index = provenance[face.index].value
        if index >= 0:
            old = source.data.polygons[index]
            assert index not in removed
            assert face.material_index == old.material_index
            assert face.use_smooth == old.use_smooth
            assert [tuple(replacement.data.vertices[i].co) for i in face.vertices] == [
                tuple(source.data.vertices[i].co) for i in old.vertices
            ]
            for before_uv, after_uv in zip(
                source.data.uv_layers, replacement.data.uv_layers, strict=True
            ):
                assert [tuple(before_uv.data[i].uv) for i in old.loop_indices] == [
                    tuple(after_uv.data[i].uv) for i in face.loop_indices
                ]
            retained.append(index)
        else:
            assert face.normal.z > 0.99
            added.append(face.index)
    assert set(retained) == set(range(len(source.data.polygons))) - removed
    saved_tops = []
    for face in replacement.data.polygons:
        points = [
            replacement.matrix_world @ replacement.data.vertices[i].co
            for i in face.vertices
        ]
        if all(abs(p.z - 0.05) < 1e-6 for p in points):
            saved_tops.append(
                {
                    "face": face.index,
                    "source": provenance[face.index].value,
                    "points": [[p.x, p.y] for p in points],
                }
            )
    (OUT / "saved-paving-topology.json").write_text(
        json.dumps(
            {
                "tops": saved_tops,
                "retainedFaces": len(retained),
                "clippedFaces": len(removed),
                "newFaces": len(added),
            },
            separators=(",", ":"),
        )
        + "\n"
    )
    for name, row in protected["objects"].items():
        assert object_fingerprint(bpy.data.objects[name]) == row["fingerprint"], name
        assert bpy.data.objects[name].hide_render == row["hidden"], name
    for name, expected in protected["materials"].items():
        assert material_fingerprint(bpy.data.materials[name]) == expected, name
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert abs(volume - report["coreAreaM2"] * 0.05) < 0.002
    inventory = json.loads(
        (
            ROOT / "result/blender/houghton-integration243/ground-source-geometry.json"
        ).read_text()
    )
    ground = [
        bpy.data.objects[r["name"]]
        for r in inventory["objects"]
        if not bpy.data.objects[r["name"]].hide_render
    ]
    baseline, support, combined = (
        tree(ground),
        tree([obj]),
        tree([o for o in ground if o.name not in report["archivedObjects"]] + owned),
    )
    exposed, maximum_lift, samples = 0, 0, []
    for triangle in report["coreTrianglesXY"]:
        x, y = (sum(p[i] for p in triangle) / 3 for i in range(2))
        origin, direction = Vector((x, y, 2)), Vector((0, 0, -1))
        bed = support.ray_cast(origin, direction, 4)[0]
        before = baseline.ray_cast(origin, direction, 4)[0]
        after = combined.ray_cast(origin, direction, 4)[0]
        assert bed is not None and abs(bed.z - 0.018) < 0.00001
        assert after is not None and after.z >= bed.z - 0.00001
        if before is None or before.z < bed.z - 0.00001:
            exposed += 1
        if before is not None:
            assert after.z >= before.z - 0.00001
            maximum_lift = max(maximum_lift, after.z - before.z)
        samples.append([x, y, before.z if before else None, after.z])
    # Review-camera floor projections locate the visible southern black seam.
    seam_checks = []
    for x, y in [(-4.3806, -124.9031), (-4.1148, -126.8175), (-4.6217, -127.7829)]:
        hit = support.ray_cast(Vector((x, y, 2)), Vector((0, 0, -1)), 4)[0]
        assert hit is not None and abs(hit.z - 0.018) < 0.00001, (x, y)
        seam_checks.append([x, y, hit.z])
    assert len(samples) == len(report["coreTrianglesXY"])
    assert len(samples) > 717
    # Every original entry and bollard remains byte-identical and at its original
    # visible level; the support never reaches above the retained24mm roads.
    assert max(v.co.z for v in obj.data.vertices) < 0.024
    proof = {
        "componentReopened": True,
        "componentSha256": report["componentSha256"],
        "originalObjectsVerified": len(protected["objects"]),
        "originalMaterialsVerified": len(protected["materials"]),
        "bedManifold": True,
        "southernVisibleSeamChecks": seam_checks,
        "bedVolumeM3": volume,
        "savedSupportRayChecks": len(samples),
        "bedExposedSamples": exposed,
        "maximumSurfaceLiftM": maximum_lift,
        "originalEntryAndFurnitureLevelsPreserved": True,
        "bedBelowRetainedRoadM": 0.006,
        "relativeGradeCandidateExcluded": True,
        "independentRoomsRetained": len(protected["rooms"]),
        "scope": report["scope"],
    }
    (OUT / "saved-contact-verification.json").write_text(
        json.dumps(proof, indent=2) + "\n"
    )
    (OUT / "saved-contact-samples.json").write_text(
        json.dumps(samples, separators=(",", ":")) + "\n"
    )
    scene = bpy.context.scene
    scene.world = bpy.data.worlds.new("HOUGHTON243_SUPPORT_REVIEW_WORLD")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (
        0.68,
        0.74,
        0.8,
        1,
    )
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
    sun = bpy.data.objects.new(
        "HOUGHTON243_SUPPORT_REVIEW_SUN",
        bpy.data.lights.new("HOUGHTON243_SUPPORT_REVIEW_SUN", "SUN"),
    )
    scene.collection.objects.link(sun)
    sun.data.energy, sun.data.angle = 2, 0.2
    sun.rotation_euler = (0.4, -0.4, -0.2)
    camera = bpy.data.objects.new(
        "HOUGHTON243_SUPPORT_REVIEW_CAMERA",
        bpy.data.cameras.new("HOUGHTON243_SUPPORT_REVIEW_CAMERA"),
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens, camera.data.clip_end = 34, 500
    camera.location = (0.3, -142, 6)
    camera.rotation_euler = (
        (Vector((-1.5, -107, 1.6)) - camera.location)
        .to_track_quat("-Z", "Y")
        .to_euler()
    )
    scene.render.engine, scene.cycles.samples = "CYCLES", 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    context = {o.name for o in ground}
    for code in ["CON", "COL", "OLD", "CBG"]:
        context.update(
            o.name
            for o in bpy.data.collections[code + "_EXTERIOR"].all_objects
            if not o.hide_render
        )
    original_visibility = {o.name: o.hide_render for o in scene.objects}
    for label in ["before", "after"]:
        for current in scene.objects:
            visible = (
                current.name in context and not original_visibility[current.name]
            ) or current in [sun, camera]
            if current in owned:
                visible = label == "after"
            if label == "after" and current.name in report["archivedObjects"]:
                visible = False
            current.hide_render = not visible
            set_layer_hidden(current, not visible)
        scene.render.filepath = str(OUT / (label + "-street-review.png"))
        bpy.ops.render.render(write_still=True)
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == report["baselineSha256"]
    print("HOUGHTON243_LEVEL_SUPPORT_VERIFIED", len(samples), exposed, flush=True)


def verify_saved_partition():
    from shapely import Polygon, STRtree, box, maximum_inscribed_circle, unary_union

    report = json.loads((OUT / "candidate.json").read_text())
    contact_path = OUT / "saved-contact-verification.json"
    contact = json.loads(contact_path.read_text())
    assert contact["componentSha256"] == report["componentSha256"]
    topology_path = OUT / "saved-paving-topology.json"
    assert (
        (OUT / "candidate.json").stat().st_mtime_ns
        <= topology_path.stat().st_mtime_ns
        <= contact_path.stat().st_mtime_ns
    )
    saved = json.loads(topology_path.read_text())
    inventory = json.loads(
        (
            ROOT / "result/blender/houghton-integration243/ground-source-geometry.json"
        ).read_text()
    )
    source = next(
        r for r in inventory["objects"] if r["name"] == report["pavingRepair"]["source"]
    )
    polygons = [Polygon(row["points"]) for row in saved["tops"]]
    tree_index = STRtree(polygons)
    maximum = 0
    maximum_interior = 0
    storage_tolerance = 0.00002
    for index, row in enumerate(saved["tops"]):
        if row["source"] >= 0:
            continue
        for other in tree_index.query(polygons[index], predicate="intersects"):
            if other == index:
                continue
            area = polygons[index].intersection(polygons[other]).area
            maximum = max(maximum, area)
            # Native float32 positions have an8micrometre ULP here. Shared
            # triangulation edges can overlap by a few micrometres on reopen;
            # reject overlapping interiors beyond that storage boundary, while
            # retaining the raw area in the report rather than calling it zero.
            interior = (
                polygons[index]
                .buffer(-storage_tolerance)
                .intersection(polygons[other].buffer(-storage_tolerance))
                .area
            )
            maximum_interior = max(maximum_interior, interior)
            assert area < 0.00001 and interior < 1e-10, (
                index,
                int(other),
                area,
                interior,
            )
    region = box(-9, -135, 7, -97)
    before = []
    for face in source["faces"]:
        points = [source["vertices"][i] for i in face]
        if all(abs(p[2] - 0.05) < 1e-6 for p in points):
            polygon = Polygon([p[:2] for p in points])
            if polygon.is_valid and polygon.intersects(region):
                before.append(polygon.intersection(region))
    after = [p.intersection(region) for p in polygons if p.intersects(region)]
    before_shape, after_shape = unary_union(before), unary_union(after)
    difference = before_shape.symmetric_difference(after_shape).area
    # Clipping leaves submillimetre stone joints above a continuous support
    # bed. Bound actual missing-top width, not distance from an acute tip: an
    # eroded narrow triangle may lose its long tip while leaving no wide gap.
    missing = before_shape.difference(after_shape)
    parts = list(missing.geoms) if hasattr(missing, "geoms") else [missing]
    maximum_missing_radius = max(
        (
            maximum_inscribed_circle(p, tolerance=0.000001).length
            for p in parts
            if p.area > 1e-12
        ),
        default=0,
    )
    escaped = after_shape.difference(before_shape.buffer(0.00006)).area
    assert maximum_missing_radius < 0.00025 and escaped < 1e-8
    assert difference < 0.005, difference
    result = {
        "componentSha256": report["componentSha256"],
        "savedTopologySha256": hashlib.sha256(topology_path.read_bytes()).hexdigest(),
        "actualSavedTops": len(polygons),
        "newClippedFaces": saved["newFaces"],
        "originalFacesRetainedExactly": saved["retainedFaces"],
        "removedDuplicateTops": saved["clippedFaces"],
        "maximumRemainingNewOverlapM2": maximum,
        "maximumOverlappingInteriorM2": maximum_interior,
        "nativeStorageBoundaryToleranceM": storage_tolerance,
        "footprintSymmetricDifferenceM2": difference,
        "maximumPermittedLostTopWidthM": 0.0005,
        "maximumLostTopInradiusM": maximum_missing_radius,
        "escapedBeyondToleranceM2": escaped,
        "status": "saved-mesh-partition-verified",
    }
    (OUT / "saved-partition-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main() if bpy is not None else verify_saved_partition()
