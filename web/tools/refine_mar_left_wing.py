"""Read-only native registration inventory; no model mutation or save."""

from pathlib import Path
import array
import bpy, json, math, hashlib
from mathutils import Vector

root = Path(__file__).resolve().parents[2]
out = root / "result/blender/mar_left_wing_next"
base = root / "result/blender/LSE_campus_detailed_v143.blend"
if not base.exists():
    base = max(
        (root / "result/blender").glob("LSE_campus_detailed_v[0-9]*.blend"),
        key=lambda p: int(p.stem.rsplit("v", 1)[1]),
    )
bpy.ops.wm.open_mainfile(filepath=str(base))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]


def fingerprint(obj):
    h = hashlib.sha256(str([list(r) for r in obj.matrix_world]).encode())
    if obj.type == "MESH":
        for data, field, kind, count in [
            (obj.data.vertices, "co", "f", 3),
            (obj.data.loops, "vertex_index", "i", 1),
            (obj.data.polygons, "material_index", "i", 1),
        ]:
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            h.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            h.update(values.tobytes())
    h.update(
        str(
            [m.name if m else None for m in getattr(obj.data, "materials", [])]
        ).encode()
    )
    return h.hexdigest()


originals = {o.name: fingerprint(o) for o in bpy.data.objects}
visibility = {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
origin = Vector((-8.696325894899289, 49.33154396120258, 0))
angle = math.radians(22)
u = Vector((math.cos(angle), math.sin(angle), 0))
n = Vector((-u.y, u.x, 0))


def local(p):
    return [(p - origin).dot(u), (p - origin).dot(n), p.z]


records = []
for obj in bpy.data.objects:
    if (
        obj.type != "MESH"
        or not obj.name.startswith("MAR")
        or not any(k in obj.name for k in ["8543", "8545", "north115", "middle_wall"])
    ):
        continue
    points = [local(obj.matrix_world @ v.co) for v in obj.data.vertices]
    plan = {tuple(round(v, 3) for v in point[:2]) for point in points}
    records.append(
        {
            "name": obj.name,
            "visible": not (obj.hide_render or obj.hide_get()),
            "bounds": [
                [min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)
            ],
            "plan": sorted(plan),
            "vertices": len(points),
            "faces": len(obj.data.polygons),
            "materials": [m.name if m else None for m in obj.data.materials],
        }
    )
(out / "native-registration-inventory.json").write_text(
    json.dumps(
        {
            "baselineSha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            "objectCount": len(bpy.data.objects),
            "localOrigin": list(origin),
            "localRotationDegrees": 22,
            "records": records,
        },
        indent=2,
    )
    + "\n"
)
for r in records:
    if "8543" in r["name"] or "8545" in r["name"]:
        print(r["name"], r["visible"], r["bounds"], r["plan"][:8])
assert originals == {o.name: fingerprint(o) for o in bpy.data.objects}
assert visibility == {
    o.name: [o.hide_render, o.hide_viewport, o.hide_get()] for o in bpy.data.objects
}
audit = json.loads((out / "audit.json").read_text())
audit["originalFingerprints"] = originals
audit["originalVisibility"] = visibility
(out / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
(out / "verification.json").write_text(
    json.dumps(
        {
            "baselineSha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            "originalObjectCount": len(originals),
            "allOriginalFingerprintsPreserved": True,
            "originalGeometryUVMaterialSlotsPreserved": True,
            "allVisibilityPreserved": True,
            "fullModelSaved": False,
            "componentCreated": False,
            "savedComponentReopened": False,
            "nativeRenderPerformed": False,
            "reason": "No uniquely registered correction; no component or render claimed.",
            "readOnlyBlenderExited": True,
        },
        indent=2,
    )
    + "\n"
)
bpy.ops.wm.quit_blender()
