"""Open documented No.50 Lincoln street-glazing and retain muted bronze glass.
Run inside Blender. All metric frontage dimensions remain inherited estimates.
Only an owned component is written; original campus geometry is never modified.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/fifty_lincoln_glazing_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v146.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
COMPONENT = OUT / "fifty-lincoln-glazing-component.blend"
PREFIX = "50L_NEXT_GLAZING_"


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    prior = (
        json.loads((OUT / "audit.json").read_text())
        if (OUT / "audit.json").exists()
        else None
    )
    shared_prior = (
        json.loads((OUT / "shared-upper-audit.json").read_text())
        if (OUT / "shared-upper-audit.json").exists()
        else None
    )
    if prior and shared_prior:
        prior["ownedObjects"] += shared_prior["ownedObjects"]
        prior["archivedObjects"] += shared_prior["archivedObjects"]
    if prior:
        for name in prior.get("ownedObjects", []):
            o = bpy.data.objects.get(name)
            if o:
                mesh = o.data
                bpy.data.objects.remove(o, do_unlink=True)
                if not mesh.users:
                    bpy.data.meshes.remove(mesh)
        for name in prior.get("archivedObjects", []):
            o = bpy.data.objects[name]
            state = prior["originalVisibility"][name]
            o.hide_render, o.hide_viewport = state[:2]
            o.hide_set(state[2])
    for m in list(bpy.data.materials):
        if m.name.startswith(PREFIX) and not m.users:
            bpy.data.materials.remove(m)
    for sc in bpy.data.scenes:
        for layer in sc.view_layers:
            layer.update()


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, key, kind, w in (
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ):
            a = array.array(kind, [0]) * (len(data) * w)
            data.foreach_get(key, a)
            h.update(a.tobytes())
        for uv in o.data.uv_layers:
            a = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", a)
            h.update(a.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


def parts(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    seen = set()
    result = []
    for seed in bm.verts:
        if seed in seen:
            continue
        todo = [seed]
        seen.add(seed)
        group = []
        while todo:
            v = todo.pop()
            group.append(v.index)
            for e in v.link_edges:
                q = e.other_vert(v)
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        result.append(group)
    bm.free()
    return result


open_baseline()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
collection = bpy.data.collections["50L_EXTERIOR"]
frame = json.loads(
    (ROOT / "result/blender/stage72/fifty-lincoln-portal-audit.json").read_text()
)["frame"]
origin, u, n = map(Vector, (frame["origin"], frame["right"], frame["outward"]))


def point(x, d, z):
    return origin + u * x + n * d + Vector((0, 0, z))


def local(p):
    q = p - origin
    return Vector((q.dot(u), q.dot(n), p.z))


C = 2.1826
W = 1.112
LO = 0.235
HI = 2.628
A = 1.32565
B = 3.97695
STONE_TOP = 4.1
owned = []
sources = []
changes = []
removed = []
materials = []
GLASS_SOURCES = ["50L_D5_window_glass", "50L_D5_portal72_glass"]
glass_owned = {}


def selected(points):
    ps = [local(p) for p in points]
    return (
        min(p.x for p in ps) >= A - 0.004
        and max(p.x for p in ps) <= B + 0.004
        and min(p.z for p in ps) >= -0.005
        and max(p.z for p in ps) <= 3.8001
    )


for src in list(collection.all_objects):
    if src.type != "MESH" or src.hide_render:
        continue
    groups = parts(src.data)
    delete_ids = []
    trim_ids = []
    for ids in groups:
        ps = [src.matrix_world @ src.data.vertices[k].co for k in ids]
        ls = [local(p) for p in ps]
        if selected(ps):
            delete_ids += ids
        elif (
            min(p.x for p in ls) >= A - 0.004
            and max(p.x for p in ls) <= B + 0.004
            and 3.7999 <= min(p.z for p in ls) < STONE_TOP
            and max(p.z for p in ls) <= 4.3001
        ):
            trim_ids += ids
    if not delete_ids and not trim_ids and src.name not in GLASS_SOURCES:
        continue
    obj = src.copy()
    obj.data = src.data.copy()
    obj.name = PREFIX + "retained_" + src.name.removeprefix("50L_")
    obj.data.name = obj.name
    collection.objects.link(obj)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    for i in trim_ids:
        v = bm.verts[i]
        p = obj.matrix_world @ v.co
        if p.z < STONE_TOP:
            p.z = STONE_TOP
            v.co = obj.matrix_world.inverted() @ p
    if delete_ids:
        bmesh.ops.delete(bm, geom=[bm.verts[k] for k in delete_ids], context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    if not obj.data.vertices:
        raise AssertionError("Unexpected complete source deletion " + src.name)
    for mod in list(obj.modifiers):
        if mod.type == "BEVEL":
            obj.modifiers.remove(mod)
    owned.append(obj)
    sources.append(src)
    changes.append(
        {
            "source": src.name,
            "owned": obj.name,
            "action": (
                "Retain every non-target construction island; remove only registered50Aground-bay placeholder and trim header below4.1m"
                if delete_ids or trim_ids
                else "Retain exact No50fanlight geometry; adjust finite glass optics"
            ),
        }
    )
    removed.append(
        {
            "source": src.name,
            "removedVertexIndices": delete_ids,
            "trimmedVertexIndices": trim_ids,
        }
    )
    if src.name in GLASS_SOURCES:
        old = src.data.materials[0]
        mat = old.copy()
        mat.name = PREFIX + src.name + "_bounded_material"
        pr = next(p for p in mat.node_tree.nodes if p.type == "BSDF_PRINCIPLED")
        keys = [
            "Base Color",
            "Roughness",
            "Metallic",
            "Alpha",
            "Transmission Weight",
            "IOR",
        ]
        before = {
            k: (
                list(pr.inputs[k].default_value)
                if k == "Base Color"
                else pr.inputs[k].default_value
            )
            for k in keys
        }
        for k, v in [
            ("Alpha", 0.82),
            ("Transmission Weight", 0.22),
            ("Roughness", 0.26),
            ("Metallic", 0.12),
            ("IOR", 1.45),
        ]:
            pr.inputs[k].default_value = v
        mat.diffuse_color = tuple(old.diffuse_color[:3]) + (0.82,)
        mat["webOpacity"] = 0.82
        obj.data.materials.clear()
        obj.data.materials.append(mat)
        glass_owned[src.name] = obj
        materials.append(
            {
                "sourceMaterial": old.name,
                "ownedMaterial": mat.name,
                "before": before,
                "after": {
                    k: (
                        list(pr.inputs[k].default_value)
                        if k == "Base Color"
                        else pr.inputs[k].default_value
                    )
                    for k in keys
                },
                "webOpacity": 0.82,
            }
        )
assert len(parts(glass_owned[GLASS_SOURCES[0]].data)) == 10
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials as geometry_materials

geometry_materials.clear()
new_batches = {}


def mat(name, color, roughness):
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = m.diffuse_color
    p.inputs["Roughness"].default_value = roughness
    return m


geometry_materials["stone"] = mat(
    "50A_photographic_warm_stone", (0.43, 0.385, 0.30), 0.72
)
geometry_materials["red"] = mat(
    "50A_handbook_dark_blue_paint", (0.018, 0.035, 0.068), 0.43
)
geometry_materials["lamp"] = mat(
    "50A_opaque_external_light", (0.052, 0.048, 0.043), 0.40
)
geometry_materials["glass"] = glass_owned[GLASS_SOURCES[0]].data.materials[0]


def batch(key):
    if key not in new_batches:
        new_batches[key] = Geometry("50L", "50A_registered_" + key, key)
    return new_batches[key]


def box(key, x, d, z, w, t, h):
    batch(key).box(point(x, d, z), (w, t, h), math.atan2(u.y, u.x))


LEFT = C - W / 2
RIGHT = C + W / 2
# Actual entrance aperture is constructed from four surrounding wall pieces.
# It is not a flat red rectangle over the previous oversized window.
for a, b in [(A, LEFT), (RIGHT, B)]:
    box("stone", (a + b) / 2, 0.04, STONE_TOP / 2, b - a, 0.34, STONE_TOP)
for a, b in [(0, LO), (HI, STONE_TOP)]:
    box("stone", C, 0.04, (a + b) / 2, W, 0.34, b - a)
for side in [-1, 1]:
    box("red", C + side * (W - 0.10) / 2, -0.045, (LO + HI) / 2, 0.10, 0.10, HI - LO)
for z, h in [(LO + 0.055, 0.11), (HI - 0.08, 0.16), (1.045, 0.12)]:
    box("red", C, -0.045, z, W, 0.10, h)
box("red", C, -0.065, 0.665, W - 0.20, 0.08, 0.66)
# One photograph-supported upper rectangular light; paper notices not invented.
box("glass", C, -0.080, 1.807, W - 0.20, 0.035, 1.404)
# The round feature is an external lamp in its inherited circular surround,
# explicitly differentiated from49L's actual circular glazed opening.
LX, LZ = 2.3155, 3.5586
for j in range(48):
    a, b = j * math.tau / 48, (j + 1) * math.tau / 48
    inner, outer = 0.31, 0.43
    vs = [
        point(LX + r * math.cos(t), d, LZ + r * math.sin(t))
        for d in (0.212, 0.295)
        for r, t in [(inner, a), (outer, a), (outer, b), (inner, b)]
    ]
    batch("stone").add(
        vs,
        [
            (0, 3, 2, 1),
            (4, 5, 6, 7),
            (0, 1, 5, 4),
            (1, 2, 6, 5),
            (2, 3, 7, 6),
            (3, 0, 4, 7),
        ],
    )
vs = [
    point(
        LX + 0.237 * math.cos(p) * math.cos(t),
        0.288 + 0.165 * math.cos(p) * math.sin(t),
        LZ + 0.237 * math.sin(p),
    )
    for p in [-math.pi / 2 + math.pi * j / 12 for j in range(13)]
    for t in [math.tau * k / 24 for k in range(24)]
]
batch("lamp").add(
    vs,
    [
        (
            j * 24 + k,
            j * 24 + (k + 1) % 24,
            (j + 1) * 24 + (k + 1) % 24,
            (j + 1) * 24 + k,
        )
        for j in range(12)
        for k in range(24)
    ],
)
box("stone", C, 0.33, 0.112, W + 0.16, 0.67, 0.18)
new = {}
for key, g in new_batches.items():
    obj = g.finish()
    obj.name = PREFIX + "50A_" + key
    obj.data.name = obj.name
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    owned.append(obj)
    changes.append(
        {
            "source": None,
            "owned": obj.name,
            "action": "Registered50Aentrance "
            + key
            + " from2022existingphoto geometry; darkbluepaint from2025/26handbook,capturedateunknown; dimensions estimated",
        }
    )
    new[key] = obj

# Documented lowest No50 triple-window edges, projected through the same
# wood-door-plane homography. Photo top is cropped: retain original6.32m
# verticaldatum is unregistered, so original4.30..6.32m height is retained.
WINDOW_L, WINDOW_R, WINDOW_BOTTOM, WINDOW_TOP = -1.91, 1.91, 4.30, 6.32
REGION_L, REGION_R, REGION_BOTTOM, REGION_TOP = -2.04, 2.10, 4.10, 6.70
shared_owned, shared_sources, shared_changes = [], [], []
shared_collection = bpy.data.collections["49L_EXTERIOR"]
# One actual cutter removes only the registered front zone and penetrates
# the old artificial49/50tenant-divider at this documented window aperture.
cutg = Geometry("50L", "registered_upper_cutter", "stone")
cutg.box(
    point((REGION_L + REGION_R) / 2, -0.45, (REGION_BOTTOM + REGION_TOP) / 2),
    (REGION_R - REGION_L, 1.5, REGION_TOP - REGION_BOTTOM),
    math.atan2(u.y, u.x),
)
cutter = cutg.finish()
bm = bmesh.new()
bm.from_mesh(cutter.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(cutter.data)
bm.free()
for src in list(bpy.data.objects):
    if src.type != "MESH" or src.hide_render or src == cutter:
        continue
    is_shared = (
        src.name.startswith("49L_") and shared_collection in src.users_collection
    )
    is_fifty = (
        src.name.startswith("50L_")
        and collection in src.users_collection
        and src not in owned
    )
    if not is_shared and not is_fifty:
        continue
    ps = [local(src.matrix_world @ v.co) for v in src.data.vertices]
    if (
        not ps
        or max(p.x for p in ps) <= REGION_L
        or min(p.x for p in ps) >= REGION_R
        or max(p.z for p in ps) <= REGION_BOTTOM
        or min(p.z for p in ps) >= REGION_TOP
        or max(p.y for p in ps) < -1.2
        or min(p.y for p in ps) > 0.3
    ):
        continue
    if is_shared:
        assert src.name not in {
            "49L_NEXT_retained_window_glass",
            "49L_D5_round_corner_window_glass",
            "49L_NEXT_fireexit_circular_window_glass",
            "49L_D5_corner_pier_cream",
        }, src.name
        obj = src.copy()
        obj.data = src.data.copy()
        obj.name = "49L_NEXT_SHARED50_" + src.name.removeprefix("49L_")
        shared_collection.objects.link(obj)
    else:
        obj = next(
            (
                o
                for o in owned
                if any(
                    c["source"] == src.name and c["owned"] == o.name for c in changes
                )
            ),
            None,
        )
        if obj is None:
            obj = src.copy()
            obj.data = src.data.copy()
            obj.name = PREFIX + "retained_" + src.name.removeprefix("50L_")
            collection.objects.link(obj)
            owned.append(obj)
            sources.append(src)
            changes.append(
                dict(
                    source=src.name,
                    owned=obj.name,
                    action="Locally remove overlap at photograph-registered lowestNo50triplewindow; all other regions retained",
                )
            )
    # Existing boxes use inverted winding; normalize only owned meshes for exact
    # solid difference. Originals retain every coordinate, UV and material slot.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    for mod in list(obj.modifiers):
        if mod.type == "BEVEL":
            obj.modifiers.remove(mod)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new("registered_window_zone", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.select_set(False)
    if is_shared:
        shared_owned.append(obj)
        shared_sources.append(src)
        shared_changes.append(
            dict(
                source=src.name,
                owned=obj.name,
                action="Trim only sharedNo50photo-zone overlap; retained49geometry elsewhere",
            )
        )
bpy.data.objects.remove(cutter, do_unlink=True)

# Remove artificial sharedtenant divider only within the actual aperture,
# extending2.6m inwards. Outside that confirmed opening its geometry stays.
apg = Geometry("50L", "registered_aperture_deep_cutter", "stone")
apg.box(
    point(0, -1.15, (WINDOW_BOTTOM + WINDOW_TOP) / 2),
    (WINDOW_R - WINDOW_L, 2.9, WINDOW_TOP - WINDOW_BOTTOM),
    math.atan2(u.y, u.x),
)
apc = apg.finish()
bm = bmesh.new()
bm.from_mesh(apc.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(apc.data)
bm.free()
for obj in shared_owned:
    if "unobserved_wall" not in obj.name:
        continue
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("true_window_aperture_deep", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = apc
    bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(apc, do_unlink=True)

# Plain brick below/above and either side of the genuine three-part opening;
# this replaces empty oldbay and cropped neighbouring fragments, not a screen.
upper_batches = {}
geometry_materials["upper_brick"] = bpy.data.materials["COOPERS_brick"]
geometry_materials["upper_frame"] = bpy.data.materials["COOPERS_white"]
geometry_materials["upper_glass"] = glass_owned[GLASS_SOURCES[0]].data.materials[0]


def upperbox(key, x, d, z, w, t, h):
    if key not in upper_batches:
        upper_batches[key] = Geometry("50L", "registered_No50_upper_" + key, key)
    upper_batches[key].box(point(x, d, z), (w, t, h), math.atan2(u.y, u.x))


for l, r in [(REGION_L, WINDOW_L), (WINDOW_R, REGION_R)]:
    upperbox(
        "upper_brick",
        (l + r) / 2,
        -0.12,
        (REGION_BOTTOM + REGION_TOP) / 2,
        r - l,
        0.25,
        REGION_TOP - REGION_BOTTOM,
    )
for lo, hi in [(REGION_BOTTOM, WINDOW_BOTTOM), (WINDOW_TOP, REGION_TOP)]:
    upperbox("upper_brick", 0, -0.12, (lo + hi) / 2, WINDOW_R - WINDOW_L, 0.25, hi - lo)
# Frame grid follows the three visible columns and photograph's visible sash
# meetingrail; unknown upper portions are not extended into the next storey.
for x in [WINDOW_L + 0.045, WINDOW_R - 0.045, -0.637, 0.637]:
    upperbox(
        "upper_frame",
        x,
        -0.015,
        (WINDOW_BOTTOM + WINDOW_TOP) / 2,
        0.09,
        0.13,
        WINDOW_TOP - WINDOW_BOTTOM,
    )
for z in [WINDOW_BOTTOM + 0.045, WINDOW_TOP - 0.045, 5.31]:
    upperbox("upper_frame", 0, -0.015, z, WINDOW_R - WINDOW_L, 0.13, 0.09)
for x in [-1.273, 0, 1.273]:
    upperbox(
        "upper_glass",
        x,
        -0.17,
        (WINDOW_BOTTOM + WINDOW_TOP) / 2,
        1.18,
        0.04,
        WINDOW_TOP - WINDOW_BOTTOM - 0.09,
    )
upper_new = {}
for key, g in upper_batches.items():
    obj = g.finish()
    obj.name = PREFIX + "No50_upper_" + key
    obj.data.name = obj.name
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    owned.append(obj)
    upper_new[key] = obj
    changes.append(
        dict(
            source=None,
            owned=obj.name,
            action="Photograph-registered lowestNo50triplewindow "
            + key
            + "; upperedge inheritedestimate",
        )
    )
SHARED_OWNED = [o.name for o in shared_owned]
SHARED_SOURCES = [o.name for o in shared_sources]
SHARED_COMPONENT = OUT / "coopers-shared-upper-component.blend"
for obj in shared_sources:
    obj.hide_render = True
    obj.hide_set(True)
bpy.data.libraries.write(
    str(SHARED_COMPONENT), set(shared_owned), fake_user=True, compress=True
)
shared_audit = dict(
    baseline=str(BASE),
    baselineSha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),
    originalObjectCount=len(originals),
    originalFingerprints=originals,
    originalVisibility=visibility,
    ownedObjects=SHARED_OWNED,
    archivedObjects=SHARED_SOURCES,
    changes=shared_changes,
    destinationCollection="49L_EXTERIOR",
    retainNewMaterials=True,
    registeredFrame=frame,
    scope="Trim sharedupper49wall/frame overlap only at photograph-registeredNo50window; four parallel49glazing sources excluded",
    trimBounds=dict(
        x=[REGION_L, REGION_R], z=[REGION_BOTTOM, REGION_TOP], depth=[-1.2, 0.3]
    ),
    limitations=[
        "Legal/sharedbuildingboundary not surveyed; photo identifies physicalNo50window independent ofmetadata ownership",
        "Photo top cropped and verticaldatum not registered. Retain inherited4.30..6.32m storeywindow height; nextsill gap remains0.71m",
    ],
)
(OUT / "shared-upper-audit.json").write_text(json.dumps(shared_audit, indent=2))

SOURCES = [o.name for o in sources]
OWNED = [o.name for o in owned]
GLASS_OWNED = [o.name for o in glass_owned.values()] + [
    new["glass"].name,
    upper_new["upper_glass"].name,
]
probes = []
for src_name, obj in glass_owned.items():
    for k, ids in enumerate(parts(obj.data)):
        c = sum(
            (obj.matrix_world @ obj.data.vertices[i].co for i in ids), Vector()
        ) / len(ids)
        probes.append(
            {
                "label": src_name + "-" + str(k),
                "source": src_name,
                "expected": obj.name,
                "point": list(c + u * 0.13 + Vector((0, 0, 0.11))),
            }
        )
probes.append(
    {
        "label": "50Aupper-glass",
        "source": GLASS_SOURCES[0],
        "expected": new["glass"].name,
        "point": list(point(C + 0.13, -0.08, 1.82)),
    }
)
# Probe the three real subpanes away from the frame meetingrail.
for x in [-1.273, 0, 1.273]:
    probes.append(
        dict(
            label="No50upper-triple-" + str(x),
            source=GLASS_SOURCES[0],
            expected=upper_new["upper_glass"].name,
            point=list(point(x, -0.17, 5.98)),
        )
    )
assert len(probes) == 14


def tree(exclude=()):
    vs = []
    fs = []
    names = []
    for obj in bpy.data.objects:
        if (
            obj.type != "MESH"
            or obj.hide_render
            or obj.name in exclude
            or not any(
                c.name in ("50L_EXTERIOR", "49L_EXTERIOR") for c in obj.users_collection
            )
        ):
            continue
        k = len(vs)
        vs.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        fs.extend(tuple(k + i for i in p.vertices) for p in obj.data.loop_triangles)
        names.extend([obj.name] * len(obj.data.loop_triangles))
    return BVHTree.FromPolygons(vs, fs, all_triangles=True), names


def cast(exclude=(), behind=False):
    b, names = tree(exclude)
    result = []
    for p in probes:
        h = b.ray_cast(Vector(p["point"]) + n * (-0.05 if behind else 0.9), -n, 30)
        result.append(
            {
                "label": p["label"],
                "firstObject": names[h[2]] if h[2] is not None else None,
                "distance": h[3],
                "hit": list(h[0]) if h[0] else None,
            }
        )
    return result


before = cast(OWNED)
for obj in sources:
    obj.hide_render = True
    obj.hide_set(True)
after = cast()
behind = cast(GLASS_OWNED, True)
assert all(r["firstObject"] == p["expected"] for r, p in zip(after, probes))
assert all(r["distance"] is None or r["distance"] > 0.65 for r in behind), behind
assert all(r["distance"] is None or r["distance"] > 2 for r in behind[-3:]), behind[-3:]
surface_samples = [
    ("red-solid-panel", point(C, 0.9, 0.61), new["red"].name),
    ("left-surround", point(LEFT - 0.16, 0.9, 1.7), new["stone"].name),
    ("right-surround", point(RIGHT + 0.16, 0.9, 1.7), new["stone"].name),
    ("external-lamp-opaque", point(LX, 0.9, LZ), new["lamp"].name),
    ("No50wood-door-retained", point(0.34, 0.9, 1.48), "50L_D5_portal72_panel"),
]


def surface_checks():
    b, names = tree()
    rs = []
    for label, p, expected in surface_samples:
        h = b.ray_cast(p, -n, 3)
        name = names[h[2]] if h[2] is not None else None
        assert name == expected, (label, name)
        rs.append({"label": label, "firstObject": name, "expected": expected})
    return rs


surfaces = surface_checks()


def door_wall_checks():
    exclude = [o.name for o in bpy.data.objects if o.name != new["stone"].name]
    b, names = tree(exclude)
    rs = []
    for dx in (-0.30, 0, 0.30):
        for z in (1.25, 1.75, 2.25):
            h = b.ray_cast(point(C + dx, 0.9, z), -n, 1.8)
            assert h[2] is None
            rs.append({"x": C + dx, "z": z, "wallBlocked": False})
    return rs


wall_checks = door_wall_checks()
assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
assert all(
    [
        bpy.data.objects[k].hide_render,
        bpy.data.objects[k].hide_viewport,
        bpy.data.objects[k].hide_get(),
    ]
    == v
    for k, v in visibility.items()
    if k not in SOURCES + SHARED_SOURCES
)
COMPONENT = OUT / "fifty-lincoln-glazing-component.blend"
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
registration = json.loads((OUT / "50a-registration.json").read_text())
blue_source = (
    ROOT
    / "data/建筑图片/50L_50 Lincoln_s Inn Fields/01_建筑实拍/small_round5_50L_handbook-000.png"
)
colour_evidence = dict(
    path=str(blue_source),
    sha256=hashlib.sha256(blue_source.read_bytes()).hexdigest(),
    publication="2025/26officialhandbook",
    captureDate=None,
    observation="50Adarkblueframe/opaque lowerpanel; upperglass remainsrealaperture",
    paintingDateUnknown=True,
)
upper_registration = dict(
    source=str(OUT / "existing-elevation-2022-000.jpg"),
    sourceSha256=registration["sourceSha256"],
    displayPhotoEdgePoints=[[730, 185], [1300, 185]],
    projectedXZ=[[-1.84872683, 5.16217655], [1.94644790, 5.20541073]],
    horizontalSpanEstimate=3.79517473,
    nativeWidthEstimate=3.82,
    axisDeviationEstimate=0.049,
    woodDoorMetricBoundsEstimated=True,
    verticalDatumRegistered=False,
    verticalBoundsRetained=[4.3, 6.32],
    photoTopCropped=True,
)

target = point(2.6, -2, 6.5)
position = target + n * 35 - u * 13 + Vector((0, 0, 5))
audit = {
    "baseline": str(BASE),
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalObjectCount": len(originals),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": OWNED,
    "archivedObjects": SOURCES,
    "archiveObjects": SOURCES,
    "changes": changes,
    "destinationCollection": "50L_EXTERIOR",
    "sourceCollections": {
        o.name: [c.name for c in o.users_collection] for o in sources
    },
    "retainNewMaterials": True,
    "removedTargetPlaceholderIslands": removed,
    "registeredFrame": frame,
    "50ARegistration": registration,
    "50AColourEvidence": colour_evidence,
    "No50UpperRegistration": upper_registration,
    "registrationIdentityChecks": [
        {
            "relation": "No50wooddoor and No50tripartite upperwindow shareaxis",
            "nativeXZ": [0, 5.31],
            "photoProjectedXZ": registration["features"]["tripartiteAxis"]["nativeXZ"],
        },
        {
            "relation": "50Aentrance and roundexternal lamp occupy stonefield betweenNo50tripartite and nextupperwindow; they are not on nextwindowaxis",
            "doorNativeXZ": [C, (LO + HI) / 2],
            "lampNativeXZ": [LX, LZ],
            "nativeNextWindowEstimatedX": 2.651,
            "photoNextWindowProjectedX": registration["features"][
                "nextUpperWindowAxisEstimate"
            ]["nativeXZ"][0],
        },
        {
            "relation": "2022planning text explicitly identifies right circular feature as neighbour external light; left49Lcircle is separate opening",
            "externalLightOpaque": True,
            "49LPreserved": True,
        },
    ],
    "geometryEstimate": {
        "doorAxis": C,
        "doorWidth": W,
        "bottom": LO,
        "top": HI,
        "targetBay": [A, B],
        "stoneTop": STONE_TOP,
        "lampCenter": [LX, LZ],
        "lampRingRadius": 0.43,
        "method": "Hand-read original image corners and homography from retainedNo50wooddoor rectangle; neither measured survey nor exact photogrammetry",
    },
    "materials": materials,
    "webOpacity": 0.82,
    "No50UpperWindowCorrection": dict(
        bounds=[WINDOW_L, WINDOW_R, WINDOW_BOTTOM, WINDOW_TOP],
        photoSource="existing-elevation-2022-000.jpg",
        photoTopCropped=True,
        estimatedUpperEdgeInherited=True,
        nextStoreySillBottom=7.03,
        minimumVerticalGap=0.71,
        sharedComponent=SHARED_COMPONENT.name,
    ),
    "probes": probes,
    "beforeFrontProbes": before,
    "afterFrontProbes": after,
    "afterBehindProbes": behind,
    "50AWallOpeningProbes": wall_checks,
    "surfaceChecks": surfaces,
    "nativePreviewCamera": {
        "position": list(position),
        "target": list(target),
        "orthoScale": 21,
    },
    "wholeExteriorReview": {
        "resolved": "Replace bogus groundstorey bay with offset50Adarkblueglazed entry and opaque external lamp. Restore No50wide triplewindow with originalstoreyheight and realopening acrosssharedfacade; higherwindows/roof and49otherregions retained.",
        "glass": "10 originalwindowpanes+1No50fanlight+1true50Aupperdoorpane with finite transparency and originalwindow colour. No fictitious interior backing.",
        "remainingMajorError": "Rightupperwindow pitch remains approximate; only definite overlap with correctedNo50triplewindow removed. Higherstoreys not extrapolated.",
        "sharedBoundary": "Physical photo establishes50Aentrance; legal property boundaries and full rear remain unknown.",
    },
    "limitations": [
        "Original image hand-read corners/metric wooddoor bounds are estimates; homography outsidedoor extrapolates and is not a measured2026survey.",
        "No50lowestupperwindow width3.82m follows relative photo estimate; verticaldatum from estimatedwooddoor is not registered, so original4.30..6.32m bounds retained. Nextsill7.03m leaves0.71m gap.",
        "Actual shop entrance/window to right of50A begins aroundprojected3.711m; existing right storefront bay remains approximate, not newly guessed.",
        "Original RGB retained for glass; new darkblue50Aframe/lowerpanel from2025/26officialhandbook photo, capturedateunknown. Stone/lampdepth estimated.",
        "Full room/floor/window boundary assignment unavailable; remote retained walls7m behind glass remain visible with bounded transparency.",
        "No store brand, fabricated paper notices, interior or current opening hours added.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
NEW_NAMES = {key: obj.name for key, obj in new.items()}
UPPER_NAMES = {key: obj.name for key, obj in upper_new.items()}
open_baseline()
collection = bpy.data.collections["50L_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(OWNED)
for obj in dst.objects:
    collection.objects.link(obj)
with bpy.data.libraries.load(str(SHARED_COMPONENT), link=False) as (src, dst):
    dst.objects = list(SHARED_OWNED)
for obj in dst.objects:
    bpy.data.collections["49L_EXTERIOR"].objects.link(obj)
for name in SOURCES + SHARED_SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
new = {key: bpy.data.objects[name] for key, name in NEW_NAMES.items()}
assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
assert all(
    [
        bpy.data.objects[k].hide_render,
        bpy.data.objects[k].hide_viewport,
        bpy.data.objects[k].hide_get(),
    ]
    == v
    for k, v in visibility.items()
    if k not in SOURCES + SHARED_SOURCES
)
assert cast() == after
assert cast(GLASS_OWNED, True) == behind
assert surface_checks() == surfaces
assert door_wall_checks() == wall_checks
# Genuine window aperture: cast through allsolid meshes, not just newbrick.
solid_exclude = [
    obj.name
    for obj in bpy.data.objects
    if obj.type == "MESH"
    and any(m and "glass" in m.name.lower() for m in obj.data.materials)
]
solid_tree, solid_names = tree(solid_exclude)
upper_walls = []
for x in [-1.273, 0, 1.273]:
    for z in [4.6, 5.98]:
        hit = solid_tree.ray_cast(point(x, 0.9, z), -n, 2.9)
        assert hit[2] is None, (x, z, solid_names[hit[2]])
        upper_walls.append(
            dict(
                x=x,
                z=z,
                wallBlocked=False,
                frontOriginDepth=0.9,
                throughDepth=2.9,
                innerDepthReached=-2.0,
            )
        )

for name in GLASS_OWNED:
    assert float(bpy.data.objects[name].data.materials[0]["webOpacity"]) == 0.82
verification = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalUvAndMaterialSlotsPreserved": True,
    "originalObjectCount": len(originals),
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest()
    == audit["baselineSha256"],
    "glassFirstHits": 14,
    "nearFieldGlassClearance": 14,
    "50AupperGlassFirstHit": True,
    "50AWallThroughProbes": 9,
    "50ASolidLowerPanelAndSurroundAndNo50DoorChecks": surfaces,
    "reloadedFrontProbes": after,
    "reloadedBehindProbes": behind,
    "No50WallThroughProbes": upper_walls,
    "No50WindowBehindAtLeast2mClear": True,
    "No50WindowVerticalBoundsRetained": [4.3, 6.32],
    "nextStoreySillGap": 0.71249979,
    "reloaded50AWallProbes": wall_checks,
    "webOpacity": 0.82,
    "reloadedBrowserOpacityVerified": True,
    "49LOriginalGeometryPreservedAndOnlySharedUpperOverlapArchived": True,
    "No50WoodDoorAndGoldenArchAndUnregisteredHigherWindowRoofPreserved": True,
    "nativeRender": "reloaded-fifty-lincoln-glazing.png",
    "rendered": False,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
shared_verification = dict(
    componentSha256=hashlib.sha256(SHARED_COMPONENT.read_bytes()).hexdigest(),
    savedComponentReopened=True,
    originalGeometryPreserved=True,
    originalUvAndMaterialSlotsPreserved=True,
    originalObjectCount=len(originals),
    unrelatedVisibilityPreserved=True,
    parallelFourSourcesUntouched=True,
    No50TripleGlassFirstHits=after[-3:],
    No50BehindClearance=behind[-3:],
    No50WallThroughProbes=upper_walls,
    No50WindowBehindAtLeast2mClear=True,
    No50WindowVerticalBoundsRetained=[4.3, 6.32],
    nextStoreySillGap=0.71249979,
    baselineUnchanged=True,
    rendered=False,
)
(OUT / "shared-upper-verification.json").write_text(
    json.dumps(shared_verification, indent=2)
)
scene = bpy.context.scene
for obj in scene.objects:
    if obj.type in {"MESH", "FONT", "CURVE"} and obj.name not in {
        o.name
        for o in list(collection.all_objects)
        + list(bpy.data.collections["49L_EXTERIOR"].all_objects)
    }:
        obj.hide_render = True
cd = bpy.data.cameras.new(PREFIX + "preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = position
cam.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 21
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_x = 1050
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-fifty-lincoln-glazing.png")
bpy.ops.render.render(write_still=True)
verification["rendered"] = True
shared_verification["rendered"] = True
shared_verification["nativeRender"] = "reloaded-fifty-lincoln-glazing.png"
(OUT / "shared-upper-verification.json").write_text(
    json.dumps(shared_verification, indent=2)
)
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("FIFTY_50A_COMPLETE", verification["componentSha256"], flush=True)
bpy.ops.wm.quit_blender()
