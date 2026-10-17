"""Independent saved-mesh review of the private SAW upper stair candidate.

Blender reopens the saved component and verifies original lower geometry/UVs.
MachineLearning then clips actual saved triangles against every usable tread
and checks source-constrained floor links. No command-line arguments are used.
A passing planar study alone cannot authorize full-campus integration.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw-circulation242"
BASE = ROOT / "result/blender/LSE_campus_detailed_v241.blend"
BASE_SHA = "3b49385387b8e5c53223a1151762b80b9b3e1e4c2bbfbd474dfa820af4e424b4"


def read(name):
    return json.loads((OUT / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified_native_source():
    """Use the retained current native once its superseded baseline is retired."""
    if BASE.is_file():
        assert sha(BASE) == BASE_SHA
        return BASE
    current = ROOT / "result/blender/LSE_campus_detailed_v242.blend"
    accepted = json.loads(
        (ROOT / "result/blender/stage242/native-verification.json").read_text()
    )
    assert accepted[
        "allOriginalGeometryNormalsUVsModifiersPropertiesAndOwnersPreserved"
    ]
    assert sha(current) == accepted["sourceModelSha256"]
    return current


def reopen_component():
    import sys

    import bmesh
    import bpy

    sys.path.insert(0, str(ROOT / "web/tools"))
    sys.dont_write_bytecode = True
    from integrate_exterior_round194 import accepted_fingerprints, object_fingerprint
    from refine_kgs_surface237 import normal_record

    record = read("component-record.json")
    assert record["baselineSha256"] == BASE_SHA
    native_source = verified_native_source()
    native_sha = sha(native_source)
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(component), link=False) as (_, target):
        target.objects = list(record["addedObjects"])
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    for name in record["addedObjects"]:
        obj = bpy.data.objects[name]
        assert object_fingerprint(obj) == record["addedFingerprints"][name], name
        assert normal_record(obj.data) == record["replacementNormals"][name], name
    # Read the actual three lower batches from the accepted native independently.
    originals = [row["source"] for row in record["retention"]]
    with bpy.data.libraries.load(str(native_source), link=False) as (_, target):
        target.objects = list(originals)
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.update()
    expected = accepted_fingerprints(ROOT / "result/blender/stage241", BASE_SHA)
    retained_faces = 0
    for row in record["retention"]:
        source = bpy.data.objects[row["source"]]
        replacement = bpy.data.objects[row["replacement"]]
        bindings = record["replacementMaterialBindings"][replacement.name]
        for index, name in enumerate(bindings):
            source.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(source) == expected[source.name]
        assert source.matrix_world == replacement.matrix_world
        selected = [source.data.polygons[i] for i in row["sourceFaces"]]
        assert len(selected) == len(replacement.data.polygons)
        assert [layer.name for layer in source.data.uv_layers] == [
            layer.name for layer in replacement.data.uv_layers
        ]
        for original, copy in zip(selected, replacement.data.polygons, strict=True):
            assert (
                original.material_index == copy.material_index
                and original.use_smooth == copy.use_smooth
            )
            assert [tuple(source.data.vertices[i].co) for i in original.vertices] == [
                tuple(replacement.data.vertices[i].co) for i in copy.vertices
            ]
            for old_layer, new_layer in zip(
                source.data.uv_layers, replacement.data.uv_layers, strict=True
            ):
                assert [tuple(old_layer.data[i].uv) for i in original.loop_indices] == [
                    tuple(new_layer.data[i].uv) for i in copy.loop_indices
                ]
        retained_faces += len(selected)
    rows = []
    solids = []
    for name in record["addedObjects"]:
        obj = bpy.data.objects[name]
        obj.data.calc_loop_triangles()
        if "Coordinated_floor" in name:
            assert all(face.normal.z > 0.99 for face in obj.data.polygons), name
        if "continuous_winding_waist" in name:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            assert all(edge.is_manifold for edge in bm.edges)
            assert not any(not v.link_edges for v in bm.verts)
            volume = bm.calc_volume(signed=True)
            assert volume > 0
            solids.append({"object": name, "closedManifold": True, "volumeM3": volume})
            bm.free()
        rows.append(
            {
                "name": name,
                "vertices": [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                "faces": [list(p.vertices) for p in obj.data.polygons],
                "triangles": [list(t.vertices) for t in obj.data.loop_triangles],
            }
        )
    result = {
        "baselineSha256": BASE_SHA,
        "componentSha256": sha(component),
        "savedComponentReopened": True,
        "retainedLowerFacesVerified": retained_faces,
        "lowerCoordinatesUVsMaterialIndicesAndSmoothFlagsUnchanged": True,
        "solids": solids,
        "objects": rows,
    }
    (OUT / "reopened-surfaces.json").write_text(
        json.dumps(result, separators=(",", ":")) + "\n"
    )
    assert sha(native_source) == native_sha
    print("SAW242_COMPONENT_REOPENED", len(rows), retained_faces, solids, flush=True)


def prove_clearance():
    import importlib.util

    import numpy as np
    from shapely.geometry import LineString, Point, Polygon, mapping, shape
    from shapely.ops import unary_union

    spec = importlib.util.spec_from_file_location(
        "planner242", ROOT / "web/tools/plan_saw_upper242.py"
    )
    planner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(planner)
    unit_floor = {
        "name": "two-sided-floor-regression",
        "vertices": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
        "faces": [[0, 1, 2], [0, 3, 2]],
    }
    assert (
        abs(
            unary_union(
                [
                    r["polygon"]
                    for r in planner.horizontal_surfaces(unit_floor, two_sided=True)
                ]
            ).area
            - 1
        )
        < 1e-9
    )
    assert (
        abs(
            unary_union(
                [r["polygon"] for r in planner.horizontal_surfaces(unit_floor)]
            ).area
            - 0.5
        )
        < 1e-9
    )
    record = read("component-record.json")
    saved = read("reopened-surfaces.json")
    data = read("geometry-plan.json")
    assert sha(OUT / "geometry-plan.json") == record["geometryPlanSha256"]
    baseline = read("current-surfaces.json")
    assert (
        saved["componentSha256"]
        == sha(ROOT / record["componentPath"])
        == record["componentSha256"]
    )
    assert baseline["baselineSha256"] == BASE_SHA
    verified_native_source()
    rows = [
        row
        for row in baseline["objects"]
        if row["name"] not in record["archivedObjects"]
    ] + saved["objects"]
    walking = [
        surface
        for row in saved["objects"]
        if "continuous_winding_waist" in row["name"]
        for surface in planner.horizontal_surfaces(row)
    ]
    matches = []
    for expected in data["walkingSurfaces"]:
        actual = [
            row
            for row in walking
            if abs(row["top"] - expected["top"]) < 1e-4
            and f"Flight{expected['flight']}_" in row["object"]
        ]
        polygon = unary_union([row["polygon"] for row in actual])
        assert (
            actual
            and polygon.symmetric_difference(shape(expected["polygon"])).area < 0.0001
        )
        matches.extend(actual)
    assert len(matches) == len(walking)

    def clip(points, normal, offset):
        result = []
        for a, b in zip(points, points[1:] + points[:1]):
            da = float(np.dot(normal, a) - offset)
            db = float(np.dot(normal, b) - offset)
            if da >= -1e-8:
                result.append(a)
            if (da >= 0) != (db >= 0):
                result.append(a + (b - a) * (da / (da - db)))
        return result

    def area3(points):
        if len(points) < 3:
            return 0
        return sum(
            np.linalg.norm(np.cross(points[i] - points[0], points[i + 1] - points[0]))
            / 2
            for i in range(1, len(points) - 1)
        )

    triangles = []
    for row in rows:
        vertices = np.array(row["vertices"])
        faces = vertices[np.array(row["triangles"])]
        if len(faces):
            triangles.append((row["name"], faces, faces.min(1), faces.max(1)))
    retained_walks = [
        surface
        for row in rows
        if row["name"].startswith("SAW233_Flight")
        for surface in planner.horizontal_surfaces(row)
        if 8.09 <= surface["top"] <= 11.1001
    ]
    conflicts = []
    tested = 0
    for number, walk in enumerate([*matches, *retained_walks]):
        polygon = walk["polygon"].buffer(-0.0001, join_style=2)
        ring = np.array(polygon.exterior.coords[:-1])
        if (
            sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(ring, np.roll(ring, -1, axis=0))
            )
            < 0
        ):
            ring = ring[::-1]
        planes = []
        for a, b in zip(ring, np.roll(ring, -1, axis=0)):
            edge = b - a
            normal = np.array([-edge[1], edge[0], 0.0])
            planes.append((normal, float(np.dot(normal[:2], a))))
        low, high = walk["top"] + 0.005, walk["top"] + 2.1
        planes.extend(
            [(np.array([0.0, 0.0, 1.0]), low), (np.array([0.0, 0.0, -1.0]), -high)]
        )
        minx, miny, maxx, maxy = polygon.bounds
        for name, faces, minimum, maximum in triangles:
            mask = (
                (maximum[:, 0] > minx + 1e-6)
                & (minimum[:, 0] < maxx - 1e-6)
                & (maximum[:, 1] > miny + 1e-6)
                & (minimum[:, 1] < maxy - 1e-6)
                & (maximum[:, 2] > low + 1e-6)
                & (minimum[:, 2] < high - 1e-6)
            )
            for index in np.where(mask)[0]:
                tested += 1
                points = list(faces[index])
                for normal, offset in planes:
                    points = clip(points, normal, offset)
                    if len(points) < 3:
                        break
                area = area3(points)
                if area > 1e-7:
                    conflicts.append(
                        {
                            "walk": number,
                            "walkObject": walk["object"],
                            "walkTop": walk["top"],
                            "obstacle": name,
                            "triangle": int(index),
                            "clippedAreaM2": float(area),
                        }
                    )
    lifts = unary_union(
        [
            shape(row)
            for row in json.loads(
                (ROOT / "result/blender/saw-circulation233/plan.json").read_text()
            )["lifts"]
        ]
    )
    after_lift = []
    for row in rows:
        if not any(
            part in row["name"]
            for part in [
                "registered_main_treads",
                "continuous_waists",
                "continuous_winding_waist",
                "ST04_continuous_spiral",
            ]
        ):
            continue
        for walk in planner.horizontal_surfaces(row):
            area = walk["polygon"].intersection(lifts).area
            if area > 1e-5:
                after_lift.append(
                    {"object": row["name"], "top": walk["top"], "overlapM2": area}
                )
    zones = {
        row["page"]: shape(row["worldWhiteRegion"])
        for row in read("vector-source-white-zones.json")["records"]
    }
    partial = {
        "conflicts": conflicts,
        "remainingLiftConflicts": after_lift,
        "matchedSavedWalkingFaces": len(matches),
        "retainedWalkingFacesRechecked": len(retained_walks),
        "status": "Headroom review complete; horizontal routes pending",
    }
    (OUT / "partial-clearance-proof.json").write_text(
        json.dumps(partial, separators=(",", ":")) + "\n"
    )
    floor_checks = []
    for floor in data["floors"]:
        datum = floor["datum"]
        page = {11.1: 29, 14.1: 28, 18.0: 27}[datum]
        actual = unary_union(
            [
                surface["polygon"]
                for row in saved["objects"]
                if row["name"] == floor["name"]
                for surface in planner.horizontal_surfaces(row, two_sided=True)
            ]
        )
        assert actual.symmetric_difference(shape(floor["polygon"])).area < 0.003
        old_floor_name = next(
            row["source"] for row in data["objects"] if row["name"] == floor["name"]
        )
        landing_name = next(
            row["name"]
            for row in baseline["objects"]
            if row["name"].endswith("coordinated_shared_floor_landings")
        )
        old_support = unary_union(
            [
                surface["polygon"]
                for row in baseline["objects"]
                if row["name"] in [old_floor_name, landing_name]
                for surface in planner.horizontal_surfaces(
                    row, two_sided=row["name"] == old_floor_name
                )
                if abs(surface["top"] - datum) < 0.001
            ]
        )
        outside_difference = (
            actual.difference(shape(floor["editRegion"]))
            .symmetric_difference(old_support.difference(shape(floor["editRegion"])))
            .area
        )
        assert outside_difference < 0.003, (datum, outside_difference)

        blocked = []
        low, high = datum + 0.005, datum + 2.1
        for name, faces, minimum, maximum in triangles:
            mask = (maximum[:, 2] > low + 1e-6) & (minimum[:, 2] < high - 1e-6)
            for triangle in faces[mask]:
                points = list(triangle)
                for normal, offset in [
                    (np.array([0.0, 0.0, 1.0]), low),
                    (np.array([0.0, 0.0, -1.0]), -high),
                ]:
                    points = clip(points, normal, offset)
                    if len(points) < 2:
                        break
                if len(points) >= 3:
                    polygon = Polygon([point[:2] for point in points])
                    if polygon.area > 1e-9:
                        blocked.append(polygon.buffer(0.001))
                    elif polygon.length > 1e-7:
                        blocked.append(
                            LineString([point[:2] for point in points]).buffer(0.001)
                        )
        # The retained lower assembly uses documented3mm slab/tread seams.
        # Include actual level treads and close only that5mm authoring tolerance
        # before subtracting real obstacles; never close a wall/guard barrier.
        level_treads = [
            surface["polygon"]
            for row in rows
            if any(
                part in row["name"]
                for part in [
                    "registered_main_treads",
                    "continuous_waists",
                    "continuous_winding_waist",
                    "ST04_continuous_spiral",
                ]
            )
            for surface in planner.horizontal_surfaces(row)
            if abs(surface["top"] - datum) < 0.001
        ]
        support = (
            unary_union([actual, *level_treads])
            .buffer(0.0025, join_style=2)
            .buffer(-0.0025, join_style=2)
        )
        clear = support.intersection(zones[page]).difference(unary_union(blocked))
        if datum == 14.1:
            lower, upper = data["routes"]
            arrival = np.array(lower["end"]) + np.array(lower["endDirection"]) * 0.65
            departure = (
                np.array(upper["start"]) - np.array(upper["startDirection"]) * 0.65
            )
        elif datum == 11.1:
            lower = json.loads(
                (ROOT / "result/blender/saw-circulation233/plan.json").read_text()
            )["routes"][1]
            arrival = (
                np.array(lower["end"]) + np.array(lower["runDirections"][1]) * 0.65
            )
            upper = data["routes"][0]
            departure = (
                np.array(upper["start"]) - np.array(upper["startDirection"]) * 0.65
            )
        else:
            lower = data["routes"][1]
            arrival = np.array(lower["end"]) + np.array(lower["endDirection"]) * 0.65
            spiral = next(
                row
                for row in baseline["objects"]
                if row["name"].startswith("SAW223_ST04_continuous_spiral")
            )
            surfaces = planner.horizontal_surfaces(spiral)
            levels = sorted(
                {round(row["top"], 4) for row in surfaces if row["top"] > 18.01}
            )
            first_height, second_height = levels[:2]
            first = unary_union(
                [
                    row["polygon"]
                    for row in surfaces
                    if abs(row["top"] - first_height) < 0.001
                ]
            )
            second = unary_union(
                [
                    row["polygon"]
                    for row in surfaces
                    if abs(row["top"] - second_height) < 0.001
                ]
            )
            direction = np.array(second.centroid.coords[0]) - np.array(
                first.centroid.coords[0]
            )
            direction /= np.linalg.norm(direction)
            departure = np.array(first.centroid.coords[0]) - direction * 0.8
        checks = []
        for width in [1.1, 0.8, 0.6, 0.4]:
            eroded = clear.buffer(-width / 2, join_style=2)
            components = list(eroded.geoms) if hasattr(eroded, "geoms") else [eroded]
            connected = any(
                region.distance(Point(arrival)) < 0.08
                and region.distance(Point(departure)) < 0.08
                for region in components
            )
            checks.append({"width": width, "connected": connected})
        floor_checks.append(
            {
                "datum": datum,
                "anchors": [arrival.tolist(), departure.tolist()],
                "checks": checks,
                "actualFullHeightClearRegion": mapping(clear),
                "outsideEditFloorFootprintDifferenceM2": outside_difference,
            }
        )
    result = {
        "savedActualMeshVerified": True,
        "componentSha256": saved["componentSha256"],
        "baselineSha256": BASE_SHA,
        "fullUsableWidthHeadroomHeight": 2.1,
        "inheritedFloorTreadSeamToleranceM": 0.005,
        "headroomStartOffset": 0.005,
        "matchedSavedWalkingFaces": len(matches),
        "retainedWalkingFacesRechecked": len(retained_walks),
        "broadPhaseTrianglePairsTested": tested,
        "actualTriangleHeadroomConflicts": conflicts,
        "conflictCount": len(conflicts),
        "remainingLiftConflicts": after_lift,
        "remainingLiftConflictCount": len(after_lift),
        "floorConnections": floor_checks,
        "status": "accepted-for-native-integration"
        if not conflicts
        and not after_lift
        and all(row["checks"][0]["connected"] for row in floor_checks)
        else "rejected-do-not-integrate",
        "limitations": "Historical source and authoring estimates; not a current survey, accessibility or safety certification.",
    }
    (OUT / "saved-triangle-proof.json").write_text(
        json.dumps(result, separators=(",", ":")) + "\n"
    )
    print(
        "SAW242_SAVED_TRIANGLE_PROOF",
        len(matches),
        len(conflicts),
        len(after_lift),
        [(row["datum"], row["checks"][0]["connected"]) for row in floor_checks],
        flush=True,
    )
    if conflicts:
        print("FIRST_CONFLICTS", conflicts[:8], flush=True)
    assert result["status"] == "accepted-for-native-integration", result["status"]


if __name__ == "__main__":
    try:
        import bpy
    except ImportError:
        bpy = None
    if bpy is None:
        prove_clearance()
    else:
        reopen_component()
