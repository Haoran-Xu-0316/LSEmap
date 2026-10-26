"""Fresh independent geometry verification for CBG's bounded upperG4repair.

Re-derives target groups from actual loaded269meshes and the registeredG4axis.
No authoring geometry helpers are imported. Retained face coordinates, normals,
UVs and material slots must be exact; physical rays test removal and glazing.
"""

import collections
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v269.blend"
SHA = "a44026d64bb57cea159a44b1fa96b7b9be13e7d4af034f57d09beb62480ef21b"
OUT = ROOT / "result/blender/cbg274"
STEP = 52.2 / 13
OWNER = "CBG_EXTERIOR"
SHADE_COUNTS = {
    "coloured_blades": 1,
    "pale_blades": 1,
    "brackets": 2,
    "caps": 2,
    "bolts": 4,
    "leading_strips": 3,
    "tie_rods": 1,
}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def groups(obj, local):
    mesh = obj.data
    links = [[] for _ in mesh.vertices]
    for edge in mesh.edges:
        a, b = edge.vertices
        links[a].append(b)
        links[b].append(a)
    unseen = set(range(len(links)))
    parts, owner = [], {}
    while unseen:
        first = unseen.pop()
        vertices, todo = {first}, [first]
        while todo:
            for other in links[todo.pop()]:
                if other in unseen:
                    unseen.remove(other)
                    vertices.add(other)
                    todo.append(other)
        points = [local(obj.matrix_world @ mesh.vertices[i].co) for i in vertices]
        low = [min(p[i] for p in points) for i in range(3)]
        high = [max(p[i] for p in points) for i in range(3)]
        for v in vertices:
            owner[v] = len(parts)
        parts.append(
            {
                "vertices": vertices,
                "low": low,
                "high": high,
                "centre": [(a + b) / 2 for a, b in zip(low, high, strict=True)],
                "faces": [],
            }
        )
    for face in mesh.polygons:
        index = owner[face.vertices[0]]
        assert all(owner[i] == index for i in face.vertices)
        parts[index]["faces"].append(face)
    return parts


def signature(obj, face):
    corners = []
    for i in face.loop_indices:
        point = obj.matrix_world @ obj.data.vertices[obj.data.loops[i].vertex_index].co
        corners.append(
            (
                tuple(point),
                tuple(obj.data.corner_normals[i].vector),
                tuple((uv.name, tuple(uv.data[i].uv)) for uv in obj.data.uv_layers),
            )
        )
    return (
        face.material_index,
        face.use_smooth,
        tuple(face.normal),
        min(tuple(corners[i:] + corners[:i]) for i in range(len(corners))),
    )


def tree(obj):
    obj.data.calc_loop_triangles()
    return BVHTree.FromPolygons(
        [obj.matrix_world @ v.co for v in obj.data.vertices],
        [tuple(t.vertices) for t in obj.data.loop_triangles],
        all_triangles=True,
        epsilon=0,
    )


def actual_scene_tree():
    points, triangles, owners = [], [], []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.collections[OWNER].all_objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        offset = len(points)
        points.extend(evaluated.matrix_world @ v.co for v in mesh.vertices)
        triangles.extend(
            tuple(offset + i for i in t.vertices) for t in mesh.loop_triangles
        )
        owners.extend([obj.name] * len(mesh.loop_triangles))
        evaluated.to_mesh_clear()
    return BVHTree.FromPolygons(
        points, triangles, all_triangles=True, epsilon=0
    ), owners


def clipped_xz_area(points, rectangle):
    ring = [(p.x, p.z) for p in points]
    for axis, bound, positive in (
        (0, rectangle[0], True),
        (0, rectangle[1], False),
        (1, rectangle[2], True),
        (1, rectangle[3], False),
    ):
        if not ring:
            return 0.0
        output = []
        previous = ring[-1]
        previous_side = (previous[axis] - bound) * (1 if positive else -1)
        for current in ring:
            current_side = (current[axis] - bound) * (1 if positive else -1)
            if (current_side >= 0) != (previous_side >= 0):
                t = previous_side / (previous_side - current_side)
                output.append(
                    tuple(
                        previous[i] + t * (current[i] - previous[i]) for i in range(2)
                    )
                )
            if current_side >= 0:
                output.append(current)
            previous, previous_side = current, current_side
        ring = output
    return (
        abs(
            sum(
                a[0] * b[1] - b[0] * a[1]
                for a, b in zip(ring, ring[1:] + ring[:1], strict=True)
            )
        )
        / 2
    )


def single_pane_coverage(patch, local):
    rectangle = [patch["low"][0], patch["high"][0], patch["low"][2], patch["high"][2]]
    contacts = []
    deps = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.collections[OWNER].all_objects:
        if (
            obj.type != "MESH"
            or obj.hide_render
            or not any(m and m.get("webOpacity", 1) < 1 for m in obj.data.materials)
        ):
            continue
        evaluated = obj.evaluated_get(deps)
        for index, part in enumerate(groups(evaluated, local)):
            if (
                part["high"][0] < rectangle[0]
                or part["low"][0] > rectangle[1]
                or part["high"][2] < rectangle[2]
                or part["low"][2] > rectangle[3]
            ):
                continue
            parallel = []
            for face in part["faces"]:
                material = evaluated.data.materials[face.material_index]
                if material.get("webOpacity", 1) >= 1:
                    continue
                points = [
                    local(evaluated.matrix_world @ evaluated.data.vertices[i].co)
                    for i in face.vertices
                ]
                low, high = min(p.y for p in points), max(p.y for p in points)
                if high - low < 0.00001 and abs(low - patch["low"][1]) < 0.05:
                    parallel.append((low, points))
            if not parallel:
                continue
            first = min(y for y, _ in parallel)
            area = sum(
                clipped_xz_area(points, rectangle)
                for y, points in parallel
                if abs(y - first) < 0.00001
            )
            if area > 0.000001:
                contacts.append(
                    {
                        "object": obj.name,
                        "connectedPane": index,
                        "overlapAreaM2": area,
                        "frontLocalYM": first,
                    }
                )
    expected = (rectangle[1] - rectangle[0]) * (rectangle[3] - rectangle[2])
    assert (
        len(contacts) == 1
        and contacts[0]["object"] == "CBG274_G4_upper_clear_glass_patches"
    ), ("duplicate-or-missing-pane", contacts)
    assert abs(contacts[0]["overlapAreaM2"] - expected) < 0.00005
    return {
        "expectedPatchAreaM2": expected,
        "actualSinglePane": contacts[0],
        "otherNearPlaneOpticalPaneOverlapAreaM2": 0.0,
    }


def geometry_proof(audit):
    sys.path.insert(0, str(ROOT / "web/tools"))
    from integrate_exterior_round194 import object_fingerprint
    from refine_portsmouth_exterior207 import material_fingerprint

    plan = json.loads((OUT / "plan.json").read_text())
    native = json.loads((OUT / "native-inspection.json").read_text())
    origin = Vector((*native["frame"]["origin_G7_SW_world"], 0))
    x_axis, y_axis = [
        Vector((*native["frame"][n], 0)) for n in ("x_unit_SW", "y_unit_SE_rear")
    ]

    def local(point):
        delta = point - origin
        return Vector((delta.dot(x_axis), delta.dot(y_axis), point.z))

    def world(x, y, z):
        return origin + x_axis * x + y_axis * y + Vector((0, 0, z))

    rows = plan["replacements"]
    bracket_row = next(r for r in rows if r["role"] == "brackets")
    bracket_parts = groups(bpy.data.objects[bracket_row["sourceObject"]], local)
    stations = {}
    for floor in (11, 12):
        xs = sorted(
            p["centre"][0]
            for p in bracket_parts
            if math.floor(p["centre"][2] / STEP) == floor
            and p["centre"][1] < -0.2
            and -24 < p["centre"][0] < 0
        )
        unique = []
        for x in xs:
            if not unique or abs(x - unique[-1]) > 0.0001:
                unique.append(x)
        stations[floor] = unique
        assert len([x for x in unique if x > -18]) == 4
    checks, removed_parts, surface_rays, retained_faces = [], {}, 0, 0
    boundary_profiles = []
    old_triangles, new_triangles = 0, 0
    leaf_parts = []
    vent_parts = []
    for row in rows:
        source, obj = (
            bpy.data.objects[row["sourceObject"]],
            bpy.data.objects[row["replacement"]],
        )
        assert source.hide_render and not obj.hide_render and not obj.modifiers
        assert object_fingerprint(source) == row["sourceFingerprint"]
        assert object_fingerprint(obj) == audit["addedFingerprints"][obj.name]
        assert sorted(c.name for c in obj.users_collection) == [OWNER]
        assert [m.name for m in obj.data.materials] == [
            m.name for m in source.data.materials
        ]
        parts = groups(source, local)
        selected = []
        station_counts = collections.Counter()
        for part in parts:
            x, y, z = part["centre"]
            floor = math.floor(z / STEP)
            if floor not in (11, 12) or y >= -0.2 and row["role"] in SHADE_COUNTS:
                continue
            if row["role"] in SHADE_COUNTS:
                if not -24 < x < 0:
                    continue
                station = min(stations[floor], key=lambda p: abs(p - x))
                assert abs(station - x) < 0.25
                if station <= -18:
                    continue
                station_counts[(floor, round(station, 4))] += 1
            elif not -18 < x < -15:
                continue
            selected.append(part)
        expected_count = (
            8 * SHADE_COUNTS[row["role"]] if row["role"] in SHADE_COUNTS else 2
        )
        assert len(selected) == expected_count, row["role"]
        if station_counts:
            assert len(station_counts) == 8 and set(station_counts.values()) == {
                SHADE_COUNTS[row["role"]]
            }
        if row["role"] == "office_solid":
            leaf_parts = selected
        if row["role"] == "office_vent":
            vent_parts = selected
        deleted_vertices = {v for p in selected for v in p["vertices"]}
        deleted_faces = {f.index for p in selected for f in p["faces"]}
        assert deleted_vertices == set(row["removedVertices"])
        assert deleted_faces == set(row["removedFaces"])
        assert (
            len(deleted_vertices) == 8 * expected_count
            and len(deleted_faces) == 6 * expected_count
        )
        expected = collections.Counter(
            signature(source, f)
            for f in source.data.polygons
            if f.index not in deleted_faces
        )
        observed = collections.Counter(signature(obj, f) for f in obj.data.polygons)
        assert observed == expected, ("retained-face-change", row["role"])
        assert len(obj.data.vertices) == len(source.data.vertices) - len(
            deleted_vertices
        )
        new_parts = groups(obj, local)
        assert len(new_parts) == len(parts) - expected_count
        if row["role"] in SHADE_COUNTS:
            boundary = [
                p
                for p in new_parts
                if p["centre"][1] < -0.2
                and -24 < p["centre"][0] < 0
                and math.floor(p["centre"][2] / STEP) in (11, 12)
            ]
            assert boundary
            maximum = max(p["high"][0] for p in boundary)
            boundary_profiles.append(
                {
                    "role": row["role"],
                    "object": obj.name,
                    "maximumLocalXM": maximum,
                    "beyondG4M": max(0, maximum + 18),
                }
            )
        old_tree, new_tree = tree(source), tree(obj)
        for part in selected:
            for face in part["faces"]:
                points = [
                    source.matrix_world @ source.data.vertices[i].co
                    for i in face.vertices
                ]
                centre = sum(points, Vector()) / len(points)
                normal = (
                    source.matrix_world.to_3x3().inverted().transposed() @ face.normal
                ).normalized()
                ray = centre + normal * 0.01
                old = old_tree.ray_cast(ray, -normal, 0.021)
                assert old[0] is not None and abs(old[3] - 0.01) < 0.00005
                assert new_tree.ray_cast(ray, -normal, 0.021)[0] is None, (
                    "remaining-shade-or-leaf",
                    row["role"],
                )
                surface_rays += 1
        old_triangles += len(source.data.loop_triangles)
        new_triangles += len(obj.data.loop_triangles)
        retained_faces += sum(expected.values())
        removed_parts[row["role"]] = expected_count
        checks.append(
            {
                "role": row["role"],
                "removedClosedParts": expected_count,
                "retainedFacesCoordinatesNormalsUVsMaterialsExact": sum(
                    expected.values()
                ),
                "retainedComponentCount": len(new_parts),
            }
        )
    assert sum(removed_parts[k] for k in SHADE_COUNTS) == 112
    glass = bpy.data.objects[plan["newGlassObject"]]
    template = bpy.data.objects[plan["glassSource"]]
    assert (
        not glass.hide_render
        and object_fingerprint(template) == plan["glassSourceFingerprint"]
    )
    assert (
        [m.name for m in glass.data.materials]
        == [m.name for m in template.data.materials]
        == plan["glassMaterials"]
    )
    assert all(abs(m.get("webOpacity", 1) - 0.4) < 1e-8 for m in glass.data.materials)
    for material in glass.data.materials:
        assert (
            material_fingerprint(material)
            == audit["reusedMaterialGraphs"][material.name]
        )
    glass_parts = groups(glass, local)
    template_parts = groups(template, local)
    assert len(glass_parts) == 2
    bm = bmesh.new()
    bm.from_mesh(glass.data)
    assert (
        all(edge.is_manifold for edge in bm.edges) and bm.calc_volume(signed=True) > 0
    )
    bm.free()
    visible, owners = actual_scene_tree()
    pane_rays = 0
    pane_coverage = []
    for leaf in leaf_parts:
        floor = math.floor(leaf["centre"][2] / STEP)
        patch = next(
            p for p in glass_parts if math.floor(p["centre"][2] / STEP) == floor
        )
        adjacent = next(
            p
            for p in template_parts
            if math.floor(p["centre"][2] / STEP) == floor and -18 < p["centre"][0] < -15
        )
        for side in (0, 1):
            assert (
                abs(patch[("low", "high")[side]][0] - leaf[("low", "high")[side]][0])
                < 0.00001
            )
            assert (
                abs(
                    patch[("low", "high")[side]][1] - adjacent[("low", "high")[side]][1]
                )
                < 0.00001
            )
            assert (
                abs(
                    patch[("low", "high")[side]][2] - adjacent[("low", "high")[side]][2]
                )
                < 0.00001
            )
        # Existing office glass is the adjacent2marea, not a duplicate of
        # the old1mleaf. Prove full-area non-overlap, then scan all visible
        # near-plane optical components to rule out legacy coplanar proxies.
        rectangle = [
            patch["low"][0],
            patch["high"][0],
            patch["low"][2],
            patch["high"][2],
        ]
        adjacent_overlap = max(
            0,
            min(adjacent["high"][0], rectangle[1])
            - max(adjacent["low"][0], rectangle[0]),
        ) * max(
            0,
            min(adjacent["high"][2], rectangle[3])
            - max(adjacent["low"][2], rectangle[2]),
        )
        assert adjacent_overlap == 0
        coverage = single_pane_coverage(patch, local)
        coverage["floor"] = floor
        coverage["originalAdjacentGlassOverlapAreaM2"] = adjacent_overlap
        coverage["originalAdjacentGlassEdgeGapM"] = (
            patch["low"][0] - adjacent["high"][0]
        )
        pane_coverage.append(coverage)
        for u in (0.2, 0.5, 0.8):
            for v in (0.2, 0.5, 0.8):
                x = patch["low"][0] + (patch["high"][0] - patch["low"][0]) * u
                z = patch["low"][2] + (patch["high"][2] - patch["low"][2]) * v
                hit = visible.ray_cast(world(x, -2, z), y_axis, 2.1)
                assert hit[0] is not None and owners[hit[2]] == glass.name, (
                    "opaque-first-surface",
                    floor,
                    x,
                    z,
                    owners[hit[2]] if hit[2] is not None else None,
                )
                assert abs(local(hit[0]).y - adjacent["low"][1]) < 0.00001
                pane_rays += 1
    for vent in vent_parts:
        x, _, z = vent["centre"]
        hit = visible.ray_cast(world(x, -2, z), y_axis, 2.1)
        assert hit[0] is not None and owners[hit[2]] == template.name, (
            "remaining-office-vent",
            x,
            z,
        )
    structural_profiles = []
    for record in native["visibleExterior"]:
        if not record["name"].endswith(
            ("tower_I_flanges", "tower_I_webs", "tower_column_caps")
        ):
            continue
        obj = bpy.data.objects[record["name"]]
        assert not obj.hide_render and object_fingerprint(obj) == record["fingerprint"]
        pieces = [
            p
            for p in groups(obj, local)
            if abs(p["centre"][0] + 18) < 0.3
            and p["centre"][1] < 0.3
            and p["high"][2] >= 11 * STEP
        ]
        assert pieces
        structural_profiles.append(
            {
                "object": obj.name,
                "maximumLocalXM": max(p["high"][0] for p in pieces),
                "beyondG4M": max(0, max(p["high"][0] for p in pieces) + 18),
            }
        )
    assert len(structural_profiles) == 3
    maximum_shade = max(p["beyondG4M"] for p in boundary_profiles)
    maximum_structure = max(p["beyondG4M"] for p in structural_profiles)
    assert maximum_shade <= maximum_structure
    boundary = {
        "retainedShadeProfiles": boundary_profiles,
        "unchangedG4StructuralProfiles": structural_profiles,
        "maximumRetainedShadeBeyondAxisM": maximum_shade,
        "maximumUnchangedStructureBeyondAxisM": maximum_structure,
        "retainedShadeXExtentWithinExistingG4StructuralXEnvelope": True,
        "wholeAssembliesClaimedEntirelyAtOrLeftOfG4": False,
        "sourceManualMarkerUncertaintyPixels": 10,
        "approximateG4ControlUncertaintyM": [
            6 * 10 / (828 - 735),
            6 * 10 / (906 - 828),
        ],
        "sourceToleranceRole": "Illustrative local conversion of the archived10pixel source controls using adjacent6maxes. Not a survey or permission to retain a full misplaced assembly; native frame/profile overhang is reported separately.",
    }
    glass.data.calc_loop_triangles()
    net = new_triangles + len(glass.data.loop_triangles) - old_triangles
    assert net == -1368 and surface_rays == 696 and pane_rays == 18
    return {
        "status": "passed-bounded-upper-G4-candidate",
        "targetFloors": [11, 12],
        "G4LocalXM": -18,
        "removedShadeAssemblies": 8,
        "removedPartsByRole": removed_parts,
        "replacementChecks": checks,
        "retainedFacesCoordinatesNormalsUVsMaterialsExact": retained_faces,
        "removedSolidSurfaceRays": surface_rays,
        "newClearPatchFirstSurfaceRays": pane_rays,
        "obsoleteOfficeVentFirstSurfaceRays": len(vent_parts),
        "samePlaneAndOpticalMaterialAsAdjacentNativeGlass": True,
        "originalAdjacentGlassUnchanged": True,
        "actualSinglePaneCoverage": pane_coverage,
        "actualBoundaryExtent": boundary,
        "noUnpairedShadeSupportsLeftInTargetAssemblies": True,
        "newMaterials": 0,
        "newImages": 0,
        "netTriangles": net,
        "wholeFacadeAccepted": False,
        "globalFinPhaseUnchanged": True,
        "storeyHeightsUnchanged": True,
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
    assert set(bpy.data.objects.keys()) == set(audit["addedObjects"])
    assert all(
        object_fingerprint(bpy.data.objects[n]) == f
        for n, f in audit["addedFingerprints"].items()
    )
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    images = sorted(i.name for i in bpy.data.images)
    assert len(before["objects"]) == 8752 and len(before["materials"]) == 2355
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
        visibility = (
            [True, before["visibility"][name][1], True]
            if name in audit["archivedObjects"]
            else before["visibility"][name]
        )
        assert after["visibility"][name] == visibility, name
    assert set(after["objects"]) == set(before["objects"]) | set(audit["addedObjects"])
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
        "originalObjectsProtected": 8752,
        "originalMaterialGraphsProtected": 2355,
        "roomMembershipsProtected": 35,
        "allUnlistedOriginalStatePreserved": True,
        "actualMeshProof": proof,
        "wholeNativeSaved": False,
    }
    (OUT / "fresh-process-verification.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print("CBG274_FRESH_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
