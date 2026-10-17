"""Close bounded Houghton paving gaps without changing entry or furniture levels.

The historical relative grade candidate is retained privately for coordinated
facade work. Its north transition conflicts with accepted OLD access geometry,
so only the level support bed is eligible for this campus integration.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import barycentric_transform

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589"
OUT = ROOT / "result/blender/houghton-footway243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    plan = json.loads(
        (ROOT / "result/blender/houghton-integration243/grade-plan.json").read_text()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    protected = {o.name: object_fingerprint(o) for o in bpy.data.objects}
    vertices, faces, indices, edges = [], [], {}, {}
    for triangle in plan["levelSupport"]["trianglesXY"]:
        face = []
        for x, y in triangle:
            key = (round(x, 8), round(y, 8))
            if key not in indices:
                indices[key] = len(vertices)
                vertices.append((x, y, 0.018))
            face.append(indices[key])
        faces.append(face)
        for a, b in zip(face, face[1:] + face[:1]):
            key = tuple(sorted((a, b)))
            edges[key] = edges.get(key, 0) + 1
    count = len(vertices)
    vertices.extend([(x, y, z - 0.05) for x, y, z in vertices.copy()])
    faces.extend([[i + count for i in reversed(face)] for face in faces.copy()])
    for (a, b), used in edges.items():
        assert used in [1, 2]
        if used == 1:
            faces.append([a, b, b + count, a + count])
    mesh = bpy.data.meshes.new("SITE243_Houghton_paving_support")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assert all(e.is_manifold for e in bm.edges)
    assert (
        abs(bm.calc_volume(signed=True) - plan["levelSupport"]["areaM2"] * 0.05) < 0.002
    )
    bm.to_mesh(mesh)
    bm.free()
    material = bpy.data.materials["SITE172_SITE_V47_slab_0_Houghton.001"]
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="MetricUV")
    for face in mesh.polygons:
        for index in face.loop_indices:
            point = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = (point.x, point.y)
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection = bpy.data.collections.new("SITE243_HOUGHTON_FOOTWAY_COMPONENT")
    bpy.context.scene.collection.children.link(collection)
    collection.objects.link(obj)
    obj["destinationCollection"] = "00_SITE"
    obj["scope"] = (
        "Estimated support below retained Houghton paving; no terrain grade change"
    )
    paving_plan = plan["pavingRepair"]
    source = bpy.data.objects[paving_plan["source"]]
    replacement = source.copy()
    replacement.data = source.data.copy()
    replacement.name = "SITE243_Houghton_paving_nonoverlapping_edges"
    replacement.data.name = replacement.name
    replacement["originalObject"] = source.name
    replacement["destinationCollection"] = "00_SITE"
    replacement["scope"] = paving_plan["scope"]
    collection.objects.link(replacement)
    bm = bmesh.new()
    bm.from_mesh(replacement.data)
    bm.faces.ensure_lookup_table()
    source_index = bm.faces.layers.int.new("sourceFace243")
    for face in bm.faces:
        face[source_index] = face.index
    uv_layers = [
        (layer, bm.loops.layers.uv[layer.name]) for layer in source.data.uv_layers
    ]
    source_faces = list(bm.faces)
    inverse = source.matrix_world.inverted()
    for repair in paving_plan["repairs"]:
        original = source.data.polygons[repair["sourceFace"]]
        assert len(original.vertices) == 3
        corners = [
            source.matrix_world @ source.data.vertices[i].co for i in original.vertices
        ]
        source_uv = [
            [Vector((*layer.data[i].uv, 0)) for i in original.loop_indices]
            for layer, _ in uv_layers
        ]
        for triangle in repair["trianglesXY"]:
            points = [Vector((x, y, 0.05)) for x, y in triangle]
            if (points[1] - points[0]).cross(points[2] - points[0]).z < 0:
                points.reverse()
            face = bm.faces.new([bm.verts.new(inverse @ point) for point in points])
            face.material_index = original.material_index
            face[source_index] = -1
            for loop, point in zip(face.loops, points):
                for (_, layer), values in zip(uv_layers, source_uv):
                    loop[layer].uv = barycentric_transform(point, *corners, *values).xy
    bmesh.ops.delete(
        bm,
        geom=[source_faces[r["sourceFace"]] for r in paving_plan["repairs"]],
        context="FACES_ONLY",
    )
    bm.normal_update()
    bm.to_mesh(replacement.data)
    bm.free()
    owned = [obj, replacement]
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[n]) == value
        for n, value in protected.items()
    )
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "component.blend"
    bpy.data.libraries.write(str(path), {collection}, fake_user=True, compress=True)
    report = {
        "baselineSha256": BASE_SHA,
        "component": str(path.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "addedObjects": [o.name for o in owned],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in owned},
        "archivedObjects": [source.name],
        "replacementMaterialBindings": {
            o.name: [m.name if m else None for m in o.data.materials] for o in owned
        },
        "pavingRepair": paving_plan,
        "coreAreaM2": plan["levelSupport"]["areaM2"],
        "coreTrianglesXY": [
            [[p[0], p[1]] for p in t] for t in plan["levelSupport"]["trianglesXY"]
        ],
        "retainedStreetLevels": True,
        "gradeCandidateAccepted": False,
        "reasonGradeDeferred": "Relative historical profiles lack a common datum; current transition buries OLD lower steps and two street bollard bases.",
        "scope": "Close inherited Houghton paving gaps and clip overlapping coplanar edge tops; retain original geometry privately and preserve all entry, room and street fixture levels",
        "status": "candidate-awaiting-independent-saved-mesh-and-visual-checks",
    }
    (OUT / "candidate.json").write_text(json.dumps(report, indent=2) + "\n")
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print(
        "HOUGHTON243_LEVEL_SUPPORT_SAVED",
        round(plan["levelSupport"]["areaM2"], 3),
        flush=True,
    )


if __name__ == "__main__":
    main()
