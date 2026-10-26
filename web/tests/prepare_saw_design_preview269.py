"""Create a private SAW design-coordinate proof scene for the parent to inspect.

This is a registration/control-surface candidate, not a repaired exterior. It
clones the whole visible public structure through one common map and overlays
source-derived wall-line controls. It never clips slabs, changes original
objects/materials/visibility, or saves over native263.
"""
import array
import hashlib
import json
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "result/blender/saw269"
BASE = ROOT / "result/blender/LSE_campus_detailed_v263.blend"
EXPECTED = "f55f5975ea5e4d755f0c883bc64965b928a3d03add666c598a9b7e987bb70c2d"
OUTPUT = FOLDER / "design-coordinate-review.blend"


def file_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def signature(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == "MESH":
        for seq, field, kind, width in ((obj.data.vertices, "co", "f", 3),
                (obj.data.loops, "vertex_index", "i", 1), (obj.data.polygons, "material_index", "i", 1)):
            values = array.array(kind, [0]) * (len(seq) * width)
            seq.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array("f", [0]) * (len(layer.data) * 2)
            layer.data.foreach_get("uv", values)
            digest.update(values.tobytes())
        digest.update(str([material.name if material else None for material in obj.data.materials]).encode())
    return digest.hexdigest()


assert not OUTPUT.exists(), "Preserve the existing private candidate until reviewed"
assert file_sha(BASE) == EXPECTED
candidate = json.loads((FOLDER / "design-registration-candidate.json").read_text())
inspection = json.loads((FOLDER / "native-inspection.json").read_text())
assert candidate["baselineSha256"] == inspection["baselineSha256"] == EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes["00_CAMPUS_COMPLETE"]
for layer in bpy.context.scene.view_layers:
    layer.update()
source_objects = list(bpy.data.collections["SAW_PUBLIC_INTERIOR_study"].all_objects)
source_objects += list(bpy.data.collections["SAW_EXTERIOR"].all_objects)
source_objects = list(dict.fromkeys(source_objects))
before = {obj.name: {"signature": signature(obj), "visibility": [obj.hide_render, obj.hide_viewport, obj.hide_get()]}
          for obj in source_objects}

scene = bpy.data.scenes.new("SAW269_DESIGN_COORDINATE_REVIEW")
collection = bpy.data.collections.new("SAW269_private_coordinate_candidate")
scene.collection.children.link(collection)
scene["status"] = "Coordinate proof only; not an accepted replacement shell"
scene["sourceModelSha256"] = EXPECTED
scene["noSlabClipping"] = True

transform = candidate["transforms"]["legacyNativeToMetricDesign"]
a, t = transform["matrix"], transform["offset"]
world_to_design = Matrix(((a[0][0], a[0][1], 0, t[0]),
                          (a[1][0], a[1][1], 0, t[1]),
                          (0, 0, 1, 0), (0, 0, 0, 1)))
visible = set(inspection["visibleObjects"])
public = {obj.name for obj in bpy.data.collections["SAW_PUBLIC_INTERIOR_study"].all_objects}
cloned = []
for obj in source_objects:
    if obj.type != "MESH" or obj.name not in visible or obj.name not in public:
        continue
    clone = obj.copy()
    clone.data = obj.data.copy()
    clone.name = "SAW269_PUBLIC_" + obj.name
    clone.parent = None
    clone.matrix_world = world_to_design @ obj.matrix_world
    collection.objects.link(clone)
    clone["retainedSource"] = obj.name
    clone["sourceRelationship"] = "Same invertible XY map for the entire floor/stair/lift assembly; Z unchanged"
    cloned.append(clone.name)

# These paths are measured wall-line controls. They do not pretend that a terrace
# edge is masonry, or that a missing glazing/brick boundary has been recovered.
controls = []
for level in candidate["levelWallLineControls"]:
    curve = bpy.data.curves.new("SAW269_source_wall_line_" + str(level["datum"]), "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    spline = curve.splines.new("POLY")
    points = level["designMetresContour"]
    spline.points.add(len(points) - 1)
    for point, xy in zip(spline.points, points):
        point.co = (xy[0], xy[1], level["datum"], 1)
    obj = bpy.data.objects.new(curve.name, curve)
    collection.objects.link(obj)
    obj["evidence"] = "Historical guide grey exterior wall-line contour, registered to dimensioned architect plan"
    obj["status"] = "Control line, not replacement wall material or accepted shell"
    controls.append(obj.name)

# Keep old front planes visibly separate as wire references, so the conflict is
# shown rather than hidden by the newly aligned source wall lines.
old_plane_references = []
for name in ("SAW_NEXT_EXTERIOR155_north_fold_pierced_wall", "SAW_SAW_central_return_pierced_wall",
             "SAW_SAW_south_fold_pierced_wall"):
    source = bpy.data.objects.get(name)
    if source is None:
        continue
    clone = source.copy()
    clone.data = source.data.copy()
    clone.name = "SAW269_OLD_PLANE_REFERENCE_" + name
    clone.parent = None
    clone.matrix_world = world_to_design @ source.matrix_world
    clone.display_type = "WIRE"
    clone.hide_render = True
    collection.objects.link(clone)
    clone["status"] = "Rejected as an automatic clipping authority; reference only"
    old_plane_references.append(clone.name)

for layer in scene.view_layers:
    layer.update()
for obj in source_objects:
    assert signature(obj) == before[obj.name]["signature"], obj.name
    assert [obj.hide_render, obj.hide_viewport, obj.hide_get()] == before[obj.name]["visibility"], obj.name
bpy.data.libraries.write(str(OUTPUT), {scene}, fake_user=True)
assert file_sha(BASE) == EXPECTED
report = {"status": "private-coordinate-candidate-not-exterior-repair", "baselineSha256": EXPECTED,
    "candidatePath": str(OUTPUT.relative_to(ROOT)), "candidateSha256": file_sha(OUTPUT),
    "publicClones": cloned, "sourceWallControls": controls, "oldPlaneReferences": old_plane_references,
    "originalGeometryUvMaterialsTransformsAndVisibilityUnchanged": True,
    "nativeFileUnchanged": True, "wholeAssemblyTransform": transform,
    "remainingWork": candidate["remainingConstraints"]}
(FOLDER / "design-preview-build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print("SAW269_PRIVATE_COORDINATE_PREVIEW", len(cloned), len(controls), flush=True)
