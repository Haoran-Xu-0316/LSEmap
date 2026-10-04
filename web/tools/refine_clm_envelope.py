"""Open documented Clement House street-window reveals and retain muted bronze glass.
Run inside Blender. All metric frontage dimensions remain inherited estimates.
Only an owned component is written; original campus geometry is never modified.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/clm_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v144.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
COMPONENT = OUT / "clement-envelope-component.blend"
PREFIX = "CLM_NEXT_ENVELOPE_"
RENDER_NATIVE_PREVIEW = (
    False  # Existing preview used identical optical/geometry parameters.
)
SOURCES = [
    "CLM_V114_retained_D3_recess_shadow_liners",
    "CLM_V114_retained_D3_window_glass",
    "CLM_NEXT_FACADE_split_tall_panes",
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
collection = bpy.data.collections["CLM_EXTERIOR"]
rec = next(
    b
    for b in json.loads((ROOT / "result/blender/site_geometry.json").read_text())[
        "buildings"
    ]
    if b["code"] == "CLM"
)
centre = Vector(rec["center"])
pts = [Vector(rec["rings"][0][i]) for i in (5, 4, 3, 2, 1)]
segments = []
length = 0
for a, b in zip(pts, pts[1:]):
    u = (b - a).normalized()
    n = Vector((u.y, -u.x))
    n = -n if n.dot((a + b) / 2 - centre) < 0 else n
    size = (b - a).length
    segments.append((length, length + size, a, u, n))
    length += size


def axes(p):
    def distance(t):
        _, _, a, u, n = t
        s = max(0, min(t[1] - t[0], (Vector(p[:2]) - a).dot(u)))
        return (Vector(p[:2]) - a - u * s).length

    st, en, a, u, n = min(segments, key=distance)
    return Vector((u.x, u.y, 0)), Vector((n.x, n.y, 0))


def glass_probes(objects):
    result = []
    for obj in objects:
        for k, ids in enumerate(parts(obj.data)):
            vs = [obj.matrix_world @ obj.data.vertices[i].co for i in ids]
            c = sum(vs, Vector()) / len(vs)
            u, n = axes(c)
            # Off-center location avoids the photographed three-column mullions and rails.
            p = c + u * 0.22 + Vector((0, 0, 0.13))
            result.append(
                {
                    "label": obj.name + "-" + str(k),
                    "source": obj.name,
                    "center": list(c),
                    "point": list(p),
                    "normal": list(n),
                }
            )
    return result


sources = [bpy.data.objects[n] for n in SOURCES]
assert all(not o.hide_render for o in sources)
probes = glass_probes(sources[1:])
assert len(probes) == 39
owned = []
changes = []
for source in sources:
    o = source.copy()
    o.data = source.data.copy()
    o.name = PREFIX + (
        "open_four_sided_reveals"
        if source == sources[0]
        else "street_glass" if source == sources[1] else "tall_split_glass"
    )
    o.data.name = o.name
    collection.objects.link(o)
    owned.append(o)
    changes.append(
        {
            "source": source.name,
            "owned": o.name,
            "action": (
                "Remove only closed front/back reveal caps; preserve original jamb/soffit/sill faces and UV"
                if source == sources[0]
                else "Retain exact glass geometry/UV; replace opaque material with bounded translucent muted glass"
            ),
        }
    )
reveal = owned[0]
bm = bmesh.new()
bm.from_mesh(reveal.data)
remove = []
for face in bm.faces:
    c = reveal.matrix_world @ face.calc_center_median()
    u, n = axes(c)
    normal = (
        reveal.matrix_world.to_3x3().inverted().transposed() @ face.normal
    ).normalized()
    if abs(normal.dot(n)) > 0.97:
        remove.append(face)
assert len(remove) == 50, len(remove)
bmesh.ops.delete(bm, geom=remove, context="FACES_ONLY")
bm.to_mesh(reveal.data)
bm.free()
reveal.data.update()
assert len(reveal.data.polygons) == 100
original_material = sources[1].data.materials[0]
material = original_material.copy()
material.name = PREFIX + "muted_bronze_translucent_glass"
pr = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
original_params = {
    k: (
        list(pr.inputs[k].default_value)
        if k == "Base Color"
        else pr.inputs[k].default_value
    )
    for k in [
        "Base Color",
        "Roughness",
        "Metallic",
        "Alpha",
        "Transmission Weight",
        "IOR",
    ]
}
# Photograph-guided bounded transmission: keep neutral tint and reflection. This
# is not clear glass, measured optical data or permission to invent rooms.
pr.inputs["Alpha"].default_value = 0.82
pr.inputs["Transmission Weight"].default_value = 0.22
pr.inputs["Roughness"].default_value = 0.26
pr.inputs["Metallic"].default_value = 0.12
pr.inputs["IOR"].default_value = 1.45
material.diffuse_color = tuple(original_material.diffuse_color[:3]) + (0.82,)
material["webOpacity"] = 0.82
for o in owned[1:]:
    o.data.materials.clear()
    o.data.materials.append(material)
new_params = {
    k: (
        list(pr.inputs[k].default_value)
        if k == "Base Color"
        else pr.inputs[k].default_value
    )
    for k in original_params
}


def raytree(exclude=()):
    vs = []
    fs = []
    names = []
    # Include genuine public interiors across all scenes, rather than confuse a
    # horizontal ray missing floors with proof that no floors exist.
    objects = [
        o
        for o in bpy.data.objects
        if o.type == "MESH"
        and not o.hide_render
        and o.name not in exclude
        and (
            o.name.startswith("CLM_")
            or "CLM" in [c.name for c in o.users_collection]
            or any("CLM" in c.name for c in o.users_collection)
        )
    ]
    for o in objects:
        k = len(vs)
        vs.extend(o.matrix_world @ v.co for v in o.data.vertices)
        fs.extend(tuple(k + i for i in p.vertices) for p in o.data.polygons)
        names.extend([o.name] * len(o.data.polygons))
    return BVHTree.FromPolygons(vs, fs), names


def cast(probes, exclude=(), behind=False):
    tree, names = raytree(exclude)
    results = []
    for p in probes:
        n = Vector(p["normal"])
        start = Vector(p["point"]) + n * (-0.05 if behind else 0.9)
        h = tree.ray_cast(start, -n, 40)
        results.append(
            {
                "label": p["label"],
                "firstObject": names[h[2]] if h[2] is not None else None,
                "distance": h[3],
                "hit": list(h[0]) if h[0] else None,
            }
        )
    return results


before = cast(probes, exclude=[o.name for o in owned])
before_back = cast(probes, exclude=[o.name for o in owned] + SOURCES[1:], behind=True)
for o in sources:
    o.hide_render = True
    o.hide_set(True)
after = cast(probes)
after_back = cast(probes, exclude=[o.name for o in owned[1:]], behind=True)
assert all(
    p["firstObject"] == changes[1 if p["label"].startswith(SOURCES[1]) else 2]["owned"]
    for p in after
), after
# The near original liner cap sat 24 mm behind glass. A true aperture must be
# unobstructed across its original recess depth, not merely a transparent pane.
assert all(
    p["distance"] is None or p["distance"] > 0.65 for p in after_back
), after_back
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
    if n not in SOURCES
)
for source, o in zip(sources[1:], owned[1:]):
    assert [tuple(v.co) for v in source.data.vertices] == [
        tuple(v.co) for v in o.data.vertices
    ]
    assert [tuple(p.vertices) for p in source.data.polygons] == [
        tuple(p.vertices) for p in o.data.polygons
    ]
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
focus_xy = sum((a for _, _, a, _, _ in segments), Vector((0, 0))) / len(segments)
u, n = axes(Vector((focus_xy.x, focus_xy.y, 13)))
target = Vector((focus_xy.x, focus_xy.y, 13.5))
position = target + n * 44 + u * 6 + Vector((0, 0, 4))
references = []
for name, date in [
    ("result/blender/stage73/clm-2018.jpg", "2018-04-24"),
    ("result/blender/stage73/clm-2023.jpg", "2023-11-15"),
    (
        "data/建筑图片/CLM_Clement House/01_建筑实拍/exteriors_lse_estate_003.jpg",
        "unknown",
    ),
]:
    f = ROOT / name
    references.append(
        {
            "local": name,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "captureDate": date,
        }
    )
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
    "destinationCollection": "CLM_EXTERIOR",
    "retainNewMaterials": True,
    "references": references,
    "wholeExteriorReview": {
        "massing": "Retain seven-bay convex stone frontage, five dormers and four chimneys; dates/photos establish topology but heights/GIS bow remain estimates. No documented distinct tower to invent.",
        "windows": "39 existing glass boxes in lower/small upper tiers and fourteen split tall panes; preserve all frame arrangements, genuine opaque mid-window bands and window positions.",
        "streetAndEntry": "Central colonnade, side carved timber portals, entrance stone and existing steps retained.",
        "roof": "Five dormer and seven attic glass retained opaque because this scope does not register their back shells; no invented rear elevation.",
        "stone": "Original Portland stone, courses, piers, ledges and opaque brown strips retained.",
    },
    "resolvedIssue": "25 closed full-window dark recess cuboids covered the true window opening immediately behind glass. Remove their 50 vertical cap faces while retaining all100 perimeter faces; existing stone openings need no recut.",
    "removedRevealCaps": 50,
    "retainedRevealFaces": 100,
    "registeredStreetGlassCount": 39,
    "materialBefore": original_params,
    "materialAfter": new_params,
    "glassParameterSource": "Original neutral tint retained. Alpha0.82/transmission0.22/roughness0.26/metallic0.12/IOR1.45 are photographic visual estimates, not measured bronze/glass specifications. Explicit limited transparency prevents remote empty shell from dominating.",
    "probes": probes,
    "beforeFrontProbes": before,
    "beforeBehindProbes": before_back,
    "afterFrontProbes": after,
    "afterBehindProbes": after_back,
    "nativePreviewCamera": {
        "position": list(position),
        "target": list(target),
        "orthoScale": 37,
    },
    "limitations": [
        "Complete rooms and per-window room boundary registration remain absent. Horizontal rays find remote retained building walls15–32m away; they do not prove floors missing. No fictitious backplate/room/floor added.",
        "Photo trees/vehicles obscure finer casement hardware and lower pedestrian passage geometry.",
        "Rear massing, rear openings and present-day roof equipment remain unverified.",
        "Transparency is bounded visual estimate; no claim of clear see-through whole building or measured2026 survey.",
    ],
}
audit["webOpacity"] = 0.82
audit["nativePreviewReuse"] = (
    "Previously inspected native preview has identical geometry and Principled parameters; explicit webOpacity affects browser export only."
)
audit["sourceCollections"] = {
    o.name: [c.name for c in o.users_collection] for o in sources
}
audit["nativePreviewLimitations"] = [
    "One native preview exposes all window tiers; rightmost bay partially cropped. The39 aperture probes include that whole bay. Existing black background/lighting retained; EEVEE alpha dithering produces grain, not a new surface texture."
]
audit["nearApertureVerification"] = {
    "glassBoxBackDepthFromStreet": 0.201,
    "originalRevealFrontDepthFromStreet": 0.225,
    "gap": 0.024,
    "behindRayOrigin": "5cm inward from glass mid-plane, beyond both glass surfaces",
    "afterMinimumHorizontalFirstHitDistance": min(
        p["distance"] for p in after_back if p["distance"] is not None
    ),
    "remotesNotInteriors": True,
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_baseline()
collection = bpy.data.collections["CLM_EXTERIOR"]
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
assert all(
    float(o.data.materials[0]["webOpacity"]) == 0.82
    for o in dst.objects
    if o.name in audit["ownedObjects"][1:]
)
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert cast(probes) == after
assert cast(probes, exclude=audit["ownedObjects"][1:], behind=True) == after_back
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
    if n not in SOURCES
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
    "reloadedFrontProbes": after,
    "reloadedBehindProbes": after_back,
    "streetGlassFirstHits": 39,
    "windowOpeningClearWithinRecessDepth": 39,
    "originalGlassGeometryPreserved": True,
    "originalRoofAndStoneAndEntryPreserved": True,
    "retainedRevealFaces": 100,
    "removedCapFaces": 50,
    "nativeRender": "reloaded-clement-envelope.png",
    "rendered": False,
    "webOpacity": 0.82,
    "reloadedBrowserOpacityVerified": True,
    "nativePreviewReused": True,
    "nativePreviewReuseReason": "Identical geometry and Principled optics; only explicit browser export custom property added.",
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
scene = bpy.context.scene
for o in scene.objects:
    if o.type == "MESH" and o.name not in {o.name for o in collection.all_objects}:
        o.hide_render = True
camera_data = bpy.data.cameras.new(PREFIX + "preview_camera")
camera = bpy.data.objects.new(camera_data.name, camera_data)
scene.collection.objects.link(camera)
camera.location = position
camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
camera_data.type = "ORTHO"
camera_data.ortho_scale = 37
scene.camera = camera
if RENDER_NATIVE_PREVIEW:
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1250
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(OUT / "reloaded-clement-envelope.png")
    bpy.ops.render.render(write_still=True)
    verification["rendered"] = True
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
print("CLM_ENVELOPE_COMPLETE", verification["componentSha256"], flush=True)
bpy.ops.wm.quit_blender()
