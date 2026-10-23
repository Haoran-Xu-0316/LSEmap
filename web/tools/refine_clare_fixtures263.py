"""Add two photographed Clare Market hooded wall fixtures and left conduit.

The undated photographs establish visible physical shapes and two locations,
not their function or present operating state. Dimensions and pipe route remain
photo estimates. Original262geometry/material graphs/35rooms are preserved.
Fixed Blender component builder;no full-campus save or command-line options.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v262.blend"
SHA = "35547bb32309adcd934df8845c71e672e3dc7b3ca519ad5154ec9a65f143cb75"
OUT = ROOT / "result/blender/houghton263"
COLLECTION = "OLD_EXTERIOR"
WALL = "OLD194_STONE_OLD_CLARE165_retained_facade_stone"
BODY = "CLARE263_two_hooded_fixtures_and_left_conduit"
FACE = "CLARE263_recessed_neutral_fixture_faces"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_finish252 import sha


def frame():
    site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    ring = next(b for b in site["buildings"] if b["code"] == "OLD")["rings"][0]
    a, b = Vector((*ring[7], 0)), Vector((*ring[8], 0))
    right = (a - b).normalized()
    return (a + b) / 2, right, Vector((right.y, -right.x, 0)), (b - a).length


def world(x, depth, z):
    origin, right, normal, _length = frame()
    return origin + right * x + normal * depth + Vector((0, 0, z))


def local(p):
    origin, right, normal, _length = frame()
    d = p - origin
    return Vector((d.dot(right), d.dot(normal), p.z))


def capture():
    spec = importlib.util.spec_from_file_location(
        "clare263_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    result = helper.capture_source()
    result["visibility"] = {
        o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
    }
    return result


def tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        all_triangles=True,
    )
    evaluated.to_mesh_clear()
    return result


def support(mesh, x, z):
    normal = frame()[2]
    hit = mesh.ray_cast(world(x, 1, z), -normal, 2)
    assert hit[0] is not None, (x, z)
    assert abs(hit[1].dot(normal)) > 0.99999, (x, z, list(hit[1]))
    return local(hit[0]).y


class Batch:
    def __init__(self, name, material):
        self.name, self.material = name, material
        self.vertices, self.faces, self.records = [], [], []

    def solid(self, points, faces, role):
        offset = len(self.vertices)
        self.vertices.extend(world(*p) for p in points)
        self.faces.extend(tuple(offset + i for i in face) for face in faces)
        self.records.append(
            {"role": role, "vertices": list(range(offset, len(self.vertices)))}
        )

    def box(self, low, high, role):
        points = [
            (x, y, z)
            for x in [low[0], high[0]]
            for y in [low[1], high[1]]
            for z in [low[2], high[2]]
        ]
        self.solid(
            points,
            [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ],
            role,
        )

    def tube(self, path, radius, role):
        points = []
        rings = 12
        path = [Vector(p) for p in path]
        for index, p in enumerate(path):
            tangent = (
                path[min(index + 1, len(path) - 1)] - path[max(index - 1, 0)]
            ).normalized()
            in_plane = Vector((-tangent.z, 0, tangent.x)).normalized()
            for j in range(rings):
                q = (
                    p
                    + Vector((0, 1, 0)) * radius * math.cos(j * math.tau / rings)
                    + in_plane * radius * math.sin(j * math.tau / rings)
                )
                points.append(tuple(q))
        faces = [tuple(reversed(range(rings)))]
        for i in range(len(path) - 1):
            faces.extend(
                (
                    i * rings + j,
                    i * rings + (j + 1) % rings,
                    (i + 1) * rings + (j + 1) % rings,
                    (i + 1) * rings + j,
                )
                for j in range(rings)
            )
        faces.append(tuple((len(path) - 1) * rings + j for j in range(rings)))
        self.solid(points, faces, role)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(self.material)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        uv = mesh.uv_layers.new(name="Metric")
        for loop in mesh.loops:
            p = local(mesh.vertices[loop.vertex_index].co)
            uv.data[loop.index].uv = (p.x, p.z)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj["destinationCollection"] = COLLECTION
        obj["dimensionsEstimated"] = True
        obj["sourceScope"] = (
            "Only two photograph-supported Clare hooded wall fixtures and the visible left conduit;function and current condition unverified"
        )
        return obj


def hood(batch, x, d, z):
    # One closed housing surrounds a real blind recess. The front opening is
    # bounded by four rim faces;there is no coplanar opaque front plate.
    outer_rear = [
        (x - 0.13, d + 0.085, z - 0.05),
        (x + 0.13, d + 0.085, z - 0.05),
        (x + 0.13, d + 0.085, z + 0.12),
        (x - 0.13, d + 0.085, z + 0.12),
    ]
    outer_front = [
        (x - 0.13, d + 0.21, z - 0.07),
        (x + 0.13, d + 0.21, z - 0.07),
        (x + 0.13, d + 0.255, z + 0.07),
        (x - 0.13, d + 0.255, z + 0.07),
    ]
    inner_front = [
        (x - 0.108, d + 0.207, z - 0.047),
        (x + 0.108, d + 0.207, z - 0.047),
        (x + 0.108, d + 0.237, z + 0.047),
        (x - 0.108, d + 0.237, z + 0.047),
    ]
    inner_back = [
        (x - 0.108, d + 0.105, z - 0.025),
        (x + 0.108, d + 0.105, z - 0.025),
        (x + 0.108, d + 0.105, z + 0.080),
        (x - 0.108, d + 0.105, z + 0.080),
    ]
    points = outer_rear + outer_front + inner_front + inner_back
    faces = [(0, 3, 2, 1), (12, 13, 14, 15)]
    for i in range(4):
        j = (i + 1) % 4
        faces.extend(
            [
                (i, j, 4 + j, 4 + i),
                (4 + i, 4 + j, 8 + j, 8 + i),
                (8 + i, 8 + j, 12 + j, 12 + i),
            ]
        )
    batch.solid(points, faces, "closed_hood_with_blind_recess")
    return inner_front


def conduit_path(x, depth):
    left, right = x - 0.33, x + 0.33
    bottom, corner, top = 3.62, 0.05, 5.26
    path = [(left, depth, top), (left, depth, bottom + corner)]
    for step in range(1, 5):
        angle = math.pi + step * math.pi / 8
        path.append(
            (
                left + corner + corner * math.cos(angle),
                depth,
                bottom + corner + corner * math.sin(angle),
            )
        )
    path.append((right - corner, depth, bottom))
    for step in range(1, 5):
        angle = 3 * math.pi / 2 + step * math.pi / 8
        path.append(
            (
                right - corner + corner * math.cos(angle),
                depth,
                bottom + corner + corner * math.sin(angle),
            )
        )
    path.append((right, depth, top))
    return path


def build():
    body = Batch(BODY, bpy.data.materials["OLD178_Houghton_black_post_coating"])
    face = Batch(FACE, bpy.data.materials["OLD_V53_letter"])
    wall = tree(bpy.data.objects[WALL])
    length = frame()[3]
    records = []
    for index, pier in enumerate([1, 4]):
        x = -length / 2 + length * pier / 5
        z = 3.30
        checks = [
            {"x": xx, "z": zz, "wallDepth": support(wall, xx, zz)}
            for xx in [x - 0.07, x, x + 0.07]
            for zz in [z - 0.06, z, z + 0.06]
        ]
        d = max(row["wallDepth"] for row in checks)
        assert d - min(row["wallDepth"] for row in checks) < 0.00004
        body.box(
            (x - 0.075, d + 0.0004, z - 0.065),
            (x + 0.075, d + 0.026, z + 0.065),
            "wall_fixing_plate",
        )
        body.box(
            (x - 0.035, d + 0.026, z - 0.035),
            (x + 0.035, d + 0.085, z + 0.035),
            "short_fixture_bracket",
        )
        front = hood(body, x, d, z)
        # The neutral face sits inside the recess behind its projecting rim.
        corners = [Vector(p) for p in front]
        centre = sum(corners, Vector()) / 4
        pane = [centre + (p - centre) * 0.96 for p in corners]
        pane_normal = Vector((0, 1, -0.319)).normalized()
        front_pane = [p - pane_normal * 0.006 for p in pane]
        back_pane = [p - pane_normal * 0.010 for p in pane]
        points = [tuple(p) for p in front_pane + back_pane]
        face.solid(
            points,
            [
                (0, 1, 2, 3),
                (4, 7, 6, 5),
                (0, 4, 5, 1),
                (1, 5, 6, 2),
                (2, 6, 7, 3),
                (3, 7, 4, 0),
            ],
            "closed_recessed_neutral_face",
        )
        records.append(
            {
                "index": index,
                "pierIndex": pier,
                "x": x,
                "z": z,
                "wallDepth": d,
                "actualWallSupports": checks,
                "rimVertices": front,
                "estimated": True,
            }
        )
    left = records[0]
    path = conduit_path(left["x"], left["wallDepth"] + 0.0084)
    body.tube(path, 0.008, "left_visible_U_conduit")
    pipe_support = []
    for point in [path[0], path[1], path[5], path[6], path[10], path[-1]]:
        depth = support(wall, point[0], point[2])
        pipe_support.append({"point": list(point), "wallDepth": depth})
        assert abs(point[1] - 0.008 - depth - 0.0004) < 0.00004
    objects = [body.finish(), face.finish()]
    return (
        objects,
        records,
        {
            "path": path,
            "radius": 0.008,
            "actualWallSupports": pipe_support,
            "endsAndHiddenContinuation": "Only the photographed exposed U-shaped part is represented;no wiring destination or concealed branch inferred.",
        },
        {body.name: body.records, face.name: face.records},
    )


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), (
        "Review existing candidate before replacement"
    )
    review = json.loads((OUT / "source-review.json").read_text())
    assert all(sha(ROOT / r["path"]) == r["sha256"] for r in review["references"])
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert (
        len(before["objects"]) == 8744
        and len(before["materials"]) == 2355
        and len(before["rooms"]) == 35
    )
    objects, fixtures, conduit, solids = build()
    update_scene()
    after = capture()
    for key in ["objects", "materials", "visibility"]:
        assert all(after[key][name] == row for name, row in before[key].items()), key
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(
        str(component), set(objects), fake_user=True, compress=True
    )
    for obj in objects:
        obj.data.calc_loop_triangles()
    report = {
        "version": 263,
        "building": "OLD",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": COLLECTION,
        "destinationCollection": COLLECTION,
        "addedObjects": [o.name for o in objects],
        "archivedObjects": [],
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in objects},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in objects
        },
        "newMaterials": [],
        "newMaterialGraphs": {},
        "retainNewMaterials": True,
        "fixtures": fixtures,
        "leftConduit": conduit,
        "solidRecords": solids,
        "addedTriangles": sum(len(o.data.loop_triangles) for o in objects),
        "removedDisplayTriangles": 0,
        "sourceReviewSha256": sha(OUT / "source-review.json"),
        "nativeInspectionSha256": sha(OUT / "clare-native-inspection.json"),
        "scope": "Two closed Clare Market hooded wall fixtures at photo-supported piers1and4,actual wall fixing plates,short brackets,recessed neutral face plates,and only the left observed U-shaped conduit. No functional or illumination claim.",
        "limitations": review["limitations"],
    }
    report["netTriangleChange"] = report["addedTriangles"]
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert sha(BASE) == SHA
    print(
        "CLARE263_PHOTOGRAPHED_FIXTURE_COMPONENT_SAVED",
        len(objects),
        report["addedTriangles"],
        flush=True,
    )


if __name__ == "__main__":
    main()
