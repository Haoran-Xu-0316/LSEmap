"""Independently reopen KGS256 and prove each retained production glyph's pose.

Checks all originals and35rooms, the unchanged opaque mosaic, rigid per-glyph
inverse transforms, original contour topology/UV, zero triangle growth, real
front triangle samples and their backing contact. No source archive is saved.
"""

import array
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_kgs_exterior256 import (
    ADDED,
    BASE,
    CLEARANCE,
    COLLECTION,
    NUMBER_ADDED,
    NUMBER_SOURCE,
    OUT,
    SCALE,
    SHA,
    SOURCE,
    SUPPORT,
    capture,
    protect,
    sha,
    write,
)


def array_hash(collection, attribute, kind, count):
    import hashlib

    values = array.array(kind, [0]) * (len(collection) * count)
    collection.foreach_get(attribute, values)
    return hashlib.sha256(values.tobytes()).hexdigest()


def shape_topology(mesh):
    return {
        "loops": array_hash(mesh.loops, "vertex_index", "i", 1),
        "faceSizes": array_hash(mesh.polygons, "loop_total", "i", 1),
        "materials": array_hash(mesh.polygons, "material_index", "i", 1),
        "uv": {u.name: array_hash(u.data, "uv", "f", 2) for u in mesh.uv_layers},
    }


def main():
    record = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    assert record["body"] == "KING'S CHAMBERS" and record["uniformScale"] == SCALE
    assert all(sha(ROOT / s["path"]) == s["sha256"] for s in record["sources"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    source = bpy.data.objects[SOURCE]
    support = bpy.data.objects[SUPPORT]
    resolution = source.data.resolution_u
    source.data.resolution_u = min(resolution, 4)
    update_scene()
    original_mesh = bpy.data.meshes.new_from_object(
        source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    source.data.resolution_u = resolution
    update_scene()
    assert record["curveResolution"] == {
        "native": resolution,
        "production": min(resolution, 4),
    }
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [ADDED, NUMBER_ADDED]
    appended = {o.name: o for o in loaded.objects}
    assert set(appended) == {ADDED, NUMBER_ADDED}
    for item in appended.values():
        for i, name in enumerate(record["replacementMaterialBindings"][item.name]):
            item.data.materials[i] = bpy.data.materials[name]
        for field, name in (
            record.get("replacementFontBindings", {}).get(item.name, {}).items()
        ):
            assert item.type == "FONT"
            setattr(item.data, field, bpy.data.fonts[name])
        bpy.data.collections[COLLECTION].objects.link(item)
        item.hide_render = False
        set_layer_hidden(item, False)
    # Appending/linking does not immediately update matrix_world from transforms.
    # Force dependency evaluation before comparing the independently saved hash.
    update_scene()
    obj = appended[ADDED]
    number_obj = appended[NUMBER_ADDED]
    for item in appended.values():
        assert object_fingerprint(item) == record["addedFingerprints"][item.name]
    assert object_fingerprint(obj) == record["addedFingerprints"][ADDED]
    assert shape_topology(obj.data) == shape_topology(original_mesh)
    assert (
        len(original_mesh.vertices)
        == len(obj.data.vertices)
        == record["geometryBudget"]["sourceProductionVertices"]
    )
    tris = sum(len(f.vertices) - 2 for f in original_mesh.polygons)
    assert (
        record["geometryBudget"]["sourceProductionTriangles"]
        == record["geometryBudget"]["replacementTriangles"]
        == tris
    )
    original_coords = [v.co.copy() for v in original_mesh.vertices]
    assert (
        max(
            (a - Vector(b)).length
            for a, b in zip(original_coords, record["sourceProductionCoordinates"])
        )
        < 1e-7
    )
    old_depth = min(p.z for p in original_coords)
    all_indices = []
    errors = []
    lifts = []
    samples = []
    normal = (source.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
    # Verify against actual saved backing triangles, not a report-only circle.
    backing = BVHTree.FromPolygons(
        [support.matrix_world @ v.co for v in support.data.vertices],
        [tuple(f.vertices) for f in support.data.polygons],
        all_triangles=False,
    )
    for glyph in record["glyphs"]:
        ids = glyph["vertexIndices"]
        all_indices += ids
        rotation = Matrix.Rotation(-glyph["angleRadians"], 3, "Z")
        for i in ids:
            v = obj.data.vertices[i].co
            q = rotation @ Vector(
                (v.x - glyph["anchorX"], v.y - glyph["baselineLift"], 0)
            )
            recovered = Vector(
                (
                    glyph["sourceCenterX"] + q.x / SCALE,
                    q.y / SCALE,
                    v.z - record["supportLocalDepth"] - CLEARANCE + old_depth,
                )
            )
            errors.append((recovered - original_coords[i]).length)
        tri = [obj.data.vertices[i].co for i in glyph["frontTriangleVertexIndices"]]
        assert (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized().z > 0.99
        point = obj.matrix_world @ (sum(tri, Vector()) / 3)
        assert (point - Vector(glyph["worldFrontTriangleCentroid"])).length < 1e-6
        origin = point + normal * 0.025
        hit = backing.ray_cast(origin, -normal, 0.05)
        assert hit[0] is not None and 0.025 < hit[3] < 0.035
        samples.append(
            {
                "glyph": glyph["index"],
                "supportDistanceMetres": hit[3] - 0.025,
                "actualTriangleIndices": glyph["frontTriangleVertexIndices"],
            }
        )
        lifts.append((glyph["sourceCenterX"], glyph["baselineLift"]))
    assert sorted(all_indices) == list(range(len(obj.data.vertices)))
    assert len(lifts) == 14 and max(errors) < 1e-6
    assert (
        lifts[0][1] > 0.12 and lifts[-1][1] > 0.12 and min(l[1] for l in lifts) < 0.004
    )
    assert record["minimumCircleBoundaryClearanceMetres"] > 0.05
    assert (
        min(v.co.z - record["supportLocalDepth"] for v in obj.data.vertices) > 0.00099
    )
    p = next(
        n
        for n in support.data.materials[0].node_tree.nodes
        if n.type == "BSDF_PRINCIPLED"
    )
    assert (
        p.inputs["Alpha"].default_value == 1
        and p.inputs["Transmission Weight"].default_value == 0
    )
    assert obj.data.materials[0] == source.data.materials[0]
    number_source = bpy.data.objects[NUMBER_SOURCE]
    assert number_obj.type == number_source.type == "FONT"
    assert number_obj.data != number_source.data
    for field in [
        "body",
        "size",
        "extrude",
        "align_x",
        "align_y",
        "space_character",
        "space_word",
        "space_line",
        "resolution_u",
        "bevel_depth",
        "bevel_resolution",
    ]:
        assert getattr(number_obj.data, field) == getattr(number_source.data, field), (
            field
        )
    assert set(record["replacementFontBindings"][NUMBER_ADDED]) == {
        "font",
        "font_bold",
        "font_italic",
        "font_bold_italic",
    }
    for field in record["replacementFontBindings"][NUMBER_ADDED]:
        assert getattr(number_obj.data, field) == getattr(number_source.data, field)
    assert list(number_obj.data.materials) == list(number_source.data.materials)
    assert number_obj.matrix_world == Matrix(record["numbers"]["replacementMatrix"])
    assert (
        max(
            abs(number_obj.matrix_world[i][j] - number_source.matrix_world[i][j])
            for i in range(3)
            for j in range(3)
        )
        < 1e-6
    )
    delta = number_source.matrix_world.to_3x3().inverted() @ (
        number_obj.matrix_world.translation - number_source.matrix_world.translation
    )
    assert abs(delta.x) < 2e-6 and abs(delta.y) < 2e-6
    assert abs(delta.z - record["numbers"]["normalShiftMetres"]) < 2e-6
    number_resolution = number_source.data.resolution_u
    number_source.data.resolution_u = min(number_resolution, 4)
    number_obj.data.resolution_u = min(number_resolution, 4)
    update_scene()
    number_before = bpy.data.meshes.new_from_object(
        number_source.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    number_after = bpy.data.meshes.new_from_object(
        number_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    )
    number_source.data.resolution_u = number_resolution
    number_obj.data.resolution_u = number_resolution
    update_scene()
    assert shape_topology(number_before) == shape_topology(number_after)
    assert (
        len(number_before.vertices)
        == len(number_after.vertices)
        == record["numbers"]["productionVertices"]
    )
    assert (
        max(
            (a.co - b.co).length
            for a, b in zip(number_before.vertices, number_after.vertices)
        )
        < 1e-7
    )
    number_samples = []
    for sample in record["numbers"]["samples"]:
        points = [
            number_after.vertices[i].co for i in sample["frontTriangleVertexIndices"]
        ]
        assert (points[1] - points[0]).cross(
            points[2] - points[0]
        ).normalized().z > 0.99
        point = number_obj.matrix_world @ (sum(points, Vector()) / 3)
        assert (point - Vector(sample["worldFrontTriangleCentroid"])).length < 1e-6
        hit = backing.ray_cast(point + normal * 0.025, -normal, 0.05)
        assert hit[0] is not None and 0.025 < hit[3] < 0.035
        number_samples.append(
            {"glyph": sample["index"], "supportDistanceMetres": hit[3] - 0.025}
        )
    assert len(number_samples) == 4
    number_source.hide_render = True
    set_layer_hidden(number_source, True)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    protect(before, capture())
    visible = [
        o.name
        for o in bpy.data.objects
        if not o.hide_render
        and (
            (o.type == "FONT" and o.data.body == record["body"])
            or o.get("body") == record["body"]
        )
    ]
    assert visible == [ADDED], visible
    visible_numbers = [
        o.name
        for o in bpy.data.objects
        if not o.hide_render
        and (
            (o.type == "FONT" and o.data.body == "29     31")
            or o.get("body") == "29     31"
        )
    ]
    assert visible_numbers == [NUMBER_ADDED], visible_numbers
    assert sha(BASE) == SHA
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "protectedOriginalObjects": len(before["objects"]),
            "protectedMaterialGraphs": len(before["materials"]),
            "protectedRoomStudies": len(before["rooms"]),
            "protectedRoomMembers": sum(len(v) for v in before["rooms"].values()),
            "glyphs": len(lifts),
            "rigidGlyphInverseMaximumErrorMetres": max(errors),
            "everyOriginalProductionVertexRetainedOnce": True,
            "contourTopologyMaterialsAndUVPreserved": True,
            "uniformScale": SCALE,
            "sourceNativeCurveResolutionUnchanged": resolution,
            "sourceProductionCurveResolution": min(resolution, 4),
            "triangleDelta": 0,
            "soleVisibleInscription": visible,
            "unchangedOpaqueBacking": True,
            "frontFaceBackingRays": samples,
            "arcCentreLowerThanEnds": True,
            "allOriginalObjectsAndMaterialGraphsProtected": True,
            "allRoomsAndCampusRoomMembershipsUnchanged": True,
            "baselineBytesUnchanged": True,
            "numberOnlyNormalTranslationVerified": True,
            "numberCurveContourSizeLayoutAndMaterialsUnchanged": True,
            "numberBackingRays": number_samples,
            "numberTriangleDelta": 0,
        },
    )
    print("KGS256_VERIFIED", len(lifts), max(errors), flush=True)


if __name__ == "__main__":
    main()
