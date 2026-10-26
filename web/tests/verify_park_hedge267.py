"""Independently check the saved267hedge against original native triangles.

Run main() in a fresh Blender process. geometry_proof(audit) can also check an
already appended candidate. Geometry is read from meshes and archived GeoJSON;
no builder geometry, section indices or builder contact samples are trusted.
"""

import hashlib
import json
import math
import sys
from itertools import pairwise
from pathlib import Path

sys.dont_write_bytecode = True
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
BASE_SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/park267"
GROUND = "PARK233_Park_grass_outside_mapped_bandstand_hardstanding"
NAME = "PARK267_mapped_western_curved_hedge"
OWNER = "03_PUBLIC_REALM"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_houghton262 import capture
from refine_portsmouth_exterior207 import material_fingerprint


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_source():
    features = json.loads((ROOT / "data/collections/streets/derived/street_objects.geojson").read_text())["features"]
    source = next(f for f in features if f["id"] == "way/1367310700")
    assert source["properties"]["barrier"] == "hedge"
    assert source["geometry"]["type"] == "LineString"
    # Project the archived coordinates independently of the builder's frozen ENU list.
    lon0, lat0 = map(math.radians, (-0.1167, 51.5146))
    def ecef(lon, lat):
        lo, la = map(math.radians, (lon, lat))
        n = 6378137 / math.sqrt(1 - 6.69437999014e-3 * math.sin(la) ** 2)
        return (n * math.cos(la) * math.cos(lo), n * math.cos(la) * math.sin(lo),
                n * (1 - 6.69437999014e-3) * math.sin(la))
    origin = ecef(-0.1167, 51.5146)
    points = []
    for lon, lat in source["geometry"]["coordinates"]:
        d = [a-b for a, b in zip(ecef(lon, lat), origin)]
        points.append(Vector((-math.sin(lon0) * d[0] + math.cos(lon0) * d[1],
                              -math.sin(lat0) * math.cos(lon0) * d[0]
                              - math.sin(lat0) * math.sin(lon0) * d[1] + math.cos(lat0) * d[2])))
    assert len(points) == 10
    assert abs(sum((b - a).length for a, b in pairwise(points)) - 46.044556254) < 0.0001
    return points


def triangles(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    rows = []
    for t in mesh.loop_triangles:
        points = tuple(evaluated.matrix_world @ mesh.vertices[i].co for i in t.vertices)
        material = mesh.materials[t.material_index] if mesh.materials else None
        rows.append((points, material.name if material else ""))
    evaluated.to_mesh_clear()
    return rows


def tree(rows):
    points = [p for row in rows for p in row]
    return BVHTree.FromPolygons(points, [(3*i, 3*i+1, 3*i+2) for i in range(len(rows))],
                               all_triangles=True, epsilon=0)


def bounds(points):
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def xy_box(points):
    return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)


def box_distance(a, b):
    return math.hypot(max(a[0]-b[2], b[0]-a[2], 0), max(a[1]-b[3], b[1]-a[3], 0))


def point_segment(point, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx + dy*dy
    fraction = max(0, min(1, ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/length2)) if length2 else 0
    return math.hypot(point[0]-a[0]-fraction*dx, point[1]-a[1]-fraction*dy)


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def point_in_triangle(point, triangle):
    if abs(cross(*triangle)) < 1e-12:
        return False
    signs = [cross(a, b, point) for a, b in zip(triangle, triangle[1:]+triangle[:1])]
    return min(signs) >= -1e-8 or max(signs) <= 1e-8


def segment_distance(a, b, c, d):
    if cross(a, b, c)*cross(a, b, d) < 0 and cross(c, d, a)*cross(c, d, b) < 0:
        return 0.0
    return min(point_segment(a, c, d), point_segment(b, c, d),
               point_segment(c, a, b), point_segment(d, a, b))


def triangle_distance(a, b):
    if any(point_in_triangle(p, b) for p in a) or any(point_in_triangle(p, a) for p in b):
        return 0.0
    return min(segment_distance(p, q, r, s)
               for p, q in zip(a, a[1:]+a[:1]) for r, s in zip(b, b[1:]+b[:1]))


def projected_clearance(footprint, obstacles):
    assert obstacles, "Clearance set is empty"
    boxes = [xy_box(t) for t in footprint]
    whole = xy_box([p for t in footprint for p in t])
    ordered = sorted(((box_distance(whole, xy_box(t)), name, t, xy_box(t))
                      for name, t in obstacles), key=lambda r: r[0])
    best, witness, pair_checks = float("inf"), None, 0
    for lower, name, triangle, box in ordered:
        if lower > best:
            break
        for base, base_box in zip(footprint, boxes):
            if box_distance(base_box, box) > best:
                continue
            gap = triangle_distance(base, triangle)
            pair_checks += 1
            if gap < best:
                best, witness = gap, {"object": name, "nativeTriangle": [list(p) for p in triangle],
                                     "hedgeBaseTriangle": [list(p) for p in base]}
        if best == 0:
            break
    return {"minimumClearanceM": best, "nativeTriangles": len(obstacles),
            "actualTrianglePairsMeasured": pair_checks, "witness": witness}


def visible_meshes(scene):
    hidden = set()
    def visit(collection, inherited=False):
        inherited = inherited or collection.hide_render
        if inherited:
            hidden.update(o.name for o in collection.objects)
        for child in collection.children:
            visit(child, inherited)
    visit(scene.collection)
    return [o for o in scene.objects if o.type == "MESH" and not o.hide_render and o.name not in hidden]


def walking_surface_role(name, owners, material):
    """Material colour alone cannot turn a scene datum into a pedestrian route."""
    label = name.lower()
    if any(token in label for token in ("datum", "review_ground", "background", "base_ground", "ground_urban")):
        return "scene-datum-or-review"
    if not set(owners).intersection({"00_SITE", "03_PUBLIC_REALM"}):
        return "non-public-owner"
    if any(token in material.lower() for token in ("grass", "soil", "foliage")):
        return "planting-surface"
    route_name = any(token in label for token in ("footway", "footpath", "sidewalk", "pavement", "paving", "pavers", "kerb", "road_", "road_network"))
    # The accepted227replacement is an explicitly named asphalt route, whereas
    # a generic object with a reused Road asphalt material carries no route ID.
    route_name = route_name or (label.startswith(("street", "site")) and "asphalt" in label)
    return "public-route" if route_name else "other-retained-mesh"


def obstacle_role(name, owners):
    if not set(owners).intersection({"00_SITE", "03_PUBLIC_REALM"}):
        return None
    label = name.lower()
    return "trunks" if "trunk" in label else "benches" if "bench" in label else None


def semantic_classification_checks():
    cases = [
        ("SITE216_Expanded_flat_map_datum", ["00_SITE"], "Road asphalt", "scene-datum-or-review"),
        ("Ground_urban", ["00_SITE"], "Road asphalt.002", "scene-datum-or-review"),
        ("LRB_review_ground", ["00_SITE"], "Road asphalt", "scene-datum-or-review"),
        ("PARK233_cafe_closed_low_pitched_metal_roof", ["03_PUBLIC_REALM"], "Road asphalt", "other-retained-mesh"),
        ("SITE230_Slatted_benches_retained_six", ["03_PUBLIC_REALM"], "Road asphalt", "other-retained-mesh"),
        ("OLD_interior_paving", ["OLD_ROOM"], "stone", "non-public-owner"),
        ("SITE217_mapped_footway_body", ["00_SITE"], "SITE213_slab_concrete", "public-route"),
        ("SITE217_mapped_footway_edge", ["00_SITE"], "stone", "public-route"),
        ("STREET234_Mapped_asphalt_footways_deduplicated_with_contact_guard", ["00_SITE"], "Road asphalt", "public-route"),
        ("STREET227_Asphalt_clipped_beneath_retained_stone", ["00_SITE"], "Road asphalt", "public-route"),
        ("00_SITE_Road_Lincoln's Inn Fields", ["00_SITE"], "Road asphalt", "public-route"),
        ("SITE217_mapped_footway_body", ["00_SITE"], "park grass", "planting-surface"),
    ]
    for name, owners, material, expected in cases:
        assert walking_surface_role(name, owners, material) == expected, name
    obstacles = [
        ("03_PUBLIC_REALM_Plane_tree_trunk", ["03_PUBLIC_REALM"], "trunks"),
        ("SITE230_Slatted_benches_retained_six", ["03_PUBLIC_REALM"], "benches"),
        ("OLD_slatted_vent", ["00_SITE"], None),
        ("interior_bench", ["OLD_ROOM"], None),
    ]
    for name, owners, expected in obstacles:
        assert obstacle_role(name, owners) == expected, name
    return len(cases) + len(obstacles)


def native_sets(candidate_bounds):
    low, high = candidate_bounds
    rectangle = (low[0], low[1], high[0], high[1])
    # Existing paths sit atZ0.024below theZ0.05grass datum. Their horizontal
    # footprint still constrains access even without a3Dsurface intersection.
    surface_min_z = min(low[2]-0.10, -0.05)
    groups = {"paths": [], "trunks": [], "benches": []}
    collision_rows, inventory = [], []
    for obj in visible_meshes(bpy.data.scenes["00_CAMPUS_COMPLETE"]):
        if obj.name == NAME or obj.name == GROUND:
            continue
        owners = sorted(c.name for c in obj.users_collection)
        category = obstacle_role(obj.name, owners)
        corners = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
        obj_low, obj_high = bounds(corners)
        if obj_high[2] < surface_min_z or obj_low[2] > high[2]+0.01:
            continue
        nearby = box_distance(rectangle, xy_box(corners)) <= 5
        if not nearby and category is None:
            continue
        counts = {"collisionTriangles": 0, "pathTriangles": 0, "obstacleTriangles": 0}
        semantic_roles = {}
        rows = triangles(obj)
        for points, material in rows:
            tri_low, tri_high = bounds(points)
            if tri_high[2] < surface_min_z or tri_low[2] > high[2]+0.01:
                continue
            if category:
                groups[category].append((obj.name, points))
                counts["obstacleTriangles"] += 1
            if box_distance(rectangle, xy_box(points)) > 5:
                continue
            collision_rows.append((obj.name, points))
            counts["collisionTriangles"] += 1
            role = walking_surface_role(obj.name, owners, material)
            semantic_roles[role] = semantic_roles.get(role, 0) + 1
            walking = role == "public-route"
            normal = (points[1]-points[0]).cross(points[2]-points[0])
            horizontal = normal.length > 1e-10 and abs(normal.normalized().z) > 0.9
            if walking and horizontal and tri_high[2] < 0.2 and tri_high[2]-tri_low[2] < 0.02:
                groups["paths"].append((obj.name, points))
                counts["pathTriangles"] += 1
        if any(counts.values()):
            inventory.append({"object": obj.name, "owners": owners, "category": category,
                              "walkingSurfaceRoles": semantic_roles, **counts})
    assert groups["paths"] and groups["trunks"] and groups["benches"], "Missing actual native clearance geometry"
    return groups, collision_rows, inventory


def geometry_proof(audit):
    semantic_cases = semantic_classification_checks()
    update_scene()
    assert audit["addedObjects"] == [NAME] and len(audit["addedObjects"]) <= 3
    obj = bpy.data.objects[NAME]
    assert obj.type == "MESH" and not obj.hide_render
    assert sorted(c.name for c in obj.users_collection) == [OWNER]
    assert not obj.modifiers and obj.parent is None
    assert object_fingerprint(obj) == audit["addedFingerprints"][NAME]
    assert [m.name for m in obj.data.materials] == audit["replacementMaterialBindings"][NAME]
    for mat in obj.data.materials:
        assert material_fingerprint(mat) == audit["reusedMaterialGraphs"][mat.name]
        shader = mat.node_tree.nodes.get("Principled BSDF")
        assert shader.inputs["Alpha"].default_value == 1 and shader.inputs["Transmission Weight"].default_value == 0
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    assert all(e.is_manifold for e in bm.edges), "Hedge has an open or nonmanifold edge"
    assert all(v.link_edges for v in bm.verts), "Loose vertices"
    pending, components = set(bm.verts), 0
    while pending:
        components += 1
        todo = [pending.pop()]
        while todo:
            for edge in todo.pop().link_edges:
                for vertex in edge.verts:
                    if vertex in pending:
                        pending.remove(vertex)
                        todo.append(vertex)
    assert components == 1, "Hedge must be one continuous solid"
    volume = bm.calc_volume(signed=True)
    assert 20 < volume < 50, ("Unexpected signed hedge volume", volume)
    bm.free()
    rows = [t for t, _ in triangles(obj)]
    assert len(rows) <= 5000
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    low, high = bounds(points)
    line = read_source()
    max_offset = max(min(point_segment(p, a, b) for a, b in pairwise(line)) for p in points)
    assert max_offset <= 0.401, ("Hedge extends beyond the estimated0.8m corridor", max_offset)
    first = (line[1]-line[0]).normalized()
    last = (line[-1]-line[-2]).normalized()
    assert min((p.xy-line[0]).dot(first) for p in points) >= -0.0001
    assert max((p.xy-line[-1]).dot(last) for p in points) <= 0.0001
    floor = tree([t for t, _ in triangles(bpy.data.objects[GROUND])])
    bottom = [t for t in rows if (t[1]-t[0]).cross(t[2]-t[0]).normalized().z < -0.9]
    assert bottom and all(max(p.z for p in t) < 0.07 for t in bottom)
    # Every actual mesh vertex must lie inside the actual base footprint. Thus
    # projected obstacle distances also bound the upper foliage envelope.
    for p in points:
        assert any(point_in_triangle(p, t) or min(point_segment(p, a, b) for a, b in zip(t, t[1:]+t[:1])) < 0.00003 for t in bottom)
    samples = [p for t in bottom for p in t] + [sum(t, Vector()) / 3 for t in bottom]
    gaps = []
    for p in samples:
        hit, normal, _, _ = floor.ray_cast(p + Vector((0, 0, 0.15)), Vector((0, 0, -1)), 0.3)
        assert hit is not None and normal.z > 0.8, ("Base lacks actual grass support", list(p))
        gaps.append(p.z-hit.z)
    assert min(gaps) >= -0.001 and max(gaps) <= 0.0001, (min(gaps), max(gaps))
    heights = []
    for p in points:
        hit, _, _, _ = floor.ray_cast(Vector((p.x, p.y, 2)), Vector((0, 0, -1)), 3)
        assert hit is not None
        heights.append(p.z-hit.z)
    assert 1.19 <= max(heights) <= 1.201
    hedge_tree = tree(rows)
    widths = []
    for a, b in pairwise(line):
        tangent = (b-a).normalized()
        normal = Vector((-tangent.y, tangent.x, 0))
        for fraction in (0.23, 0.50, 0.77):
            p = a.lerp(b, fraction)
            hit, _, _, _ = floor.ray_cast(Vector((p.x, p.y, 2)), Vector((0, 0, -1)), 3)
            centre = Vector((p.x, p.y, hit.z+0.30))
            positive = hedge_tree.ray_cast(centre+normal, -normal, 2)
            negative = hedge_tree.ray_cast(centre-normal, normal, 2)
            assert positive[0] is not None and negative[0] is not None
            width = (positive[0]-negative[0]).length
            assert 0.76 <= width <= 0.82, ("Actual hedge width", width)
            widths.append(width)
    groups, obstacles, inventory = native_sets((low, high))
    clearance = {kind: projected_clearance(bottom, native) for kind, native in groups.items()}
    assert clearance["paths"]["minimumClearanceM"] >= 0.35, clearance["paths"]
    assert clearance["trunks"]["minimumClearanceM"] >= 0.10, clearance["trunks"]
    assert clearance["benches"]["minimumClearanceM"] >= 0.10, clearance["benches"]
    # Also test every retained nearby surface, regardless of semantic category.
    collision_tree = tree([t for _, t in obstacles])
    intersections = hedge_tree.overlap(collision_tree)
    assert not intersections, [{"hedgeTriangle": a, "object": obstacles[b][0],
                                 "nativeTriangle": [list(p) for p in obstacles[b][1]]}
                                for a, b in intersections[:8]]
    return {"status": "passed", "connectedClosedSolids": components, "volumeM3": volume,
            "triangles": len(rows), "objects": 1, "newMaterials": 0, "newImages": 0,
            "maximumMappedLineOffsetM": max_offset,
            "actualWidthM": {"minimum": min(widths), "maximum": max(widths), "samples": len(widths)},
            "actualMaximumHeightM": max(heights),
            "groundSupport": {"nativeObject": GROUND, "actualBaseSamples": len(samples),
                              "minimumGapM": min(gaps), "maximumGapM": max(gaps)},
            "projectedNativeClearances": clearance, "nativeMeshInventory": inventory,
            "semanticClassificationCases": semantic_cases,
            "walkingSurfacePolicy": "Public-route object identity plus native owner; reused asphalt/paving material alone is insufficient. Scene datums remain in3Dcollision checks.",
            "retainedSurfaceTrianglesChecked": len(obstacles), "crossingTrianglePairs": 0,
            "originalGroundExcludedOnlyAsSupportingSurface": GROUND,
            "limits": "Native triangle clearance is a model check. Estimated hedge dimensions and archived source alignment are not a2026plant survey."}


def main():
    assert sha(BASE) == BASE_SHA
    audit = json.loads((OUT / "audit.json").read_text())
    component = ROOT / audit["componentPath"]
    assert audit["baselineSha256"] == BASE_SHA and sha(component) == audit["componentSha256"]
    for path, digest in audit["sourceHashes"].items():
        assert sha(ROOT / path) == digest, path
    assert sha(ROOT / audit["verificationScript"]) == audit["verificationScriptSha256"]
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert set(bpy.data.objects.keys()) == {NAME}
    assert object_fingerprint(bpy.data.objects[NAME]) == audit["addedFingerprints"][NAME]
    assert set(bpy.data.materials.keys()) == set(audit["reusedMaterialGraphs"])
    assert len(bpy.data.images) == 0
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = capture()
    scene_members = {s.name: sorted(o.name for o in s.objects) for s in bpy.data.scenes}
    old_images = sorted(i.name for i in bpy.data.images)
    assert len(before["objects"]) == 8748 and len(before["materials"]) == 2355
    assert len(before["rooms"]) == 35
    with bpy.data.libraries.load(str(component), link=False) as (_, destination):
        # Blender replaces names with loaded objects in this list. Keep the audit immutable.
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0
            bpy.data.materials.remove(material)
    update_scene()
    after = capture()
    for name, value in before["objects"].items():
        assert after["objects"][name] == value, name
        assert after["visibility"][name] == before["visibility"][name], name
    assert set(after["objects"]) == set(before["objects"]) | {NAME}
    assert after["materials"] == before["materials"]
    assert after["rooms"] == before["rooms"] and after["campusRooms"] == before["campusRooms"]
    assert sorted(i.name for i in bpy.data.images) == old_images
    for scene, members in scene_members.items():
        assert sorted(o.name for o in bpy.data.scenes[scene].objects if o.name != NAME) == members
    proof = geometry_proof(audit)
    assert sha(BASE) == BASE_SHA and sha(component) == audit["componentSha256"]
    result = {"status": "passed", "freshBlenderProcess": True,
              "baselineSha256": BASE_SHA, "componentSha256": audit["componentSha256"],
              "actualMeshProof": proof, "originalObjectsProtected": 8748,
              "originalMaterialGraphsProtected": 2355, "roomMembershipsProtected": 35,
              "allOriginalGeometryNormalsUVsOwnersPropertiesModifiersVisibilityPreserved": True,
              "originalCampusRoomMembershipsPreserved": True, "nativeSaved": False}
    (OUT / "fresh-process-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PARK267_FRESH_PROCESS_VERIFIED", audit["componentSha256"], flush=True)


if __name__ == "__main__":
    main()
