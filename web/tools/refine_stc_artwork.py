"""Coarse native relief reconstruction of Warren Wilson's complete STC panel.
Uses manually registered historical photograph silhouettes, never a photo texture.
Run inside Blender; all paths/configuration are constants, no full campus save.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/stc_artwork_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v142.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
PREFIX = "STC_NEXT_ARTWORK_"
SOURCE = "STC_NEXT_ENVELOPE_corner_panel_proportions"
reg = json.loads((ROOT / "result/blender/stc_envelope_next/audit.json").read_text())[
    "registration"
][0]
C = Vector(reg["centre"])
U = Vector(reg["horizontalAxis"]).normalized()
N = Vector(reg["depthAxis"]).normalized()
W = 2.286
H = 11.5824
PHOTO = (
    ROOT
    / "data/建筑图片/STC_St Clement_s/01_建筑实拍/history_2015_warren_wilson_vertical_panel.jpg"
)
QUAD = [(135, 90), (186, 91), (208, 393), (110, 394)]
a = []
b = []
for (x, y), (u, v) in zip(QUAD, [(0, 0), (1, 0), (1, 1), (0, 1)]):
    a.extend([[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]])
    b.extend([u, v])
PHOTO_TO_UV = np.append(np.linalg.solve(a, b), 1).reshape(3, 3)


def uv(pixel):
    q = PHOTO_TO_UV @ [*pixel, 1]
    return (float(q[0] / q[2]), float(q[1] / q[2]))


def world(pixel, depth):
    u, v = uv(pixel)
    return C - U * ((u - 0.5) * W) + N * depth + Vector((0, 0, (0.5 - v) * H))


def fingerprint(o):
    h = hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, width in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            v = array.array(kind, [0]) * (len(data) * width)
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


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    prev = (
        json.loads((OUT / "audit.json").read_text())
        if (OUT / "audit.json").exists()
        else None
    )
    for o in list(bpy.data.objects):
        if o.name.startswith(PREFIX):
            bpy.data.objects.remove(o, do_unlink=True)
    if prev:
        for name in prev["archivedObjects"]:
            o = bpy.data.objects[name]
            s = prev["originalVisibility"][name]
            o.hide_render, o.hide_viewport = s[:2]
            o.hide_set(s[2])
    return bpy.context.scene, bpy.data.collections["STC_EXTERIOR"]


scene, col = open_base()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
owned = []
changes = []


def material(name, color, roughness, metallic=0):
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = m.diffuse_color
    p.inputs["Roughness"].default_value = roughness
    p.inputs["Metallic"].default_value = metallic
    return m


back = material("muted_mosaic_base", (0.39, 0.39, 0.32), 0.90)
silver = material("estimated_aluminium_frets", (0.72, 0.73, 0.70), 0.40, 0.65)
blue = material("thames_blue", (0.035, 0.12, 0.24), 0.82)
old = bpy.data.objects[SOURCE]
new = old.copy()
new.data = old.data.copy()
new.name = PREFIX + "background"
col.objects.link(new)
new.data.materials.clear()
new.data.materials.append(back)
old.hide_render = True
old.hide_set(True)
owned.append(new)
changes.append(
    {
        "source": SOURCE,
        "owned": new.name,
        "action": "Retain accepted panel geometry/centre/UV; replace uniform blue-grey placeholder finish with muted mosaic approximation.",
    }
)
# Shape vertices below are manually read photo pixels; perspective is rectified
# by the four-corner homography. No tesserae, engraving or unseen fasteners added.
SHAPES = {
    "clipper_ship": [
        [(143, 111), (180, 112), (174, 118), (149, 117)],
        [(159, 98), (150, 108), (159, 109)],
        [(164, 97), (173, 109), (164, 109)],
        [(151, 101), (146, 109), (151, 109)],
        [(160, 96), (162, 96), (162, 113), (160, 113)],
    ],
    "airplane": [
        [
            (146, 137),
            (156, 138),
            (176, 131),
            (183, 134),
            (167, 141),
            (178, 145),
            (174, 148),
            (160, 143),
            (150, 147),
            (147, 145),
            (155, 140),
        ]
    ],
    "royal_exchange": [
        [(137, 157), (185, 158), (185, 161), (137, 160)],
        [(136, 172), (186, 173), (185, 176), (136, 175)],
        *[
            [(x, 160), (x + 2.8, 160), (x + 2.8, 173), (x, 173)]
            for x in [140, 148, 156, 164, 172, 180]
        ],
    ],
    "justice": [
        [
            (144, 189),
            (150, 189),
            (153, 201),
            (151, 208),
            (156, 220),
            (145, 221),
            (141, 210),
            (144, 201),
        ],
        [(145, 191), (135, 190), (132, 194), (143, 196)],
        [(149, 190), (159, 190), (163, 194), (151, 196)],
        [(144, 218), (148, 218), (146, 228), (142, 228)],
        [(151, 218), (155, 219), (158, 226), (154, 228)],
        [
            (
                146 + 3 * math.cos(i * math.tau / 12),
                184 + 3 * math.sin(i * math.tau / 12),
            )
            for i in range(12)
        ],
    ],
    "westminster": [
        [
            (127, 250),
            (133, 245),
            (140, 251),
            (140, 281),
            (194, 281),
            (194, 293),
            (123, 294),
        ],
        [(133, 242), (135, 242), (135, 248), (133, 248)],
        [(131, 278), (136, 278), (136, 283), (131, 283)],
        [(148, 278), (153, 278), (153, 283), (148, 283)],
        [(177, 277), (182, 277), (182, 283), (177, 283)],
    ],
    "battersea_industry": [
        [
            (140, 347),
            (151, 346),
            (151, 323),
            (157, 319),
            (163, 324),
            (163, 343),
            (175, 343),
            (175, 322),
            (181, 319),
            (187, 325),
            (187, 354),
            (191, 359),
            (139, 361),
        ],
        [(134, 360), (194, 359), (190, 366), (139, 367)],
    ],
}


def mesh_group(name, mat, polygons, front, backdepth):
    verts = []
    faces = []
    for polygon in polygons:
        if name.startswith("mosaic_field_"):
            mapped = [uv(p) for p in polygon]
            for axis, bound, side in [(0, 0, 1), (0, 1, -1), (1, 0, 1), (1, 1, -1)]:
                clipped = []
                for i, q in enumerate(mapped):
                    p = mapped[i - 1]
                    pin = (p[axis] - bound) * side >= 0
                    qin = (q[axis] - bound) * side >= 0
                    if pin != qin:
                        t = (bound - p[axis]) / (q[axis] - p[axis])
                        clipped.append(
                            tuple(p[k] + t * (q[k] - p[k]) for k in range(2))
                        )
                    if qin:
                        clipped.append(q)
                mapped = clipped
            inverse = np.linalg.inv(PHOTO_TO_UV)
            polygon = []
            for p in mapped:
                q = inverse @ [*p, 1]
                polygon.append(tuple(q[:2] / q[2]))
        count = len(polygon)
        start = len(verts)
        verts.extend(world(p, depth) for depth in [backdepth, front] for p in polygon)
        # Triangulation preserves concave silhouettes; do not fan-fill their notches.
        from mathutils.geometry import tessellate_polygon

        coords = [Vector((*uv(p), 0)) for p in polygon]
        for tri in tessellate_polygon([coords]):
            idx = [
                (
                    int(q)
                    if isinstance(q, int)
                    else next(i for i, v in enumerate(coords) if (v - q).length < 1e-6)
                )
                for q in tri
            ]
            faces.append(tuple(start + count + i for i in idx))
            faces.append(tuple(start + i for i in reversed(idx)))
        faces.extend(
            (
                start + i,
                start + (i + 1) % count,
                start + count + (i + 1) % count,
                start + count + i,
            )
            for i in range(count)
        )
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    me.update()
    # Native object coordinates map directly to metric artwork UV without any image.
    layer = me.uv_layers.new(name="ArtworkMetricUV")
    for f in me.polygons:
        for i in f.loop_indices:
            p = me.vertices[me.loops[i].vertex_index].co - C
            layer.data[i].uv = (-p.dot(U) / W + 0.5, (p.z / H + 0.5))
    import bmesh

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
    o = bpy.data.objects.new(PREFIX + name, me)
    col.objects.link(o)
    owned.append(o)
    changes.append(
        {
            "source": None,
            "owned": o.name,
            "action": "Add coarse photo-registered "
            + name.replace("_", " ")
            + " native mesh; depth estimated.",
        }
    )
    return o


# Only broad muted fields, not invented tiny tesserae or a raster photograph.
fields = [
    ([(138, 92), (157, 92), (156, 128), (133, 130)], (0.43, 0.43, 0.31)),
    ([(157, 93), (184, 94), (188, 141), (156, 140)], (0.37, 0.39, 0.35)),
    ([(130, 143), (151, 144), (147, 178), (126, 179)], (0.48, 0.46, 0.36)),
    ([(151, 145), (189, 143), (192, 184), (150, 181)], (0.43, 0.42, 0.34)),
    ([(124, 181), (150, 181), (147, 239), (119, 244)], (0.39, 0.43, 0.35)),
    ([(151, 187), (191, 184), (199, 254), (146, 252)], (0.48, 0.45, 0.35)),
    ([(117, 264), (145, 264), (144, 331), (113, 334)], (0.32, 0.40, 0.35)),
    ([(153, 299), (201, 299), (206, 380), (159, 378)], (0.45, 0.43, 0.34)),
]
for i, (polygon, color) in enumerate(fields):
    mesh_group(
        "mosaic_field_" + str(i + 1),
        material("field_" + str(i + 1), color, 0.92),
        [polygon],
        0.0148,
        0.0132,
    )
riverpath = [
    (174, 119),
    (148, 127),
    (144, 145),
    (176, 183),
    (180, 201),
    (170, 219),
    (144, 234),
    (130, 256),
    (132, 279),
    (183, 301),
    (185, 318),
    (163, 343),
    (150, 379),
]
# Joined flat strip with rounded-direction sampling, width only a visual estimate.
left = []
right = []
riverpool = []
for k in range(len(riverpath) - 1):
    p0, p1, p2, p3 = [
        Vector(riverpath[max(0, min(j, len(riverpath) - 1))])
        for j in [k - 1, k, k + 1, k + 2]
    ]
    for step in range(6):
        t = step / 6
        v = 0.5 * (
            (2 * p1)
            + (-p0 + p2) * t
            + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
            + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t
        )
        riverpool.append(tuple(v))
riverpool.append(riverpath[-1])
for i, (x, y) in enumerate(riverpool):
    p = Vector((x, y))
    t = Vector(riverpool[min(i + 1, len(riverpool) - 1)]) - Vector(
        riverpool[max(0, i - 1)]
    )
    t.normalize()
    normal = Vector((-t.y, t.x))
    width = 5.0 + (y - 119) / 260 * 8
    left.append(tuple(p + normal * width / 2))
    right.append(tuple(p - normal * width / 2))
mesh_group("thames_meander", blue, [left + list(reversed(right))], 0.020, 0.015)
for name, polygons in SHAPES.items():
    mesh_group(name, silver, polygons, 0.055, 0.025)
OWNED = [o.name for o in owned]
PROBES = [
    ("clipper_ship", (160, 114)),
    ("airplane", (162, 140)),
    ("royal_exchange", (156, 159)),
    ("justice", (147, 205)),
    ("westminster", (155, 287)),
    ("battersea_industry", (170, 353)),
    ("thames_meander", (172, 219)),
    ("background", (197, 282)),
]


def checks():
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
    for name, pixel in PROBES:
        start = world(pixel, 0.7)
        best = None
        for o, tree in trees:
            hit = tree.ray_cast(start, -N, 1.5)
            if hit[0] is not None and (best is None or hit[3] < best[0]):
                best = (hit[3], o.name)
        assert best and best[1] == PREFIX + name, (name, pixel, best)
        records.append(
            {
                "motif": name,
                "photoPixel": pixel,
                "uv": uv(pixel),
                "firstSurface": best[1],
            }
        )
    for x, z in [
        (-W / 2 - 0.04, 0),
        (W / 2 + 0.04, 0),
        (0, -H / 2 - 0.04),
        (0, H / 2 + 0.04),
    ]:
        start = C + U * x + Vector((0, 0, z)) + N * 0.7
        best = None
        for o, tree in trees:
            hit = tree.ray_cast(start, -N, 1.5)
            if hit[0] is not None and (best is None or hit[3] < best[0]):
                best = (hit[3], o.name)
        assert best and best[1] == "STC_NEXT_ENVELOPE_corner_panel_frame", (x, z, best)
        records.append(
            {
                "motif": "preserved-border",
                "panelLocalXZ": [x, z],
                "firstSurface": best[1],
            }
        )
    return records


records = checks()
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
component = OUT / "stc-artwork-component.blend"
bpy.data.libraries.write(str(component), set(owned), fake_user=True)
audit = {
    "baseline": str(BASE.relative_to(ROOT)),
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": OWNED,
    "archivedObjects": [SOURCE],
    "changes": changes,
    "reference": {
        "path": str(PHOTO.relative_to(ROOT)),
        "sha256": hashlib.sha256(PHOTO.read_bytes()).hexdigest(),
        "sourceUrl": "https://blogs.lse.ac.uk/lsehistory/2015/07/09/printing-presses-and-science-labs-the-story-of-st-clements/",
        "captureDate": "unknown;2015article publication is not capture date",
        "resolution": [324, 478],
        "effectivePanelPixelsApprox": [51, 98, 306],
    },
    "registration": {
        "photoCorners": QUAD,
        "photoToPanelUV": PHOTO_TO_UV.tolist(),
        "panelCentre": list(C),
        "nativeGeometryAxis": list(U),
        "photoHorizontalAxis": list(-U),
        "outwardAxis": list(N),
        "preservedDimensions": [W, H],
        "depthEstimate": {
            "baseFront": 0.01303,
            "colourFields": 0.0148,
            "riverFront": 0.020,
            "aluminiumFront": 0.055,
            "aluminiumBack": 0.025,
        },
        "photoSilhouettePolygons": SHAPES,
        "thamesSourcePath": riverpath,
    },
    "scope": "Six identifiable historical raised motifs plus a blue Thames meander and eight restrained mosaic fields replace the uniform placeholder. Existing panel dimensions/frame and bottom text plaque are preserved.",
    "limitations": [
        "Historical low-resolution photo with strong vertical perspective; four-corner registration and silhouettes manually estimated, not a scan.",
        "No exact fret geometry, engraved details, tiny tesserae, material depth or current2026appearance claimed.",
        "Columns and foreground industry chimneys are coarse visible shape groupings; hidden components not inferred.",
        "No source photo/crop/raster texture embedded or exported; native polygon geometry and plain PBR only.",
    ],
    "firstSurfaceChecks": records,
}
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
scene, col = open_base()
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
bpy.data.objects[SOURCE].hide_render = True
bpy.data.objects[SOURCE].hide_set(True)
reloaded = checks()
assert reloaded == records
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in originals.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
    if n != SOURCE
)
proof = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalObjectCount": len(originals),
    "unrelatedVisibilityPreserved": True,
    "fullModelSaved": False,
    "firstSurfaceChecks": reloaded,
    "embeddedImageTextures": 0,
    "motifCount": 6,
    "originalBorderPreserved": True,
    "textPlaqueChanged": False,
}
visible = {o.name for o in col.all_objects}
for o in scene.objects:
    if o.type == "MESH" and o.name not in visible:
        o.hide_render = True
cd = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
focus = C
cam.location = focus + N * 25 + U * 0.5 + Vector((0, 0, 0.4))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 14
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 850
scene.render.resolution_y = 1500
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "reloaded-artwork.png")
bpy.ops.render.render(write_still=True)
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("STC_ARTWORK_VERIFIED", len(originals), len(reloaded))
bpy.ops.wm.quit_blender()
