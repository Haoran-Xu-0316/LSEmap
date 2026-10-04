"""Clear photographed 51L front arch stone from metal reveals. Blender Text Editor."""

from pathlib import Path
import bpy, json, math, hashlib, array
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lincoln51_oblique151"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v150.blend"
EXPECTED = "d365166d2cc3011cfab00365593400aa56bd8aab1252ce974a7dabeb4af97147"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
else:
    BASE = max((ROOT / 'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),
               key=lambda path: int(path.stem.rsplit('v', 1)[1]))
    EXPECTED = hashlib.sha256(BASE.read_bytes()).hexdigest()

SOURCES = ["51L_NEXT_recessed_ashlar_backing", "51L_NEXT_ashlar_courses"]
NAMES = ["51L_NEXT_OBLIQUE_recessed_backing", "51L_NEXT_OBLIQUE_ashlar_courses"]
COMPONENT = OUT / "lincoln51-oblique-clearance-component.blend"
reg = json.loads(
    (ROOT / "result/blender/stage92/lincolns-three-bay-audit.json").read_text()
)["frame"]
a = Vector(reg["origin"])
u = Vector(reg["right"])
n = Vector(reg["normal"])
L = reg["length"]
radius = L / 3 * 0.58 / 2
clearance = 0.008
new_radius = radius + 0.045 + clearance
camera = Vector((-61.77983943876207, 67.04184742630517, 3.7))
target = Vector((-65.16224167275132, 57.84351305928499, 3.35))


def local(p):
    return Vector(((p - a).dot(u), (p - a).dot(n), p.z))


def world(x, d, z):
    return a + u * x + n * d + Vector((0, 0, z))


def fp(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, count in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            ar = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, ar)
            h.update(ar.tobytes())
        for layer in o.data.uv_layers:
            ar = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", ar)
            h.update(ar.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    previous = json.loads((OUT / 'audit.json').read_text()) if (OUT / 'audit.json').exists() else {}
    for name in NAMES:
        obj = bpy.data.objects.get(name)
        if obj:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for name in SOURCES:
        obj = bpy.data.objects[name]
        state = previous.get('originalVisibility', {}).get(name, [False, False, False])
        obj.hide_render, obj.hide_viewport = state[:2]
        obj.hide_set(state[2])
    for layer in bpy.context.scene.view_layers:
        layer.update()


open_base()
originals = {o.name: fp(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
col = bpy.data.collections["51L_EXTERIOR"]


def probes():
    dg = bpy.context.evaluated_depsgraph_get()
    trees = []
    for o in col.all_objects:
        if o.type != "MESH" or o.hide_render:
            continue
        e = o.evaluated_get(dg)
        m = e.to_mesh()
        trees.append(
            (
                o.name,
                BVHTree.FromPolygons(
                    [o.matrix_world @ v.co for v in m.vertices],
                    [list(p.vertices) for p in m.polygons],
                ),
            )
        )
        e.to_mesh_clear()
    rows = []
    for bay in range(3):
        for j in range(1, 96):
            theta = math.pi * j / 96
            # Target the recessed inner reveal at its actual metal/stone depth overlap.
            for dr in [0, 0.005, 0.020, 0.040]:
                p = world(
                    (bay + 0.5) * L / 3 + (radius + dr) * math.cos(theta),
                    -0.035,
                    2.3 + (radius + dr) * math.sin(theta),
                )
                direction = (p - camera).normalized()
                hits = []
                for name, t in trees:
                    q = t.ray_cast(camera, direction, (p - camera).length + 0.15)
                    if q[0] != None:
                        hits.append((q[3], name, list(q[0])))
                hits.sort()
                rows.append(
                    dict(bay=bay, angle=j * 180 / 96, radiusOffset=dr, hits=hits[:3])
                )
    return rows


before = probes()
owned = []
changed = {}
for source, name in zip(SOURCES, NAMES):
    src = bpy.data.objects[source]
    o = src.copy()
    o.data = src.data.copy()
    o.name = name
    o.data.name = name
    col.objects.link(o)
    count = 0
    for v in o.data.vertices:
        p = local(o.matrix_world @ v.co)
        if p.z > 4.1 or p.z < 0.399 or abs(p.y) > 0.35:
            continue
        for bay in range(3):
            c = (bay + 0.5) * L / 3
            dx = p.x - c
            dz = p.z - 2.3
            boundary = False
            if p.z <= 2.30001 and abs(abs(dx) - radius) < 0.00004:
                p.x = c + (radius + 0.053) * (1 if dx > 0 else -1)
                boundary = True
            elif dz >= -0.00001:
                point = Vector((dx, dz))
                best = 1e9
                for j in range(24):
                    q = Vector(
                        (
                            radius * math.cos(math.pi * j / 24),
                            radius * math.sin(math.pi * j / 24),
                        )
                    )
                    r = Vector(
                        (
                            radius * math.cos(math.pi * (j + 1) / 24),
                            radius * math.sin(math.pi * (j + 1) / 24),
                        )
                    )
                    d = r - q
                    t = max(0, min(1, (point - q).dot(d) / d.length_squared))
                    best = min(best, (point - (q + t * d)).length)
                if best < 0.00004:
                    p.x = c + dx * new_radius / radius
                    p.z = 2.3 + dz * new_radius / radius
                    boundary = True
            if boundary:
                v.co = o.matrix_world.inverted() @ world(p.x, p.y, p.z)
                count += 1
                break
    o.data.update()
    changed[source] = count
    assert count > 0
    src.hide_render = True
    src.hide_set(True)
    owned.append(o)
assert all(fp(bpy.data.objects[k]) == v for k, v in originals.items())
after = probes()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
audit = dict(
    baselineSha256=EXPECTED,
    ownedObjects=NAMES,
    archivedObjects=SOURCES,
    changes=[
        dict(source=s, owned=o, action="replace aperture boundary only")
        for s, o in zip(SOURCES, NAMES)
    ],
    originalFingerprints=originals,
    originalVisibility=visibility,
    changedVertices=changed,
    registration=reg,
    originalRadiusM=radius,
    metalOuterRadiusM=radius + 0.045,
    estimatedClearanceM=clearance,
    diagnosis="Edge1 three arches: stone and metal inner reveal surfaces shared the same radius and overlapping depth, visible as oblique fragments. Not edge3 seven arches.",
    sources=[
        "data/collections/lincolns-frontage-review/51l-gsos-2025.jpg",
        "data/建筑图片/51L_51 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_015.jpg",
    ],
    limits=[
        "Photo capture dates unknown; clearance is geometric estimate",
        "All frames, glass, doors, upper stone courses, UV and material slots retained",
        "No claim of survey dimensions or unseen facade correction",
    ],
    productionCamera=dict(position=list(camera), target=list(target), fov=42),
    beforeObliqueProbes=before,
    afterObliqueProbes=after,
)
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
col = bpy.data.collections["51L_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(NAMES)
for o in dst.objects:
    col.objects.link(o)
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
reloaded = probes()
assert reloaded == after
assert all(fp(bpy.data.objects[k]) == v for k, v in originals.items())
assert all(
    [
        bpy.data.objects[k].hide_render,
        bpy.data.objects[k].hide_viewport,
        bpy.data.objects[k].hide_get(),
    ]
    == v
    for k, v in visibility.items()
    if k not in SOURCES
)
scene = bpy.context.scene
keep = {o.name for o in col.all_objects}
for o in scene.objects:
    if o.name not in keep:
        o.hide_render = True
camdata = bpy.data.cameras.new("51L_OBLIQUE_REVIEW")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = camera
cam.rotation_euler = (target - camera).to_track_quat("-Z", "Y").to_euler()
camdata.type = "PERSP"
camdata.sensor_fit = "VERTICAL"
camdata.sensor_height = 24
camdata.lens = 24 / (2 * math.tan(math.radians(42) / 2))
scene.camera = cam
lightdata = bpy.data.lights.new("51L_OBLIQUE_LIGHT", "AREA")
light = bpy.data.objects.new(lightdata.name, lightdata)
scene.collection.objects.link(light)
light.location = camera + Vector((0, 0, 5))
light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
lightdata.energy = 1800
lightdata.size = 10
scene.world.color = (0.35, 0.35, 0.35)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1936
scene.render.resolution_y = 1549
scene.render.resolution_percentage = 70
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-production-angle.png")
bpy.ops.render.render(write_still=True)
proof = dict(
    componentSha256=hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    savedComponentReopened=True,
    originalGeometryPreserved=True,
    unrelatedVisibilityPreserved=True,
    originalObjectCount=len(originals),
    obliqueProbeCount=len(after),
    savedReloadObliqueProbeParity=True,
    baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED,
    nativePreview="reloaded-production-angle.png",
    scope="Stone aperture only, edge1 three arches; two replacements",
)
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print(proof, flush=True)
