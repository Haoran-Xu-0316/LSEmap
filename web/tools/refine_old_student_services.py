"""Restore photographed mixed dense planting in the OLD Student Services forecourt.
Use Blender Text Editor. Plant species/counts/size are photo-guided estimates, not a survey.
"""

from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old_student_services_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v143.blend"
EXPECTED_SHA = "7cf90954936581f8b9416018f34ce06984464d8451fe8778a65d3c025181367d"
PREFIX = "OLD_NEXT_STUDENT_"
NAMES = [
    PREFIX + k
    for k in ["dense_planter_leaves", "upright_broad_leaves", "yellow_flower_heads"]
]
ARCHIVE = ["OLD_V53_Clare_leaf"]
COMPONENT = OUT / "old-student-services-component.blend"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
PREVIOUS = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else None
)


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for name in NAMES:
        obj = bpy.data.objects.get(name)
        if obj:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for name in ARCHIVE:
        o = bpy.data.objects[name]
        state = (
            PREVIOUS["originalVisibility"][name] if PREVIOUS else [False, False, False]
        )
        o.hide_render, o.hide_viewport = state[:2]
        o.hide_set(state[2])
    for layer in bpy.context.scene.view_layers:
        layer.update()


def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, w in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            a = array.array(kind, [0]) * (len(data) * w)
            data.foreach_get(field, a)
            h.update(a.tobytes())
        for uv in o.data.uv_layers:
            a = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", a)
            h.update(a.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


open_base()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
if BASE.stem.endswith("v143"):
    assert len(originals) == 5694
collection = bpy.data.collections["OLD_EXTERIOR"]
reg = json.loads((ROOT / "result/blender/old_facade_next/audit.json").read_text())[
    "registration"
]
origin, u, normal = [Vector(reg[k]) for k in ["origin", "right", "outward"]]


def world(x, d, z):
    return origin + u * x + normal * d + Vector((0, 0, z))


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(normal), p.z))


soil = bpy.data.objects["OLD_V53_Clare_soil"]
ps = [local(soil.matrix_world @ v.co) for v in soil.data.vertices]
LEFT = min(p.x for p in ps)
RIGHT = max(p.x for p in ps)
BOTTOM = max(p.z for p in ps)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

materials.clear()
source = bpy.data.objects[ARCHIVE[0]]
materials["leaf"] = source.data.materials[0].copy()
materials["leaf"].name = PREFIX + "green"
flower = bpy.data.materials.new(PREFIX + "yellow")
flower.use_nodes = True
shader = flower.node_tree.nodes["Principled BSDF"]
shader.inputs["Base Color"].default_value = (0.65, 0.38, 0.018, 1)
shader.inputs["Roughness"].default_value = 0.75
materials["flower"] = flower
batches = {}


def batch(label, key="leaf"):
    if label not in batches:
        g = Geometry("OLD", label, key)
        g.name = PREFIX + label
        batches[label] = g
    return batches[label]


def leaf(label, x, d, angle, length, rise, width):
    # Closed curved blade, with real thin edges rather than duplicated coplanar faces.
    count = 7
    verts = []
    for side in [-1, 1]:
        for i in range(count):
            t = i / (count - 1)
            r = length * t
            w = max(0.005, width * math.sin(math.pi * t))
            z = BOTTOM + rise * math.sin(1.48 * t) - 0.08 * t * t
            for edge in [-1, 1]:
                verts.append(
                    world(
                        x + r * math.cos(angle) - edge * w * math.sin(angle),
                        d + r * math.sin(angle) + edge * w * math.cos(angle),
                        z + side * 0.006,
                    )
                )
    n = count * 2
    faces = []
    for i in range(count - 1):
        k = i * 2
        faces.extend(
            [
                (k, k + 2, k + 3, k + 1),
                (n + k + 1, n + k + 3, n + k + 2, n + k),
                (k, n + k, n + k + 2, k + 2),
                (k + 1, k + 3, n + k + 3, n + k + 1),
            ]
        )
    faces.extend([(0, 1, n + 1, n), (n - 2, 2 * n - 2, 2 * n - 1, n - 1)])
    batch(label).add(verts, faces)


# Continuous planted bed: three staggered rows, preserving original soil outline.
CLUSTERS = []
for i in range(24):
    for row, d in enumerate([0.55, 0.84, 1.12]):
        x = (
            LEFT
            + 0.23
            + (RIGHT - LEFT - 0.46) * i / 23
            + 0.06 * math.sin(i * 1.7 + row)
        )
        CLUSTERS.append([x, d])
        for k in range(5):
            angle = i * 0.73 + row * 1.4 + k * math.tau / 5
            leaf(
                "dense_planter_leaves",
                x,
                d,
                angle,
                0.22 + 0.09 * ((i + k + row) % 3),
                0.46 + 0.09 * ((i + 2 * k + row) % 3),
                0.095 + 0.02 * ((k + i) % 3),
            )
# The close frontal photograph registers tall canna-like leaves in first ordinary bay.
# Exact planting changes with season; two high clusters are illustrative estimates.
HIGH = [[-3.2, 0.88], [-2.45, 0.88]]
for j, (x, d) in enumerate(HIGH):
    for k in range(8):
        leaf(
            "upright_broad_leaves",
            x,
            d,
            j * 0.5 + k * math.tau / 8,
            0.20 + 0.04 * (k % 3),
            0.68 + 0.12 * (k % 4),
            0.12 + 0.02 * (k % 3),
        )
    for k in range(5):
        angle = k * math.tau / 5 + 0.2 * j
        z = 2.02 + 0.08 * j
        a = world(x, d, z - 0.08)
        b = world(
            x + 0.10 * math.cos(angle - 0.35),
            d + 0.10 * math.sin(angle - 0.35),
            z + 0.06,
        )
        c = world(x + 0.15 * math.cos(angle), d + 0.15 * math.sin(angle), z + 0.20)
        e = world(
            x + 0.10 * math.cos(angle + 0.35),
            d + 0.10 * math.sin(angle + 0.35),
            z + 0.06,
        )
        verts = [v + Vector((0, 0, s * 0.006)) for s in [-1, 1] for v in [a, b, c, e]]
        batch("yellow_flower_heads", "flower").add(
            verts,
            [
                (3, 2, 1, 0),
                (4, 5, 6, 7),
                (0, 1, 5, 4),
                (1, 2, 6, 5),
                (2, 3, 7, 6),
                (3, 0, 4, 7),
            ],
        )
owned = [g.finish() for g in batches.values()]
for o in owned:
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
assert sorted(o.name for o in owned) == sorted(NAMES)
width = 2.5021476908682994
CENTRES = [
    -6.844295381736599,
    -3.4221476908683,
    0.0,
    3.4221476908683,
    6.844295381736599,
]
probes = []
# Windows above planted foreground and entrance remain true first contacts.
for i, x in enumerate(CENTRES):
    for z in [2.5, 4.7, 7.0, 9.0]:
        for q in [-0.30, 0.30]:
            probes.append(
                {
                    "kind": "retainedGlass",
                    "x": x + q * width,
                    "d": 0.25,
                    "z": z,
                    "direction": list(-normal),
                    "distance": 1.2,
                }
            )
for x in [CENTRES[0] - 0.35, CENTRES[0] + 0.35]:
    probes.append(
        {
            "kind": "retainedDoor",
            "x": x,
            "d": 0.25,
            "z": 1.6,
            "direction": list(-normal),
            "distance": 1.2,
        }
    )
for d in [0.50, 0.86, 1.22, 1.58]:
    probes.append(
        {
            "kind": "retainedStair",
            "x": CENTRES[0],
            "d": d,
            "z": 1.8,
            "direction": [0, 0, -1],
            "distance": 2,
        }
    )
for x, d in [CLUSTERS[i] for i in [8, 15, 26, 42, 53, 68]]:
    probes.append(
        {
            "kind": "plantCoverage",
            "x": x + 0.08,
            "d": d,
            "z": 2.0,
            "direction": [0, 0, -1],
            "distance": 1.2,
        }
    )
probes.append(
    {
        "kind": "clearEntranceApproach",
        "x": CENTRES[0],
        "d": 2.8,
        "z": 1.1,
        "direction": list(-normal),
        "distance": 2.4,
    }
)
probes.append(
    {
        "kind": "clearPlanterFrontWalk",
        "x": LEFT - 0.5,
        "d": 1.8,
        "z": 1.4,
        "direction": list(u),
        "distance": RIGHT - LEFT + 1,
    }
)


def cast(exclude=()):
    verts = []
    faces = []
    owners = []
    for o in collection.all_objects:
        if o.type != "MESH" or o.hide_render or o.name in exclude:
            continue
        k = len(verts)
        verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
        faces.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
    t = BVHTree.FromPolygons(verts, faces)
    rows = []
    for p in probes:
        h = t.ray_cast(
            world(p["x"], p["d"], p["z"]), Vector(p["direction"]), p["distance"]
        )
        rows.append(
            {
                **p,
                "firstObject": owners[h[2]] if h[2] is not None else None,
                "hitLocal": list(local(h[0])) if h[0] is not None else None,
            }
        )
    return rows


before = cast(NAMES)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
after = cast()
assert [p for p in before if p["kind"].startswith("retained")] == [
    p for p in after if p["kind"].startswith("retained")
]
assert all(
    p["firstObject"]
    == (
        NAMES[1]
        if any(math.hypot(p["x"] - x, p["d"] - d) < 0.35 for x, d in HIGH)
        else NAMES[0]
    )
    for p in after
    if p["kind"] == "plantCoverage"
), after
assert all(
    p["firstObject"] is None for p in after if p["kind"].startswith("clear")
), after
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in ARCHIVE
)
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)


def pbr(m):
    p = m.node_tree.nodes["Principled BSDF"]
    return {
        "name": m.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "metallic": p.inputs["Metallic"].default_value,
        "roughness": p.inputs["Roughness"].default_value,
        "alpha": p.inputs["Alpha"].default_value,
    }


references = []
for name, reason in [
    (
        "reference-04.png",
        "Front photo shows dense continuous green planting, high broad leaves and yellow flowers in first ordinary bay; sculpture occludes part of bed.",
    ),
    (
        "reference-08.png",
        "Oblique photo corroborates continuous planted bed, tall broad leaves and sculpture red front/white sides. Foreground shrub is outside bed and not reconstructed.",
    ),
]:
    p = ROOT / "data/collections/public-realm-2026/user-references" / name
    references.append(
        {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "captureDate": "unknown",
            "evidence": reason,
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": NAMES,
    "archivedObjects": ARCHIVE,
    "archiveObjects": ARCHIVE,
    "changes": [
        {
            "source": ARCHIVE[0] if i == 0 else None,
            "owned": n,
            "action": (
                "Replace sparse uniform one-row foliage with continuous closed broad-leaf planting"
                if i == 0
                else "Add photograph-supported high leaf/flower family at first ordinary planter bay"
            ),
        }
        for i, n in enumerate(NAMES)
    ],
    "references": references,
    "registration": {
        **reg,
        "soilBounds": [LEFT, RIGHT],
        "soilTop": BOTTOM,
        "denseClusterCentres": CLUSTERS,
        "highClusterCentres": HIGH,
        "estimation": "Planter outline/soil height inherited native. Three staggered rows,72clusters and blade dimensions are authored estimates for photographed coverage, not surveyed planting counts. Tall clusters registered to first ordinary window centre-3.422m;±0.5m location uncertainty.",
    },
    "wholeFrontReview": {
        "fiveBays": "Already accepted53 registration retained",
        "blueCasements": "87 four-column ordinary lights and127 entrance2x2 transom retained",
        "stoneHead": "136 closure retained",
        "sculpture": "Native red front/white thickness,2.45m estimated height retained; no photo proves replacement",
        "entranceAndSteps": "Existing four steps,door,handrails,inscriptions and stone planter retained",
        "difference": "Native leaf family maximum1.408m above0.05m street,only0.351m above soil and repeated sparse one-row silhouettes; photos show continuous dense planting and taller broad leaves.",
    },
    "materials": {
        "sourceGreen": pbr(source.data.materials[0]),
        "ownedGreen": pbr(materials["leaf"]),
        "newYellow": pbr(flower),
        "originalMaterialSlotsUnchanged": True,
    },
    "beforeProbes": before,
    "afterProbes": after,
    "limitations": [
        "Capture dates and seasonal planting species/counts unknown. Flowers are visible in04 but exact live seasonal presence is not guaranteed.",
        "Leaf forms/heights/petal placement are photo-guided artistic estimates, not botanical scan.",
        "Complete upper architecture, exact setback/step dimensions and interior remain unmeasured; no unrelated facade change.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["OLD_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = NAMES
for o in dst.objects:
    collection.objects.link(o)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
assert cast() == after
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in ARCHIVE
)
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type not in {"LIGHT", "CAMERA"} and o.name not in members:
        o.hide_render = True
focus = world(-1, 0.4, 4.7)
camdata = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + normal * 26 + u * 5 + Vector((0, 0, 4))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 22
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-student-services.png")
bpy.ops.render.render(write_still=True)
v = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalObjectCount": len(originals),
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA,
    "reloadedProbes": after,
    "retainedGlazingDoorStepsFirstContacts": True,
    "entranceApproachAndFrontWalkClear": True,
    "ownedVertices": {o.name: len(o.data.vertices) for o in dst.objects},
    "ownedPolygons": {o.name: len(o.data.polygons) for o in dst.objects},
    "render": "reloaded-student-services.png",
    "camera": list(cam.location),
    "target": list(focus),
}
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print("OLD_STUDENT_VERIFIED", len(originals), len(after))
bpy.ops.wm.quit_blender()
