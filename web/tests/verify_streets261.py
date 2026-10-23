"""Independent native geometry controls and gate approach walkability diagnostic.

Run once inside Blender. This does not write a component or modify the baseline.
It updates all layers first and uses real path direction instead of extending
an entrance normal into unrelated lawn or beyond an oblique pavement.
"""

import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import itertools

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v260.blend"
BASE_SHA = "c208a1086482bcc1bf20ec25ccdd9c684a0ea88a4891e5a007439c1076c1eec2"
OUT = ROOT / "result/blender/streets261"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    assert digest(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    transforms_before = {
        o.name: tuple(tuple(v) for v in o.matrix_world) for o in bpy.data.objects
    }
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    scene = bpy.context.scene
    changed = [
        o.name
        for o in bpy.data.objects
        if transforms_before[o.name] != tuple(tuple(v) for v in o.matrix_world)
    ]
    deps = bpy.context.evaluated_depsgraph_get()
    inspection = json.loads((OUT / "native-inspection.json").read_text())
    assert inspection["baselineSha256"] == BASE_SHA
    gate_positions = [Vector(g["centre"]) for g in inspection["gateChecks"]]
    geometry = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
    # The source paths only nominate probes. A supported sample must intersect
    # an evaluated native triangle; the archived map never supplies a height.
    routes = []
    for way in geometry["roads"]:
        if way["properties"].get("highway") != "footway":
            continue
        points = [Vector((*p, 0)) for p in way["geometry"]["coordinates"]]
        if any((p - g).length < 0.001 for p in points for g in gate_positions):
            routes.append((way["id"], points))
    owners = {}
    evaluated_objects = []
    fence_rows = []
    for obj in scene.objects:
        if obj.type != "MESH" or obj.hide_render:
            continue
        if not obj.name.startswith(
            ("SITE", "STREET", "GROUND", "PARK211_", "PARK233_")
        ):
            continue
        evaluated = obj.evaluated_get(deps)
        corners = [evaluated.matrix_world @ Vector(v) for v in evaluated.bound_box]
        if min(v.z for v in corners) > 1.6 or max(v.z for v in corners) < -0.1:
            continue
        mesh = evaluated.to_mesh()
        evaluated_objects.append(evaluated)
        mesh.calc_loop_triangles()
        vertices = [evaluated.matrix_world @ v.co for v in mesh.vertices]
        triangles = [tuple(t.vertices) for t in mesh.loop_triangles]
        if not triangles:
            continue
        tree = BVHTree.FromPolygons(vertices, triangles, all_triangles=True)
        owners[obj.name] = tree
        if obj.name.startswith("PARK211_"):
            fence_rows.extend([tuple(vertices[i] for i in t) for t in triangles])

    def ground(point):
        hits = []
        for name, tree in owners.items():
            location, normal, triangle, _distance = tree.ray_cast(
                point + Vector((0, 0, 0.20)), Vector((0, 0, -1)), 0.40
            )
            if location is not None and normal.z > 0.5:
                hits.append({"object": name, "z": location.z, "triangle": triangle})
        return sorted(hits, key=lambda row: -row["z"])

    paths = []
    for way, points in routes:
        samples = []
        for start, end in itertools.pairwise(points):
            length = (end - start).length
            count = max(1, math.ceil(length / 0.5))
            for index in range(count + 1):
                p = start.lerp(end, index / count)
                if min((p - g).length for g in gate_positions) > 14:
                    continue
                hits = ground(p)
                samples.append(
                    {
                        "xy": list(p.xy),
                        "hits": hits,
                        "pathSupport": bool(hits)
                        and hits[0]["z"] > 0.015
                        and hits[0]["z"] < 0.10
                        and "grass" not in hits[0]["object"].lower(),
                    }
                )
        paths.append(
            {
                "way": way,
                "samples": samples,
                "unsupported": sum(not r["pathSupport"] for r in samples),
            }
        )

    # Direct triangle/segment intersection is independent of BVHTree. These
    # positive controls prove the mapped visible fence has not been filtered out.
    def segment_triangle(origin, direction, triangle, limit):
        a, b, c = triangle
        edge1 = b - a
        edge2 = c - a
        h = direction.cross(edge2)
        det = edge1.dot(h)
        if abs(det) < 1e-10:
            return None
        inv = 1 / det
        s = origin - a
        u = inv * s.dot(h)
        if u < -1e-7 or u > 1 + 1e-7:
            return None
        q = s.cross(edge1)
        v = inv * direction.dot(q)
        if v < -1e-7 or u + v > 1 + 1e-7:
            return None
        t = inv * edge2.dot(q)
        return t if 0 <= t <= limit else None

    source_park = next(row for row in geometry["greens"] if row["id"] == "way/30613392")
    ring = [Vector((*p, 0)) for p in source_park["geometry"]["coordinates"][0][:-1]]
    fence_controls = []
    for start, end in zip(ring, ring[1:] + ring[:1]):
        along = (end - start).normalized()
        normal = Vector((-along.y, along.x, 0))
        # Two rail heights avoid relying on an arbitrary picket spacing.
        middle = (start + end) / 2 + Vector((0, 0, 1.31))
        origin = middle - normal * 0.2
        direct = [
            value
            for tri in fence_rows
            if (value := segment_triangle(origin, normal, tri, 0.4)) is not None
        ]
        fence_controls.append(
            {"xy": list(middle.xy), "directTriangleHits": len(direct)}
        )
    failures = []
    if len(paths) != 12 or len({row["way"] for row in paths}) != 12:
        failures.append(
            "Expected exactly12 distinct source routes through8 mapped gates."
        )
    if sum(len(row["samples"]) for row in paths) != 323 or any(
        not row["samples"] for row in paths
    ):
        failures.append(
            "Expected323 nonempty route-centre samples for the fixed source and configuration."
        )
    if any(not sample["pathSupport"] for row in paths for sample in row["samples"]):
        failures.append(
            "At least one requested route-centre sample lacks a low visible native path surface."
        )
    if len(fence_controls) != 16 or any(
        row["directTriangleHits"] <= 0 for row in fence_controls
    ):
        failures.append(
            "At least one of16 fence positive controls did not hit a real native triangle."
        )
    if digest(BASE) != BASE_SHA:
        failures.append("Baseline native file changed during verification.")
    output = {
        "version": 261,
        "status": "failed" if failures else "passed",
        "failureReasons": failures,
        "baselineSha256": BASE_SHA,
        "sourceGeometrySha256": digest(ROOT / "result/blender/site_geometry.json"),
        "layerUpdateApplied": True,
        "transformsChangedByLayerUpdate": changed,
        "meshOwners": list(owners),
        "visibleFenceTriangles": len(fence_rows),
        "fencePositiveControls": fence_controls,
        "sourceRouteChecks": paths,
        "routeSamples": sum(len(r["samples"]) for r in paths),
        "unsupportedRouteSamples": sum(r["unsupported"] for r in paths),
        "nativeSaved": False,
        "limitations": "Support diagnostic on archived mapped route centrelines, not current width or accessibility certification.",
    }
    (OUT / "independent-path-verification.json").write_text(
        json.dumps(output, indent=2) + "\n"
    )
    for obj in evaluated_objects:
        obj.to_mesh_clear()
    assert not failures, "; ".join(failures)
    print(
        "STREETS261_ROUTE_CHECK",
        output["routeSamples"],
        output["unsupportedRouteSamples"],
        "matrix updates",
        len(changed),
        flush=True,
    )


if __name__ == "__main__":
    verify()
