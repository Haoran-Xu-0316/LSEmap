"""Register completed Portsmouth project's seven-tree scheme to native buildings.
No arguments. Positions and planting/container dimensions are scheme estimates,
not a current survey. Builds only a reusable local component; never a campus.
"""

from pathlib import Path
from collections import Counter
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/portsmouth_public_realm_next"
PREFIX = "SITE_NEXT_PORTSMOUTH_"
COMPONENT = OUT / "portsmouth-public-realm-component.blend"
BASE = ROOT / "result/blender/LSE_campus_detailed_v143.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
ANCHORS = [
    {
        "label": "OCS north-west street corner",
        "pixel": [595, 701],
        "native": [-47.68997370155647, 44.425589506584764],
    },
    {
        "label": "OCS south-west street corner",
        "pixel": [621, 752],
        "native": [-46.19752084107656, 41.33259999555706],
    },
    {
        "label": "OCS south-east corner",
        "pixel": [704, 777],
        "native": [-39.29741049451205, 39.363273237003554],
    },
    {
        "label": "MAR southern ground-plan tip",
        "pixel": [1243, 950],
        "native": [0.3956825597066434, 24.454533528170252],
    },
]
PIXELS = [
    [435, 576],
    [470, 650],
    [506, 719],
    [829, 843],
    [937, 887],
    [1040, 926],
    [1145, 982],
]
px = sum(a["pixel"][0] for a in ANCHORS) / 4
py = sum(a["pixel"][1] for a in ANCHORS) / 4
nx = sum(a["native"][0] for a in ANCHORS) / 4
ny = sum(a["native"][1] for a in ANCHORS) / 4
D = sum((a["pixel"][0] - px) ** 2 + (a["pixel"][1] - py) ** 2 for a in ANCHORS)
a = (
    sum(
        (p["pixel"][0] - px) * (p["native"][0] - nx)
        - (p["pixel"][1] - py) * (p["native"][1] - ny)
        for p in ANCHORS
    )
    / D
)
b = (
    sum(
        (p["pixel"][1] - py) * (p["native"][0] - nx)
        + (p["pixel"][0] - px) * (p["native"][1] - ny)
        for p in ANCHORS
    )
    / D
)
tx = nx - a * px - b * py
ty = ny - b * px + a * py


def registered(pixel):
    x, y = pixel
    return Vector((a * x + b * y + tx, b * x - a * y + ty, 0.05))


positions = [registered(p) for p in PIXELS]
for p in ANCHORS:
    p["registeredNative"] = list(registered(p["pixel"]))[:2]
    p["residualMetres"] = math.dist(p["registeredNative"], p["native"])
assert max(p["residualMetres"] for p in ANCHORS) < 0.65
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
scene = bpy.context.scene
prior = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else {}
)
for o in list(bpy.data.objects):
    if o.name.startswith(PREFIX):
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data and hasattr(data, "use_fake_user"):
            data.use_fake_user = False
        if data and not data.users and isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
for name in prior.get("archivedObjects", []):
    if name in bpy.data.objects:
        o = bpy.data.objects[name]
        v = prior["originalVisibility"][name]
        o.hide_render, o.hide_viewport = v[:2]
        o.hide_set(v[2])
for m in list(bpy.data.materials):
    if m.name.startswith(PREFIX) and not m.users:
        bpy.data.materials.remove(m)


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, count in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            v = array.array(kind, [0]) * (len(data) * count)
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


originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
owned = []
changes = []
removed = {}
archives = []


def polyrecord(mesh, f):
    return f.material_index, tuple(
        (
            tuple(mesh.vertices[mesh.loops[i].vertex_index].co),
            tuple(tuple(layer.data[i].uv) for layer in mesh.uv_layers),
        )
        for i in f.loop_indices
    )


# Replace only disconnected legacy tree components whose centres duplicate new
# registered tree locations. Retain all other vertices/UV/materials in copies.
for name in ["03_PUBLIC_REALM_Plane_tree_trunk", "03_PUBLIC_REALM_Plane_tree_crown"]:
    source = bpy.data.objects.get(name)
    if not source or source.hide_render or source.hide_get():
        continue
    mesh = source.data
    parent = list(range(len(mesh.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for f in mesh.polygons:
        root = find(f.vertices[0])
        for i in f.vertices[1:]:
            parent[find(i)] = root
    groups = {}
    for v in mesh.vertices:
        groups.setdefault(find(v.index), []).append(v.index)
    rejected = set()
    duplicate = []
    for ids in groups.values():
        coords = [source.matrix_world @ mesh.vertices[i].co for i in ids]
        centre = sum(coords, Vector()) / len(coords)
        nearest = min(math.hypot(centre.x - p.x, centre.y - p.y) for p in positions)
        if nearest < 2.4:
            rejected.update(ids)
            duplicate.append(
                {"centre": list(centre), "distanceToSchemeMetres": nearest}
            )
    if not rejected:
        continue
    faces = [f.index for f in mesh.polygons if any(i in rejected for i in f.vertices)]
    removed[name] = faces
    copy = source.copy()
    copy.data = mesh.copy()
    copy.name = PREFIX + "retained_" + name
    for col in source.users_collection:
        col.objects.link(copy)
    bm = bmesh.new()
    bm.from_mesh(copy.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in rejected], context="VERTS")
    bm.to_mesh(copy.data)
    bm.free()
    source.hide_render = True
    source.hide_set(True)
    archives.append(name)
    owned.append(copy)
    changes.append(
        {
            "source": name,
            "owned": copy.name,
            "action": "replace",
            "collection": source.users_collection[0].name,
            "duplicateComponents": duplicate,
        }
    )


def material(label, color, rough):
    m = bpy.data.materials.new(PREFIX + label)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = m.diffuse_color
    p.inputs["Roughness"].default_value = rough
    return m


stone = material("estimated_yorkstone_planter", (0.43, 0.425, 0.38), 0.88)
soil = material("soil", (0.12, 0.10, 0.075), 0.95)
trunk_source = bpy.data.objects["03_PUBLIC_REALM_Plane_tree_trunk"]
leaf_source = bpy.data.objects["03_PUBLIC_REALM_Plane_tree_crown"]
wood = trunk_source.data.materials[0]
leaf = leaf_source.data.materials[0]


class Batch:
    def __init__(self, label, mats):
        self.name = PREFIX + label
        self.verts = []
        self.faces = []
        self.slots = []
        self.mats = mats

    def cylinder(self, p, r, z, h, slot):
        k = len(self.verts)
        self.verts.extend(
            (
                p.x + r * math.cos(i * math.tau / 24),
                p.y + r * math.sin(i * math.tau / 24),
                level,
            )
            for level in [z, z + h]
            for i in range(24)
        )
        fs = [tuple(reversed(range(24))), tuple(range(24, 48))] + [
            (i, (i + 1) % 24, (i + 1) % 24 + 24, i + 24) for i in range(24)
        ]
        self.faces.extend(tuple(k + j for j in f) for f in fs)
        self.slots.extend([slot] * len(fs))

    def ring(self, p, r1, r2, z1, z2, slot):
        k = len(self.verts)
        for r, z in [(r1, z1), (r2, z1), (r1, z2), (r2, z2)]:
            self.verts.extend(
                (
                    p.x + r * math.cos(i * math.tau / 24),
                    p.y + r * math.sin(i * math.tau / 24),
                    z,
                )
                for i in range(24)
            )
        for i in range(24):
            j = (i + 1) % 24
            for f in [
                (i, j, j + 24, i + 24),
                (i + 48, i + 72, j + 72, j + 48),
                (i, i + 48, j + 48, j),
                (i + 24, j + 24, j + 72, i + 72),
            ]:
                self.faces.append(tuple(k + x for x in f))
                self.slots.append(slot)

    def crown(self, p, index):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
        verts = list(bm.verts)
        lookup = {v: i for i, v in enumerate(verts)}
        k = len(self.verts)
        rx = 1.8 + 0.12 * (index % 3)
        ry = 1.75 + 0.09 * ((index + 1) % 3)
        height = 1.9 + 0.1 * (index % 2)
        self.verts.extend(
            (p.x + v.co.x * rx, p.y + v.co.y * ry, 4.4 + v.co.z * height) for v in verts
        )
        self.faces.extend(tuple(k + lookup[v] for v in f.verts) for f in bm.faces)
        self.slots.extend([0] * len(bm.faces))
        bm.free()

    def save(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.verts, [], self.faces)
        for m in self.mats:
            mesh.materials.append(m)
        for f, slot in zip(mesh.polygons, self.slots):
            f.material_index = slot
        mesh.update()
        o = bpy.data.objects.new(self.name, mesh)
        bpy.data.collections["00_SITE"].objects.link(o)
        owned.append(o)
        changes.append(
            {"source": None, "owned": o.name, "action": "add", "collection": "00_SITE"}
        )
        return o


planters = Batch("registered_seven_tree_pools", [stone, soil])
trunks = Batch("registered_seven_tree_trunks", [wood])
crowns = Batch("registered_seven_tree_crowns", [leaf])
for i, p in enumerate(positions):
    planters.ring(p, 0.61, 0.72, 0.05, 0.25, 0)
    planters.cylinder(p, 0.61, 0.05, 0.16, 1)
    trunks.cylinder(p, 0.10, 0.21, 4.3, 0)
    crowns.crown(p, i)
planters.save()
trunks.save()
crowns.save()
bpy.context.view_layer.update()
owned_names = [o.name for o in owned]


def validate():
    assert originals == {
        name: fingerprint(bpy.data.objects[name]) for name in originals
    }
    assert all(
        [
            bpy.data.objects[name].hide_render,
            bpy.data.objects[name].hide_viewport,
            bpy.data.objects[name].hide_get(),
        ]
        == state
        for name, state in visibility.items()
        if name not in archives
    )
    for c in changes:
        if not c["source"]:
            continue
        src = bpy.data.objects[c["source"]].data
        copy = bpy.data.objects[c["owned"]].data
        exclude = set(removed[c["source"]])
        assert Counter(
            polyrecord(src, f) for f in src.polygons if f.index not in exclude
        ) == Counter(polyrecord(copy, f) for f in copy.polygons)
    trees = []
    for o in scene.objects:
        if o.type == "MESH" and not o.hide_render and not o.hide_get():
            trees.append(
                (
                    o.name,
                    BVHTree.FromPolygons(
                        [o.matrix_world @ v.co for v in o.data.vertices],
                        [tuple(f.vertices) for f in o.data.polygons],
                    ),
                )
            )

    def first(p, d, distance):
        hits = []
        for name, tree in trees:
            loc, no, face, dist = tree.ray_cast(p, d, distance)
            if loc is not None:
                hits.append({"object": name, "distance": dist, "point": list(loc)})
        return min(hits, key=lambda h: h["distance"]) if hits else None

    pool = []
    for p in positions:
        hit = first(Vector((p.x + 0.35, p.y, 0.8)), Vector((0, 0, -1)), 1)
        assert hit and hit["object"] == planters.name, hit
        pool.append(hit)
    route = json.loads((OUT / "native-inspection.json").read_text())["centreLineProbes"]
    passage = []
    for sample in route:
        x, y = sample["xy"]
        distance = min(math.hypot(x - p.x, y - p.y) for p in positions)
        assert distance > 0.72 + 0.45, (sample, distance)
        hit = first(Vector((x, y, 0.30)), Vector((0, 0, -1)), 0.5)
        assert hit and hit["object"] == "SITE_V47_Portsmouth_Street", hit
        passage.append(
            {"xy": [x, y], "nearestPoolCentreMetres": distance, "groundFirstHit": hit}
        )
    return pool, passage


# Physical basin circles must remain outside every registered building footprint.
def point_inside(point, ring):
    x, y = point
    inside = False
    for start, end in zip(ring, ring[1:] + ring[:1]):
        if (start[1] > y) != (end[1] > y) and x < (end[0] - start[0]) * (
            y - start[1]
        ) / (end[1] - start[1]) + start[0]:
            inside = not inside
    return inside


def segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    den = dx * dx + dy * dy
    t = (
        max(0, min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / den))
        if den
        else 0
    )
    return math.dist(point, [start[0] + dx * t, start[1] + dy * t])


footprints = json.loads((ROOT / "result/blender/site_geometry.json").read_text())[
    "buildings"
]
clearances = []
for centre in positions:
    point = list(centre)[:2]
    candidates = []
    for building in footprints:
        if not building["rings"]:
            continue
        assert not (
            point_inside(point, building["rings"][0])
            and not any(point_inside(point, hole) for hole in building["rings"][1:])
        ), building["id"]
        ring = building["rings"][0]
        distance = min(
            segment_distance(point, start, end)
            for start, end in zip(ring, ring[1:] + ring[:1])
        )
        candidates.append((distance, building["id"], building["code"]))
    distance, identifier, code = min(candidates, key=lambda entry: entry[0])
    assert distance - 0.72 > 0.3
    clearances.append(
        {
            "centre": point,
            "nearestBuilding": identifier,
            "code": code,
            "distanceToFootprint": distance,
            "poolOuterRadius": 0.72,
            "clearance": distance - 0.72,
            "insideAnyBuildingFootprint": False,
        }
    )
(OUT / "building-clearances.json").write_text(json.dumps(clearances, indent=2) + "\n")

initial = validate()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
audit = {
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalObjectCount": len(originals),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": owned_names,
    "archivedObjects": archives,
    "changes": changes,
    "destinationCollection": "00_SITE",
    "retainNewMaterials": True,
    "buildingClearanceFile": "building-clearances.json",
    "buildingPoolClearanceMinimumMetres": min(c["clearance"] for c in clearances),
    "planPixelsSourceResolution": [2200, 1554],
    "removedFaces": removed,
    "scope": "Seven tree pools registered from completed Portsmouth2021approved scheme, with deliberately estimated container and vegetation dimensions. No benches,cycle stands or gully changes.",
    "registration": {
        "model": "Similarity with image-Y reflection; not unrestricted affine",
        "equations": ["X=a*pixelX+b*pixelY+tx", "Y=b*pixelX-a*pixelY+ty"],
        "a": a,
        "b": b,
        "tx": tx,
        "ty": ty,
        "metresPerPixel": math.hypot(a, b),
        "anchors": ANCHORS,
        "maxResidualMetres": max(p["residualMetres"] for p in ANCHORS),
        "treeCentres": [
            {"pixel": pixel, "native": list(p)} for pixel, p in zip(PIXELS, positions)
        ],
    },
    "dimensionsEstimated": {
        "poolOuterDiameter": 1.44,
        "poolInnerDiameter": 1.22,
        "poolRimAbovePaving": 0.20,
        "treeHeightRange": [6.3, 6.4],
        "canopyDiameterRange": [3.5, 4.08],
        "trunkDiameter": 0.20,
    },
    "sources": [
        {
            "local": "portsmouth-approved-plan-2021.pdf",
            "url": "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Marshall-Building/Newsletters/Plan-Update-redline-FINAL-May-2021.pdf",
            "date": "May2021",
            "supports": "Registered intended seven-tree positions and approximate circular green footprints",
        },
        {
            "url": "https://www.westminstertransportationservices.co.uk/projects/project_details.php?id=541",
            "supports": "Project completed; seven trees in planters; Yorkstone shared surface",
        },
    ],
    "limitations": [
        "Official completed scheme registration, not a2026condition survey. Positions carry drawing-to-native residual and later installation uncertainty.",
        "Four noncollinear corner anchors cover OCS and MAR; native source GIS and raster drawing are approximate.",
        "Planter circular geometry,0.20m rim and planting heights/leaf volume are conservative modelling estimates, not observed installed container detail.",
        "Two benches/three stands not positioned because their installed placement is unconfirmed. Five illustrative gullies left untouched.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
scene = bpy.context.scene
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = owned_names
for o in dst.objects:
    c = next(c for c in changes if c["owned"] == o.name)
    bpy.data.collections[c["collection"]].objects.link(o)
    if c["source"]:
        source = bpy.data.objects[c["source"]]
        for i, m in enumerate(source.data.materials):
            o.data.materials[i] = m
for name in archives:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
bpy.context.view_layer.update()
reloaded = validate()
assert initial == reloaded
proof = {
    "baselineSha256": audit["baselineSha256"],
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryUVMaterialSlotsPreserved": True,
    "allOriginalFingerprintsPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "registeredPoolFirstHits": reloaded[0],
    "corridorFirstHits": reloaded[1],
    "allProtectedBuildingsGlobeRoadsPreserved": True,
    "fullModelSaved": False,
    "allPoolsOutsideBuildingFootprints": True,
    "minimumPoolToFootprintClearanceMetres": min(c["clearance"] for c in clearances),
}
# One useful aerial framing: all seven positions, old-shop bend and MAR frontage.
focus = Vector((-31, 43, 2))
position = Vector((-110, -35, 110))
cd = bpy.data.cameras.new(PREFIX + "preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = position
cam.rotation_euler = (focus - position).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 113
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
world = bpy.data.worlds.new(PREFIX + "world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.65, 0.7, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
scene.world = world
ld = bpy.data.lights.new(PREFIX + "key", "AREA")
ld.energy = 22000
ld.size = 65
lo = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(lo)
lo.location = Vector((-35, 5, 90))
lo.rotation_euler = (focus - lo.location).to_track_quat("-Z", "Y").to_euler()
(
    scene.render.resolution_x,
    scene.render.resolution_y,
    scene.render.resolution_percentage,
) = (1100, 1000, 100)
scene.render.filepath = str(OUT / "reloaded-portsmouth-public-realm.png")
proof["nativeRender"] = scene.render.filepath
audit["nativePreviewCamera"] = {
    "position": [float(v) for v in position],
    "target": [float(v) for v in focus],
    "orthoScale": 113,
    "coordinateSystem": "Native Blender Z-up metres",
    "resolution": [1100, 1000],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
bpy.ops.render.render(write_still=True)
print("PORTSMOUTH_COMPONENT_VERIFIED", proof["componentSha256"])
bpy.ops.wm.quit_blender()
