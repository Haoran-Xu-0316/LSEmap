"""Build a bounded native Houghton grade candidate; preserve accepted sources.

Relative profiles are historical evidence. The shared zero datum and transition
collar are authoring estimates; this is not a current topographic survey.
"""

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
BASE_SHA = "b81a627db462ffbd98ca206879fea43d8da018e36edeb2e2bca62c85a2db4589"
OUT = ROOT / "result/blender/houghton-integration243"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from plan_houghton_grade243 import grade_height


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    plan = json.loads((OUT / "grade-plan.json").read_text())
    inventory = json.loads((OUT / "ground-source-geometry.json").read_text())
    protected = json.loads(
        (ROOT / "result/blender/stage243/protected-source-state.json").read_text()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[n]) == r["fingerprint"]
        for n, r in protected["objects"].items()
    )
    collection = bpy.data.collections.new("SITE243_HOUGHTON_GRADE_COMPONENT")
    bpy.context.scene.collection.children.link(collection)
    owned = []
    changes = []
    for row in inventory["objects"]:
        if row["name"] == "SITE216_Expanded_flat_map_datum":
            continue
        source = bpy.data.objects[row["name"]]
        world = source.matrix_world.copy()
        inverse = world.inverted()
        offsets = [grade_height(p[0], p[1]) for p in row["vertices"]]
        if max(offsets, default=0) < 0.00001:
            continue
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = "SITE243_" + source.name
        obj.data.name = obj.name
        collection.objects.link(obj)
        obj["originalObject"] = source.name
        # The integrator restores every source owner, including landscape groups.
        if "destinationCollection" in obj:
            del obj["destinationCollection"]
        obj["scope"] = (
            "Historical relative Houghton grade with estimated datum and transition collar"
        )
        mesh = obj.data
        # Refine only long ground faces crossing the grade field. Inherited
        # grout triangles can span several streets even inside a dense tile
        # batch; warping only their endpoints creates false humps.
        locally_retessellated = (
            row["bounds"]["max"][2] <= 0.1
            and row["bounds"]["max"][2] - row["bounds"]["min"][2] <= 0.06
        )
        if locally_retessellated:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            flag = bm.faces.layers.int.new("houghton243_refine")

            def bounds(face, transform=world):
                points = [transform @ v.co for v in face.verts]
                return (
                    min(p.x for p in points),
                    min(p.y for p in points),
                    max(p.x for p in points),
                    max(p.y for p in points),
                )

            def in_region(box):
                return box[2] > -18 and box[0] < 15 and box[3] > -126 and box[1] < -75

            for face in bm.faces:
                box = bounds(face)
                face[flag] = int(
                    in_region(box) and max(box[2] - box[0], box[3] - box[1]) > 0.75
                )
            for axis, limits in [(1, (-126, -75)), (0, (-18, 15))]:
                world_normal = Vector((1, 0, 0) if axis == 0 else (0, 1, 0))
                normal = world.to_3x3().transposed() @ world_normal
                for step in range(limits[0] * 2, limits[1] * 2 + 1):
                    coordinate = step / 2
                    selected = []
                    for face in bm.faces:
                        if not face[flag]:
                            continue
                        box = bounds(face)
                        if (
                            in_region(box)
                            and box[axis] < coordinate - 1e-7
                            and box[axis + 2] > coordinate + 1e-7
                        ):
                            selected.append(face)
                    if not selected:
                        continue
                    geometry = set(selected)
                    for face in selected:
                        geometry.update(face.edges)
                        geometry.update(face.verts)
                    point = Vector(
                        (coordinate, 0, 0) if axis == 0 else (0, coordinate, 0)
                    )
                    bmesh.ops.bisect_plane(
                        bm,
                        geom=list(geometry),
                        plane_co=inverse @ point,
                        plane_no=normal,
                        dist=1e-7,
                        clear_inner=False,
                        clear_outer=False,
                    )
            bm.faces.layers.int.remove(flag)
            bm.to_mesh(mesh)
            bm.free()
        changed = 0
        maximum = 0
        for vertex in mesh.vertices:
            point = world @ vertex.co
            offset = grade_height(point.x, point.y)
            if offset > 1e-9:
                point.z += offset
                vertex.co = inverse @ point
                changed += 1
                maximum = max(maximum, offset)
        mesh.update()
        if mesh.has_custom_normals:
            mesh.normals_split_custom_set([(0, 0, 0)] * len(mesh.loops))
        owned.append(obj)
        changes.append(
            {
                "source": source.name,
                "replacement": obj.name,
                "vertices": len(mesh.vertices),
                "locallyRetessellated": locally_retessellated,
                "changedVertices": changed,
                "maximumRelativeRiseM": maximum,
                "materials": [m.name if m else None for m in mesh.materials],
                "sourceFingerprint": row["fingerprint"],
            }
        )
    # A thin bed closes inherited gaps between street slabs and facade edges.
    # Its surface sits below both the24mm base roads and40-50mm paving, avoiding
    # coplanar overlaps and keeping source utility covers visible above it.
    vertices = []
    faces = []
    lookup = {}

    def vertex_id(point):
        key = tuple(round(v, 7) for v in point)
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(point)
        return lookup[key]

    edge_counts = {}
    for triangle in plan["coreTriangles"]:
        ids = [vertex_id(tuple(p)) for p in triangle]
        faces.append(ids)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            key = tuple(sorted((a, b)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    top_count = len(vertices)
    vertices.extend(
        [(x, y, z - plan["coreBedThicknessM"]) for x, y, z in vertices.copy()]
    )
    faces.extend([[i + top_count for i in reversed(face)] for face in faces.copy()])
    for (a, b), count in edge_counts.items():
        assert count in [1, 2]
        if count == 1:
            faces.append([a, b, b + top_count, a + top_count])
    mesh = bpy.data.meshes.new("SITE243_Houghton_graded_footway_bed")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assert all(e.is_manifold for e in bm.edges)
    assert abs(bm.calc_volume() - plan["coreAreaM2"] * 0.05) < 0.002
    bm.to_mesh(mesh)
    bm.free()
    material = bpy.data.materials["SITE172_SITE_V47_slab_0_Houghton.001"]
    mesh.materials.append(material)
    uv = mesh.uv_layers.new(name="MetricUV")
    for polygon in mesh.polygons:
        for index in polygon.loop_indices:
            point = mesh.vertices[mesh.loops[index].vertex_index].co
            uv.data[index].uv = (point.x, point.y)
    bed = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(bed)
    bed["destinationCollection"] = "00_SITE"
    bed["scope"] = (
        "Estimated common-datum street bed under retained Houghton paving; relative source slopes only"
    )
    owned.append(bed)
    update_scene()
    assert all(
        object_fingerprint(bpy.data.objects[n]) == r["fingerprint"]
        for n, r in protected["objects"].items()
    )
    path = OUT / "grade-component.blend"
    bpy.data.libraries.write(str(path), {collection}, fake_user=True, compress=True)
    record = {
        "component": str(path.relative_to(ROOT)),
        "componentSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "baselineSha256": BASE_SHA,
        "originalObjectsPreserved": len(protected["objects"]),
        "ownedObjects": [o.name for o in owned],
        "objectFingerprints": {o.name: object_fingerprint(o) for o in owned},
        "archivedObjects": [c["source"] for c in changes],
        "changes": changes,
        "destinationCollection": "00_SITE",
        "replacementMaterialBindings": {
            o.name: [m.name if m else None for m in o.data.materials] for o in owned
        },
        "newObjects": [bed.name],
        "status": "candidate-awaiting-independent-saved-mesh-contact-and-visibility-checks",
        "nativeIntegrated": False,
        "limitations": plan["limitations"],
    }
    (OUT / "grade-component-record.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
    print(
        "HOUGHTON243_COMPONENT",
        len(owned),
        "meshes",
        sum(c["changedVertices"] for c in changes),
        "warped vertices",
        flush=True,
    )


if __name__ == "__main__":
    main()
