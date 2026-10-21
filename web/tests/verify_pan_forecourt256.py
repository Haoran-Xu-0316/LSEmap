"""Reopen actual PAN furniture meshes and verify support and three swept routes.

Triangle/box separating axes inspect complete continuous rectangular passage
volumes plus conservative turn envelopes, including every retained nearby mesh.
No centre-ray shortcut or current-layout/accessibility certification is used.
"""

import json
import math
import sys
from itertools import pairwise
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_pan_forecourt256 import (
    ARCHIVES,
    BASE,
    COLLECTION,
    OUT,
    PREFIX,
    SHA,
    STONE,
    bounds,
    capture,
    ground_trees,
    leaf_groups,
    local,
    protection,
    sha,
    support_at,
    write,
)


def triangle_box(triangle, half):
    """Closed triangle versus axis-aligned box SAT; coordinates are box-local."""
    edges = [triangle[(i + 1) % 3] - triangle[i] for i in range(3)]
    basis = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    axes = (
        basis + [edges[0].cross(edges[1])] + [e.cross(a) for e in edges for a in basis]
    )
    for axis in axes:
        if axis.length_squared < 1e-18:
            continue
        radius = sum(abs(axis[k]) * half[k] for k in range(3))
        projected = [p.dot(axis) for p in triangle]
        if min(projected) > radius + 1e-7 or max(projected) < -radius - 1e-7:
            return False
    return True


def visible_objects():
    allowed = set()

    def walk(collection, hidden=False):
        hidden = hidden or collection.hide_render
        if not hidden:
            allowed.update(o.name for o in collection.objects)
        for child in collection.children:
            walk(child, hidden)

    walk(bpy.context.scene.collection)
    return [
        o
        for o in bpy.context.scene.objects
        if o.type == "MESH" and not o.hide_render and o.name in allowed
    ]


def blockers():
    rows = []
    for obj in visible_objects():
        bound = bounds([local(obj.matrix_world @ Vector(p)) for p in obj.bound_box])
        if (
            bound[1][0] < -0.9
            or bound[0][0] > 9.1
            or bound[1][1] < 0.1
            or bound[0][1] > 7.6
            or bound[1][2] < 0.12
            or bound[0][2] > 2.1
        ):
            continue
        vertices = [Vector(local(obj.matrix_world @ v.co)) for v in obj.data.vertices]
        obj.data.calc_loop_triangles()
        triangles = []
        for face in obj.data.loop_triangles:
            triangle = [vertices[k] for k in face.vertices]
            box = bounds(triangle)
            if (
                box[1][0] < -0.9
                or box[0][0] > 9.1
                or box[1][1] < 0.1
                or box[0][1] > 7.6
                or box[1][2] < 0.12
                or box[0][2] > 2.1
            ):
                continue
            triangles.append(triangle)
        if triangles:
            rows.append((obj.name, triangles))
    return rows


def route_volume(route, trees, obstacles):
    paths = route["points"]
    width, height = route["width"], route["height"]
    probes = []
    volumes = []
    for a, b in pairwise(paths):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        along = Vector((dx / length, dy / length, 0))
        across = Vector((-dy / length, dx / length, 0))
        samples = max(2, math.ceil(length / 0.15))
        z = []
        for k in range(samples + 1):
            fraction = k / samples
            for side in [-0.5, 0, 0.5]:
                x = a[0] + dx * fraction + across.x * width * side
                d = a[1] + dy * fraction + across.y * width * side
                ground, owner = support_at(x, d, trees)
                z.append(ground)
                probes.append({"localXY": [x, d], "groundZ": ground, "support": owner})
        # The complete torso/leg volume starts100mm above the highest retained
        # paving patch. The74mm inherited grade discontinuity is reported below;
        # this is obstruction verification, not a route-grade certification.
        low = max(z) + 0.10
        volumes.append(
            {
                "center": Vector(
                    ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, low + height / 2)
                ),
                "along": along,
                "across": across,
                "half": (length / 2, width / 2, height / 2),
                "kind": "continuous-segment",
            }
        )
    for vertex in paths[1:-1]:
        ground, _ = support_at(*vertex, trees)
        volumes.append(
            {
                "center": Vector((*vertex, ground + 0.10 + height / 2)),
                "along": Vector((1, 0, 0)),
                "across": Vector((0, 1, 0)),
                "half": (width / 2, width / 2, height / 2),
                "kind": "conservative-square-turn",
            }
        )
    candidates = 0
    for volume in volumes:
        center, along, across, half = [
            volume[k] for k in ["center", "along", "across", "half"]
        ]
        for name, triangles in obstacles:
            for triangle in triangles:
                converted = []
                for vertex in triangle:
                    delta = vertex - center
                    converted.append(
                        Vector((delta.dot(along), delta.dot(across), delta.z))
                    )
                box = bounds(converted)
                if any(
                    box[1][k] < -half[k] - 1e-7 or box[0][k] > half[k] + 1e-7
                    for k in range(3)
                ):
                    continue
                candidates += 1
                assert not triangle_box(converted, half), (
                    route["door"],
                    volume["kind"],
                    name,
                    [list(v) for v in triangle],
                )
    return {
        "door": route["door"],
        "width": width,
        "height": height,
        "volumes": [
            {
                "kind": v["kind"],
                "center": list(v["center"]),
                "halfDimensions": v["half"],
            }
            for v in volumes
        ],
        "retainedTriangleCandidates": candidates,
        "groundSamples": probes,
        "groundRange": [
            min(p["groundZ"] for p in probes),
            max(p["groundZ"] for p in probes),
        ],
        "obstructed": False,
    }


def main():
    record = json.loads((OUT / "audit.json").read_text())
    before = json.loads((OUT / "protected-source-state.json").read_text())
    assert sha(BASE) == SHA == record["baselineSha256"]
    component = ROOT / record["componentPath"]
    assert sha(component) == record["componentSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    assert capture() == before
    with bpy.data.libraries.load(str(component), link=False) as (_, loaded):
        loaded.objects = record["addedObjects"]
    for obj in loaded.objects:
        for index, name in enumerate(record["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        assert object_fingerprint(obj) == record["addedFingerprints"][obj.name], (
            obj.name
        )
        bpy.data.collections[COLLECTION].objects.link(obj)
    for name in ARCHIVES:
        source = bpy.data.objects[name]
        source.hide_render = True
        set_layer_hidden(source, True)
    update_scene()
    protection(before, capture())
    stone = bpy.data.objects[PREFIX + "stone_planter_seating"]
    soil = bpy.data.objects[PREFIX + "retained_soil"]
    leaves = bpy.data.objects[PREFIX + "rigidly_relocated_leaves"]
    topology = []
    for obj in [stone, soil]:
        mesh = bmesh.new()
        mesh.from_mesh(obj.data)
        mesh.normal_update()
        nonmanifold = sum(not edge.is_manifold for edge in mesh.edges)
        assert nonmanifold == 0, (obj.name, nonmanifold)
        volume = mesh.calc_volume(signed=True)
        assert volume > 0, (obj.name, volume)
        topology.append(
            {"name": obj.name, "closedEdges": len(mesh.edges), "signedVolume": volume}
        )
        mesh.free()
    node = bpy.data.materials[STONE].node_tree.nodes["Principled BSDF"]
    assert (
        node.inputs["Metallic"].default_value == 0
        and node.inputs["Roughness"].default_value > 0.8
    )
    trees = ground_trees()
    contacts = []
    for vertex in stone.data.vertices:
        px, pd, pz = local(stone.matrix_world @ vertex.co)
        for unit in record["units"]:
            if abs(pz - unit["base"]) < 0.0001:
                ground, owner = support_at(px, pd, trees)
                assert abs(ground - pz) < 0.0001, (
                    unit["id"],
                    px,
                    pd,
                    pz,
                    ground,
                    owner,
                )
                contacts.append({"point": [px, pd, pz], "support": owner})
                break
    assert len(contacts) > 20
    # Distinct units may share internal tiled faces but must not overlap each
    # other. The hole contains soil above its real stone base, never a top cap.
    for i, unit in enumerate(record["units"]):
        for other in record["units"][i + 1 :]:
            for a in unit["rectangles"]:
                for b in other["rectangles"]:
                    assert min(a[1], b[1]) <= max(a[0], b[0]) or min(a[3], b[3]) <= max(
                        a[2], b[2]
                    ), (unit["id"], other["id"])
    original = leaf_groups(bpy.data.objects[record["leafSource"]])
    source_faces = [row for group in original for row in group["faces"]]
    assert len(leaves.data.polygons) == len(source_faces) == 120
    max_error = 0
    root_checks = []
    for move in record["leafRigidMoves"]:
        root = Vector(move["targetRoot"])
        px, pd, pz = local(root)
        unit = next(u for u in record["units"] if u["id"] == move["unit"])
        a, b, c, d = unit["inner"]
        assert a < px < b and c < pd < d and abs(pz - unit["soilTop"] - 0.002) < 0.00002
        root_checks.append(
            {"unit": unit["id"], "localRoot": [px, pd, pz], "soilTop": unit["soilTop"]}
        )
    for face, (source_points, source_uv) in zip(leaves.data.polygons, source_faces):
        points = [
            leaves.matrix_world @ leaves.data.vertices[k].co for k in face.vertices
        ]
        for i in range(3):
            error = abs(
                (points[(i + 1) % 3] - points[i]).length
                - (source_points[(i + 1) % 3] - source_points[i]).length
            )
            max_error = max(max_error, error)
        if source_uv is None:
            assert leaves.data.uv_layers.active is None
            assert len(leaves.data.uv_layers) == 0
        else:
            assert leaves.data.uv_layers.active is not None
            uv = [
                tuple(leaves.data.uv_layers.active.data[k].uv)
                for k in face.loop_indices
            ]
            assert uv == source_uv
    assert max_error < 0.00003, max_error
    obstacles = blockers()
    # Independently measure the actual retained envelope. SAT below still
    # includes all door rings and leaves; these are exterior-only starts.
    ring = bpy.data.objects["PAN_D5_entry88_revolving_door_rings"]
    measured_front = max(
        local(ring.matrix_world @ vertex.co)[1] for vertex in ring.data.vertices
    )
    external_starts = []
    for route in record["registration"]["routes"]:
        if route["door"].startswith("revolving"):
            clearance = route["points"][0][1] - route["width"] / 2 - measured_front
            assert clearance >= 0.12 - 0.00001, (route["door"], clearance)
            external_starts.append(
                {
                    "door": route["door"],
                    "actualRetainedFront": measured_front,
                    "minimumConservativeStartClearance": clearance,
                }
            )
    routes = [
        route_volume(route, trees, obstacles)
        for route in record["registration"]["routes"]
    ]
    assert len(routes) == 3
    write(
        "verification.json",
        {
            "passed": True,
            "componentSha256": sha(component),
            "savedComponentReopened": True,
            "protectedOriginalObjects": len(before["objects"]),
            "protectedOriginalMaterialGraphs": len(before["materials"]),
            "protectedRoomStudies": len(before["rooms"]),
            "topology": topology,
            "originalSharedSilverGraphPreserved": True,
            "groundContacts": contacts,
            "leafRoots": root_checks,
            "leafTriangleCount": 120,
            "leafUVPreserved": True,
            "leafUVState": {
                "sourceLayers": [
                    layer.name
                    for layer in bpy.data.objects[record["leafSource"]].data.uv_layers
                ],
                "replacementLayers": [layer.name for layer in leaves.data.uv_layers],
            },
            "maximumRigidLeafEdgeError": max_error,
            "drawBatches": 3,
            "retainedNearbyObstacleMeshes": len(obstacles),
            "routes": routes,
            "externalDoorStarts": external_starts,
            "routeScope": "Door-exterior forecourt only; no traversal through closed leaves or original threshold is proved",
            "wrongSideCycleProxyArchived": True,
            "newCycleLayoutClaimed": False,
            "visualReviewRequired": True,
        },
    )
    assert sha(BASE) == SHA
    print("PAN_FORECOURT256_REOPEN_VERIFIED", len(contacts), len(obstacles), flush=True)


if __name__ == "__main__":
    main()
