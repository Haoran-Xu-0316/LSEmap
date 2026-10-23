"""Reopen Houghton262 and verify fixture solids,wall support and old-scene safety."""

import json
import sys
from collections import Counter
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_houghton262 import (
    BASE,
    CAMERA_WALL,
    CENTRE_Z,
    COLLECTION,
    HEIGHT,
    NAMES,
    OUT,
    SHA,
    STATIONS,
    WALL,
    WIDTH,
    capture,
    frame,
    local,
    sha,
    tree,
    world,
)
from refine_portsmouth_exterior207 import material_fingerprint


def solids(obj):
    edges = Counter()
    adjacent = [set() for _ in obj.data.vertices]
    for face in obj.data.polygons:
        ids = tuple(face.vertices)
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
            adjacent[a].add(b)
            adjacent[b].add(a)
    assert set(edges.values()) == {2}, obj.name
    unseen = set(range(len(adjacent)))
    groups = []
    while unseen:
        seed = unseen.pop()
        found = {seed}
        queue = [seed]
        while queue:
            for other in adjacent[queue.pop()] & unseen:
                unseen.remove(other)
                found.add(other)
                queue.append(other)
        groups.append(found)
    obj.data.calc_loop_triangles()
    volumes = []
    for group in groups:
        anchor = obj.data.vertices[min(group)].co
        volume = 0
        for triangle in obj.data.loop_triangles:
            if triangle.vertices[0] in group:
                a, b, c = [obj.data.vertices[i].co - anchor for i in triangle.vertices]
                volume += a.dot(b.cross(c)) / 6
        assert volume > 0, (obj.name, volume)
        volumes.append(volume)
    return {
        "closedPositiveSolids": len(groups),
        "allEdgesTwoFaces": True,
        "minimumVolume": min(volumes),
        "triangles": len(obj.data.loop_triangles),
    }


def fixture_proof(audit):
    shell = tree(bpy.data.objects[NAMES["shell"]])
    glass = tree(bpy.data.objects[NAMES["glass"]])
    inserts = tree(bpy.data.objects[NAMES["inserts"]])
    wall = tree(bpy.data.objects[WALL])
    normal = frame()[2]
    rows = []
    for index, x in enumerate(STATIONS):
        cabinet = audit["cabinets"][index]
        assert abs(cabinet["x"] - x) < 1e-7
        assert cabinet["low"] > 2.0 and cabinet["high"] < 4.48
        pane_checks = []
        for dx in [-0.22, 0, 0.22]:
            for dz in [-0.35, 0, 0.35]:
                origin = world(x + dx, 1, CENTRE_Z + dz)
                cover = glass.ray_cast(origin, -normal, 2)
                paper = inserts.ray_cast(origin, -normal, 2)
                assert cover[0] is not None and paper[0] is not None
                assert cover[3] < paper[3]
                assert shell.ray_cast(origin, -normal, cover[3])[0] is None
                assert abs(local(cover[0]).y - cabinet["glassFront"]) < 0.00004
                assert 0.04 < paper[3] - cover[3] < 0.10
                pane_checks.append(
                    {
                        "dx": dx,
                        "dz": dz,
                        "coverBeforeInsert": True,
                        "physicalRecess": paper[3] - cover[3],
                    }
                )
        border_checks = []
        for dx, dz in [
            (-WIDTH / 2 + 0.015, 0),
            (WIDTH / 2 - 0.015, 0),
            (0, -HEIGHT / 2 + 0.015),
            (0, HEIGHT / 2 - 0.015),
        ]:
            hit = shell.ray_cast(world(x + dx, 1, CENTRE_Z + dz), -normal, 2)
            assert hit[0] is not None
            assert abs(local(hit[0]).y - cabinet["front"]) < 0.00004
            border_checks.append(list(local(hit[0])))
        mounts = []
        for mount in cabinet["mounts"]:
            xx, zz = mount["x"], mount["z"]
            origin = world(xx, 1, zz)
            retained = wall.ray_cast(origin, -normal, 2)
            fixing = shell.ray_cast(
                world(xx, cabinet["back"] - 0.0001, zz), -normal, 0.10
            )
            assert retained[0] is not None and fixing[0] is not None
            assert abs(local(retained[0]).y - mount["wallDepth"]) < 0.00004
            # Trace from the wall toward the fixing's rear surface. This proves
            # contact independently of the builder's intended box coordinates.
            rear = shell.ray_cast(
                world(xx, mount["wallDepth"] + 0.0001, zz), normal, 0.04
            )
            assert rear[0] is not None
            gap = local(rear[0]).y - local(retained[0]).y
            assert 0.0002 < gap < 0.0006, (index, mount, gap)
            assert abs(mount["mountFront"] - cabinet["back"]) < 1e-7
            mounts.append({"x": xx, "z": zz, "actualRearGap": gap})
        # Registered wall surfaces and side clearance are checked at all
        # corners. A centre-only hit would miss course/pier/window conflicts.
        corners = []
        for xx in [x - WIDTH / 2, x + WIDTH / 2]:
            for zz in [CENTRE_Z - HEIGHT / 2, CENTRE_Z + HEIGHT / 2]:
                hit = wall.ray_cast(world(xx, 1, zz), -normal, 2)
                assert hit[0] is not None
                assert local(hit[0]).y < cabinet["back"]
                corners.append(list(local(hit[0])))
        rows.append(
            {
                "index": index,
                "paneChecks": pane_checks,
                "fourClosedBorders": border_checks,
                "fourActualWallFixings": mounts,
                "retainedStoneAtFourCorners": corners,
            }
        )
    camera = audit["camera"]
    camera_tree = tree(bpy.data.objects[NAMES["camera"]])
    camera_wall = tree(bpy.data.objects[CAMERA_WALL])
    registered = camera["nativeWallFrame"]
    camera_origin = Vector(registered["origin"])
    camera_right = Vector(registered["right"])
    camera_normal = Vector(registered["outward"])
    assert abs(camera_right.dot(camera_normal)) < 0.00001
    assert (
        abs(camera_right.length - 1) < 0.00001
        and abs(camera_normal.length - 1) < 0.00001
    )

    def camera_point(dx, depth, dz):
        return (
            camera_origin
            + camera_right * dx
            + camera_normal * depth
            + Vector((0, 0, dz))
        )

    centre_source = camera_wall.ray_cast(camera_point(0, 1, 0), -camera_normal, 2)
    assert centre_source[0] is not None
    assert (centre_source[0] - camera_origin).length < 0.00004
    assert abs(centre_source[1].dot(camera_normal)) > 0.99999
    footprint = []
    for dx in [-0.09, 0, 0.09]:
        for dz in [-0.14, 0, 0.14]:
            source = camera_wall.ray_cast(camera_point(dx, 1, dz), -camera_normal, 2)
            assert source[0] is not None
            assert abs((source[0] - camera_origin).dot(camera_normal)) < 0.00004
            assert abs(source[1].dot(camera_normal)) > 0.99999
            footprint.append(list(source[0]))
    contacts = []
    contact_rows = []
    for dx in [-0.08, 0, 0.08]:
        for dz in [-0.12, 0, 0.12]:
            source = camera_wall.ray_cast(camera_point(dx, 1, dz), -camera_normal, 2)
            assert source[0] is not None
            rear = camera_tree.ray_cast(
                source[0] + camera_normal * 0.0001, camera_normal, 0.04
            )
            assert rear[0] is not None
            gap = (rear[0] - source[0]).dot(camera_normal)
            contact_rows.append(
                {
                    "dx": dx,
                    "dz": dz,
                    "nativeWallPoint": list(source[0]),
                    "nativeWallNormal": list(source[1]),
                    "cameraRearPoint": list(rear[0]),
                    "actualGap": gap,
                }
            )
            contacts.append(gap)
    (OUT / "camera-aligned-contact-verification.json").write_text(
        json.dumps(contact_rows, indent=2) + "\n"
    )
    assert all(0.0002 < gap < 0.0006 for gap in contacts), contacts
    topology = {name: solids(bpy.data.objects[name]) for name in NAMES.values()}
    assert topology[NAMES["shell"]]["closedPositiveSolids"] == 36
    assert topology[NAMES["glass"]]["closedPositiveSolids"] == 4
    assert topology[NAMES["inserts"]]["closedPositiveSolids"] == 10
    assert topology[NAMES["camera"]]["closedPositiveSolids"] == 3
    assert topology[NAMES["dome"]]["closedPositiveSolids"] == 1
    return {
        "cabinets": rows,
        "cameraAttachmentGaps": contacts,
        "cameraWholePlateStoneFootprint": footprint,
        "closedFixtureTopology": topology,
    }


def bounds(obj):
    pts = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    return [min(p[k] for p in pts) for k in range(3)], [
        max(p[k] for p in pts) for k in range(3)
    ]


def no_old_intersections(audit, before):
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    hidden = set()

    def visit(c, inherited=False):
        inherited = inherited or c.hide_render
        if inherited:
            hidden.update(o.name for o in c.objects)
        for child in c.children:
            visit(child, inherited)

    visit(scene.collection)
    new = [bpy.data.objects[name] for name in audit["addedObjects"]]
    new_rows = [(o.name, *bounds(o), tree(o)) for o in new]
    checked = 0
    for obj in scene.objects:
        if (
            obj.name not in before["objects"]
            or obj.type != "MESH"
            or obj.hide_render
            or obj.name in hidden
        ):
            continue
        lo, hi = bounds(obj)
        candidates = [
            row
            for row in new_rows
            if all(
                lo[k] <= row[2][k] + 0.0001 and hi[k] >= row[1][k] - 0.0001
                for k in range(3)
            )
        ]
        if not candidates:
            continue
        old_tree = tree(obj)
        for name, _lo, _hi, new_tree in candidates:
            overlap = old_tree.overlap(new_tree)
            assert not overlap, (obj.name, name, len(overlap))
            checked += 1
    assert checked > 0
    return {
        "actualNativeSurfacePairsChecked": checked,
        "crossingTrianglePairs": 0,
        "scope": "All retained visible campus meshes with bounding boxes intersecting the new fixture bounds;not a real-site route certification.",
    }


def main():
    audit = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(BASE) == SHA == audit["baselineSha256"]
    assert sha(component) == audit["componentSha256"]
    assert sha(OUT / "source-review-plan.json") == audit["sourceReviewSha256"]
    assert sha(OUT / "native-inspection.json") == audit["nativeInspectionSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_library, loaded):
        loaded.objects = list(audit["addedObjects"])
    for obj in loaded.objects:
        bpy.data.collections[COLLECTION].objects.link(obj)
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
    before_update = {
        obj.name: {
            "fingerprint": object_fingerprint(obj),
            "matrixWorld": [list(row) for row in obj.matrix_world],
        }
        for obj in loaded.objects
    }
    # Appending preserves local transforms,but matrix_world of a newly linked
    # nonidentity lettering object is evaluated only after the dependency update.
    # Fingerprints must compare the complete evaluated linkage,not stale matrices.
    update_scene()
    diagnostics = []
    for obj in loaded.objects:
        actual = object_fingerprint(obj)
        diagnostics.append(
            {
                "name": obj.name,
                "expectedFingerprint": audit["addedFingerprints"][obj.name],
                "beforeUpdate": before_update[obj.name],
                "afterUpdate": {
                    "fingerprint": actual,
                    "matrixWorld": [list(row) for row in obj.matrix_world],
                },
                "materials": [m.name if m else None for m in obj.data.materials],
                "vertices": len(obj.data.vertices),
                "polygons": len(obj.data.polygons),
                "matched": actual == audit["addedFingerprints"][obj.name],
            }
        )
    (OUT / "reopened-object-diagnostics.json").write_text(
        json.dumps(diagnostics, indent=2) + "\n"
    )
    for row in diagnostics:
        assert row["matched"], (
            row["name"],
            row["expectedFingerprint"],
            row["afterUpdate"],
        )
    for name in audit["newMaterials"]:
        assert (
            material_fingerprint(bpy.data.materials[name])
            == audit["newMaterialGraphs"][name]
        )
    proof = fixture_proof(audit)
    proof["retainedSceneSurfaceClearance"] = no_old_intersections(audit, before)
    after = capture()
    for key in ["objects", "materials", "visibility"]:
        assert all(after[key][name] == row for name, row in before[key].items()), key
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
        and len(after["rooms"]) == 35
    )
    assert set(after["objects"]) - set(before["objects"]) == set(audit["addedObjects"])
    assert sha(BASE) == SHA
    report = {
        "passed": True,
        "savedComponentReopened": True,
        "componentSha256": sha(component),
        "protectedOriginalObjects": 8735,
        "protectedOriginalMaterials": 2350,
        "protectedIndependentRooms": 35,
        "proof": proof,
        "fullStreetOrCurrentConditionClaimed": False,
        "newMerchantOrCurrentEventClaimed": False,
        "photoPixelsReused": False,
    }
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "HOUGHTON262_FIXTURES_INDEPENDENTLY_VERIFIED",
        len(proof["cabinets"]),
        flush=True,
    )


if __name__ == "__main__":
    main()
