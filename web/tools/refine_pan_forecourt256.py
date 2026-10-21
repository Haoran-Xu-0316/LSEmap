"""Replace PAN's inherited generic furniture by historical stone planter seating.

Three grouped meshes reuse all120original leaf triangles through rigid movement.
Ground and doorway dimensions are inherited; placement and stone colour are
photo-guided estimates, not a2026survey. No street surface or facade is edited.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "result/blender/LSE_campus_detailed_v255.blend"
SHA = "bcb85b059475971cc0e684597d2cc8e5081d47302e669e17d48a923ea44fb3ad"
OUT = ROOT / "result/blender/forecourt256"
COLLECTION = "PAN_EXTERIOR"
PREFIX = "PAN_FORECOURT256_"
STONE = PREFIX + "estimated_grey_stone"
ARCHIVES = [
    "PAN_D3_forecourt_planter_boxes",
    "PAN_D3_forecourt_planter_soil",
    "PAN_D3_forecourt_plant_leaves",
    "PAN_D3_bench_seat",
    "PAN_D3_bench_supports",
    "PAN_D3_cycle_stands",
]
FRAME = json.loads(
    (ROOT / "result/blender/stage88/tower-entry-audit.json").read_text()
)["frame"]
ORIGIN, RIGHT, OUTSIDE = [Vector(FRAME[k]) for k in ["origin", "right", "outward"]]
sys.path.insert(0, str(ROOT / "web/tools"))
sys.dont_write_bytecode = True
import itertools

from integrate_exterior_round194 import (
    object_fingerprint,
    set_layer_hidden,
    update_scene,
)
from refine_col_finish252 import sha


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2) + "\n")


def capture():
    spec = importlib.util.spec_from_file_location(
        "forecourt256_protection", ROOT / "web/tests/verify_campus241.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.BASE_SHA = SHA
    return helper.capture_source()


def local(point):
    delta = point - ORIGIN
    return delta.dot(RIGHT), delta.dot(OUTSIDE), point.z


def world(x, d, z):
    return ORIGIN + RIGHT * x + OUTSIDE * d + Vector((0, 0, z))


def bounds(points):
    return [
        [min(p[a] for p in points) for a in range(3)],
        [max(p[a] for p in points) for a in range(3)],
    ]


def ground_trees():
    inspection = json.loads((OUT / "inspection.json").read_text())
    return [
        (
            name,
            BVHTree.FromPolygons(
                [obj.matrix_world @ v.co for v in obj.data.vertices],
                [list(f.vertices) for f in obj.data.polygons],
            ),
        )
        for name in inspection["supportObjects"]
        for obj in [bpy.data.objects[name]]
    ]


def support_at(x, d, trees):
    hits = []
    for name, tree in trees:
        hit = tree.ray_cast(world(x, d, 2), Vector((0, 0, -1)), 4)
        if hit[0] is not None:
            hits.append((float(hit[0].z), name))
    assert hits, (x, d, "No inherited ground support")
    return max(hits)


class MeshBuilder:
    def __init__(self):
        self.vertices = []
        self.faces = []
        self.indices = {}
        self.uv = []

    def face(self, points, uv=None):
        face = []
        for point in points:
            key = tuple(round(float(v), 7) for v in point)
            if key not in self.indices:
                self.indices[key] = len(self.vertices)
                self.vertices.append(tuple(point))
            face.append(self.indices[key])
        assert len(set(face)) == len(face)
        self.faces.append(face)
        self.uv.append(uv)

    def finish(self, name, material, uv_name="SurfaceUV"):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.materials.append(material)
        mesh.update()
        if uv_name is not None:
            layer = mesh.uv_layers.new(name=uv_name)
            for face, coords in zip(mesh.polygons, self.uv):
                if coords is None:
                    coords = [
                        (self.vertices[k][0], self.vertices[k][1])
                        for k in face.vertices
                    ]
                for index, coord in zip(face.loop_indices, coords):
                    layer.data[index].uv = coord
        obj = bpy.data.objects.new(name, mesh)
        bpy.data.collections[COLLECTION].objects.link(obj)
        obj["destinationCollection"] = COLLECTION
        obj["scope"] = (
            "Historical source-guided furniture; dimensions and fitted positions estimated"
        )
        return obj


def field_mesh(builder, unit, base):
    """Closed continuous stepped solid with an actual soil cavity, no box overlap."""
    x, d = unit["centre"]
    width, depth = unit["size"]
    outer = [x - width / 2, x + width / 2, d - depth / 2, d + depth / 2]
    inner = [outer[0] + 0.085, outer[1] - 0.085, outer[2] + 0.085, outer[3] - 0.085]
    rectangles = [(outer, 0.65)]
    for key in ["seat", "returnSeat"]:
        if key in unit:
            rectangles.append((unit[key], 0.42))
    xs = sorted({inner[0], inner[1], *[v for r, _ in rectangles for v in r[:2]]})
    ds = sorted({inner[2], inner[3], *[v for r, _ in rectangles for v in r[2:]]})
    heights = {}
    for i, (a, b) in enumerate(itertools.pairwise(xs)):
        for j, (c, e) in enumerate(itertools.pairwise(ds)):
            px, pd = (a + b) / 2, (c + e) / 2
            h = max(
                [
                    height
                    for rect, height in rectangles
                    if rect[0] < px < rect[1] and rect[2] < pd < rect[3]
                ],
                default=0,
            )
            if inner[0] < px < inner[1] and inner[2] < pd < inner[3]:
                h = 0.08
            if h:
                heights[i, j] = h
    for (i, j), height in heights.items():
        a, b = xs[i : i + 2]
        c, e = ds[j : j + 2]
        corners = [(a, c), (b, c), (b, e), (a, e)]
        builder.face([world(px, pd, base + height) for px, pd in corners])
        builder.face([world(px, pd, base) for px, pd in reversed(corners)])
        neighbours = [(i, j - 1), (i + 1, j), (i, j + 1), (i - 1, j)]
        for side, neighbour in enumerate(neighbours):
            lower = heights.get(neighbour, 0)
            if lower >= height:
                continue
            p, q = corners[side], corners[(side + 1) % 4]
            levels = sorted(
                {
                    lower,
                    height,
                    *[z for z in [0.08, 0.42, 0.65] if lower < z < height],
                }
            )
            for low, high in itertools.pairwise(levels):
                builder.face(
                    [
                        world(*p, base + low),
                        world(*q, base + low),
                        world(*q, base + high),
                        world(*p, base + high),
                    ]
                )
    return {
        "id": unit["id"],
        "outer": outer,
        "inner": inner,
        "base": base,
        "rectangles": [r for r, _ in rectangles],
        "seatHeight": 0.42,
        "planterHeight": 0.65,
        "soilBase": base + 0.08,
        "soilTop": base + 0.61,
    }


def box_mesh(builder, rect, low, high):
    a, b, c, d = rect
    rings = [[(a, c, z), (b, c, z), (b, d, z), (a, d, z)] for z in [low, high]]
    builder.face([world(*p) for p in reversed(rings[0])])
    builder.face([world(*p) for p in rings[1]])
    for i in range(4):
        j = (i + 1) % 4
        builder.face(
            [
                world(*rings[0][i]),
                world(*rings[0][j]),
                world(*rings[1][j]),
                world(*rings[1][i]),
            ]
        )


def leaf_groups(obj):
    groups = {}
    for face in obj.data.polygons:
        points = [obj.matrix_world @ obj.data.vertices[k].co for k in face.vertices]
        root = min(points, key=lambda p: p.z)
        key = tuple(round(float(v), 5) for v in root)
        if key not in groups:
            groups[key] = {"root": root, "faces": []}
        uv = obj.data.uv_layers.active
        groups[key]["faces"].append(
            (points, [tuple(uv.data[k].uv) for k in face.loop_indices] if uv else None)
        )
    result = sorted(groups.values(), key=lambda row: local(row["root"]))
    assert len(result) == 24 and all(len(g["faces"]) == 5 for g in result)
    return result


def protection(before, after):
    for name, row in before["objects"].items():
        expected = dict(row)
        if name in ARCHIVES:
            expected["hidden"] = True
        assert after["objects"][name] == expected, name
    assert all(
        after["materials"][name] == graph for name, graph in before["materials"].items()
    )
    assert (
        before["rooms"] == after["rooms"]
        and before["campusRooms"] == after["campusRooms"]
    )
    assert len(before["rooms"]) == 35


def main():
    assert sha(BASE) == SHA
    assert not (OUT / "component.blend").exists(), "Review candidate before replacement"
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    update_scene()
    before = capture()
    write("protected-source-state.json", before)
    plan = json.loads((OUT / "placement-plan.json").read_text())
    # Passage proof begins in the forecourt outside the original door envelope;
    # it must not claim traversal through the retained closed/rotating leaves.
    ring = bpy.data.objects["PAN_D5_entry88_revolving_door_rings"]
    actual_front = max(
        local(ring.matrix_world @ vertex.co)[1] for vertex in ring.data.vertices
    )
    for route in plan["routes"]:
        if route["door"].startswith("revolving"):
            minimum_depth = actual_front + route["width"] / 2 + 0.12
            route["points"][0][1] = math.ceil(minimum_depth * 10) / 10
            route["externalStartBasis"] = {
                "retainedDoorMaximumOutwardDepth": actual_front,
                "bodyHalfWidth": route["width"] / 2,
                "requiredExtraMargin": 0.12,
                "roundedExternalStartDepth": route["points"][0][1],
                "scope": "Door-exterior forecourt only; original closed door and threshold traversal unproved",
            }
    trees = ground_trees()
    stone = bpy.data.materials.new(STONE)
    stone.use_nodes = True
    stone.diffuse_color = (0.42, 0.44, 0.43, 1)
    node = stone.node_tree.nodes["Principled BSDF"]
    node.inputs["Base Color"].default_value = stone.diffuse_color
    node.inputs["Metallic"].default_value = 0
    node.inputs["Roughness"].default_value = 0.85
    stone["referenceScope"] = (
        "Photo-guided grey stone, uncalibrated estimate; shared silver material unchanged"
    )
    body, soil, leaves = MeshBuilder(), MeshBuilder(), MeshBuilder()
    units = []
    support = []
    for unit in plan["units"]:
        x, d = unit["centre"]
        base, name = support_at(x, d, trees)
        base = round(base, 5)
        row = field_mesh(body, unit, base)
        # Verify the actual native support over every footprint grid vertex.
        for rect in row["rectangles"]:
            for u in [0, 0.25, 0.5, 0.75, 1]:
                for v in [0, 0.25, 0.5, 0.75, 1]:
                    px = rect[0] + (rect[1] - rect[0]) * u
                    pd = rect[2] + (rect[3] - rect[2]) * v
                    ground, owner = support_at(px, pd, trees)
                    assert abs(ground - base) < 0.0001, (
                        unit["id"],
                        px,
                        pd,
                        ground,
                        base,
                        owner,
                    )
                    support.append(
                        {
                            "unit": unit["id"],
                            "localXY": [px, pd],
                            "z": ground,
                            "object": owner,
                        }
                    )
        box_mesh(soil, row["inner"], row["soilBase"], row["soilTop"])
        units.append(row)
    moves = []
    leaf_source = bpy.data.objects["PAN_D3_forecourt_plant_leaves"]
    source_uv = leaf_source.data.uv_layers.active
    # An untextured source mesh has no UV state to preserve. Do not invent a
    # generated projection for the replacement just because new stone uses UVs.
    assert source_uv is not None or len(leaf_source.data.uv_layers) == 0
    groups = leaf_groups(leaf_source)
    for number, group in enumerate(groups):
        unit = units[number // 8]
        col, row = number % 2, (number % 8) // 2
        a, b, c, d = unit["inner"]
        px = a + (b - a) * (0.3 if col == 0 else 0.7)
        pd = c + (d - c) * (row + 0.5) / 4
        target = world(px, pd, unit["soilTop"] + 0.002)
        delta = target - group["root"]
        for points, uv in group["faces"]:
            leaves.face([p + delta for p in points], uv)
        moves.append(
            {
                "sourceRoot": list(group["root"]),
                "targetRoot": list(target),
                "delta": list(delta),
                "unit": unit["id"],
                "faceCount": len(group["faces"]),
            }
        )
    owned = [
        body.finish(PREFIX + "stone_planter_seating", stone),
        soil.finish(PREFIX + "retained_soil", bpy.data.materials["PAN_D3_dark"]),
        leaves.finish(
            PREFIX + "rigidly_relocated_leaves",
            bpy.data.materials["PAN_D3_green"],
            uv_name=source_uv.name if source_uv else None,
        ),
    ]
    assert len(owned[2].data.polygons) == 120
    for name in ARCHIVES:
        obj = bpy.data.objects[name]
        assert not obj.hide_render
        obj.hide_render = True
        set_layer_hidden(obj, True)
    update_scene()
    after = capture()
    protection(before, after)
    component = OUT / "component.blend"
    bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
    sources = json.loads((OUT / "sources.json").read_text())
    write(
        "audit.json",
        {
            "version": 256,
            "building": "PAN",
            "baseline": str(BASE.relative_to(ROOT)),
            "baselineSha256": SHA,
            "componentPath": str(component.relative_to(ROOT)),
            "componentSha256": sha(component),
            "targetCollection": COLLECTION,
            "destinationCollection": COLLECTION,
            "addedObjects": [o.name for o in owned],
            "archivedObjects": ARCHIVES,
            "changedObjects": [],
            "addedFingerprints": {o.name: object_fingerprint(o) for o in owned},
            "replacementMaterialBindings": {
                o.name: [m.name for m in o.data.materials] for o in owned
            },
            "newMaterials": [STONE],
            "newMaterialGraphs": {STONE: after["materials"][STONE]},
            "sources": sources["sources"],
            "registration": plan,
            "units": units,
            "supportProbes": support,
            "leafRigidMoves": moves,
            "leafSource": ARCHIVES[2],
            "leafUVState": {
                "sourceActive": source_uv.name if source_uv else None,
                "replacementLayers": [layer.name for layer in owned[2].data.uv_layers],
            },
            "triangleCounts": {
                o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in owned
            },
            "cycleCorrection": {
                "sourceObject": "PAN_D3_cycle_stands",
                "oldBBox": [
                    [0.769997388, 2.670298189, 0.1],
                    [3.530000031, 3.329697251, 0.878531694],
                ],
                "yellowRevealNativeX": 11.63,
                "referenceEvidence": "Official tour places bicycle row beyond yellow-wall corner; PLB completed-project night view corroborates opposite side to automatic door. Exact replacement coordinates unregistered.",
                "newCycleGeometry": False,
            },
            "limitations": [
                "Historical photo-guided furniture study, not proof of2026current layout.",
                "Three relative placements, sizes, heights, wall thickness and stone colour are estimates; no calibrated pavement homography or survey is claimed.",
                "Shared metal.8 silver is retained unchanged; its dark blue web appearance was reflection, not evidence of blue paint.",
                "Existing pavement.024and flat map datum-.05are inherited model supports, not surveyed street grade.",
                "No new cycle positions are invented; old wrong-side stand proxies archived.",
                "Three retained doorway routes require independent continuous-volume checks; no accessibility certification.",
            ],
            "status": "saved_awaiting_independent_reopen_and_production_review",
        },
    )
    assert sha(BASE) == SHA
    print("PAN_FORECOURT256_COMPONENT_SAVED", sha(component), flush=True)


if __name__ == "__main__":
    main()
