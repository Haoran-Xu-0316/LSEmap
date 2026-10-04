"""Bounded Columbia whole-envelope audit without speculative facade changes.
Run in Blender Text Editor. Only local evidence and a private native preview.
"""

from pathlib import Path
import array, hashlib, json, math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v144.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
bpy.context.window.scene = scene
sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith("v144"):
    assert sha == "a8bbab18e6b2a624f61ce4d9460e2577809f9aaf6d092d1804f34fa34a4e692e"


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
if BASE.stem.endswith("v144"):
    assert len(original) == 5748
col = bpy.data.collections["COL_EXTERIOR"]
site = json.loads((ROOT / "result/blender/site_geometry.json").read_text())
building = next(b for b in site["buildings"] if b["code"] == "COL")
ring = building["rings"][0]
signed = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))
frames = []
for i in [10, 11, 12]:
    origin = Vector((*ring[i], 0))
    end = Vector((*ring[(i + 1) % len(ring)], 0))
    u = (end - origin).normalized()
    n = Vector((u.y, -u.x, 0)) * (1 if signed > 0 else -1)
    frames.append((i, origin, u, n, (end - origin).length))
vertices = []
faces = []
owners = []
for o in col.all_objects:
    if o.type != "MESH" or o.hide_render:
        continue
    offset = len(vertices)
    vertices.extend(o.matrix_world @ v.co for v in o.data.vertices)
    faces.extend(tuple(offset + i for i in f.vertices) for f in o.data.polygons)
    owners.extend([o.name] * len(o.data.polygons))
tree = BVHTree.FromPolygons(vertices, faces)
probes = []
pane_rows = {}
materials = {}
for name in ["COL_V99_retained_D4_recessed_glass", "COL_V99_corner_D4_recessed_glass"]:
    o = bpy.data.objects[name]
    assert not o.hide_render
    adj = {i: set() for i in range(len(o.data.vertices))}
    for e in o.data.edges:
        a, b = e.vertices
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    for seed in adj:
        if seed in seen:
            continue
        pending = [seed]
        seen.add(seed)
        part = []
        while pending:
            i = pending.pop()
            part.append(i)
            for neighbour in adj[i]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    pending.append(neighbour)
        points = [o.matrix_world @ o.data.vertices[i].co for i in part]
        centre = sum(points, Vector()) / len(points)
        index, origin, u, n, length = min(
            frames, key=lambda f: abs((centre - f[1]).dot(f[3]) + 0.4)
        )
        width = max(p.dot(u) for p in points) - min(p.dot(u) for p in points)
        samples = []
        for fraction in [0.28, -0.28, 0]:
            sample = centre + u * width * fraction
            hit = tree.ray_cast(sample + n * 1.2, -n, 1.4)
            actual = owners[hit[2]] if hit[2] is not None else None
            samples.append({"fraction": fraction, "firstSurface": actual})
            if actual == name:
                break
        probes.append(
            {
                "glassObject": name,
                "facadeIndex": index,
                "centre": list(centre),
                "sample": list(sample),
                "zBounds": [min(p.z for p in points), max(p.z for p in points)],
                "samples": samples,
                "firstSurface": actual,
                "glassClear": actual == name,
            }
        )
        key = str(round(centre.z, 3))
        pane_rows[key] = pane_rows.get(key, 0) + 1
    materials[name] = []
    for m in o.data.materials:
        shader = m.node_tree.nodes.get("Principled BSDF")
        materials[name].append(
            {
                "name": m.name,
                "baseColor": list(shader.inputs["Base Color"].default_value),
                "roughness": float(shader.inputs["Roughness"].default_value),
                "transmission": float(
                    shader.inputs["Transmission Weight"].default_value
                ),
                "alpha": float(shader.inputs["Alpha"].default_value),
            }
        )
assert all(fingerprint(bpy.data.objects[n]) == v for n, v in original.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
)
origin = Vector((16.679906845092773, -127.4544677734375, 0))
u = Vector((-0.999708354473114, 0.024150928482413292, 0))
n = Vector((-0.024150928482413292, -0.999708354473114, 0))
focus = origin + u * 3 + Vector((0, 0, 14))
camera_position = focus + n * 48 - u * 22 + Vector((0, 0, 15))
refs = []
for name, purpose in [
    (
        "small_round5_COL_handbook-000.png",
        "Clear main portal and two lower street levels; left half obscured by tree.",
    ),
    (
        "exteriors_lse_estate_004.jpg",
        "300x376 oblique corner and street facade; roof cropped; insufficient detail to establish upper exact pane count.",
    ),
]:
    p = ROOT / "data/建筑图片/COL_Columbia House/01_建筑实拍" / name
    refs.append(
        {
            "file": str(p.relative_to(ROOT)),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "purpose": purpose,
            "captureDate": "unknown",
            "url": (
                "https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf"
                if "handbook" in name
                else "https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate"
            ),
        }
    )
audit = {
    "baseline": str(BASE),
    "baselineSha256": sha,
    "originalObjectCount": len(original),
    "originalFingerprints": original,
    "originalVisibility": visibility,
    "readOnly": True,
    "ownedObjects": [],
    "archivedObjects": [],
    "changes": [],
    "references": refs,
    "boundedIncrementalSourceCheck": {
        "url": "https://www.accessable.co.uk/london-school-of-economics/access-guides/columbia-house",
        "result": "403 Forbidden; not read and no photographs obtained",
        "queryCount": 1,
    },
    "fullEnvelopeAssessment": {
        "currentDefinition": "7 facade rows with boundaries[0,4.8,8.6,12.1,15.6,19.1,22.6,26.1]; estimated inset roof26.4..29m; mapped3street segments with4/1/9bay division.",
        "verifiedScope": "Official photographs support light stone main/lower street fabric, dark window joinery, the main portal and Garrick corner; accepted portal three-column window and full school lettering preserved.",
        "notEstablished": "Full upper-bay count, actual seventh-row/roof registration, mansard shape/height and unseen rear-wall treatment cannot be certified by the cropped300x376photo or ground-level handbook photo.",
        "rusticationReview": "D4 applies repeated horizontal grooves at lower2levels. Handbook shows smoother main portal piers with some thin horizontal joints; corner/ROKA has pronounced horizontal courses. Tree obstruction and lack of rectified facade view do not support removing all main-face grooves or uniformly copying corner courses.",
        "glazingReview": "Actual retained source glass/neutral materials preserved. No measured room/backing geometry supports opacity/transmission changes; genuine windows are not replaced by paint or an invented backing wall.",
    },
    "paneCentreRows": pane_rows,
    "glazingMaterials": materials,
    "firstSurfaceChecks": probes,
    "safeNextRegistration": {
        "needed": "A complete built street elevation including roof/parapet, main portal and identifiableGarrickcorner; sufficient pixels to count upperlights and floorbands.",
        "use": "Register upper bays/cornice/roof to mapped segments10/11/12 before replacing the estimated whole upper envelope. Lower rustication needs a clear unoccluded photo covering each proposed stone pier.",
    },
    "conclusion": "No new evidence-supported major exterior modification identified in this bounded check. Retain existing component rather than claim complete facade accuracy.",
    "componentProduced": False,
    "camera": {
        "position": list(camera_position),
        "target": list(focus),
        "type": "ORTHO",
        "scale": 43,
        "resolution": [1100, 1100],
    },
    "limitations": [
        "Existing heights, widths, roof and unseen walls are estimates, not as-built measurement.",
        "No component/reopen is claimed because no modified component was made.",
        "Unchanged native preview audits envelope only; it does not establish complete interior or measured facade accuracy.",
    ],
}
(OUT / "audit.json").write_text(json.dumps(audit, indent=2))
proof = {
    "baselineSha256": sha,
    "originalObjectCount": len(original),
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "readOnly": True,
    "ownedObjects": [],
    "archivedObjects": [],
    "componentProduced": False,
    "componentSha256": None,
    "savedComponentReopened": False,
    "fullModelSaved": False,
    "firstSurfaceChecks": probes,
    "glazingMaterialsPreserved": True,
    "actualGlassFirstHits": sum(p["glassClear"] for p in probes),
    "paneSamples": len(probes),
}
for o in scene.objects:
    if o.type == "MESH" and o.name not in {x.name for x in col.all_objects}:
        o.hide_render = True
cd = bpy.data.cameras.new("COL_ENVELOPE_readonly_camera")
cam = bpy.data.objects.new(cd.name, cd)
scene.collection.objects.link(cam)
cam.location = camera_position
cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
cd.type = "ORTHO"
cd.ortho_scale = 43
scene.camera = cam
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.world = bpy.data.worlds.new("COL_ENVELOPE_preview_world")
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.65, 0.7, 0.75, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.7
ld = bpy.data.lights.new("COL_ENVELOPE_preview_area", "AREA")
ld.energy = 12000
ld.shape = "DISK"
ld.size = 30
light = bpy.data.objects.new(ld.name, ld)
scene.collection.objects.link(light)
light.location = focus + n * 25 + u * 12 + Vector((0, 0, 35))
light.rotation_euler = (focus - light.location).to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_x = 1100
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
scene.render.filepath = str(OUT / "baseline-street-envelope.png")
bpy.ops.render.render(write_still=True)
proof.update(
    {"nativeRender": str(OUT / "baseline-street-envelope.png"), "renderCount": 1}
)
(OUT / "verification.json").write_text(json.dumps(proof, indent=2))
print(
    "COL_ENVELOPE_READONLY", len(original), len(probes), proof["actualGlassFirstHits"]
)
bpy.ops.wm.quit_blender()
