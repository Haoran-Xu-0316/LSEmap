"""Read-only COW envelope verification; roof depth is not measured as-built.
Run in Blender. No component is produced without a registered roof correction.
"""

from pathlib import Path
import bpy, json, array, hashlib
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/cow_envelope_next"
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / "result/blender/LSE_campus_detailed_v139.blend"
if not BASE.exists():
    BASE = max(
        (ROOT / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
# No owned or archived objects exist in this read-only stage. Latest fallback
# therefore retains the current source exactly without restoring older models.
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
bpy.context.window.scene = scene
bpy.context.view_layer.update()


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


original = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
roof = bpy.data.objects["COW_D5_roof"]
points = [roof.matrix_world @ v.co for v in roof.data.vertices]
trees = []
for o in scene.objects:
    if (
        o.type == "MESH"
        and o.name.startswith("COW")
        and not o.hide_render
        and not o.hide_get()
    ):
        trees.append(
            (
                o.name,
                BVHTree.FromPolygons(
                    [o.matrix_world @ v.co for v in o.data.vertices],
                    [tuple(p.vertices) for p in o.data.polygons],
                ),
            )
        )
probes = []
for side in [3, 4, 5]:
    a, b, upperB, upperA = points[side * 4 : side * 4 + 4]
    normal = (b - a).cross(upperA - a).normalized()
    if normal.z < 0:
        normal = -normal
    for f in [2 / 7, 4 / 7, 6 / 7] if side == 3 else [0.15, 0.5, 0.85]:
        point = (a.lerp(b, f) + upperA.lerp(upperB, f)) * 0.5
        origin = point + normal * 0.15
        hits = []
        for name, tree in trees:
            q, no, i, d = tree.ray_cast(origin, -normal, 1)
            if q is not None:
                hits.append({"object": name, "distance": d})
        hit = min(hits, key=lambda x: x["distance"]) if hits else None
        assert hit and hit["object"] in [
            roof.name,
            "COW_D5_dormer_cheek_lead",
            "COW_D5_dormer_back_slate",
        ], hit
        roofTree = next(t for name, t in trees if name == roof.name)
        q, no, i, d = roofTree.ray_cast(origin, -normal, 1)
        assert q is not None and abs(d - 0.15) < 0.001
        probes.append(
            {
                "ringSide": side,
                "fraction": f,
                "surfacePoint": list(point),
                "outwardNormal": list(normal),
                "firstHit": hit,
            }
        )
assert all(fingerprint(bpy.data.objects[n]) == h for n, h in original.items())
assert all(
    [
        bpy.data.objects[n].hide_render,
        bpy.data.objects[n].hide_viewport,
        bpy.data.objects[n].hide_get(),
    ]
    == v
    for n, v in visibility.items()
)
(OUT / "original-state.json").write_text(
    json.dumps(
        {"originalFingerprints": original, "originalVisibility": visibility}, indent=2
    )
)
proof = {
    "baselineSha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
    "originalObjectCount": len(original),
    "readOnly": True,
    "allOriginalFingerprintsPreserved": True,
    "originalGeometryPreserved": True,
    "unrelatedVisibilityPreserved": True,
    "roofSurfaceDirectProbes": len(probes),
    "roofActualSceneFirstHits": sum(
        x["firstHit"]["object"] == roof.name for x in probes
    ),
    "dormerActualSceneFirstHits": sum(
        x["firstHit"]["object"] != roof.name for x in probes
    ),
    "roofProbes": probes,
    "ownedObjects": [],
    "archivedObjects": [],
    "changes": [],
    "savedComponentReopened": False,
    "rendered": False,
    "renderCount": 0,
    "fullModelSaved": False,
}
(OUT / "verification.json").write_text(json.dumps(proof, indent=2))
print("COW_READONLY_VERIFIED", len(original), len(probes))
bpy.ops.wm.quit_blender()
