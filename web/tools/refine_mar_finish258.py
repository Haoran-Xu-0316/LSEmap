"""Correct the documented darker tone of MAR's retained north concrete fins.

Only three isolated object/mesh copies and one material copy are made. The new
linearRGB is94%of the backing panelRGB as a restrained display estimate. This
is not a measured reflectance and does not reconstruct the inward colour fade.
"""

import importlib.util
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
SHA = "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"
OUT = ROOT / "result/blender/mar-finish258"
COLLECTION = "MAR_EXTERIOR"
FIN = "MAR_V115_fin"
BACKGROUND = "MAR_V75_concrete"
MATERIAL = "MAR_FINISH258_slightly_darker_north_concrete"
FACTOR = 0.94
TARGETS = {
    "MAR_V115_retained_D5_NEXT_upper_screen_shafts": "MAR_FINISH258_upper_screen_shafts",
    "MAR_V115_retained_D5_NEXT_upper_screen_hammerheads": "MAR_FINISH258_upper_screen_hammerheads",
    "MAR_D5_north115_fin": "MAR_FINISH258_north_lower_fins",
}
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    geometry_policy_name,
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha
from refine_kgs_surface237 import normal_record
from refine_portsmouth_exterior207 import material_fingerprint


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "mar258_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def shader(material):
    return next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def protect(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in TARGETS:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def other_material_values_preserved(candidate, source):
    """Reset only the two allowed colour fields on a disposable copy as witness."""
    witness = candidate.copy()
    witness.diffuse_color = source.diffuse_color
    shader(witness).inputs["Base Color"].default_value = (
        shader(source).inputs["Base Color"].default_value
    )
    match = material_fingerprint(witness) == material_fingerprint(source)
    bpy.data.materials.remove(witness)
    assert match, "A material value besides diffuse/base colour changed"


def components(mesh):
    adjacency = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacency[a].add(b)
        adjacency[b].add(a)
    pending = set(range(len(adjacency)))
    result = []
    while pending:
        seed = pending.pop()
        part = {seed}
        stack = [seed]
        while stack:
            for index in adjacency[stack.pop()] & pending:
                pending.remove(index)
                part.add(index)
                stack.append(index)
        result.append(sorted(part))
    return sorted(
        result, key=lambda ids: sum(mesh.vertices[k].co.x for k in ids) / len(ids)
    )


def geometry_groups(obj):
    rows = []
    for ids in components(obj.data):
        points = [obj.matrix_world @ obj.data.vertices[k].co for k in ids]
        rows.append(
            {
                "vertexIndices": ids,
                "worldBounds": [
                    [min(p[a] for p in points) for a in range(3)],
                    [max(p[a] for p in points) for a in range(3)],
                ],
                "height": max(p.z for p in points) - min(p.z for p in points),
            }
        )
    return rows


def face_probes(obj):
    obj.data.calc_loop_triangles()
    groups = components(obj.data)
    result = []
    north = Vector((0, 1, 0))
    for index in sorted({0, len(groups) // 2, len(groups) - 1}):
        ids = set(groups[index])
        candidates = []
        for triangle in obj.data.loop_triangles:
            if not set(triangle.vertices) <= ids:
                continue
            points = [
                obj.matrix_world @ obj.data.vertices[k].co for k in triangle.vertices
            ]
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            if normal.dot(north) > 0.8:
                candidates.append((triangle.area, triangle, points, normal))
        assert candidates, (obj.name, index)
        _, triangle, points, normal = max(candidates, key=lambda row: row[0])
        centroid = sum(points, Vector()) / 3
        result.append(
            {
                "index": index,
                "object": obj.name,
                "triangleVertexIndices": list(triangle.vertices),
                "worldFrontTriangleCentroid": list(centroid),
                "worldOutwardNormal": list(normal),
                "worldProbeOrigin": list(centroid + normal * 0.035),
            }
        )
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), (
        "Review existing candidate before replacement"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    source_material = bpy.data.materials[FIN]
    background = bpy.data.materials[BACKGROUND]
    old = shader(source_material).inputs["Base Color"]
    back = shader(background).inputs["Base Color"]
    assert not old.is_linked and not back.is_linked
    old_rgb = tuple(old.default_value[:3])
    background_rgb = tuple(back.default_value[:3])
    assert all(a > b for a, b in zip(old_rgb, background_rgb)), (
        old_rgb,
        background_rgb,
    )
    expected = tuple(v * FACTOR for v in background_rgb)
    material = source_material.copy()
    material.name = MATERIAL
    material.diffuse_color = (*expected, source_material.diffuse_color[3])
    shader(material).inputs["Base Color"].default_value = (
        *expected,
        old.default_value[3],
    )
    other_material_values_preserved(material, source_material)
    owned = []
    records = []
    for source_name, target_name in TARGETS.items():
        source = bpy.data.objects[source_name]
        assert not source.hide_render and source.type == "MESH"
        assert (
            len(source.data.materials) == 1
            and source.data.materials[0] == source_material
        )
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = target_name
        obj.data.name = target_name
        obj["originalObject"] = source_name
        obj["webGeometrySource"] = geometry_policy_name(source)
        obj["destinationCollection"] = COLLECTION
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj.data.materials[0] = material
        assert mesh_record(obj) == mesh_record(source), source_name
        assert normal_record(obj.data) == normal_record(source.data), source_name
        groups = geometry_groups(obj)
        expected_count = 20 if source_name == "MAR_D5_north115_fin" else 38
        assert len(groups) == expected_count, (source_name, len(groups))
        expected_height = (
            10.6
            if expected_count == 20
            else 0.5
            if "hammerheads" in source_name
            else 11.5
        )
        assert all(abs(g["height"] - expected_height) < 0.0001 for g in groups)
        records.append(
            {
                "source": source_name,
                "added": target_name,
                "mesh": mesh_record(obj),
                "normals": normal_record(obj.data),
                "groups": groups,
                "worldFaceProbes": face_probes(obj),
                "productionTriangles": sum(
                    len(p.vertices) - 2 for p in obj.data.polygons
                ),
            }
        )
        owned.append(obj)
        source.hide_render = True
        set_layer_hidden(source, True)
    update_scene()
    after = capture()
    protect(before, after)
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    source_review = json.loads(
        (ROOT / "result/blender/mar-exterior258/source-review.json").read_text()
    )
    write(
        "audit.json",
        {
            "version": 258,
            "code": "MAR",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "targetCollection": COLLECTION,
            "destinationCollection": COLLECTION,
            "addedObjects": [o.name for o in owned],
            "archivedObjects": list(TARGETS),
            "changedObjects": [],
            "addedFingerprints": {o.name: object_fingerprint(o) for o in owned},
            "replacementMaterialBindings": {o.name: [MATERIAL] for o in owned},
            "newMaterials": [MATERIAL],
            "newMaterialGraphs": {MATERIAL: after["materials"][MATERIAL]},
            "records": records,
            "colour": {
                "sourceFin": FIN,
                "sourceBackground": BACKGROUND,
                "newMaterial": MATERIAL,
                "originalFinLinearRGB": old_rgb,
                "backgroundLinearRGB": background_rgb,
                "estimatedFactor": FACTOR,
                "newFinLinearRGB": list(
                    shader(material).inputs["Base Color"].default_value[:3]
                ),
                "interpretation": "Fins slightly darker than backing window panels. Factor.94is an uncalibrated restrained display estimate, not measured reflectance.",
            },
            "sourceReview": source_review,
            "sourceReviewSha256": sha(
                ROOT / "result/blender/mar-exterior258/source-review.json"
            ),
            "geometryPreserved": {
                "upperShafts": 38,
                "upperHeight": 11.5,
                "hammerheads": 38,
                "lowerFins": 20,
                "lowerHeight": 10.6,
                "triangleGrowth": 0,
            },
            "limitations": [
                "Concrete Quarterly Summer2022built-facade technical account is not a2026condition survey.",
                "Only slight darker overall fin tone is corrected. The described inward fade is not reconstructed without independent face registration.",
                "No geometry, UV, normals, modifier, roughness, links, texture, glass, other material graphs, other building objects or35rooms changed.",
            ],
            "status": "saved_awaiting_independent_reopen_and_production_review",
        },
    )
    assert sha(BASE) == SHA
    print("MAR_FINISH258_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
