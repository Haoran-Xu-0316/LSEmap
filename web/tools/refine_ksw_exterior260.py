"""Correct the photographed KSW entrance's two recessed stone treads.

Fixed project paths; run in Blender's editor. The inherited portal registration
and all original meshes/materials are retained. Only the append-only component
and its audit are saved; complete campus assembly remains a separate operation.
"""

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v259.blend"
SHA = "b304b1fe4f519a6aafd3df15dcf9235ca25a99f3bd699e99a14beaab410c7e8e"
OUT = ROOT / "result/blender/ksw260"
COLLECTION = "KSW_EXTERIOR"
NAME = "KSW260_recessed_two_step_approach"
GROUND_SHA = "16569eeb9bbbeb5c49f85ec12cc14e2a1ad03d079f980441934db77044274428"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_ksw_exterior195 import connected_parts, registration


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture():
    spec = importlib.util.spec_from_file_location(
        "ksw260_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def local(point):
    origin, axis, outward = registration()
    delta = point - origin
    return Vector((delta.dot(axis), delta.dot(outward), point.z))


def world(point):
    origin, axis, outward = registration()
    return origin + axis * point[0] + outward * point[1] + Vector((0, 0, point[2]))


def bounds(obj):
    points = [local(obj.matrix_world @ v.co) for v in obj.data.vertices]
    return [[min(p[d] for p in points), max(p[d] for p in points)] for d in range(3)]


def make_steps(source, layout):
    vertices, faces = [], []
    for tread in layout["treads"]:
        left, right = layout["openingX"]
        rear, front = tread["depth"]
        bottom, top = tread["height"]
        start = len(vertices)
        vertices.extend(
            world((x, y, z))
            for z in [bottom, top]
            for y in [rear, front]
            for x in [left, right]
        )
        faces.extend(
            tuple(start + i for i in face)
            for face in [
                (0, 2, 3, 1),
                (4, 5, 7, 6),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 4, 6, 2),
                (1, 3, 7, 5),
            ]
        )
    # Owned copy keeps the established stone material binding. Mesh data are new;
    # no source geometry, normal, UV or original material node is edited.
    obj = source.copy()
    obj.name = NAME
    obj.data = bpy.data.meshes.new(NAME + "_mesh")
    obj.matrix_world = Matrix.Identity(4)
    obj.modifiers.clear()
    obj.data.from_pydata(vertices, [], faces)
    for material in source.data.materials:
        obj.data.materials.append(material)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    uv = obj.data.uv_layers.new(name="Metric")
    for loop in obj.data.loops:
        point = local(obj.data.vertices[loop.vertex_index].co)
        uv.data[loop.index].uv = (point.x, point.y + point.z)
    obj.data.update()
    obj["originalObject"] = source.name
    obj["destinationCollection"] = COLLECTION
    obj["sourceScope"] = (
        "Two photo-supported recessed entrance treads; inherited portal scale, estimated tread run"
    )
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.hide_render = False
    obj.hide_set(False)
    return obj


def ground_registration(opening, front):
    path = OUT / "actual-ground-support.json"
    assert sha(path) == GROUND_SHA
    report = json.loads(path.read_text())
    assert report["baselineSha256"] == SHA and report["nativeReadOnly"] is True
    assert len(report["rows"]) == 9
    centre = sum(opening) / 2
    expected = [
        world((centre + dx, front + depth, 1))
        for dx in [-0.4, 0, 0.4]
        for depth in [0.04, 0.15, 0.35]
    ]
    first_hits = []
    for row, point in zip(report["rows"], expected):
        assert (Vector(row["origin"]) - point).length < 1e-4
        assert row["hits"] and row["hits"] == sorted(
            row["hits"], key=lambda h: h["distance"]
        )
        hit = row["hits"][0]
        assert abs(row["origin"][2] - hit["point"][2] - hit["distance"]) < 1e-6
        first_hits.append(hit)
    elevations = [hit["point"][2] for hit in first_hits]
    assert max(elevations) - min(elevations) < 1e-6
    assert {hit["object"] for hit in first_hits} == {"SITE216_Expanded_flat_map_datum"}
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": GROUND_SHA,
        "nativeBaselineSha256": SHA,
        "firstHitCount": 9,
        "sourceObjects": sorted({hit["object"] for hit in first_hits}),
        "elevation": sum(elevations) / len(elevations),
    }


def entrance_layout(visible):
    threshold = [o for o in visible if "door_threshold" in o.name]
    approach = [
        o for o in visible if "approach_step" in o.name or "step_nosing" in o.name
    ]
    assert len(threshold) == 1 and len(approach) == 2
    threshold = threshold[0]
    portal = [o for o in visible if "pier_moulded_base" in o.name]
    assert len(portal) == 1
    piers = []
    for group in connected_parts(portal[0].data):
        points = [
            local(portal[0].matrix_world @ portal[0].data.vertices[i].co) for i in group
        ]
        piers.append(
            [[min(p[d] for p in points), max(p[d] for p in points)] for d in range(3)]
        )
    assert len(piers) == 2
    piers.sort(key=lambda p: p[0][0])
    opening = [piers[0][0][1], piers[1][0][0]]
    assert 1.2 < opening[1] - opening[0] < 2.1
    door = [
        o
        for o in visible
        if any(m and "door_timber" in m.name.lower() for m in o.data.materials)
    ]
    assert door
    db = [bounds(o) for o in door]
    rear = min(b[1][0] for b in db) - 0.02
    door_front = max(b[1][1] for b in db)
    front = min(p[1][1] for p in piers)
    middle = (front + door_front) / 2
    height = bounds(threshold)[2][1]
    ground = ground_registration(opening, front)
    grade = ground["elevation"]
    rise = (height - grade) / 2
    assert 0.11 <= rise <= 0.17
    assert 0.25 < front - door_front < 0.9
    assert rear < door_front < middle < front
    return (
        threshold,
        approach,
        {
            "openingX": opening,
            "originalThresholdBounds": bounds(threshold),
            "portalBaseObject": portal[0].name,
            "pierBaseBounds": piers,
            "doorObjects": [o.name for o in door],
            "doorFrontDepth": door_front,
            "registeredRise": rise,
            "groundSupport": ground,
            "treads": [
                {"depth": [rear, front], "height": [grade, grade + rise]},
                {"depth": [rear, middle], "height": [grade + rise, height]},
            ],
            "scaleBasis": "Actual native SITE ground at-50mm to retained245mm threshold gives two147.5mm rises. Door and pier geometry register the recess. Guide reports two11–17cm steps; tread run remains estimated.",
        },
    )


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert len(before["objects"]) == 8731 and len(before["materials"]) == 2350
    assert len(before["rooms"]) == 35
    visible = [
        o
        for o in bpy.data.collections[COLLECTION].all_objects
        if o.type == "MESH" and not o.hide_render
    ]
    threshold, approach, layout = entrance_layout(visible)
    added = make_steps(threshold, layout)
    archived = [threshold.name] + [o.name for o in approach]
    for name in archived:
        bpy.data.objects[name].hide_render = True
        bpy.data.objects[name].hide_set(True)
    update_scene()
    after = capture()
    for name, expected in before["objects"].items():
        expected = dict(expected)
        if name in archived:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {added}, fake_user=True, compress=True)
    report = {
        "version": 260,
        "building": "KSW",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": COLLECTION,
        "destinationCollection": COLLECTION,
        "addedObjects": [added.name],
        "archivedObjects": archived,
        "changedObjects": [],
        "addedFingerprints": {added.name: object_fingerprint(added)},
        "replacementMaterialBindings": {
            added.name: [m.name for m in added.data.materials]
        },
        "newMaterials": [],
        "newMaterialGraphs": {},
        "addedTriangles": 24,
        "layout": layout,
        "sourceReviewSha256": sha(OUT / "source-review.json"),
        "geometrySourceFingerprints": {
            name: object_fingerprint(bpy.data.objects[name])
            for name in [threshold.name, layout["portalBaseObject"]]
            + layout["doorObjects"]
            + layout["groundSupport"]["sourceObjects"]
        },
        "limitations": [
            "Two recessed entrance treads only; no full-building completion claim.",
            "Retained portal scale and threshold elevation are inherited estimates. The survey supports step count and rise range; tread run is estimated from the photos.",
            "Photo and accessibility-survey dates unknown; not a2026accessibility certification.",
            "Door joinery, stone colour, glass, upper windows, carving and roof remain unchanged. Full rear and roof evidence still absent.",
        ],
    }
    (OUT / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (OUT / "protected-source-state.json").write_text(
        json.dumps(before, indent=2) + "\n"
    )
    assert sha(BASE) == SHA
    print("KSW260_RECESSED_TWO_STEPS_SAVED", archived, layout, flush=True)


if __name__ == "__main__":
    main()
