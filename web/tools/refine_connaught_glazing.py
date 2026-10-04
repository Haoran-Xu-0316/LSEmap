"""CON photo-supported entrance apertures and limited lower-frontage glazing.
Constant authoring configuration; preserve original scene objects, save only component.
"""

from pathlib import Path
import array, hashlib, json, math, sys
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/con_glazing151"
BASE = ROOT / "result/blender/LSE_campus_detailed_v150.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
PREFIX = "CON_NEXT_GLAZING151_"
COMPONENT = OUT / "connaught-glazing-component.blend"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from facade_geometry import Geometry, materials


def fingerprint(obj):
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == "MESH":
        for coll, field, kind, width in [
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
            (obj.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(coll) * width)
            coll.foreach_get(field, values)
            h.update(values.tobytes())
        for uv in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(uv.data) * 2)
            uv.data.foreach_get("uv", values)
            h.update(values.tobytes())
    h.update(
        str(
            [m.name if m else None for m in getattr(obj.data, "materials", [])]
        ).encode()
    )
    return h.hexdigest()


def surface_fingerprint(obj):
    """Check original pane positions, topology and UVs independently of new slots."""
    h = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    for coll, field, kind, width in [
        (obj.data.vertices, "co", "f", 3),
        (obj.data.loops, "vertex_index", "i", 1),
    ]:
        values = array.array(kind, [0]) * (len(coll) * width)
        coll.foreach_get(field, values)
        h.update(values.tobytes())
    for uv in obj.data.uv_layers:
        values = array.array("f", [0]) * (len(uv.data) * 2)
        uv.data.foreach_get("uv", values)
        h.update(values.tobytes())
    return h.hexdigest()


def parts(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    seen = set()
    result = []
    for seed in bm.verts:
        if seed in seen:
            continue
        group = []
        stack = [seed]
        seen.add(seed)
        while stack:
            vertex = stack.pop()
            group.append(vertex.index)
            for edge in vertex.link_edges:
                other = edge.other_vert(vertex)
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        result.append(group)
    bm.free()
    return result


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
        for name in prior["archivedObjects"]:
            state = prior["originalVisibility"][name]
            obj = bpy.data.objects[name]
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
reg = inspection["registration"]
origin = Vector(reg["origin"])
u = Vector(reg["right"])
normal = Vector(reg["outward"])
collection = bpy.data.collections["CON_EXTERIOR"]
owned = []
changes = []


def local(p):
    return Vector(((p - origin).dot(u), (p - origin).dot(normal), p.z))


def world(x, d, z):
    return origin + u * x + normal * d + Vector((0, 0, z))


def duplicate(source, label):
    obj = bpy.data.objects[source].copy()
    obj.data = obj.data.copy()
    obj.name = PREFIX + label
    obj.data.name = obj.name
    collection.objects.link(obj)
    owned.append(obj)
    changes.append(
        {
            "source": source,
            "owned": obj.name,
            "action": "Owned replacement, archive original display only",
        }
    )
    return obj


# Only the independent invented backing panel is removed. Side linings and ceiling remain.
wall = duplicate("CON_D5_vestibule68_wall", "vestibule_without_false_backing")
components = parts(wall.data)
selected = []
for ids in components:
    ps = [local(wall.matrix_world @ wall.data.vertices[i].co) for i in ids]
    c = sum(ps, Vector()) / len(ps)
    if abs(c.x) < 0.01 and abs(c.y + 3.11) < 0.01 and abs(c.z - 1.49) < 0.01:
        selected.append(ids)
assert len(selected) == 1 and len(selected[0]) == 8
bm = bmesh.new()
bm.from_mesh(wall.data)
bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in selected[0]], context="VERTS")
bm.to_mesh(wall.data)
bm.free()
assert len(parts(wall.data)) == len(components) - 1

# The old frame was a solid bronze box immediately behind genuine fanlight glass.
# Subtract precisely its glazing aperture, retaining bronze perimeter and material.
frame = duplicate("CON_D4_bronze_fanlight", "opened_bronze_fanlight")
bm = bmesh.new()
bm.from_mesh(frame.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(frame.data)
bm.free()
materials.clear()
materials["cut"] = frame.data.materials[0]
g = Geometry("CON", "glazing151_aperture_cutter", "cut")
g.box(world(0, -0.26, 3.39), (1.79, 0.8, 0.47), math.atan2(u.y, u.x))
cutter = g.finish()
for m in list(cutter.modifiers):
    cutter.modifiers.remove(m)
bm = bmesh.new()
bm.from_mesh(cutter.data)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
bm.to_mesh(cutter.data)
bm.free()
bpy.context.view_layer.objects.active = frame
modifier = frame.modifiers.new("True fanlight opening", "BOOLEAN")
modifier.operation = "DIFFERENCE"
modifier.solver = "EXACT"
modifier.object = cutter
bpy.ops.object.modifier_apply(modifier=modifier.name)
bpy.data.objects.remove(cutter, do_unlink=True)

# Original colours, geometric panes and UVs are retained. Only photographed bays change slots.
glass_targets = {
    "CON_NEXT_PORTAL_WINDOW_recessed_glass": {1, 2, 5, 6, 7},
    "CON_D4_fanlight_glass": {0},
    "CON_D5_vestibule68_glass": {0, 1},
}
new_labels = {
    "CON_NEXT_PORTAL_WINDOW_recessed_glass": "registered_lower_frontage_glass",
    "CON_D4_fanlight_glass": "fanlight_glass",
    "CON_D5_vestibule68_glass": "inner_door_glass",
}
parameters = []
for source, indices in glass_targets.items():
    obj = duplicate(source, new_labels[source])
    source_material = obj.data.materials[0]
    material = source_material.copy()
    material.name = PREFIX + new_labels[source] + "_material"
    bs = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    before = {
        "color": list(bs.inputs["Base Color"].default_value),
        "transmission": bs.inputs["Transmission Weight"].default_value,
        "alpha": bs.inputs["Alpha"].default_value,
        "webOpacity": source_material.get("webOpacity"),
    }
    bs.inputs["Transmission Weight"].default_value = 0.22
    bs.inputs["Alpha"].default_value = 0.82
    material["webOpacity"] = 0.82
    material.diffuse_color = (*before["color"][:3], 0.82)
    obj.data.materials.append(material)
    slot = len(obj.data.materials) - 1
    ids = {
        v
        for part, group in enumerate(parts(obj.data))
        if part in indices
        for v in group
    }
    for face in obj.data.polygons:
        if all(v in ids for v in face.vertices):
            face.material_index = slot
    parameters.append(
        {
            "source": source,
            "owned": obj.name,
            "parts": sorted(indices),
            "before": before,
            "after": {
                "color": list(bs.inputs["Base Color"].default_value),
                "transmission": 0.22,
                "alpha": 0.82,
                "webOpacity": 0.82,
            },
            "colourAndUVPreserved": True,
            "roughnessAndMetallicPreserved": True,
        }
    )
archives = [c["source"] for c in changes]
lookup = {c["source"]: c["owned"] for c in changes}
for name in archives:
    obj = bpy.data.objects[name]
    obj.hide_render = True
    obj.hide_set(True)


def probes():
    scene_names = {o.name for s in bpy.data.scenes for o in s.objects}
    objects = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name not in scene_names:
            continue
        ps = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
        if all(
            min(p[i] for p in ps) <= origin[i] + 35
            and max(p[i] for p in ps) >= origin[i] - 35
            for i in range(2)
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
    back, bnames = tree({lookup[s] for s in glass_targets})

    def cast(bvh, names, p, d, length):
        hit = bvh.ray_cast(p, d, length)
        return {
            "object": names[hit[2]] if hit[2] is not None else None,
            "distance": hit[3],
            "hit": list(hit[0]) if hit[0] is not None else None,
        }

    result = []
    for panel in inspection["panels"]:
        source = panel["object"]
        if source not in glass_targets or panel["part"] not in glass_targets[source]:
            continue
        n = Vector(panel["normal"])
        rows = []
        for p in panel["samples"]:
            point = Vector(p)
            first = cast(full, names, point + n * 0.4, -n, 0.8)
            behind = cast(back, bnames, point - n * 0.02, -n, 1.98)
            assert first["object"] == lookup[source], first
            assert behind["object"] is None, behind
            rows.append({"point": p, "first": first, "behind02To2m": behind})
        result.append(
            {
                "source": source,
                "owned": lookup[source],
                "part": panel["part"],
                "samples": rows,
            }
        )
    assert len(result) == 8
    return result


def protected():
    for source in glass_targets:
        assert surface_fingerprint(bpy.data.objects[source]) == surface_fingerprint(
            bpy.data.objects[lookup[source]]
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
        if name not in archives
    )


before_save = probes()
protected()
bpy.data.libraries.write(str(COMPONENT), set(owned), fake_user=True, compress=True)
reference = (
    ROOT / "data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg"
)
audit = {
    "baseline": str(BASE),
    "baselineSha256": BASE_SHA,
    "originalObjectCount": len(originals),
    "ownedObjects": [o.name for o in owned],
    "archivedObjects": archives,
    "changes": changes,
    "destinationCollection": "CON_EXTERIOR",
    "retainNewMaterials": True,
    "originalFingerprints": originals,
    "originalVisibility": visibility,
    "materials": parameters,
    "scope": "Remove one invented inner-door backing and make the solid fanlight frame a true ring; finite transparency only in five photographed lower-frontage parts, fanlight and two inner doors",
    "reference": {
        "path": str(reference),
        "sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        "captureDate": "unknown",
        "dimensions": [300, 400],
        "supports": "Photo-visible deep glazed vestibule, transparent crest-bearing fanlight, closest two street windows and three first-upper windows. Far columns/high levels excluded.",
    },
    "removedBacking": {
        "source": "CON_D5_vestibule68_wall",
        "partVertexCount": 8,
        "localCenter": [0, -3.11, 1.49],
        "dimensions": [2.05, 0.09, 2.8],
        "nearFieldBeforeDistance": 0.2875,
        "sourceRationale": "refine_connaught_vestibule.py intentionally added a shallow interior backing, not a surveyed interior wall",
    },
    "fanlightAperture": {
        "width": 1.79,
        "bottom": 3.155,
        "top": 3.625,
        "cutDepthRange": [-0.66, 0.14],
        "supports": "Existing actual glazing perimeter, not enlarged opening",
    },
    "limitations": [
        "Undated300x400px photo does not certify upper elevations, roof or rear; inherited massing unchanged.",
        "Dimensions/depth of vestibule estimated previously; removal does not invent a reconstructed room.",
        "Neutral finite transparency0.82/T0.22 is a visual estimate; original RGB/roughness/metallic/UV remain.",
        "Historical CON_EXTERIOR_Glazing_bays shell overlaps other buildings; not modified or newly certified.",
        "Full room boundaries beyond2m remain unverified.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2))
# Reload source and independent component without mutating audit object-name lists.
open_source()
with bpy.data.libraries.load(str(COMPONENT), link=False) as (src, dst):
    dst.objects = list(audit["ownedObjects"])
collection = bpy.data.collections["CON_EXTERIOR"]
for obj in dst.objects:
    collection.objects.link(obj)
for name in archives:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
protected()
reloaded = probes()
assert reloaded == before_save
for record in parameters:
    obj = bpy.data.objects[record["owned"]]
    mat = obj.data.materials[-1]
    assert mat.get("webOpacity") == 0.82
scene = bpy.context.scene
members = {o.name for o in collection.all_objects}
for obj in scene.objects:
    if obj.type == "MESH" and obj.name not in members:
        obj.hide_render = True
focus = world(0, 0, 12.5)
camdata = bpy.data.cameras.new(PREFIX + "review")
cam = bpy.data.objects.new(camdata.name, camdata)
scene.collection.objects.link(cam)
cam.location = focus + normal * 65 - u * 5 + Vector((0, 0, 3))
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
camdata.type = "ORTHO"
camdata.ortho_scale = 33.5
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 8
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "CON-reloaded-frontage.png")
bpy.ops.render.render(write_still=True)
proof = {
    "componentSha256": hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),
    "savedComponentReopened": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "originalObjectCount": len(originals),
    "baselineUnchanged": hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA,
    "glassPrincipalFaces": 8,
    "glassFirstHitPassCount": 32,
    "behind02To2mClearCount": 32,
    "reopenedProbes": reloaded,
    "explicitWebOpacity": 0.82,
    "nativePreview": "CON-reloaded-frontage.png",
    "previewViewed": False,
    "camera": {
        "position": list(cam.location),
        "target": list(focus),
        "orthoScale": 33.5,
    },
    "newWholeModelSaved": False,
}
assert proof["baselineUnchanged"]
(OUT / "verification.json").write_text(json.dumps(proof, indent=2))
print("CON_GLAZING151_DONE", proof["componentSha256"], flush=True)
bpy.ops.wm.quit_blender()
