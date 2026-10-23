"""Recover two photographed Sheffield planter/seat units at retained tree sites.

Run inside Blender. Fixed configuration, no arguments, no renders and no native
save. Original8735objects,2350materials and35room studies remain unchanged.
"""

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
OUT = ROOT / "result/blender/sheffield262"
BASE = ROOT / "result/blender/LSE_campus_detailed_v261.blend"
BASE_SHA = "9890521a376afabfbb3d6c130d20ce40988315c49b8adea4c00749960a97482a"
PREFIX = "SHEFFIELD262_"
NAMES = [
    PREFIX + "painted_planter_shells_seats_and_root_clear_baseplates",
    PREFIX + "soil_with_open_tree_root_wells",
]
OWNER = "SAW_EXTERIOR"
TREE_CENTRES = [
    (-51.93190161640516, -5.006349644512923),
    (-45.35089874267578, 10.536345958709717),
]
ALONG = Vector((0.342, 0.93969262, 0)).normalized()
ACROSS = Vector((ALONG.y, -ALONG.x, 0))
RED = "SAW_NEXT_D2_steel_red"
SOIL = "SITE_V47_soil"
PAVING = [
    "SITE194_SITE_V47_Sheffield_Street",
    "SITE211_Sheffield_Street_stone_courses",
    "SITE211_Sheffield_Street_joint_bed",
]
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import object_fingerprint, update_scene
from refine_ksw_exterior219 import modifier_state
from refine_portsmouth_exterior207 import material_fingerprint


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, r):
    p.write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")


def state():
    meta = json.loads((ROOT / "web/tools/building-metadata.json").read_text())
    rooms = {
        r["collection"]: sorted(
            o.name for o in bpy.data.collections[r["collection"]].all_objects
        )
        for r in meta["spaces"]
    }
    return {
        "objects": {o.name: object_fingerprint(o) for o in bpy.data.objects},
        "materials": {m.name: material_fingerprint(m) for m in bpy.data.materials},
        "owners": {
            o.name: sorted(c.name for c in o.users_collection) for o in bpy.data.objects
        },
        "modifiers": {o.name: modifier_state(o) for o in bpy.data.objects},
        "props": {o.name: repr(sorted(o.items())) for o in bpy.data.objects},
        "visibility": {o.name: o.hide_render for o in bpy.data.objects},
        "rooms": rooms,
    }


def preserve(before):
    assert all(
        object_fingerprint(bpy.data.objects[n]) == v
        for n, v in before["objects"].items()
    )
    assert all(
        material_fingerprint(bpy.data.materials[n]) == v
        for n, v in before["materials"].items()
    )
    assert all(
        sorted(c.name for c in bpy.data.objects[n].users_collection) == v
        for n, v in before["owners"].items()
    )
    assert all(
        modifier_state(bpy.data.objects[n]) == v for n, v in before["modifiers"].items()
    )
    assert all(
        repr(sorted(bpy.data.objects[n].items())) == v
        for n, v in before["props"].items()
    )
    assert all(
        bpy.data.objects[n].hide_render == v for n, v in before["visibility"].items()
    )
    assert all(
        sorted(o.name for o in bpy.data.collections[n].all_objects) == v
        for n, v in before["rooms"].items()
    )
    assert sha(BASE) == BASE_SHA


class Batch:
    def __init__(self, name, material):
        self.name = name
        self.material = material
        self.vertices = []
        self.faces = []
        self.solids = []

    def add(self, points, faces, label):
        first = len(self.vertices)
        self.vertices.extend(points)
        self.faces.extend(tuple(first + i for i in f) for f in faces)
        self.solids.append(label)

    def box(self, centre, u, v, height, label):
        points = [
            centre
            + ALONG * (a * u / 2)
            + ACROSS * (b * v / 2)
            + Vector((0, 0, c * height / 2))
            for a, b, c in [
                (-1, -1, -1),
                (1, -1, -1),
                (1, 1, -1),
                (-1, 1, -1),
                (-1, -1, 1),
                (1, -1, 1),
                (1, 1, 1),
                (-1, 1, 1),
            ]
        ]
        # ALONG x ACROSS points down, so reverse the conventional right-handed box.
        faces = [
            tuple(reversed(f))
            for f in [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ]
        ]
        self.add(points, faces, label)

    def bearing_foot(self, centre, ground_tree, top, label):
        points = []
        contacts = []
        for a, b in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
            p = centre + ALONG * (a * 0.05) + ACROSS * (b * 0.05)
            hit = ground_tree.ray_cast(p + Vector((0, 0, 0.3)), Vector((0, 0, -1)), 0.4)
            assert hit[0] is not None, (
                label,
                "No real pavement at bearing corner",
                list(p),
            )
            assert 0.020 <= hit[0].z <= 0.051
            points.append(Vector((p.x, p.y, hit[0].z - 0.0005)))
            contacts.append(
                {
                    "xy": list(p.xy),
                    "supportZ": hit[0].z,
                    "bottomZ": hit[0].z - 0.0005,
                    "triangle": hit[2],
                }
            )
        points.extend(Vector((p.x, p.y, top)) for p in list(points))
        faces = [
            tuple(reversed(f))
            for f in [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ]
        ]
        self.add(points, faces, label)
        return contacts

    def rooted_ring(self, centre, half_u, half_v, radius, bottom, top, label):
        count = 32
        points = []
        # Build in right-handed world XY. The outer rectangle follows ALONG/ACROSS
        # but its sample order is reversed to account for their left handed frame.
        for z in [bottom, top]:
            for family in ["outer", "inner"]:
                for i in range(count):
                    a = -i * math.tau / count
                    du, dv = math.cos(a), math.sin(a)
                    scale = (
                        min(
                            half_u / abs(du) if abs(du) > 1e-12 else 1e9,
                            half_v / abs(dv) if abs(dv) > 1e-12 else 1e9,
                        )
                        if family == "outer"
                        else radius
                    )
                    points.append(
                        centre
                        + ALONG * (du * scale)
                        + ACROSS * (dv * scale)
                        + Vector((0, 0, z))
                    )
        faces = []
        for i in range(count):
            j = (i + 1) % count
            faces.extend(
                [
                    (i, j, 2 * count + j, 2 * count + i),
                    (count + j, count + i, 3 * count + i, 3 * count + j),
                    (2 * count + i, 2 * count + j, 3 * count + j, 3 * count + i),
                    (j, i, count + i, count + j),
                ]
            )
        self.add(points, faces, label)

    def finish(self):
        mesh = bpy.data.meshes.new(self.name + "_mesh")
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(bpy.data.materials[self.material])
        mesh.update()
        uv = mesh.uv_layers.new(name="MetricUV")
        for loop in mesh.loops:
            uv.data[loop.index].uv = mesh.vertices[loop.vertex_index].co.xy
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.normal_update()
        assert all(e.is_manifold for e in bm.edges), self.name
        assert bm.calc_volume(signed=True) > 0, self.name
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections[OWNER].objects.link(obj)
        obj["destinationCollection"] = OWNER
        obj["sourceReview"] = "result/blender/sheffield262/source-review.json"
        obj["scope"] = (
            "Two photograph-supported red planter/seat units registered to retained native tree positions; source-based estimated dimensions, no new tree or lamp."
        )
        obj["dimensionStatus"] = (
            "Estimated furniture proportions; exact existing tree positions, paving and all other native objects retained."
        )
        return obj


def build():
    assert sha(BASE) == BASE_SHA
    assert not (OUT / "component.blend").exists(), "Retain existing component evidence."
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    update_scene()
    before = state()
    assert (
        len(before["objects"]) == 8735
        and len(before["materials"]) == 2350
        and len(before["rooms"]) == 35
    )
    inspection = json.loads((OUT / "native-inspection.json").read_text())
    assert inspection["baselineSha256"] == BASE_SHA
    assert not any(name.startswith(PREFIX) for name in bpy.data.objects)
    paving_vertices = []
    paving_faces = []
    for name in PAVING:
        paving = bpy.data.objects[name]
        assert not paving.hide_render
        paving.data.calc_loop_triangles()
        offset = len(paving_vertices)
        paving_vertices.extend(paving.matrix_world @ v.co for v in paving.data.vertices)
        paving_faces.extend(
            tuple(offset + i for i in t.vertices) for t in paving.data.loop_triangles
        )
    pt = BVHTree.FromPolygons(paving_vertices, paving_faces, all_triangles=True)
    red = Batch(NAMES[0], RED)
    soil = Batch(NAMES[1], SOIL)
    units = []
    supports = []
    for index, xy in enumerate(TREE_CENTRES):
        centre = Vector((*xy, 0))
        unit_contacts = []
        # Probe the actual support under both long walls, two ends and the seat front.
        for u in [-0.90, -0.68, 0, 0.68, 0.90]:
            for v in [-0.80, 0.80, 1.24]:
                p = centre + ALONG * u + ACROSS * v
                hit = pt.ray_cast(p + Vector((0, 0, 0.3)), Vector((0, 0, -1)), 0.4)
                assert hit[0] is not None, (index, u, v, "missing existing paving")
                assert 0.020 <= hit[0].z <= 0.051, (index, u, v, hit[0].z)
                unit_contacts.append(
                    {"xy": list(p.xy), "supportZ": hit[0].z, "triangle": hit[2]}
                )
        ground = max(row["supportZ"] for row in unit_contacts) + 0.014
        # The shell is carried by individually grounded hidden bearing feet. A slab
        # height difference is not converted into an allowed unsupported base gap.
        for a, b in [
            (-0.68, -0.79),
            (0.68, -0.79),
            (-0.68, 0.79),
            (0.68, 0.79),
            (-0.68, 1.24),
            (0.68, 1.24),
        ]:
            contacts = red.bearing_foot(
                centre + ALONG * a + ACROSS * b,
                pt,
                ground + 0.003,
                f"unit{index}_actual_ground_bearing_{a}_{b}",
            )
            supports.extend(dict(unit=index, bearing=True, **row) for row in contacts)

        def p(u, v, z, anchor=centre, base_z=ground):
            return anchor + ALONG * u + ACROSS * v + Vector((0, 0, base_z + z))

        # 1.90x1.64m planter, open at top. All walls are closed slender solids.
        for side in [-1, 1]:
            red.box(
                p(0, side * 0.79, 0.255),
                1.90,
                0.06,
                0.51,
                f"unit{index}_long_wall_{side}",
            )
            red.box(
                p(side * 0.92, 0, 0.255),
                0.06,
                1.52,
                0.51,
                f"unit{index}_end_wall_{side}",
            )
        # Open-root base plate clears the retained trunk and entire old grate height.
        # It connects to the wall inner faces and carries the soil above the old grate.
        red.rooted_ring(
            centre,
            0.89,
            0.76,
            0.31,
            ground + 0.003,
            ground + 0.018,
            f"unit{index}_root_clear_baseplate",
        )
        soil.rooted_ring(
            centre,
            0.888,
            0.758,
            0.312,
            ground + 0.018,
            ground + 0.39,
            f"unit{index}_soil_annulus",
        )
        # Narrow seat on the side opposite the existing slatted bench group.
        # Front and end risers carry the closed seat plate; no floating cap or legs.
        red.box(p(0, 1.045, 0.4175), 1.90, 0.45, 0.045, f"unit{index}_seat_plate")
        red.box(
            p(0, 1.2425, 0.1975), 1.90, 0.055, 0.395, f"unit{index}_seat_front_riser"
        )
        for side in [-1, 1]:
            red.box(
                p(side * 0.92, 1.045, 0.1975),
                0.06,
                0.34,
                0.395,
                f"unit{index}_seat_end_riser_{side}",
            )
        units.append(
            {
                "index": index,
                "centre": list(centre),
                "along": list(ALONG),
                "across": list(ACROSS),
                "bodyBaseZ": ground,
                "nativePavingHeightRangeM": [
                    min(row["supportZ"] for row in unit_contacts),
                    max(row["supportZ"] for row in unit_contacts),
                ],
                "rootWellRadiusM": 0.312,
                "planterOuterDimensionsM": [1.90, 1.64, 0.51],
                "seatTopZ": ground + 0.44,
                "seatWidthM": 0.45,
                "soilTopZ": ground + 0.39,
                "sourceRegistration": "Existing exact native trunk centre; no tree relocated",
                "clearCorridor": {
                    "centre": list(centre + ACROSS * 2.25),
                    "direction": list(ALONG),
                    "widthM": 1.8,
                    "lengthM": 6.0,
                },
            }
        )
        supports.extend(dict(unit=index, **row) for row in unit_contacts)
    added = [red.finish(), soil.finish()]
    update_scene()
    preserve(before)
    assert set(bpy.data.objects.keys()) - set(before["objects"]) == set(NAMES)
    assert set(bpy.data.materials.keys()) == set(before["materials"])
    fingerprints = {o.name: object_fingerprint(o) for o in added}
    bindings = {o.name: [m.name for m in o.data.materials] for o in added}
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(added), fake_user=True, compress=True)
    component_sha = sha(component)
    source = json.loads((OUT / "source-review.json").read_text())
    for row in source["sources"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    audit = {
        "version": 262,
        "status": "component-authored-pending-independent-geometry-test",
        "baseline": str(BASE.relative_to(ROOT)),
        "baselineSha256": BASE_SHA,
        "componentPath": str(component.relative_to(ROOT)),
        "componentSha256": component_sha,
        "targetCollection": OWNER,
        "destinationCollection": OWNER,
        "addedObjects": NAMES,
        "archivedObjects": [],
        "changedObjects": [],
        "addedFingerprints": fingerprints,
        "replacementMaterialBindings": bindings,
        "objectOwners": {name: OWNER for name in NAMES},
        "retainNewMaterials": [],
        "units": units,
        "supportContacts": supports,
        "sourceManifest": "result/blender/sheffield262/source-review.json",
        "supportSurfaceObjects": PAVING,
        "sourceHashes": {row["path"]: row["sha256"] for row in source["sources"]},
        "geometryBudget": {
            "objects": 2,
            "materialSlots": 2,
            "newMaterials": 0,
            "vertices": sum(len(o.data.vertices) for o in added),
            "faces": sum(len(o.data.polygons) for o in added),
        },
        "construction": {
            "redClosedSolids": len(red.solids),
            "soilClosedSolids": len(soil.solids),
            "rootWellOpenings": 2,
            "retainedTrees": 2,
            "addedTrees": 0,
            "addedLights": 0,
        },
        "verification": {
            "originalObjectsPreserved": 8735,
            "originalMaterialsPreserved": 2350,
            "independentRoomsPreserved": 35,
            "originalFingerprintsVisibilityOwnersPropertiesModifiersUnchanged": True,
            "baselineUnchanged": True,
            "noFullNativeSaved": True,
        },
        "scope": "Recover two existing-photo-supported Sheffield red planter/seat units around two retained native trees. Keep original paving, flat grates, benches, trees, buildings and rooms.",
        "limitations": [
            "2017/2019upload-path photographs and2021site photographs are archival references, not an October2026survey.",
            "Planter and seat proportions, root-well sizes, hidden bearing feet and finish attribution are bounded presentation estimates. No exact current furniture inventory claimed.",
            "Reuse existing SAW_NEXT_D2_steel_red and soil materials without edits. No new material, photo texture, tree, light or speculative future scheme.",
        ],
    }
    write(OUT / "audit.json", audit)
    bpy.ops.wm.open_mainfile(filepath=str(component))
    assert all(
        object_fingerprint(bpy.data.objects[n]) == v for n, v in fingerprints.items()
    )
    assert sha(BASE) == BASE_SHA and sha(component) == component_sha
    write(
        OUT / "component-reopen.json",
        {
            "status": "passed",
            "componentSha256": component_sha,
            "objectsVerified": 2,
            "bindingsPreserved": True,
            "baselineUnchanged": True,
        },
    )
    print("SHEFFIELD262_COMPONENT", component_sha, flush=True)


if __name__ == "__main__":
    build()
