"""Register CBG low-wing lower stone/shade skins to their evidenced street sides.
Run in Blender's Text Editor. No full campus output and no command-line settings.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/cbg_facade_registration_next"
OUT.mkdir(parents=True, exist_ok=True)
PREFIX = "CBG_NEXT_REGISTERED_"
BASE = ROOT / "result/blender/LSE_campus_detailed_v143.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
previous = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else None
)
registration_review = (
    previous.get("facadeRegistration", previous.get("facadeRegistrationConflict", {}))
    if previous
    else {}
)
registration_review["status"] = (
    "Root independently checked GIS transform and viewedRSHP020/026; bounded low-wing skin-side exchange accepted"
)
SOURCES = [
    "CBG_D_houghton_stone_rainscreen",
    "CBG_D_stone_horizontal_shadow_joints",
    "CBG_D_gold_solar_blades",
    "CBG_D_pale_solar_blades",
    "CBG_D_shade_leading_silver_strips",
    "CBG_D_shade_cantilever_brackets",
    "CBG_D_shade_module_caps",
    "CBG_D_shade_fixing_bolt_heads",
    "CBG_D_shade_mid_tie_rods",
]


def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    bpy.context.window.scene = scene
    if previous:
        for name in previous.get("ownedObjects", []):
            obj = bpy.data.objects.get(name)
            if obj:
                mesh = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                mesh.use_fake_user = False
                if not mesh.users:
                    bpy.data.meshes.remove(mesh)
        for name in previous.get("archivedObjects", []):
            obj = bpy.data.objects[name]
            v = previous["originalVisibility"][name]
            obj.hide_render, obj.hide_viewport = v[:2]
            obj.hide_set(v[2])
    for layer in scene.view_layers:
        layer.update()
    return scene


scene = open_source()
col = bpy.data.collections["CBG_EXTERIOR"]


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, n in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * n)
            data.foreach_get(field, values)
            h.update(values.tobytes())
        for layer in o.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            h.update(values.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


original = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith("v143"):
    assert sha == "7cf90954936581f8b9416018f34ce06984464d8451fe8778a65d3c025181367d"
    assert len(original) == 5694
site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
cx, cy = next(b["center"] for b in site["buildings"] if b["code"] == "CBG")
c, s = math.cos(math.radians(58)), math.sin(math.radians(58))


def local(p):
    return Vector(
        (c * (p.x - cx) + s * (p.y - cy), -s * (p.x - cx) + c * (p.y - cy), p.z)
    )


def world(p):
    x, y, z = p
    return Vector((cx + c * x - s * y, cy + s * x + c * y, z))


def signed_part_volume(faces):
    total = 0
    origin = next(iter(faces)).verts[0].co.copy()
    for face in faces:
        points = [v.co - origin for v in face.verts]
        for i in range(1, len(points) - 1):
            total += points[0].dot(points[i].cross(points[i + 1])) / 6
    return total


owned = []
changes = []
stats = []
shade_centres = []
for name in SOURCES:
    old = bpy.data.objects[name]
    assert not old.hide_render
    new = old.copy()
    new.data = old.data.copy()
    new.name = PREFIX + name.removeprefix("CBG_D_")
    new.data.name = new.name
    col.objects.link(new)
    for mod in list(new.modifiers):
        if mod.type == "BEVEL":
            new.modifiers.remove(mod)
    bm = bmesh.new()
    bm.from_mesh(new.data)
    original_volume = bm.calc_volume(signed=True)
    seen = set()
    moved = []
    for vertex in bm.verts:
        if vertex in seen:
            continue
        seen.add(vertex)
        stack = [vertex]
        part = []
        while stack:
            v = stack.pop()
            part.append(v)
            for edge in v.link_edges:
                n = edge.other_vert(v)
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        points = [local(new.matrix_world @ v.co) for v in part]
        lo = [min(p[k] for p in points) for k in range(3)]
        hi = [max(p[k] for p in points) for k in range(3)]
        centre = [(lo[k] + hi[k]) / 2 for k in range(3)]
        stone = "stone" in name
        selected = stone or (
            lo[0] > 7.05
            and hi[0] < 35
            and lo[2] > 4.25
            and hi[2] < 12.35
            and lo[1] > 1.9
        )
        if not selected:
            continue
        assert lo[0] > 7 and hi[0] < 35 and lo[2] > 4.25 and hi[2] < 12.35, (
            name,
            lo,
            hi,
        )
        faces = {f for v in part for f in v.link_faces}
        volume_before = signed_part_volume(faces)
        for vertex, p in zip(part, points):
            p.y = -12 - p.y
            vertex.co = new.matrix_world.inverted() @ world(p)
        # Reflection changes handedness. Reverse these complete solid components,
        # retaining each loop's UV association; outward winding is not optional.
        bmesh.ops.reverse_faces(bm, faces=list(faces))
        bmesh.ops.recalc_face_normals(bm, faces=list(faces))
        volume_after = signed_part_volume(faces)
        assert volume_after > 0, (name, volume_after)
        assert abs(abs(volume_before) - volume_after) < max(
            0.002, abs(volume_before) * 0.03
        ), (name, volume_before, volume_after)
        moved.append(
            {
                "oldBounds": [lo, hi],
                "newYBounds": [-12 - hi[1], -12 - lo[1]],
                "faces": len(faces),
                "signedVolumeBefore": volume_before,
                "signedVolumeAfter": volume_after,
            }
        )
        if name == "CBG_D_gold_solar_blades":
            shade_centres.append([centre[0], -12 - centre[1], centre[2]])
    assert moved, name
    new_volume = bm.calc_volume(
        signed=True
    )  # Original source boxes have inward winding; selected solids are now outward.
    bm.to_mesh(new.data)
    bm.free()
    new.data.update()
    old.hide_render = True
    old.hide_set(True)
    owned.append(new)
    stats.append(
        {
            "source": name,
            "owned": new.name,
            "movedClosedComponents": len(moved),
            "registration": moved,
            "signedVolumeBefore": original_volume,
            "signedVolumeAfter": new_volume,
            "reflectionWindingCorrected": True,
            "selectedClosedComponentsRecalculatedOutward": True,
        }
    )
    changes.append(
        {
            "source": name,
            "owned": new.name,
            "action": "Exchange only low-wing lower floor1/2 stone/shade skin betweenY-14 andY+2 by corrected reflection; all other disconnected components retained",
        }
    )
N = (world((0, 1, 0)) - world((0, 0, 0))).normalized()


def tree():
    verts = []
    faces = []
    owners = []
    for o in col.all_objects:
        if o.type != "MESH" or o.hide_render:
            continue
        offset = len(verts)
        verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
        faces.extend(tuple(offset + i for i in p.vertices) for p in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
    return BVHTree.FromPolygons(verts, faces), owners


BASE_GLASS = "CBG_NEXT_office_retained_CBG_NEXT_neutral_curtain_wall_glazing"
STONE = PREFIX + "houghton_stone_rainscreen"
GOLD = PREFIX + "gold_solar_blades"


def checks():
    bvh, owners = tree()
    rows = []

    def probe(label, p, d, expected, normal_sign=None):
        hit = bvh.ray_cast(world(p), d, 5)
        actual = owners[hit[2]] if hit[2] is not None else None
        assert actual == expected, (label, p, actual, expected)
        dot = hit[1].dot(N)
        if normal_sign is not None:
            assert dot * normal_sign > 0.9, (label, dot)
        rows.append(
            {
                "label": label,
                "localOrigin": list(p),
                "firstSurface": actual,
                "hitLocal": list(local(hit[0])),
                "normalDotLocalPositiveY": dot,
            }
        )

    for floor in (1, 2):
        z = (floor + 0.5) * 25 / 6
        for x in [10.5, 17.5, 24.5, 31.5]:
            probe("street stone", (x, 3.5, z), -N, STONE, 1)
        for x in [7.65, 14.35, 21.35, 28.6, 34.35]:
            probe("street clear window", (x, 3.5, z), -N, BASE_GLASS)
        # Solar leaves are outside the original negative-Y glass, not an opaque wall.
        for centre in shade_centres:
            if abs(centre[2] - z) < 0.1:
                probe("square red blade", (centre[0], -16.5, z), N, GOLD)
        for i in [2, 8, 14, 20, 24]:
            module = 7 + (i + 0.5) * 28 / 26
            candidates = []
            for offset in [0.36, 0.40, 0.45, 0.50, 0.55, 0.60]:
                x = module + offset
                hit = bvh.ray_cast(world((x, -16.5, z)), N, 5)
                actual = owners[hit[2]] if hit[2] is not None else None
                candidates.append({"offset": offset, "firstSurface": actual})
                if actual == BASE_GLASS:
                    probe(
                        "square clear gap between blades", (x, -16.5, z), N, BASE_GLASS
                    )
                    rows[-1]["apertureSampleCandidates"] = candidates
                    break
            else:
                raise AssertionError(
                    (
                        "no true glazing aperture between these blades",
                        i,
                        floor,
                        candidates,
                    )
                )
    # No end-face or tower source is replaced; retain genuinely clear end cells.
    D = Vector((c, s, 0))
    for z in [6.25, 10.4166667]:
        probe(
            "entrance end clear cell",
            (5.8, -1.17, z),
            D,
            "CBG_NEXT_neutral_end_wall_glazing",
        )
    for x, z in [(-40.2, 14), (-34.2, 38), (-28.2, 46)]:
        probe("tower office unchanged", (x, -2.20, z), N, "CBG_NEXT_office_glass")
    return rows


records = checks()
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in original.items())
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
component = OUT / "cbg-facade-registration-component.blend"
names = [o.name for o in owned]
material_names = {
    o.name: [m.name if m else None for m in o.data.materials] for o in owned
}
bpy.data.libraries.write(str(component), set(owned), fake_user=True)
refs = json.loads(
    (ROOT / "data/collections/cbg_facade_contractor/source-index.json").read_text()
)["photographs"]
for number in ["020", "026"]:
    photo = ROOT / f"data/collections/exteriors/images/cbg_rshp_{number}.jpg"
    refs.append(
        {
            "file": str(photo.relative_to(ROOT)),
            "sha256": hashlib.sha256(photo.read_bytes()).hexdigest(),
            "url": "https://rshp.com/projects/education/lse-centre-building/",
            "captureDate": "unknown;2019project not photograph date",
        }
    )
focus = world((-8, -1, 25))
camera_local = (-110, -140, 61)
camera_position = world(camera_local)
audit = {
    "baselineSha256": sha,
    "baselinePath": str(BASE),
    "ownedObjects": names,
    "archivedObjects": SOURCES,
    "changes": changes,
    "originalFingerprints": original,
    "originalVisibility": visibility,
    "originalObjectCount": len(original),
    "sourceCollection": "CBG_EXTERIOR",
    "destinationCollection": "CBG_EXTERIOR",
    "references": refs,
    "facadeRegistration": registration_review,
    "changeSummary": "Swap low-wing lower2storeys stone street skin and glass/shading square skin to the geographic/photosupported sides; retain the2original glass skins and their real clear windows.",
    "reflectionChecks": stats,
    "sourceMaterialSlots": material_names,
    "camera": {
        "position": list(camera_position),
        "target": list(focus),
        "localPosition": camera_local,
        "type": "ORTHO",
        "orthographicScale": 95,
        "resolution": [1100, 950],
    },
    "limitations": [
        "Photo capture dates unknown; shapes, dimensions and levels inherited photo/GIS estimates, not measured survey.",
        "Both existing curtain-wall grids and all glass optical materials preserved; no fake opaque backing.",
        "Main tower, tower offices, end faces, street doors, roofs and low-wing otherstoreys preserved.",
        "Separate top-floor canopy/vent pane registration and office interior-boundary questions remain unresolved.",
        "Red-primary blade fronts/orange returns preserved, not recoloured from daylight photographs.",
        "Inherited source boxes had inward winding; only swapped closed components recalculated outward, original glass remains preserved.",
    ],
    "surfaceProbes": records,
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2))
scene = open_source()
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = names
for o in dst.objects:
    col = bpy.data.collections["CBG_EXTERIOR"]
    col.objects.link(o)
    # Reuse unchanged source material IDs after the library append.
    for slot, name in zip(o.material_slots, material_names[o.name]):
        slot.material = bpy.data.materials.get(name) if name else None
for name in SOURCES:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:
    layer.update()
reloaded = checks()
assert reloaded == records
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in original.items())
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
proof = {
    "componentSha256": hashlib.sha256(component.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "originalObjectCount": len(original),
    "unrelatedVisibilityPreserved": True,
    "fullModelSaved": False,
    "firstSurfaceChecks": reloaded,
    "windingCorrected": True,
    "glassMaterialsPreserved": True,
    "towerAndEndFacesPreserved": True,
    "camera": audit["camera"],
}
for o in scene.objects:
    if o.type != "CAMERA" and not o.name.startswith("CBG"):
        o.hide_render = True
cd = bpy.data.cameras.new(PREFIX + "preview")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = camera_position
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 95
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new(PREFIX + "preview_world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.65, 0.7, 0.75, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
ld = bpy.data.lights.new(PREFIX + "area", "AREA")
ld.energy = 45000
ld.shape = "DISK"
ld.size = 60
light = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(light)
light.location = world((-10, -50, 85))
light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_x = 1100
scene.render.resolution_y = 950
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "reloaded-square-envelope.png")
bpy.ops.render.render(write_still=True)
proof.update(
    {
        "nativeRender": str(OUT / "reloaded-square-envelope.png"),
        "modifiedRenderCount": 1,
        "priorReadOnlyRenderCount": 1,
    }
)
(OUT / "verification.json").write_text(json.dumps(proof, indent=2))
print("CBG_REGISTERED_VERIFIED", len(original), len(reloaded))
bpy.ops.wm.quit_blender()
