"""Correct photographed 61 Aldwych photographed dark roof dormer cheeks and shallow pitched caps.
Run in Blender Text Editor. Only street-wing roof dormers change; corner pavilion and lower facades remain unchanged.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/aldwych_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v140.blend"
BASE_SHA = "08ec52560290c5969deeda40eb760db0f2c33c7c0674833273e95085892a0ea2"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()

SOURCES = ["61A_D5_roof_dormer_stone", "61A_D5_dormer_coping_trim"]
NAMES = [
    "61A_NEXT_ENVELOPE_dark_dormer_cheeks",
    "61A_NEXT_ENVELOPE_pitched_dormer_caps",
    "61A_NEXT_ENVELOPE_dormer_perimeter_frames",
]
prior = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else None
)


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for name in NAMES:
        o = bpy.data.objects.get(name)
        if o:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    if prior:
        for name in SOURCES:
            o = bpy.data.objects[name]
            state = prior["originalVisibility"][name]
            o.hide_render, o.hide_viewport = state[:2]
            o.hide_set(state[2])
    for sc in bpy.data.scenes:
        for layer in sc.view_layers:
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
collection = bpy.data.collections["61A_EXTERIOR"]
assert len(originals) >= 5616


def boxes(o):
    assert len(o.data.vertices) % 8 == 0
    return [
        [o.matrix_world @ v.co for v in o.data.vertices[i : i + 8]]
        for i in range(0, len(o.data.vertices), 8)
    ]


class MeshBuilder:
    def __init__(self, name, material):
        self.name = name
        self.material = material
        self.v = []
        self.f = []
        self.extra = []
        self.extraFaces = []

    def add(self, vs, fs):
        start = len(self.v)
        self.v.extend(vs)
        self.f.extend(tuple(start + i for i in f) for f in fs)

    def box(self, w, x, z, width, height, depth, offset):
        def point(xx, dd, zz):
            return w["centre"] + w["u"] * xx + w["n"] * dd + Vector((0, 0, zz - 30.7))

        vs = [
            point(x + a * width / 2, offset + b * depth / 2, z + c * height / 2)
            for a, b, c in [
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
        self.add(
            vs,
            [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ],
        )

    def finish(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.v, [], self.f)
        mesh.update()
        uv = mesh.uv_layers.new(name="SurfaceUV")
        for face in mesh.polygons:
            ps = [mesh.vertices[i].co for i in face.vertices]
            a = ps[0]
            u = (ps[1] - a).normalized()
            n = (ps[1] - a).cross(ps[-1] - a).normalized()
            v = n.cross(u)
            for i, p in zip(face.loop_indices, ps):
                uv.data[i].uv = ((p - a).dot(u), (p - a).dot(v))
        mesh.materials.append(self.material)
        for m in self.extra:
            mesh.materials.append(m)
        for i in self.extraFaces:
            mesh.polygons[i].material_index = 1
        o = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(o)
        return o


slate = bpy.data.materials["61A_slate"]
bronze = bpy.data.materials["61A_bronze"]
wall = MeshBuilder(NAMES[0], slate)
cap = MeshBuilder(NAMES[1], slate)
frame = MeshBuilder(NAMES[2], bronze)
windows = []
glassboxes = boxes(bpy.data.objects["61A_D5_roof_window_glass"])
for index, ps in enumerate(boxes(bpy.data.objects[SOURCES[0]])):
    c = sum(ps, Vector()) / 8
    g = min(glassboxes, key=lambda gs: (sum(gs, Vector()) / 8 - c).length)
    gc = sum(g, Vector()) / 8
    u = (ps[4] - ps[0]).normalized()
    n = Vector((gc.x - c.x, gc.y - c.y, 0)).normalized()
    w = {"centre": c, "u": u, "n": n, "index": index}
    assert abs(c.z - 30.7) < 0.001 and abs((ps[4] - ps[0]).length - 1.95) < 0.001
    w["retainedCorner"] = (
        Vector((c.x, c.y, 0)) - Vector((-40.832898, -129.292874, 0))
    ).length < 3.5
    windows.append(w)
    if w["retainedCorner"]:
        start = len(wall.f)
        wall.add(
            ps,
            [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ],
        )
        wall.extraFaces.extend(range(start, len(wall.f)))
        cps = boxes(bpy.data.objects[SOURCES[1]])[index]
        start = len(cap.f)
        cap.add(
            cps,
            [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ],
        )
        cap.extraFaces.extend(range(start, len(cap.f)))
        continue
    # Real full-depth opening retains original1.50×1.65 glazing, rather than painting glass over a solid box.
    for side in [-1, 1]:
        wall.box(w, side * 0.8625, 30.7, 0.225, 2.45, 1.35, 0)
    for z in [29.675, 31.725]:
        wall.box(w, 0, z, 1.5, 0.40, 1.35, 0)
    for side in [-1, 1]:
        frame.box(w, side * 0.75, 30.7, 0.055, 1.705, 0.08, 0.715)
    for z in [29.875, 31.525]:
        frame.box(w, 0, z, 1.555, 0.055, 0.08, 0.715)

    # A dark, shallow hip replaces the old flat pale coping. Pitch is photo estimated.
    def point(x, d, z):
        return c + u * x + n * d + Vector((0, 0, z - 30.7))

    outer = [
        point(x, d, 31.925)
        for x, d in [(-1.025, -0.74), (1.025, -0.74), (1.025, 0.74), (-1.025, 0.74)]
    ]
    ridge = [point(-0.775, 0, 32.18), point(0.775, 0, 32.18)]
    cap.add(
        outer + ridge, [(0, 1, 5, 4), (1, 2, 5), (2, 3, 4, 5), (3, 0, 4), (3, 2, 1, 0)]
    )
wall.extra = [bpy.data.materials["61A_stone"]]
cap.extra = [bpy.data.materials["61A_trim"]]
assert sum(w["retainedCorner"] for w in windows) == 2
owned = [wall.finish(), cap.finish(), frame.finish()]
assert len(windows) == 26
probes = []
for w in windows:
    if w["retainedCorner"]:
        probes.append(
            {"index": w["index"], "kind": "retainedCornerCheek", "x": 0.87, "z": 30.7}
        )
        probes.append(
            {"index": w["index"], "kind": "retainedCornerCap", "x": 0, "z": 31.98}
        )
        continue
    for x in [-0.35, 0.35]:
        probes.append({"index": w["index"], "kind": "glass", "x": x, "z": 30.7})
    for x in [-0.87, 0.87]:
        probes.append({"index": w["index"], "kind": "cheek", "x": x, "z": 30.7})
    probes.append({"index": w["index"], "kind": "cap", "x": 0, "z": 32.04})
    probes.append({"index": w["index"], "kind": "retainedFacade", "x": 0.2, "z": 23.9})


def visible():
    return [
        o
        for o in collection.all_objects
        if o.type == "MESH" and len(o.data.vertices) and not o.hide_render
    ]


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
    out = []
    for p in probes:
        w = windows[p["index"]]
        start = (
            w["centre"] + w["u"] * p["x"] + w["n"] * 4 + Vector((0, 0, p["z"] - 30.7))
        )
        h = tree.ray_cast(start, -w["n"], 7)
        out.append({**p, "firstObject": names[h[2]] if h[2] is not None else None})
    return out


before = cast([o for o in visible() if o not in owned])
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
after = cast(visible())
for p in after:
    if p["kind"] == "glass":
        assert p["firstObject"] == "61A_D5_roof_window_glass", p
    elif p["kind"] == "cheek":
        assert p["firstObject"] == NAMES[0], p
    elif p["kind"] == "cap":
        assert p["firstObject"] == NAMES[1], p
aliases = dict(zip(NAMES, SOURCES))
assert [p for p in before if p["kind"].startswith("retained")] == [
    {**p, "firstObject": aliases.get(p["firstObject"], p["firstObject"])}
    for p in after
    if p["kind"].startswith("retained")
]
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in SOURCES
)
component = OUT / "aldwych-envelope-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)


def pbr(m):
    p = m.node_tree.nodes["Principled BSDF"]
    return {
        "name": m.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "roughness": p.inputs["Roughness"].default_value,
        "metallic": p.inputs["Metallic"].default_value,
        "transmission": p.inputs["Transmission Weight"].default_value,
        "alpha": p.inputs["Alpha"].default_value,
    }


photo = (
    ROOT
    / "data/建筑图片/61A_61 Aldwych/01_建筑实拍/campus_photos_round2_61A_aldwych_survey_01.jpg"
)
audit = {
    "baseline": str(BASE),
    "baselineSha256": BASE_SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": NAMES,
    "archivedObjects": SOURCES,
    "archiveObjects": SOURCES,
    "changes": [
        {"source": s, "owned": n, "action": a}
        for s, n, a in zip(
            SOURCES,
            NAMES,
            [
                "Replace solid pale blocks with dark four-sided cheeks and genuine full-depth window apertures",
                "Replace flat pale coping with shallow dark hipped caps",
            ],
        )
    ]
    + [
        {
            "source": None,
            "owned": NAMES[2],
            "action": "Add dark perimeter joinery around retained glazing",
        }
    ],
    "references": [
        {
            "local": str(photo),
            "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
            "url": "https://www.walshandassociates.co.uk/projects",
            "captureDate": "unknown",
            "supports": "Both visible street wings show dark roof dormer cheeks and shallow pitched dark hats, not full pale stone cubes.",
        }
    ],
    "dimensions": {
        "dormerCountInherited": 26,
        "wingDormersCorrected": 24,
        "stoneCornerDormersRetained": 2,
        "outerWidth": 1.95,
        "outerHeight": 2.45,
        "originalOpeningRetained": [1.5, 1.65],
        "capBase": 31.925,
        "capRidge": 32.18,
        "method": "Existing native bay positions and dimensions retained; cap rise0.255m estimated from shallow cap proportions in undated survey photo. Not a measured survey.",
    },
    "materials": {
        "originalBody": pbr(bpy.data.objects[SOURCES[0]].data.materials[0]),
        "originalCap": pbr(bpy.data.objects[SOURCES[1]].data.materials[0]),
        "newBodyAndCap": pbr(slate),
        "newPerimeterFrames": pbr(bronze),
        "glazingUnchanged": True,
    },
    "beforeProbes": before,
    "afterProbes": after,
    "wholeFacadeReview": {
        "lower": "Accepted137 portal and64 continuous piers/spandrels retained; photo supports their overall stone/dark recess arrangement. Ground obscured by trees outside corner.",
        "upper": "Ordinary upper stone window rows and balcony remain; this component corrects the full model roof dormer family.",
        "corner": "Accepted63 octagonal pavilion, pyramid and finial retained.",
        "roof": "Main flat roof29.5m remains provisional; tall stone roofline interruption slabs/chimneys visible in photograph not yet registered.",
        "rear": "Unseen elevations and interior unchanged.",
    },
    "limitations": [
        "Photo capture date unknown; not proof of2026 conversion condition.",
        "Inherited26 dormer positions/count not independently verified from perspective photo; dark finish and cap morphology are photo supported.",
        "No newly invented rooms or glass backing; original glass PBR unchanged.",
        "Main roof height/coverage, roofline stone interruption positions and upper stone ornament remain unresolved.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["61A_EXTERIOR"]
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = NAMES
for o in dst.objects:
    collection.objects.link(o)
    for i, m in enumerate(o.data.materials):
        original = (
            bpy.data.materials.get(m.name.rsplit(".", 1)[0])
            if m.name[-3:].isdigit()
            else m
        )
        if original:
            o.data.materials[i] = original
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
assert cast(visible()) == after
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in SOURCES
)
verification = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "originalObjectCount": len(originals),
    "reloadedProbes": after,
    "dormers": 24,
    "cornerDormersRetained": 2,
    "retainedFacadeProbesUnchanged": True,
    "nativeRender": "reloaded-aldwych-envelope.png",
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type == "MESH" and o.name not in members:
        o.hide_render = True
ps = [o.matrix_world @ v.co for o in visible() for v in o.data.vertices]
focus = Vector(
    (
        (min(p.x for p in ps) + max(p.x for p in ps)) / 2,
        (min(p.y for p in ps) + max(p.y for p in ps)) / 2,
        19,
    )
)
camera = bpy.data.cameras.new("61A_NEXT_ENVELOPE_review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = focus + Vector((-95, -105, 55))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 105
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-aldwych-envelope.png")
bpy.ops.render.render(write_still=True)
print("ALDWYCH_ENVELOPE_VERIFIED", len(originals), len(after), flush=True)
bpy.ops.wm.quit_blender()
