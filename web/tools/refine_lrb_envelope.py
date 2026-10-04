"""Restore the photographed Blue Rain display as a static LRB facade study.
Run in Blender. Photo samples are not the23520physical LEDs or live library data.
"""

from pathlib import Path
import array, hashlib, json
from collections import Counter
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lrb_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v140.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
OWN = "LRB_NEXT_ENVELOPE_Blue_Rain_static_photo_display"
COMP = OUT / "library-envelope-component.blend"
SOURCE = "LRB_V109_facade_wall_0_0"
WALL = "LRB_NEXT_ENVELOPE_continuous_artwork_corner_wall"


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    for name in [
        o.name for o in bpy.data.objects if o.name.startswith("LRB_NEXT_ENVELOPE_")
    ]:
        obj = bpy.data.objects.get(name)
        if obj:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    prior = OUT / "audit.json"
    if prior.exists():
        audit = json.loads(prior.read_text())
        for name in audit.get("archivedObjects", []):
            old = bpy.data.objects[name]
            v = audit["originalVisibility"][name]
            old.hide_render, old.hide_viewport = v[:2]
            old.hide_set(v[2])
    for mat in list(bpy.data.materials):
        if mat.name.startswith("LRB_NEXT_ENVELOPE_") and mat.users == int(
            mat.use_fake_user
        ):
            mat.use_fake_user = False
            bpy.data.materials.remove(mat)
    # Restore only this component and its one archived source on latest fallback.
    bpy.context.view_layer.update()
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
ring = next(
    b["rings"][0]
    for b in json.loads((ROOT / "result/blender/site_geometry.json").read_text())[
        "buildings"
    ]
    if b["code"] == "LRB"
)
p, q = [Vector((*ring[i], 0)) for i in [0, 1]]
u = (q - p).normalized()
n = Vector((u.y, -u.x, 0))
buildingCentre = sum((Vector((*v, 0)) for v in ring), Vector()) / len(ring)
if n.dot((p + q) * 0.5 - buildingCentre) < 0:
    n = -n
length = (q - p).length
width = 2.38
xStart = (length - width) / 2
zBottom, zTop = 5.55, 19.35
samples = json.loads((OUT / "display-samples.json").read_text())
source = bpy.data.objects[SOURCE]
hostTree = BVHTree.FromPolygons(
    [source.matrix_world @ v.co for v in source.data.vertices],
    [tuple(f.vertices) for f in source.data.polygons],
)


def wall_point(x, z, depth=0):
    return p + u * x + Vector((0, 0, z)) + n * depth


# The inherited generic chamfer incorrectly contains four large upper apertures.
# The complete official night corner photo shows a continuous brick art pier.
# Fill only those exact existing apertures on an owned wall copy; no window backing.
apertures = [(5.715, 8.453), (9.940, 12.327), (14.204, 16.701), (18.070, 19.776)]
before = []
for lo, hi in apertures:
    hit = hostTree.ray_cast(wall_point(length / 2, (lo + hi) / 2, 1), -n, 2)
    assert hit[0] is None
    before.append({"zBounds": [lo, hi], "sourceWallSurfacePresent": False})
wall = source.copy()
wall.data = source.data.copy()
wall.name = WALL
wall.data.name = WALL
bpy.data.collections["LRB_EXTERIOR"].objects.link(wall)
bm = bmesh.new()
bm.from_mesh(wall.data)
inverse = wall.matrix_world.inverted()
for lo, hi in apertures:
    corners = [
        wall_point(x, z)
        for x, z in [(0.592, lo), (2.651, lo), (2.651, hi), (0.592, hi)]
    ]
    vs = [bm.verts.new(inverse @ v) for v in corners]
    face = bm.faces.new(vs)
    face.material_index = 0
    if (wall.matrix_world.to_3x3() @ face.normal).dot(n) < 0:
        face.normal_flip()
bm.normal_update()
bm.to_mesh(wall.data)
bm.free()
wall.data.update()
source.hide_render = True
source.hide_set(True)
# Remove only the exact false window components contained in the four filled
# apertures, preserving all other polygon records, UVs and material slots.
ownedWindowCopies = []
windowChanges = []
removedFaces = {}
for old in list(scene.objects):
    if old.type != "MESH" or not old.name.startswith(
        "LRB_V117_retained_LRB_V110_retained_"
    ):
        continue
    if not any(
        token in old.name
        for token in [
            "Glazing_bays",
            "Stone_jamb",
            "glazing_seal",
            "reveal_bead",
            "sill_drain_slot",
            "folded_jamb_return",
            "cap_shadow_joint",
            "metal_sill_channel",
            "head_flashing",
            "flashing_downstand",
            "sill_front_fascia",
        ]
    ):
        continue
    indices = []
    for f in old.data.polygons:
        points = [old.matrix_world @ old.data.vertices[i].co for i in f.vertices]
        xs = [(v - p).dot(u) for v in points]
        ds = [(v - p).dot(n) for v in points]
        zs = [v.z for v in points]
        if (
            min(xs) > 0.35
            and max(xs) < length - 0.35
            and min(ds) > -0.31
            and max(ds) < 0.31
            and any(min(zs) > lo - 0.13 and max(zs) < hi + 0.13 for lo, hi in apertures)
        ):
            indices.append(f.index)
    if not indices:
        continue
    copy = old.copy()
    copy.data = old.data.copy()
    copy.name = "LRB_NEXT_ENVELOPE_retained_" + old.name.removeprefix(
        "LRB_V117_retained_LRB_V110_retained_"
    )
    copy.data.name = copy.name
    for collection in old.users_collection:
        collection.objects.link(copy)
    bm = bmesh.new()
    bm.from_mesh(copy.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in indices], context="FACES")
    bm.to_mesh(copy.data)
    bm.free()
    copy.data.update()
    old.hide_render = True
    old.hide_set(True)
    ownedWindowCopies.append(copy)
    removedFaces[old.name] = indices
    windowChanges.append(
        {
            "source": old.name,
            "owned": copy.name,
            "action": "replace",
            "collection": old.users_collection[0].name,
        }
    )
archives = [SOURCE] + list(removedFaces)
ownedNames = [OWN, WALL] + [o.name for o in ownedWindowCopies]
surfaceDepth = 0.0
sampleDepth = 0.025
dotWidth = 0.027
dotHeight = 0.039
vertices = []
faces = []
centres = []
for horizontal, vertical in samples["samples"]:
    x = xStart + horizontal * width
    z = zTop - vertical * (zTop - zBottom)
    centres.append([x, z])
    start = len(vertices)
    for xx, zz in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        vertices.append(
            wall_point(x + xx * dotWidth / 2, z + zz * dotHeight / 2, sampleDepth)
        )
    faces.append((start + 3, start + 2, start + 1, start))
material = bpy.data.materials.new("LRB_NEXT_ENVELOPE_Blue_Rain_photo_blue")
material.use_nodes = True
material.diffuse_color = (0.012, 0.075, 0.70, 1)
shader = material.node_tree.nodes["Principled BSDF"]
shader.inputs["Base Color"].default_value = (0.012, 0.075, 0.70, 1)
shader.inputs["Roughness"].default_value = 0.35
shader.inputs["Emission Color"].default_value = (0.01, 0.09, 0.95, 1)
shader.inputs["Emission Strength"].default_value = 1.2
material["webEmission"] = True
mesh = bpy.data.meshes.new(OWN)
mesh.from_pydata(vertices, [], faces)
mesh.update()
mesh.materials.append(material)
obj = bpy.data.objects.new(OWN, mesh)
bpy.data.collections["LRB_EXTERIOR"].objects.link(obj)
bpy.context.view_layer.update()


def polygon_record(mesh, face):
    return (
        face.material_index,
        tuple(
            (
                tuple(mesh.vertices[mesh.loops[i].vertex_index].co),
                tuple(tuple(layer.data[i].uv) for layer in mesh.uv_layers),
            )
            for i in face.loop_indices
        ),
    )


def validate():
    assert all(fingerprint(bpy.data.objects[k]) == v for k, v in original.items())
    assert all(
        [
            bpy.data.objects[k].hide_render,
            bpy.data.objects[k].hide_viewport,
            bpy.data.objects[k].hide_get(),
        ]
        == v
        for k, v in visibility.items()
        if k not in archives
    )
    for change in windowChanges:
        originalMesh = bpy.data.objects[change["source"]].data
        retainedMesh = bpy.data.objects[change["owned"]].data
        removed = set(removedFaces[change["source"]])
        expected = Counter(
            polygon_record(originalMesh, f)
            for f in originalMesh.polygons
            if f.index not in removed
        )
        actual = Counter(polygon_record(retainedMesh, f) for f in retainedMesh.polygons)
        assert expected == actual, change
        assert [m.name for m in retainedMesh.materials] == [
            m.name for m in originalMesh.materials
        ]
    trees = []
    for o in scene.objects:
        if (
            o.type == "MESH"
            and o.name.startswith("LRB")
            and not o.hide_render
            and not o.hide_get()
        ):
            trees.append(
                (
                    o.name,
                    BVHTree.FromPolygons(
                        [o.matrix_world @ v.co for v in o.data.vertices],
                        [tuple(f.vertices) for f in o.data.polygons],
                    ),
                )
            )

    def first(origin, direction):
        hits = []
        for name, tree in trees:
            q, no, i, d = tree.ray_cast(origin, direction, 2)
            if q is not None:
                hits.append({"object": name, "distance": d})
        return min(hits, key=lambda h: h["distance"]) if hits else None

    probes = []
    for index in range(len(centres)):
        x, z = centres[index]
        front = first(wall_point(x, z, sampleDepth + 0.5), -n)
        assert front and (
            front["object"] == OWN or "Cornice_stringcourse" in front["object"]
        ), front
        backing = first(wall_point(x, z, sampleDepth - 0.003), -n)
        assert backing and backing["object"] == WALL, backing
        assert backing["distance"] > 0.015, backing
        probes.append(
            {
                "photoSample": index,
                "localX": x,
                "z": z,
                "frontFirstHit": front,
                "existingWallFirstHit": backing,
            }
        )
    dense = []
    for z in [6, 7, 8, 10, 11, 12, 14.5, 15.5, 16.5, 18.5, 19.5]:
        for x in [0.7, 1.2, 1.6, 2, 2.5]:
            hit = first(wall_point(x, z, 0.5), -n)
            assert hit and (
                hit["object"] in [OWN, WALL] or "Cornice_stringcourse" in hit["object"]
            ), hit
            dense.append({"localX": x, "z": z, "frontFirstHit": hit})
    (OUT / "dense-probes.json").write_text(json.dumps(dense, indent=2) + "\n")
    return probes


initial = validate()
bpy.data.libraries.write(
    str(COMP), set([obj, wall] + ownedWindowCopies), fake_user=True
)
audit = {
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalFingerprints": original,
    "originalVisibility": visibility,
    "ownedObjects": ownedNames,
    "archivedObjects": archives,
    "removedFalseWindowFaces": removedFaces,
    "filledSourceApertures": before,
    "changes": [
        {
            "source": SOURCE,
            "owned": WALL,
            "action": "replace",
            "collection": "LRB_EXTERIOR",
        },
        {
            "source": None,
            "owned": OWN,
            "action": "add",
            "collection": "LRB_EXTERIOR",
            "retainNewMaterials": True,
        },
    ]
    + windowChanges,
    "sourceObjects": archives,
    "destinationCollection": "LRB_EXTERIOR",
    "retainNewMaterials": True,
    "scope": "Whole-building corner landmark missing in native facade: replace four fictitious generic chamfer apertures with the photographed continuous brick art pier, and restore visible static Blue Rain blue points. Adjacent windows, stone and roof retained.",
    "artworkIdentity": {
        "name": "Blue Rain",
        "artist": "Michael Brown",
        "physicalLEDCount": 23520,
        "displayType": "Dynamic library borrowing/returns/catalogue-search artwork, not fixed LIBRARY lettering",
        "officialSource": "https://blogs.lse.ac.uk/lsehistory/2018/03/07/shimmering-cascades-of-light-blue-rain-by-michael-brown/",
        "sourcePublication": "2018-03-07; official page refers to2009installation photograph",
        "nativeRepresentation": "Static blue-point pattern sampled from the archived official estate night photograph; no live data or animation",
    },
    "photoSampling": {k: v for k, v in samples.items() if k != "samples"},
    "photoSampleCount": len(centres),
    "registeredFacade": {
        "ringSide": 0,
        "p": list(p),
        "q": list(q),
        "outwardNormal": list(n),
        "width": width,
        "xStart": xStart,
        "zBounds": [zBottom, zTop],
        "hostSurfaceDepth": surfaceDepth,
        "displayDepth": sampleDepth,
        "wallGap": 0.025,
        "dotSampleSize": [dotWidth, dotHeight],
    },
    "material": {
        "name": material.name,
        "baseColor": [0.012, 0.075, 0.70, 1],
        "emissionColor": [0.01, 0.09, 0.95, 1],
        "emissionStrength": 1.2,
        "webEmission": True,
        "exportRequirement": "Copy Principled Emission Color/Strength only for explicit material custom property webEmission=true. One mesh and one material; no image texture.",
        "basis": "Uncalibrated blue night photo; restrained estimated radiance, not measured LED daytime reflectance",
    },
    "limitations": [
        "Samples represent bright image pixels, not counted individual LEDs or a certified row/column topology.",
        "Carrier construction, mounting brackets, exact dimensions, pitch and current daylight/off appearance unresolved; no invented backing panel or carrier geometry added.",
        "Only a static historic display state; not current text, library activity or faithful live Blue Rain behavior.",
        "Blue threshold suppresses purple light on the stone; original stone/brick/glass colours and whole-building geometry retained.",
        "Prior verified roof/Portugal/Carey/plaza broad windows retained; unknown remaining room layouts and hidden facade accuracy not claimed.",
        "Official blog full-image retrieval failed429/timeout; primary indexed text verified identity, existing archived night photo supplies the visible display.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
scene = open_baseline()
with bpy.data.libraries.load(str(COMP), link=False) as (src, dst):
    dst.objects = ownedNames
for o in dst.objects:
    bpy.data.collections["LRB_EXTERIOR"].objects.link(o)
# Appending may suffix identical material IDs; restore retained original slots.
for change in windowChanges:
    retained = bpy.data.objects[change["owned"]].data
    originalMesh = bpy.data.objects[change["source"]].data
    for index, mat in enumerate(originalMesh.materials):
        retained.materials[index] = mat
for name in archives:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
bpy.context.view_layer.update()
reloaded = validate()
assert initial == reloaded
loaded = bpy.data.objects[OWN].data.materials[0]
assert (
    loaded.get("webEmission")
    and abs(
        loaded.node_tree.nodes["Principled BSDF"]
        .inputs["Emission Strength"]
        .default_value
        - 1.2
    )
    < 1e-6
)
proof = {
    "componentSha256": hashlib.sha256(COMP.read_bytes()).hexdigest(),
    "baselineSha256": audit["baselineSha256"],
    "savedComponentReopened": True,
    "originalObjectCount": len(original),
    "allOriginalFingerprintsPreserved": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "staticPhotoSampleCount": len(centres),
    "physicalLEDCountIsNotSampleCount": True,
    "singleDisplayMesh": True,
    "ownedObjectCount": len(ownedNames),
    "displayMaterialCount": 1,
    "fourOriginalAperturesFilled": True,
    "allFrontFirstHitsAndWallBackingPassed": all(
        p["frontFirstHit"]["object"] == OWN for p in reloaded
    ),
    "allFirstHitsAreDisplayOrExistingCornice": True,
    "visibleDisplaySampleCount": sum(
        p["frontFirstHit"]["object"] == OWN for p in reloaded
    ),
    "existingCorniceOccludedSampleCount": sum(
        p["frontFirstHit"]["object"] != OWN for p in reloaded
    ),
    "surfaceProbes": reloaded,
    "webEmissionRetained": True,
    "renderCount": 2,
    "invalidPreviewCount": 1,
    "effectivePreviewCount": 1,
    "invalidPreviewReason": "Initial isolation loop re-enabled archived sources; this corrected preview preserves archive visibility",
    "retainedWindowPolygonUVMaterialsPreserved": True,
    "fullModelSaved": False,
}
for o in scene.objects:
    if o.type != "CAMERA":
        o.hide_render = (not o.name.startswith("LRB")) or o.name in archives
focus = wall_point(length / 2, 12, 0) + Vector((28, 0, 0))
cd = bpy.data.cameras.new("LRB_ENVELOPE_preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = focus + n * 75 + Vector((0, 0, 9))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 82
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
world = bpy.data.worlds.new("LRB_ENVELOPE_preview_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.48, 0.53, 0.62, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
scene.world = world
ld = bpy.data.lights.new("LRB_ENVELOPE_area", "AREA")
ld.energy = 16000
ld.size = 40
light = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(light)
light.location = focus + n * 25 + Vector((0, 0, 30))
light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_x = 1150
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "reloaded-library-envelope.png")
bpy.ops.render.render(write_still=True)
proof["nativeRender"] = str(OUT / "reloaded-library-envelope.png")
proof["wholeCornerSurfaceProbeFile"] = (
    "result/blender/lrb_envelope_next/dense-probes.json"
)
proof["wholeCornerSurfaceProbeCount"] = 55
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("LRB_ENVELOPE_VERIFIED", proof["componentSha256"])
bpy.ops.wm.quit_blender()
