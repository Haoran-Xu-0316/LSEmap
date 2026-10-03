"""Correct the registered northern MAR office window rhythm.

Run in Blender Text Editor. Only the two north office faces are reconstructed;
photographic height registration is approximate, not an as-built survey.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v137.blend"
BASE_SHA = "868b9ef1f8d4d2b0680752a90e96a80a575ffb0c1b54b0013cd2995c51cc7d7f"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
RECOVERY_AUDIT = (
    json.loads((ROOT / "result/blender/mar_envelope_next/audit.json").read_text())
    if (ROOT / "result/blender/mar_envelope_next/audit.json").exists()
    else None
)
SOURCES = ["MAR_D5_north115_panel", "MAR_D5_north115_glass", "MAR_D5_north115_frame"]
NAMES = [
    "MAR_NEXT_ENVELOPE_north_three_row_walls",
    "MAR_NEXT_ENVELOPE_north_three_row_glass",
    "MAR_NEXT_ENVELOPE_north_three_row_frames",
]


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    # Undo this component alone when recovering from a newer merged campus.
    for name in NAMES:
        obj = bpy.data.objects.get(name)
        if obj:
            assert obj.type == "MESH"
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    if RECOVERY_AUDIT:
        for name in SOURCES:
            obj = bpy.data.objects[name]
            state = RECOVERY_AUDIT["originalVisibility"][name]
            obj.hide_render, obj.hide_viewport = state[:2]
            obj.hide_set(state[2])
    for sc in bpy.data.scenes:
        for layer in sc.view_layers:
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
collection = bpy.data.collections["MAR_EXTERIOR"]
a = math.radians(22)
u = Vector((math.cos(a), math.sin(a), 0))
n = Vector((-math.sin(a), math.cos(a), 0))
origin = Vector((-8.696325894899289, 49.33154396120258, 0))


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(n), p.z))


def point(x, y, z):
    return origin + u * x + n * y + Vector((0, 0, z))


rows = [(24.0, 26.2), (27.0, 29.2), (30.0, 32.2)]
spans = [(-30.0, -15.2, 5), (-2.0, 24.0, 10)]
owned = []
removed = []
retained = []
new_faces = {k: [] for k in ["panel", "glass", "frame"]}


def face(kind, coords):
    new_faces[kind].append([point(*p) for p in coords])


def plane(kind, x0, x1, z0, z1, depth):
    face(kind, [(x1, depth, z0), (x0, depth, z0), (x0, depth, z1), (x1, depth, z1)])


def masonry(x0, x1, z0, z1):
    # Real 100mm wall depth and opening returns; nothing closes a window hole.
    plane("panel", x0, x1, z0, z1, 18.8)
    plane("panel", x1, x0, z0, z1, 18.7)
    for xx in [x0, x1]:
        face("panel", [(xx, 18.8, z0), (xx, 18.7, z0), (xx, 18.7, z1), (xx, 18.8, z1)])
    for zz in [z0, z1]:
        face("panel", [(x0, 18.8, zz), (x1, 18.8, zz), (x1, 18.7, zz), (x0, 18.7, zz)])


windows = []
for left, right, columns in spans:
    cuts = []
    for i in range(columns):
        x = left + (i + 0.5) * (right - left) / columns
        for bottom, top in rows:
            cuts.append((x - 0.725, bottom, x + 0.725, top))
            windows.append({"centreX": x, "bottom": bottom, "top": top})
    xs = sorted({left, right, *[v for r in cuts for v in [r[0], r[2]]]})
    zs = sorted({23.4, 32.65, *[v for r in cuts for v in [r[1], r[3]]]})
    for x0, x1 in zip(xs, xs[1:]):
        for z0, z1 in zip(zs, zs[1:]):
            if any(
                c[0] < (x0 + x1) / 2 < c[2] and c[1] < (z0 + z1) / 2 < c[3]
                for c in cuts
            ):
                continue
            masonry(x0, x1, z0, z1)
    for x0, z0, x1, z1 in cuts:
        plane("glass", x0 + 0.02, x1 - 0.02, z0 + 0.02, z1 - 0.02, 18.68)
        for xx in [x0, x1]:
            plane("frame", xx - 0.025, xx + 0.025, z0, z1, 18.71)
        for zz in [z0, z1]:
            plane("frame", x0, x1, zz - 0.025, zz + 0.025, 18.71)
        zz = z0 + (z1 - z0) * 0.52
        plane("frame", x0, x1, zz - 0.018, zz + 0.018, 18.72)
for kind, name, source_name in zip(["panel", "glass", "frame"], NAMES, SOURCES):
    source = bpy.data.objects[source_name]
    assert not source.hide_render
    vertices = []
    faces = []
    indices = []
    uvs = [[] for l in source.data.uv_layers]
    kept = []
    removed_count = 0
    for f in source.data.polygons:
        ps = [
            local(source.matrix_world @ source.data.vertices[i].co) for i in f.vertices
        ]
        north = (
            all(abs(p.y - 18.8) < 1e-4 for p in ps)
            if kind == "panel"
            else all(18.675 < p.y < 18.726 for p in ps)
        )
        registered = any(
            all(left - 0.03 < p.x < right + 0.03 for p in ps)
            for left, right, c in spans
        )
        if north and registered:
            removed_count += 1
            continue
        offset = len(vertices)
        points = [source.data.vertices[i].co.copy() for i in f.vertices]
        vertices.extend(points)
        faces.append(tuple(range(offset, offset + len(points))))
        indices.append(f.material_index)
        kept.append([list(p) for p in points])
        for j, layer in enumerate(source.data.uv_layers):
            uvs[j].extend(list(layer.data[i].uv) for i in f.loop_indices)
    assert removed_count > 0
    inverse = source.matrix_world.inverted()
    for ps in new_faces[kind]:
        offset = len(vertices)
        vertices.extend(inverse @ p for p in ps)
        faces.append(tuple(range(offset, offset + len(ps))))
        indices.append(0)
        for layer in uvs:
            layer.extend((0.0, 0.0) for p in ps)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    for m in source.data.materials:
        mesh.materials.append(m)
    for f, index in zip(mesh.polygons, indices):
        f.material_index = index
    for layer, values in zip(source.data.uv_layers, uvs):
        uv = mesh.uv_layers.new(name=layer.name)
        for data, value in zip(uv.data, values):
            data.uv = value
        uv.active_render = layer.active_render
    mesh.update()
    o = source.copy()
    o.data = mesh
    o.name = name
    collection.objects.link(o)
    owned.append(o)
    removed.append(removed_count)
    retained.append(
        {
            "source": source_name,
            "faces": len(kept),
            "geometrySha256": hashlib.sha256(json.dumps(kept).encode()).hexdigest(),
        }
    )
assert removed[1] == 30 and removed[2] == 150, removed
probes = []
for i, w in enumerate(windows):
    probes.extend(
        [
            {
                "label": "glass-" + str(i),
                "x": w["centreX"] + 0.40,
                "z": w["bottom"] + 0.75,
                "depth": 19.2,
            },
            {
                "label": "head-" + str(i),
                "x": w["centreX"],
                "z": w["top"] + 0.15,
                "depth": 19.2,
            },
        ]
    )
probes.extend(
    {
        "label": "glazing-edge-" + str(i),
        "x": w["centreX"] - 0.695,
        "z": w["bottom"] + 0.75,
        "depth": 19.2,
    }
    for i, w in enumerate(windows)
)
# Registered fissure sky/return checks prove the existing court remains unchanged.
probes.extend(
    {"label": "fissure-" + str(z), "x": -8.5, "z": z, "depth": 22.5}
    for z in [25.0, 28.0, 31.0, 34.0]
)


def cast(objects):
    vs = []
    fs = []
    names = []
    for o in objects:
        k = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        fs.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        names.extend([o.name] * len(o.data.polygons))
    tree = BVHTree.FromPolygons(vs, fs)
    results = []
    for p in probes:
        hit = tree.ray_cast(point(p["x"], p["depth"], p["z"]), -n, 40)
        results.append(
            {**p, "firstObject": names[hit[2]] if hit[2] is not None else None}
        )
    return results


visible = lambda: [
    o for o in collection.all_objects if o.type == "MESH" and not o.hide_render
]
before = cast([o for o in visible() if o not in owned])
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
after = cast(visible())
assert all(
    p["firstObject"] == NAMES[0 if i % 2 else 1] for i, p in enumerate(after[:90])
), after[:90]
assert all(p["firstObject"] == NAMES[1] for p in after[90:135])
aliases = dict(zip(NAMES, SOURCES))
assert [
    {**p, "firstObject": aliases.get(p["firstObject"], p["firstObject"])}
    for p in after[135:]
] == before[135:]
assert all(fingerprint(bpy.data.objects[name]) == v for name, v in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in SOURCES
)


def pbr(m):
    shader = m.node_tree.nodes.get("Principled BSDF")
    return {
        "name": m.name,
        "baseColor": list(shader.inputs["Base Color"].default_value),
        "metallic": shader.inputs["Metallic"].default_value,
        "roughness": shader.inputs["Roughness"].default_value,
        "alpha": shader.inputs["Alpha"].default_value,
        "transmission": shader.inputs["Transmission Weight"].default_value,
    }


component = OUT / "marshall-north-three-row-envelope-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
refs = []
for number in ["02", "04", "03", "05"]:
    p = ROOT / (
        "data/建筑图片/MAR_Marshall Building/01_建筑实拍/architecture_round5_MAR_mar_kane_"
        + number
        + ".jpg"
    )
    refs.append(
        {
            "local": str(p.relative_to(ROOT)),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "source": "Nick Kane architect project photography",
            "url": "https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/",
            "uploadYear": 2022,
            "captureDate": "unknown",
            "role": "02/04 register three northern office rows;03 shows roof separation;05 bounds courtyard unchanged",
        }
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
            "action": "Replace only registered north office face two-row fenestration with true three-row openings; retain all courtyard return faces",
        }
        for s, o in zip(SOURCES, NAMES)
    ],
    "references": refs,
    "windowRegistration": {
        "oldRows": [[24.0, 27.55], [28.65, 32.2]],
        "newRows": rows,
        "northPlane": 18.8,
        "wallThicknessEstimated": 0.10,
        "recessedGlassPlane": 18.68,
        "spans": spans,
        "windowWidthRetained": 1.45,
        "glassFrameOverlapEstimated": 0.005,
        "newWindowCount": 45,
        "retainedReturnWindowCount": 16,
        "absoluteDimensionsEstimated": True,
    },
    "retainedFaces": retained,
    "removedFaceCounts": removed,
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
    "wholeEnvelopeReview": {
        "screen": "Existing manufacturer-supported38 upper and20 lower fins retained, including all returns, original materials and recorded dimensional limitations.",
        "fissure": "Existing115 deep central court retained; no displacement of its known registration or newly imagined bridge geometry.",
        "roof": "Current115 northern setback/terrace and taller rear blocks retained;03 confirms separation but hidden rear roof details not measured.",
        "rear": "05 supports rear wings and courtyard grid; accepted opening guards unchanged, unseen wall and exact window schedule not asserted.",
        "north": "02 and04 clearly show three glazed rows behind the upper screen; old115 only had two very tall windows per bay. True wall openings, glass and joinery now revised coherently.",
        "glass": "Original native PBR retained. Root handles web environment reflection binding; no blind transparency or guessed room enclosure.",
    },
    "limitations": [
        "Photo capture dates unknown;2022 upload not current survey.",
        "Northern sill/head values are estimated proportional registration inside the retained23.4–32.65m wall extent.",
        "North bay counts and widths inherited from115; exact current measured facade dimensions remain unverified.",
        "Court return windows remain the original two-row approximation because front/side photos do not establish their full schedule.",
        "No interior partitions, additional room volumes or unseen rear faces were reconstructed.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
print("MAR_ENVELOPE_COMPONENT_SAVED", removed, flush=True)
open_base()
collection = bpy.data.collections["MAR_EXTERIOR"]
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
assert all(fingerprint(bpy.data.objects[name]) == v for name, v in originals.items())
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
focus = point(-3, 20, 24)
camera = bpy.data.cameras.new("MAR_NEXT_ENVELOPE_review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = focus + n * 72 + Vector((0, 0, 5))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 60
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1150
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-marshall-north-envelope.png")
bpy.ops.render.render(write_still=True)
verification = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "originalObjectCount": len(originals),
    "reloadedProbes": after,
    "nativeRender": "reloaded-marshall-north-envelope.png",
    "northWindowCount": 45,
    "retainedReturnWindowCount": 16,
    "fissureProbesUnchanged": True,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("MAR_ENVELOPE_REOPENED_VERIFIED", len(originals), len(after), flush=True)
bpy.ops.wm.quit_blender()
