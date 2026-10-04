"""Clear 51Ledge3stone voussoirs from the registered black arched frame.
Use Blender Text Editor. Preserve the actual seven openings and all unknown faces.
"""

from pathlib import Path
import array, hashlib, json, math, bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lincoln51_arch_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v149.blend"
EXPECTED = "9057f87e47163c1d900d1365ce08315e24193f7443fbe915b9e43833eb05704e"
SOURCE = "51L_D5_threebay92_retained_V20_EXT_stone_arch_voussoirs_stone"
NAME = "51L_NEXT_ARCH_CLEARANCE_voussoirs"
FRAME = "51L_D5_threebay92_retained_V20_EXT_arched_window_frame_metal"
GLASS = "51L_D5_threebay92_retained_V20_EXT_arched_fanlight_glass"
COMPONENT = OUT / "lincoln51-arch-clearance-component.blend"
PREVIOUS = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else {}
)
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    o = bpy.data.objects.get(NAME)
    if o:
        mesh = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        mesh.use_fake_user = False
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    o = bpy.data.objects[SOURCE]
    state = PREVIOUS.get("originalVisibility", {}).get(SOURCE, [False, False, False])
    o.hide_render, o.hide_viewport = state[:2]
    o.hide_set(state[2])
    for layer in bpy.context.scene.view_layers:
        layer.update()


open_base()


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, n in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            ar = array.array(kind, [0]) * (len(data) * n)
            data.foreach_get(field, ar)
            h.update(ar.tobytes())
        for uv in o.data.uv_layers:
            ar = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", ar)
            h.update(ar.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
if BASE.stem.endswith("v149"):
    assert len(originals) == 5857
inspection = json.loads((OUT / "boundary-inspection.json").read_text())
reg = {
    key: value for key, value in inspection["registration"].items() if key != "pitch"
}
# Seven measured native glass-island centres/radii below drive every geometric edit.
windows = inspection["windows"]
a = Vector(reg["origin"])
u = Vector(reg["axis"])
n = Vector(reg["normal"])
collection = bpy.data.collections["51L_EXTERIOR"]


def world(x, d, z):
    return a + u * x + n * d + Vector((0, 0, z))


def local(p):
    return Vector(((p - a).dot(u), (p - a).dot(n), p.z))


source = bpy.data.objects[SOURCE]
copy = source.copy()
copy.data = source.data.copy()
copy.name = NAME
collection.objects.link(copy)
adj = {v.index: set() for v in copy.data.vertices}
for e in copy.data.edges:
    x, y = e.vertices
    adj[x].add(y)
    adj[y].add(x)
seen = set()
groups = []
moved = []
unchangedOuter = []
for seed in copy.data.vertices:
    if seed.index in seen:
        continue
    todo = [seed.index]
    seen.add(seed.index)
    ids = []
    while todo:
        i = todo.pop()
        ids.append(i)
        for j in adj[i]:
            if j not in seen:
                seen.add(j)
                todo.append(j)
    assert len(ids) == 8
    pts = [local(copy.matrix_world @ copy.data.vertices[i].co) for i in ids]
    centre = sum(pts, Vector()) / 8
    bay = min(range(7), key=lambda j: abs(windows[j]["centreX"] - centre.x))
    w = windows[bay]
    radial = Vector((centre.x - w["centreX"], 0, centre.z - w["spring"])).normalized()
    projections = [
        Vector((p.x - w["centreX"], 0, p.z - w["spring"])).dot(radial) for p in pts
    ]
    lo = min(projections)
    hi = max(projections)
    # Derive actual frame outer radius from existing vertices on this registered window, not a nominal3baywidth.
    frame = bpy.data.objects[FRAME]
    rhos = []
    for v in frame.data.vertices:
        p = local(frame.matrix_world @ v.co)
        if (
            abs(p.x - w["centreX"]) < w["radius"] + 0.05
            and w["spring"] - 0.001 <= p.z <= w["top"] + 0.05
        ):
            rhos.append(math.hypot(p.x - w["centreX"], p.z - w["spring"]))
    outer = max(rhos)
    target = outer + 0.008
    delta = max(0, target - lo)
    assert delta < 0.09, (bay, delta)
    changed = []
    for i, p, projection in zip(ids, pts, projections):
        if projection < lo + 0.00002:
            q = p + radial * delta
            copy.data.vertices[i].co = copy.matrix_world.inverted() @ world(
                q.x, q.y, q.z
            )
            changed.append(i)
            moved.append(i)
        else:
            unchangedOuter.append(i)
    assert len(changed) == 4
    groups.append(
        {
            "bay": bay,
            "vertices": ids,
            "innerVertices": changed,
            "originalInnerPlaneRadius": lo,
            "frameOuterRadius": outer,
            "newInnerPlaneRadius": target,
            "outwardMoveM": delta,
        }
    )
copy.data.update()
assert len(groups) == 91 and len(moved) == 364
assert all(
    tuple(copy.data.vertices[i].co) == tuple(source.data.vertices[i].co)
    for i in unchangedOuter
)
assert [[tuple(d.uv) for d in uv.data] for uv in copy.data.uv_layers] == [
    [tuple(d.uv) for d in uv.data] for uv in source.data.uv_layers
]
probes = []
for bay, w in enumerate(windows):
    for j in range(1, 40):
        t = math.pi * j / 40
        x = w["centreX"] + w["radius"] * math.cos(t)
        z = w["spring"] + w["radius"] * math.sin(t)
        probes.append(
            {
                "kind": "frameClearance",
                "bay": bay,
                "origin": list(world(x, 0.8, z)),
                "expected": [
                    FRAME,
                    "51L_D5_threebay92_retained_V20_EXT_window_mullion_metal",
                ]
                if j == 20
                else FRAME,
            }
        )
    for dx in [-0.15, 0.15]:
        for z in [2.56, 2.92]:
            probes.append(
                {
                    "kind": "retainedArchGlass",
                    "bay": bay,
                    "origin": list(world(w["centreX"] + dx, 0.8, z)),
                    "expected": GLASS,
                }
            )
    # Stone joint and outside face retain actual material/coverage.
    x = w["centreX"]
    z = w["spring"] + w["radius"] + 0.12
    probes.append(
        {
            "kind": "retainedOuterStone",
            "bay": bay,
            "origin": list(world(x, 0.8, z)),
            "expected": None,
        }
    )


def cast(exclude=(), evaluated=False):
    vertices = []
    faces = []
    owners = []
    indices = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in collection.all_objects:
        if o.type != "MESH" or o.hide_render or o.name in exclude:
            continue
        ob = o.evaluated_get(dg) if evaluated else o
        mesh = ob.to_mesh() if evaluated else ob.data
        k = len(vertices)
        vertices.extend(ob.matrix_world @ v.co for v in mesh.vertices)
        faces.extend(tuple(k + i for i in f.vertices) for f in mesh.polygons)
        owners.extend([o.name] * len(mesh.polygons))
        indices.extend(f.index for f in mesh.polygons)
        if evaluated:
            ob.to_mesh_clear()
    tree = BVHTree.FromPolygons(vertices, faces)
    rows = []
    for p in probes:
        h = tree.ray_cast(Vector(p["origin"]), -n, 1.2)
        name = owners[h[2]] if h[2] is not None else None
        rows.append(
            {
                **p,
                "firstObject": name,
                "face": indices[h[2]] if h[2] is not None else None,
                "point": list(h[0]) if h[0] is not None else None,
            }
        )
    return rows


before = cast([NAME])
source.hide_render = True
source.hide_set(True)
after = cast()
evalAfter = cast(evaluated=True)
for row in after + evalAfter:
    if row["expected"]:
        assert (
            row["firstObject"] in row["expected"]
            if isinstance(row["expected"], list)
            else row["firstObject"] == row["expected"]
        ), row
    else:
        assert row["firstObject"] == NAME, row
for row in before:
    if row["kind"] == "retainedArchGlass":
        assert row["firstObject"] == GLASS, row
assert (
    sum(p["firstObject"] == SOURCE for p in before if p["kind"] == "frameClearance")
    > 200
)


def preserved():
    assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
    assert all(
        [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
        for o in bpy.data.objects
        if o.name in originals and o.name != SOURCE
    )


preserved()
bpy.data.libraries.write(str(COMPONENT), {copy}, fake_user=True, compress=True)
refs = []
for p, date in [
    (
        ROOT
        / "data/建筑图片/51L_51 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_015.jpg",
        "Official LSE;capture unknown",
    ),
    (
        ROOT / "data/collections/lincolns-frontage-review/51l-gsos-2025.jpg",
        "LSEGSOS2025-07-31publication;capture unknown",
    ),
]:
    refs.append(
        {
            "path": str(p),
            "date": date,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "evidence": "Stone semicircular surround lies outside continuous black arched window frame, no jagged stone tabs within black ring.",
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": SHA,
    "ownedObjects": [NAME],
    "archivedObjects": [SOURCE],
    "archiveObjects": [SOURCE],
    "changes": [
        {
            "source": SOURCE,
            "owned": NAME,
            "action": "Move only91voussoir inner planes outside measured7blackframeouterradii+estimated8mm joint;364innervertices moved,364outervertices unchanged, alltopologyUVslots retained",
        }
    ],
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "registration": reg,
    "windows": windows,
    "voussoirGroups": groups,
    "beforeProbes": before,
    "afterProbes": after,
    "evaluatedAfterProbes": evalAfter,
    "references": refs,
    "material": "Original EXT20_stone and bevel modifier preserved, no material change",
    "limitations": [
        "No absolute facade survey; original window centres/radii retained.8mm stone/frame clearance is a modeling tolerance estimate informed by photograph relationship.",
        "7existingedge3openings retained; edge1threebayashlar,148door glass, allupper/rear/roof surfaces unmodified.",
        "No enlarged wholewall opening or fictitious interior; actual aperture主体wasclearbefore.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["51L_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = [NAME]
for o in dst.objects:
    collection.objects.link(o)
bpy.data.objects[SOURCE].hide_render = True
bpy.data.objects[SOURCE].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
reloaded = cast()
reloadedEval = cast(evaluated=True)
assert reloaded == after and reloadedEval == evalAfter
preserved()
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type not in {"LIGHT", "CAMERA"} and o.name not in members:
        o.hide_render = True
focus = world(reg["length"] / 2, 0, 2.0)
camdata = bpy.data.cameras.new(NAME + "_review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + n * 25 + u * 2 + Vector((0, 0, 1))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 21
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1300
scene.render.resolution_y = 650
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-edge3-arches.png")
bpy.ops.render.render(write_still=True)
v = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA,
    "reloadedProbes": reloaded,
    "reloadedEvaluatedProbes": reloadedEval,
    "probeCount": len(reloaded),
    "render": "reloaded-edge3-arches.png",
    "camera": list(cam.location),
    "target": list(focus),
}
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print(
    "51L_ARCH_CLEARANCE_VERIFIED", len(originals), len(reloaded), v["componentSha256"]
)
bpy.ops.wm.quit_blender()
