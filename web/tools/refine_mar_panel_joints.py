"""Restore MAR's registered blank western tower wall, not a decorative grid.

Run in Blender without arguments. The source plane is registered by the
8546_5 five-column end ->8546_0 side ->8546_1 top-band native edge sequence.
Photo05 supports a blank side; seam positions, width and depth are estimates.
"""

from pathlib import Path
from collections import Counter
import array, hashlib, json
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/mar_panel_joints_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v142.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
COMPONENT = OUT / "marshall-blank-wall-component.blend"
PREFIX = "MAR_NEXT_PANEL_"
WALL = PREFIX + "registered_8546_0_blank_wall"
COLLECTION = "MAR_EXTERIOR"
SURFACE = next(
    s
    for s in json.loads(
        (ROOT / "result/blender/stage75/mar-fenestration.json").read_text()
    )["surfaces"]
    if s["name"] == "MAR_rear_way/1376078546_0"
)
END_SURFACE = next(
    s
    for s in json.loads(
        (ROOT / "result/blender/stage75/mar-fenestration.json").read_text()
    )["surfaces"]
    if s["name"] == "MAR_rear_way/1376078546_5"
)
end_p, end_q = Vector((*END_SURFACE["p"], 0)), Vector((*END_SURFACE["q"], 0))
end_u = (end_q - end_p).normalized()
end_n = Vector((end_u.y, -end_u.x, 0))
p, q = Vector((*SURFACE["p"], 0)), Vector((*SURFACE["q"], 0))
u = (q - p).normalized()
n = Vector((u.y, -u.x, 0))
RIGHT_LONG_SURFACE = next(
    s
    for s in json.loads(
        (ROOT / "result/blender/stage75/mar-fenestration.json").read_text()
    )["surfaces"]
    if s["name"] == "MAR_rear_way/1376078546_4"
)
centre = (
    sum(
        [
            p,
            q,
            end_p,
            end_q,
            Vector((*RIGHT_LONG_SURFACE["p"], 0)),
            Vector((*RIGHT_LONG_SURFACE["q"], 0)),
        ],
        Vector(),
    )
    / 6
)
if n.dot((p + q) / 2 - centre) < 0:
    n = -n
LENGTH = (q - p).length
LOW, HIGH = 12.8, 42.8
SEAM_WIDTH, SEAM_DEPTH = 0.018, 0.012


def world_point(x, z, depth=0):
    return p + u * x + n * depth + Vector((0, 0, z))


def open_baseline():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    prior_path = OUT / "audit.json"
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else {}
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for name in prior.get("archivedObjects", []):
        obj = bpy.data.objects[name]
        state = prior["originalVisibility"][name]
        obj.hide_render, obj.hide_viewport = state[:2]
        obj.hide_set(state[2])
    bpy.context.view_layer.update()
    return bpy.context.scene


def fingerprint(obj):
    digest = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == "MESH":
        for data, field, kind, count in [
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
            (obj.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            digest.update(values.tobytes())
    digest.update(
        str(
            [m.name if m else None for m in getattr(obj.data, "materials", [])]
        ).encode()
    )
    return digest.hexdigest()


def polygon_record(mesh, face):
    return face.material_index, tuple(
        (
            tuple(mesh.vertices[mesh.loops[i].vertex_index].co),
            tuple(tuple(layer.data[i].uv) for layer in mesh.uv_layers),
        )
        for i in face.loop_indices
    )


scene = open_baseline()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
owned, changes, removed = [], [], {}
# The inherited registered window family has35 false cuboids on this face.
# Remove only faces contained in this plane slab and its exact wall height/span.
for source in list(bpy.data.collections[COLLECTION].all_objects):
    if source.type != "MESH" or source.hide_render or source.hide_get():
        continue
    indices = []
    for face in source.data.polygons:
        points = [
            source.matrix_world @ source.data.vertices[i].co for i in face.vertices
        ]
        local = [((v - p).dot(u), (v - p).dot(n), v.z) for v in points]
        if not local:
            continue
        face_centre = sum(points, Vector()) / len(points)
        end_x, end_depth, end_z = (
            (face_centre - end_p).dot(end_u),
            (face_centre - end_p).dot(end_n),
            face_centre.z,
        )
        if abs(end_depth) < 0.8 and any(
            a - 0.10 < end_x < c + 0.10 and b - 0.16 < end_z < d + 0.16
            for a, b, c, d in END_SURFACE["openings"]
        ):
            continue
        xmid = sum(v[0] for v in local) / len(local)
        zmid = sum(v[2] for v in local) / len(local)
        in_registered_aperture = any(
            a - 0.10 < xmid < c + 0.10 and b - 0.16 < zmid < d + 0.16
            for a, b, c, d in SURFACE["openings"]
        )
        is_concrete_wall_batch = source.name == "MAR_V115_retained_D5_wings75_concrete"
        if (
            (is_concrete_wall_batch or in_registered_aperture)
            and 0.15 < xmid < LENGTH - 0.15
            and all(
                -0.35 < x < LENGTH + 0.35
                and -0.71 < depth < 0.71
                and LOW - 0.16 < z < HIGH + 0.16
                for x, depth, z in local
            )
        ):
            indices.append(face.index)
    if not indices:
        continue
    copy = source.copy()
    copy.data = source.data.copy()
    copy.name = (
        PREFIX
        + "retained_"
        + str(len(owned)).zfill(2)
        + "_"
        + source.name.removeprefix("MAR_")[-30:]
    )
    copy.data.name = copy.name
    bpy.data.collections[COLLECTION].objects.link(copy)
    bm = bmesh.new()
    bm.from_mesh(copy.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in indices], context="FACES")
    bm.to_mesh(copy.data)
    bm.free()
    copy.data.update()
    source.hide_render = True
    source.hide_set(True)
    owned.append(copy)
    removed[source.name] = indices
    changes.append(
        {
            "source": source.name,
            "owned": copy.name,
            "action": "replace",
            "collection": COLLECTION,
        }
    )
glass_source = "MAR_V115_retained_D5_wings75_glass"
assert len(removed.get(glass_source, [])) == 35 * 6, removed.get(glass_source)
# Physical concrete wall: front panels and their shallow recessed seam strips
# share the existing0.40m depth. No floating black lines or window backing plate.
material = bpy.data.objects["MAR_V115_retained_D5_wings75_concrete"].data.materials[0]
vertices, faces = [], []
x_cuts = [
    0,
    LENGTH / 3 - SEAM_WIDTH / 2,
    LENGTH / 3 + SEAM_WIDTH / 2,
    LENGTH * 2 / 3 - SEAM_WIDTH / 2,
    LENGTH * 2 / 3 + SEAM_WIDTH / 2,
    LENGTH,
]
z_cuts = [
    LOW,
    22.8 - SEAM_WIDTH / 2,
    22.8 + SEAM_WIDTH / 2,
    32.8 - SEAM_WIDTH / 2,
    32.8 + SEAM_WIDTH / 2,
    HIGH,
]
for ix, (left, right) in enumerate(zip(x_cuts, x_cuts[1:])):
    for iz, (bottom, top) in enumerate(zip(z_cuts, z_cuts[1:])):
        front = 0.4 - SEAM_DEPTH if ix % 2 or iz % 2 else 0.4
        start = len(vertices)
        vertices.extend(
            world_point(x, z, depth)
            for x, depth, z in [
                (left, 0, bottom),
                (left, 0, top),
                (left, front, bottom),
                (left, front, top),
                (right, 0, bottom),
                (right, 0, top),
                (right, front, bottom),
                (right, front, top),
            ]
        )
        faces.extend(
            tuple(start + i for i in face)
            for face in [
                (0, 4, 6, 2),
                (1, 3, 7, 5),
                (0, 1, 5, 4),
                (2, 6, 7, 3),
                (0, 2, 3, 1),
                (4, 5, 7, 6),
            ]
        )
mesh = bpy.data.meshes.new(WALL)
mesh.from_pydata(vertices, [], faces)
mesh.materials.append(material)
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(mesh)
bm.free()
uv = mesh.uv_layers.new(name="RegisteredWallMetricUV")
for face in mesh.polygons:
    for index in face.loop_indices:
        point = mesh.vertices[mesh.loops[index].vertex_index].co
        uv.data[index].uv = ((point - p).dot(u), point.z)
wall = bpy.data.objects.new(WALL, mesh)
bpy.data.collections[COLLECTION].objects.link(wall)
owned.append(wall)
changes.append(
    {
        "source": None,
        "owned": WALL,
        "action": "add",
        "collection": COLLECTION,
        "retainsMaterialSource": "MAR_V115_retained_D5_wings75_concrete",
    }
)
archives = list(removed)
owned_names = [o.name for o in owned]
bpy.context.view_layer.update()


def validate():
    assert all(
        fingerprint(bpy.data.objects[name]) == value
        for name, value in originals.items()
    )
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
    for change in changes:
        if not change["source"]:
            continue
        source = bpy.data.objects[change["source"]].data
        copy = bpy.data.objects[change["owned"]].data
        rejected = set(removed[change["source"]])
        assert Counter(
            polygon_record(source, f)
            for f in source.polygons
            if f.index not in rejected
        ) == Counter(polygon_record(copy, f) for f in copy.polygons), change
        assert [m.name for m in source.materials] == [m.name for m in copy.materials]
    trees = []
    for obj in scene.objects:
        if (
            obj.type == "MESH"
            and obj.name.startswith("MAR")
            and not obj.hide_render
            and not obj.hide_get()
        ):
            trees.append(
                (
                    obj.name,
                    BVHTree.FromPolygons(
                        [obj.matrix_world @ v.co for v in obj.data.vertices],
                        [tuple(f.vertices) for f in obj.data.polygons],
                    ),
                )
            )

    def first(point, direction):
        hits = []
        for name, tree in trees:
            loc, normal, face, distance = tree.ray_cast(point, direction, 2)
            if loc is not None:
                hits.append({"object": name, "distance": distance})
        return min(hits, key=lambda h: h["distance"]) if hits else None

    surface = []
    for rectangle in SURFACE["openings"]:
        a, b, c, d = rectangle
        hit = first(world_point((a + c) / 2, (b + d) / 2, 0.8), -n)
        assert hit and hit["object"] == WALL, hit
        surface.append({"oldAperture": rectangle, "firstHit": hit})
    seams = []
    for x, z in [
        (LENGTH / 3, 27),
        (LENGTH * 2 / 3, 27),
        (LENGTH / 2, 22.8),
        (LENGTH / 2, 32.8),
    ]:
        hit = first(world_point(x, z, 0.6), -n)
        assert (
            hit
            and hit["object"] == WALL
            and abs(hit["distance"] - (0.2 + SEAM_DEPTH)) < 2e-5
        ), hit
        seams.append(
            {"x": x, "z": z, "firstHit": hit, "physicalRecessDepth": SEAM_DEPTH}
        )
    real_windows = []
    end_out = Vector((end_u.y, -end_u.x, 0))
    if end_out.dot((end_p + end_q) / 2 - centre) < 0:
        end_out = -end_out
    expected_glass = next(
        c["owned"]
        for c in changes
        if c["source"] == "MAR_V115_retained_D5_wings75_glass"
    )
    for index, rectangle in enumerate(END_SURFACE["openings"]):
        a, b, c, d = rectangle
        point = end_p + end_u * (a + (c - a) * 0.31) + Vector((0, 0, (b + d) / 2))
        hit = first(point + end_out * 0.8, -end_out)
        assert hit and hit["object"] == expected_glass, hit
        real_windows.append(
            {
                "window": index,
                "originalAperture": rectangle,
                "point": list(point),
                "firstHit": hit,
            }
        )
    assert len(real_windows) == 40
    (OUT / "real-five-column-window-first-hits.json").write_text(
        json.dumps(real_windows, indent=2) + "\n"
    )
    return surface, seams


initial = validate()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
audit = {
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "ownedObjects": owned_names,
    "archivedObjects": archives,
    "changes": changes,
    "sourceObjects": archives,
    "destinationCollection": COLLECTION,
    "removedFaces": removed,
    "scope": "Restore the registered8546_0 blank western tower wall and remove35 fictitious windows with their associated trim/guards. Add physically recessed panel joints only on this registered facade.",
    "planeRegistration": {
        "sourceSurface": SURFACE["name"],
        "p": list(p),
        "q": list(q),
        "outwardNormal": list(n),
        "outwardDirectionBasis": "Right tower registered edge centre, not whole-campus building centroid",
        "retainedWallNormalBounds": [0, 0.4],
        "exteriorSurfaceDepth": 0.4,
        "length": LENGTH,
        "zBounds": [LOW, HIGH],
        "oldApertures": SURFACE["openings"],
        "edgeOrder": [
            "8546_5 five-column real-window end",
            "8546_0 photographed blank western side",
            "8546_1 top band behind lower block",
        ],
        "trueEndSurfaceRetained": "MAR_rear_way/1376078546_5",
        "rearTopBandRetained": "MAR_MAR_rear_way/1376078546_1_pierced_wall",
    },
    "joints": {
        "verticalFractionsEstimated": [1 / 3, 2 / 3],
        "horizontalHeightsEstimated": [22.8, 32.8],
        "widthEstimated": SEAM_WIDTH,
        "recessDepthEstimated": SEAM_DEPTH,
        "basis": "Sparse photo-proportioned principal panel subdivision on photograph05 blank face; not a measured fabrication schedule",
    },
    "references": [
        {
            "local": "data/建筑图片/MAR_Marshall Building/01_建筑实拍/architecture_round5_MAR_mar_kane_05.jpg",
            "date": "2022 upload; capture date unknown",
            "supports": "Blank western side next to five-column glazed end face",
        },
        {
            "local": "result/blender/stage75/mar-fenestration.json",
            "supports": "Native edge registration and inherited apertures; not proof that the inherited windows are real",
        },
    ],
    "limitations": [
        "Only8546_0 is uniquely registered. The left tower blank facade is not unambiguously matched after115mass/court edits and is retained.",
        "Massing, wall bounds, floor datums and0.40m depth retained as model estimates; no current measured survey claimed.",
        "Panel subdivision positions/width/depth are photo estimates, not a complete certified precast shop schedule.",
        "8546_1 lower area is concealed by the lower wing. No artificial new wall is added there.",
        "All real8546_5 windows, roof/top band and hidden faces outside the registered side remain unchanged.",
    ],
}
import math

preview_origin = (-8.696325894899289, 49.33154396120258, 0)


def preview_world(local):
    angle = math.radians(22)
    x, y, z = local
    return [
        preview_origin[0] + math.cos(angle) * x - math.sin(angle) * y,
        preview_origin[1] + math.sin(angle) * x + math.cos(angle) * y,
        z,
    ]


audit["nativePreviewCamera"] = {
    "position": preview_world((-80, -100, 65)),
    "target": preview_world((-3, -1, 22)),
    "orthoScale": 77,
    "resolution": [1150, 1050],
    "coordinateSystem": "Native Blender world: Z up, metres",
    "localPosition": [-80, -100, 65],
    "localTarget": [-3, -1, 22],
    "localOrigin": list(preview_origin),
    "localRotationDegrees": 22,
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
scene = open_baseline()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(owned_names)
for obj in dst.objects:
    bpy.data.collections[COLLECTION].objects.link(obj)
for change in changes:
    copy = bpy.data.objects[change["owned"]]
    if change["source"]:
        source = bpy.data.objects[change["source"]]
        for i, mat in enumerate(source.data.materials):
            copy.data.materials[i] = mat
        source.hide_render = True
        source.hide_set(True)
    else:
        copy.data.materials[0] = bpy.data.objects[
            "MAR_V115_retained_D5_wings75_concrete"
        ].data.materials[0]
bpy.context.view_layer.update()
reloaded = validate()
assert initial == reloaded
proof = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "baselineSha256": audit["baselineSha256"],
    "savedComponentReopened": True,
    "originalObjectCount": len(originals),
    "allOriginalFingerprintsPreserved": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "retainedFaceGeometryUVMaterialSlotsPreserved": True,
    "falseWindowCountRemoved": 35,
    "blankWallFirstHitProbes": reloaded[0],
    "physicalJointRecessProbes": reloaded[1],
    "componentRenderCount": 2,
    "invalidComponentPreviewCount": 1,
    "effectiveComponentPreviewCount": 1,
    "invalidPreviewReason": "Whole-building centroid pointed the local west facade normal into the right tower; corrected with this tower edge centre before final preview",
    "fullModelSaved": False,
    "realAdjacentEndWindowCount": 40,
    "allRealAdjacentEndWindowFirstHitsPreserved": True,
    "realAdjacentEndWindowFirstHitFile": str(
        OUT / "real-five-column-window-first-hits.json"
    ),
}
# Useful southwest whole-wing view. Archived sources remain hidden.
for obj in scene.objects:
    if obj.type != "CAMERA":
        obj.hide_render = (
            not obj.name.startswith("MAR")
            or obj.name in archives
            or visibility.get(obj.name, [False])[0]
        )
import math

basis = Vector((math.cos(math.radians(22)), math.sin(math.radians(22)), 0))
normal_basis = Vector((-basis.y, basis.x, 0))
origin = Vector((-8.696325894899289, 49.33154396120258, 0))


def local_point(x, y, z):
    return origin + basis * x + normal_basis * y + Vector((0, 0, z))


focus = local_point(-3, -1, 22)
cd = bpy.data.cameras.new("MAR_PANEL_preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = local_point(-80, -100, 65)
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type, cd.ortho_scale = "ORTHO", 77
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples, scene.cycles.use_denoising = 12, True
world = bpy.data.worlds.new("MAR_PANEL_world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.52, 0.55, 0.60, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
scene.world = world
ld = bpy.data.lights.new("MAR_PANEL_key", "AREA")
ld.energy, ld.size = 24000, 40
light = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(light)
light.location = local_point(30, -45, 68)
light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
(
    scene.render.resolution_x,
    scene.render.resolution_y,
    scene.render.resolution_percentage,
) = (1150, 1050, 100)
scene.render.filepath = str(OUT / "reloaded-mar-blank-wall.png")
bpy.ops.render.render(write_still=True)
proof["nativeRender"] = str(OUT / "reloaded-mar-blank-wall.png")
(OUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
print("MAR_BLANK_WALL_VERIFIED", proof["componentSha256"])
bpy.ops.wm.quit_blender()
