"""Build the photographed OLD Student Services counter and mezzanine cutaway.

Run in Blender Text Editor. This bounded, independent room study uses the user's
photo and an official LSE hub image. Room size, stations, stairs and furniture
placements are estimates; it does not claim a complete or measured ground floor.
"""

from pathlib import Path
import array
import hashlib
import json
import math
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web/tools"))
from facade_geometry import Geometry, materials

OUT = ROOT / "result/blender/old_ssc_room_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v143.blend"
PREFIX = "OLD_NEXT_SSC_"
COMPONENT = OUT / "old-ssc-room-component.blend"
baseline_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
assert (
    baseline_sha == "7cf90954936581f8b9416018f34ce06984464d8451fe8778a65d3c025181367d"
)
bpy.ops.wm.open_mainfile(filepath=str(BASE))
main_scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
bpy.context.window.scene = main_scene


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == "MESH":
        for data, field, kind, size in [
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
            (obj.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * size)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            digest.update(values.tobytes())
    digest.update(
        str(
            [m.name if m else None for m in getattr(obj.data, "materials", [])]
        ).encode()
    )
    return digest.hexdigest()


for s in bpy.data.scenes:
    for layer in s.view_layers:
        layer.update()
original = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
assert len(original) == 5694
collection = bpy.data.collections.new("OLD_SSC_ROOM_study")
collection["roomSample"] = True
collection["roomLabel"] = "Student Services Centre接待区"
scene = bpy.data.scenes.new("REVIEW_OLD_SSC")
scene.collection.children.link(collection)
bpy.context.window.scene = scene
palette = {
    "red": (0.18, 0.008, 0.007),
    "white": (0.77, 0.77, 0.73),
    "floor": (0.17, 0.19, 0.19),
    "dark": (0.014, 0.020, 0.021),
    "counter": (0.052, 0.062, 0.063),
    "metal": (0.40, 0.44, 0.44),
    "glass": (0.29, 0.40, 0.43),
    "logo": (0.91, 0.88, 0.74),
    "leaf": (0.105, 0.22, 0.067),
    "pot": (0.56, 0.55, 0.49),
    "light": (0.92, 0.91, 0.83),
}
materials.clear()
for key, color in palette.items():
    mat = bpy.data.materials.new(PREFIX + key)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = (
        0.24 if key == "floor" else 0.43 if key == "metal" else 0.72
    )
    if key == "metal":
        shader.inputs["Metallic"].default_value = 0.6
    if key == "counter":
        shader.inputs["Metallic"].default_value = 0.12
    if key == "glass":
        shader.inputs["Roughness"].default_value = 0.20
        shader.inputs["Transmission Weight"].default_value = 0.30
        shader.inputs["Alpha"].default_value = 0.27
        mat.diffuse_color = (*color, 0.27)
        mat.surface_render_method = "DITHERED"
    if key == "light":
        shader.inputs["Emission Color"].default_value = (*color, 1)
        shader.inputs["Emission Strength"].default_value = 0.35
    materials[key] = mat
batches = {}


def group(family, material):
    key = (family, material)
    if key not in batches:
        g = Geometry("OLD", family, material)
        g.name = PREFIX + family + "_" + material
        g.collection = collection
        batches[key] = g
    return batches[key]


def box(family, material, center, size):
    group(family, material).box(center, size)


def tube(family, material, start, end, radius=0.025, sides=10):
    a, b = Vector(start), Vector(end)
    axis = (b - a).normalized()
    u = axis.cross(Vector((0, 0, 1)))
    if u.length < 0.01:
        u = axis.cross(Vector((0, 1, 0)))
    u.normalize()
    v = axis.cross(u)
    points = [
        p
        + radius
        * (u * math.cos(i * math.tau / sides) + v * math.sin(i * math.tau / sides))
        for p in [a, b]
        for i in range(sides)
    ]
    group(family, material).add(
        points,
        [tuple(reversed(range(sides))), tuple(range(sides, 2 * sides))]
        + [
            (i, (i + 1) % sides, (i + 1) % sides + sides, i + sides)
            for i in range(sides)
        ],
    )


def perforated_guard(family, start_x, end_x, y, start_z, end_z):
    """Finite open slot grid; spacing is a photo-guided rendering estimate."""
    width = abs(end_x - start_x)
    columns = max(12, round(width / 0.075))
    rows = 12
    hole_u = 0.016 / width
    hole_v = 0.016 / 0.85
    geometry = group(family, "dark")

    def strip(u0, u1, v0, v1):
        points = []
        for u, v in [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]:
            points.append(
                (
                    start_x + (end_x - start_x) * u,
                    y,
                    start_z + (end_z - start_z) * u + 0.13 + 0.85 * v,
                )
            )
        geometry.add(points, [(0, 1, 2, 3), (3, 2, 1, 0)])

    for row in range(rows + 1):
        v = row / rows
        strip(
            0,
            1,
            max(0, v - (1 / rows - hole_v) / 2),
            min(1, v + (1 / rows - hole_v) / 2),
        )
    for column in range(columns + 1):
        u = column / columns
        strip(
            max(0, u - (1 / columns - hole_u) / 2),
            min(1, u + (1 / columns - hole_u) / 2),
            0,
            1,
        )


# Cutaway omits the near wall and ceiling slab, keeping the photographed surfaces.
box("floor", "floor", (0, 0, -0.08), (11.6, 8.2, 0.16))
box("red_wall", "red", (-1.10, 4.1, 2.13), (9.4, 0.16, 4.26))
box("left_wall", "white", (-5.8, 1.9, 2.05), (0.16, 4.4, 4.10))
for y in [-3.1, -0.40, 2.3]:
    box("window_glass", "glass", (5.78, y, 2.06), (0.025, 2.38, 4.02))
    for yy in [y - 1.19, y, y + 1.19]:
        box("window_frame", "dark", (5.75, yy, 2.06), (0.09, 0.05, 4.08))
    for z in [0.07, 1.12, 2.12, 3.12, 4.07]:
        box("window_frame", "dark", (5.75, y, z), (0.09, 2.4, 0.045))
    box("window_pier", "white", (5.72, y + 1.33, 2.05), (0.24, 0.25, 4.10))
box("rear_window", "glass", (4.71, 4.05, 2.1), (2.04, 0.025, 4.0))
for x in [3.68, 4.37, 5.05, 5.74]:
    box("rear_window_frame", "dark", (x, 4.0, 2.1), (0.045, 0.09, 4.1))
for z in [0.07, 0.88, 1.69, 2.5, 3.31, 4.09]:
    box("rear_window_frame", "dark", (4.71, 4.0, z), (2.08, 0.09, 0.045))
# Long counter: five visible stations, real open work zone behind the visitor face.
box("counter_plinth", "counter", (0.50, -0.82, 0.14), (0.40, 6.18, 0.28))
box("counter_top", "dark", (0.02, -0.82, 1.10), (1.34, 6.28, 0.07))
box("staff_worktop", "dark", (-0.75, -0.82, 0.78), (1.25, 6.18, 0.06))
# Open rectangular perforations are a bounded approximation of the photo's slots.
for panel in range(5):
    center_y = -3.30 + panel * 1.24
    for row in range(9):
        z = 0.31 + row * 0.078
        box("counter_perforation", "counter", (0.63, center_y, z), (0.024, 1.18, 0.033))
    for col in range(18):
        y = center_y - 0.57 + col * 0.067
        box("counter_perforation", "counter", (0.63, y, 0.625), (0.024, 0.027, 0.66))
    for y in [center_y - 0.60, center_y + 0.60]:
        box("counter_edge", "dark", (0.64, y, 0.65), (0.045, 0.035, 0.88))
    box("monitor_back", "white", (-0.77, center_y, 1.03), (0.075, 0.49, 0.35))
    box("monitor_screen", "dark", (-0.812, center_y, 1.03), (0.012, 0.44, 0.30))
    tube(
        "monitor_support",
        "metal",
        (-0.80, center_y, 0.82),
        (-0.80, center_y, 0.95),
        0.024,
    )
    box("monitor_base", "metal", (-0.80, center_y, 0.811), (0.30, 0.24, 0.025))
    box("station_notice", "red", (0.05, center_y, 1.34), (0.035, 0.22, 0.31))
    box("chair_seat", "dark", (-1.69, center_y, 0.46), (0.48, 0.48, 0.065))
    box("chair_back", "dark", (-1.91, center_y, 0.79), (0.07, 0.47, 0.55))
    tube(
        "chair_support",
        "metal",
        (-1.69, center_y, 0.04),
        (-1.69, center_y, 0.43),
        0.035,
    )
    for a in range(5):
        angle = a * math.tau / 5
        tube(
            "chair_base",
            "dark",
            (-1.69, center_y, 0.05),
            (-1.69 + 0.29 * math.cos(angle), center_y + 0.29 * math.sin(angle), 0.04),
            0.020,
        )
# Two straight climbing flights with an intermediate landing and dark open steps.
flights = [(3.35, 1.05, 0.0, 1.10, 8), (-0.05, -3.05, 1.10, 2.35, 9)]
for start_x, end_x, low_z, high_z, count in flights:
    for i in range(count):
        x = start_x + (end_x - start_x) * (i + 0.5) / count
        z = low_z + (high_z - low_z) * (i + 1) / count
        box(
            "stair_tread",
            "dark",
            (x, 3.17, z - 0.03),
            (abs(end_x - start_x) / count, 1.33, 0.06),
        )
    for y in [2.48, 3.86]:
        tube(
            "stair_stringer",
            "dark",
            (start_x, y, low_z - 0.10),
            (end_x, y, high_z - 0.10),
            0.080,
            8,
        )
        # Dark perforated plates retain the source's narrow bright top rail.
        perforated_guard("stair_guard", start_x, end_x, y, low_z, high_z)
        tube(
            "stair_handrail",
            "metal",
            (start_x, y, low_z + 0.98),
            (end_x, y, high_z + 0.98),
            0.018,
        )
        for t in [0, 0.5, 1]:
            x = start_x + (end_x - start_x) * t
            z = low_z + (high_z - low_z) * t
            tube("stair_post", "metal", (x, y, z + 0.02), (x, y, z + 1.0), 0.015)
for left, right, z in [(-0.05, 1.05, 1.10), (-5.72, -3.05, 2.35)]:
    box(
        "stair_landing",
        "dark",
        ((left + right) / 2, 3.17, z - 0.055),
        (right - left, 1.4, 0.11),
    )
    perforated_guard("landing_guard", left, right, 2.47, z, z)
    tube(
        "landing_handrail",
        "metal",
        (left, 2.47, z + 1.0),
        (right, 2.47, z + 1.0),
        0.018,
    )
box("under_stair_door", "dark", (-4.02, 3.98, 1.00), (1.03, 0.07, 2.0))
box("door_inset", "glass", (-4.02, 3.92, 1.17), (0.84, 0.025, 1.52))
# Reuse the accepted vector brand outline, not a generic font or source photograph.
old_logo = bpy.data.objects["OLD_V100_vector_logo"]
old_sign = bpy.data.objects["OLD_V97_LSE_entry_sign"]
right = (old_sign.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
points = [old_logo.matrix_world @ v.co for v in old_logo.data.vertices]
xs = [p.dot(right) for p in points]
zs = [p.z for p in points]
normal = (old_sign.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
depths = [p.dot(normal) for p in points]
depth_span = max(depths) - min(depths)
assert depth_span > 0
height = max(zs) - min(zs)
mid_x = (max(xs) + min(xs)) / 2
mid_z = (max(zs) + min(zs)) / 2
mesh = old_logo.data.copy()
mesh.materials.clear()
mesh.materials.append(materials["logo"])
for vertex, p in zip(mesh.vertices, points):
    vertex.co = (
        1.66 + (p.dot(right) - mid_x) / height,
        3.88 - (p.dot(normal) - min(depths)) / depth_span * 0.008,
        3.29 + (p.z - mid_z) / height,
    )
mesh.update()
obj = bpy.data.objects.new(PREFIX + "vector_lse_wordmark", mesh)
collection.objects.link(obj)
owned = [obj]
# Fixed benches and two bounded plants beside the right-hand windows.
for y in [-0.6, 2.0]:
    box("bench_seat", "metal", (5.22, y, 0.46), (0.59, 1.8, 0.07))
    for yy in [y - 0.65, y + 0.65]:
        box("bench_support", "metal", (5.22, yy, 0.23), (0.46, 0.07, 0.46))
for y in [-2.48, 2.90]:
    tube("plant_pot", "pot", (5.19, y, 0.02), (5.19, y, 0.38), 0.23, 16)
    for i in range(9):
        a = i * math.tau / 9
        tip = Vector(
            (
                5.19 + 0.33 * math.cos(a),
                y + 0.33 * math.sin(a),
                1.15 + 0.3 * (i % 3) / 2,
            )
        )
        tube("plant_stem", "leaf", (5.19, y, 0.36), tip, 0.01, 6)
        for f in [0.6, 0.82]:
            base = Vector((5.19, y, 0.36)).lerp(tip, f)
            end = base + Vector((0.30 * math.cos(a), 0.30 * math.sin(a), 0.08))
            side = Vector((-0.07 * math.sin(a), 0.07 * math.cos(a), 0))
            group("plant_leaf", "leaf").add(
                [base, base.lerp(end, 0.5) + side, end, base.lerp(end, 0.5) - side],
                [(0, 1, 2, 3), (3, 2, 1, 0)],
            )
for y in [-2.65, -0.2, 2.25]:
    for x in [-3.6, -0.9, 2.5]:
        tube("downlight", "light", (x, y, 4.025), (x, y, 4.075), 0.080, 16)
for g in batches.values():
    obj = g.finish()
    obj["scope"] = (
        "Photo-informed SSC independent cutaway; all dimensions and placements estimated"
    )
    owned.append(obj)
owned_names = [o.name for o in owned]
# Original full-campus objects, UVs, slots and visibility remain unchanged.
bpy.context.window.scene = main_scene
for source_scene in bpy.data.scenes:
    for source_layer in source_scene.view_layers:
        source_layer.update()
mismatches = [n for n, h in original.items() if fingerprint(bpy.data.objects[n]) != h]
assert not mismatches, mismatches
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == state
    for n, state in visibility.items()
)
room = {
    "id": "old-ssc",
    "code": "OLD",
    "collection": collection.name,
    "label": "Student Services Centre接待区",
    "scope": "依据用户照片与LSE官方接待区照片建立的独立局部空间。红墙、接待柜台、两段金属楼梯和夹层可见；尺寸、家具及踏步数量为估计，未连接为完整楼层。",
    "gallery": "old-ssc-interior",
    "interiorStudy": {
        "kind": "room-sample",
        "label": "Student Services Centre接待区",
        "scope": "照片可见的接待与夹层局部，尺寸与配置估计，不代表整栋OLD内部。",
    },
    "interiorView": {
        "position": [11.5, 5.4, 14.5],
        "target": [0, 1.4, -1.1],
        "fov": 42,
    },
}
audit = {
    "baselineSha256": baseline_sha,
    "originalFingerprints": original,
    "originalVisibility": visibility,
    "ownedObjects": owned_names,
    "archivedObjects": [],
    "changes": [
        {"source": None, "owned": n, "action": "Add bounded photo-informed SSC cutaway"}
        for n in owned_names
    ],
    "collections": [{"name": collection.name, "ownedObjects": owned_names}],
    "room": room,
    "sources": json.loads(
        (ROOT / "data/collections/old-ssc-2026/sources.json").read_text()
    ),
    "estimates": {
        "roomWidth": 11.6,
        "roomDepth": 8.2,
        "ceilingHeight": 4.1,
        "counterHeight": 1.10,
        "counterStations": 5,
        "mezzanineLevel": 2.35,
        "stairRiserCount": 17,
        "guardPerforationSpacingEstimated": True,
        "measuredFloorPlan": False,
    },
    "limitations": [
        "All dimensions and room registration are estimated",
        "Near wall and ceiling slab intentionally omitted for cutaway",
        "No invisible offices, current opening hours or whole-floor claim",
    ],
}
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True)
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
expected = {o.name: fingerprint(o) for o in owned}
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
for source_scene in bpy.data.scenes:
    for source_layer in source_scene.view_layers:
        source_layer.update()
mismatches = [n for n, h in original.items() if fingerprint(bpy.data.objects[n]) != h]
assert not mismatches, mismatches
with bpy.data.libraries.load(str(COMPONENT), link=False) as (source, target):
    assert set(owned_names) <= set(source.objects)
    target.objects = owned_names
review_collection = bpy.data.collections.new("SSC_RELOADED")
review_scene = bpy.data.scenes.new("SSC_SAVED_REVIEW")
review_scene.collection.children.link(review_collection)
for o in target.objects:
    review_collection.objects.link(o)
assert {o.name: fingerprint(o) for o in target.objects} == expected
bpy.context.window.scene = review_scene
for layer in review_scene.view_layers:
    layer.update()
trees = [
    (
        o.name,
        BVHTree.FromPolygons(
            [o.matrix_world @ v.co for v in o.data.vertices],
            [tuple(p.vertices) for p in o.data.polygons],
        ),
    )
    for o in target.objects
    if o.type == "MESH"
]


def first(origin, direction, length=6):
    hits = []
    for name, tree in trees:
        point, normal, index, distance = tree.ray_cast(
            Vector(origin), Vector(direction), length
        )
        if point is not None:
            hits.append({"object": name, "point": list(point), "distance": distance})
    return min(hits, key=lambda h: h["distance"]) if hits else None


checks = []
for x in [2.0, 3.0, 4.0]:
    for y in [-3.6, -2.4, -1.2, 0, 1.2]:
        hit = first((x, y, 2.0), (0, 0, -1))
        assert hit and hit["object"] == PREFIX + "floor_floor", hit
        checks.append({"kind": "visitor-floor", "sample": [x, y], "hit": hit})
for start_x, end_x, low_z, high_z, count in flights:
    for i in range(count):
        x = start_x + (end_x - start_x) * (i + 0.5) / count
        z = low_z + (high_z - low_z) * (i + 1) / count
        hit = first((x, 3.17, z + 0.10), (0, 0, -1))
        assert hit and hit["object"] == PREFIX + "stair_tread_dark", hit
        checks.append({"kind": "stair-tread", "index": i, "hit": hit})
for x, z in [(0.5, 1.1), (-4.0, 2.35)]:
    hit = first((x, 3.17, z + 0.10), (0, 0, -1))
    assert hit and hit["object"] == PREFIX + "stair_landing_dark", hit
    checks.append({"kind": "stair-landing", "hit": hit})
for y in [-3.30, -2.06, -0.82, 0.42, 1.66]:
    hit = first((1.1, y, 1.12), (-1, 0, 0))
    assert hit and hit["object"] == PREFIX + "counter_top_dark", hit
    checks.append({"kind": "counter-top-edge", "hit": hit})
world = bpy.data.worlds.new("SSC_REVIEW_WORLD")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.74, 0.78, 0.81, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.65
review_scene.world = world
for point, power, size in [((2, -2, 6), 1100, 7), ((-4, 0, 5), 650, 6)]:
    data = bpy.data.lights.new("SSC_REVIEW_AREA", "AREA")
    data.energy = power
    data.shape = "DISK"
    data.size = size
    light = bpy.data.objects.new(data.name, data)
    review_scene.collection.objects.link(light)
    light.location = point
camera_data = bpy.data.cameras.new("SSC_REVIEW_CAMERA")
camera = bpy.data.objects.new(camera_data.name, camera_data)
review_scene.collection.objects.link(camera)
camera.location = (11.5, -14.5, 5.4)
camera.rotation_euler = (
    (Vector((0, 1.1, 1.4)) - camera.location).to_track_quat("-Z", "Y").to_euler()
)
camera_data.lens = 35
review_scene.camera = camera
review_scene.render.engine = "BLENDER_EEVEE"
review_scene.render.resolution_x = 1400
review_scene.render.resolution_y = 1000
review_scene.render.resolution_percentage = 100
review_scene.render.image_settings.file_format = "PNG"
review_scene.render.filepath = str(OUT / "reloaded-ssc-room.png")
bpy.ops.render.render(write_still=True)
verification = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(original),
    "ownedObjects": len(owned_names),
    "firstSurfaceChecks": checks,
    "embeddedImageTextures": 0,
    "fullModelSaved": False,
    "nativeRender": "reloaded-ssc-room.png",
    "roomDimensionsMeasured": False,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("SSC_COMPONENT_SAVED_AND_REOPENED", len(owned_names), len(checks), flush=True)
bpy.ops.wm.quit_blender()
