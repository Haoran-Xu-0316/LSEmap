"""Restore six documentedSALgable window apertures and30frontageglazing.
Constant Blender authoring; only owned component saved, no completecampuscopy.
"""

from pathlib import Path
import bpy, bmesh, array, hashlib, json, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/sal_glazing149"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v148.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
PREFIX = "SAL_NEXT_GLAZING149_"
COMPONENT = OUT / "sardinia-glazing-component.blend"
CODE = "SAL"
GLASS = "SAL_Window_glazing"
WALL = "SAL_Dutch_gable_masonry"
TARGET_PARTS = list(range(4, 16)) + list(range(27, 39)) + list(range(52, 58))
GABLE_PARTS = list(range(52, 58))


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


def bvh(code, skip=()):
    vs = []
    fs = []
    names = []
    for o in bpy.data.collections[code + "_EXTERIOR"].all_objects:
        if o.type != "MESH" or o.hide_render or o.name in skip:
            continue
        k = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        o.data.calc_loop_triangles()
        fs.extend(tuple(k + i for i in p.vertices) for p in o.data.loop_triangles)
        names.extend([o.name] * len(o.data.loop_triangles))
    return BVHTree.FromPolygons(vs, fs, all_triangles=True), names


def protected(originals, visibility, archives):
    assert all(
        fingerprint(bpy.data.objects[name]) == h for name, h in originals.items()
    )
    assert all(
        [
            bpy.data.objects[name].hide_render,
            bpy.data.objects[name].hide_viewport,
            bpy.data.objects[name].hide_get(),
        ]
        == v
        for name, v in visibility.items()
        if name not in archives
    )


def get_panels(obj, centre):
    result = []
    for j, ids in enumerate(parts(obj.data)):
        ids = set(ids)
        ps = [obj.matrix_world @ obj.data.vertices[i].co for i in ids]
        c = sum(ps, Vector()) / len(ps)
        polys = [p for p in obj.data.polygons if all(i in ids for i in p.vertices)]
        face = max(polys, key=lambda p: p.area)
        n = obj.matrix_world.to_3x3() @ face.normal
        n.z = 0
        n.normalize()
        if n.dot(c - centre) < 0:
            n = -n
        u = Vector((-n.y, n.x, 0))
        coords = [(p - c).dot(u) for p in ps]
        result.append(
            dict(
                source=obj.name,
                part=j,
                center=list(c),
                normal=list(n),
                axis=list(u),
                width=max(coords) - min(coords),
                bottom=min(p.z for p in ps),
                top=max(p.z for p in ps),
                point=list(
                    c
                    + u * ((max(coords) - min(coords)) * 0.19)
                    + Vector(
                        (0, 0, (max(p.z for p in ps) - min(p.z for p in ps)) * 0.13)
                    )
                ),
            )
        )
    return result


def probes(code, panels, skip=(), behind=False):
    b, names = bvh(code, skip)
    rs = []
    for p in panels:
        normal = Vector(p["normal"])
        hit = b.ray_cast(
            Vector(p["point"]) + normal * (-0.055 if behind else 0.8), -normal, 30
        )
        rs.append(
            dict(
                source=p["source"],
                part=p["part"],
                firstObject=names[hit[2]] if hit[2] is not None else None,
                distance=hit[3],
                hit=list(hit[0]) if hit[0] else None,
            )
        )
    return rs


def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    if (OUT / "audit.json").exists():
        a = json.loads((OUT / "audit.json").read_text())
        for name in a["ownedObjects"]:
            o = bpy.data.objects.get(name)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        for name in a["archivedObjects"]:
            o = bpy.data.objects[name]
            state = a["originalVisibility"][name]
            o.hide_render, o.hide_viewport = state[:2]
            o.hide_set(state[2])
    for sc in bpy.data.scenes:
        for layer in sc.view_layers:
            layer.update()


open_source()
col = bpy.data.collections["SAL_EXTERIOR"]
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
inspection = json.loads((OUT / "inspection.json").read_text())
panels = [
    p
    for p in inspection["panels"]
    if p["source"] == GLASS and p["part"] in TARGET_PARTS
]
assert len(panels) == 30
before_front = probes(CODE, panels)
before_back = probes(
    CODE,
    panels,
    [
        p["name"]
        for p in inspection["objects"]
        if any("glass" in m.lower() or "glaz" in m.lower() for m in p["materials"])
    ],
    True,
)
source = bpy.data.objects[GLASS]
glass = source.copy()
glass.data = source.data.copy()
glass.name = PREFIX + "retained_frontage_glass"
glass.data.name = glass.name
col.objects.link(glass)
old = source.data.materials[0]
m = old.copy()
m.name = PREFIX + "photographed_finite_glass"
pr = next(p for p in m.node_tree.nodes if p.type == "BSDF_PRINCIPLED")
keys = ["Alpha", "Transmission Weight", "Roughness", "Metallic", "IOR"]
oldparams = {k: pr.inputs[k].default_value for k in keys}
for k, v in [
    ("Alpha", 0.82),
    ("Transmission Weight", 0.22),
    ("Roughness", 0.26),
    ("Metallic", 0.12),
    ("IOR", 1.45),
]:
    pr.inputs[k].default_value = v
m.diffuse_color = tuple(old.diffuse_color[:3]) + (0.82,)
m["webOpacity"] = 0.82
glass.data.materials.append(m)
groups = parts(source.data)
target_ids = set(i for j in TARGET_PARTS for i in groups[j])
for poly in glass.data.polygons:
    if all(i in target_ids for i in poly.vertices):
        poly.material_index = len(glass.data.materials) - 1
# No new opaque plane: cut six realwindowvoids in an ownedgable copy.
sourcewall = bpy.data.objects[WALL]
wall = sourcewall.copy()
wall.data = sourcewall.data.copy()
wall.name = PREFIX + "opened_six_gable_masonry"
wall.data.name = wall.name
col.objects.link(wall)
bm = bmesh.new()
bm.from_mesh(wall.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(wall.data)
bm.free()
for mod in list(wall.modifiers):
    if mod.type == "BEVEL":
        wall.modifiers.remove(mod)
cutrecords = []
for p in panels:
    if p["part"] not in GABLE_PARTS:
        continue
    c = Vector(p["center"])
    n = Vector(p["normal"])
    u = Vector(p["axis"])
    lo, hi = p["bottom"] - 0.002, p["top"] + 0.002
    width = p["width"] + 0.004
    vs = [
        c + u * (x * width / 2) + n * d + Vector((0, 0, z - c.z))
        for x in [-1, 1]
        for d in [-0.75, 0.4]
        for z in [lo, hi]
    ]
    me = bpy.data.meshes.new(PREFIX + "aperture_tool")
    me.from_pydata(
        vs,
        [],
        [
            (0, 4, 6, 2),
            (1, 3, 7, 5),
            (0, 1, 5, 4),
            (2, 6, 7, 3),
            (0, 2, 3, 1),
            (4, 5, 7, 6),
        ],
    )
    me.update()
    tool = bpy.data.objects.new(me.name, me)
    col.objects.link(tool)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = wall
    mod = wall.modifiers.new("actualgable_windowvoid", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = tool
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)
    bpy.data.meshes.remove(me)
    cutrecords.append(
        dict(
            part=p["part"],
            center=p["center"],
            normal=p["normal"],
            width=width,
            bottom=lo,
            top=hi,
            depth=[-0.75, 0.4],
        )
    )
# Three leftgablewindows additionally overlap the inheritedfrontbrick band.
pier_source = bpy.data.objects["SAL_Front_brick_piers"]
pier = pier_source.copy()
pier.data = pier_source.data.copy()
pier.name = PREFIX + "opened_left_gable_frontbrick"
pier.data.name = pier.name
col.objects.link(pier)
bm = bmesh.new()
bm.from_mesh(pier.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(pier.data)
bm.free()
for mod in list(pier.modifiers):
    if mod.type == "BEVEL":
        pier.modifiers.remove(mod)
for p in panels:
    if p["part"] not in [52, 53, 54]:
        continue
    c = Vector(p["center"])
    n = Vector(p["normal"])
    u = Vector(p["axis"])
    lo, hi = p["bottom"] - 0.002, p["top"] + 0.002
    width = p["width"] + 0.004
    vs = [
        c + u * (x * width / 2) + n * d + Vector((0, 0, z - c.z))
        for x in [-1, 1]
        for d in [-0.75, 0.4]
        for z in [lo, hi]
    ]
    me = bpy.data.meshes.new(PREFIX + "left_aperture_tool")
    me.from_pydata(
        vs,
        [],
        [
            (0, 4, 6, 2),
            (1, 3, 7, 5),
            (0, 1, 5, 4),
            (2, 6, 7, 3),
            (0, 2, 3, 1),
            (4, 5, 7, 6),
        ],
    )
    me.update()
    tool = bpy.data.objects.new(me.name, me)
    col.objects.link(tool)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    bpy.context.view_layer.objects.active = pier
    mod = pier.modifiers.new("actual_leftgable_windowvoid", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = tool
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(tool, do_unlink=True)
    bpy.data.meshes.remove(me)

for src in [source, sourcewall, pier_source]:
    src.hide_render = True
    src.hide_set(True)
front = probes(CODE, panels)
allglass = [
    o.name
    for o in col.all_objects
    if o.type == "MESH"
    and any(
        m and ("glass" in m.name.lower() or "glaz" in m.name.lower())
        for m in o.data.materials
    )
]
back = probes(CODE, panels, allglass, True)
assert all(r["firstObject"] == glass.name for r in front), front
assert all(r["distance"] is None or r["distance"] > 2 for r in back[:24]), back[:24]
assert all(r["distance"] is None or r["distance"] > 0.6 for r in back[24:]), back[24:]
assert all(
    r["firstObject"] == "SAL_Roof_slates" or r["distance"] is None or r["distance"] > 2
    for r in back[24:]
), back[24:]
owned = [glass, wall, pier]
archives = [GLASS, WALL, "SAL_Front_brick_piers"]
protected(originals, visibility, archives)
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
A = math.radians(24.35)
N = Vector((-math.sin(A), math.cos(A), 0))
U = Vector((-math.cos(A), -math.sin(A), 0))
O = Vector((120.73, 121.65, 0))
target = O + Vector((0, 0, 14))
position = target + N * 70 - U * 10 + Vector((0, 0, 7))
a = dict(
    baseline=str(BASE),
    baselineSha256=sha,
    originalObjectCount=len(originals),
    originalFingerprints=originals,
    originalVisibility=visibility,
    ownedObjects=[o.name for o in owned],
    archivedObjects=archives,
    changes=[
        dict(
            source="SAL_Front_brick_piers",
            owned=pier.name,
            action="Three leftgable truewindowapertures through secondaryfrontbrick overlap; everyotherbrickregion retained",
        ),
        dict(
            source=GLASS,
            owned=glass.name,
            action="Only30photographedmainfrontage/glazing parts finite transparency; everyglassmesh/UV/RGB preserved, allotherparts retainoriginalopaque material",
        ),
        dict(
            source=WALL,
            owned=wall.name,
            action="Six realDutchgable windowapertures cut through ownedmasonry; trueframes/gablecontours/ornaments retained",
        ),
    ],
    destinationCollection="SAL_EXTERIOR",
    retainNewMaterials=True,
    sourceCollections={
        src.name: [c.name for c in src.users_collection]
        for src in [source, sourcewall, pier_source]
    },
    targetGlassParts=TARGET_PARTS,
    panels=panels,
    sixGableApertures=cutrecords,
    beforeFrontProbes=before_front,
    beforeBehindProbes=before_back,
    afterFrontProbes=front,
    afterBehindProbes=back,
    materials=dict(
        source=old.name,
        owned=m.name,
        before=oldparams,
        after={k: pr.inputs[k].default_value for k in keys},
        webOpacity=0.82,
        originalBaseColourPreserved=True,
    ),
    references=[
        dict(
            path="data/collections/library_round5/photos/SAL_d0d696021ed0.jpg",
            sha256=hashlib.sha256(
                (
                    ROOT / "data/collections/library_round5/photos/SAL_d0d696021ed0.jpg"
                ).read_bytes()
            ).hexdigest(),
            sourceUrl="https://www.jesticowhiles.com/project/lincolns-inn-fields-london-school-of-economics/",
            projectYear=2012,
            captureDate=None,
        )
    ],
    nativePreviewCamera=dict(
        position=list(position), target=list(target), orthoScale=66
    ),
    limitations=[
        "30selectedpieces comprise18acceptedfourlightupperwindows/6broadstreetlevelwindows/6photographedgablewindows; not wholebuildingglass replacement",
        "Allnativeglazinggeometry and139acceptedframes/crosses/oriels unchanged; inheritedwindowdimensions estimated",
        "Orielrear stoneposts0.95to1.99m are not provedfalse roomwalls and retainedopaque; oldflat/orielbackpanes not newlytranslucent",
        "Towerbackvolume1.065m and seventhcentralgablewindowfrontpost/roomassignment unresolved; retainopaque",
        "Glasspavilion alreadyT0.9 and lanternalreadyfinite remainunaltered",
        "No registeredrooms/floors or inventedinteriors; originalslopingroof remains approximately1.44m behindgablewindows and is not deleted to force2m clearance",
    ],
)
(OUT / "audit.json").write_text(json.dumps(a, indent=2) + "\n")
ownnames = list(a["ownedObjects"])
glassname = glass.name
wallname = wall.name
piername = pier.name
open_source()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(ownnames)
for obj in dst.objects:
    col = bpy.data.collections["SAL_EXTERIOR"]
    col.objects.link(obj)
for name in archives:
    o = bpy.data.objects[name]
    o.hide_render = True
    o.hide_set(True)
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
protected(originals, visibility, archives)
assert probes(CODE, panels) == front
assert probes(CODE, panels, allglass, True) == back
newglass = bpy.data.objects[glassname]
assert newglass.data.materials[-1]["webOpacity"] == 0.82
# Sixholes tested at fourinner points, through masonry only; this verifies
# actual throughvoids rather than relying on a glassfirsthit alone.
t, names = bvh(
    CODE, [o.name for o in col.all_objects if o.name not in {wallname, piername}]
)
holes = []
for p in panels:
    if p["part"] not in GABLE_PARTS:
        continue
    c = Vector(p["center"])
    n = Vector(p["normal"])
    u = Vector(p["axis"])
    for dx in [-0.22, 0.22]:
        for dz in [-0.27, 0.27]:
            hit = t.ray_cast(c + u * dx + Vector((0, 0, dz)) + n * 0.8, -n, 1.8)
            assert hit[2] is None
            holes.append(dict(part=p["part"], dx=dx, dz=dz, masonryBlocked=False))
# Selectedownmesh materialassignment is restricted to targetpolygons.
expected_ids = set(i for j in TARGET_PARTS for i in groups[j])
assert all(
    poly.material_index
    == (
        len(newglass.data.materials) - 1
        if all(i in expected_ids for i in poly.vertices)
        else bpy.data.objects[GLASS].data.polygons[poly.index].material_index
    )
    for poly in newglass.data.polygons
)
v = dict(
    componentSha256=hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    savedComponentReopened=True,
    originalGeometryPreserved=True,
    originalUvAndMaterialSlotsPreserved=True,
    originalObjectCount=len(originals),
    unrelatedVisibilityPreserved=True,
    baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == sha,
    glassFirstHits=30,
    nearFieldAtLeast2mClear=24,
    gableBehindExistingRoofProbes=back[24:],
    gableWindowsClearOfNearOpaqueFacade=True,
    reloadedFrontProbes=front,
    reloadedBehindProbes=back,
    trueGableThroughProbes=holes,
    gableApertureCount=6,
    untargetedGlassMaterialPreserved=True,
    existingFourLightFramesAndOrielPreserved=True,
    webOpacity=0.82,
    reloadedBrowserOpacityVerified=True,
    rendered=False,
)
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
scene = bpy.context.scene
for obj in scene.objects:
    if obj.type in {"MESH", "CURVE", "FONT"} and obj.name not in col.all_objects:
        obj.hide_render = True
cd = bpy.data.cameras.new(PREFIX + "preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = position
cam.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 66
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_x = 1300
scene.render.resolution_y = 950
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "SAL-reloaded-frontage.png")
bpy.ops.render.render(write_still=True)
v["rendered"] = True
v["nativeRender"] = "SAL-reloaded-frontage.png"
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print("SAL149_COMPLETE", v["componentSha256"], len(holes), flush=True)
bpy.ops.wm.quit_blender()
