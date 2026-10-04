"""Finite glass optics for confirmed Lincoln Chambers windows; no invented interior.
Run in Blender Text Editor.148shopfront, original geometry and all source UVs retained.
"""

from pathlib import Path
import array, hashlib, json, bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/lch_glazing149"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v148.blend"
EXPECTED = "536b63660f8542ecae569523ef8beb2c45013068487f2aaa160820225e7076f2"
PREFIX = "LCH_NEXT_GLAZING149_"
ARCHIVE = [
    "LCH_D5_arched_fanlight_glass",
    "LCH_D5_door_glazed_panel_glass",
    "LCH_D5_V42_window_glass_glass",
    "LCH_D5_V42_bay_cheek_glass_glass",
    "LCH_D5_V42_arch_glass_glass",
    "LCH_NEXT_EXTERIOR148_retained_right_basement_glass",
]
NAMES = [
    PREFIX + s
    for s in [
        "porch_fanlights",
        "porch_lights",
        "front_windows",
        "bay_cheeks",
        "central_arch",
        "right_basement",
    ]
]
COMPONENT = OUT / "lincoln-chambers-glazing149-component.blend"
PREVIOUS = (
    json.loads((OUT / "audit.json").read_text())
    if (OUT / "audit.json").exists()
    else {}
)
if BASE.exists():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED
else:
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()


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
        o = bpy.data.objects[name]
        state = PREVIOUS.get("originalVisibility", {}).get(name, [False, False, False])
        o.hide_render, o.hide_viewport = state[:2]
        o.hide_set(state[2])
    for layer in bpy.context.scene.view_layers:
        layer.update()


open_base()


def fingerprint(o):
    h = hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
    if o.type == "MESH":
        for data, field, kind, n in [
            (o.data.vertices, "co", "f", 3),
            (o.data.loops, "vertex_index", "i", 1),
            (o.data.polygons, "material_index", "i", 1),
        ]:
            ar = array.array(kind, [0]) * (len(data) * n)
            data.foreach_get(field, ar)
            h.update(ar.tobytes())
        for uv in o.data.uv_layers:
            ar = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", ar)
            h.update(ar.tobytes())
    h.update(
        str([m.name if m else None for m in getattr(o.data, "materials", [])]).encode()
    )
    return h.hexdigest()


originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
if BASE.stem.endswith("v148"):
    assert len(originals) == 5843
collection = bpy.data.collections["LCH_EXTERIOR"]
reg = json.loads((ROOT / "result/blender/lch_exterior148/audit.json").read_text())[
    "registration"
]
n = Vector(reg["normal"])
a = Vector(reg["origin"])
u = Vector(reg["axis"])
leftX = reg["leftStoreCentreX"]


def world(x, d, z):
    return a + u * x + n * d + Vector((0, 0, z))


raw = json.loads((OUT / "glazing-contacts.json").read_text())
contacts = []
discarded = []
for row in raw["contacts"]:
    o = bpy.data.objects[row["source"]]
    o.data.calc_loop_triangles()
    tri = o.data.loop_triangles[row["triangle"]]
    if (
        row["source"] in [ARCHIVE[1], ARCHIVE[2], ARCHIVE[3], ARCHIVE[5]]
        and tri.area < 0.04
    ):
        discarded.append(
            {**row, "reason": "Thin pane edge surface, not principal glazed plane"}
        )
        continue
    contacts.append(row)
assert all(any(p["source"] == name for p in contacts) for name in ARCHIVE)


def cast(mapping):
    verts = []
    faces = []
    owners = []
    ps = [
        o.matrix_world @ Vector(p)
        for o in collection.all_objects
        if o.type == "MESH" and not o.hide_render
        for p in o.bound_box
    ]
    lo = [min(p[i] for p in ps) - 1 for i in range(3)]
    hi = [max(p[i] for p in ps) + 1 for i in range(3)]
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.hide_render or not o.data.polygons:
            continue
        pts = [o.matrix_world @ Vector(p) for p in o.bound_box]
        if any(
            max(p[i] for p in pts) < lo[i] or min(p[i] for p in pts) > hi[i]
            for i in range(3)
        ):
            continue
        k = len(verts)
        verts.extend(o.matrix_world @ v.co for v in o.data.vertices)
        faces.extend(tuple(k + i for i in f.vertices) for f in o.data.polygons)
        owners.extend([o.name] * len(o.data.polygons))
    tree = BVHTree.FromPolygons(verts, faces)
    rows = []
    for p in contacts:
        normal = Vector(p["normal"])
        front = tree.ray_cast(Vector(p["origin"]), -normal, 1.2)
        name = owners[front[2]] if front[2] is not None else None
        assert name == mapping.get(p["source"], p["source"]), (name, p)
        back = tree.ray_cast(Vector(p["behindOrigin"]), -normal, 2)
        behind = owners[back[2]] if back[2] is not None else None
        assert behind == p["nearObject"], (behind, p)
        if behind:
            assert abs(back[3] - p["nearDistance"]) < 0.00002
        rows.append(
            {
                "source": p["source"],
                "firstObject": name,
                "frontPoint": list(front[0]),
                "behindObject": behind,
                "behindDistance": back[3] if back[2] is not None else None,
                "behindPoint": list(back[0]) if back[0] is not None else None,
                "behindOrigin": p["behindOrigin"],
            }
        )
    return rows


before = cast({})
owned = []
changes = []
materials = []
matCopies = {}


def pbr(m):
    p = m.node_tree.nodes["Principled BSDF"]
    return {
        "name": m.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "alpha": p.inputs["Alpha"].default_value,
        "nativeTransmission": p.inputs["Transmission Weight"].default_value,
        "metallic": p.inputs["Metallic"].default_value,
        "roughness": p.inputs["Roughness"].default_value,
        "ior": p.inputs["IOR"].default_value,
        "webOpacity": m.get("webOpacity"),
        "surfaceRenderMethod": getattr(m, "surface_render_method", None),
    }


for sourceName, newName in zip(ARCHIVE, NAMES):
    source = bpy.data.objects[sourceName]
    o = source.copy()
    o.data = source.data.copy()
    o.name = newName
    collection.objects.link(o)
    for index, oldMat in enumerate(source.data.materials):
        if oldMat.name not in matCopies:
            m = oldMat.copy()
            m.name = PREFIX + "optics_" + str(len(matCopies))
            p = m.node_tree.nodes["Principled BSDF"]
            p.inputs["Transmission Weight"].default_value = 0.38
            p.inputs["Alpha"].default_value = 0.78
            p.inputs["Metallic"].default_value = 0.08
            p.inputs["Roughness"].default_value = 0.22
            p.inputs["IOR"].default_value = 1.46
            m["webOpacity"] = 0.78
            if hasattr(m, "surface_render_method"):
                m.surface_render_method = "BLENDED"
            if hasattr(m, "use_transparency_overlap"):
                m.use_transparency_overlap = False
            matCopies[oldMat.name] = m
            materials.append(
                {
                    "original": pbr(oldMat),
                    "new": pbr(m),
                    "reason": "Official2025shows actual store transparency and upper sash reflection; estimated restrained glass optics, original tint retained",
                }
            )
        o.data.materials[index] = matCopies[oldMat.name]
    owned.append(o)
    changes.append(
        {
            "source": sourceName,
            "owned": newName,
            "action": "Preserve exact mesh,transform,UV and frame registration; replace glass optical material only",
        }
    )
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
mapping = dict(zip(ARCHIVE, NAMES))
after = cast(mapping)


def preserved():
    assert all(fingerprint(bpy.data.objects[k]) == v for k, v in originals.items())
    assert all(
        [o.hide_render, o.hide_viewport, o.hide_get()] == visibility[o.name]
        for o in bpy.data.objects
        if o.name in originals and o.name not in ARCHIVE
    )


preserved()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
ref = ROOT / "data/collections/lincoln-review/lse-volunteer-may2025.jpg"
audit = {
    "baseline": str(BASE),
    "baselineSha256": SHA,
    "ownedObjects": list(NAMES),
    "archivedObjects": list(ARCHIVE),
    "archiveObjects": list(ARCHIVE),
    "changes": changes,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "materials": materials,
    "references": [
        {
            "path": str(ref),
            "sha256": hashlib.sha256(ref.read_bytes()).hexdigest(),
            "url": "https://blogs.lse.ac.uk/vcb/2025/09/22/welcome-to-lse-or-welcome-back/",
            "date": "FilenameMay2025;article2025-09-22;captureEXIFunverified",
        }
    ],
    "beforeProbes": before,
    "afterProbes": after,
    "contacts": contacts,
    "excludedThinEdgeSamples": discarded,
    "frameOccludedSamples": raw["frameOccludedSamples"],
    "retainedBoundaryContacts": [p for p in after if p["behindObject"]],
    "registration": reg,
    "limitations": [
        "Optics T0.38,Alpha/webOpacity0.78,roughness0.22,metallic0.08,IOR1.46 estimated; original baseColour retained.",
        "Eight sidefanlight peripheral samples encounter existing external stone pier after0.17-0.19m; these are registered return-wall boundaries,not a whole window backing plate. Photograph insufficient to prove external pier should be excavated, so masonry preserved.",
        "One-sided originalfanlight/arch glass planes have no separate back-face; near-field rays start5mmbehind measured plane. Thick panes use actual rear-face contacts.",
        "Two-meter checks do not establish full room/interior; no fictitious scene or backboard.",
        "148leftwhitepanel,rightbasement,windowgrids and allroof/masonry/frames preserved.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
open_base()
collection = bpy.data.collections["LCH_EXTERIOR"]
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(NAMES)
for o in dst.objects:
    collection.objects.link(o)
for name in ARCHIVE:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
reloaded = cast(mapping)
assert reloaded == after
preserved()
for name in NAMES:
    for m in bpy.data.objects[name].data.materials:
        assert (
            abs(m["webOpacity"] - 0.78) < 1e-6
            and abs(
                m.node_tree.nodes["Principled BSDF"]
                .inputs["Transmission Weight"]
                .default_value
                - 0.38
            )
            < 1e-6
        )
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for o in scene.objects:
    if o.type not in {"LIGHT", "CAMERA"} and o.name not in members:
        o.hide_render = True
focus = world(leftX / 2, 0, 6.5)
camdata = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + n * 30 + u * 0.3 + Vector((0, 0, 1))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 20
scene.camera = cam
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1400
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "reloaded-lch-glazing.png")
bpy.ops.render.render(write_still=True)
v = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == SHA,
    "reloadedProbes": reloaded,
    "probeCount": len(reloaded),
    "nearFieldBoundaryCount": sum(p["behindObject"] is not None for p in reloaded),
    "webOpacityVerified": 0.78,
    "render": "reloaded-lch-glazing.png",
    "camera": list(cam.location),
    "target": list(focus),
}
(OUT / "verification.json").write_text(json.dumps(v, indent=2) + "\n")
print("LCH149_VERIFIED", len(originals), len(reloaded), v["componentSha256"])
bpy.ops.wm.quit_blender()
