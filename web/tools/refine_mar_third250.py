"""Inspect then refine MAR's third-floor source core as a separate component.

The complete249 native is immutable. A source-supported edit is chosen only
from the actual saved geometry, with all other floors, rooms and materials
protected. The first run writes a read-only inventory and never a component.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar-third250"
BASE = ROOT / "result/blender/LSE_campus_detailed_v249.blend"
BASE_SHA = "cad99a189122994fd484794fb617a9223c31e90fd506fb434ef22d9e87e30e24"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_native():
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_mar_exterior174 import local

    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    objects = set(bpy.data.collections["MAR_EXTERIOR"].all_objects)
    objects |= set(bpy.data.collections["MAR_PUBLIC_INTERIOR_study"].all_objects)
    rows = []
    for obj in sorted(objects, key=lambda item: item.name):
        if obj.type != "MESH" or obj.hide_render:
            continue
        points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        if not points:
            continue
        low, high = min(p.z for p in points), max(p.z for p in points)
        if high < 16.9 or low > 22.1:
            continue
        faces = []
        for face in obj.data.polygons:
            polygon = [points[index] for index in face.vertices]
            if max(p.z for p in polygon) < 16.9 or min(p.z for p in polygon) > 22.1:
                continue
            faces.append(
                {
                    "index": face.index,
                    "points": [list(p) for p in polygon],
                    "materialIndex": face.material_index,
                }
            )
        bounds = [
            [min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)
        ]
        local_points = [local(point) for point in points]
        local_bounds = [
            [min(p[i] for p in local_points), max(p[i] for p in local_points)]
            for i in range(3)
        ]
        rows.append(
            {
                "name": obj.name,
                "bounds": bounds,
                "localBounds": local_bounds,
                "materials": [m.name if m else None for m in obj.data.materials],
                "collections": sorted(c.name for c in obj.users_collection),
                "faceCount": len(obj.data.polygons),
                "sourceFingerprint": before[obj.name],
                "candidateFaces": faces,
            }
        )
    assert before == {obj.name: object_fingerprint(obj) for obj in bpy.data.objects}
    assert sha(BASE) == BASE_SHA
    report = {
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "readOnly": True,
        "nativeUnchanged": True,
        "objectCount": len(before),
        "thirdFloorDatum": 17.5,
        "nextFloorDatum": 21.9,
        "verticalDatumAccuracy": "Retained native estimate, not source-measured height",
        "rows": rows,
    }
    (OUT / "native-inventory.json").write_text(
        json.dumps(report, separators=(",", ":")) + "\n"
    )
    print("MAR250_NATIVE_INSPECTED", len(rows), len(before), flush=True)
    bpy.ops.wm.quit_blender()


def prepare_source_plan():
    import math

    import numpy as np
    from shapely import constrained_delaunay_triangles
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    review = json.loads(
        (ROOT / "result/blender/mar-exterior249/review.json").read_text()
    )
    registration = review["coreRegistration"]["thirdPdfToSecondPdf"]
    geo = json.loads(
        (ROOT / "result/blender/mar-registration217/audit.json").read_text()
    )["geographicRegistration"]
    fit = geo["secondPdfToNativeLocalCandidate"]
    a = math.radians(geo["nativeBasisDegrees"])
    basis = np.array([[math.cos(a), math.sin(a)], [-math.sin(a), math.cos(a)]])
    origin = np.array(geo["nativeOrigin"])

    def xform(points, t):
        return t["scale"] * np.asarray(points) @ np.array(t["rotation"]) + np.array(
            t["translation"]
        )

    def world(points):
        return origin + xform(xform(points, registration)[:, ::-1], fit) @ basis

    # Inner concrete shaft boundaries, not the smaller thin lift-car rectangles used
    # as alignment controls in249. Opposite exact wall-edge paths are kept finite.
    sources = [
        {
            "id": "south-west-upper-shaft",
            "pdf": [
                [402.6492, 532.5771],
                [409.5782, 532.5771],
                [409.5855, 541.9956],
                [402.6395, 541.9906],
            ],
            "vectors": [
                "line-94213",
                "line-94273",
                "line-94265",
                "line-94269",
                "line-94175",
                "line-94225",
            ],
        },
        {
            "id": "south-west-lower-shaft",
            "pdf": [
                [402.6447, 542.8272],
                [409.5747, 542.8272],
                [409.5765, 552.2232],
                [402.6467, 552.2232],
            ],
            "vectors": ["line-94271", "line-94123", "line-94199", "curve-26299"],
        },
        {
            "id": "south-east-upper-shaft",
            "pdf": [
                [421.137, 532.5824],
                [428.0672, 532.5839],
                [428.0742, 542.0028],
                [421.1442, 542.0018],
            ],
            "vectors": ["line-94101", "line-94113", "line-94115", "line-94107"],
        },
    ]
    raw = json.loads((OUT / "core-wall-vectors.json").read_text())
    vector_ids = {r["id"] for r in raw}
    assert all(set(h["vectors"]) <= vector_ids for h in sources)
    car_bounds = review["coreRegistration"]["fitSourceBounds"]
    holes = []
    for row, b in zip(sources, car_bounds):
        p = Polygon(world(row["pdf"]))
        x, y, xx, yy = b
        car = Polygon(world([[x, y], [xx, y], [xx, yy], [x, yy]]))
        assert p.covers(car)
        holes.append(p)
        row["world"] = list(p.exterior.coords)[:-1]
        row["areaSquareMetres"] = p.area
        row["carControlAreaSquareMetres"] = car.area
        # actual finite door-way/beam strips remain in the original deck, beyond the
        # four concrete inside edges; no access-corridor continuation is removed.
        row["minimumShaftToCarClearanceMetres"] = p.boundary.distance(car)
    assert all(p.disjoint(q) for i, p in enumerate(holes) for q in holes[i + 1 :])
    cut = unary_union(holes)
    inventory = json.loads((OUT / "native-inventory.json").read_text())
    source = next(
        r for r in inventory["rows"] if r["name"] == "MAR_MAR_floor_way/1376078546_17.5"
    )
    assert source["faceCount"] == 4
    original = unary_union(
        [Polygon(np.array(f["points"])[:, :2]) for f in source["candidateFaces"]]
    )
    assert original.covers(cut)
    for p in holes:
        assert original.boundary.distance(p) > 0.5
    faces = []
    for row in source["candidateFaces"]:
        p = Polygon(np.array(row["points"])[:, :2])
        assert p.is_valid and abs(max(v[2] for v in row["points"]) - 17.5) < 0.0001
        retained = p.difference(cut)
        triangles = [
            list(t.exterior.coords)[:3]
            for t in constrained_delaunay_triangles(retained).geoms
        ]
        assert abs(sum(Polygon(t).area for t in triangles) - retained.area) < 1e-6
        faces.append(
            {
                "sourceFace": row["index"],
                "sourcePoints": row["points"],
                "materialIndex": row["materialIndex"],
                "trianglesXY": triangles,
                "retainedAreaSquareMetres": retained.area,
            }
        )
    retained = unary_union([Polygon(t) for f in faces for t in f["trianglesXY"]])
    assert retained.symmetric_difference(original.difference(cut)).area < 1e-6
    plan = {
        "version": 250,
        "building": "MAR",
        "baseline": inventory["baseline"],
        "baselineSha256": inventory["baselineSha256"],
        "sourceObject": source["name"],
        "sourceFingerprint": source["sourceFingerprint"],
        "targetCollection": "MAR_PUBLIC_INTERIOR_study",
        "ownedObject": "MAR250_third_floor_with_source_lift_shafts",
        "archivedObjects": [source["name"]],
        "sourceReview": "result/blender/mar-exterior249/review.json",
        "sourcePdf": "data/collections/mar-built-registration-2026/grafton-marshall-built-plans-2022.pdf",
        "sourcePdfSha256": review["source"]["sha256"],
        "sourcePage": 1,
        "sourceFloor": "third",
        "holes": sources,
        "sourceFacePlans": faces,
        "originalAreaSquareMetres": original.area,
        "removedAreaSquareMetres": cut.area,
        "retainedAreaSquareMetres": retained.area,
        "minimumHoleToExternalDeckEdgeMetres": min(
            original.boundary.distance(p) for p in holes
        ),
        "sourceFitMaximumMetres": review["coreRegistration"]["fitMaximumMetres"],
        "coreHeldOutMaximumMetres": review["coreRegistration"]["heldOutMaximumMetres"],
        "perimeterCandidateMaximumMetres": review["geographicRegistration"][
            "thirdPerimeterMaximumResidualMetres"
        ],
        "floorDatum": 17.5,
        "nextFloorDatum": 21.9,
        "datumPolicy": "Retain exact native floor17.5m; no floor height, thickness, wall, flight or roof invented",
        "limitations": [
            "Only three structurally bounded lift-shaft deck openings at one existing floor are corrected. Other floors, lift cores, stairs and shaft walls are incomplete and preserved.",
            "Source2022published floor plan is not a2026survey.",
            "Concrete inside-edge picks retain centimetre-scale drawing stroke/coordinate noise; lift-car thin rectangles are not used as the opening boundary.",
            "Registration uses the shared core; no OSM warp or perimeter change.",
            "No claim to a complete operational lift, accessible route or furnished third floor.",
        ],
    }
    (OUT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(
        plan["originalAreaSquareMetres"],
        plan["removedAreaSquareMetres"],
        plan["retainedAreaSquareMetres"],
        plan["minimumHoleToExternalDeckEdgeMetres"],
    )


def capture_source():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "mar250_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = BASE_SHA
    return helper.capture_source()


def render_review(source, replacement):
    import bpy
    from mathutils import Vector

    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    camera = bpy.data.objects.new(
        "MAR250_temporary_review_camera",
        bpy.data.cameras.new("MAR250_temporary_review_camera"),
    )
    scene.collection.objects.link(camera)
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_shadows = False
    scene.display.shading.show_cavity = False
    scene.display.shading.background_type = "WORLD"
    scene.world.color = (0.82, 0.84, 0.85)
    scene.render.resolution_x, scene.render.resolution_y = 1200, 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for obj in scene.objects:
        if obj.type in {"MESH", "FONT", "CURVE"}:
            obj.hide_render = obj not in [source, replacement]
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 15.5
    target = Vector((10.8, 53.6, 17.5))
    for view, offset in [("plan", (0, 0, 35)), ("oblique", (10, -16, 26))]:
        camera.location = target + Vector(offset)
        camera.rotation_euler = (
            (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        for phase in ["before", "after"]:
            source.hide_render = phase != "before"
            replacement.hide_render = phase != "after"
            scene.render.filepath = str(OUT / f"{phase}-{view}.png")
            bpy.ops.render.render(write_still=True)


def build_component():
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene

    plan = json.loads((OUT / "plan.json").read_text())
    assert plan["baselineSha256"] == BASE_SHA == sha(BASE)
    component = OUT / "component.blend"
    assert not component.exists(), "Never overwrite a saved candidate component"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture_source()
    (OUT / "protected-source-state.json").write_text(json.dumps(before) + "\n")
    source = bpy.data.objects[plan["sourceObject"]]
    assert (
        not source.hide_render
        and object_fingerprint(source) == plan["sourceFingerprint"]
    )
    assert len(source.data.polygons) == 4
    assert not source.data.shape_keys
    assert not any(
        attribute.data_type == "FLOAT_COLOR" for attribute in source.data.attributes
    )
    points, polygons, records = [], [], []
    inverse = source.matrix_world.inverted()
    uv_checks = []
    for row in plan["sourceFacePlans"]:
        old_face = source.data.polygons[row["sourceFace"]]
        assert len(old_face.vertices) == 3
        original = [
            source.matrix_world @ source.data.vertices[index].co
            for index in old_face.vertices
        ]
        assert all(
            (actual - Vector(expected)).length < 2e-5
            for actual, expected in zip(original, row["sourcePoints"])
        )
        a, b, c = original
        determinant = (b.x - a.x) * (c.y - a.y) - (c.x - a.x) * (b.y - a.y)
        assert abs(determinant) > 1e-7
        for triangle in row["trianglesXY"]:
            triangle = list(triangle)
            determinant_new = (triangle[1][0] - triangle[0][0]) * (
                triangle[2][1] - triangle[0][1]
            ) - (triangle[2][0] - triangle[0][0]) * (triangle[1][1] - triangle[0][1])
            if determinant_new * determinant < 0:
                triangle.reverse()
            offset = len(points)
            points.extend(
                inverse @ Vector((x, y, plan["floorDatum"])) for x, y in triangle
            )
            polygons.append(tuple(range(offset, offset + 3)))
            corner_uvs = []
            for x, y in triangle:
                weight_b = (
                    (x - a.x) * (c.y - a.y) - (c.x - a.x) * (y - a.y)
                ) / determinant
                weight_c = (
                    (b.x - a.x) * (y - a.y) - (x - a.x) * (b.y - a.y)
                ) / determinant
                weights = [1 - weight_b - weight_c, weight_b, weight_c]
                assert min(weights) > -1e-5 and max(weights) < 1.00001
                layer_values = []
                for layer in source.data.uv_layers:
                    values = [layer.data[index].uv for index in old_face.loop_indices]
                    result = sum(
                        (value * weight for value, weight in zip(values, weights)),
                        Vector((0, 0)),
                    )
                    layer_values.append(list(result))
                    uv_checks.append(
                        {
                            "layer": layer.name,
                            "sourceFace": old_face.index,
                            "weights": weights,
                            "uv": list(result),
                        }
                    )
                corner_uvs.append(layer_values)
            records.append({"sourceFace": old_face.index, "uvs": corner_uvs})
    mesh = bpy.data.meshes.new(plan["ownedObject"])
    mesh.from_pydata(points, [], polygons)
    for material in source.data.materials:
        mesh.materials.append(material)
    for face, row in zip(mesh.polygons, records):
        old_face = source.data.polygons[row["sourceFace"]]
        face.material_index = old_face.material_index
        face.use_smooth = old_face.use_smooth
    for layer_index, source_layer in enumerate(source.data.uv_layers):
        layer = mesh.uv_layers.new(name=source_layer.name)
        for face, row in zip(mesh.polygons, records):
            for loop, corner in zip(face.loop_indices, row["uvs"]):
                layer.data[loop].uv = corner[layer_index]
        layer.active_render = source_layer.active_render
    mesh.update()
    assert not mesh.validate(clean_customdata=False)
    replacement = source.copy()
    replacement.name = plan["ownedObject"]
    replacement.data = mesh
    replacement.hide_render = False
    replacement.hide_set(False)
    replacement["publicInteriorComponent"] = True
    replacement["destinationCollection"] = plan["targetCollection"]
    replacement["webGeometrySource"] = source.name
    replacement["evidence_status"] = (
        "Three source2022structural lift-shaft openings at retained17.5mthird-floor;not complete lift cores"
    )
    bpy.data.collections[plan["targetCollection"]].objects.link(replacement)
    update_scene()
    after = capture_source()
    assert all(
        after["objects"][name] == state for name, state in before["objects"].items()
    )
    assert all(
        after["materials"][name] == state for name, state in before["materials"].items()
    )
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert set(after["objects"]) == set(before["objects"]) | {replacement.name}
    fingerprint = object_fingerprint(replacement)
    bpy.data.libraries.write(
        str(component), {replacement}, fake_user=True, compress=True
    )
    audit = {
        "version": 250,
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": sha(component),
        "targetCollection": plan["targetCollection"],
        "destinationCollection": plan["targetCollection"],
        "addedObjects": [replacement.name],
        "archivedObjects": [source.name],
        "changedObjects": [],
        "addedFingerprints": {replacement.name: fingerprint},
        "replacementMaterialBindings": {
            replacement.name: [
                m.name if m else None for m in replacement.data.materials
            ]
        },
        "sourceFitMaximumMetres": plan["sourceFitMaximumMetres"],
        "coreHeldOutMaximumMetres": plan["coreHeldOutMaximumMetres"],
        "perimeterCandidateMaximumMetres": plan["perimeterCandidateMaximumMetres"],
        "oldTriangles": len(source.data.polygons),
        "newTriangles": len(mesh.polygons),
        "sourceUVLayers": [layer.name for layer in source.data.uv_layers],
        "uvInterpolationSamples": len(uv_checks),
        "scope": "Remove only the three source-registered structural lift-shaft interiors from one retained17.5mdeck. Keep outer deck, corridor and inter-shaft strips, optics, all other floors and rooms.",
        "status": "candidate_requires_saved_mesh_and_visual_review",
        "limitations": plan["limitations"],
    }
    (OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    (OUT / "uv-interpolation.json").write_text(
        json.dumps(
            {"sourceObject": source.name, "faceRecords": records, "samples": uv_checks}
        )
        + "\n"
    )
    render_review(source, replacement)
    assert sha(BASE) == BASE_SHA
    print("MAR250_COMPONENT_WRITTEN", sha(component), len(mesh.polygons), flush=True)
    bpy.ops.wm.quit_blender()


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ModuleNotFoundError:
        prepare_source_plan()
    else:
        build_component()
