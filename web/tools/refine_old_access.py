"""Connect OLD's photographed four exterior and four foyer steps.

Run in Blender Text Editor. Riser counts are observed; dimensions are modelling
estimates. The existing paved street and GF surfaces anchor a continuous route.
Only the lower portal and access geometry change; originals remain archived.
"""

from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old_access_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v140.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
PREFIX = "OLD_NEXT_ACCESS_"
COMPONENT = OUT / "old-access-component.blend"
prior = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else None
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and not mesh.users:
                bpy.data.meshes.remove(mesh)
    if prior:
        for name in prior["archivedObjects"]:
            obj = bpy.data.objects[name]
            state = prior["originalVisibility"][name]
            obj.hide_render, obj.hide_viewport = state[:2]
            obj.hide_set(state[2])
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


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


open_base()
originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
visibility = {
    obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()]
    for obj in bpy.data.objects
}
collection = bpy.data.collections["OLD_EXTERIOR"]
registration = json.loads(
    (ROOT / "result/blender/old_houghton_next/audit.json").read_text()
)["registration"]
origin, u, normal = [Vector(registration[k]) for k in ["origin", "right", "outward"]]
angle = math.atan2(u.y, u.x)


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(normal), p.z))


def world(x, depth, z):
    return origin + u * x + normal * depth + Vector((0, 0, z))


glass_source = bpy.data.objects["OLD_V112_entry_V97_D5_entry65_glass"]
points = [local(glass_source.matrix_world @ v.co) for v in glass_source.data.vertices]
left, right = min(p.x for p in points) - 0.085, max(p.x for p in points) + 0.085
centre = (left + right) / 2
# Street surface .050 is measured from the native paving, not surveyed AOD.
# Four estimated160mm exterior rises leave four138.75mm inner rises to native GF.
street, gf = 0.050, 1.245
outer_rise, outer_run = 0.160, 0.450
threshold = street + 4 * outer_rise
inner_rise, inner_run = (gf - threshold) / 4, 0.280
inner_begin = -3.20
owned, archived, changes, cuts = [], [], [], []


def copy_source(name, label):
    source = bpy.data.objects[name]
    assert not source.hide_render, name
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = PREFIX + label
    obj.data.name = obj.name
    collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_viewport = False
    obj.hide_set(False)
    owned.append(obj)
    archived.append(name)
    changes.append({"source": name, "owned": obj.name, "action": label})
    return obj


def connected_parts(mesh):
    seen = set()
    for start in mesh.verts:
        if start in seen:
            continue
        todo = [start]
        seen.add(start)
        group = []
        while todo:
            vertex = todo.pop()
            group.append(vertex)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other not in seen:
                    seen.add(other)
                    todo.append(other)
        yield group


# Cut actual stone/joint surfaces down to the new threshold, rather than hiding
# an obstructing plinth under transparent panes. Every upper face stays intact.
wall_sources = [
    o.name
    for o in collection.all_objects
    if not o.hide_render and o.name.startswith("OLD_V112_entry_V52_Houghton_ashlar_")
]
wall_sources.append("OLD_V112_entry_Ashlar_course_shadow_lines")
for name in wall_sources:
    source = bpy.data.objects[name]
    obj = copy_source(name, "opening_" + name.removeprefix("OLD_V112_entry_"))
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    inverse = obj.matrix_world.inverted()
    for position, direction in [
        (world(left, 0, 0), u),
        (world(right, 0, 0), u),
        (world(0, 0, threshold), Vector((0, 0, 1))),
        (world(0, 0, 1.246), Vector((0, 0, 1))),
    ]:
        bmesh.ops.bisect_plane(
            mesh,
            geom=list(mesh.verts) + list(mesh.edges) + list(mesh.faces),
            plane_co=inverse @ position,
            plane_no=obj.matrix_world.to_3x3().transposed() @ direction,
            dist=1e-6,
        )
    remove = []
    for face in mesh.faces:
        p = local(obj.matrix_world @ face.calc_center_median())
        if (
            left + 1e-5 < p.x < right - 1e-5
            and threshold - 1e-5 < p.z < 1.246 + 1e-5
            and p.y > -3.1
        ):
            remove.append(face)
    bmesh.ops.delete(mesh, geom=remove, context="FACES")
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    cuts.append({"source": name, "removedFaces": len(remove)})

# Shared meshes contain door members, pulls and old railings. Rebuild the
# approach railings separately and move only the door's lower members.
for family in ["glass", "frame", "steel"]:
    name = (
        glass_source.name
        if family == "glass"
        else "OLD_V112_entry_D5_entry65_" + family
    )
    obj = copy_source(name, "door_" + family)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    inverse = obj.matrix_world.inverted()
    removed = 0
    moved = 0
    for part in list(connected_parts(mesh)):
        positions = [local(obj.matrix_world @ v.co) for v in part]
        bounds = [
            [min(p[i] for p in positions), max(p[i] for p in positions)]
            for i in range(3)
        ]
        xspan = bounds[0][1] - bounds[0][0]
        zspan = bounds[2][1] - bounds[2][0]
        old_rail = family == "steel" and bounds[2][1] < 2.1
        old_rail |= (
            family == "frame"
            and xspan < 0.18
            and bounds[1][1] > -2.57
            and bounds[2][1] < 2.1
        )
        old_paving = (
            family == "frame" and zspan < 0.005 and abs(bounds[2][0] - 1.237) < 0.015
        )
        if old_rail or old_paving:
            bmesh.ops.delete(mesh, geom=part, context="VERTS")
            removed += 1
            continue
        if family == "glass" and bounds[2][0] < 1.3:
            for vertex in part:
                p = obj.matrix_world @ vertex.co
                if p.z < 1.30:
                    p.z += threshold - 1.245
                    vertex.co = inverse @ p
                    moved += 1
        elif family == "frame":
            bottom = xspan > 4 and bounds[2][1] < 1.3
            jamb = bounds[2][0] < 1.3 and bounds[2][1] > 3.5 and xspan < 0.15
            for vertex in part:
                p = obj.matrix_world @ vertex.co
                if bottom or (jamb and p.z < 1.3):
                    p.z += threshold - 1.245
                    vertex.co = inverse @ p
                    moved += 1
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    cuts.append(
        {
            "source": name,
            "removedRailOrPavingParts": removed,
            "loweredDoorVertices": moved,
        }
    )

materials.clear()
for key, source in [
    ("stone", "OLD_V116_entrance_limestone"),
    ("steel", "OLD_V65_steel"),
    ("frame", "OLD_V65_frame"),
]:
    material = bpy.data.materials[source].copy()
    material.name = PREFIX + key
    materials[key] = material
batches = {}


def batch(label, key):
    token = (label, key)
    if token not in batches:
        batches[token] = Geometry("OLD", label, key)
        batches[token].name = PREFIX + label
    return batches[token]


def box(label, key, x, depth, z, width, thickness, height):
    batch(label, key).box(world(x, depth, z), (width, thickness, height), angle)


def tube(label, key, a, b, radius=0.024):
    start, end = world(*a), world(*b)
    axis = (end - start).normalized()
    cross = axis.cross(Vector((0, 0, 1)))
    if cross.length < 0.01:
        cross = u.copy()
    cross.normalize()
    other = axis.cross(cross).normalized()
    vertices = [
        p
        + radius
        * (cross * math.cos(i * math.tau / 12) + other * math.sin(i * math.tau / 12))
        for p in [start, end]
        for i in range(12)
    ]
    faces = [(i, (i + 1) % 12, (i + 1) % 12 + 12, i + 12) for i in range(12)] + [
        tuple(reversed(range(12))),
        tuple(range(12, 24)),
    ]
    batch(label, key).add(vertices, faces)


for index in range(4):
    front = 3.05 - index * outer_run
    back = front - outer_run
    half = 4.40 - 0.12 * index
    chamfer = 0.18
    outline = [
        (-half, back),
        (half, back),
        (half, front - chamfer),
        (half - chamfer, front),
        (-half + chamfer, front),
        (-half, front - chamfer),
    ]
    top = street + (index + 1) * outer_rise
    vertices = [world(centre + x, d, z) for z in [street, top] for x, d in outline]
    faces = [tuple(reversed(range(6))), tuple(range(6, 12))] + [
        (i, (i + 1) % 6, (i + 1) % 6 + 6, i + 6) for i in range(6)
    ]
    batch("external_four_steps", "stone").add(vertices, faces)
landing_front = 3.05 - 4 * outer_run
box(
    "threshold_landing",
    "stone",
    centre,
    (landing_front + inner_begin) / 2,
    threshold / 2,
    8.08,
    landing_front - inner_begin,
    threshold,
)
for index in range(4):
    near = inner_begin - index * inner_run
    far = near - inner_run
    top = threshold + (index + 1) * inner_rise
    box(
        "foyer_four_steps",
        "stone",
        centre,
        (near + far) / 2,
        top / 2,
        4.90,
        inner_run,
        top,
    )
inner_end = inner_begin - 4 * inner_run
box("foyer_gf_landing", "stone", centre, inner_end - 0.25, gf / 2, 4.90, 0.50, gf)
# Rail geometry is attached to tread surfaces. Interior rail ends extend on the
# two local landings; exterior rails stop at the flight, matching the access guide.
for sign in [-1, 1]:
    x = centre + sign * 2.95
    for depth, base in [(2.82, street + outer_rise), (1.43, threshold)]:
        box("rail_posts", "frame", x, depth, base + 0.45, 0.06, 0.06, 0.90)
        box("rail_feet", "steel", x, depth, base + 0.012, 0.12, 0.12, 0.024)
    tube(
        "exterior_handrails",
        "steel",
        (x, 2.82, street + outer_rise + 0.90),
        (x, 1.43, threshold + 0.90),
    )
    x = centre + sign * 2.20
    for depth, base in [(inner_begin + 0.12, threshold), (inner_end - 0.12, gf)]:
        box("rail_posts", "frame", x, depth, base + 0.45, 0.06, 0.06, 0.90)
        box("rail_feet", "steel", x, depth, base + 0.012, 0.12, 0.12, 0.024)
    tube(
        "interior_handrails",
        "steel",
        (x, inner_begin, threshold + 0.90),
        (x, inner_end, gf + 0.90),
    )
    tube(
        "interior_handrails",
        "steel",
        (x, inner_begin + 0.18, threshold + 0.90),
        (x, inner_begin, threshold + 0.90),
    )
    tube(
        "interior_handrails",
        "steel",
        (x, inner_end, gf + 0.90),
        (x, inner_end - 0.18, gf + 0.90),
    )
for geometry in batches.values():
    obj = geometry.finish()
    owned.append(obj)
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
# Replace obstructing old shadow slab with real foyer steps and an open portal.
replacements = {
    "OLD_V116_chamfered_fan_stair": PREFIX + "external_four_steps",
    "OLD_V116_retained_entrance_landing": PREFIX + "threshold_landing",
    "OLD_V112_entry_Door_inner_shadow": PREFIX + "foyer_four_steps",
}
for source, name in replacements.items():
    archived.append(source)
    changes.append(
        {
            "source": source,
            "owned": name,
            "action": "Replace obsolete access surface with connected two-flight geometry",
        }
    )
used = {change["owned"] for change in changes}
for obj in owned:
    if obj.name not in used:
        changes.append(
            {
                "source": None,
                "owned": obj.name,
                "action": "Add photographed connected foyer or handrail surface",
            }
        )
for name in archived:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()


def tree_for(objects):
    vertices = []
    faces = []
    names = []
    for obj in objects:
        start = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(start + i for i in f.vertices) for f in obj.data.polygons)
        names.extend([obj.name] * len(obj.data.polygons))
    return BVHTree.FromPolygons(vertices, faces), names


def probes():
    visible = [
        o for o in collection.all_objects if o.type == "MESH" and not o.hide_render
    ]
    tree, names = tree_for(visible)
    rows = []

    def probe(kind, x, d, z, direction, expected_z=None, expected_name=None):
        hit = tree.ray_cast(world(x, d, z), Vector(direction), 20)
        obj = names[hit[2]] if hit[2] is not None else None
        value = hit[0].z if hit[0] is not None else None
        if expected_z is not None:
            assert value is not None and abs(value - expected_z) < 1e-4, (
                kind,
                x,
                d,
                obj,
                value,
                expected_z,
            )
        if expected_name is not None:
            assert obj == expected_name, (kind, obj, expected_name)
        rows.append({"kind": kind, "x": x, "depth": d, "firstObject": obj, "z": value})

    for index in range(4):
        for dx in [-1.4, 0, 1.4]:
            probe(
                "externalTread",
                centre + dx,
                3.05 - (index + 0.5) * outer_run,
                3,
                (0, 0, -1),
                street + (index + 1) * outer_rise,
                PREFIX + "external_four_steps",
            )
            probe(
                "foyerTread",
                centre + dx,
                inner_begin - (index + 0.5) * inner_run,
                3,
                (0, 0, -1),
                threshold + (index + 1) * inner_rise,
                PREFIX + "foyer_four_steps",
            )
    for d in [1.10, 0.5, -0.2, -1, -2.5, -3.12]:
        probe(
            "continuousThreshold",
            centre,
            d,
            3,
            (0, 0, -1),
            threshold,
            PREFIX + "threshold_landing",
        )
    for dx in [-1.6, -0.5, 0.5, 1.6]:
        probe(
            "lowerDoorClearance",
            centre + dx,
            8,
            0.78,
            -normal,
            None,
            PREFIX + "door_glass",
        )
    return rows


results = probes()
assert all(
    fingerprint(bpy.data.objects[name]) == value for name, value in originals.items()
)
assert all(
    [
        bpy.data.objects[name].hide_render,
        bpy.data.objects[name].hide_viewport,
        bpy.data.objects[name].hide_get(),
    ]
    == state
    for name, state in visibility.items()
    if name not in archived
)
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
audit = {
    "baselineSha256": BASE_SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": [o.name for o in owned],
    "archivedObjects": archived,
    "changes": changes,
    "cuts": cuts,
    "registration": {
        "centreX": centre,
        "doorEdges": [left, right],
        "nativePavedStreetZ": street,
        "nativeGFZ": gf,
        "thresholdZ": threshold,
        "externalSteps": 4,
        "externalRiserEstimate": outer_rise,
        "externalTreadEstimate": outer_run,
        "internalSteps": 4,
        "internalRiserEstimate": inner_rise,
        "internalTreadEstimate": inner_run,
        "method": "Anchor to native paved street and GF; separate photographed four-plus-four flights. Riser/tread and plan widths are estimates, not measured AOD or compliance claims.",
        "absoluteDimensionsEstimated": True,
    },
    "references": [
        "https://www.accessable.co.uk/london-school-of-economics/access-guides/old-building",
        "https://webbyates.com/projects/the-old-building/",
    ],
    "sourceEvidenceFiles": [
        "result/blender/old_access_next/section-evidence.json",
        "result/blender/old_houghton_next/access-guide-evidence.json",
    ],
    "surfaceChecks": results,
    "limitations": [
        "Only the visible lower approach and foyer flight are reconstructed; no complete internal layout.",
        "Long raised side route, accessibility lift and unseen details remain unresolved.",
        "Street/GF heights are native model registration; not a site survey.",
        "Artwork, main arch, upper windows and roof retained.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = audit["ownedObjects"]
for obj in dst.objects:
    collection = bpy.data.collections["OLD_EXTERIOR"]
    collection.objects.link(obj)
    obj.hide_render = False
    obj.hide_set(False)
for name in archived:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
collection = bpy.data.collections["OLD_EXTERIOR"]
reloaded = probes()
assert reloaded == results
assert all(
    fingerprint(bpy.data.objects[name]) == value for name, value in originals.items()
)
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for obj in scene.objects:
    if obj.type == "MESH" and obj.name not in members:
        obj.hide_render = True
focus = world(centre, -1, 3.5)
camera = bpy.data.cameras.new(PREFIX + "review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = world(centre + 2, 19, 7)
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 11.7
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-old-access.png")
bpy.ops.render.render(write_still=True)
proof = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "originalObjectCount": len(originals),
    "reloadedProbes": reloaded,
    "nativeRender": "reloaded-old-access.png",
    "externalSteps": 4,
    "internalSteps": 4,
    "thresholdContinuous": True,
    "oldWallBelowDoorRemoved": True,
}
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print(
    "OLD_ACCESS_REOPENED_VERIFIED",
    len(originals),
    len(owned),
    len(reloaded),
    flush=True,
)
bpy.ops.wm.quit_blender()
