"""Update photographed Lincoln Chambers shopfront details from official May2025 reference.
Use Blender Text Editor. Retain obscured right basement and all upper/roof geometry.
"""

from pathlib import Path
import array, hashlib, json, bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lch_exterior148"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v147.blend"
EXPECTED = "02607a215a50db6fb0807091000c271e93a1686d035e9512fe565acd1de30e6a"
PREFIX = "LCH_NEXT_EXTERIOR148_"
ARCHIVE = [
    "LCH_D5_V43_basement_" + s
    for s in ["glass_glass", "splayed_surround_frame", "rails_frame", "grid_metal"]
] + ["LCH_D5_V42_shop_upper_lights_frame", "LCH_D5_V42_sash_rail_frame"]
NAMES = [
    PREFIX + s
    for s in [
        "retained_right_basement_glass",
        "retained_right_basement_surround",
        "retained_right_basement_rails",
        "retained_right_basement_grid",
        "shop_upper_grid",
        "retained_sash_rails",
        "left_white_lower_panel",
    ]
]
COMPONENT = OUT / "lincoln-chambers-exterior148-component.blend"
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
    for name in NAMES:
        o = bpy.data.objects.get(name)
        if o:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for name in ARCHIVE:
        o = bpy.data.objects[name]
        state = PREVIOUS.get("originalVisibility", {}).get(name, [False, False, False])
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
if BASE.stem.endswith("v147"):
    assert len(originals) == 5829
collection = bpy.data.collections["LCH_EXTERIOR"]
transom = bpy.data.objects["LCH_D5_V42_shop_transom_frame"]
ps = [transom.matrix_world @ v.co for v in transom.data.vertices]
c0 = sum(ps[:8], Vector()) / 8
c1 = sum(ps[8:], Vector()) / 8
u = (c1 - c0).normalized()
n = Vector((-u.y, u.x, 0))
a = c0.copy()
a.z = 0
rightX = (c1 - c0).length


def world(x, d, z):
    return a + u * x + n * d + Vector((0, 0, z))


def local(p):
    return Vector(((p - a).dot(u), (p - a).dot(n), p.z))


x0 = min(local(p).x for p in ps[:8])
x1 = max(local(p).x for p in ps[:8])
owned = []
changes = []


def box(mesh, xlo, xhi, dlo, dhi, zlo, zhi, matrix):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    pts = [
        world(x, d, z)
        for x, d, z in [
            (xlo, dlo, zlo),
            (xlo, dlo, zhi),
            (xlo, dhi, zlo),
            (xlo, dhi, zhi),
            (xhi, dlo, zlo),
            (xhi, dlo, zhi),
            (xhi, dhi, zlo),
            (xhi, dhi, zhi),
        ]
    ]
    vs = [bm.verts.new(matrix.inverted() @ p) for p in pts]
    for ids in [
        (0, 4, 6, 2),
        (1, 3, 7, 5),
        (0, 1, 5, 4),
        (2, 6, 7, 3),
        (0, 2, 3, 1),
        (4, 5, 7, 6),
    ]:
        bm.faces.new([vs[i] for i in ids])
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()


for index, (sourceName, newName) in enumerate(zip(ARCHIVE, NAMES)):
    source = bpy.data.objects[sourceName]
    o = source.copy()
    o.data = source.data.copy()
    o.name = newName
    collection.objects.link(o)
    if index < 4:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        delete = [v for v in bm.verts if local(o.matrix_world @ v.co).x > rightX / 2]
        bmesh.ops.delete(bm, geom=delete, context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        action = "Remove only left basement detail covered by 2025 continuous white lower panel; right vertices/topology/UV and slots retained"
    elif index == 4:
        for x in [0, rightX]:
            box(o.data, x + x0, x + x1, -0.04, 0.04, 3.025, 3.055, o.matrix_world)
        action = "Add missing middle horizontal glazing bar to existing 12 columns per side: three bays each with2x4 high-level panes"
    else:
        bm = bmesh.new()
        bm.from_mesh(o.data)
        delete = [v for v in bm.verts if 2.14 < (o.matrix_world @ v.co).z < 2.23]
        assert len(delete) == 16, len(delete)
        bmesh.ops.delete(bm, geom=delete, context="VERTS")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        action = "Remove only two incorrect ground shop main-glazing middle sash rails at2.185m;2025and2022photos show continuous tall glass. All31other rail cuboids and UV preserved"
    owned.append(o)
    changes.append({"source": sourceName, "owned": newName, "action": action})
mesh = bpy.data.meshes.new(NAMES[6] + "_mesh")
panel = bpy.data.objects.new(NAMES[6], mesh)
collection.objects.link(panel)
mesh.materials.append(bpy.data.materials["LCH_V42_frame"])
box(mesh, rightX + x0, rightX + x1, 0.075, 0.215, 0.025, 1.02, Matrix.Identity(4))
owned.append(panel)
changes.append(
    {
        "source": None,
        "owned": panel.name,
        "action": "Continuous solid left white panel over registered former basement band; thickness0.14m and height1.02m estimated from official2025 image, no claim for obscured right side",
    }
)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
probes = []
for x in [rightX + x0 + 0.3, rightX, rightX + x1 - 0.3]:
    for z in [0.25, 0.70, 0.90]:
        probes.append({"kind": "leftLowerPanel", "x": x, "z": z, "expected": NAMES[6]})
for x in [-1.65 + 0.25, 0.25, 1.65 + 0.25]:
    probes.append(
        {"kind": "retainedRightBasement", "x": x, "z": 0.6, "expected": NAMES[0]}
    )
probes.append({"kind": "retainedRightGrid", "x": 0, "z": 0.6, "expected": NAMES[3]})
for cx in [0, rightX]:
    for dx in [-1.4, -0.6, 0.6, 1.4]:
        probes.append(
            {
                "kind": "correctedTallShopGlass",
                "x": cx + dx,
                "z": 2.185,
                "expected": "LCH_D5_V42_window_glass_glass",
            }
        )
    for dx in [-1.4, -0.6, 0.6, 1.4]:
        probes.append(
            {"kind": "newMiddleRail", "x": cx + dx, "z": 3.04, "expected": NAMES[4]}
        )
        for z in [2.91, 3.20]:
            probes.append(
                {
                    "kind": "retainedUpperGlass",
                    "x": cx + dx,
                    "z": z,
                    "expected": "LCH_D5_V42_window_glass_glass",
                }
            )


def cast():
    vs = []
    fs = []
    owners = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.hide_render or not o.data.polygons:
            continue
        pts = [o.matrix_world @ Vector(p) for p in o.bound_box]
        if min((p - a).length for p in pts) > 35:
            continue
        k = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        fs.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
    tree = BVHTree.FromPolygons(vs, fs)
    rows = []
    for p in probes:
        h = tree.ray_cast(world(p["x"], 0.8, p["z"]), -n, 1.8)
        name = owners[h[2]] if h[2] is not None else None
        row = {**p, "firstObject": name, "point": list(h[0]) if h[0] else None}
        rows.append(row)
        assert name == p["expected"], row
    return rows


def preserved():
    assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
    assert all(
        [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
        for o in bpy.data.objects
        if o.name in originals and o.name not in ARCHIVE
    )


rows = cast()
preserved()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
refs = []
for file, date in [
    (
        "lse-volunteer-may2025.jpg",
        "FilenameMay2025; official LSE article2025-09-22; EXIF unverified",
    ),
    ("ian-wood-2022.jpg", "IanWood2022-08-21; historical comparison only"),
]:
    p = ROOT / "data/collections/lincoln-review" / file
    refs.append(
        {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "date": date,
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": list(NAMES),
    "archivedObjects": list(ARCHIVE),
    "archiveObjects": list(ARCHIVE),
    "changes": changes,
    "references": refs,
    "registration": {
        "origin": list(a),
        "axis": list(u),
        "normal": list(n),
        "rightStoreCentreX": 0,
        "leftStoreCentreX": rightX,
        "leftBandX": [rightX + x0, rightX + x1],
        "panelZ": [0.025, 1.02],
        "panelDepth": [0.075, 0.215],
    },
    "probes": rows,
    "evidence": [
        "2025 official left store has continuous pale lower panel from pavement to main glazing sill; no basement grilles are visible across that full band.",
        "2022 records exposed three left basement lights; superseded for this visible left band. Right2025lower band obscured by people and unchanged.",
        "Both2022and2025main tall store panes lack the erroneous ground sash middle rail; removed only those2rails. Both2022and2025images show middle horizontal bar in each store high-level glazing, absent in native. Existing11verticalbars per store already form12columns and retained.",
    ],
    "materials": "Inherited white LCH_V42_frame PBR; no glass material changes",
    "wholeExteriorReview": "Central Diocletian window, upper tripartite window and canted end bays already modelled. Roof dormers described by official listing but current photo registration unavailable.",
    "newEvidence": {
        "url": "https://historicengland.org.uk/listing/the-list/list-entry/1227132",
        "listDate": "1987-12-01",
        "relevance": "Confirms3storeys+attic,7windows,stone ground and specified upper windows; mentions roof dormers but no metric locations. Not a current measured survey.",
    },
    "limitations": [
        "Photo-derived lower panel extent/depth and rail0.03m height estimated; inherited window geometry remains estimated.",
        "Roof dormer positions/heights and unseen elevations not reconstructed.",
        "Store internal layout and furnishings not inferred; optical glazing unchanged in this component.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["LCH_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(NAMES)
for o in dst.objects:
    collection.objects.link(o)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
reloaded = cast()
assert rows == reloaded
preserved()
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type not in {"LIGHT", "CAMERA"} and o.name not in members:
        o.hide_render = True
focus = world(rightX / 2, 0, 6.5)
camdata = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + n * 30 + u * 0.3 + Vector((0, 0, 1))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 20
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-lch-frontage.png")
bpy.ops.render.render(write_still=True)
v = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA,
    "reloadedProbes": reloaded,
    "render": "reloaded-lch-frontage.png",
    "camera": list(cam.location),
    "target": list(focus),
}
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print("LCH148_VERIFIED", len(originals), len(reloaded), v["componentSha256"])
bpy.ops.wm.quit_blender()
