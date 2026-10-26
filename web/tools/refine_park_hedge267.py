"""Author the archived western Lincoln's Inn Fields hedge as one small component.

Open in Blender's Text Editor and run main(). STAGE selects inspect or build;
there are no command-line options. The complete263 native file is read-only.
Only the mapped46.04m line is reconstructed. Width0.8m,height1.2m and foliage
contours are presentation estimates. No full-campus save or new material/image.
"""

import hashlib
import importlib.util
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
STAGE = "build"
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
BASE_SHA = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUT = ROOT / "result/blender/park267"
COMPONENT = OUT / "component.blend"
SOURCE_AUDIT = ROOT / "result/blender/park267-audit.json"
SOURCE_GEOJSON = ROOT / "data/collections/streets/derived/street_objects.geojson"
WAY = "way/1367310700"
OWNER = "03_PUBLIC_REALM"
GROUND = "PARK233_Park_grass_outside_mapped_bandstand_hardstanding"
NAME = "PARK267_mapped_western_curved_hedge"
WIDTH, HEIGHT = 0.8, 1.2
SECTION_STEP = 0.70
CONTACT_INSET = 0.0005
MATERIALS = ["SITE232_LIF_opaque_foliage_" + str(i) for i in (0, 1, 2)]
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


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def snapshot():
    result = capture()
    result["baselineSha256"] = BASE_SHA
    result["sceneMembers"] = {
        s.name: sorted(o.name for o in s.objects) for s in bpy.data.scenes
    }
    result["images"] = sorted(i.name for i in bpy.data.images)
    return result


def unchanged(before, added=()):
    after = snapshot()
    for name, state in before["objects"].items():
        assert after["objects"][name] == state, ("Original object changed", name)
        assert after["visibility"][name] == before["visibility"][name], name
    assert set(after["objects"]) == set(before["objects"]) | set(added)
    assert after["materials"] == before["materials"], "Original material graphs changed"
    assert after["rooms"] == before["rooms"] and len(after["rooms"]) == 35
    assert after["campusRooms"] == before["campusRooms"]
    assert after["images"] == before["images"], "Image datablocks changed"
    for name, members in before["sceneMembers"].items():
        assert sorted(n for n in after["sceneMembers"][name] if n not in added) == members
    assert sha(BASE) == BASE_SHA


def source_line():
    frozen = json.loads(SOURCE_AUDIT.read_text())
    for path in [SOURCE_GEOJSON, ROOT / "data/collections/streets/raw/osm_map.osm"]:
        assert sha(path) == frozen["sourceHashes"][str(path.relative_to(ROOT))]
    feature = next(
        f for f in json.loads(SOURCE_GEOJSON.read_text())["features"] if f["id"] == WAY
    )
    assert feature["geometry"]["type"] == "LineString"
    assert feature["properties"]["barrier"] == "hedge"
    assert feature["properties"]["osm_timestamp"] == "2025-03-14T11:32:05Z"
    points = [Vector(p) for p in frozen["selectedFinding"]["alignmentENU_m"]]
    assert len(points) == len(feature["geometry"]["coordinates"]) == 10
    assert abs(sum((b - a).length for a, b in pairwise(points)) - 46.044556254) < 0.0001
    return points, feature["properties"]


def surface_tree(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    mesh.calc_loop_triangles()
    result = BVHTree.FromPolygons(
        [evaluated.matrix_world @ v.co for v in mesh.vertices],
        [tuple(t.vertices) for t in mesh.loop_triangles],
        all_triangles=True,
    )
    evaluated.to_mesh_clear()
    return result


def ground_height(tree, xy):
    hit, normal, _, _ = tree.ray_cast(Vector((xy.x, xy.y, 2)), Vector((0, 0, -1)), 3)
    assert hit is not None and normal.z > 0.8, ("Native grass support missing", list(xy))
    assert abs(hit.z - 0.05) < 0.005, ("Unexpected native ground datum", list(hit))
    return hit.z


def sections(points):
    result, station = [], 0.0
    for a, b in pairwise(points):
        length = (b - a).length
        count = math.ceil(length / SECTION_STEP)
        for index in range(count):
            fraction = index / count
            result.append((a.lerp(b, fraction), station + length * fraction))
        station += length
    result.append((points[-1].copy(), station))
    return result


def inspect():
    assert sha(BASE) == BASE_SHA
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = snapshot()
    assert len(before["objects"]) == 8748 and len(before["materials"]) == 2355
    assert len(before["rooms"]) == 35 and NAME not in bpy.data.objects
    points, properties = source_line()
    floor = bpy.data.objects[GROUND]
    assert not floor.hide_render
    ground = surface_tree(floor)
    samples = []
    for index, (xy, station) in enumerate(sections(points)):
        samples.append({"xy": list(xy), "stationM": station, "groundZ": ground_height(ground, xy)})
    result = {
        "baseline": str(BASE.relative_to(ROOT)), "baselineSha256": BASE_SHA,
        "sourceWay": WAY, "sourceProperties": properties,
        "samples": samples, "nativeGroundObject": GROUND,
        "sourceAuditSha256": sha(SOURCE_AUDIT), "nativeSaved": False,
        "originalObjects": len(before["objects"]), "originalMaterials": len(before["materials"]),
        "roomMemberships": len(before["rooms"]),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "native-inspection.json", result)
    unchanged(before)
    return before, points, ground, properties


def build_volume(points, ground):
    rows = sections(points)
    vertices, faces, slots, contacts = [], [], [], []
    # A rounded shoulder and broad longitudinal lobes form one connected skin.
    # These are foliage masses, not separate leaf cards or intersecting shells.
    profile = [(-0.4, 0), (0.4, 0), (0.4, 0.60), (0.34, 0.88),
               (0.15, 0.99), (-0.13, 1.0), (-0.34, 0.88), (-0.4, 0.60)]
    for index, (xy, station) in enumerate(rows):
        previous = rows[max(0, index - 1)][0]
        following = rows[min(len(rows) - 1, index + 1)][0]
        tangent = (following - previous).normalized()
        normal = Vector((-tangent.y, tangent.x))
        broad_lobe = (1 - math.cos(math.tau * station / 3.8)) / 2
        top = HEIGHT - 0.045 * broad_lobe
        for across, fraction in profile:
            point = xy + normal * across
            support = ground_height(ground, point)
            vertices.append((point.x, point.y, support - CONTACT_INSET + top * fraction))
            if fraction == 0:
                contacts.append({"xy": list(point), "groundZ": support})
    count = len(profile)
    faces.append(tuple(reversed(range(count))))
    slots.append(0)
    for row in range(len(rows) - 1):
        for side in range(count):
            following = (side + 1) % count
            faces.append((row * count + side, row * count + following,
                          (row + 1) * count + following, (row + 1) * count + side))
            # Shade coherent broad masses, rather than assigning random leaf colours.
            slots.append(0 if side == 0 else (int(rows[row][1] / 3.8) + side // 3) % 3)
    faces.append(tuple((len(rows) - 1) * count + k for k in range(count)))
    slots.append(0)
    mesh = bpy.data.meshes.new(NAME + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    for name in MATERIALS:
        material = bpy.data.materials[name]
        principled = material.node_tree.nodes.get("Principled BSDF")
        assert principled.inputs["Alpha"].default_value == 1
        assert principled.inputs["Transmission Weight"].default_value == 0
        mesh.materials.append(material)
    for polygon, slot in zip(mesh.polygons, slots):
        polygon.material_index = slot
        polygon.use_smooth = False
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(edge.is_manifold for edge in bm.edges)
    assert bm.calc_volume(signed=True) > 20
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    uv = mesh.uv_layers.new(name="Metric")
    for loop in mesh.loops:
        point = mesh.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (point.x, point.z)
    obj = bpy.data.objects.new(NAME, mesh)
    obj.use_fake_user = True
    bpy.data.collections[OWNER].objects.link(obj)
    obj["destinationCollection"] = OWNER
    obj["sourceOsmWay"] = WAY
    obj["dimensionsEstimated"] = True
    obj["estimatedWidthMetres"] = WIDTH
    obj["estimatedMaximumHeightMetres"] = HEIGHT
    obj["scope"] = "Only the archived46.04mopen western hedge; no whole-park planting inference"
    obj["sourceAuditSha256"] = sha(SOURCE_AUDIT)
    return obj, contacts


def verifier():
    path = ROOT / "web/tests/verify_park_hedge267.py"
    spec = importlib.util.spec_from_file_location("park267_independent_geometry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_component(audit, before):
    with bpy.data.libraries.load(str(COMPONENT), link=False) as (_, destination):
        # Blender replaces names with loaded objects in this list. Keep the audit immutable.
        destination.objects = list(audit["addedObjects"])
    for obj in destination.objects:
        for index, name in enumerate(audit["replacementMaterialBindings"][obj.name]):
            obj.data.materials[index] = bpy.data.materials[name]
        bpy.data.collections[OWNER].objects.link(obj)
    for material in list(bpy.data.materials):
        if material.name not in before["materials"]:
            assert material.users == 0, ("Unexpected imported material user", material.name)
            bpy.data.materials.remove(material)
    update_scene()
    return destination.objects


def build():
    before, points, ground, properties = inspect()
    write(OUT / "protected-source-state.json", before)
    obj, contacts = build_volume(points, ground)
    update_scene()
    obj.data.calc_loop_triangles()
    assert len(obj.data.loop_triangles) < 5000
    unchanged(before, [NAME])
    paths = [SOURCE_AUDIT, SOURCE_GEOJSON,
             ROOT / "data/collections/streets/raw/osm_map.osm",
             ROOT / "result/blender/stage263/reopened-verification.json",
             ROOT / "web/tools/building-metadata.json"]
    audit = {
        "version": 267, "status": "candidate-built-not-published",
        "baseline": str(BASE.relative_to(ROOT)), "baselineSha256": BASE_SHA,
        "componentPath": str(COMPONENT.relative_to(ROOT)),
        "targetCollection": OWNER, "destinationCollection": OWNER,
        "addedObjects": [NAME], "archivedObjects": [], "changedObjects": [],
        "addedFingerprints": {NAME: object_fingerprint(obj)},
        "objectOwners": {NAME: OWNER},
        "replacementMaterialBindings": {NAME: MATERIALS},
        "reusedMaterialGraphs": {n: material_fingerprint(bpy.data.materials[n]) for n in MATERIALS},
        "addedMaterialFingerprints": {}, "newMaterialGraphs": {},
        "sourceWay": WAY, "sourceProperties": properties,
        "sourceHashes": {str(p.relative_to(ROOT)): sha(p) for p in paths},
        "sourceAudit": str(SOURCE_AUDIT.relative_to(ROOT)),
        "sourceAuditSha256": sha(SOURCE_AUDIT),
        "authoringScript": str(Path(__file__).relative_to(ROOT)),
        "authoringScriptSha256": sha(Path(__file__)),
        "verificationScript": "web/tests/verify_park_hedge267.py",
        "verificationScriptSha256": sha(ROOT / "web/tests/verify_park_hedge267.py"),
        "dimensions": {"mappedLengthM": 46.04455625407017,
                       "estimatedWidthM": WIDTH, "estimatedMaximumHeightM": HEIGHT,
                       "estimatedTopVariationM": 0.045,
                       "groundContactInsetM": CONTACT_INSET},
        "budget": {"objects": 1, "vertices": len(obj.data.vertices),
                   "triangles": len(obj.data.loop_triangles),
                   "newMaterials": 0, "newImages": 0, "reusedMaterialSlots": len(MATERIALS)},
        "scope": "Restore only the source-mapped western curved hedge as one closed continuous opaque volume with broad low-poly foliage lobes.",
        "limitations": ["OSM2025mapping is not a current planting survey.",
                        "Width,height,foliage shape and colour are presentation estimates.",
                        "No complete perimeter shrub bed,plant species or current pruning state inferred."],
        "builderContactSamples": contacts,
        "protectedSourceState": "result/blender/park267/protected-source-state.json",
        "noFullNativeSaved": True,
    }
    # Save only the new object and its existing material dependencies.
    bpy.data.libraries.write(str(COMPONENT), {obj}, fake_user=False)
    audit["componentSha256"] = sha(COMPONENT)
    bpy.ops.wm.open_mainfile(filepath=str(COMPONENT))
    assert set(bpy.data.objects.keys()) == {NAME}
    assert object_fingerprint(bpy.data.objects[NAME]) == audit["addedFingerprints"][NAME]
    assert all(material_fingerprint(bpy.data.materials[n]) == v
               for n, v in audit["reusedMaterialGraphs"].items())
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    append_component(audit, before)
    unchanged(before, [NAME])
    proof = verifier().geometry_proof(audit)
    assert sha(COMPONENT) == audit["componentSha256"]
    audit["verification"] = {"componentReopened": True, "componentAppendedToExactBaseline": True,
                             "originalObjectsProtected": 8748, "originalMaterialsProtected": 2355,
                             "roomMembershipsProtected": 35, "allOriginalStateUnchanged": True,
                             "actualMeshProof": proof, "freshProcessRequired": True}
    write(OUT / "audit.json", audit)
    write(OUT / "verification.json", {"status": "passed-builder-roundtrip",
          "baselineSha256": BASE_SHA, "componentSha256": audit["componentSha256"],
          "actualMeshProof": proof, "freshBlenderProcess": False,
          "originalObjectsProtected": 8748, "originalMaterialsProtected": 2355,
          "roomMembershipsProtected": 35, "nativeSaved": False})
    print("PARK267_COMPONENT_READY", audit["componentSha256"], flush=True)


def main(stage=STAGE):
    if stage == "inspect":
        inspect()
    elif stage == "build":
        build()
    else:
        raise ValueError("Stage must be inspect or build")


if __name__ == "__main__":
    main()
