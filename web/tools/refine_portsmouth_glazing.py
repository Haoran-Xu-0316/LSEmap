"""Correct photograph-supported Portsmouth and51Lincoln exterior glass.
Constant-config Blender builder. Sources stay immutable; only components saved.
"""

from pathlib import Path
import bpy, bmesh, array, hashlib, json, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/por_exterior148"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v147.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
CONFIG = {
    "POR": dict(
        prefix="POR_NEXT_EXTERIOR148_",
        component="portsmouth-exterior-component.blend",
        audit="audit.json",
        proof="verification.json",
        glass=["POR_D5_sash_glass_glass", "POR_D5_shop_display_glass_glass"],
        wood=None,
        refs=[
            "data/建筑图片/POR_1 Portsmouth Street/01_建筑实拍/exteriors_lse_estate_024.jpg",
            "data/建筑图片/POR_1 Portsmouth Street/01_建筑实拍/small_round5_POR_handbook-000.png",
        ],
    ),
    "51L": dict(
        prefix="51L_NEXT_EXTERIOR148_",
        component="lincoln51-doors-component.blend",
        audit="lincoln51-audit.json",
        proof="lincoln51-verification.json",
        glass=["51L_D5_round96_V20_EXT_door_glazed_panel_glass"],
        wood="51L_D5_round96_V20_EXT_oak_door_leaf_wood",
        refs=[
            "data/建筑图片/51L_51 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_015.jpg",
            "data/collections/lincolns-frontage-review/51l-gsos-2025.jpg",
        ],
    ),
}


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


def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for code, cfg in CONFIG.items():
        p = OUT / cfg["audit"]
        if not p.exists():
            continue
        old = json.loads(p.read_text())
        for name in old.get("ownedObjects", []):
            o = bpy.data.objects.get(name)
            if o:
                bpy.data.objects.remove(o, do_unlink=True)
        for name in old.get("archivedObjects", []):
            o = bpy.data.objects[name]
            state = old["originalVisibility"][name]
            o.hide_render, o.hide_viewport = state[:2]
            o.hide_set(state[2])
    for m in list(bpy.data.materials):
        if any(m.name.startswith(c["prefix"]) for c in CONFIG.values()) and not m.users:
            bpy.data.materials.remove(m)
    for sc in bpy.data.scenes:
        for layer in sc.view_layers:
            layer.update()


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
                point=list(c + u * 0.073 + Vector((0, 0, 0.19))),
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


open_source()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
baseline_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
audits = {}
for code, cfg in CONFIG.items():
    col = bpy.data.collections[code + "_EXTERIOR"]
    points = [
        o.matrix_world @ v.co
        for o in col.all_objects
        if o.type == "MESH" and not o.hide_render
        for v in o.data.vertices
    ]
    centre = sum(points, Vector()) / len(points)
    owned = []
    archive = []
    changes = []
    panels = []
    params = []
    for name in cfg["glass"]:
        source = bpy.data.objects[name]
        obj = source.copy()
        obj.data = source.data.copy()
        obj.name = cfg["prefix"] + "retained_" + name
        obj.data.name = obj.name
        col.objects.link(obj)
        m = source.data.materials[0].copy()
        m.name = cfg["prefix"] + source.data.materials[0].name + "_finite_glass"
        pr = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        before = {
            k: pr.inputs[k].default_value
            for k in ["Alpha", "Transmission Weight", "Roughness", "Metallic", "IOR"]
        }
        for k, v in [
            ("Alpha", 0.82),
            ("Transmission Weight", 0.22),
            ("Roughness", 0.26),
            ("Metallic", 0.12),
            ("IOR", 1.45),
        ]:
            pr.inputs[k].default_value = v
        m.diffuse_color = tuple(source.data.materials[0].diffuse_color[:3]) + (0.82,)
        m["webOpacity"] = 0.82
        obj.data.materials.clear()
        obj.data.materials.append(m)
        panels += get_panels(source, centre)
        owned.append(obj)
        archive.append(source)
        changes.append(
            dict(
                source=name,
                owned=obj.name,
                action="Preserve exactoriginalglassgeometry/UV/basecolour; finite neutral transparency for actualphotographed glazing",
            )
        )
        params.append(
            dict(
                source=source.data.materials[0].name,
                owned=m.name,
                before=before,
                after={k: pr.inputs[k].default_value for k in before},
                webOpacity=0.82,
                originalBaseColourPreserved=True,
            )
        )
    # Baseline rays explicitly include originals while ignoring their new copies.
    before_front = probes(code, panels, [o.name for o in owned])
    before_back = probes(code, panels, [o.name for o in owned] + cfg["glass"], True)
    if cfg["wood"]:
        for solid_name in [cfg["wood"], "51L_D5_round96_V20_EXT_door_recess_metal"]:
            src = bpy.data.objects[solid_name]
            obj = src.copy()
            obj.data = src.data.copy()
            obj.name = cfg["prefix"] + "opened_" + solid_name
            obj.data.name = obj.name
            col.objects.link(obj)
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
            bm.to_mesh(obj.data)
            bm.free()
            for mod in list(obj.modifiers):
                if mod.type == "BEVEL":
                    obj.modifiers.remove(mod)
            for p in panels:
                c = Vector(p["center"])
                n = Vector(p["normal"])
                u = Vector(p["axis"])
                width = p["width"] + 0.008
                lo = p["bottom"] - 0.004
                hi = p["top"] + 0.004
                vs = [
                    c + u * (x * width / 2) + n * d + Vector((0, 0, z - c.z))
                    for x in [-1, 1]
                    for d in [-0.65, 0.3]
                    for z in [lo, hi]
                ]
                me = bpy.data.meshes.new(cfg["prefix"] + "aperture_tool")
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
                bpy.context.view_layer.objects.active = obj
                mod = obj.modifiers.new("actual_upperdoor_glass_aperture", "BOOLEAN")
                mod.operation = "DIFFERENCE"
                mod.solver = "EXACT"
                mod.object = tool
                bpy.ops.object.modifier_apply(modifier=mod.name)
                bpy.data.objects.remove(tool, do_unlink=True)
                bpy.data.meshes.remove(me)
            owned.append(obj)
            archive.append(src)
            changes.append(
                dict(
                    source=src.name,
                    owned=obj.name,
                    action="Two true apertures follow original upperdoor glass outlines; surroundingopaque wood ormetal retained, no inventedroom",
                )
            )
    for source in archive:
        source.hide_render = True
        source.hide_set(True)
    own_names = [o.name for o in owned]
    glass_owned = [c["owned"] for c in changes if c["source"] in cfg["glass"]]
    front = probes(code, panels)
    back = probes(code, panels, glass_owned, True)
    lookup = {c["source"]: c["owned"] for c in changes}
    assert all(
        r["firstObject"] == lookup[p["source"]] for p, r in zip(panels, front)
    ), front
    assert all(r["distance"] is None or r["distance"] > 2 for r in back), back
    protected(originals, visibility, [o.name for o in archive])
    path = OUT / cfg["component"]
    bpy.data.libraries.write(str(path), set(owned), fake_user=True, compress=True)
    a = dict(
        code=code,
        baseline=str(BASE),
        baselineSha256=baseline_sha,
        originalObjectCount=len(originals),
        originalFingerprints=originals,
        originalVisibility=visibility,
        ownedObjects=own_names,
        archivedObjects=[o.name for o in archive],
        changes=changes,
        destinationCollection=code + "_EXTERIOR",
        retainNewMaterials=True,
        sourceCollections={
            o.name: [c.name for c in o.users_collection] for o in archive
        },
        materials=params,
        panels=panels,
        beforeFrontProbes=before_front,
        beforeBehindProbes=before_back,
        afterFrontProbes=front,
        afterBehindProbes=back,
        sources=[
            dict(
                path=str(ROOT / p),
                sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest(),
                captureDate=None,
            )
            for p in cfg["refs"]
        ],
        assetBoundary="Only "
        + code
        + "_EXTERIOR sources;49L/50L and allothercol untouched",
        limitations=[
            "Photo-supported glazing identity; nativeheight,width anddepth inheritedestimates",
            "No fabricatedinterior; distantpartywalls are approximate shells, not registeredrooms",
            "Upper51L androofglazing leftunchanged: threenativerooflights have roofbehind atabout0.86m, aperturelayout notphotographicallyconfirmed",
            "POR historicbookshop branding is archival; handbookphotocapturedateunknown",
        ],
    )
    (OUT / cfg["audit"]).write_text(json.dumps(a, indent=2) + "\n")
    audits[code] = a
    # Restore original visibility after isolated collection checks; both complete
    # candidates are checked together below after component reread.
    for source in archive:
        v = visibility[source.name]
        source.hide_render, source.hide_viewport = v[:2]
        source.hide_set(v[2])
    for obj in owned:
        bpy.data.objects.remove(obj, do_unlink=True)
open_source()
all_archives = []
for code, cfg in CONFIG.items():
    a = audits[code]
    with bpy.data.libraries.load(str(OUT / cfg["component"]), link=False) as (src, dst):
        dst.objects = list(a["ownedObjects"])
    for obj in dst.objects:
        bpy.data.collections[code + "_EXTERIOR"].objects.link(obj)
    for name in a["archivedObjects"]:
        o = bpy.data.objects[name]
        o.hide_render = True
        o.hide_set(True)
    all_archives += a["archivedObjects"]
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
protected(originals, visibility, all_archives)
for code, cfg in CONFIG.items():
    a = audits[code]
    gs = [c["owned"] for c in a["changes"] if c["source"] in cfg["glass"]]
    assert probes(code, a["panels"]) == a["afterFrontProbes"]
    assert probes(code, a["panels"], gs, True) == a["afterBehindProbes"]
    for name in gs:
        assert bpy.data.objects[name].data.materials[0]["webOpacity"] == 0.82
    walls = []
    if cfg["wood"]:
        wood = next(c["owned"] for c in a["changes"] if c["source"] == cfg["wood"])
        recess = next(
            c["owned"]
            for c in a["changes"]
            if c["source"] == "51L_D5_round96_V20_EXT_door_recess_metal"
        )
        t, names = bvh(
            code,
            [
                o.name
                for o in bpy.data.collections[code + "_EXTERIOR"].all_objects
                if o.name not in {wood, recess}
            ],
        )
        for p in a["panels"]:
            c = Vector(p["center"])
            u = Vector(p["axis"])
            n = Vector(p["normal"])
            for dx in [-0.11, 0.11]:
                for dz in [-0.15, 0.15]:
                    hit = t.ray_cast(c + u * dx + Vector((0, 0, dz)) + n * 0.8, -n, 1.4)
                    assert hit[2] is None
                    walls.append(
                        dict(part=p["part"], dx=dx, dz=dz, opaqueLeafBlocked=False)
                    )
        solids = []
        for p in a["panels"]:
            c = Vector(p["center"])
            n = Vector(p["normal"])
            test = Vector((c.x, c.y, 0.65))
            hit = t.ray_cast(test + n * 0.8, -n, 1.5)
            assert hit[2] is not None
            solids.append(dict(part=p["part"], lowerOpaqueLeafFirstHit=names[hit[2]]))
    else:
        solids = []
    v = dict(
        componentSha256=hashlib.sha256(
            (OUT / cfg["component"]).read_bytes()
        ).hexdigest(),
        savedComponentReopened=True,
        originalGeometryPreserved=True,
        originalUvAndMaterialSlotsPreserved=True,
        originalObjectCount=len(originals),
        unrelatedVisibilityPreserved=True,
        baselineUnchanged=hashlib.sha256(BASE.read_bytes()).hexdigest() == baseline_sha,
        reloadedFrontProbes=a["afterFrontProbes"],
        reloadedBehindProbes=a["afterBehindProbes"],
        glassFirstHits=len(a["panels"]),
        nearFieldAtLeast2mClear=len(a["panels"]),
        realDoorApertureProbes=walls,
        retainedLowerSolidDoorProbes=solids,
        reloadedBrowserOpacityVerified=True,
        webOpacity=0.82,
        rendered=False,
    )
    # One native preview perwholeasset. Store exactcamera so mainviewer canmatch.
    scene = bpy.context.scene
    col = bpy.data.collections[code + "_EXTERIOR"]
    active = [o for o in col.all_objects if o.type == "MESH" and not o.hide_render]
    pts = [o.matrix_world @ v.co for o in active for v in o.data.vertices]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    target = (lo + hi) / 2
    direction = Vector(a["panels"][0]["normal"])
    if code == "51L":
        direction = (direction + Vector(a["panels"][1]["normal"])).normalized()
    position = target + direction * 45 + Vector((0, 0, 6))
    scale = max(hi.z - lo.z, hi.x - lo.x, hi.y - lo.y) * 1.28
    a["nativePreviewCamera"] = dict(
        position=list(position), target=list(target), orthoScale=scale
    )
    (OUT / cfg["audit"]).write_text(json.dumps(a, indent=2) + "\n")
    states = {o.name: o.hide_render for o in scene.objects}
    for o in scene.objects:
        if o.type in {"MESH", "CURVE", "FONT"} and o.name not in col.all_objects:
            o.hide_render = True
    cd = bpy.data.cameras.new(cfg["prefix"] + "preview")
    cam = bpy.data.objects.new(cd.name, cd)
    scene.collection.objects.link(cam)
    cam.location = position
    cam.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
    cd.type = "ORTHO"
    cd.ortho_scale = scale
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / (code + "-reloaded-whole.png"))
    bpy.ops.render.render(write_still=True)
    v["rendered"] = True
    v["nativeRender"] = code + "-reloaded-whole.png"
    (OUT / cfg["proof"]).write_text(json.dumps(v, indent=2) + "\n")
    for name, state in states.items():
        bpy.data.objects[name].hide_render = state
    print(
        "EXTERIOR148_COMPLETE", code, v["componentSha256"], len(a["panels"]), flush=True
    )
bpy.ops.wm.quit_blender()
