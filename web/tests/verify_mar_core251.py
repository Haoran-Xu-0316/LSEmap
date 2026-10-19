"""Reopen MAR251 and verify protected native state, access and structural contact.

Run in Blender for actual saved-mesh/native rays, then project Python for an
independent cross-section and top-cap coverage comparison. No full native save.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar-core251"
BASE = ROOT / "result/blender/LSE_campus_detailed_v250.blend"
SHA = "833c92b1af57b5c60fbf6f7cd85deb35ea506f680beefcbf6ffde502516dc4ee"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def verify_native():
    import bmesh
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint, update_scene
    from refine_mar_core251 import capture_source, mesh_tree, native_context

    plan = json.loads((OUT / "plan.json").read_text())
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert digest(component) == audit["componentSha256"] and digest(BASE) == SHA
    bpy.ops.wm.open_mainfile(filepath=str(component))
    wall = bpy.data.objects[plan["ownedObject"]]
    assert object_fingerprint(wall) == audit["addedFingerprints"][wall.name]
    bm = bmesh.new()
    bm.from_mesh(wall.data)
    assert all(edge.is_manifold for edge in bm.edges)
    volume = bm.calc_volume(signed=True)
    assert volume > 0 and abs(volume - plan["expectedVolumeCubicMetres"]) < 0.0002
    unseen = set(bm.verts)
    components = 0
    while unseen:
        components += 1
        pending = [unseen.pop()]
        while pending:
            current = pending.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    pending.append(other)
    bm.free()
    assert components == 2, components
    metric_errors = []
    for face in wall.data.polygons:
        vertices = [wall.matrix_world @ wall.data.vertices[i].co for i in face.vertices]
        uvs = [wall.data.uv_layers[0].data[i].uv for i in face.loop_indices]
        for i in range(len(vertices)):
            error = abs(
                (vertices[(i + 1) % len(vertices)] - vertices[i]).length
                - (uvs[(i + 1) % len(uvs)] - uvs[i]).length
            )
            assert error < 0.00002, (face.index, error)
            metric_errors.append(error)
    write(
        "saved-mesh.json",
        {
            "positions": [list(wall.matrix_world @ v.co) for v in wall.data.vertices],
            "faces": [list(p.vertices) for p in wall.data.polygons],
        },
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture_source() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = list(audit["addedObjects"])
    wall = loaded.objects[0]
    bpy.data.collections[audit["targetCollection"]].objects.link(wall)
    for i, name in enumerate(audit["replacementMaterialBindings"][wall.name]):
        wall.data.materials[i] = bpy.data.materials[name]
    update_scene()
    after = capture_source()
    assert set(after["objects"]) == set(before["objects"]) | {wall.name}
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
    assert object_fingerprint(wall) == audit["addedFingerprints"][wall.name]
    context = native_context(wall)
    deck = mesh_tree(bpy.data.objects[context["deck"]])
    upper = mesh_tree(bpy.data.objects[context["nextFloor"]])
    tree = mesh_tree(wall)
    low, top = plan["height"]["base"], plan["height"]["top"]
    height = plan["height"]["estimatedDoorClearHeight"]
    points = [wall.matrix_world @ v.co for v in wall.data.vertices]
    foot_sites = [p for p in points if abs(p.z - low) < 0.00002]
    top_sites = [p for p in points if abs(p.z - top) < 0.00002]
    for face in wall.data.polygons:
        sites = [points[i] for i in face.vertices]
        if all(abs(p.z - low) < 0.00002 for p in sites):
            foot_sites.append(sum(sites, Vector()) / len(sites))
        if all(abs(p.z - top) < 0.00002 for p in sites):
            top_sites.append(sum(sites, Vector()) / len(sites))
    for point in foot_sites:
        hit = deck.ray_cast(point + Vector((0, 0, 0.01)), Vector((0, 0, -1)), 0.02)[0]
        assert hit is not None and abs(hit.z - point.z) < 0.00002, (
            "unseated foot",
            list(point),
        )
    for point in top_sites:
        hit = upper.ray_cast(point + Vector((0, 0, 0.01)), Vector((0, 0, -1)), 0.02)[0]
        assert hit is not None and abs(hit.z - point.z) < 0.00002, (
            "top-floor gap",
            list(point),
        )
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    depsgraph = bpy.context.evaluated_depsgraph_get()
    doors = []
    for door in plan["doors"]:
        centre = Vector(door["centre"])
        normal = Vector(door["normal"])
        along = Vector((-normal.y, normal.x))
        clear = 0
        for offset in [-0.30, 0, 0.30]:
            for z in [0.25, 1.05, 2.0]:
                point = centre + along * offset * door["widthMetres"] - normal * 0.55
                origin = Vector((*point, low + z))
                direction = Vector((*normal, 0))
                assert tree.ray_cast(origin, direction, 1.1)[0] is None, (
                    door["id"],
                    offset,
                    z,
                )
                assert not scene.ray_cast(depsgraph, origin, direction, distance=1.1)[
                    0
                ], ("existing obstruction", door["id"], offset, z)
                clear += 1
        origin = Vector((*(centre - normal * 0.55), low + height + 0.12))
        direction = Vector((*normal, 0))
        assert tree.ray_cast(origin, direction, 1.1)[0] is not None, (
            "missing head",
            door["id"],
        )
        for sign in [-1, 1]:
            point = (
                centre + along * sign * (door["widthMetres"] / 2 + 0.07) - normal * 0.55
            )
            assert (
                tree.ray_cast(Vector((*point, low + 1.0)), direction, 1.1)[0]
                is not None
            ), ("missing jamb", door["id"], sign)
        doors.append(
            {
                "id": door["id"],
                "sourceWidthMetres": door["widthMetres"],
                "clearActualSceneRays": clear,
                "estimatedHeight": height,
                "lintelAndBothJambsPresent": True,
            }
        )
    voids = 0
    inherited_caps = []
    for index, ring in enumerate(plan["shaftHoles"]):
        corners = [Vector(point) for point in ring[:4]]
        for i in range(1, 10):
            for j in range(1, 10):
                point = (
                    corners[0]
                    .lerp(corners[1], i / 10)
                    .lerp(corners[3].lerp(corners[2], i / 10), j / 10)
                )
                origin = Vector((*point, low + 0.01))
                direction = Vector((0, 0, 1))
                assert tree.ray_cast(origin, direction, top - low + 0.02)[0] is None, (
                    "new shaft cap",
                    index,
                )
                assert not scene.ray_cast(
                    depsgraph, origin, direction, distance=top - low - 0.03
                )[0], ("storey shaft obstruction", index)
                voids += 1
        point = sum(corners, Vector((0, 0))) / 4
        inherited_caps.append(
            {
                "shaft": index,
                "upperUnmodifiedGenericFloorCoversCentre": upper.ray_cast(
                    Vector((*point, top + 0.01)), Vector((0, 0, -1)), 0.02
                )[0]
                is not None,
            }
        )
    assert digest(BASE) == SHA
    write(
        "saved-verification.json",
        {
            "savedComponentReopened": True,
            "componentSha256": digest(component),
            "baselineSha256": SHA,
            "sourceNativeUnchanged": True,
            "originalObjectsPreserved": len(before["objects"]),
            "originalMaterialsPreserved": len(before["materials"]),
            "roomsPreserved": len(before["rooms"]),
            "roomMembersPreserved": sum(len(v) for v in before["rooms"].values()),
            "closedManifold": True,
            "connectedConcreteCores": components,
            "positiveVolumeCubicMetres": volume,
            "metricUvEdgesChecked": len(metric_errors),
            "maximumMetricUvError": max(metric_errors),
            "wallFootContactRays": len(foot_sites),
            "wallTopContactRays": len(top_sites),
            "sourceWidthDoors": doors,
            "shaftInteriorClearActualSceneRays": voids,
            "newShaftCaps": 0,
            "nativeContext": context,
            "inheritedUpperFloorLimit": inherited_caps,
            "wholeNativeSaved": False,
            "originalFloorsModified": False,
        },
    )
    print(
        "MAR251_SAVED_VERIFIED",
        volume,
        "door-rays",
        sum(d["clearActualSceneRays"] for d in doors),
        "shaft-rays",
        voids,
        flush=True,
    )
    bpy.ops.wm.quit_blender()


def verify_sections():
    from shapely.geometry import LineString, Polygon
    from shapely.ops import polygonize, unary_union

    plan = json.loads((OUT / "plan.json").read_text())
    mesh = json.loads((OUT / "saved-mesh.json").read_text())
    assert digest(ROOT / plan["sourcePdf"]) == plan["sourcePdfSha256"]
    checks = []
    for key, z in [
        ("lowerFootprint", plan["height"]["base"] + 0.5),
        (
            "upperFootprint",
            plan["height"]["base"] + plan["height"]["estimatedDoorClearHeight"] + 0.2,
        ),
    ]:
        expected = unary_union(
            [Polygon(row["outer"], row["holes"]) for row in plan[key]]
        )
        lines = []
        for face in mesh["faces"]:
            points = [mesh["positions"][i] for i in face]
            hits = []
            for a, b in zip(points, points[1:] + points[:1]):
                if (a[2] - z) * (b[2] - z) < 0:
                    t = (z - a[2]) / (b[2] - a[2])
                    hits.append([a[i] + t * (b[i] - a[i]) for i in [0, 1]])
            if len(hits) == 2:
                lines.append(LineString(hits))
        actual = unary_union(
            [
                poly
                for poly in polygonize(unary_union(lines))
                if expected.buffer(0.00002).covers(poly.representative_point())
            ]
        )
        error = actual.symmetric_difference(expected).area
        assert error < 0.0005, (key, error)
        checks.append(
            {
                "section": key,
                "height": z,
                "areaSquareMetres": actual.area,
                "symmetricDifferenceSquareMetres": error,
            }
        )
    top = plan["height"]["top"]
    caps = unary_union(
        [
            Polygon([mesh["positions"][i][:2] for i in face])
            for face in mesh["faces"]
            if all(abs(mesh["positions"][i][2] - top) < 0.00002 for i in face)
        ]
    )
    wells = unary_union([Polygon(points) for points in plan["shaftHoles"]])
    assert caps.intersection(wells).area < 0.00005
    write(
        "section-verification.json",
        {
            "actualSavedCrossSections": checks,
            "newTopCapOverlapWithShaftInteriorSquareMetres": caps.intersection(
                wells
            ).area,
            "actualSourcePdfHashVerified": True,
        },
    )
    print(
        "MAR251_SECTIONS_VERIFIED",
        [row["symmetricDifferenceSquareMetres"] for row in checks],
    )


if __name__ == "__main__":
    try:
        import bpy  # noqa: F401
    except ModuleNotFoundError:
        verify_sections()
    else:
        verify_native()
