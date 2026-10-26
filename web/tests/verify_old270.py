"""Independently verify OLD270's actual lower casement meshes in a fresh process.

No authoring geometry is imported. Native upper-member faces, UVs and slots are
compared exactly; lower pane counts, closed solids, real outer-frame contacts
and glazing behind the clear panes are measured from loaded meshes.
"""

import collections
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/old270"
OWNER = "OLD_EXTERIOR"
SOURCE = "OLD_D5_clare87_casements"
REPLACEMENT = "OLD270_Clare_lower_six_column_eight_row_casements"
FRAME_SOURCE = "OLD201_CLARE_joinery"
GLASS_SOURCE = "OLD201_CLARE_glazing"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def groups(mesh):
    parents = list(range(len(mesh.vertices)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for edge in mesh.edges:
        a, b = (root(v) for v in edge.vertices)
        parents[b] = a
    result = collections.defaultdict(list)
    for index in range(len(parents)):
        result[root(index)].append(index)
    return list(result.values())


def frame(native):
    return tuple(
        Vector(native["frame"][name]) for name in ("origin", "right", "outward")
    )


def local(point, axes):
    origin, right, outward = axes
    delta = point - origin
    return Vector((delta.dot(right), delta.dot(outward), point.z))


def world(x, depth, z, axes):
    origin, right, outward = axes
    return origin + right * x + outward * depth + Vector((0, 0, z))


def face_signature(obj, face):
    corners = []
    for loop in face.loop_indices:
        point = (
            obj.matrix_world @ obj.data.vertices[obj.data.loops[loop].vertex_index].co
        )
        corners.append(
            (
                tuple(point),
                tuple((uv.name, tuple(uv.data[loop].uv)) for uv in obj.data.uv_layers),
            )
        )
    return (
        face.material_index,
        face.use_smooth,
        min(tuple(corners[i:] + corners[:i]) for i in range(len(corners))),
    )


def describe(obj, axes):
    records = []
    for vertices in groups(obj.data):
        selected = set(vertices)
        faces = [f for f in obj.data.polygons if set(f.vertices) <= selected]
        assert len(vertices) == 8 and len(faces) == 6
        edges = collections.Counter()
        directed = collections.Counter()
        volume = 0
        centre = sum((obj.data.vertices[i].co for i in vertices), Vector()) / len(
            vertices
        )
        for face in faces:
            points = [obj.data.vertices[i].co - centre for i in face.vertices]
            volume += sum(
                points[0].dot(points[i].cross(points[i + 1])) / 6
                for i in range(1, len(points) - 1)
            )
            ring = list(face.vertices)
            for a, b in zip(ring, ring[1:] + ring[:1], strict=True):
                edges[tuple(sorted((a, b)))] += 1
                directed[(a, b)] += 1
        assert len(edges) == 12 and set(edges.values()) == {2}
        assert all(count == directed[(b, a)] for (a, b), count in directed.items())
        assert volume > 0
        points = [
            local(obj.matrix_world @ obj.data.vertices[i].co, axes) for i in vertices
        ]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        records.append(
            {
                "vertices": vertices,
                "faces": faces,
                "centre": [(a + b) / 2 for a, b in zip(low, high, strict=True)],
                "size": [b - a for a, b in zip(low, high, strict=True)],
                "low": low,
                "high": high,
                "volume": volume,
            }
        )
    assert sum(len(r["faces"]) for r in records) == len(obj.data.polygons)
    return records


def mesh_triangles(obj, predicate=None):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = []
    for tri in mesh.loop_triangles:
        material = mesh.materials[tri.material_index] if mesh.materials else None
        if predicate is None or predicate(material.name.lower() if material else ""):
            result.append(
                tuple(
                    evaluated.matrix_world @ mesh.vertices[i].co for i in tri.vertices
                )
            )
    evaluated.to_mesh_clear()
    return result


def tree(triangles):
    assert triangles
    return BVHTree.FromPolygons(
        [p for t in triangles for p in t],
        [(3 * i, 3 * i + 1, 3 * i + 2) for i in range(len(triangles))],
        all_triangles=True,
        epsilon=0,
    )


def geometry_proof(audit):
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint

    native = json.loads((OUT / "native-inspection.json").read_text())
    axes = frame(native)
    source, obj = bpy.data.objects[SOURCE], bpy.data.objects[REPLACEMENT]
    assert source.hide_render and not obj.hide_render and not obj.modifiers
    assert object_fingerprint(source) == native["sourceFingerprint"]
    assert object_fingerprint(obj) == audit["addedFingerprints"][REPLACEMENT]
    assert (
        sorted(c.name for c in obj.users_collection)
        == native["sourceOwners"]
        == [OWNER]
    )
    assert [m.name for m in obj.data.materials] == native["materials"]
    old, new = describe(source, axes), describe(obj, axes)
    assert len(old) == 56 and len(new) == 76
    upper_old = [r for r in old if r["centre"][2] > 6]
    upper_new = [r for r in new if r["centre"][2] > 6]
    assert len(upper_old) == len(upper_new) == 28
    expected = collections.Counter(
        face_signature(source, f) for r in upper_old for f in r["faces"]
    )
    observed = collections.Counter(
        face_signature(obj, f) for r in upper_new for f in r["faces"]
    )
    assert expected == observed
    lower = [r for r in new if r["centre"][2] < 6]
    assert len(lower) == 48
    lower_windows = [w for w in native["legacyWindows"] if w["family"] == "lower"]
    bars = tree(mesh_triangles(obj))
    outward = axes[2]
    frame_triangles, glazing_triangles = [], []
    frame_names, glazing_names = [], []
    for record in native["nearbyActualTriangles"]:
        other = bpy.data.objects[record["name"]]
        assert (
            not other.hide_render and object_fingerprint(other) == record["fingerprint"]
        )
        # The201component copied native materials into numbered slots. Use
        # the registered joinery/glazing owners, not a blue/glass name guess.
        if other.name == FRAME_SOURCE:
            frame_triangles.extend(mesh_triangles(other))
            frame_names.append(other.name)
        if other.name == GLASS_SOURCE:
            glazing_triangles.extend(mesh_triangles(other))
            glazing_names.append(other.name)
    assert frame_names == [FRAME_SOURCE] and glazing_names == [GLASS_SOURCE]
    actual_frame, glazing = tree(frame_triangles), tree(glazing_triangles)

    def supported_endpoint(endpoint):
        # Existing201outer-frame faces have inward winding. Solid membership
        # therefore uses boundary-crossing parity, independent of normal sign.
        # Both depth directions must start inside the actual retained frame.
        first_exits = []
        for sign in (-1, 1):
            direction = outward * sign
            point, travelled, crossings = endpoint.copy(), 0.0, []
            while travelled < 1.0:
                hit, _, _, distance = actual_frame.ray_cast(
                    point, direction, 1.0 - travelled
                )
                if hit is None:
                    break
                crossings.append(travelled + distance)
                travelled += distance + 0.00002
                point = hit + direction * 0.00002
            assert len(crossings) % 2 == 1, (
                "endpoint-outside-native-frame",
                tuple(endpoint),
                sign,
                crossings,
            )
            assert crossings[0] > 0
            first_exits.append(crossings[0])
        return first_exits

    clear_panes, frame_contacts, glazing_depths, frame_distances = 0, 0, [], []
    window_results = []
    for window in lower_windows:
        cx, width, lowz, height = (
            window["x"],
            window["w"],
            window["z"] - window["h"] / 2,
            window["h"],
        )
        parts = [r for r in lower if abs(r["centre"][0] - cx) < width / 2 - 0.01]
        assert len(parts) == 12
        horizontal = sorted(
            (r for r in parts if r["size"][0] > width * 0.99),
            key=lambda r: r["centre"][2],
        )
        vertical = sorted(
            (r for r in parts if r["size"][2] > height * 0.99),
            key=lambda r: r["centre"][0],
        )
        assert len(horizontal) == 7 and len(vertical) == 5
        zs = [(r["centre"][2] - lowz) / height for r in horizontal]
        xs = [(r["centre"][0] - cx + width / 2) / width for r in vertical]
        assert max(abs(z - (i + 1) / 8) for i, z in enumerate(zs)) < 0.00001
        expected_x = [0.135, 0.3175, 0.5, 0.6825, 0.865]
        assert max(abs(a - b) for a, b in zip(xs, expected_x, strict=True)) < 0.00001
        assert (
            max(
                abs(r["size"][2] - (0.095 if i % 2 else 0.045))
                for i, r in enumerate(horizontal)
            )
            < 0.00005
        )
        assert (
            max(
                abs(r["size"][0] - (0.052 if i % 2 == 0 else 0.028))
                for i, r in enumerate(vertical)
            )
            < 0.00005
        )
        for part in parts:
            assert (
                abs(part["centre"][1] + 0.10) < 0.00005
                and abs(part["size"][1] - 0.15) < 0.00005
            )
            assert (
                part["low"][0] >= cx - width / 2 - 0.00005
                and part["high"][0] <= cx + width / 2 + 0.00005
            )
            assert (
                part["low"][2] >= lowz - 0.00005
                and part["high"][2] <= lowz + height + 0.00005
            )
            assert (
                bars.ray_cast(
                    world(*part["centre"][:2], part["centre"][2], axes) + outward,
                    -outward,
                    2,
                )[0]
                is not None
            )
        # Ray across each finite member end through an existing physical outer
        # blue frame. New members are excluded from this support BVH.
        for row in horizontal:
            for sign in (-1, 1):
                endpoint = world(cx + sign * width / 2, -0.10, row["centre"][2], axes)
                frame_distances.extend(
                    supported_endpoint(endpoint - axes[1] * sign * 0.02)
                )
                direction = axes[1] * sign
                hit, _, _, distance = actual_frame.ray_cast(
                    endpoint - direction * 0.10, direction, 0.20
                )
                assert hit is not None, (
                    "outer-jamb-contact",
                    cx,
                    row["centre"][2],
                    sign,
                )
                frame_distances.append(distance)
                frame_contacts += 1
        for row in vertical:
            for z, sign in ((lowz, -1), (lowz + height, 1)):
                endpoint = world(row["centre"][0], -0.10, z, axes)
                frame_distances.extend(
                    supported_endpoint(endpoint - Vector((0, 0, sign * 0.02)))
                )
                direction = Vector((0, 0, sign))
                hit, _, _, distance = actual_frame.ray_cast(
                    endpoint - direction * 0.10, direction, 0.20
                )
                assert hit is not None, (
                    "outer-head-sill-contact",
                    cx,
                    row["centre"][0],
                    z,
                )
                frame_distances.append(distance)
                frame_contacts += 1
        x_edges, z_edges = [0, *xs, 1], [i / 8 for i in range(9)]
        for xa, xb in zip(x_edges, x_edges[1:], strict=False):
            for za, zb in zip(z_edges, z_edges[1:], strict=False):
                x, z = (
                    cx - width / 2 + width * (xa + xb) / 2,
                    lowz + height * (za + zb) / 2,
                )
                origin = world(x, 0.5, z, axes)
                assert bars.ray_cast(origin, -outward, 1.0)[0] is None, (
                    "blocked-pane",
                    cx,
                    x,
                    z,
                )
                hit, _, _, _ = glazing.ray_cast(origin, -outward, 1.0)
                assert hit is not None, ("missing-native-glazing", cx, x, z)
                depth = local(hit, axes).y
                assert depth < -0.175, ("glazing-in-front-of-bars", depth)
                glazing_depths.append(depth)
                clear_panes += 1
        window_results.append(
            {
                "centreX": cx,
                "rows": len(horizontal) + 1,
                "columns": len(vertical) + 1,
                "actualVerticalFractions": xs,
                "actualHorizontalFractions": zs,
                "closedMemberVolumesM3": [r["volume"] for r in parts],
            }
        )
    assert clear_panes == 192 and frame_contacts == 96
    old_triangles = len(mesh_triangles(source))
    new_triangles = len(mesh_triangles(obj))
    assert new_triangles - old_triangles == 240 and new_triangles == 912
    return {
        "status": "passed-bounded-lower-casement-grid",
        "actualWindows": window_results,
        "actualClosedPositiveSolids": len(new),
        "upperNativeMembersExact": 28,
        "upperNativeFacesCoordinatesUVsMaterialsExact": sum(expected.values()),
        "doorUpperLightAndUpperWindowsProtected": True,
        "unobstructedActualGlassPaneRays": clear_panes,
        "actualNativeOuterFrameContacts": frame_contacts,
        "contactSamplesInsetFromFiniteMemberEndsM": 0.02,
        "contactsRequireOddActualFrameCrossingParityInBothDepthDirections": True,
        "outerFrameSourceObjects": frame_names,
        "outerFrameContactRayDistancesM": [min(frame_distances), max(frame_distances)],
        "glazingSourceObjects": glazing_names,
        "actualGlazingLocalDepthM": [min(glazing_depths), max(glazing_depths)],
        "triangles": new_triangles,
        "netTrianglesAdded": new_triangles - old_triangles,
        "materialsAdded": 0,
        "imagesAdded": 0,
        "dimensionsEstimated": True,
        "wholeBuildingAccepted": False,
    }


def main():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import (
        object_fingerprint,
        set_layer_hidden,
        update_scene,
    )
    from refine_houghton262 import capture

    assert sha(BASE) == SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert audit["baselineSha256"] == SHA and sha(component) == audit["componentSha256"]
    assert sha(ROOT / audit["sourcePlan"]) == audit["sourcePlanSha256"]
    assert all(sha(ROOT / p) == h for p, h in audit["sourceHashes"].items())
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == {REPLACEMENT}
    assert (
        object_fingerprint(bpy.data.objects[REPLACEMENT])
        == audit["addedFingerprints"][REPLACEMENT]
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
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
    bpy.data.objects[SOURCE].hide_render = True
    set_layer_hidden(bpy.data.objects[SOURCE], True)
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        expected = dict(value)
        if name == SOURCE:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
        visibility = (
            [True, before["visibility"][name][1], True]
            if name == SOURCE
            else before["visibility"][name]
        )
        assert after["visibility"][name] == visibility, name
    assert set(after["objects"]) == set(before["objects"]) | {REPLACEMENT}
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert sorted(i.name for i in bpy.data.images) == images
    proof = geometry_proof(audit)
    assert sha(BASE) == SHA and sha(component) == audit["componentSha256"]
    result = {
        "status": "passed-bounded-candidate",
        "freshBlenderProcess": True,
        "baselineSha256": SHA,
        "componentSha256": audit["componentSha256"],
        "originalObjectsProtected": len(before["objects"]),
        "originalMaterialGraphsProtected": len(before["materials"]),
        "roomMembershipsProtected": 35,
        "allUnlistedOriginalStatePreserved": True,
        "actualMeshProof": proof,
        "wholeNativeSaved": False,
    }
    (OUT / "fresh-process-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("OLD270_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
