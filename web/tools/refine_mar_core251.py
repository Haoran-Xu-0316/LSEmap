"""Recover and author the finite MAR third-floor southern concrete lift core.

The plan uses actual opaque PDF fills, not lift-car outlines or line weights.
All vertical dimensions remain inherited/explicit estimates. Only an independent
component is saved; no complete native or shared website file is overwritten.
"""

import hashlib
import json
import math
import sys
from collections import Counter
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar-core251"
BASE = ROOT / "result/blender/LSE_campus_detailed_v250.blend"
BASE_SHA = "833c92b1af57b5c60fbf6f7cd85deb35ea506f680beefcbf6ffde502516dc4ee"
OWNED = "MAR251_third_south_lift_core_walls"
COLLECTION = "MAR_PUBLIC_INTERIOR_study"
LOW, DOOR_HEIGHT, TOP = 17.5, 2.1, 21.9
FILLS = [
    "curve-26113",
    "curve-26115",
    "curve-26191",
    "curve-26207",
    "curve-26209",
    "curve-26287",
    "curve-26299",
    "curve-26303",
]
DOORS = [
    (
        "west-upper-stair-side",
        [
            [401.8207, 535.0166],
            [402.6437, 535.0046],
            [402.6457, 539.5633],
            [401.8237, 539.5723],
        ],
    ),
    (
        "west-upper-corridor-side",
        [
            [409.5737, 535.0026],
            [410.4037, 535.0146],
            [410.4067, 539.5703],
            [409.5757, 539.5603],
        ],
    ),
    (
        "west-lower-corridor-side",
        [
            [409.5757, 545.2373],
            [410.4067, 545.2483],
            [410.4097, 549.8053],
            [409.5867, 549.8193],
        ],
    ),
    (
        "east-upper-corridor-side",
        [
            [420.3171, 535.008],
            [421.1321, 535.011],
            [421.1341, 539.567],
            [420.3201, 539.565],
        ],
    ),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def prepare():
    import numpy as np
    from shapely import constrained_delaunay_triangles, set_precision
    from shapely.affinity import affine_transform
    from shapely.geometry import LineString, Polygon, box
    from shapely.geometry.polygon import orient
    from shapely.ops import polygonize, unary_union

    review = json.loads(
        (ROOT / "result/blender/mar-exterior249/review.json").read_text()
    )
    geometry = json.loads(
        (ROOT / "result/blender/mar-registration217/audit.json").read_text()
    )["geographicRegistration"]
    fit, place = (
        review["coreRegistration"]["thirdPdfToSecondPdf"],
        geometry["secondPdfToNativeLocalCandidate"],
    )
    angle = math.radians(geometry["nativeBasisDegrees"])
    basis = np.array(
        [[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]]
    )

    def world(points):
        points = fit["scale"] * np.asarray(points) @ np.array(
            fit["rotation"]
        ) + np.array(fit["translation"])
        points = place["scale"] * points[:, ::-1] @ np.array(
            place["rotation"]
        ) + np.array(place["translation"])
        return np.array(geometry["nativeOrigin"]) + points @ basis

    origin, x, y = world([[0, 0], [1, 0], [0, 1]])
    x, y = x - origin, y - origin
    coefficients = [x[0], y[0], x[1], y[1], origin[0], origin[1]]
    source = json.loads((OUT / "retained-source-wall-fills.json").read_text())
    assert {row["id"] for row in source} == set(FILLS)
    assert all(
        row["fill"] and not row["stroke"] and row["non_stroking_color"] == [0, 0, 0, 1]
        for row in source
    )
    raw = [Polygon(row["pts"]) for row in source]
    assert all(p.is_valid for p in raw)
    domain = unary_union(
        [
            box(401.6147, 531.7496, 410.4157, 553.0583),
            box(420.3081, 531.7511, 428.9041, 542.825),
        ]
    )
    source_walls = unary_union(raw).intersection(domain)
    source_duplicates = (
        sum(p.intersection(domain).area for p in raw) - source_walls.area
    )
    mesh = json.loads(
        (ROOT / "result/blender/mar-third250/saved-mesh.json").read_text()
    )
    floor = unary_union(
        [Polygon([mesh["positions"][i][:2] for i in face]) for face in mesh["faces"]]
    )
    source_world = affine_transform(source_walls, coefficients)
    # A tenth-millimetre bearing inset coordinates source-stroke corner noise with
    # the actual250mesh. The floor itself and its three openings are untouched.
    bearing = floor.buffer(-0.0001)
    lower = set_precision(source_world.intersection(bearing), 0.00002)
    doors = []
    for name, points in DOORS:
        polygon = Polygon(world(points))
        clipped = set_precision(polygon.intersection(bearing), 0.00002)
        left = (world([points[0]])[0] + world([points[1]])[0]) / 2
        right = (world([points[2]])[0] + world([points[3]])[0]) / 2
        tangent = (right - left) / np.linalg.norm(right - left)
        across = np.array([-tangent[1], tangent[0]])
        doors.append(
            {
                "id": name,
                "sourcePdf": points,
                "world": list(clipped.exterior.coords),
                "widthMetres": float(np.linalg.norm(right - left)),
                "heightMetresEstimated": DOOR_HEIGHT,
                "centre": ((left + right) / 2).tolist(),
                "normal": across.tolist(),
                "wallThicknessMetres": float(
                    np.linalg.norm(world([points[1]])[0] - world([points[0]])[0])
                ),
            }
        )
    caps = [Polygon(row["world"]) for row in doors]
    full = set_precision(unary_union([lower] + caps), 0.00002)
    assert full.geom_type == "MultiPolygon" and len(full.geoms) == 2
    assert sorted(len(poly.interiors) for poly in full.geoms) == [1, 2]
    lines = set_precision(unary_union([lower.boundary, full.boundary]), 0.00002)
    cells = [
        orient(poly, sign=1)
        for poly in polygonize(lines)
        if poly.area > 1e-10 and full.covers(poly.representative_point())
    ]
    assert unary_union(cells).symmetric_difference(full).area < 1e-8
    bottoms = [
        LOW if lower.covers(poly.representative_point()) else LOW + DOOR_HEIGHT
        for poly in cells
    ]
    edge_cells = {}
    for index, cell in enumerate(cells):
        for ring in [cell.exterior] + list(cell.interiors):
            points = list(ring.coords)
            for a, b in pairwise(points):
                key = tuple(
                    sorted(
                        [tuple(round(v, 5) for v in a), tuple(round(v, 5) for v in b)]
                    )
                )
                edge_cells.setdefault(key, []).append((index, a, b))
    assert all(len(owners) <= 2 for owners in edge_cells.values())
    vertices, faces, uv_values = [], [], []
    vertex_map = {}

    def add_face(points, uv):
        indices = []
        for point in points:
            key = tuple(round(float(v), 5) for v in point)
            if key not in vertex_map:
                vertex_map[key] = len(vertices)
                vertices.append(key)
            indices.append(vertex_map[key])
        assert len(set(indices)) == len(indices)
        faces.append(indices)
        uv_values.append(uv)

    for index, cell in enumerate(cells):
        triangles = list(constrained_delaunay_triangles(cell).geoms)
        assert abs(sum(p.area for p in triangles) - cell.area) < 1e-8
        for triangle in triangles:
            points = list(orient(triangle, sign=1).exterior.coords)[:3]
            add_face([(*p, TOP) for p in points], points)
            reversed_points = list(reversed(points))
            add_face([(*p, bottoms[index]) for p in reversed_points], reversed_points)
    for owners in edge_cells.values():
        for index, a, b in owners:
            others = [other for other, _, _ in owners if other != index]
            for z0, z1 in [(LOW, LOW + DOOR_HEIGHT), (LOW + DOOR_HEIGHT, TOP)]:
                if bottoms[index] > z0 + 0.000001:
                    continue
                if any(bottoms[other] <= z0 + 0.000001 for other in others):
                    continue
                length = LineString([a, b]).length
                add_face(
                    [(*a, z0), (*b, z0), (*b, z1), (*a, z1)],
                    [
                        (0, z0 - LOW),
                        (length, z0 - LOW),
                        (length, z1 - LOW),
                        (0, z1 - LOW),
                    ],
                )
    counts = Counter(
        tuple(sorted((a, b)))
        for face in faces
        for a, b in zip(face, face[1:] + face[:1])
    )
    if set(counts.values()) != {2}:
        for edge, count in counts.items():
            if count != 2:
                print(
                    "NONMANIFOLD",
                    count,
                    [vertices[i] for i in edge],
                    [
                        (i, face)
                        for i, face in enumerate(faces)
                        if all(x in face for x in edge)
                    ],
                )
        write(
            "mesh-debug.json",
            {
                "vertices": vertices,
                "faces": faces,
                "cellBottoms": bottoms,
                "cells": [
                    [list(p.exterior.coords), [list(r.coords) for r in p.interiors]]
                    for p in cells
                ],
            },
        )
    assert set(counts.values()) == {2}, Counter(counts.values())
    volume = 0
    for face in faces:
        a = np.array(vertices[face[0]])
        for i in range(1, len(face) - 1):
            volume += float(a @ np.cross(vertices[face[i]], vertices[face[i + 1]])) / 6
    expected = sum(poly.area * (TOP - bottom) for poly, bottom in zip(cells, bottoms))
    assert abs(volume - expected) < 1e-7 and volume > 0, (volume, expected)
    plan = {
        "version": 251,
        "building": "MAR",
        "baselineSha256": BASE_SHA,
        "sourcePdf": review["source"]["path"],
        "sourcePdfSha256": review["source"]["sha256"],
        "sourcePage": 1,
        "sourceFloor": "third",
        "sourceFills": FILLS,
        "sourceFilledAreaPdfPointsSquared": source_walls.area,
        "duplicatePaintAreaRemovedPdfPointsSquared": source_duplicates,
        "sourceFillInterpretation": "Actual black opaque filled polygons;stroke=False. Nominal0.6ptline widths are ignored, and unfilled lift-car contours are excluded.",
        "sourceBoundedDomainsPdf": [
            [401.6147, 531.7496, 410.4157, 553.0583],
            [420.3081, 531.7511, 428.9041, 542.825],
        ],
        "wallFootprintRawSquareMetres": source_world.area,
        "supportedWallFootprintSquareMetres": lower.area,
        "footprintClippedForExistingDeckSquareMetres": source_world.difference(
            lower
        ).area,
        "bearingInsetMetres": 0.0001,
        "coordinateGridMetres": 0.00002,
        "fullUpperWallFootprintSquareMetres": full.area,
        "height": {
            "base": LOW,
            "top": TOP,
            "estimatedDoorClearHeight": DOOR_HEIGHT,
            "policy": "Retained250native17.5m/21.9mstorey datums must be confirmed on open;door height2.1mestimated. No source-measured height claim.",
        },
        "sourceCoreFitMaximumMetres": review["coreRegistration"]["fitMaximumMetres"],
        "sourcePerimeterCandidateMaximumMetres": review["geographicRegistration"][
            "thirdPerimeterMaximumResidualMetres"
        ],
        "sourceVerticalEvidence": {
            "page1": "SectionAA has no explicit readable vertical dimension or shared stated scale;not used to measure height.",
            "page2": "KingstonTownHouse;notMARandnotused.",
        },
        "doors": doors,
        "shaftHoles": [
            hole["world"]
            for hole in json.loads(
                (ROOT / "result/blender/mar-third250/plan.json").read_text()
            )["holes"]
        ],
        "lowerFootprint": [
            {
                "outer": list(p.exterior.coords),
                "holes": [list(r.coords) for r in p.interiors],
            }
            for p in lower.geoms
        ],
        "upperFootprint": [
            {
                "outer": list(p.exterior.coords),
                "holes": [list(r.coords) for r in p.interiors],
            }
            for p in full.geoms
        ],
        "vertices": vertices,
        "faces": faces,
        "metricUvs": uv_values,
        "expectedVolumeCubicMetres": expected,
        "planarCells": len(cells),
        "closedManifoldCpu": True,
        "ownedObject": OWNED,
        "targetCollection": COLLECTION,
        "limitations": [
            "Source2022published plan is not a2026survey;the inter-core corridor and adjacent stair/service continuations outside the finite domain are not rebuilt.",
            "2.1mdoor clear height is an estimate;no lift cars,doors,equipment or upper stair flights are fabricated.",
            "New wall top remains open above each of the three shaft interiors. Existing higher-level generic floor plates are preserved and may still cap the continued shafts.",
            "Native17.5m/21.9mlevels are inherited estimates,not source measurements;no entire upper-level envelope adjustment.",
            "Only these bounded third-storey walls are reconstructed;other floors and all35rooms must remain unchanged.",
        ],
    }
    write("plan.json", plan)
    print(
        "MAR251_PLAN",
        len(vertices),
        len(faces),
        volume,
        "doors",
        [round(row["widthMetres"], 4) for row in doors],
        flush=True,
    )


def capture_source():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mar251_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = BASE_SHA
    return helper.capture_source()


def mesh_tree(obj):
    from mathutils.bvhtree import BVHTree

    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [list(p.vertices) for p in obj.data.polygons],
    )


def native_context(walls):
    import bpy
    from integrate_exterior_round194 import object_fingerprint
    from mathutils.bvhtree import BVHTree

    deck = bpy.data.objects["MAR250_third_floor_with_source_lift_shafts"]
    upper = bpy.data.objects["MAR_MAR_floor_way/1376078546_21.9"]
    assert not deck.hide_render and not upper.hide_render
    assert all(
        abs((deck.matrix_world @ v.co).z - LOW) < 0.00002 for v in deck.data.vertices
    )
    assert all(
        abs((upper.matrix_world @ v.co).z - TOP) < 0.00002 for v in upper.data.vertices
    )
    old = json.loads((ROOT / "result/blender/mar-third250/audit.json").read_text())
    assert object_fingerprint(deck) == old["addedFingerprints"][deck.name]
    points = [walls.matrix_world @ v.co for v in walls.data.vertices]
    bounds = [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
    candidates = []
    vertices = []
    faces = []
    owners = []
    members = set(bpy.data.collections["MAR_EXTERIOR"].all_objects) | set(
        bpy.data.collections[COLLECTION].all_objects
    )
    for obj in members:
        if obj == walls or obj.type != "MESH" or obj.hide_render:
            continue
        coordinates = [obj.matrix_world @ v.co for v in obj.data.vertices]
        for face in obj.data.polygons:
            poly = [coordinates[i] for i in face.vertices]
            if (
                max(p.z for p in poly) <= LOW + 0.001
                or min(p.z for p in poly) >= TOP - 0.001
            ):
                continue
            if any(
                max(p[i] for p in poly) < bounds[i][0] - 0.0001
                or min(p[i] for p in poly) > bounds[i][1] + 0.0001
                for i in [0, 1]
            ):
                continue
            offset = len(vertices)
            vertices.extend(poly)
            faces.append(tuple(range(offset, offset + len(poly))))
            owners.append(obj.name)
    intersections = []
    if faces:
        tree = BVHTree.FromPolygons(vertices, faces)
        intersections = [owners[j] for _, j in mesh_tree(walls).overlap(tree)]
    assert not intersections, sorted(set(intersections))
    candidates = sorted(set(owners))
    return {
        "deck": deck.name,
        "deckFingerprint": object_fingerprint(deck),
        "nextFloor": upper.name,
        "nextFloorFingerprint": object_fingerprint(upper),
        "actualDeckHeight": LOW,
        "actualNextFloorHeight": TOP,
        "priorWallCandidateFaces": len(faces),
        "candidateOwners": candidates,
        "overlappingPriorWallFaces": 0,
        "existingWallDuplicationAction": "No overlapping existing wall geometry; no original objects removed or hidden",
    }


def render_review(walls):
    import bpy
    from mathutils import Vector

    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    deck = bpy.data.objects["MAR250_third_floor_with_source_lift_shafts"]
    camera = bpy.data.objects.new(
        "MAR251_temporary_review_camera",
        bpy.data.cameras.new("MAR251_temporary_review_camera"),
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (0.82, 0.84, 0.85)
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for obj in scene.objects:
        if obj.type in {"MESH", "FONT", "CURVE"}:
            obj.hide_render = obj not in [deck, walls]
    target = Vector((10.8, 53.6, 19.1))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 18
    for view, offset in [("plan", (0, 0, 38)), ("oblique", (13, -17, 18))]:
        camera.location = target + Vector(offset)
        camera.rotation_euler = (
            (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        for phase in ["before", "after"]:
            walls.hide_render = phase == "before"
            scene.render.filepath = str(OUT / f"{phase}-{view}.png")
            bpy.ops.render.render(write_still=True)


def build():
    import bmesh
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene

    plan = json.loads((OUT / "plan.json").read_text())
    component = OUT / "component.blend"
    assert not component.exists(), "Do not overwrite an existing component"
    assert (
        sha(BASE) == BASE_SHA == plan["baselineSha256"]
        and sha(ROOT / plan["sourcePdf"]) == plan["sourcePdfSha256"]
    )
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture_source()
    write("protected-source-state.json", before)
    assert OWNED not in bpy.data.objects
    material = bpy.data.materials["MAR_D3_concrete"]
    mesh = bpy.data.meshes.new(OWNED)
    mesh.from_pydata(plan["vertices"], [], plan["faces"])
    mesh.materials.append(material)
    mesh.update()
    uv = mesh.uv_layers.new(name="MetricUV")
    for face, values in zip(mesh.polygons, plan["metricUvs"]):
        for loop, value in zip(face.loop_indices, values):
            uv.data[loop].uv = value
    assert not mesh.validate(clean_customdata=False)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    assert all(e.is_manifold for e in bm.edges)
    volume = bm.calc_volume(signed=True)
    bm.free()
    assert volume > 0 and abs(volume - plan["expectedVolumeCubicMetres"]) < 0.0002, (
        volume,
        plan["expectedVolumeCubicMetres"],
    )
    obj = bpy.data.objects.new(OWNED, mesh)
    bpy.data.collections[COLLECTION].objects.link(obj)
    obj["destinationCollection"] = COLLECTION
    obj["publicInteriorComponent"] = True
    obj["evidence_status"] = (
        "Actual2022third-floor concrete fills;retained17.5to21.9mlevels and2.1mdoor-height estimate;no lift equipment"
    )
    update_scene()
    context = native_context(obj)
    write("native-context.json", context)
    after = capture_source()
    assert set(after["objects"]) == set(before["objects"]) | {OWNED}
    assert all(
        after["objects"][name] == state for name, state in before["objects"].items()
    )
    assert all(
        after["materials"][name] == state for name, state in before["materials"].items()
    )
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    fingerprint = object_fingerprint(obj)
    bpy.data.libraries.write(str(component), {obj}, fake_user=True, compress=True)
    mesh.calc_loop_triangles()
    audit = {
        "version": 251,
        "building": "MAR",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": COLLECTION,
        "destinationCollection": COLLECTION,
        "addedObjects": [OWNED],
        "archivedObjects": [],
        "changedObjects": [],
        "addedFingerprints": {OWNED: fingerprint},
        "replacementMaterialBindings": {OWNED: [material.name]},
        "sourcePlan": "result/blender/mar-core251/plan.json",
        "sourcePlanSha256": sha(OUT / "plan.json"),
        "nativeContext": context,
        "addedTriangles": len(mesh.loop_triangles),
        "closedVolumeCubicMetres": volume,
        "newMaterials": 0,
        "scope": "Restore only finite source-filled third-floor south lift-core walls with four source-width openings and estimated2.1mheads. No shaft caps, floor alteration, lift equipment or upper-flight invention.",
        "status": "candidate_requires_saved_mesh_and_visual_review",
        "limitations": plan["limitations"],
    }
    write("audit.json", audit)
    render_review(obj)
    assert sha(BASE) == BASE_SHA
    print(
        "MAR251_COMPONENT_WRITTEN",
        sha(component),
        "triangles",
        len(mesh.loop_triangles),
        "volume",
        volume,
        flush=True,
    )
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ModuleNotFoundError:
        prepare()
    else:
        build()
