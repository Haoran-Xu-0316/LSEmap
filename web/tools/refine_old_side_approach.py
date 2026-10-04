"""Build the registered continuous OLD right-hand approach ramp and silver rail.
Run in Blender Text Editor. Existing external/internal four-step flights and threshold remain unchanged.
"""

from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old_side_approach_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v142.blend"
BASE_SHA = "94dd2300c8da557ab333b664f6382d4fd5f57c5f533ab18ecc2d94a15e75e4a1"
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
    BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()

PREFIX = "OLD_NEXT_APPROACH_"
NAMES = [
    PREFIX + k
    for k in [
        "continuous_ramp_surface",
        "tapered_stone_sidewall",
        "silver_posts",
        "continuous_handrail",
        "masonry_junction_return",
    ]
]
COMPONENT = OUT / "old-side-approach-component.blend"


def open_base():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    for name in NAMES:
        obj = bpy.data.objects.get(name)
        if obj:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            mesh.use_fake_user = False
            if not mesh.users:
                bpy.data.meshes.remove(mesh)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
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
if BASE.stem.endswith("v142"):
    assert len(originals) == 5662
collection = bpy.data.collections["OLD_EXTERIOR"]
reg = json.loads((ROOT / "result/blender/old_houghton_next/audit.json").read_text())[
    "registration"
]
origin, u, normal = [Vector(reg[k]) for k in ["origin", "right", "outward"]]
angle = math.atan2(u.y, u.x)


def world(x, d, z):
    return origin + u * x + normal * d + Vector((0, 0, z))


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(normal), p.z))


landing = bpy.data.objects["OLD_NEXT_ACCESS_threshold_landing"]
points = [local(landing.matrix_world @ v.co) for v in landing.data.vertices]
START = max(p.x for p in points)
HEIGHT = max(p.z for p in points)
OUTER = max(p.y for p in points)
# Same registered1900px elevation frame used by accepted112; endpoint atpx765.
# This is an estimated station in an existing elevation, not a measured plan dimension.
PIXEL_END = 765.0
END = -34.50 + (PIXEL_END - 240) / 1294 * 56.98
STREET = 0.050
WALL_THICKNESS = 0.18
RAIL_D = OUTER - WALL_THICKNESS / 2
RAIL_HEIGHT = 0.90
assert (
    abs(START + 23.25366) < 0.002
    and abs(HEIGHT - 0.69) < 0.002
    and abs(OUTER - 1.25) < 0.002
)
LENGTH = END - START
assert 11 < LENGTH < 13


def top(x):
    return HEIGHT + (STREET - HEIGHT) * (x - START) / LENGTH


sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials

materials.clear()
for key, source in [
    ("stone", landing.data.materials[0]),
    (
        "silver",
        bpy.data.objects["OLD_NEXT_ACCESS_exterior_handrails"].data.materials[0],
    ),
    (
        "facadeStone",
        bpy.data.objects["OLD_D5_houghton112_middle_stone"].data.materials[0],
    ),
]:
    material = source.copy()
    material.name = PREFIX + key
    materials[key] = material
batches = {}


def batch(label, key):
    if label not in batches:
        geometry = Geometry("OLD", label, key)
        geometry.name = PREFIX + label
        batches[label] = geometry
    return batches[label]


def wedge(label, d0, d1):
    # Closed triangular prism tapers exactly to the native street, with no raised terminal cap.
    verts = [
        world(START, d0, HEIGHT),
        world(START, d1, HEIGHT),
        world(END, d0, STREET),
        world(END, d1, STREET),
        world(START, d0, STREET),
        world(START, d1, STREET),
    ]
    batch(label, "stone").add(
        verts, [(0, 2, 3, 1), (4, 5, 3, 2), (0, 1, 5, 4), (0, 4, 2), (1, 3, 5)]
    )


wedge("continuous_ramp_surface", 0, OUTER - WALL_THICKNESS)
wedge("tapered_stone_sidewall", OUTER - WALL_THICKNESS, OUTER)


def tube(label, a, b, radius=0.024):
    a, b = world(*a), world(*b)
    t = (b - a).normalized()
    v = t.cross(Vector((0, 0, 1)))
    if v.length < 0.001:
        v = u.copy()
    v.normalize()
    w = t.cross(v)
    segments = 12
    vertices = [
        p
        + radius
        * (
            v * math.cos(i * math.tau / segments)
            + w * math.sin(i * math.tau / segments)
        )
        for p in [a, b]
        for i in range(segments)
    ]
    faces = [tuple(reversed(range(segments))), tuple(range(segments, 2 * segments))] + [
        (i, (i + 1) % segments, (i + 1) % segments + segments, i + segments)
        for i in range(segments)
    ]
    batch(label, "silver").add(vertices, faces)


# Eight posts estimated from the visible existing-elevation support rhythm. No scan claim.
POSTS = [START + 0.14 + (LENGTH - 0.54) * i / 7 for i in range(8)]
for x in POSTS:
    tube("silver_posts", (x, RAIL_D, top(x)), (x, RAIL_D, top(x) + RAIL_HEIGHT), 0.027)
tube(
    "continuous_handrail",
    (START, RAIL_D, HEIGHT + RAIL_HEIGHT),
    (END - 0.25, RAIL_D, top(END - 0.25) + RAIL_HEIGHT),
)
# Connect to the actual retained upper end of the right exterior stair handrail.
# Its native station and height are inherited from accepted OLD_NEXT_ACCESS registration.
access = json.loads((ROOT / "result/blender/old_access_next/audit.json").read_text())[
    "registration"
]
join = (access["centreX"] + 2.95, 1.43, HEIGHT + RAIL_HEIGHT)
tube("continuous_handrail", join, (START, RAIL_D, HEIGHT + RAIL_HEIGHT))
# Close the missing junction between two registered masonry planes, never a glazing bay.
# A narrow front bridge and perpendicular return share a boundary; no original mesh changes.
JUNCTION_LEFT = -18.926475
JUNCTION_RIGHT = -18.280494
JUNCTION_TOP = 16.895


def stone_box(x0, x1, d0, d1, z0, z1):
    vertices = [world(x, d, z) for z in [z0, z1] for d in [d0, d1] for x in [x0, x1]]
    batch("masonry_junction_return", "facadeStone").add(
        vertices,
        [
            (0, 2, 3, 1),
            (4, 5, 7, 6),
            (0, 1, 5, 4),
            (2, 6, 7, 3),
            (0, 4, 6, 2),
            (1, 3, 7, 5),
        ],
    )


stone_box(JUNCTION_LEFT, -18.410494, -2.24, -1.84, HEIGHT, JUNCTION_TOP)
stone_box(-18.410494, JUNCTION_RIGHT, -2.24, 0.005, HEIGHT, JUNCTION_TOP)
owned = [g.finish() for g in batches.values()]
# Keep exact shared boundary coordinates; a bevel would retract the registered seams.
for obj in owned:
    for modifier in list(obj.modifiers):
        obj.modifiers.remove(modifier)
assert sorted(o.name for o in owned) == sorted(NAMES)
probes = []
for i in range(13):
    x = START + 0.02 + (LENGTH - 0.04) * i / 12
    for d in [0.28, 0.80]:
        probes.append(
            {
                "kind": "rampSurface",
                "origin": list(world(x, d, top(x) + 0.30)),
                "direction": [0, 0, -1],
                "distance": 4,
                "expectedObject": NAMES[0],
                "expectedZ": top(x),
            }
        )
    probes.append(
        {
            "kind": "stoneFace",
            "origin": list(world(x, OUTER + 1, (top(x) + STREET) / 2)),
            "direction": list(-normal),
            "distance": 2,
            "expectedObject": (
                "OLD_NEXT_ACCESS_external_four_steps" if i == 0 else NAMES[1]
            ),
        }
    )
for x in POSTS:
    probes.append(
        {
            "kind": "silverRail",
            "origin": list(world(x, RAIL_D, top(x) + RAIL_HEIGHT + 1)),
            "direction": [0, 0, -1],
            "distance": 1.2,
            "expectedObject": NAMES[3],
        }
    )
for x, expected in [
    (START - 0.001, landing.name),
    (START + 0.001, NAMES[0]),
    (END - 0.001, NAMES[0]),
    (END + 0.001, None),
]:
    probes.append(
        {
            "kind": "seam",
            "origin": list(
                world(
                    x,
                    0.55,
                    (HEIGHT if x < START else top(x) if x < END else STREET) + 0.30,
                )
            ),
            "direction": [0, 0, -1],
            "distance": 3,
            "expectedObject": expected,
            "expectedZ": HEIGHT if x < START else top(x) if x < END else STREET,
        }
    )
for d in [1.475, 1.925, 2.375, 2.825]:
    probes.append(
        {
            "kind": "retainedExternalSteps",
            "origin": list(world(access["centreX"], d, 3)),
            "direction": [0, 0, -1],
            "distance": 4,
        }
    )
for d in [-3.34, -3.62, -3.90, -4.18]:
    probes.append(
        {
            "kind": "retainedInternalSteps",
            "origin": list(world(access["centreX"], d, 3)),
            "direction": [0, 0, -1],
            "distance": 4,
        }
    )
# A ray0.40m above the whole walking line proves no new opaque cross-wall blocks the ramp.
a = world(START + 0.01, 0.55, top(START + 0.01) + 0.40)
b = world(END - 0.01, 0.55, top(END - 0.01) + 0.40)
probes.append(
    {
        "kind": "clearTravelLine",
        "origin": list(a),
        "direction": list((b - a).normalized()),
        "distance": (b - a).length,
    }
)
a = world(START + 0.01, 0.55, top(START + 0.01) + 1.50)
b = world(END - 0.01, 0.55, top(END - 0.01) + 1.50)
probes.append(
    {
        "kind": "clearHeadTravelLine",
        "origin": list(a),
        "direction": list((b - a).normalized()),
        "distance": (b - a).length,
    }
)

# Front and side probes establish physical closure; neighboring window contacts stay unchanged.
for z in [2.0, 6.0, 10.0, 14.0, 16.6, 16.85]:
    for x in [-18.90, -18.70, -18.50, -18.35]:
        probes.append(
            {
                "kind": "junctionFront",
                "origin": list(world(x, 4, z)),
                "direction": list(-normal),
                "distance": 10,
                "expectedObject": NAMES[4],
            }
        )
    probes.append(
        {
            "kind": "junctionSide",
            "origin": list(world(-17.0, -0.9, z)),
            "direction": list(-u),
            "distance": 5,
            "expectedObject": NAMES[4],
        }
    )
for z in [2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 17.0, 18.0, 19.0]:
    for x in [-19.8, -17.3]:
        probes.append(
            {
                "kind": "retainedFacadeContact",
                "origin": list(world(x, 4, z)),
                "direction": list(-normal),
                "distance": 10,
            }
        )
probes.append(
    {
        "kind": "retainedAtticContact",
        "origin": list(world(-18.5, 4, 16.90)),
        "direction": list(-normal),
        "distance": 10,
    }
)


def cast(exclude=()):
    verts = []
    faces = []
    owners = []
    for o in bpy.context.scene.objects:
        if (
            o.type != "MESH"
            or not len(o.data.vertices)
            or o.hide_render
            or o.name in exclude
        ):
            continue
        bounds = [local(o.matrix_world @ Vector(p)) for p in o.bound_box]
        if (
            max(p.x for p in bounds) < START - 9
            or min(p.x for p in bounds) > END + 2
            or max(p.y for p in bounds) < -5
            or min(p.y for p in bounds) > 5
            or max(p.z for p in bounds) < -0.2
            or min(p.z for p in bounds) > 24
        ):
            continue
        k = len(verts)
        verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
        faces.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
    tree = BVHTree.FromPolygons(verts, faces)
    result = []
    for p in probes:
        hit = tree.ray_cast(Vector(p["origin"]), Vector(p["direction"]), p["distance"])
        result.append(
            {
                **p,
                "firstObject": owners[hit[2]] if hit[2] is not None else None,
                "hitZ": hit[0].z if hit[0] is not None else None,
                "hitLocal": list(local(hit[0])) if hit[0] is not None else None,
            }
        )
    return result


before = cast(NAMES)
for probe, existing in zip(probes, before):
    if probe["kind"].startswith("junction") and existing["firstObject"]:
        probe["expectedObject"] = existing["firstObject"]
before = cast(NAMES)
after = cast()
for p in after:
    if p.get("expectedObject"):
        assert p["firstObject"] == p["expectedObject"], p
    if p.get("expectedZ") is not None:
        assert p["hitZ"] is not None and abs(p["hitZ"] - p["expectedZ"]) < 0.0002, p
    if p["kind"] in ["clearTravelLine", "clearHeadTravelLine"]:
        assert p["firstObject"] is None, p
assert [p for p in before if p["kind"].startswith("retained")] == [
    p for p in after if p["kind"].startswith("retained")
]
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals
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


references = []
for rel, coverage, date in [
    (
        "data/collections/old-roof-2024/existing-south.pdf",
        "Existing/strip-out south elevation080201P1, not proposed. Last low ramp wall and rail endpoint around registeredpx765.",
        "2022-12-07",
    ),
    (
        "data/collections/public-realm-2026/user-references/reference-09.png",
        "User long street photo confirms raised stone-sided approach and silver rail. No measured dimensions.",
        "capture unknown",
    ),
    (
        "data/建筑图片/OLD_Old Building/01_建筑实拍/campus_photos_round2_OLD_old_webbyates_01.jpg",
        "Built frontal portal photograph shows route connected to entry platform and declining beyond right side.",
        "capture unknown; project completed2024",
    ),
]:
    p = ROOT / rel
    references.append(
        {
            "path": str(p),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "coverage": coverage,
            "date": date,
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": BASE_SHA,
    "ownedObjects": NAMES,
    "archivedObjects": [],
    "archiveObjects": [],
    "changes": [
        {
            "source": None,
            "owned": n,
            "action": "Add connected registered visible continuous side approach; preserve existing portal and both four-step flights",
        }
        for n in NAMES
    ],
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "references": references,
    "registration": {
        "origin": list(origin),
        "right": list(u),
        "outward": list(normal),
        "pixelToLocalX": "x=-34.50+(px-240)/1294*56.98",
        "endpointPixel": PIXEL_END,
        "startX": START,
        "endX": END,
        "length": LENGTH,
        "endpointXEstimatedUncertainty": 0.35,
        "startZ": HEIGHT,
        "endZ": STREET,
        "heightSources": "Start inherited from active OLD_NEXT_ACCESS_threshold_landing; end inherited native Houghton paving0.05. Neither is a surveyed spot height. Drawing GF19.345/GL18.100 are not reused as ramp threshold.",
        "nominalProjectionWidth": OUTER,
        "stoneEdgeThickness": WALL_THICKNESS,
        "clearSurfaceWidth": OUTER - WALL_THICKNESS,
        "entrySidewallOcclusion": "First approximately0.36m of outward sidewall adjoins retained wider external fan flight and is occluded in horizontal first-contact probes; originals unchanged.",
        "slope": "Linear descent to the right from registered threshold to existing-elevation endpoint; width, linear slope, intermediate level and support stations estimated.",
        "postsX": POSTS,
        "handrailJoinNative": join,
        "drawingStatus": "existing-south080201P1; proposedAA/BB/DD reviewed for context but not treated as measured current ramp section.",
    },
    "materials": {
        "sourceStone": pbr(landing.data.materials[0]),
        "ownedStone": pbr(materials["stone"]),
        "sourceSilver": pbr(
            bpy.data.objects["OLD_NEXT_ACCESS_exterior_handrails"].data.materials[0]
        ),
        "ownedSilver": pbr(materials["silver"]),
        "originalMaterialsNotChanged": True,
    },
    "uv": {
        "method": "Metric planar SurfaceUV for every face; tubular rails have longitudinal planar UV projection.",
        "ownedLayers": {o.name: [u.name for u in o.data.uv_layers] for o in owned},
    },
    "beforeProbes": before,
    "afterProbes": after,
    "limitations": [
        "Existing elevation endpoint is visually registeredpx765±approximately8px/0.35m; not a surveyed plan terminal.",
        "Overall1.25m projection and0.18m stone edge/0.90m handrail height are estimates; no accessibility compliance claim.",
        "Linear slope uses native start0.69/end0.05; exact built gradient and curvature unknown.",
        "Only the complete registered visible slope segment is constructed, not a guessed continuation to the far building corner.",
        "No global street, existing four-step flights, doorway, arch, windows or roof geometry modified.",
    ],
}
audit["registration"][
    "endpointBayNote"
] = "px765 is near third middle low-window stationpx764, not second; terminology corrected after comparing accepted112 window centres."
audit["verificationNotes"] = {
    "surfaceRays": "Downward surface probes originate0.30m above the slope so that pre-existing facade cornices aroundz1.99 do not replace walking-surface contact. A second whole-length head-height ray remains clear.",
    "sidewallFirstPoint": "First0.36m adjoins wider retained entrance step edge; outward sidewall ray there correctly encounters original stair, not an invented new wall.",
}
audit["shellClosure"] = {
    "cause": "Real missing masonry: two-sided baseline front and side rays return no polygon, not backface culling or shadow.",
    "sourceBoundaries": {
        "entryStoneRightX": -18.906475,
        "middleStoneLeftX": -18.295494,
        "entryFrontDepth": -1.789021,
        "middleFrontDepth": 0.0,
        "atticStartZ": 16.895,
    },
    "ownedObject": NAMES[4],
    "frontBridgeDepth": -1.84,
    "bridgeRecessReason": "Approximately0.05m recessed from entry ashlar so that retained projecting cornice end faces remain first contacts.",
    "shape": "Two adjoining closed stone prisms form a narrow front bridge and perpendicular return.0.015..0.02m station overlap closes source boundaries; bridge front is recessed0.05m from ashlar to retain cornice end contact.",
    "heightRange": [HEIGHT, JUNCTION_TOP],
    "limits": "Photos confirm continuous masonry, not surveyed setback depth. Native plane difference is preserved rather than asserted as measured built geometry. Two nearest real window apertures are outside closure bounds.",
    "nativeEvidence": ["shell-inspection.json", "shell-upper-inspection.json"],
}
audit["materials"]["sourceFacadeStone"] = pbr(
    bpy.data.objects["OLD_D5_houghton112_middle_stone"].data.materials[0]
)
audit["materials"]["ownedFacadeStone"] = pbr(materials["facadeStone"])
audit["changes"][-1][
    "action"
] = "Add missing registered solid stone junction and return between existing entry and middle planes; preserve original masonry and glazing."
audit["limitations"].append(
    "Facade junction depth follows current registered native planes; exact built setback and course rhythm remain unmeasured."
)
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["OLD_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = NAMES
for o in dst.objects:
    collection.objects.link(o)
for sc in bpy.data.scenes:
    for layer in sc.view_layers:
        layer.update()
assert cast() == after
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in originals.items())
assert all(
    [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
    for o in bpy.data.objects
    if o.name in originals
)
verification = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "reloadedProbes": after,
    "startSeamConnected": True,
    "endSeamFlushToStreet": True,
    "retainedFourStepFlightsUnchanged": True,
    "clearTravelLine": True,
    "clearHeadTravelLine": True,
    "ownedModifiers": 0,
    "junctionClosed": True,
    "retainedFacadeContactsUnchanged": True,
    "nativeRender": "reloaded-old-side-approach.png",
}
(OUT / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if (
        o.type == "MESH"
        and o.name not in members
        and o.name not in ["SITE_V48_Houghton_Street", "Road_Houghton Street.001"]
    ):
        o.hide_render = True
focus = world(-22, 0.5, 8.5)
camera = bpy.data.cameras.new(PREFIX + "review_camera")
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
cam.location = focus + normal * 40 - u * 16 + Vector((0, 0, 12))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camera.type = "ORTHO"
camera.ortho_scale = 30
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-old-side-approach.png")
bpy.ops.render.render(write_still=True)
print("OLD_APPROACH_VERIFIED", len(originals), LENGTH, len(after), flush=True)
bpy.ops.wm.quit_blender()
