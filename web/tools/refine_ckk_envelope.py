"""Restore CKK's photographed broad top-storey windows in both projecting wings.

Run in Blender Text Editor. All dimensions remain photo-based estimates; existing
frontage, roof apertures, rooms and material finishes are preserved.
"""

from pathlib import Path
import array, hashlib, json, math
from collections import Counter
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/ckk_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v138.blend"
BASE_SHA = "6696488952844255f1e38ca718af49bd14f2fb6969d9951a83655c734ef40253"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
families = [
    "masonry",
    "recessed_glass",
    "window_frames",
    "stone_reveals",
    "centre_mullions",
    "projecting_sills",
]
SOURCES = ["CKK_NEXT_WING_" + f for f in families]
NAMES = ["CKK_NEXT_ENVELOPE_" + f for f in families]
prior = (
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
            assert obj.type == "MESH"
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    if prior:
        for name in SOURCES:
            obj = bpy.data.objects[name]
            state = prior["originalVisibility"][name]
            obj.hide_render, obj.hide_viewport = state[:2]
            obj.hide_set(state[2])
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, width in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            a = array.array(kind, [0]) * (len(data) * width)
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
collection = bpy.data.collections["CKK_EXTERIOR"]
centre = Vector((-110.49102024587766, 77.56014819690478, 0))
angle = math.radians(22)
outward = Vector((math.cos(angle), math.sin(angle), 0))
axis = Vector((-math.sin(angle), math.cos(angle), 0))


def local(p):
    q = p - centre
    return Vector((q.dot(outward), q.dot(axis), p.z))


def world(p):
    return centre + outward * p.x + axis * p.y + Vector((0, 0, p.z))


low, high, width = 22.5, 24.0, 3.65
middles = [-12.65, 12.65]


def parts(bm):
    seen = set()
    for seed in bm.verts:
        if seed in seen:
            continue
        todo = [seed]
        seen.add(seed)
        part = []
        while todo:
            v = todo.pop()
            part.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o not in seen:
                    seen.add(o)
                    todo.append(o)
        yield part


def add_box(bm, obj, p, size):
    x, y, z = p
    a, b, h = [v / 2 for v in size]
    inverse = obj.matrix_world.inverted()
    vertices = [
        bm.verts.new(inverse @ world(Vector((x + dx * a, y + dy * b, z + dz * h))))
        for dx, dy, dz in [
            (-1, -1, -1),
            (-1, -1, 1),
            (-1, 1, -1),
            (-1, 1, 1),
            (1, -1, -1),
            (1, -1, 1),
            (1, 1, -1),
            (1, 1, 1),
        ]
    ]
    for f in [
        (0, 2, 6, 4),
        (1, 5, 7, 3),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 1, 3, 2),
        (4, 6, 7, 5),
    ]:
        bm.faces.new([vertices[i] for i in f])


owned = []
counts = []
retained = {}
for family, source_name, name in zip(families, SOURCES, NAMES):
    source = bpy.data.objects[source_name]
    assert not source.hide_render
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    obj.data.name = name
    collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    delete = []
    removed = 0
    untouched = []
    for part in list(parts(bm)):
        pts = [local(obj.matrix_world @ v.co) for v in part]
        avg = sum(pts, Vector()) / len(pts)
        top = (
            low - 0.19 <= min(p.z for p in pts) and max(p.z for p in pts) <= high + 0.19
        )
        wing = any(abs(avg.y - y) < 3.76 for y in middles)
        if top and wing:
            delete.extend(part)
            removed += 1
        else:
            untouched.extend(tuple(v.co) for v in part)
    assert (
        removed
        == {
            "masonry": 8,
            "recessed_glass": 6,
            "window_frames": 24,
            "stone_reveals": 12,
            "centre_mullions": 6,
            "projecting_sills": 6,
        }[family]
    ), (family, removed)
    bmesh.ops.delete(bm, geom=delete, context="VERTS")
    for y in middles:
        left, right = y - 3.75, y + 3.75
        x = 23.2
        if family == "masonry":
            for a, b in [(left, y - width / 2), (y + width / 2, right)]:
                add_box(
                    bm,
                    obj,
                    (x - 0.25, (a + b) / 2, (low + high) / 2),
                    (0.5, b - a, high - low),
                )
        elif family == "recessed_glass":
            add_box(bm, obj, (x - 0.15, y, (low + high) / 2), (0.06, width, high - low))
        elif family == "window_frames":
            for side in [-1, 1]:
                add_box(
                    bm,
                    obj,
                    (x - 0.075, y + side * (width / 2 - 0.035), (low + high) / 2),
                    (0.12, 0.075, high - low),
                )
            for z in [low + 0.035, high - 0.035]:
                add_box(bm, obj, (x - 0.075, y, z), (0.12, width, 0.07))
        elif family == "stone_reveals":
            for side in [-1, 1]:
                add_box(
                    bm,
                    obj,
                    (x + 0.045, y + side * (width / 2 + 0.07), (low + high) / 2),
                    (0.19, 0.14, high - low + 0.16),
                )
        elif family == "centre_mullions":
            for side in [-1, 1]:
                add_box(
                    bm,
                    obj,
                    (x - 0.055, y + side * width / 6, (low + high) / 2),
                    (0.12, 0.055, high - low),
                )
        elif family == "projecting_sills":
            add_box(bm, obj, (x + 0.12, y, low - 0.10), (0.44, width + 0.30, 0.15))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    assert not Counter(untouched) - Counter(tuple(v.co) for v in obj.data.vertices)
    retained[name] = len(untouched)
    owned.append(obj)
    counts.append(
        {"family": family, "removedParts": removed, "unchangedVertices": len(untouched)}
    )
probes = []
for y in middles:
    for z in [22.8, 23.65]:
        for dy in [-1.2, -0.3, 0.3, 1.2]:
            probes.append({"kind": "broadGlass", "y": y + dy, "z": z})
for y in middles:
    for z in [22.8, 23.65]:
        for dy in [-2.2, 2.2]:
            probes.append({"kind": "formerOuterPaneNowStone", "y": y + dy, "z": z})
for y in middles:
    for dy in [-width / 6, width / 6]:
        probes.append({"kind": "threeLightMullion", "y": y + dy, "z": 23.35})
for y in [-14.65, -12.35, -10.65, 10.65, 12.95, 14.65]:
    for z in [10.3, 14.6, 18.8]:
        probes.append({"kind": "retainedLowerWindow", "y": y, "z": z})
for y in [-7, -3.2, 3.8, 7]:
    probes.append({"kind": "retainedCentralTop", "y": y, "z": 23.2})


def cast(objects):
    vs = []
    fs = []
    names = []
    for o in objects:
        offset = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        fs.extend(tuple(offset + i for i in f.vertices) for f in o.data.polygons)
        names.extend([o.name] * len(o.data.polygons))
    tree = BVHTree.FromPolygons(vs, fs)
    results = []
    for p in probes:
        h = tree.ray_cast(world(Vector((26, p["y"], p["z"]))), -outward, 5)
        results.append({**p, "firstObject": names[h[2]] if h[2] is not None else None})
    return results


visible = lambda: [
    o for o in collection.all_objects if o.type == "MESH" and not o.hide_render
]
before = cast([o for o in visible() if o not in owned])
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
after = cast(visible())
aliases = dict(zip(NAMES, SOURCES))
assert all(p["firstObject"] == NAMES[1] for p in after[:16]), after[:16]
assert all(p["firstObject"] == NAMES[0] for p in after[16:24]), after[16:24]
assert all(p["firstObject"] == NAMES[4] for p in after[24:28]), after[24:28]
assert [
    {**p, "firstObject": aliases.get(p["firstObject"], p["firstObject"])}
    for p in after[28:]
] == before[28:]
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in SOURCES
)


def pbr(m):
    p = m.node_tree.nodes["Principled BSDF"]
    return {
        "name": m.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "metallic": p.inputs["Metallic"].default_value,
        "roughness": p.inputs["Roughness"].default_value,
        "alpha": p.inputs["Alpha"].default_value,
        "transmission": p.inputs["Transmission Weight"].default_value,
    }


component = OUT / "cheng-kin-ku-broad-attic-window-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
photo = (
    ROOT
    / "data/建筑图片/CKK_Cheng Kin Ku Building/01_建筑实拍/exteriors_ckk_grimshaw_010.jpg"
)
audit = {
    "baselineSha256": BASE_SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": NAMES,
    "archivedObjects": SOURCES,
    "archiveObjects": SOURCES,
    "changes": [
        {
            "source": s,
            "owned": o,
            "action": "Replace wing top-storey three discrete narrow openings with one broad three-light opening; retain all other parts",
        }
        for s, o in zip(SOURCES, NAMES)
    ],
    "reference": {
        "local": str(photo.relative_to(ROOT)),
        "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "source": "Grimshaw completed New Academic Building photography",
        "captureDate": "unknown",
        "supports": "Both projecting wings have a single broad horizontal opening in the stone short-storey immediately below the mansard, rather than three masonry-separated narrow lights.",
    },
    "registration": {
        "centres": middles,
        "sill": low,
        "head": high,
        "oldThreeOpeningCombinedSpan": 4.92,
        "newSingleOpeningWidth": width,
        "estimatedWidthRelativeToCentralWindow": width / 1.65,
        "newLights": 3,
        "dimensionBasis": "Photo010 wing opening roughly2.2 times a central top-storey window; existing central1.65m datum retained",
        "absoluteDimensionsEstimated": True,
    },
    "geometryChanges": counts,
    "retainedVertices": retained,
    "materials": [
        {
            "source": s,
            "original": pbr(bpy.data.objects[s].data.materials[0]),
            "owned": pbr(o.data.materials[0]),
            "changed": False,
        }
        for s, o in zip(SOURCES, owned)
    ],
    "beforeProbes": before,
    "afterProbes": after,
    "wholeFrontageReview": {
        "outline": "Historic stepped stone front and two projecting wings retained; GIS footprint/depth and absolute heights remain estimates.",
        "windowRows": "Central5 bays and lower wing narrow windows retained; prior18 middle/upper wing corrections and segmental pediments unchanged.",
        "attic": "Two broad stone-top openings now reproduce the photographed horizontal composition; mansard18 apertures and roof pavilion retained.",
        "glass": "Inherited glazing PBR unchanged; no guessed interior enclosure or global opacity adjustment.",
        "entrance": "Arched fanlight rim and unsplit accepted glazing retained; door, rustication and all room samples unchanged.",
    },
    "limitations": [
        "Photo date unverified; not a present-day measured survey.",
        "Overall opening width and internalthree-light spacing estimated; photographs are not window shop drawings.",
        "Original top-storey sill/head and projecting wing offsets retained; exact survey levels unknown.",
        "Unseen rear/interior structure, exact window opening mechanisms and roof depths remain unvalidated.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
print("CKK_ENVELOPE_SAVED", counts, flush=True)
open_base()
collection = bpy.data.collections["CKK_EXTERIOR"]
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = NAMES
for o, s in zip(dst.objects, SOURCES):
    collection.objects.link(o)
    for i, m in enumerate(bpy.data.objects[s].data.materials):
        o.data.materials[i] = m
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
assert cast(visible()) == after
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in SOURCES
)
scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type == "MESH" and o.name not in members:
        o.hide_render = True
focus = world(Vector((23, 0, 15.7)))
camera = bpy.data.cameras.new("CKK_NEXT_ENVELOPE_review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = focus + outward * 70 + Vector((0, 0, 1))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 37
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1450
scene.render.resolution_y = 1300
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-ckk-front-envelope.png")
bpy.ops.render.render(write_still=True)
verification = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "originalObjectCount": len(originals),
    "reloadedProbes": after,
    "retainedVertices": retained,
    "nativeRender": "reloaded-ckk-front-envelope.png",
    "broadWingWindows": 2,
    "threeLightDivisions": 4,
    "retainedLowerAndCentralProbesUnchanged": True,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("CKK_ENVELOPE_REOPENED_VERIFIED", len(originals), len(after), flush=True)
bpy.ops.wm.quit_blender()
