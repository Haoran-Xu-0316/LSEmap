"""Give only the registered MAR third-floor south deck a finite concrete body.

All existing top corner positions and UV pairings, three lift openings and251
wall footings stay fixed. The original inward top winding is corrected.0.32m
thickness is inherited from223as a display estimate, not a measured section.
No exterior object, higher floor, glass, room or original material is edited.
"""

import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v257.blend"
SHA = "5f73b29480de08425d4d8ab3c39aa1e2b9231656f81f1f763ee1ffa200568db9"
OUT = ROOT / "result/blender/mar258"
SOURCE = "MAR250_third_floor_with_source_lift_shafts"
REPLACEMENT = "MAR258_third_south_deck_solid"
COLLECTION = "MAR_PUBLIC_INTERIOR_study"
THICKNESS = 0.32
WALLS = "MAR251_third_south_lift_core_walls"
BEARING = "MAR_NEXT_PANEL_retained_01_5_retained_D5_wings75_concrete"
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha


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


def source_plan(source):
    unique, indices, remap = [], {}, {}
    for vertex in source.data.vertices:
        key = tuple(vertex.co)
        if key not in indices:
            indices[key] = len(unique)
            unique.append(key)
        remap[vertex.index] = indices[key]
    top = [
        tuple(remap[i] for i in reversed(face.vertices))
        for face in source.data.polygons
    ]
    edges = {}
    for face in top:
        for a, b in zip(face, face[1:] + face[:1]):
            edges.setdefault(tuple(sorted((a, b))), []).append((a, b))
    assert {len(rows) for rows in edges.values()} == {1, 2}
    boundary = [rows[0] for rows in edges.values() if len(rows) == 1]
    assert len(unique) == 20 and len(top) == 24 and len(boundary) == 20
    world = [source.matrix_world @ Vector(p) for p in unique]
    assert max(p.z for p in world) == min(p.z for p in world) == 17.5
    assert all(
        (world[b] - world[a]).cross(world[c] - world[a]).z > 0 for a, b, c in top
    )
    neighbors = {}
    for a, b in boundary:
        assert a not in neighbors
        neighbors[a] = b
    unseen, loops = set(neighbors), []
    while unseen:
        seed = min(unseen)
        current, loop = seed, []
        while current in unseen:
            unseen.remove(current)
            loop.append(current)
            current = neighbors[current]
        assert current == seed
        loops.append(loop)
    assert len(loops) == 4
    return unique, top, boundary, loops


def top_corner_records(obj, face_count):
    rows = []
    for face in list(obj.data.polygons)[:face_count]:
        corners = []
        for loop_index in face.loop_indices:
            loop = obj.data.loops[loop_index]
            corners.append(
                {
                    "world": list(
                        obj.matrix_world @ obj.data.vertices[loop.vertex_index].co
                    ),
                    "uv": {
                        uv.name: list(uv.data[loop_index].uv)
                        for uv in obj.data.uv_layers
                    },
                }
            )
        rows.append(sorted(json.dumps(corner, sort_keys=True) for corner in corners))
    return rows


def build(source):
    unique, top, boundary, loops = source_plan(source)
    count = len(unique)
    inverse = source.matrix_world.inverted()
    points = [Vector(p) for p in unique]
    points += [
        inverse @ (source.matrix_world @ Vector(p) - Vector((0, 0, THICKNESS)))
        for p in unique
    ]
    bottom = [tuple(reversed(tuple(i + count for i in face))) for face in top]
    sides = [(a, a + count, b + count, b) for a, b in boundary]
    mesh = bpy.data.meshes.new(REPLACEMENT + "_mesh")
    mesh.from_pydata(points, [], top + bottom + sides)
    for material in source.data.materials:
        mesh.materials.append(material)
    assert len(mesh.materials) == 1 and mesh.materials[0].name == "MAR_D3_concrete"
    for index, face in enumerate(mesh.polygons):
        face.material_index = 0
        face.use_smooth = (
            source.data.polygons[index].use_smooth if index < len(top) else False
        )
    for original in source.data.uv_layers:
        layer = mesh.uv_layers.new(name=original.name)
        for index, face in enumerate(mesh.polygons):
            if index < len(top):
                old = source.data.polygons[index]
                bindings = {
                    tuple(
                        source.data.vertices[source.data.loops[i].vertex_index].co
                    ): original.data[i].uv.copy()
                    for i in old.loop_indices
                }
                values = [
                    bindings[tuple(mesh.vertices[mesh.loops[i].vertex_index].co)]
                    for i in face.loop_indices
                ]
            elif index < len(top) + len(bottom):
                values = [
                    (
                        source.matrix_world
                        @ mesh.vertices[mesh.loops[i].vertex_index].co
                    ).xy
                    for i in face.loop_indices
                ]
            else:
                a, b = boundary[index - len(top) - len(bottom)]
                length = (
                    source.matrix_world @ Vector(unique[b])
                    - source.matrix_world @ Vector(unique[a])
                ).length
                values = [(0, THICKNESS), (0, 0), (length, 0), (length, THICKNESS)]
            for loop_index, value in zip(face.loop_indices, values):
                layer.data[loop_index].uv = value
        layer.active_render = original.active_render
    if source.data.uv_layers.active:
        mesh.uv_layers.active = mesh.uv_layers[source.data.uv_layers.active.name]
    mesh.update()
    obj = source.copy()
    obj.data = mesh
    obj.name = REPLACEMENT
    obj["originalObject"] = SOURCE
    obj["webGeometrySource"] = source.get("webGeometrySource", SOURCE)
    obj["destinationCollection"] = COLLECTION
    obj["publicInteriorComponent"] = True
    obj["thicknessEstimateMetres"] = THICKNESS
    obj["sourceScope"] = (
        "Registered third-storey south deck only; finite display thickness, original top/holes/UV retained"
    )
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj.hide_render = False
    set_layer_hidden(obj, False)
    source.hide_render = True
    set_layer_hidden(source, True)
    assert top_corner_records(source, 24) == top_corner_records(obj, 24)
    return obj, loops


def actual_tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    positions = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
    result = BVHTree.FromPolygons(positions, triangles, all_triangles=True)
    evaluated.to_mesh_clear()
    return result


def section_proof(source, obj):
    _unique, top, _boundary, _loops = source_plan(source)
    mesh = obj.data
    mesh.calc_loop_triangles()
    edge_counts = Counter(
        tuple(sorted((a, b)))
        for face in mesh.polygons
        for a, b in zip(
            tuple(face.vertices), tuple(face.vertices)[1:] + tuple(face.vertices)[:1]
        )
    )
    assert all(count == 2 for count in edge_counts.values())
    assert len(mesh.vertices) - len(edge_counts) + len(mesh.polygons) == -4
    assert (
        len(mesh.vertices) == 40
        and len(mesh.polygons) == 68
        and len(mesh.loop_triangles) == 88
    )
    assert top_corner_records(source, 24) == top_corner_records(obj, 24)
    world = [obj.matrix_world @ v.co for v in mesh.vertices]
    low, high = min(p.z for p in world), max(p.z for p in world)
    assert high == 17.5 and abs(high - low - THICKNESS) < 1e-6
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    assert all(
        (normal_matrix @ face.normal).z > 0.999 for face in list(mesh.polygons)[:24]
    )
    assert all(
        (normal_matrix @ face.normal).z < -0.999 for face in list(mesh.polygons)[24:48]
    )
    anchor = world[0]
    volume = math.fsum(
        (world[t.vertices[0]] - anchor).dot(
            (world[t.vertices[1]] - anchor).cross(world[t.vertices[2]] - anchor)
        )
        / 6
        for t in mesh.loop_triangles
    )
    area = math.fsum(
        (world[b] - world[a]).cross(world[c] - world[a]).z / 2 for a, b, c in top
    )
    assert volume > 0 and abs(volume - area * (high - low)) < 0.001
    tree = actual_tree(obj)
    surfaces = []
    for face in list(mesh.polygons)[:24]:
        center = obj.matrix_world @ face.center
        for direction, origin, expected in [
            (Vector((0, 0, -1)), center + Vector((0, 0, 0.05)), 0.05),
            (Vector((0, 0, 1)), Vector((center.x, center.y, low - 0.05)), 0.05),
        ]:
            hit, _, _, distance = tree.ray_cast(origin, direction, 0.1)
            assert hit is not None and abs(distance - expected) < 2e-5
        surfaces.append(list(center))
    # Use the accepted250registered holes and dense points strictly inside them.
    holes = json.loads((ROOT / "result/blender/mar-third250/plan.json").read_text())[
        "holes"
    ]
    hole_probes = []
    for hole in holes:
        polygon = [Vector(point) for point in hole["world"]]
        center = sum(polygon, Vector((0, 0))) / len(polygon)
        for point in polygon:
            for fraction in [0.15, 0.35, 0.55, 0.75, 0.90]:
                xy = center.lerp(point, fraction)
                hit, _, _, _ = tree.ray_cast(
                    Vector((xy.x, xy.y, high + 0.05)),
                    Vector((0, 0, -1)),
                    THICKNESS + 0.1,
                )
                assert hit is None, (hole["id"], list(xy))
                hole_probes.append({"hole": hole["id"], "xy": list(xy)})
    foot_probes = []
    wall = bpy.data.objects[WALLS]
    feet = {
        tuple(wall.matrix_world @ v.co)
        for v in wall.data.vertices
        if abs((wall.matrix_world @ v.co).z - high) < 1e-5
    }
    for point in sorted(feet):
        hit, _, _, distance = tree.ray_cast(
            Vector(point) + Vector((0, 0, 0.03)), Vector((0, 0, -1)), 0.06
        )
        assert hit is not None and abs(distance - 0.03) < 2e-5, point
        foot_probes.append(list(point))
    return {
        "topAreaSquareMetres": area,
        "actualThicknessMetres": high - low,
        "closedVolumeCubicMetres": volume,
        "closedManifoldEveryEdgeTwoFaces": True,
        "eulerCharacteristic": -4,
        "independentBoundaryLoops": 4,
        "liftHoles": 3,
        "topAndBottomSurfaceSamples": surfaces,
        "openLiftShaftRays": hole_probes,
        "wallFootBearingRays": foot_probes,
        "correctedTopWinding": "+Zfrom inherited-Z; original corner world/UVpairings exact",
        "allBottomNormalsDown": True,
    }


def clip_polygon(poly, signed_distance):
    """Clip a real triangle against one plane, retaining degenerate line hits."""
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = signed_distance(a), signed_distance(b)
        if da >= 0:
            result.append(a)
        if (da >= 0) != (db >= 0):
            fraction = da / (da - db)
            result.append([a[d] + fraction * (b[d] - a[d]) for d in range(3)])
    return result


def distance_to_edge(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    factor = max(
        0,
        min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / (dx * dx + dy * dy)),
    )
    return math.hypot(point[0] - a[0] - factor * dx, point[1] - a[1] - factor * dy)


def triangle_contact_rows(world, top, boundary, low, high, neighbors):
    """Intersect actual neighboring triangles with the actual candidate volume."""
    findings = []
    for neighbor in neighbors:
        contacts = []
        for index, triangle in enumerate(neighbor["triangles"]):
            poly = [neighbor["worldPositions"][i] for i in triangle]
            poly = clip_polygon(poly, lambda p: p[2] - low - 0.00001)
            poly = clip_polygon(poly, lambda p: high - 0.00001 - p[2])
            if not poly:
                continue
            pieces = []
            for face in top:
                hit = poly
                for i, j in zip(face, face[1:] + face[:1]):
                    a, b = world[i], world[j]
                    hit = clip_polygon(
                        hit,
                        lambda p, a=a, b=b: (
                            (b[0] - a[0]) * (p[1] - a[1])
                            - (b[1] - a[1]) * (p[0] - a[0])
                        ),
                    )
                    if not hit:
                        break
                if not hit:
                    continue
                # Exclude exact outer/shaft boundary contact, but retain strict
                # interior line intersections of vertical real triangle faces.
                samples = hit + [
                    [math.fsum(p[d] for p in hit) / len(hit) for d in range(3)]
                ]
                inside = [
                    p
                    for p in samples
                    if min(distance_to_edge(p, world[a], world[b]) for a, b in boundary)
                    > 0.0001
                ]
                if inside:
                    pieces.extend(inside)
            if pieces:
                contacts.append(
                    {
                        "triangleIndex": index,
                        "maxBoundaryInsetMetres": max(
                            min(
                                distance_to_edge(p, world[a], world[b])
                                for a, b in boundary
                            )
                            for p in pieces
                        ),
                        "samples": pieces,
                    }
                )
        if contacts:
            findings.append({"object": neighbor["object"], "triangles": contacts})
    return findings


def volume_contact_proof(source, obj):
    """Re-evaluate all nearby source neighbors after candidate append/reopen."""
    _unique, top, boundary, _loops = source_plan(source)
    world = [list(obj.matrix_world @ v.co) for v in obj.data.vertices]
    low, high = min(p[2] for p in world), max(p[2] for p in world)
    inspection = json.loads((OUT / "third-deck-inspection.json").read_text())
    assert object_fingerprint(source) == inspection["sourceFingerprint"]
    neighbors = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for row in inspection["neighbors"]:
        neighbor = bpy.data.objects[row["object"]]
        assert object_fingerprint(neighbor) == row["fingerprint"]
        evaluated = neighbor.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        points = [list(evaluated.matrix_world @ v.co) for v in mesh.vertices]
        # Match the documented read-only native inspection's local triangle ids.
        triangles = [
            tuple(t.vertices)
            for t in mesh.loop_triangles
            if min(points[i][2] for i in t.vertices) <= 18
            and max(points[i][2] for i in t.vertices) >= 17
        ]
        neighbors.append(
            {"object": neighbor.name, "worldPositions": points, "triangles": triangles}
        )
        evaluated.to_mesh_clear()
    findings = triangle_contact_rows(world, top, boundary, low, high, neighbors)
    assert len(findings) == 1 and findings[0]["object"] == BEARING, findings
    contacts = findings[0]["triangles"]
    assert len(contacts) == 4 and {p["triangleIndex"] for p in contacts} == {
        598,
        599,
        1130,
        1131,
    }, contacts
    assert max(p["maxBoundaryInsetMetres"] for p in contacts) < 0.0041
    return {
        "candidateActualZRange": [low, high],
        "evaluatedNeighborCount": len(neighbors),
        "strictInteriorInsetMetres": 0.0001,
        "topBottomContactExcludedMetres": 0.00001,
        "retainedPeripheralConcreteContacts": findings,
        "glassFramesAndOtherNeighborsWithoutVolumeIntrusion": True,
    }


def check_protection(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == row for name, row in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def main():
    assert sha(BASE) == SHA
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "component.blend").exists()
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    source = bpy.data.objects[SOURCE]
    assert not source.hide_render and not source.modifiers
    assert {c.name for c in source.users_collection} == {COLLECTION}
    obj, _loops = build(source)
    update_scene()
    section = section_proof(source, obj)
    contacts = volume_contact_proof(source, obj)
    check_protection(before, capture())
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    write(
        "audit.json",
        {
            "version": 258,
            "building": "MAR",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "destinationCollection": COLLECTION,
            "targetCollection": COLLECTION,
            "addedObjects": [REPLACEMENT],
            "archivedObjects": [SOURCE],
            "changedObjects": [],
            "addedFingerprints": {REPLACEMENT: object_fingerprint(obj)},
            "replacementMaterialBindings": {
                REPLACEMENT: [m.name if m else None for m in obj.data.materials]
            },
            "newMaterials": [],
            "newMaterialGraphs": {},
            "retainNewMaterials": True,
            "topCornerWorldAndUVPairsPreserved": True,
            "thicknessEstimateMetres": THICKNESS,
            "inheritedThicknessSource": "result/blender/mar-structure223/audit.json",
            "sectionProof": section,
            "actualVolumeContactProof": contacts,
            "netAddedTriangles": 64,
            "nativeNeighborDiagnostic": "result/blender/mar258/deck-volume-diagnostic.json",
            "sources": [
                {
                    "path": "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf",
                    "sha256": sha(
                        ROOT
                        / "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf"
                    ),
                    "scope": "2022built third-floor plan provides holes; SectionAA supports finite slab structure, not0.32mthickness.",
                },
                {
                    "url": "https://www.concretecentre.com/Case-Studies/Marshall-Building,-London.aspx",
                    "date": "Concrete Quarterly summer2022",
                    "scope": "Upper office levels use post-tensioned floor slabs; does not specify thickness.",
                },
            ],
            "limitations": [
                "0.32mthickness and17.5m/12.8mlevels are inherited display estimates, not measured engineering dimensions or clearance certification.",
                "Only the250registered south deck is solidified. Other third-floor sheets, fourth-level layout, lift continuation and full interiors remain incomplete.",
                "Known4peripheral concrete triangle contacts extend only1–4mminside the inherited outer boundary; retained and disclosed, not zero-contact construction.",
                "No exterior source object, glass, material graph or independent room changes. No reinforcement, beam or false structural-load claim.",
            ],
        },
    )
    assert sha(BASE) == SHA
    print("MAR258_THIRD_SOUTH_DECK_SOLID_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
