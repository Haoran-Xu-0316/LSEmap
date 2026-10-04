"""OLD Clare Market: restore finite glazing across the photographed blue-frame facade.
The actual ten-pane geometry and cavities stay intact; no invented interior.
Constant Blender authoring; save an independent component rather than full campus.
"""

from pathlib import Path
import array, hashlib, json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/old_glazing152"
BASE = ROOT / "result/blender/LSE_campus_detailed_v151.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
SOURCE = "OLD_V53_Clare_glass"
OWNED = "OLD_NEXT_GLAZING152_Clare_photographed_glass"
PREFIX = "OLD_NEXT_GLAZING152_"
COMPONENT = OUT / "old-clare-glazing-component.blend"
OUT.mkdir(parents=True, exist_ok=True)


def fingerprint(obj, surface_only=False):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == "MESH":
        fields = [
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
        ]
        if not surface_only:
            fields.append((obj.data.polygons, "material_index", "i", 1))
        for coll, field, typ, width in fields:
            values = array.array(typ, [0]) * (len(coll) * width)
            coll.foreach_get(field, values)
            h.update(values.tobytes())
        for uv in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", values)
            h.update(values.tobytes())
    if not surface_only:
        h.update(
            str(
                [m.name if m else None for m in getattr(obj.data, "materials", [])]
            ).encode()
        )
    return h.hexdigest()


def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
    prior = (
        json.loads((OUT / "audit.json").read_text())
        if (OUT / "audit.json").exists()
        else None
    )
    for obj in list(bpy.data.objects):
        if obj.name.startswith(PREFIX):
            bpy.data.objects.remove(obj, do_unlink=True)
    if prior:
        obj = bpy.data.objects[SOURCE]
        state = prior["originalVisibility"][SOURCE]
        obj.hide_render, obj.hide_viewport = state[:2]
        obj.hide_set(state[2])
    for material in list(bpy.data.materials):
        if material.name.startswith(PREFIX) and not material.users:
            bpy.data.materials.remove(material)
    for scene in bpy.data.scenes:
        for layer in scene.view_layers:
            layer.update()


open_source()
BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()
originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
inspection = json.loads((OUT / "inspection.json").read_text())
panels = inspection["entrancePanels"]
assert len(panels) == 10
source = bpy.data.objects[SOURCE]
owned = source.copy()
owned.data = source.data.copy()
owned.name = OWNED
owned.data.name = OWNED
collection = bpy.data.collections["OLD_EXTERIOR"]
collection.objects.link(owned)
material = source.data.materials[0].copy()
material.name = PREFIX + "neutral_glass"
bs = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def material_values(mat):
    p = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    return {
        "name": mat.name,
        "baseColor": list(p.inputs["Base Color"].default_value),
        "roughness": p.inputs["Roughness"].default_value,
        "metallic": p.inputs["Metallic"].default_value,
        "transmission": p.inputs["Transmission Weight"].default_value,
        "alpha": p.inputs["Alpha"].default_value,
        "webOpacity": mat.get("webOpacity"),
    }


before = material_values(source.data.materials[0])
bs.inputs["Transmission Weight"].default_value = 0.22
bs.inputs["Alpha"].default_value = 0.82
material["webOpacity"] = 0.82
material.diffuse_color = (*material.diffuse_color[:3], 0.82)
owned.data.materials[0] = material
after = material_values(material)
source.hide_render = True
source.hide_set(True)


def probes():
    # Include active mesh data from all native scenes. Spatial broad phase is30m,
    # sufficient for requested2m near field; far hits recorded as uncertain shells.
    centres = [Vector(p["center"]) for p in panels]
    scene_names = {o.name for s in bpy.data.scenes for o in s.objects}
    objects = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name not in scene_names:
            continue
        ps = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        if any(
            all(
                min(p[i] for p in ps) <= c[i] + 30
                and max(p[i] for p in ps) >= c[i] - 30
                for i in range(3)
            )
            for c in centres
        ):
            objects.append(obj)

    def tree(skip):
        vs = []
        fs = []
        names = []
        for obj in objects:
            if obj.name in skip:
                continue
            k = len(vs)
            vs.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
            obj.data.calc_loop_triangles()
            fs.extend(tuple(k + i for i in t.vertices) for t in obj.data.loop_triangles)
            names.extend([obj.name] * len(obj.data.loop_triangles))
        return BVHTree.FromPolygons(vs, fs, all_triangles=True), names

    full, names = tree(set())
    back, bnames = tree({OWNED})

    def cast(tree, names, p, d, length):
        h = tree.ray_cast(p, d, length)
        return {
            "object": names[h[2]] if h[2] is not None else None,
            "distance": h[3],
            "hit": list(h[0]) if h[0] is not None else None,
        }

    result = []
    for pane in panels:
        n = Vector(pane["normal"])
        rows = []
        for r in pane["samples"]:
            p = Vector(r["paneFrontPoint"])
            first = cast(full, names, p + n * 0.4, -n, 0.8)
            behind = cast(back, bnames, p - n * 0.02, -n, 1.98)
            far = cast(back, bnames, p - n * 0.02, -n, 30)
            assert first["object"] == OWNED, first
            assert behind["object"] is None, behind
            rows.append(
                {
                    "point": list(p),
                    "glassFirstHit": first,
                    "behind02To2m": behind,
                    "farFieldUpTo30m": far,
                }
            )
        result.append(
            {
                "part": pane["part"],
                "principalFacePolygon": pane["principalFacePolygon"],
                "actualNormal": pane["normal"],
                "samples": rows,
            }
        )
    return result


def protected():
    assert fingerprint(bpy.data.objects[SOURCE], True) == fingerprint(
        bpy.data.objects[OWNED], True
    )
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
        if name != SOURCE
    )
    current = material_values(bpy.data.objects[OWNED].data.materials[0])
    assert (
        current["baseColor"] == before["baseColor"]
        and current["roughness"] == before["roughness"]
        and current["metallic"] == before["metallic"]
    )
    assert current["webOpacity"] == 0.82


protected()
before_save = probes()
bpy.data.libraries.write(str(COMPONENT), {owned}, fake_user=True, compress=True)
references = []
for filename in ["reference-04.png", "reference-08.png"]:
    path = ROOT / "data/collections/public-realm-2026/user-references" / filename
    references.append(
        {
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "captureDate": "unknown",
            "supports": "Blue-frame Clare facade glass combines reflected street with visible interior/cross-street layers; does not support opaque plates or invented interiors.",
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": BASE_SHA,
    "originalObjectCount": len(originals),
    "ownedObjects": [OWNED],
    "archivedObjects": [SOURCE],
    "changes": [
        {
            "source": SOURCE,
            "owned": OWNED,
            "action": "Finite reflective transparency across ten existing photographed Clare facade sheets; no geometry replacement or new internal surfaces",
        }
    ],
    "destinationCollection": "OLD_EXTERIOR",
    "retainNewMaterials": True,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "references": references,
    "scope": "Five Clare bays across two visible levels, including Student Services entrance. Existing four-column casements/transom, limestone/Frith reliefs/planter/LSE sculpture and Houghton detailed portal preserved.",
    "materialBefore": before,
    "materialAfter": after,
    "surfaceSha256": fingerprint(source, True),
    "glassPrincipalFaces": 10,
    "geometryUnchanged": True,
    "limitations": [
        "Optical T0.22/Alpha0.82 is a bounded visual estimate, not calibrated glazing specification. Source RGB, roughness and metallic are retained.",
        "Actual nearfield windows are clear but complete rooms beyond2m remain unmodelled or unverified. Farfield objects are recorded without identifying them as measured room boundaries.",
        "No reconstructed furniture, fake backing planes or full interior inferred.",
        "Houghton glazing, main portal/Final Sale lattice, all roof glass and unphotographed faces retain current materials.",
        "Two supplied photos cover finite Clare facade and partial upper cut-off; inherited storey heights and exact dimensions not claimed surveyed.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
open_source()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(audit["ownedObjects"])
collection = bpy.data.collections["OLD_EXTERIOR"]
owned = dst.objects[0]
collection.objects.link(owned)
source = bpy.data.objects[SOURCE]
source.hide_render = True
source.hide_set(True)
protected()
reloaded = probes()
assert reloaded == before_save
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for obj in scene.objects:
    if obj.type == "MESH" and obj.name not in members:
        obj.hide_render = True
frame = inspection["registration"]["student"]["frame"]
origin = Vector(frame["origin"])
u = Vector(frame["right"])
n = Vector(frame["outward"])
focus = origin + Vector((0, 0, 7.5))
camdata = bpy.data.cameras.new(PREFIX + "production_angle")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + n * 40 - u * 14 + Vector((0, 0, 2.5))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 25
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.resolution_x = 1250
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "OLD-reloaded-Clare-facade.png")
bpy.ops.render.render(write_still=True)
proof = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "reopenedCoordinatesTopologyUVHash": fingerprint(owned, True),
    "originalAndOwnedSurfaceEqual": True,
    "originalRGBRoughnessMetallicRetained": True,
    "explicitWebOpacity": owned.data.materials[0]["webOpacity"],
    "glassPrincipalFaces": 10,
    "glassFirstHitPassCount": 40,
    "behind02To2mClearCount": 40,
    "reopenedProbes": reloaded,
    "nativePreview": "OLD-reloaded-Clare-facade.png",
    "previewViewed": False,
    "camera": {"position": list(cam.location), "target": list(focus), "orthoScale": 25},
    "fullCampusSaved": False,
}
assert proof["baselineUnchanged"]
(OUT / "verification.json").write_text(json.dumps(proof, indent=2))
print("OLD152_DONE", proof["componentSha256"], flush=True)
bpy.ops.wm.quit_blender()
