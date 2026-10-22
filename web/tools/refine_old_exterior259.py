"""Restore eight photo-supported Houghton window boxes in three shared batches.

Window axes and bearing heights come from accepted258 glass/sill components.
Box dimensions and planting silhouettes are display estimates. Existing walls,
windows, entrance, roof, original materials and35 room studies remain unchanged.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v258.blend"
SHA = "46a6d58baf708af45c8a8669f85fa6b24efdbfb1d3721cd4aca315e85ba0d835"
OUT = ROOT / "result/blender/old259"
COLLECTION = "OLD_EXTERIOR"
GLASS = "GLASS181_OLD_D5_houghton112_middle_glass"
STONE = "OLD194_STONE_OLD_D5_houghton112_middle_stone"
BINDINGS = {
    "OLD259_Houghton_window_boxes": "OLD178_Houghton_black_post_coating",
    "OLD259_Houghton_window_box_soil": "OLD_V53_soil",
    "OLD259_Houghton_window_box_planting": "OLD_NEXT_OLD_NEXT_STUDENT_green",
}
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_col_finish252 import sha


def capture():
    spec = importlib.util.spec_from_file_location(
        "old259_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def frame():
    record = json.loads(
        (ROOT / "result/blender/stage52/old-houghton-audit.json").read_text()
    )
    return [Vector(record[key]) for key in ["origin", "right", "outward"]]


def connected(mesh):
    adjacent = [set() for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        adjacent[a].add(b)
        adjacent[b].add(a)
    unseen, groups = set(range(len(mesh.vertices))), []
    while unseen:
        seed = unseen.pop()
        group, stack = [seed], [seed]
        while stack:
            for other in adjacent[stack.pop()] & unseen:
                unseen.remove(other)
                stack.append(other)
                group.append(other)
        groups.append(sorted(group))
    return groups


def local(point):
    origin, right, outward = frame()
    delta = point - origin
    return [delta.dot(right), delta.dot(outward), point.z]


def registered_windows():
    obj = bpy.data.objects[GLASS]
    windows = []
    for group in connected(obj.data):
        points = [local(obj.matrix_world @ obj.data.vertices[i].co) for i in group]
        bounds = [
            [min(p[d] for p in points), max(p[d] for p in points)] for d in range(3)
        ]
        if abs(bounds[2][0] - 4.48) < 1e-5 or abs(bounds[2][0] - 8.32) < 1e-5:
            windows.append(
                {
                    "x": sum(bounds[0]) / 2,
                    "low": bounds[2][0],
                    "high": bounds[2][1],
                    "width": bounds[0][1] - bounds[0][0],
                    "sourceGlassVertices": group,
                }
            )
    windows.sort(key=lambda w: (w["low"], w["x"]))
    assert len(windows) == 20
    selected = [
        w
        for low in [4.48, 8.32]
        for w in [x for x in windows if abs(x["low"] - low) < 1e-5][:4]
    ]
    assert len(selected) == 8
    return selected


class Batch:
    def __init__(self, name):
        self.name, self.vertices, self.faces = name, [], []
        self.origin, self.right, self.outward = frame()

    def add(self, points, faces):
        offset = len(self.vertices)
        self.vertices += [
            self.origin + self.right * p[0] + self.outward * p[1] + Vector((0, 0, p[2]))
            for p in points
        ]
        self.faces += [tuple(i + offset for i in face) for face in faces]

    def box(self, lo, hi):
        points = [
            (x, y, z)
            for z in [lo[2], hi[2]]
            for y in [lo[1], hi[1]]
            for x in [lo[0], hi[0]]
        ]
        self.add(
            points,
            [
                (0, 2, 3, 1),
                (4, 5, 7, 6),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 4, 6, 2),
                (1, 3, 7, 5),
            ],
        )

    def finish(self):
        mesh = bpy.data.meshes.new(self.name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(bpy.data.materials[BINDINGS[self.name]])
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        uv = mesh.uv_layers.new(name="Metric")
        for loop in mesh.loops:
            point = mesh.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = point.xy
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj["destinationCollection"] = COLLECTION
        obj["sourceScope"] = (
            "Eight near Houghton window boxes visible in undated user photograph; dimensions and foliage estimated"
        )
        return obj


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8728 and len(before["materials"]) == 2350
    windows = registered_windows()
    boxes, soil, planting = [Batch(name) for name in BINDINGS]
    for index, window in enumerate(windows):
        x, z = window["x"], window["low"]
        width = window["width"] * 0.84
        left, right = x - width / 2, x + width / 2
        # The rear50mm bears on the retained175mm projecting stone sill.
        # The back face is beyond the retained115mm blue frame front.
        back, front, thickness = 0.125, 0.365, 0.018
        boxes.box((left, back, z), (right, front, z + thickness))
        boxes.box((left, back, z + thickness), (right, back + thickness, z + 0.16))
        boxes.box((left, front - thickness, z + thickness), (right, front, z + 0.16))
        boxes.box(
            (left, back + thickness, z + thickness),
            (left + thickness, front - thickness, z + 0.16),
        )
        boxes.box(
            (right - thickness, back + thickness, z + thickness),
            (right, front - thickness, z + 0.16),
        )
        soil.box(
            (left + 0.02, back + 0.02, z + 0.105),
            (right - 0.02, front - 0.02, z + 0.125),
        )
        # Six connected clumps, five folded solid leaves each, merged into one
        # scene object. A short root enters soil; no transparent leaf textures.
        for cluster in range(6):
            cx = left + 0.08 + (width - 0.16) * cluster / 5
            cy = 0.205 + 0.055 * (cluster % 2)
            for leaf in range(5):
                angle = 2 * math.pi * (leaf / 5 + index * 0.037 + cluster * 0.071)
                dx, dy = math.cos(angle) * 0.085, math.sin(angle) * 0.035
                root = (cx, cy, z + 0.12)
                mid = (cx + dx * 0.55, cy + dy * 0.55, z + 0.215 + 0.015 * (leaf % 2))
                tip = (cx + dx, cy + dy, z + 0.31 + 0.02 * ((cluster + leaf) % 3))
                width_leaf = 0.037
                contour = [
                    root,
                    (mid[0] - width_leaf, mid[1], mid[2]),
                    tip,
                    (mid[0] + width_leaf, mid[1], mid[2]),
                ]
                # A folded diamond with finite1.5mm thickness, one connected
                # closed solid per leaf and positive outward surface normals.
                points = contour + [(p[0], p[1] + 0.0015, p[2]) for p in contour]
                planting.add(
                    points,
                    [
                        (0, 1, 2),
                        (0, 2, 3),
                        (4, 6, 5),
                        (4, 7, 6),
                        (0, 4, 5, 1),
                        (1, 5, 6, 2),
                        (2, 6, 7, 3),
                        (3, 7, 4, 0),
                    ],
                )
        window.update(
            {
                "id": index,
                "boxWidth": width,
                "boxDepth": [back, front],
                "boxTop": z + 0.16,
                "bearingLocalPoints": [
                    [left + 0.06, 0.15, z],
                    [x, 0.15, z],
                    [right - 0.06, 0.15, z],
                ],
                "foliageMaximumHeight": z + 0.35,
                "maximumOpeningHeightFraction": 0.35 / (window["high"] - z),
            }
        )
    added = [batch.finish() for batch in [boxes, soil, planting]]
    update_scene()
    after = capture()
    assert all(after["objects"][name] == row for name, row in before["objects"].items())
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    record = {
        "version": 259,
        "building": "OLD",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": COLLECTION,
        "destinationCollection": COLLECTION,
        "addedObjects": [o.name for o in added],
        "archivedObjects": [],
        "changedObjects": [],
        "addedFingerprints": {o.name: object_fingerprint(o) for o in added},
        "replacementMaterialBindings": {
            o.name: [m.name for m in o.data.materials] for o in added
        },
        "newMaterials": [],
        "newMaterialGraphs": {},
        "planters": windows,
        "geometrySourceFingerprints": {
            name: object_fingerprint(bpy.data.objects[name]) for name in [GLASS, STONE]
        },
        "sourceReviewSha256": sha(OUT / "source-review.json"),
        "sharedBatches": 3,
        "addedTriangles": sum(
            sum(len(p.vertices) - 2 for p in o.data.polygons) for o in added
        ),
        "limitations": [
            "Only eight photo-supported near Houghton boxes,not whole-building exterior completion.",
            "Window axes/sills retained from258; box dimensions,overhang,foliage count and leaf shape are authored display estimates,not measured botanical or support-engineering data.",
            "Undated seasonal photograph does not establish2026 planting condition. Farther bays,courtyard,main portal and roof unchanged.",
        ],
    }
    (OUT / "audit.json").write_text(json.dumps(record, indent=2) + "\n")
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    assert sha(BASE) == SHA
    print("OLD259_WINDOW_BOXES_COMPONENT_SAVED", record["addedTriangles"], flush=True)


if __name__ == "__main__":
    main()
