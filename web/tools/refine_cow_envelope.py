"""Correct the photographed COW short-side ground-storey brick partition.
Use Blender Text Editor. Apertures, UVs and all source geometry remain intact.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/cow_envelope_next"
BASE = ROOT / "result/blender/LSE_campus_detailed_v144.blend"
EXPECTED = "a8bbab18e6b2a624f61ce4d9460e2577809f9aaf6d092d1804f34fa34a4e692e"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
PREFIX = "COW_NEXT_"
ARCHIVE = [
    "COW_D5_window_piers_stone",
    "COW_D5_window_spandrel_stone",
    "COW_D5_window_head_stone",
]
NAMES = [PREFIX + "ground_partition_" + s for s in ["piers", "spandrels", "heads"]]
COMPONENT = OUT / "cow-envelope-component.blend"
PREVIOUS = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else {}
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
    for name in ARCHIVE:
        state = PREVIOUS.get("originalVisibility", {}).get(name, [False, False, False])
        o = bpy.data.objects[name]
        o.hide_render, o.hide_viewport = state[:2]
        o.hide_set(state[2])
    for layer in bpy.context.scene.view_layers:
        layer.update()


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, n in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            a = array.array(kind, [0]) * (len(data) * n)
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
if BASE.stem.endswith("v144"):
    assert len(originals) == 5748
collection = bpy.data.collections["COW_EXTERIOR"]
ring = next(
    b["rings"][0]
    for b in json.loads((ROOT / "result/blender/site_geometry.json").read_text())[
        "buildings"
    ]
    if b["code"] == "COW"
)
walls = []
for side in range(len(ring)):
    a, b = [Vector((*ring[i % len(ring)], 0)) for i in [side, side + 1]]
    u = (b - a).normalized()
    n = Vector((-u.y, u.x, 0))
    walls.append((a, u, n, (b - a).length))


def side_of(centre):
    candidates = []
    for side, (a, u, n, length) in enumerate(walls):
        x = (centre - a).dot(u)
        if -0.01 < x < length + 0.01:
            candidates.append((abs((centre - a).dot(n)), side))
    return min(candidates)[1] if candidates else None


brickSource = bpy.data.objects["COW_D5_window_piers_brick"].data.materials[0]
brick = brickSource.copy()
brick.name = PREFIX + "short_ground_brick"
owned = []
changes = []
probes = []
for sourceName, newName in zip(ARCHIVE, NAMES):
    source = bpy.data.objects[sourceName]
    o = source.copy()
    o.data = source.data.copy()
    o.name = newName
    collection.objects.link(o)
    slot = len(o.data.materials)
    o.data.materials.append(brick)
    mesh = o.data
    adj = {v.index: set() for v in mesh.vertices}
    for e in mesh.edges:
        x, y = e.vertices
        adj[x].add(y)
        adj[y].add(x)
    seen = set()
    groups = []
    changedFaces = []
    for vertex in mesh.vertices:
        if vertex.index in seen:
            continue
        todo = [vertex.index]
        seen.add(vertex.index)
        group = []
        while todo:
            i = todo.pop()
            group.append(i)
            for j in adj[i]:
                if j not in seen:
                    seen.add(j)
                    todo.append(j)
        points = [o.matrix_world @ mesh.vertices[i].co for i in group]
        centre = sum(points, Vector()) / len(points)
        if side_of(centre) != 5 or max(p.z for p in points) > 4.901:
            continue
        ids = set(group)
        faces = [f for f in mesh.polygons if all(i in ids for i in f.vertices)]
        for f in faces:
            f.material_index = slot
            changedFaces.append(f.index)
        groups.append(
            {"centre": list(centre), "vertexCount": len(group), "faceCount": len(faces)}
        )
        probes.append(
            {
                "kind": "brickPartition",
                "origin": list(centre + walls[5][2] * 0.8),
                "direction": list(-walls[5][2]),
                "distance": 1.4,
                "source": sourceName,
                "owned": newName,
            }
        )
    assert groups, (sourceName, "No side5 component")
    # Source coordinates, loop topology and UVs are copied exactly, with only selected material indices changed.
    assert list(o.matrix_world) == list(source.matrix_world)
    assert [tuple(v.co) for v in mesh.vertices] == [
        tuple(v.co) for v in source.data.vertices
    ]
    assert [tuple(f.vertices) for f in mesh.polygons] == [
        tuple(f.vertices) for f in source.data.polygons
    ]
    assert [[tuple(d.uv) for d in uv.data] for uv in mesh.uv_layers] == [
        [tuple(d.uv) for d in uv.data] for uv in source.data.uv_layers
    ]
    changes.append(
        {
            "source": sourceName,
            "owned": newName,
            "action": "Change only registered short-side ground masonry material to inherited Cowdray brick",
            "changedFaces": changedFaces,
            "componentCount": len(groups),
            "components": groups,
            "newMaterialSlot": slot,
            "sourceSlots": [m.name for m in source.data.materials],
        }
    )
    owned.append(o)
glass = json.loads((OUT / "glazing-first-contact.json").read_text())
for p in glass:
    n = walls[p["side"]][2]
    probes.append(
        {
            "kind": "retainedGlass",
            "origin": list(Vector(p["panePoint"]) + n * 0.8),
            "direction": list(-n),
            "distance": 2,
        }
    )
a, b = [Vector((*ring[i], 0)) for i in [4, 5]]
pc = (a + b) / 2
u = (b - a).normalized()
pn = Vector((-u.y, u.x, 0))
for z in [1.5, 3.2]:
    probes.append(
        {
            "kind": "retainedPortal",
            "origin": list(pc + pn * 0.8 + Vector((0, 0, z))),
            "direction": list(-pn),
            "distance": 2,
        }
    )


def cast(exclude=()):
    vertices = []
    faces = []
    owners = []
    indices = []
    for o in collection.all_objects:
        if o.type != "MESH" or o.hide_render or o.name in exclude:
            continue
        k = len(vertices)
        vertices.extend(o.matrix_world @ v.co for v in o.data.vertices)
        faces.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
        indices.extend(f.index for f in o.data.polygons)
    tree = BVHTree.FromPolygons(vertices, faces)
    rows = []
    for p in probes:
        h = tree.ray_cast(Vector(p["origin"]), Vector(p["direction"]), p["distance"])
        name = owners[h[2]] if h[2] is not None else None
        face = indices[h[2]] if h[2] is not None else None
        material = (
            bpy.data.objects[name]
            .data.materials[bpy.data.objects[name].data.polygons[face].material_index]
            .name
            if name
            else None
        )
        rows.append(
            {
                **p,
                "firstObject": name,
                "firstMaterial": material,
                "hitPoint": list(h[0]) if h[0] is not None else None,
            }
        )
    return rows


before = cast(NAMES)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
after = cast()
mapping = dict(zip(ARCHIVE, NAMES))
for p, q in zip(before, after):
    assert q["firstObject"] == mapping.get(p["firstObject"], p["firstObject"]), (p, q)
    assert q["hitPoint"] == p["hitPoint"], (p, q)
    if q["kind"] == "brickPartition" and q["firstObject"] == q["owned"]:
        assert q["firstMaterial"] == brick.name
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in ARCHIVE
)
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)


def pbr(m):
    p = m.node_tree.nodes["Principled BSDF"]
    return {
        "name": m.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "metallic": p.inputs["Metallic"].default_value,
        "roughness": p.inputs["Roughness"].default_value,
        "alpha": p.inputs["Alpha"].default_value,
    }


refs = []
for file, date in [
    (
        "campus_photos_round2_COW_cow_russell_05.jpg",
        "Contractor project2019; capture unknown",
    ),
    ("exteriors_lse_estate_006.jpg", "LSE Estates; capture unknown"),
]:
    p = ROOT / "data/建筑图片/COW_Cowdray House/01_建筑实拍" / file
    refs.append(
        {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "date": date,
            "evidence": "Long-side stone ground frontage and chamfer stone portal contrast with short-side brick continuing to street level.",
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": SHA,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": NAMES,
    "archivedObjects": ARCHIVE,
    "archiveObjects": ARCHIVE,
    "changes": changes,
    "references": refs,
    "registration": {
        "side": 5,
        "edgeEndpoints": [ring[5], ring[6]],
        "edgeLength": walls[5][3],
        "rule": "Connected existing masonry components assigned to nearest GIS edge5, below4.9m. Native footprint/heights estimated, not surveyed.",
    },
    "materials": {
        "sourceBrick": pbr(brickSource),
        "ownedBrick": pbr(brick),
        "sourceStoneSlotsPreserved": True,
    },
    "beforeProbes": before,
    "afterProbes": after,
    "wholeExteriorReview": {
        "upperStoreys": 3,
        "streetGlazingContacts": 82,
        "streetDormers": 11,
        "shortGround": "Incorrect continuous pale stone replaced by photograph-supported brick partition only",
        "coordinatesTopologyUVPreserved": True,
    },
    "limitations": [
        "Short-side ground window widths/heights remain inherited estimates; low-resolution oblique photos cannot reliably register a shrinkage.",
        "Roof plan-depth, unequal centroid-derived slopes, chimney/party roof registration remain unresolved. No arbitrary uniform roof angle.",
        "Brick PBR inherited existing upper Cowdray wall. No exact colour measurement claimed.",
        "Unseen elevations and all interiors unchanged.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["COW_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = NAMES
for o in dst.objects:
    collection.objects.link(o)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
# Material names receive loader suffixes; verify PBR identity and normalize probe metadata only.
reloaded = cast()
for p, q in zip(after, reloaded):
    assert p["firstObject"] == q["firstObject"] and p["hitPoint"] == q["hitPoint"], (
        p,
        q,
    )
    if q["firstObject"] in NAMES and p["firstMaterial"] == brick.name:
        assert q["firstMaterial"].startswith("COW_NEXT_short_ground_brick")
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals and o.name not in ARCHIVE
)
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type not in {"LIGHT", "CAMERA"} and o.name not in members:
        o.hide_render = True
focus = pc + Vector((0, 0, 10))
camdata = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + pn * 40 + Vector((0, 0, 6))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 39
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1500
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-cow-frontage.png")
bpy.ops.render.render(write_still=True)
v = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA,
    "reloadedProbes": reloaded,
    "render": "reloaded-cow-frontage.png",
    "camera": list(cam.location),
    "target": list(focus),
    "coordinateAndUVPreservingMaterialPartition": True,
}
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print(
    "COW_PARTITION_VERIFIED",
    len(originals),
    len(after),
    [c["componentCount"] for c in changes],
)
bpy.ops.wm.quit_blender()
