"""Restore the photographed four-light stone-cross rhythm on SAL's upper frontage.
Run in Blender with constant configuration; writes a component library only.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/sal_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v138.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
PREFIX = "SAL_NEXT_ENVELOPE_"
ARCHIVES = ["SAL_Window_stone_mullions", "SAL_NEXT_middle_sash_bars"]
A = math.radians(24.35)
U = Vector((-math.cos(A), -math.sin(A), 0))
N = Vector((-math.sin(A), math.cos(A), 0))
O = Vector((120.73, 121.65, 0))
WINDOWS = [
    (x, z, h)
    for x in [-16.75, -12, -7.25, 7.25, 12, 16.75]
    for z, h in [(7.3, 3.45), (11.65, 3.35), (15.85, 3.35)]
]
W = 3.42
TRANSOM_RATIO = 0.58
TRANSOM_HEIGHT = 0.12
PHOTO = ROOT / "data/collections/library_round5/photos/SAL_d0d696021ed0.jpg"


def point(x, d, z):
    return O + U * x + N * d + Vector((0, 0, z))


def local(p):
    q = p - O
    return q.dot(U), q.dot(N), p.z


def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, count in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            v = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, v)
            h.update(v.tobytes())
        for layer in o.data.uv_layers:
            v = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", v)
            h.update(v.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    previous = (
        json.loads((OUT / "audit.json").read_text())
        if (OUT / "audit.json").exists()
        else None
    )
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    if previous:
        for name in previous["archivedObjects"]:
            o = bpy.data.objects[name]
            state = previous["originalVisibility"][name]
            o.hide_render, o.hide_viewport = state[:2]
            o.hide_set(state[2])
    return bpy.context.scene, bpy.data.collections["SAL_EXTERIOR"]


scene, col = open_baseline()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
owned = []
removed = {}
for source, suffix, expected in [
    (ARCHIVES[0], "retained_stone_mullions", 36),
    (ARCHIVES[1], "retained_sash_bars", 216),
]:
    old = bpy.data.objects[source]
    new = old.copy()
    new.data = old.data.copy()
    new.name = PREFIX + suffix
    col.objects.link(new)
    for m in list(new.modifiers):
        if m.type == "BEVEL":
            new.modifiers.remove(m)
    bm = bmesh.new()
    bm.from_mesh(new.data)
    bm.verts.ensure_lookup_table()
    visited = set()
    selected = []
    count = 0
    for seed in bm.verts:
        if seed in visited:
            continue
        stack = [seed]
        part = []
        visited.add(seed)
        while stack:
            v = stack.pop()
            part.append(v)
            for e in v.link_edges:
                q = e.other_vert(v)
                if q not in visited:
                    visited.add(q)
                    stack.append(q)
        coords = [local(new.matrix_world @ v.co) for v in part]
        center = [sum(p[k] for p in coords) / len(coords) for k in range(3)]
        match = next(
            (
                (x, z, h)
                for x, z, h in WINDOWS
                if abs(center[0] - x) < W / 2 - 0.1
                and abs(center[1] + 0.17) < 0.025
                and all(z - h / 2 - 0.002 < p[2] < z + h / 2 + 0.002 for p in coords)
            ),
            None,
        )
        if match:
            assert len(part) == 8, (source, len(part), center)
            selected.extend(part)
            count += 1
    assert count == expected, (source, count, expected)
    bmesh.ops.delete(bm, geom=selected, context="VERTS")
    bm.to_mesh(new.data)
    bm.free()
    new.data.update()
    removed[source] = count
    owned.append(new)
    old.hide_render = True
    old.hide_set(True)


def geometry(name, material, boxes):
    verts = []
    faces = []
    for x, d, z, w, t, h in boxes:
        offset = len(verts)
        verts.extend(
            point(x + sx * w / 2, d + sy * t / 2, z + sz * h / 2)
            for sx, sy, sz in [
                (-1, -1, -1),
                (-1, -1, 1),
                (-1, 1, -1),
                (-1, 1, 1),
                (1, -1, -1),
                (1, -1, 1),
                (1, 1, -1),
                (1, 1, 1),
            ]
        )
        faces.extend(
            tuple(offset + k for k in f)
            for f in [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ]
        )
    mesh = bpy.data.meshes.new(PREFIX + name)
    mesh.from_pydata(verts, [], faces)
    mesh.materials.append(material)
    mesh.update()
    uv = mesh.uv_layers.new(name="SurfaceUV")
    for f in mesh.polygons:
        p = [mesh.vertices[k].co for k in f.vertices]
        axis = (p[1] - p[0]).normalized()
        vertical = f.normal.cross(axis)
        for i, v in zip(f.loop_indices, p):
            uv.data[i].uv = ((v - p[0]).dot(axis), (v - p[0]).dot(vertical))
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    col.objects.link(obj)
    owned.append(obj)
    return obj


stone = []
blue = []
for x, z, h in WINDOWS:
    cross = z - h / 2 + h * TRANSOM_RATIO
    stone.extend((x - W / 2 + W * k / 4, -0.17, z, 0.15, 0.40, h) for k in [1, 2, 3])
    stone.append((x, -0.17, cross, W, 0.40, TRANSOM_HEIGHT))
    for k in range(4):
        mid = x - W / 2 + W * (k + 0.5) / 4
        blue.append((mid, -0.18, z, 0.035, 0.11, h))
        for j in [1, 2, 3]:
            blue.append((mid, -0.18, z - h / 2 + h * j / 4, W / 4 - 0.15, 0.11, 0.033))
geometry("four_light_stone", bpy.data.objects[ARCHIVES[0]].data.materials[0], stone)
geometry("four_light_blue", bpy.data.objects[ARCHIVES[1]].data.materials[0], blue)
OWNED = [o.name for o in owned]


def probes():
    trees = [
        (
            o,
            BVHTree.FromPolygons(
                [o.matrix_world @ v.co for v in o.data.vertices],
                [tuple(f.vertices) for f in o.data.polygons],
                all_triangles=False,
            ),
        )
        for o in col.all_objects
        if o.type == "MESH" and not o.hide_render and len(o.data.polygons)
    ]
    records = []
    for index, (x, z, h) in enumerate(WINDOWS):
        cross = z - h / 2 + h * TRANSOM_RATIO
        samples = [
            (
                "stone-mullion",
                x - W / 2 + W * k / 4,
                z + h * 0.10,
                PREFIX + "four_light_stone",
            )
            for k in [1, 2, 3]
        ]
        samples += [("stone-cross", x - W * 0.31, cross, PREFIX + "four_light_stone")]
        samples += [
            (
                "clear-light",
                x - W / 2 + W * (k + 0.30) / 4,
                z + h * f,
                "SAL_Window_glazing",
            )
            for k in range(4)
            for f in [-0.36, 0.36]
        ]
        samples += [
            ("former-mullion", x + s * 0.57, z + h * 0.10, "SAL_Window_glazing")
            for s in [-1, 1]
        ]
        for kind, px, pz, expected in samples:
            start = point(px, 1, pz)
            best = None
            for o, tree in trees:
                hit = tree.ray_cast(start, -N, 3)
                if hit[0] is not None and (best is None or hit[3] < best[0]):
                    best = (hit[3], o.name)
            assert best and best[1] == expected, (index, kind, px, pz, best, expected)
            records.append(
                {
                    "window": index,
                    "kind": kind,
                    "localPoint": [px, 1, pz],
                    "firstSurface": best[1],
                }
            )
    return records


checks = probes()
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
component = OUT / "sal-envelope-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True)
audit = {
    "baseline": str(BASE.relative_to(ROOT)),
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": OWNED,
    "archivedObjects": ARCHIVES,
    "changes": [
        {
            "source": ARCHIVES[0],
            "owned": OWNED[0],
            "action": "Retain all stone mullions except36 internal posts across18 upper main windows.",
        },
        {
            "source": ARCHIVES[1],
            "owned": OWNED[1],
            "action": "Retain all blue/charcoal/pale bars except216 three-light internal bars in the same18 openings.",
        },
        {
            "source": None,
            "owned": OWNED[2],
            "action": "Add54 front stone mullions and18 continuous stone transoms.",
        },
        {
            "source": None,
            "owned": OWNED[3],
            "action": "Rebuild four-light fine blue sash joinery in the18 registered openings.",
        },
    ],
    "removedConnectedBoxes": removed,
    "windowRegistration": WINDOWS,
    "reference": {
        "path": str(PHOTO.relative_to(ROOT)),
        "sha256": hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
        "sourceUrl": "https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/",
        "captureDate": "unknown",
        "projectYear": 2012,
    },
    "evidence": "Built oblique photo clearly shows four vertical glazed lights with three pale exterior stone posts and a continuous pale stone cross at each of six broad bays across three upper floors. Posts and cross join exterior surrounds and cast exterior shadows; they are not interior reflected bars.",
    "estimates": {
        "openingWidth": W,
        "stoneMullionWidth": 0.15,
        "stoneTransomHeight": TRANSOM_HEIGHT,
        "transomHeightRatioFromSill": TRANSOM_RATIO,
        "dimensionStatus": "Visual estimates using inherited openings; not measured elevation. Existing stone and blue colors preserved.",
        "clearAreaFractionWithoutPerimeter": round(
            (W - 0.45) / W * (3.35 - 0.12) / 3.35, 3
        ),
    },
    "preserved": [
        "Ground row, central oriel, narrow bays, tower and attic",
        "Side alley charcoal/pale frames and bars outside18 openings",
        "Every original mesh, matrix, UV and material slot; glazing shader and glazing geometry",
    ],
    "limitations": [
        "Ground row obscured by trees/fence is unchanged.",
        "Precise cross height and stone profiles estimated; photograph date unknown.",
        "Unseen elevations and interior remain unchanged.",
    ],
    "firstSurfaceChecks": checks,
}
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
scene, col = open_baseline()
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = src.objects
for o in dst.objects:
    col.objects.link(o)
    for slot in o.material_slots:
        m = slot.material
        if m and "." in m.name and m.name.rsplit(".", 1)[1].isdigit():
            canonical = bpy.data.materials.get(m.name.rsplit(".", 1)[0])
            if canonical:
                slot.material = canonical
for name in ARCHIVES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
reloaded = probes()
assert reloaded == checks
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
    if n not in ARCHIVES
)
proof = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalObjectCount": len(originals),
    "unrelatedVisibilityPreserved": True,
    "fullModelSaved": False,
    "firstSurfaceChecks": reloaded,
    "registeredWindowCount": 18,
    "checkCount": len(reloaded),
    "stoneFrontDepth": 0.03,
    "glassFrontDepth": -0.2925,
    "clearAreaFractionWithoutPerimeter": audit["estimates"][
        "clearAreaFractionWithoutPerimeter"
    ],
}
# One final native review; isolate SAL for useful exterior visibility.
visible = {o.name for o in col.all_objects}
for o in scene.objects:
    if o.type == "MESH" and o.name not in visible:
        o.hide_render = True
focus = point(0, 0, 15)
cd = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = focus + N * 85 + U * 6 + Vector((0, 0, 6))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 58
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "reloaded-frontage.png")
bpy.ops.render.render(write_still=True)
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("SAL_ENVELOPE_VERIFIED", len(originals), len(reloaded))
bpy.ops.wm.quit_blender()
