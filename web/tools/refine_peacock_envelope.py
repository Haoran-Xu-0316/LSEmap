"""Open documented Peacock Theatre entrance/ticket apertures and retain muted bronze glass.
Run inside Blender. All metric frontage dimensions remain inherited estimates.
Only an owned component is written; original campus geometry is never modified.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/peacock_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v145.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
COMPONENT = OUT / "peacock-envelope-component.blend"
PREFIX = "PEA_NEXT_ENVELOPE_"
SOURCES = [
    "PEA_D5_exterior62_ground_dark_dark",
    "PEA_D5_exterior62_ground_stone_stone",
    "PEA_D5_exterior62_entry_glazing_glass",
    "PEA_D5_exterior62_ticket_glass_glass",
    "PEA_D5_exterior62_upper_glass_glass",
]


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    prior = (
        json.loads((OUT / "audit.json").read_text())
        if (OUT / "audit.json").exists()
        else None
    )
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
collection = bpy.data.collections["PEA_EXTERIOR"]
profile = json.loads(
    (ROOT / "result/blender/stage62/peacock-exterior-audit.json").read_text()
)
wall = profile["frontWall"]
origin = Vector((*wall["p"], 0))
u = (Vector((*wall["q"], 0)) - origin).normalized()
n = Vector((*wall["outward"], 0))
sources = [bpy.data.objects[x] for x in SOURCES]
assert all(not o.hide_render for o in sources)
owned = []
changes = []
for src, label in zip(
    sources,
    [
        "ground_dark_with_real_apertures",
        "ticket_stone_with_real_aperture",
        "entry_glass",
        "ticket_glass",
        "upper_glass",
    ],
):
    o = src.copy()
    o.data = src.data.copy()
    o.name = PREFIX + label
    o.data.name = o.name
    collection.objects.link(o)
    owned.append(o)
    changes.append(
        {
            "source": src.name,
            "owned": o.name,
            "action": (
                "Boolean exact difference of existing registered entrance/ticket glass extent through existing wall depth"
                if src in sources[:2]
                else "Exact original glass/UV; bounded transmission with explicit browser opacity"
            ),
        }
    )


# Cutters are derived from the registered original glass boxes, not invented
# rectangular entrances. Extend only along the known frontage normal so both
# old solid cladding/backing slabs are penetrated at the exact glazing edges.
def outward_normals(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


for obj in owned[:2]:
    outward_normals(obj)
cut_report = []
for wall_obj in owned[:2]:
    for glass in sources[2:4]:
        cutter = glass.copy()
        cutter.data = glass.data.copy()
        cutter.name = PREFIX + "temporary_aperture_cutter"
        collection.objects.link(cutter)
        points = [cutter.matrix_world @ v.co for v in cutter.data.vertices]
        center = sum(points, Vector()) / len(points)
        inverse = cutter.matrix_world.inverted()
        for vertex in cutter.data.vertices:
            p = cutter.matrix_world @ vertex.co
            d = (p - center).dot(n)
            vertex.co = inverse @ (p + n * ((1 if d > 0 else -1) * 1.1 - d))
        outward_normals(cutter)
        bpy.context.view_layer.update()
        before_faces = len(wall_obj.data.polygons)
        bpy.context.view_layer.objects.active = wall_obj
        wall_obj.hide_set(False)
        wall_obj.select_set(True)
        mod = wall_obj.modifiers.new("Documented actual glazed opening", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
        wall_obj.select_set(False)
        mesh = cutter.data
        bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.data.meshes.remove(mesh)
        cut_report.append(
            {
                "ownedWall": wall_obj.name,
                "registeredGlass": glass.name,
                "beforeFaces": before_faces,
                "afterFaces": len(wall_obj.data.polygons),
            }
        )
# The current official photograph shows muted reflections, a dark entrance and
# light upper windows. Keep the inherited colour, do not erase remote shells.
original_material = sources[2].data.materials[0]
material = original_material.copy()
material.name = PREFIX + "bounded_reflective_glass"
pr = next(m for m in material.node_tree.nodes if m.type == "BSDF_PRINCIPLED")
keys = ["Base Color", "Roughness", "Metallic", "Alpha", "Transmission Weight", "IOR"]
old_params = {
    k: (
        list(pr.inputs[k].default_value)
        if k == "Base Color"
        else pr.inputs[k].default_value
    )
    for k in keys
}
pr.inputs["Alpha"].default_value = 0.82
pr.inputs["Transmission Weight"].default_value = 0.22
pr.inputs["Roughness"].default_value = 0.26
pr.inputs["Metallic"].default_value = 0.12
pr.inputs["IOR"].default_value = 1.45
material.diffuse_color = tuple(original_material.diffuse_color[:3]) + (0.82,)
material["webOpacity"] = 0.82
for o in owned[2:]:
    o.data.materials.clear()
    o.data.materials.append(material)
new_params = {
    k: (
        list(pr.inputs[k].default_value)
        if k == "Base Color"
        else pr.inputs[k].default_value
    )
    for k in keys
}
probes = []
for o in sources[2:]:
    for k, ids in enumerate(parts(o.data)):
        vs = [o.matrix_world @ o.data.vertices[i].co for i in ids]
        c = sum(vs, Vector()) / len(vs)
        p = c + u * 0.15 + Vector((0, 0, 0.13))
        probes.append(
            {
                "label": o.name + "-" + str(k),
                "source": o.name,
                "point": list(p),
                "center": list(c),
            }
        )
assert len(probes) == 11


def tree(exclude=()):
    vs = []
    fs = []
    names = []
    for o in bpy.data.objects:
        if (
            o.type != "MESH"
            or o.hide_render
            or o.name in exclude
            or not any("PEA" in c.name for c in o.users_collection)
        ):
            continue
        k = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        o.data.calc_loop_triangles()
        fs.extend(tuple(k + i for i in p.vertices) for p in o.data.loop_triangles)
        names.extend([o.name] * len(o.data.loop_triangles))
    return BVHTree.FromPolygons(vs, fs, all_triangles=True), names


def cast(exclude=(), behind=False):
    b, names = tree(exclude)
    result = []
    for p in probes:
        start = Vector(p["point"]) + n * (-0.022 if behind else 0.9)
        h = b.ray_cast(start, -n, 40)
        result.append(
            {
                "label": p["label"],
                "firstObject": names[h[2]] if h[2] is not None else None,
                "distance": h[3],
                "hit": list(h[0]) if h[0] else None,
            }
        )
    return result


before = cast([o.name for o in owned])
back_before = cast([o.name for o in owned] + SOURCES[2:], True)
for o in sources:
    o.hide_render = True
    o.hide_set(True)
after = cast()
back_after = cast([o.name for o in owned[2:]], True)
for p, hit in zip(probes, after):
    assert hit["firstObject"] == changes[SOURCES.index(p["source"])]["owned"], hit
assert all(
    h["distance"] is None or h["distance"] > 0.65 for h in back_after
), back_after
assert (
    back_before[0]["distance"] < 0.01 and back_before[1]["distance"] < 0.15
), back_before[:2]


def aperture_wall_grid(wall_objects):
    vs = []
    fs = []
    for obj in wall_objects:
        k = len(vs)
        vs.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        obj.data.calc_loop_triangles()
        fs.extend(tuple(k + i for i in tri.vertices) for tri in obj.data.loop_triangles)
    b = BVHTree.FromPolygons(vs, fs, all_triangles=True)
    results = []
    for glass in sources[2:4]:
        points = [glass.matrix_world @ v.co for v in glass.data.vertices]
        c = sum(points, Vector()) / len(points)
        width = max((v - c).dot(u) for v in points) - min(
            (v - c).dot(u) for v in points
        )
        height = max(v.z for v in points) - min(v.z for v in points)
        for dx in (-0.35, 0, 0.35):
            for dz in (-0.35, 0, 0.35):
                p = c + u * width * dx + Vector((0, 0, height * dz))
                h = b.ray_cast(p + n * 0.9, -n, 2)
                results.append(
                    {
                        "registeredGlass": glass.name,
                        "relativeX": dx,
                        "relativeZ": dz,
                        "blocked": h[2] is not None,
                        "distance": h[3],
                    }
                )
    return results


wall_before = aperture_wall_grid(sources[:2])
wall_after = aperture_wall_grid(owned[:2])
assert all(p["blocked"] for p in wall_before)
assert all(not p["blocked"] for p in wall_after)
assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
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
for src, obj in zip(sources[2:], owned[2:]):
    assert [tuple(v.co) for v in src.data.vertices] == [
        tuple(v.co) for v in obj.data.vertices
    ]
    assert [tuple(p.vertices) for p in src.data.polygons] == [
        tuple(p.vertices) for p in obj.data.polygons
    ]
    for a, b in zip(src.data.uv_layers, obj.data.uv_layers):
        assert [tuple(d.uv) for d in a.data] == [tuple(d.uv) for d in b.data]
# Off-aperture slabs keep their original wall bounds; boolean returns local
# interpolation UV for new aperture reveals rather than a textureless overlay.
for src, obj in zip(sources[:2], owned[:2]):
    assert len(obj.data.uv_layers) == len(src.data.uv_layers)
    for axis in range(3):
        for op in [min, max]:
            assert (
                abs(
                    op(v.co[axis] for v in src.data.vertices)
                    - op(v.co[axis] for v in obj.data.vertices)
                )
                < 0.0001
            )
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
ref = (
    ROOT
    / "data/建筑图片/PEA_Peacock Theatre/01_建筑实拍/campus_photos_round3_PEA_sadlers_exterior_01.jpg"
)
target = origin + u * 2.03 - n * 4 + Vector((0, 0, 9.7))
position = target + n * 40 - u * 22 + Vector((0, 0, 9))
audit = {
    "baseline": str(BASE),
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalObjectCount": len(originals),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": [o.name for o in owned],
    "archivedObjects": SOURCES,
    "archiveObjects": SOURCES,
    "changes": changes,
    "destinationCollection": "PEA_EXTERIOR",
    "retainNewMaterials": True,
    "sourceCollections": {
        o.name: [c.name for c in o.users_collection] for o in sources
    },
    "reference": {
        "local": str(ref.relative_to(ROOT)),
        "sha256": hashlib.sha256(ref.read_bytes()).hexdigest(),
        "source": "https://www.sadlerswells.com/your-visit/peacock-theatre/",
        "imageArchiveUpload": "2023/09",
        "captureDate": "unknown",
        "currentOfficialPageChecked": True,
    },
    "wholeExteriorReview": {
        "massing": "Photo supports low broad podium plus narrower pale upper wing, dark side brick and neighbouring SAW kept separate. Existing GIS outline/19.5m and6.6m heights remain photo estimates.",
        "windows": "Retain three columns/three rows, top fanlights, original frames and sills. Nine upper windows already have true near-field masonry gaps.",
        "lowerFacade": "Blue-black/star fascia and pale portal retained. Actual entrance and ticket window were blocked by solid backing slabs; now cut through the existing black and pale slabs. No extra stars/signs/posters.",
        "sideAndRoof": "Current photo shows side brick, pale edge, low louvres; retained. Pale roof outriggers visible in photo remain not registered to native roof footprint, so not invented.",
        "glass": "11 original glass pieces retained, exact UV/geometry; bounded alpha/transmission. Upper glass retains source light neutral-green approximation, not a measured material spec.",
    },
    "cuts": cut_report,
    "ownedWallNormalsRecalculated": True,
    "wallApertureGridBefore": wall_before,
    "wallApertureGridAfter": wall_after,
    "rayTreeTopology": "Blender calc_loop_triangles actual triangulation, not polygon fan",
    "materialBefore": old_params,
    "materialAfter": new_params,
    "webOpacity": 0.82,
    "opticalSource": "Photo visual estimate, original colour preserved; remote shells remain16m away so do not use unlimited clear transparency.",
    "probes": probes,
    "beforeFrontProbes": before,
    "beforeBehindProbes": back_before,
    "afterFrontProbes": after,
    "afterBehindProbes": back_after,
    "nativePreviewCamera": {
        "position": list(position),
        "target": list(target),
        "orthoScale": 27,
    },
    "limitations": [
        "No measured2026 complete survey; mass height, window sizes, roof and unseen party elevations remain inherited estimates.",
        "Visible pale roof outrigger/pergola structure remains a documented whole-roof gap requiring plan registration.",
        "Nearest remote upper shell15.8m away; interior rooms, all ceiling/floor extents and per-window room boundaries not reconstructed. Horizontal rays do not establish absence of floor plates.",
        "Source entrance photograph is dark and glass reflectivity varies with daylight; optical parameters are bounded visual estimates, not glass specification.",
        "No fake room backing or fabricated current show posters.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_baseline()
collection = bpy.data.collections["PEA_EXTERIOR"]
sources = [bpy.data.objects[k] for k in SOURCES]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(audit["ownedObjects"])
for o in dst.objects:
    collection.objects.link(o)
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
    for l in sc.view_layers:
        l.update()
assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
assert cast() == after
assert cast(audit["ownedObjects"][2:], True) == back_after
assert (
    aperture_wall_grid([bpy.data.objects[k] for k in audit["ownedObjects"][:2]])
    == wall_after
)
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
assert all(
    float(bpy.data.objects[name].data.materials[0]["webOpacity"]) == 0.82
    for name in audit["ownedObjects"][2:]
)
verification = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalUvAndMaterialSlotsPreserved": True,
    "originalObjectCount": len(originals),
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest()
    == audit["baselineSha256"],
    "glassGeometryAndUvPreserved": True,
    "wallBoundsPreserved": True,
    "registeredGlassFirstHits": 11,
    "nearFieldRealApertureClearanceProbes": 11,
    "reloadedFrontProbes": after,
    "reloadedBehindProbes": back_after,
    "wallApertureThroughProbes": 18,
    "reloadedWallApertureGrid": wall_after,
    "webOpacity": 0.82,
    "reloadedBrowserOpacityVerified": True,
    "nativeRender": "reloaded-peacock-envelope.png",
    "rendered": False,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
scene = bpy.context.scene
for o in scene.objects:
    if o.type == "MESH" and o.name not in {o.name for o in collection.all_objects}:
        o.hide_render = True
camdata = bpy.data.cameras.new(PREFIX + "preview")
camera = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(camera)
camera.location = position
camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 27
scene.camera = camera
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1150
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-peacock-envelope.png")
bpy.ops.render.render(write_still=True)
verification["rendered"] = True
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("PEACOCK_ENVELOPE_COMPLETE", verification["componentSha256"], flush=True)
bpy.ops.wm.quit_blender()
