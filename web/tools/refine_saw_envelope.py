"""Add the three photographed six-leaf SAW facade shading groups.

Run in Blender. Existing glass, brick outlines and interiors are preserved.
Leaf depth, width and positions are photo-proportion estimates, not a survey.
"""

from pathlib import Path
import array, hashlib, json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/saw_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v138.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
OWNED = "SAW_NEXT_ENVELOPE_grouped_timber_shading"
COMPONENT = OUT / "saw-envelope-component.blend"


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    own = bpy.data.objects.get(OWNED)
    if own:
        mesh = own.data
        bpy.data.objects.remove(own, do_unlink=True)
        mesh.use_fake_user = False
        if not mesh.users:
            bpy.data.meshes.remove(mesh)
    for m in list(bpy.data.materials):
        if m.name.startswith("SAW_NEXT_ENVELOPE_") and m.users == int(m.use_fake_user):
            m.use_fake_user = False
            bpy.data.materials.remove(m)
    (
        scene.view_layers.update()
        if hasattr(scene.view_layers, "update")
        else bpy.context.view_layer.update()
    )
    return scene


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, n in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            v = array.array(kind, [0]) * (len(data) * n)
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


scene = open_baseline()
original = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
record = next(
    x
    for x in json.loads(
        (ROOT / "result/blender/stage82/saw-curtain-audit.json").read_text()
    )["facades"]
    if x["family"] == "north_fold"
)
p, u, n = map(Vector, [record["p"], record["u"], record["n"]])
length = record["length"]


def point(x, z, depth):
    return p + u * x + n * depth + Vector((0, 0, z))


# Photograph909_01: three equal six-leaf groups on the flat-head first-floor glazing.
# Fractions are measured by the overall facade width; perspective prevents surveyed precision.
centres = [length * f for f in [0.16, 0.36, 0.56]]
width = 0.045
pitch = 0.17
depthBounds = [-0.10, 0.10]
zBounds = [3.55, 7.70]
verts = []
faces = []
leafRecords = []
boxFaces = [
    (0, 4, 6, 2),
    (1, 3, 7, 5),
    (0, 1, 5, 4),
    (2, 6, 7, 3),
    (0, 2, 3, 1),
    (4, 5, 7, 6),
]
for group, centre in enumerate(centres):
    for leaf in range(6):
        x = centre + (leaf - 2.5) * pitch
        start = len(verts)
        for a, b, c in [
            (0, 0, 0),
            (0, 0, 1),
            (0, 1, 0),
            (0, 1, 1),
            (1, 0, 0),
            (1, 0, 1),
            (1, 1, 0),
            (1, 1, 1),
        ]:
            verts.append(
                point(x + (-width / 2, width / 2)[a], zBounds[b], depthBounds[c])
            )
        faces.extend(tuple(start + i for i in f) for f in boxFaces)
        leafRecords.append(
            {
                "group": group + 1,
                "leaf": leaf + 1,
                "x": x,
                "zBounds": zBounds,
                "depthBounds": depthBounds,
            }
        )
assert max(r["x"] + width / 2 for r in leafRecords) < record["headKnots"][1][0]
mat = bpy.data.materials["SAW_V82_jatoba"].copy()
mat.name = "SAW_NEXT_ENVELOPE_photographed_pale_timber"
mat.diffuse_color = (0.50, 0.43, 0.31, 1)
sh = mat.node_tree.nodes["Principled BSDF"]
sh.inputs["Base Color"].default_value = (0.50, 0.43, 0.31, 1)
sh.inputs["Roughness"].default_value = 0.55
mesh = bpy.data.meshes.new(OWNED)
mesh.from_pydata(verts, [], faces)
mesh.update()
mesh.materials.append(mat)
obj = bpy.data.objects.new(OWNED, mesh)
bpy.data.collections["SAW_EXTERIOR"].objects.link(obj)
bpy.context.view_layer.update()


def validate():
    assert all(
        fingerprint(bpy.data.objects[name]) == value for name, value in original.items()
    )
    assert all(
        [
            bpy.data.objects[name].hide_render,
            bpy.data.objects[name].hide_viewport,
            bpy.data.objects[name].hide_get(),
        ]
        == value
        for name, value in visibility.items()
    )
    trees = []
    for o in scene.objects:
        if (
            o.type == "MESH"
            and o.name.startswith("SAW")
            and not o.hide_render
            and not o.hide_get()
        ):
            trees.append(
                (
                    o.name,
                    BVHTree.FromPolygons(
                        [o.matrix_world @ v.co for v in o.data.vertices],
                        [tuple(poly.vertices) for poly in o.data.polygons],
                    ),
                )
            )

    def ray(origin, direction):
        hits = []
        for name, tree in trees:
            q, no, i, d = tree.ray_cast(origin, direction, 30)
            if q is not None:
                hits.append({"object": name, "distance": d})
        return min(hits, key=lambda row: row["distance"]) if hits else None

    probes = []
    for r in leafRecords:
        x = r["x"]
        z = sum(zBounds) / 2
        front = ray(point(x, z, 1), -n)
        assert front and front["object"] == OWNED, front
        behind = ray(point(x, z, -0.12), -n)
        assert behind and (
            "glazing_north_fold_panes" in behind["object"]
            or "curtain82_north_fold" in behind["object"]
        ), behind
        probes.append(
            {
                "group": r["group"],
                "leaf": r["leaf"],
                "frontFirstHit": front,
                "behindShadingFirstHit": behind,
            }
        )
    return probes


probes = validate()
bpy.data.libraries.write(str(COMPONENT), {obj}, fake_user=True)
photo = (
    ROOT
    / "data/建筑图片/SAW_Saw Swee Hock Student Centre/01_建筑实拍/architecture_round5_SAW_saw_909_01.jpg"
)
audit = {
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalFingerprints": original,
    "originalVisibility": visibility,
    "ownedObjects": [OWNED],
    "archivedObjects": [],
    "changes": [
        {
            "source": None,
            "owned": OWNED,
            "action": "add",
            "collection": "SAW_EXTERIOR",
            "retainNewMaterials": True,
        }
    ],
    "sourceObjects": [
        "SAW_D5_curtain82_north_fold_mullions",
        "SAW_D5_curtain82_north_fold_head",
        "SAW_NEXT_glazing_north_fold_panes",
    ],
    "destinationCollection": "SAW_EXTERIOR",
    "retainNewMaterials": True,
    "source": {
        "local": str(photo.relative_to(ROOT)),
        "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
        "url": "https://www.photography909.co.uk/saw-swee-hocklse-gallery",
        "stage": "built building;2017 upload path, capture date unknown",
    },
    "improvement": "Restore three clearly photographed six-leaf pale timber external shading groups on the main first-floor glazing. Existing generic mullions are retained and not counted as shading.",
    "registration": {
        "facade": "north_fold",
        "p": list(p),
        "u": list(u),
        "outwardNormal": list(n),
        "centreFractions": [0.16, 0.36, 0.56],
        "headFlatEnds": record["headKnots"][1][0],
        "leafWidth": width,
        "pitch": pitch,
        "zBounds": zBounds,
        "depthBounds": depthBounds,
        "existingGlassDepthBounds": [-0.33, -0.305],
        "minGlassToShadingGap": 0.205,
        "groups": 3,
        "leavesPerGroup": 6,
    },
    "leaves": leafRecords,
    "material": {
        "baseColorLinear": [0.50, 0.43, 0.31, 1],
        "roughness": 0.55,
        "basis": "Photo-estimated pale timber, no color chart. Existing jatoba shader copied; glass parameters unchanged.",
    },
    "limitations": [
        "Positions, section dimensions, timber species/color and fastening are photographic estimates, not an as-built survey.",
        "Only the three fully visible first-floor groups are built; no unseen/notch/upper-floor fins extrapolated.",
        "Perforated brick screen bands, folded silhouette and whole-building window columns remain inherited and unmeasured.",
        "No window backing, floor slab or interior partition added.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
scene = open_baseline()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = [OWNED]
for o in dst.objects:
    bpy.data.collections["SAW_EXTERIOR"].objects.link(o)
bpy.context.view_layer.update()
reloaded = validate()
assert len(bpy.data.objects[OWNED].data.vertices) == 144
proof = {
    "baselineSha256": audit["baselineSha256"],
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalObjectCount": len(original),
    "allOriginalFingerprintsPreserved": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "groups": 3,
    "leavesPerGroup": 6,
    "leafCount": 18,
    "frontFirstHitCount": 18,
    "surfaceProbes": reloaded,
    "wholeCampusSaved": False,
    "renderCount": 1,
}
# One overall native preview shows all groups alongside the folded masonry.
for o in scene.objects:
    if o.type != "CAMERA":
        o.hide_render = not o.name.startswith("SAW")
camdata = bpy.data.cameras.new("SAW_ENVELOPE_preview")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
focus = point(length * 0.56, 12, -2)
cam.location = focus + n * 55 + u * 5 + Vector((0, 0, 8))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 39
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
world = bpy.data.worlds.new("SAW_ENVELOPE_preview_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.65, 0.70, 0.75, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.65
scene.world = world
ld = bpy.data.lights.new("SAW_ENVELOPE_preview_area", "AREA")
ld.energy = 18000
ld.shape = "DISK"
ld.size = 25
light = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(light)
light.location = focus + n * 20 - u * 10 + Vector((0, 0, 25))
light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_x = 1100
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "reloaded-envelope.png")
bpy.ops.render.render(write_still=True)
proof["nativeRender"] = str(OUT / "reloaded-envelope.png")
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("SAW_ENVELOPE_VERIFIED", proof["componentSha256"])
bpy.ops.wm.quit_blender()
