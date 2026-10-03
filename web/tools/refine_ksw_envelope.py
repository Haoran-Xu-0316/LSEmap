"""Correct photographed KSW street-level glazed storefront divisions and finish.
Run in Blender Text Editor. Upper storeys and unseen elevations remain unchanged.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/ksw_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v139.blend"
BASE_SHA = "f0e9fe3b5be9fa073c10d0a92efc69ca22a5d2689bdfee4519d117e0f90b74ee"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
families = [
    "window_glass",
    "window_outer_frames",
    "window_mullions",
    "window_glazing_bars",
]
SOURCES = ["KSW_D3_" + f for f in families]
NAMES = ["KSW_NEXT_ENVELOPE_" + f for f in families] + [
    "KSW_NEXT_ENVELOPE_opaque_storefront_bands"
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
collection = bpy.data.collections["KSW_EXTERIOR"]
record = next(
    b
    for b in json.loads((ROOT / "result/blender/site_geometry.json").read_text())[
        "buildings"
    ]
    if b["code"] == "KSW"
)
ring = record["rings"][0]
a, b = Vector((*ring[11], 0)), Vector((*ring[0], 0))
origin = (a + b) / 2
u = (b - a).normalized()
n = Vector((u.y, -u.x, 0))
center = Vector((*record["center"], 0))
if (origin - center).dot(n) < 0:
    n = -n


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(n), p.z))


def world(p):
    return origin + u * p.x + n * p.y + Vector((0, 0, p.z))


def parts(bm):
    seen = set()
    for seed in bm.verts:
        if seed in seen:
            continue
        part = []
        todo = [seed]
        seen.add(seed)
        while todo:
            v = todo.pop()
            part.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if o not in seen:
                    seen.add(o)
                    todo.append(o)
        yield part


def ground(ps):
    return min(p.z for p in ps) > 1.0 and max(p.z for p in ps) < 5.0


finish = bpy.data.materials.new("KSW_NEXT_ENVELOPE_dark_storefront_paint")
finish.use_nodes = True
finish.diffuse_color = (0.024, 0.035, 0.043, 1)
shader = finish.node_tree.nodes["Principled BSDF"]
shader.inputs["Base Color"].default_value = finish.diffuse_color
shader.inputs["Metallic"].default_value = 0.25
shader.inputs["Roughness"].default_value = 0.46
owned = []
counts = []
windows = []
for family, source_name, name in zip(families, SOURCES, NAMES):
    source = bpy.data.objects[source_name]
    assert not source.hide_render
    o = source.copy()
    o.data = source.data.copy()
    o.name = name
    o.data.name = name
    collection.objects.link(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    selected = [
        part
        for part in parts(bm)
        if ground([local(o.matrix_world @ v.co) for v in part])
    ]
    assert selected
    if family == "window_glass":
        assert len(selected) == 2
        for part in selected:
            assert len(part) == 8
            ps = [local(o.matrix_world @ v.co) for v in part]
            lo, hi = min(p.z for p in ps), max(p.z for p in ps)
            band_lo = lo + 0.70 * (hi - lo)
            band_hi = lo + 0.82 * (hi - lo)
            windows.append(
                {
                    "x0": min(p.x for p in ps),
                    "x1": max(p.x for p in ps),
                    "depth": max(p.y for p in ps),
                    "low": lo,
                    "high": hi,
                    "bandLow": band_lo,
                    "bandHigh": band_hi,
                }
            )
            geom = (
                list(part)
                + list({e for v in part for e in v.link_edges})
                + list({f for v in part for f in v.link_faces})
            )
            new = bmesh.ops.duplicate(bm, geom=geom)
            upper = [v for v in new["geom"] if isinstance(v, bmesh.types.BMVert)]
            for v in part:
                p = o.matrix_world @ v.co
                if p.z > (lo + hi) / 2:
                    p.z = band_lo
                    v.co = o.matrix_world.inverted() @ p
            for v in upper:
                p = o.matrix_world @ v.co
                if p.z < (lo + hi) / 2:
                    p.z = band_hi
                    v.co = o.matrix_world.inverted() @ p
    else:
        o.data.materials.append(finish)
        idx = len(o.data.materials) - 1
        if family == "window_glazing_bars":
            bmesh.ops.delete(
                bm, geom=[v for part in selected for v in part], context="VERTS"
            )
            # Actual band boundaries replace the two equal-height horizontal divisions.
            inverse = o.matrix_world.inverted()
            for w in windows:
                for z in [w["bandLow"], w["bandHigh"]]:
                    x0, x1 = w["x0"], w["x1"]
                    d = w["depth"] + 0.065
                    coords = [
                        (x0, d - 0.03, z - 0.025),
                        (x0, d - 0.03, z + 0.025),
                        (x1, d - 0.03, z - 0.025),
                        (x1, d - 0.03, z + 0.025),
                        (x0, d + 0.03, z - 0.025),
                        (x0, d + 0.03, z + 0.025),
                        (x1, d + 0.03, z - 0.025),
                        (x1, d + 0.03, z + 0.025),
                    ]
                    vs = [bm.verts.new(inverse @ world(Vector(p))) for p in coords]
                    for f in [
                        (0, 2, 6, 4),
                        (1, 5, 7, 3),
                        (0, 4, 5, 1),
                        (2, 3, 7, 6),
                        (0, 1, 3, 2),
                        (4, 6, 7, 5),
                    ]:
                        bm.faces.new([vs[i] for i in f]).material_index = idx
        else:
            for f in {f for part in selected for v in part for f in v.link_faces}:
                f.material_index = idx
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    owned.append(o)
    counts.append({"family": family, "selectedConnectedParts": len(selected)})
# Opaque infill is genuine geometry, with no transparent glass behind its zone.
source = bpy.data.objects[SOURCES[0]]
band = source.copy()
band.data = source.data.copy()
band.name = NAMES[4]
band.data.name = band.name
collection.objects.link(band)
bm = bmesh.new()
bm.from_mesh(band.data)
for part in list(parts(bm)):
    ps = [local(band.matrix_world @ v.co) for v in part]
    if not ground(ps):
        bmesh.ops.delete(bm, geom=part, context="VERTS")
        continue
    lo, hi = min(p.z for p in ps), max(p.z for p in ps)
    for v, p in zip(part, ps):
        p.z = lo + (0.70 if p.z < (lo + hi) / 2 else 0.82) * (hi - lo)
        p.y += 0.035
        v.co = band.matrix_world.inverted() @ world(p)
bm.to_mesh(band.data)
bm.free()
band.data.materials.clear()
band.data.materials.append(finish)
for f in band.data.polygons:
    f.material_index = 0
band.data.update()
owned.append(band)
probes = []
for i, w in enumerate(windows):
    for fraction in [0.2, 0.5, 0.8]:
        probes.append(
            {
                "kind": "opaqueBand",
                "x": w["x0"] + (w["x1"] - w["x0"]) * fraction,
                "z": (w["bandLow"] + w["bandHigh"]) / 2,
            }
        )
    for fraction in [0.25, 0.55]:
        for height in [0.30, 0.91]:
            probes.append(
                {
                    "kind": "upperLowerGlass",
                    "x": w["x0"] + (w["x1"] - w["x0"]) * fraction,
                    "z": w["low"] + (w["high"] - w["low"]) * height,
                }
            )
# Existing upper frames, window columns and curved central bay are retained.
for x in [-3.5, -1.75, 0.3, 1.75, 3.5]:
    for z in [11.0, 14.5, 18.0]:
        probes.append({"kind": "retainedUpper", "x": x, "z": z})


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
        h = tree.ray_cast(world(Vector((p["x"], 2.5, p["z"]))), -n, 5)
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
assert all(
    p["firstObject"] == NAMES[4] for p in after if p["kind"] == "opaqueBand"
), after
assert all(
    p["firstObject"] == NAMES[0] for p in after if p["kind"] == "upperLowerGlass"
), after
assert [
    {**p, "firstObject": aliases.get(p["firstObject"], p["firstObject"])}
    for p in after
    if p["kind"] == "retainedUpper"
] == [p for p in before if p["kind"] == "retainedUpper"]
assert all(fingerprint(bpy.data.objects[name]) == v for name, v in originals.items())
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


component = OUT / "kingsway-envelope-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True, compress=True)
photo = ROOT / "data/建筑图片/KSW_20 Kingsway/01_建筑实拍/exteriors_lse_estate_009.jpg"
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
            "action": "Correct only photographed ground storefront glazing and dark frame finish; keep all upper geometry",
        }
        for s, o in zip(SOURCES, NAMES)
    ]
    + [
        {
            "source": None,
            "owned": NAMES[4],
            "action": "Add2 opaque horizontal infill bands inside the existing street openings",
        }
    ],
    "references": [
        {
            "local": str(photo.relative_to(ROOT)),
            "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
            "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/20KSW-web.jpg",
            "captureDate": "unknown",
        },
        {
            "local": "data/documents/property_handbook.pdf",
            "sha256": hashlib.sha256(
                (ROOT / "data/documents/property_handbook.pdf").read_bytes()
            ).hexdigest(),
            "physicalPage": 24,
            "printedPage": 22,
            "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf",
            "captureDate": "unknown",
            "supports": "Dark ground shopfront framework, short upper glazing above a broad opaque dark horizontal band; stone portal/red first-floor rustication preserved.",
        },
    ],
    "storefrontRegistration": {
        "windows": windows,
        "opaqueBandFractionFromSill": [0.70, 0.82],
        "dimensionMethod": "Estimated street-level band proportions from two oblique official photographs; inherited opening sill/head retained",
        "absoluteDimensionsEstimated": True,
    },
    "geometryChanges": counts,
    "materials": {
        "originalSources": [
            {"source": s, "pbr": pbr(bpy.data.objects[s].data.materials[0])}
            for s in SOURCES
        ],
        "newGroundPaint": pbr(finish),
        "retainedGlazingUnchanged": True,
        "upperFrameMaterialsUnchanged": True,
    },
    "beforeProbes": before,
    "afterProbes": after,
    "wholeFacadeReview": {
        "upper": "Existing upper brick5-column facade and pale-stone oriel retained;300×400 estate photo only partially covers upper levels and cannot establish roof/crown accurately.",
        "red": "Accepted red first-floor blockwork/joints retained, not recoloured.",
        "ground": "Correct short upper glazing/dark infill relationship within both retained openings; old equally spaced horizontal bars removed.",
        "oriel": "54 curved geometry preserved; exact upper curvature/column schedule still not surveyed.",
        "portal": "Stone quoins, cartouche, doorway and entry steps unchanged.",
        "rear": "Unseen elevations and all room samples untouched.",
    },
    "limitations": [
        "Official photograph dates unknown; no contemporary site-survey claim.",
        "Band position, thickness and paint reflectance are estimates.",
        "Ground vertical bay counts retained because obscured/oblique photographs do not establish a reliable complete sash schedule.",
        "Upper crown, full high-level oriel articulation, rear facade and exact current glazing optics remain unresolved.",
        "No false rooms or backing walls added behind glazing.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
print("KSW_ENVELOPE_SAVED", counts, flush=True)
open_base()
collection = bpy.data.collections["KSW_EXTERIOR"]
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = NAMES
for o in dst.objects:
    collection.objects.link(o)
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
focus = world(Vector((0, 0, 10)))
camera = bpy.data.cameras.new("KSW_NEXT_ENVELOPE_review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = focus + n * 45 + Vector((0, 0, 1))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 23
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1050
scene.render.resolution_y = 1450
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-kingsway-envelope.png")
bpy.ops.render.render(write_still=True)
verification = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "originalObjectCount": len(originals),
    "reloadedProbes": after,
    "nativeRender": "reloaded-kingsway-envelope.png",
    "storefrontWindows": 2,
    "opaqueBands": 2,
    "upperGeometryProbesUnchanged": True,
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("KSW_ENVELOPE_REOPENED_VERIFIED", len(originals), len(after), flush=True)
bpy.ops.wm.quit_blender()
