"""Remove the unsupported continuous belt course from Cowdray's short street side.

Existing contractor and LSE photographs show brick continuing between the
short-side ground and upper windows. The generic heritage builder mistakenly
repeated the long-side stone belt on every elevation. Only that independent box
is removed; corner portal, long side, upper cornices and all interiors remain.
The previously proposed rainwater pipe was rejected and is not part of this work.
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

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v254.blend"
SHA = "47db5d164487cc7d5f87c4c6f0df47b4800238cb16e650ce1325e6db99f97140"
OUT = ROOT / "result/blender/cow255"
COLLECTION = "COW_EXTERIOR"
SOURCE = "COW217_COW_D5_layered_cornice_trim"
REPLACEMENT = "COW255_cornices_without_short_street_false_belt"
HEAD_SOURCE = "COW217_COW_NEXT_ground_partition_heads"
HEAD_REPLACEMENT = "COW255_short_street_brick_head_continuous_joints"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import mesh_record, sha
from refine_kgs_surface237 import normal_record


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "cow255_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def registration():
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    ring = next(b["rings"][0] for b in site["buildings"] if b["code"] == "COW")
    start, end = [Vector((*ring[i], 0)) for i in (5, 6)]
    tangent = (end - start).normalized()
    return start, end, tangent, Vector((-tangent.y, tangent.x, 0))


def components(obj):
    neighbors = {v.index: set() for v in obj.data.vertices}
    for edge in obj.data.edges:
        a, b = edge.vertices
        neighbors[a].add(b)
        neighbors[b].add(a)
    result, visited = [], set()
    for seed in neighbors:
        if seed in visited:
            continue
        part, pending = set(), [seed]
        visited.add(seed)
        while pending:
            current = pending.pop()
            part.add(current)
            for adjacent in neighbors[current]:
                if adjacent not in visited:
                    visited.add(adjacent)
                    pending.append(adjacent)
        result.append(part)
    return result


def find_short_belt(obj):
    """Require an entire independently connected box in the registered wall plane."""
    start, end, tangent, normal = registration()
    length = (end - start).length
    matches = []
    for indices in components(obj):
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in indices]
        along = [(p - start).dot(tangent) for p in points]
        depth = [(p - start).dot(normal) for p in points]
        height = [p.z for p in points]
        if (
            abs(min(along) + 0.04) < 2e-5
            and abs(max(along) - length - 0.04) < 2e-5
            and abs(min(depth) + 0.145) < 2e-5
            and abs(max(depth) - 0.345) < 2e-5
            and abs(min(height) - 4.785) < 2e-5
            and abs(max(height) - 5.015) < 2e-5
        ):
            matches.append(indices)
    assert len(matches) == 1, (
        "Expected one independent short-street belt",
        len(matches),
    )
    indices = matches[0]
    faces = [
        p.index for p in obj.data.polygons if all(i in indices for i in p.vertices)
    ]
    assert len(indices) == 8 and len(faces) == 6, (len(indices), len(faces))
    return indices, faces


def face_records(obj):
    """Compare every retained corner coordinate, UV, split normal and material."""
    mesh = obj.data
    mesh.update()
    result = []
    for face in mesh.polygons:
        corners = []
        for index in face.loop_indices:
            loop = mesh.loops[index]
            corners.append(
                {
                    "position": list(mesh.vertices[loop.vertex_index].co),
                    "normal": list(mesh.corner_normals[index].vector),
                    "uv": {uv.name: list(uv.data[index].uv) for uv in mesh.uv_layers},
                }
            )
        rotations = [corners[i:] + corners[:i] for i in range(len(corners))]
        canonical = min(json.dumps(row, sort_keys=True) for row in rotations)
        result.append(
            hashlib.sha256(
                json.dumps(
                    {
                        "corners": canonical,
                        "material": face.material_index,
                        "smooth": face.use_smooth,
                        "normal": list(face.normal),
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()
        )
    return result


def verify_remainder(source, obj, removed_faces):
    before = face_records(source)
    expected = [row for i, row in enumerate(before) if i not in removed_faces]
    actual = face_records(obj)
    assert Counter(actual) == Counter(expected), "Retained face data changed"
    assert [m.name for m in source.data.materials] == [
        m.name for m in obj.data.materials
    ]
    assert [list(row) for row in obj.matrix_world] == [
        list(row) for row in source.matrix_world
    ]
    assert source.data.uv_layers.active.name == obj.data.uv_layers.active.name
    assert [uv.name for uv in source.data.uv_layers if uv.active_render] == [
        uv.name for uv in obj.data.uv_layers if uv.active_render
    ]
    return {
        "originalFaces": len(before),
        "retainedFaces": len(actual),
        "removedFaces": len(removed_faces),
        "retainedFaceRecordSha256": hashlib.sha256(
            json.dumps(sorted(actual)).encode()
        ).hexdigest(),
    }


def check_protection(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in [SOURCE, HEAD_SOURCE]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == value for name, value in before["materials"].items()
    )
    for field in ["rooms", "campusRooms"]:
        assert after[field] == before[field]
    assert len(before["rooms"]) == 35


def short_head_parts(obj):
    start, end, tangent, normal = registration()
    pitch = (end - start).length / 5
    found = []
    for indices in components(obj):
        points = [obj.matrix_world @ obj.data.vertices[i].co for i in indices]
        heights = [p.z for p in points]
        depths = [(p - start).dot(normal) for p in points]
        along = [(p - start).dot(tangent) for p in points]
        if abs(min(heights) - 4.27) > 2e-5 or abs(max(heights) - 4.9) > 2e-5:
            continue
        if abs(min(depths) + 0.35) > 2e-5 or abs(max(depths) - 0.01) > 2e-5:
            continue
        bay = round(min(along) / pitch)
        if (
            0 <= bay < 5
            and abs(min(along) - bay * pitch) < 2e-5
            and abs(max(along) - (bay + 1) * pitch) < 2e-5
        ):
            assert len(indices) == 8
            found.append((bay, indices))
    assert sorted(bay for bay, _ in found) == list(range(5)), found
    return found


def source_head_is_target(point):
    start, end, tangent, normal = registration()
    along, depth = (point - start).dot(tangent), (point - start).dot(normal)
    return (
        -0.00002 <= along <= (end - start).length + 0.00002
        and -0.35002 <= depth <= 0.01002
        and 4.26998 <= point.z <= 4.90002
    )


def evaluated_other_head_records(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh(
        preserve_all_data_layers=True, depsgraph=bpy.context.evaluated_depsgraph_get()
    )
    # A temporary datablock wrapper is sufficient; no source data is changed.
    wrapper = bpy.data.objects.new("COW255_evaluated_record_only", mesh.copy())
    wrapper.matrix_world = obj.matrix_world.copy()
    records = face_records(wrapper)
    retained = [
        record
        for face, record in zip(wrapper.data.polygons, records)
        if not source_head_is_target(wrapper.matrix_world @ face.center)
    ]
    data = wrapper.data
    bpy.data.objects.remove(wrapper)
    bpy.data.meshes.remove(data)
    evaluated.to_mesh_clear()
    return Counter(retained)


def correct_head_joints(source):
    parts = short_head_parts(source)
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = HEAD_REPLACEMENT
    obj.data.name = HEAD_REPLACEMENT + "_mesh"
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["originalObject"] = HEAD_SOURCE
    obj["webGeometrySource"] = source.get("webGeometrySource", HEAD_SOURCE)
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Retain wall/UV/apertures; cancel bevel only on four internal short-street head interfaces"
    )
    assert len(source.modifiers) == 1
    before_modifier = source.modifiers[0]
    assert before_modifier.type == "BEVEL" and before_modifier.limit_method == "ANGLE"
    assert abs(before_modifier.width - 0.012) < 1e-7
    assert not source.data.attributes.get("bevel_weight_edge")
    weights = obj.data.attributes.new(
        name="bevel_weight_edge", type="FLOAT", domain="EDGE"
    )
    for value in weights.data:
        value.value = 1
    start, end, tangent, _normal = registration()
    pitch = (end - start).length / 5
    selected = []
    part_vertices = set().union(*(indices for _, indices in parts))
    for edge in obj.data.edges:
        if not all(index in part_vertices for index in edge.vertices):
            continue
        coordinates = [
            (obj.matrix_world @ obj.data.vertices[index].co - start).dot(tangent)
            for index in edge.vertices
        ]
        if any(
            all(
                abs(coordinate - interface * pitch) < 2e-5 for coordinate in coordinates
            )
            for interface in range(1, 5)
        ):
            weights.data[edge.index].value = 0
            selected.append(edge.index)
    assert len(selected) == 32, selected
    obj.modifiers[0].limit_method = "WEIGHT"
    if hasattr(obj.modifiers[0], "edge_weight"):
        obj.modifiers[0].edge_weight = "bevel_weight_edge"
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    assert mesh_record(source) == mesh_record(obj)
    assert normal_record(source.data) == normal_record(obj.data)
    assert evaluated_other_head_records(source) == evaluated_other_head_records(obj), (
        "Other elevations changed after explicit bevel weighting"
    )
    return obj, selected


def wall_join_rays():
    from mathutils.bvhtree import BVHTree

    surfaces = []
    for obj in bpy.data.collections[COLLECTION].all_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        materials = [
            mesh.materials[mesh.polygons[t.polygon_index].material_index].name
            for t in mesh.loop_triangles
        ]
        surfaces.append(
            (
                obj.name,
                BVHTree.FromPolygons(vertices, triangles, all_triangles=True),
                materials,
            )
        )
        evaluated.to_mesh_clear()
    start, end, tangent, normal = registration()
    rows = []
    for fraction in [0.2, 0.4, 0.5, 0.6, 0.8]:
        for height in [4.888, 4.889, 4.895, 4.899, 4.8999, 4.9, 4.9001]:
            for delta in [-0.0001, 0, 0.0001]:
                origin = (
                    start
                    + tangent * ((end - start).length * fraction + delta)
                    + normal * 0.7
                    + Vector((0, 0, height))
                )
                hits = []
                for name, tree, materials in surfaces:
                    hit, _normal, index, distance = tree.ray_cast(origin, -normal, 1.5)
                    if hit is not None:
                        hits.append((distance, name, materials[index]))
                assert hits, (fraction, height, delta)
                distance, name, material = min(hits)
                assert 0.68 < distance < 0.72 and "brick" in material.lower(), (
                    fraction,
                    height,
                    delta,
                    distance,
                    name,
                    material,
                )
                rows.append(
                    {
                        "fraction": fraction,
                        "height": height,
                        "alongDeltaMetres": delta,
                        "distance": distance,
                        "object": name,
                        "material": material,
                    }
                )
    return rows


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists(), (
        "Inspect existing candidate before replacing"
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    protected = capture()
    write("protected-source-state.json", protected)
    source = bpy.data.objects[SOURCE]
    assert source.type == "MESH" and not source.hide_render
    assert not source.data.has_custom_normals
    vertices, removed_faces = find_short_belt(source)
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = REPLACEMENT
    obj.data.name = REPLACEMENT + "_mesh"
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = SOURCE
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Photographed short-street brick continuation; only unsupported4.9mcontinuous belt removed"
    )
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in vertices], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    update_scene()
    remainder = verify_remainder(source, obj, removed_faces)
    head, cancelled_edges = correct_head_joints(bpy.data.objects[HEAD_SOURCE])
    ray_proof = wall_join_rays()
    check_protection(protected, capture())
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj, head}, fake_user=True, compress=True)
    sources = []
    for local, url in [
        (
            "data/collections/campus_photos_round2/images/COW/COW_cow_russell_05.jpg",
            "https://www.russellcawberry.com/projects/cowdray-house",
        ),
        (
            "data/建筑图片/COW_Cowdray House/01_建筑实拍/exteriors_lse_estate_006.jpg",
            "https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate",
        ),
    ]:
        sources.append(
            {
                "path": local,
                "sha256": sha(ROOT / local),
                "url": url,
                "date": "Contractor project2019; estate photo undated; capture dates unknown",
                "supports": "Brick continues between short-side ground and upper windows; long-side continuous white belt does not wrap the short side",
            }
        )
    write(
        "audit.json",
        {
            "version": 255,
            "building": "COW",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "addedObjects": [REPLACEMENT, HEAD_REPLACEMENT],
            "archivedObjects": [SOURCE, HEAD_SOURCE],
            "changedObjects": [],
            "addedFingerprints": {
                REPLACEMENT: object_fingerprint(obj),
                HEAD_REPLACEMENT: object_fingerprint(head),
            },
            "replacementMaterialBindings": {
                REPLACEMENT: [m.name for m in obj.data.materials],
                HEAD_REPLACEMENT: [m.name for m in head.data.materials],
            },
            "newMaterials": [],
            "newMaterialGraphs": {},
            "retainNewMaterials": True,
            "removedSourceVertices": sorted(vertices),
            "removedSourceFaces": removed_faces,
            "retainedFaceProof": remainder,
            "headBevel": {
                "sourceLimitMethod": bpy.data.objects[HEAD_SOURCE]
                .modifiers[0]
                .limit_method,
                "candidateLimitMethod": head.modifiers[0].limit_method,
                "width": head.modifiers[0].width,
                "segments": head.modifiers[0].segments,
                "weightAttribute": "bevel_weight_edge",
                "weights": [
                    value.value
                    for value in head.data.attributes["bevel_weight_edge"].data
                ],
                "weightsSha256": hashlib.sha256(
                    json.dumps(
                        [
                            value.value
                            for value in head.data.attributes["bevel_weight_edge"].data
                        ]
                    ).encode()
                ).hexdigest(),
                "geometryPolicySource": head["webGeometrySource"],
            },
            "cancelledInternalBevelEdges": cancelled_edges,
            "headGeometryUVNormalsPreserved": True,
            "otherElevationEvaluatedHeadsExact": True,
            "savedEvaluatedJoinRays": ray_proof,
            "registeredStreetSegment": 5,
            "removedHeightRangeMetres": [4.785, 5.015],
            "removedTriangles": 12,
            "sources": sources,
            "rejectedPipeCandidate": "result/blender/cow255/rejection.json",
            "limitations": [
                "Sources are historical/undated rather than a2026site survey.",
                "Remove unsupported generic stone belt and cancel internal short-street head bevels only; original wall vertices, UVs and apertures retained. No new brick geometry or surfaces.",
                "No rainwater pipe is created. Roof, upper cornices, long side, corner portal, glazing and35room studies remain unchanged.",
            ],
        },
    )
    assert sha(BASE) == SHA
    print("COW255_SHORT_BELT_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
