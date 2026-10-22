"""Reopen MAR's material-only north-fin correction with full source protection.

Every copied coordinate, topology/UV byte, normal and retained fin group is
compared with the original. Only diffuse/baseRGB changes in the new material.
Actual saved face-triangle probes retain their location and outward direction.
"""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record
from refine_kgs_surface237 import normal_record
from refine_mar_finish258 import (
    BACKGROUND,
    BASE,
    COLLECTION,
    FACTOR,
    FIN,
    MATERIAL,
    OUT,
    SHA,
    TARGETS,
    capture,
    geometry_groups,
    other_material_values_preserved,
    protect,
    sha,
    shader,
    write,
)


def actual_trees():
    trees = []
    for obj in list(bpy.data.collections[COLLECTION].all_objects):
        if obj.type != "MESH" or obj.hide_render:
            continue
        obj.data.calc_loop_triangles()
        trees.append(
            (
                obj.name,
                BVHTree.FromPolygons(
                    [obj.matrix_world @ v.co for v in obj.data.vertices],
                    [tuple(t.vertices) for t in obj.data.loop_triangles],
                    all_triangles=True,
                ),
            )
        )
    return trees


def main():
    record = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    assert (
        sha(ROOT / "result/blender/mar-exterior258/source-review.json")
        == record["sourceReviewSha256"]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(TARGETS.values())
    appended = {o.name: o for o in loaded.objects}
    assert set(appended) == set(TARGETS.values())
    for obj in appended.values():
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for name in TARGETS:
        source = bpy.data.objects[name]
        source.hide_render = True
        set_layer_hidden(source, True)
    update_scene()
    material = bpy.data.materials[MATERIAL]
    background = bpy.data.materials[BACKGROUND]
    original = bpy.data.materials[FIN]
    other_material_values_preserved(material, original)
    base = shader(material).inputs["Base Color"]
    assert not base.is_linked
    actual = list(base.default_value[:3])
    bg = list(shader(background).inputs["Base Color"].default_value[:3])
    assert all(abs(a - b * FACTOR) < 1e-7 for a, b in zip(actual, bg)), (actual, bg)
    assert all(a < b for a, b in zip(actual, bg))
    assert (
        abs(
            base.default_value[3]
            - shader(original).inputs["Base Color"].default_value[3]
        )
        < 1e-7
    )
    assert all(abs(material.diffuse_color[i] - actual[i]) < 1e-7 for i in range(3))
    meshes = []
    for row in record["records"]:
        obj = appended[row["added"]]
        source = bpy.data.objects[row["source"]]
        assert object_fingerprint(obj) == record["addedFingerprints"][obj.name]
        assert obj.data != source.data and obj.data.materials[0] == material
        assert mesh_record(obj) == mesh_record(source) == row["mesh"]
        assert normal_record(obj.data) == normal_record(source.data) == row["normals"]
        groups = geometry_groups(obj)
        assert groups == row["groups"]
        count = 20 if row["source"] == "MAR_D5_north115_fin" else 38
        height = (
            10.6 if count == 20 else 0.5 if "hammerheads" in row["source"] else 11.5
        )
        assert len(groups) == count and all(
            abs(group["height"] - height) < 0.0001 for group in groups
        )
        triangles = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        assert triangles == row["productionTriangles"]
        meshes.append(
            {
                "object": obj.name,
                "source": source.name,
                "groups": len(groups),
                "height": height,
                "triangles": triangles,
                "meshUVAndNormalsIdentical": True,
            }
        )
    trees = actual_trees()
    probes = []
    for row in record["records"]:
        obj = appended[row["added"]]
        for sample in row["worldFaceProbes"]:
            points = [
                obj.matrix_world @ obj.data.vertices[k].co
                for k in sample["triangleVertexIndices"]
            ]
            centroid = sum(points, Vector()) / 3
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            assert (
                centroid - Vector(sample["worldFrontTriangleCentroid"])
            ).length < 1e-6
            assert (normal - Vector(sample["worldOutwardNormal"])).length < 1e-6
            origin = centroid + normal * 0.035
            assert (origin - Vector(sample["worldProbeOrigin"])).length < 1e-6
            hits = []
            for name, tree in trees:
                hit = tree.ray_cast(origin, -normal, 0.07)
                if hit[0] is not None:
                    hits.append((hit[3], name))
            assert hits, (obj.name, sample["index"])
            first = min(hits)
            assert first[1] == obj.name and abs(first[0] - 0.035) < 0.00002, (
                obj.name,
                first,
            )
            probes.append(
                {
                    "object": obj.name,
                    "group": sample["index"],
                    "firstSurface": first[1],
                    "distance": first[0],
                }
            )
    assert len(probes) == 9
    protect(before, capture())
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "savedComponentReopened": True,
            "protectedOriginalObjects": len(before["objects"]),
            "protectedOriginalMaterialGraphs": len(before["materials"]),
            "protectedRoomStudies": len(before["rooms"]),
            "allOtherMaterialValuesAndGraphsPreserved": True,
            "geometryUVNormalsAndModifiersPreserved": True,
            "triangleGrowth": 0,
            "copiedObjects": meshes,
            "backgroundLinearRGB": bg,
            "newFinLinearRGB": actual,
            "estimatedFactor": FACTOR,
            "onlyToneRelationshipCorrected": True,
            "actualNativeFaceProbes": probes,
            "visualReviewRequired": True,
        },
    )
    assert sha(BASE) == SHA
    print("MAR_FINISH258_REOPEN_VERIFIED", len(probes), flush=True)


if __name__ == "__main__":
    main()
