"""Fresh native verification of MAR's Second-floor-only three-shaft candidate.

Uses actual closed meshes, original faces, ray airspace and material graphs.
No authoring geometry functions are imported. Passing these bounded checks does
not accept full-height coordination with the retained third-floor deck/core.
"""

import collections
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/mar269"
OWNER = "MAR_PUBLIC_INTERIOR_study"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_houghton262 import capture
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def rows(obj):
    obj.data.calc_loop_triangles()
    return [
        tuple(obj.matrix_world @ obj.data.vertices[i].co for i in t.vertices)
        for t in obj.data.loop_triangles
    ]


def tree(triangles):
    return BVHTree.FromPolygons(
        [p for t in triangles for p in t],
        [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(triangles))],
        all_triangles=True,
        epsilon=0,
    )


def inside(point, ring):
    x, y = point[:2]
    result = False
    for a, b in zip(ring, ring[1:] + ring[:1], strict=False):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            result = not result
    return result


def gap_to_edge(point, ring):
    result = float("inf")
    for a, b in zip(ring, ring[1:] + ring[:1], strict=False):
        u, v = b[0] - a[0], b[1] - a[1]
        t = max(
            0, min(1, ((point[0] - a[0]) * u + (point[1] - a[1]) * v) / (u * u + v * v))
        )
        result = min(
            result, math.hypot(point[0] - a[0] - t * u, point[1] - a[1] - t * v)
        )
    return result


def samples(ring):
    lo = [min(p[i] for p in ring) for i in range(2)]
    hi = [max(p[i] for p in ring) for i in range(2)]
    result = []
    for i in range(1, 10):
        for j in range(1, 10):
            p = [lo[0] + (hi[0] - lo[0]) * i / 10, lo[1] + (hi[1] - lo[1]) * j / 10]
            if inside(p, ring) and gap_to_edge(p, ring) > 0.025:
                result.append(p)
    assert len(result) > 30
    return result


def signature(obj, face):
    corners = []
    for index in face.loop_indices:
        point = (
            obj.matrix_world @ obj.data.vertices[obj.data.loops[index].vertex_index].co
        )
        corners.append(
            (
                tuple(point),
                tuple((uv.name, tuple(uv.data[index].uv)) for uv in obj.data.uv_layers),
            )
        )
    canonical = min(tuple(corners[i:] + corners[:i]) for i in range(len(corners)))
    return face.material_index, face.use_smooth, canonical


def solid_proof(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    directed = collections.Counter(
        (a, b)
        for face in obj.data.polygons
        for a, b in zip(
            list(face.vertices),
            list(face.vertices)[1:] + list(face.vertices)[:1],
            strict=False,
        )
    )
    assert all(count == directed[(b, a)] for (a, b), count in directed.items()), (
        obj.name
    )
    assert all(e.is_manifold for e in bm.edges), obj.name
    pending = set(bm.verts)
    parts = 0
    while pending:
        parts += 1
        todo = [pending.pop()]
        while todo:
            for edge in todo.pop().link_edges:
                for v in edge.verts:
                    if v in pending:
                        pending.remove(v)
                        todo.append(v)
    assert parts == 1 and all(v.link_edges for v in bm.verts)
    volume = bm.calc_volume(signed=True)
    assert volume > 0
    bm.free()
    return volume


def polygon_area(ring):
    return (
        abs(
            sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(ring, ring[1:] + ring[:1], strict=False)
            )
        )
        / 2
    )


def polygon_centroid(ring):
    cross = [
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(ring, ring[1:] + ring[:1], strict=False)
    ]
    total = sum(cross)
    assert abs(total) > 1e-9
    return [
        sum(
            (a[i] + b[i]) * w
            for a, b, w in zip(ring, ring[1:] + ring[:1], cross, strict=False)
        )
        / (3 * total)
        for i in range(2)
    ]


def clipped_area(subject, triangle):
    clip = [tuple(p[:2]) for p in triangle]
    sign = sum(
        a[0] * b[1] - b[0] * a[1]
        for a, b in zip(clip, clip[1:] + clip[:1], strict=False)
    )
    if abs(sign) < 1e-12:
        return 0.0
    orientation = 1 if sign > 0 else -1
    points = [tuple(p[:2]) for p in subject]
    for a, b in zip(clip, clip[1:] + clip[:1], strict=False):
        output = []

        def side(p, a=a, b=b):
            return orientation * (
                (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
            )

        if not points:
            break
        previous = points[-1]
        sp = side(previous)
        for current in points:
            sc = side(current)
            if (sc >= 0) != (sp >= 0):
                t = sp / (sp - sc)
                output.append(
                    (
                        previous[0] + t * (current[0] - previous[0]),
                        previous[1] + t * (current[1] - previous[1]),
                    )
                )
            if sc >= 0:
                output.append(current)
            previous, sp = current, sc
        points = output
    return polygon_area(points) if len(points) > 2 else 0.0


def top_boundary_loops(obj, height):
    edges = collections.Counter()
    directed = []
    for triangle in rows(obj):
        if not all(abs(p.z - height) < 0.00001 for p in triangle):
            continue
        points = [tuple(p) for p in triangle]
        for a, b in zip(points, points[1:] + points[:1], strict=False):
            edges[tuple(sorted((a, b)))] += 1
            directed.append((a, b))
    boundary = [(a, b) for a, b in directed if edges[tuple(sorted((a, b)))] == 1]
    following = dict(boundary)
    assert len(following) == len(boundary) and set(following) == set(following.values())
    pending = set(following)
    loops = []
    while pending:
        first = min(pending)
        point = first
        loop = []
        while point in pending:
            pending.remove(point)
            loop.append(point[:2])
            point = following[point]
        assert point == first
        loops.append(loop)
    return loops


def vertical_proof(evidence, second_finish):
    expected = evidence["verticalCoordination"]
    deck = bpy.data.objects[expected["existingThirdDeckObject"]]
    walls = bpy.data.objects[expected["existingThirdCoreObject"]]
    upper_loops = [
        ring for ring in top_boundary_loops(deck, 17.5) if 4 < polygon_area(ring) < 8
    ]
    assert len(upper_loops) == 3
    second_loops = top_boundary_loops(second_finish, 12.800000190734863)
    top = [t for t in rows(deck) if all(abs(p.z - 17.5) < 0.00001 for p in t)]
    wall_feet = [t for t in rows(walls) if all(abs(p.z - 17.5) < 0.00001 for p in t)]
    actual = []
    for source in evidence["confirmedGap"]["newSecondSourceShafts"]:
        control = polygon_centroid(source["cutWorldXY"])
        second = min([r for r in second_loops if inside(control, r)], key=polygon_area)
        centre = polygon_centroid(second)
        upper = min(upper_loops, key=lambda r: math.dist(centre, polygon_centroid(r)))
        upper_centre = polygon_centroid(upper)
        cap = sum(clipped_area(second, t) for t in top)
        wall = sum(clipped_area(second, t) for t in wall_feet)
        overlap = sum(
            clipped_area(second, [upper[0], upper[i], upper[i + 1]])
            for i in range(1, len(upper) - 1)
        )
        assert abs(cap + overlap - polygon_area(second)) < 0.0002
        record = {
            "secondShaft": source["id"],
            "axisOffsetM": math.dist(centre, upper_centre),
            "axisOffsetXY_m": [centre[i] - upper_centre[i] for i in range(2)],
            "actualSecondAreaM2": polygon_area(second),
            "actualThirdOpeningAreaM2": polygon_area(upper),
            "overlapFractionOfSecond": overlap / polygon_area(second),
            "overlapFractionOfThird": overlap / polygon_area(upper),
            "existingThirdDeckProjectedCapM2": cap,
            "existing251WallFootprintProjectionOverlapM2": wall,
        }
        prior = next(
            r for r in expected["relationships"] if r["secondShaft"] == source["id"]
        )
        assert abs(record["axisOffsetM"] - prior["axisOffsetM"]) < 0.00005
        assert abs(cap - prior["existingThirdDeckProjectedCapM2"]) < 0.0002
        assert abs(wall - prior["existing251WallFootprintProjectionOverlapM2"]) < 0.0002
        actual.append(record)
    return {
        "status": "actual_mesh_relative_boundaries_remain_uncoordinated",
        "candidateOnly": True,
        "fullHeightAcceptance": False,
        "actualMeshRelationships": actual,
        "totalThirdDeckProjectedCapM2": sum(
            r["existingThirdDeckProjectedCapM2"] for r in actual
        ),
        "total251ProjectedWallOverlapM2": sum(
            r["existing251WallFootprintProjectionOverlapM2"] for r in actual
        ),
        "relativeControlUncertainty": expected["relativeControlUncertainty"],
        "retainedContextFingerprintsVerified": True,
        "sourcePolicy": "Second-floor inner boundaries stay on their own drawing; no upper geometry was moved or down-projected.",
    }


def geometry_proof(audit):
    update_scene()
    plan = json.loads((ROOT / audit["sourcePlan"]).read_text())
    evidence = json.loads((ROOT / audit["sourceEvidence"]).read_text())
    assert sha(ROOT / audit["sourcePlan"]) == audit["sourcePlanSha256"]
    assert (
        plan["sourceFloor"] == "Second floor"
        and plan["sourcePage"] == 1
        and plan["noThirdFloorPolygonsUsed"]
    )
    assert evidence["sourceIdentity"]["page1Owner"] == "The Marshall Building,LSE"
    holes = [r["cutWorldXY"] for r in evidence["confirmedGap"]["newSecondSourceShafts"]]
    area = evidence["confirmedGap"]["totalPlanAreaToRemovePerLayerM2"]
    assert len(holes) == 3
    checks = []
    old_all = []
    new_all = []
    for item in plan["objects"]:
        source = bpy.data.objects[item["sourceObject"]]
        obj = bpy.data.objects[item["replacement"]]
        assert source.hide_render and not obj.hide_render
        assert object_fingerprint(source) == item["sourceFingerprint"]
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
        assert sorted(c.name for c in obj.users_collection) == [OWNER]
        assert obj.matrix_world == source.matrix_world
        assert not obj.modifiers and obj.parent == source.parent
        assert [m.name for m in obj.data.materials] == [
            m.name for m in source.data.materials
        ]
        assert [uv.name for uv in obj.data.uv_layers] == [
            uv.name for uv in source.data.uv_layers
        ]
        for material in obj.data.materials:
            assert (
                material_fingerprint(material)
                == audit["reusedMaterialGraphs"][material.name]
            )
        old_rows, new_rows = rows(source), rows(obj)
        old_all.extend(old_rows)
        new_all.extend(new_rows)
        old_tree, new_tree = tree(old_rows), tree(new_rows)
        low, high = item["sourceZ"]
        actual_z = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
        assert min(actual_z) == low and max(actual_z) == high
        volume = solid_proof(obj)
        old_volume = solid_proof(source)
        expected = area * (high - low)
        assert abs((old_volume - volume) - expected) < 0.001, (
            obj.name,
            old_volume - volume,
            expected,
        )
        old_top = [t for t in old_rows if all(abs(p.z - high) < 1e-6 for p in t)]
        new_top = [t for t in new_rows if all(abs(p.z - high) < 1e-6 for p in t)]
        top_area = lambda ts: sum(
            abs((t[1] - t[0]).cross(t[2] - t[0]).z) / 2 for t in ts
        )
        assert abs((top_area(old_top) - top_area(new_top)) - area) < 0.0002
        actual_faces = collections.Counter(signature(obj, f) for f in obj.data.polygons)
        retained = 0
        for row in item["faceRecords"]:
            if row["role"] == "retained-native-face":
                expected_sig = signature(
                    source, source.data.polygons[row["sourceFace"]]
                )
                assert actual_faces[expected_sig] > 0, (obj.name, row["sourceFace"])
                actual_faces[expected_sig] -= 1
                retained += 1
        air = 0
        edge_contacts = 0
        retained_floor = 0
        for ring in holes:
            for point in samples(ring):
                origin = Vector((*point, high + 0.04))
                assert (
                    old_tree.ray_cast(origin, Vector((0, 0, -1)), high - low + 0.08)[0]
                    is not None
                )
                assert (
                    new_tree.ray_cast(origin, Vector((0, 0, -1)), high - low + 0.08)[0]
                    is None
                )
                air += 1
            signed = sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(ring, ring[1:] + ring[:1], strict=False)
            )
            for a, b in zip(ring, ring[1:] + ring[:1], strict=False):
                tangent = Vector((b[0] - a[0], b[1] - a[1], 0))
                if tangent.length < 0.0001:
                    continue
                tangent.normalize()
                outward = Vector((tangent.y, -tangent.x, 0)) * (1 if signed > 0 else -1)
                middle = Vector(
                    ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (low + high) / 2)
                )
                origin = middle - outward * 0.025
                if not inside(origin, ring):
                    continue
                hit = new_tree.ray_cast(origin, outward, 0.05)
                assert hit[0] is not None and abs(hit[3] - 0.025) < 0.00005, (
                    obj.name,
                    list(middle),
                    hit[3],
                )
                edge_contacts += 1
        for tri in old_top:
            for i in range(1, 5):
                for j in range(1, 5 - i):
                    point = (
                        tri[0] * (1 - (i + j) / 5) + tri[1] * (i / 5) + tri[2] * (j / 5)
                    )
                    if any(
                        inside(point, h) or gap_to_edge(point, h) < 0.0001
                        for h in holes
                    ):
                        continue
                    hit = new_tree.ray_cast(
                        point + Vector((0, 0, 0.04)), Vector((0, 0, -1)), 0.08
                    )
                    assert hit[0] is not None and abs(hit[0].z - high) < 0.00001
                    retained_floor += 1
        checks.append(
            {
                "object": obj.name,
                "closedConnectedSolid": True,
                "volumeM3": volume,
                "removedVolumeM3": old_volume - volume,
                "expectedRemovedVolumeM3": expected,
                "actualTopAreaRemovedM2": top_area(old_top) - top_area(new_top),
                "retainedNativeFacesCoordinatesUVsMaterialsExact": retained,
                "sourceZ": item["sourceZ"],
                "oldFilledToNewOpenSamples": air,
                "actualFiniteBoreEdgeContacts": edge_contacts,
                "retainedFloorSamples": retained_floor,
                "triangles": len(new_rows),
            }
        )
    # The complete three-layer replacement must leave continuous airspace over
    # the entire inherited0.345mstack, not merely punch holes in its visible skin.
    old_stack, new_stack = tree(old_all), tree(new_all)
    stack_low = min(r["sourceZ"][0] for r in plan["objects"])
    stack_high = max(r["sourceZ"][1] for r in plan["objects"])
    through = 0
    for ring in holes:
        for point in samples(ring):
            origin = Vector((*point, stack_high + 0.05))
            assert (
                old_stack.ray_cast(
                    origin, Vector((0, 0, -1)), stack_high - stack_low + 0.1
                )[0]
                is not None
            )
            assert (
                new_stack.ray_cast(
                    origin, Vector((0, 0, -1)), stack_high - stack_low + 0.1
                )[0]
                is None
            )
            through += 1
    vertical = evidence["verticalCoordination"]
    assert vertical["candidateOnly"] and not vertical["fullHeightAcceptance"]
    for key in ["existingThirdDeckObject", "existingThirdCoreObject"]:
        name = vertical[key]
        fp = vertical[key.replace("Object", "Fingerprint")]
        assert object_fingerprint(bpy.data.objects[name]) == fp, name
    finish = next(
        bpy.data.objects[r["replacement"]]
        for r in plan["objects"]
        if r["sourceObject"] == "MAR223_second_floor_finish"
    )
    vertical = vertical_proof(evidence, finish)
    return {
        "status": "passed-bounded-second-floor-candidate",
        "sourceFloor": "Second floor",
        "layers": checks,
        "throughCompleteStackRays": through,
        "completeStackZ": [stack_low, stack_high],
        "threeFloorBoresOpen": True,
        "newMaterials": 0,
        "allOtherFloorsAnd251WallsUnchanged": True,
        "verticalCoordination": vertical,
        "candidateOnly": True,
        "fullHeightShaftAcceptance": False,
        "acceptanceGate": "Geometry checks cover the three edited Second-floor layers. Retained third-deck cap strips and251projection conflicts remain unresolved; no full-height or production acceptance implied.",
    }


def main():
    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert sha(component) == audit["componentSha256"] and audit["baselineSha256"] == SHA
    assert all(sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == set(audit["addedObjects"])
    assert all(
        object_fingerprint(bpy.data.objects[n]) == f
        for n, f in audit["addedFingerprints"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    assert (
        len(before["objects"]) == 8748
        and len(before["materials"]) == 2355
        and len(before["rooms"]) == 35
    )
    images = sorted(i.name for i in bpy.data.images)
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
        obj.hide_render = False
        set_layer_hidden(obj, False)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    for name in audit["archivedObjects"]:
        bpy.data.objects[name].hide_render = True
        set_layer_hidden(bpy.data.objects[name], True)
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name in audit["archivedObjects"]:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        expected_visibility = (
            [True, before["visibility"][name][1], True]
            if name in audit["archivedObjects"]
            else before["visibility"][name]
        )
        assert after["visibility"][name] == expected_visibility, name
    assert set(after["objects"]) == set(before["objects"]) | set(audit["addedObjects"])
    assert after["materials"] == before["materials"]
    assert (
        after["rooms"] == before["rooms"]
        and after["campusRooms"] == before["campusRooms"]
    )
    assert sorted(i.name for i in bpy.data.images) == images
    proof = geometry_proof(audit)
    assert sha(BASE) == SHA and sha(component) == audit["componentSha256"]
    result = {
        "status": "passed-bounded-candidate-only",
        "freshBlenderProcess": True,
        "componentSha256": audit["componentSha256"],
        "baselineSha256": SHA,
        "originalObjectsProtected": 8748,
        "originalMaterialGraphsProtected": 2355,
        "roomMembershipsProtected": 35,
        "allUnlistedOriginalStatePreserved": True,
        "actualMeshProof": proof,
        "candidateOnly": True,
        "fullHeightShaftAcceptance": False,
        "wholeNativeSaved": False,
    }
    (OUT / "fresh-process-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        "MAR269_FRESH_BOUNDED_CANDIDATE_VERIFIED", audit["componentSha256"], flush=True
    )


if __name__ == "__main__":
    main()
