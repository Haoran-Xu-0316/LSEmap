"""Independently reopen LCH257 and inspect actual letters, support and occluders.

Checks the original15production glyphs by inverse rigid transforms, unchanged
number curve/font and other three identities,1mm backing clearance, actual
front-triangle rays, original materials and35room memberships.
"""

import array
import hashlib
import json
import math
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
from refine_lch_exterior257 import (
    ADDED,
    BASE,
    CLEARANCE,
    COLLECTION,
    NUMBER_ADDED,
    NUMBER_BASELINE,
    NUMBER_SOURCE,
    OUT,
    SHA,
    SOURCE,
    SUPPORT,
    capture,
    evaluated_font,
    fan_frame,
    protect,
    sha,
    write,
)


def buffer_hash(values, field, kind, count):
    data = array.array(kind, [0]) * (len(values) * count)
    values.foreach_get(field, data)
    return hashlib.sha256(data.tobytes()).hexdigest()


def topology(mesh):
    return {
        "loops": buffer_hash(mesh.loops, "vertex_index", "i", 1),
        "faceSizes": buffer_hash(mesh.polygons, "loop_total", "i", 1),
        "materials": buffer_hash(mesh.polygons, "material_index", "i", 1),
        "uv": {u.name: buffer_hash(u.data, "uv", "f", 2) for u in mesh.uv_layers},
    }


def native_trees():
    result = []
    old_ngon = []
    # Font evaluation updates dependency state. Snapshot the RNA collection
    # before those updates so newly appended text objects cannot be skipped.
    for obj in list(bpy.data.collections[COLLECTION].all_objects):
        if obj.hide_render or obj.type not in {"MESH", "FONT", "CURVE"}:
            continue
        temp = None
        if obj.type == "MESH":
            mesh = obj.data
        else:
            mesh, _ = evaluated_font(obj)
            temp = mesh
        points = [obj.matrix_world @ v.co for v in mesh.vertices]
        mesh.calc_loop_triangles()
        result.append(
            (
                obj.name,
                BVHTree.FromPolygons(
                    points,
                    [tuple(t.vertices) for t in mesh.loop_triangles],
                    all_triangles=True,
                ),
            )
        )
        old_ngon.append(
            (
                obj.name,
                BVHTree.FromPolygons(
                    points, [tuple(f.vertices) for f in mesh.polygons]
                ),
            )
        )
        if temp:
            bpy.data.meshes.remove(temp)
    assert {ADDED, NUMBER_ADDED, SUPPORT} <= {name for name, _ in result}
    return result, old_ngon


def probe_hits(sample, trees):
    origin = Vector(sample["worldProbeOrigin"])
    normal = Vector(sample["worldOutwardNormal"])
    hits = []
    for name, tree in trees:
        hit = tree.ray_cast(origin, -normal, 0.05)
        if hit[0] is not None:
            hits.append({"distance": hit[3], "object": name, "point": list(hit[0])})
    return sorted(hits, key=lambda row: row["distance"])


def front_and_support(sample, expected, backing, trees):
    point = Vector(sample["worldFrontTriangleCentroid"])
    normal = Vector(sample["worldOutwardNormal"])
    origin = point + normal * 0.025
    assert (origin - Vector(sample["worldProbeOrigin"])).length < 1e-6
    hits = []
    for name, tree in trees:
        hit = tree.ray_cast(origin, -normal, 0.05)
        if hit[0] is not None:
            hits.append((hit[3], name))
    assert hits, expected
    hit = min(hits)
    assert hit[1] == expected, (expected, hit)
    support = backing.ray_cast(origin, -normal, 0.05)
    assert support[0] is not None
    assert 0.026 < support[3] < 0.030, (expected, support[3])
    return {
        "glyph": sample["index"],
        "expected": expected,
        "firstSurface": hit[1],
        "frontDistance": hit[0],
        "fanlightDistance": support[3],
    }


def main():
    record = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    assert all(
        sha(ROOT / source["path"]) == source["sha256"] for source in record["sources"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    original = bpy.data.objects[SOURCE]
    number_source = bpy.data.objects[NUMBER_SOURCE]
    support = bpy.data.objects[SUPPORT]
    assert original.data.body == "LINCOLN CHAMBERS" and number_source.data.body == "3"
    assert (
        original.name == "LCH_D5_sign.002" and original.matrix_world.translation.z < 3
    )
    original_mesh, native_resolution = evaluated_font(original)
    number_mesh, number_resolution = evaluated_font(number_source)
    frame = fan_frame(original, support)
    assert record["curveResolution"] == {
        "native": native_resolution,
        "production": min(native_resolution, 4),
    }
    assert record["numbers"]["sourceNativeResolution"] == number_resolution
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = [ADDED, NUMBER_ADDED]
    appended = {o.name: o for o in loaded.objects}
    for obj in appended.values():
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        for field, name in (
            record.get("replacementFontBindings", {}).get(obj.name, {}).items()
        ):
            setattr(obj.data, field, bpy.data.fonts[name])
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for source in [original, number_source]:
        source.hide_render = True
        set_layer_hidden(source, True)
    update_scene()
    for obj in appended.values():
        assert object_fingerprint(obj) == record["addedFingerprints"][obj.name], (
            obj.name
        )
    title = appended[ADDED]
    number = appended[NUMBER_ADDED]
    assert title.type == "MESH" and number.type == "FONT"
    assert topology(title.data) == topology(original_mesh)
    assert (
        len(title.data.vertices)
        == len(original_mesh.vertices)
        == record["geometryBudget"]["sourceVertices"]
    )
    assert (
        sum(len(p.vertices) - 2 for p in title.data.polygons)
        == record["geometryBudget"]["sourceAndReplacementTriangles"]
    )
    coordinates = [v.co.copy() for v in original_mesh.vertices]
    assert (
        max(
            (a - Vector(b)).length
            for a, b in zip(coordinates, record["sourceProductionCoordinates"])
        )
        < 1e-7
    )
    old_depth = min(v.z for v in coordinates)
    all_indices = []
    errors = []
    glyph_boxes = []
    for glyph in record["glyphs"]:
        ids = glyph["vertexIndices"]
        all_indices.extend(ids)
        inverse = Matrix.Rotation(glyph["angleRadians"], 3, "Z")
        for index in ids:
            v = title.data.vertices[index].co
            p = inverse @ Vector(
                (v.x - glyph["anchor"][0], v.y - glyph["anchor"][1], 0)
            )
            recovered = Vector(
                (
                    glyph["sourceCenterX"] + p.x / record["uniformInPlaneScale"],
                    p.y / record["uniformInPlaneScale"],
                    v.z - frame["depth"] - CLEARANCE + old_depth,
                )
            )
            errors.append((recovered - coordinates[index]).length)
        points = [title.data.vertices[k].co for k in ids]
        glyph_boxes.append(
            [
                [min(v[a] for v in points) for a in range(2)],
                [max(v[a] for v in points) for a in range(2)],
            ]
        )
        assert (
            min(
                frame["radius"]
                - math.hypot(v.x - frame["centerX"], v.y - frame["springY"])
                for v in points
            )
            > 0.03
        )
        assert min(v.z - frame["depth"] for v in points) > 0.00099
        tri = [title.data.vertices[k].co for k in glyph["frontTriangleVertexIndices"]]
        assert (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized().z > 0.99
        centroid = title.matrix_world @ (sum(tri, Vector()) / 3)
        assert (centroid - Vector(glyph["worldFrontTriangleCentroid"])).length < 1e-6
    assert (
        sorted(all_indices) == list(range(len(title.data.vertices)))
        and len(record["glyphs"]) == 15
    )
    assert max(errors) < 1e-6, max(errors)
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
        assert getattr(number.data, field) == getattr(number_source.data, field), field
    for field in record["replacementFontBindings"][NUMBER_ADDED]:
        assert getattr(number.data, field) == getattr(number_source.data, field), field
    assert list(number.data.materials) == list(number_source.data.materials)
    assert number.matrix_world == Matrix(record["numbers"]["replacementMatrix"])
    assert abs(number.matrix_world.translation.z - NUMBER_BASELINE) < 1e-6
    assert (
        max(
            abs(number.matrix_world[i][j] - number_source.matrix_world[i][j])
            for i in range(3)
            for j in range(3)
        )
        < 1e-6
    )
    number_points = [
        original.matrix_world.inverted() @ (number.matrix_world @ v.co)
        for v in number_mesh.vertices
    ]
    assert min(p.z - frame["depth"] for p in number_points) > 0.00099
    assert max(abs(p.z - frame["depth"] - CLEARANCE) for p in number_points) < 0.0031
    assert (
        min(
            frame["radius"] - math.hypot(v.x - frame["centerX"], v.y - frame["springY"])
            for v in number_points
        )
        > 0.05
    )
    nb = [
        [min(v[a] for v in number_points) for a in range(2)],
        [max(v[a] for v in number_points) for a in range(2)],
    ]
    assert all(
        box[1][0] < nb[0][0]
        or box[0][0] > nb[1][0]
        or box[1][1] < nb[0][1]
        or box[0][1] > nb[1][1]
        for box in glyph_boxes
    ), "Letter/number envelopes overlap"
    number_mesh.calc_loop_triangles()
    for sample in record["numbers"]["samples"]:
        tri = [number_mesh.vertices[k].co for k in sample["frontTriangleVertexIndices"]]
        centroid = number.matrix_world @ (sum(tri, Vector()) / 3)
        assert (centroid - Vector(sample["worldFrontTriangleCentroid"])).length < 1e-6
    support.data.calc_loop_triangles()
    backing = BVHTree.FromPolygons(
        [support.matrix_world @ v.co for v in support.data.vertices],
        [tuple(t.vertices) for t in support.data.loop_triangles],
        all_triangles=True,
    )
    trees, old_ngon = native_trees()
    diagnostics = []
    for sample in record["glyphs"] + record["numbers"]["samples"]:
        diagnostics.append(
            {
                "index": sample["index"],
                "expected": ADDED if sample in record["glyphs"] else NUMBER_ADDED,
                "probeOrigin": sample["worldProbeOrigin"],
                "oldNgonHits": probe_hits(sample, old_ngon),
                "actualRenderedTriangleHits": probe_hits(sample, trees),
            }
        )
    write(
        "native-ray-topology-diagnostic.json",
        {
            "unchangedProbeLocations": True,
            "actualTriangleTrees": [name for name, _ in trees],
            "originalNgonTrees": [name for name, _ in old_ngon],
            "probes": diagnostics,
        },
    )
    rays = [
        front_and_support(glyph, ADDED, backing, trees) for glyph in record["glyphs"]
    ]
    rays.extend(
        front_and_support(sample, NUMBER_ADDED, backing, trees)
        for sample in record["numbers"]["samples"]
    )
    protect(before, capture())
    assert len(rays) == 16
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "savedComponentReopened": True,
            "protectedOriginalObjects": len(before["objects"]),
            "protectedOriginalMaterialGraphs": len(before["materials"]),
            "protectedRoomStudies": len(before["rooms"]),
            "otherThreeFontsPreserved": record["otherOriginalFontsPreserved"],
            "glyphContoursTopologyUVPreserved": True,
            "productionResolution": min(native_resolution, 4),
            "maximumInverseRigidError": max(errors),
            "glyphCount": 15,
            "titleNumberEnvelopesSeparated": True,
            "numberCurveParametersPreserved": True,
            "actualNativeFrontAndSupportRays": rays,
            "triangleGrowth": 0,
            "originalGlazingAndJoineryPreserved": True,
            "visualReviewRequired": True,
        },
    )
    assert sha(BASE) == SHA
    print("LCH257_REOPEN_VERIFIED", len(rays), flush=True)


if __name__ == "__main__":
    main()
