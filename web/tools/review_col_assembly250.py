"""Compare private COL geometry in the current native without saving that native."""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "result/blender/col-assembly250"
sys.path.insert(0, str(ROOT / "web/tools"))
from integrate_exterior_round194 import update_scene

BASE = ROOT / "result/blender/LSE_campus_detailed_v250.blend"
accepted = json.loads(
    (ROOT / "result/blender/stage250/building-refinement.json").read_text()
)
BASE_SHA = accepted["sourceModelSha256"]
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
plan = json.loads(
    (ROOT / "result/blender/col-registration249/registration-plan.json").read_text()
)
audit = json.loads((ROOT / "result/blender/col-registration249/audit.json").read_text())
source = json.loads((ROOT / plan["sourcePlan"]).read_text())
bpy.ops.wm.open_mainfile(filepath=str(BASE))
update_scene()
original_scene = bpy.context.scene
# Rebase only after the current saved campus proves that every original COL
# exterior object, material graph and room membership is still compatible.
import importlib.util

spec = importlib.util.spec_from_file_location(
    "source_protection", ROOT / "web/tests/verify_campus241.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
current = helper.capture_source()
protected_path = ROOT / "result/blender/col-registration249/protected-source-state.json"
protected = json.loads(protected_path.read_text())
source_names = [obj.name for obj in bpy.data.collections["COL_EXTERIOR"].all_objects]
for name in source_names:
    assert current["objects"][name] == protected["objects"][name], name
for name, record in protected["materials"].items():
    assert current["materials"][name] == record, name
assert current["rooms"] == protected["rooms"]
assert current["campusRooms"] == protected["campusRooms"]
rebased = dict(audit)
rebased["baseline"] = str(BASE.relative_to(ROOT))
rebased["baselineSha256"] = BASE_SHA
rebased["originalObjectsPreserved"] = len(current["objects"])
rebased["status"] = "private_candidate_compatible_with250_roof_not_accepted"
rebased["compatibilityProof"] = (
    "result/blender/col-assembly250/current-source-compatibility.json"
)
(OUT / "candidate-audit.json").write_text(json.dumps(rebased, indent=2) + "\n")
compatibility = {
    "baseline": str(BASE.relative_to(ROOT)),
    "baselineSha256": BASE_SHA,
    "sourceProtectionSha256": hashlib.sha256(protected_path.read_bytes()).hexdigest(),
    "colExteriorObjectsVerified": len(source_names),
    "originalMaterialGraphsVerified": len(protected["materials"]),
    "protectedRooms": len(protected["rooms"]),
    "privateComponentSha256": audit["componentSha256"],
    "wholeBuildingRoofAccepted": False,
    "previous248NativeRequiredForCurrentCandidate": False,
    "scope": "Current source compatibility only. A bounded facade is not whole-building roof acceptance.",
}
(OUT / "current-source-compatibility.json").write_text(
    json.dumps(compatibility, indent=2) + "\n"
)
with bpy.data.libraries.load(str(ROOT / audit["component"]), link=False) as (
    _library,
    loaded,
):
    loaded.collections = ["COL249_REGISTERED_CANDIDATE"]
collection = loaded.collections[0]
original_scene.collection.children.link(collection)
for name in audit["archivedObjects"]:
    bpy.data.objects[name].hide_render = True
update_scene()
objects = [
    o
    for o in list(bpy.data.collections["COL_EXTERIOR"].all_objects)
    + list(collection.all_objects)
    if o.type == "MESH" and not o.hide_render
]
rows = []
for obj in objects:
    mats = []
    for mat in obj.data.materials:
        mats.append({"name": mat.name, "colour": list(mat.diffuse_color)})
    rows.append(
        {
            "name": obj.name,
            "cameraVisible": obj.visible_camera,
            "visibleInLayer": obj.visible_get(),
            "viewportHidden": obj.hide_viewport,
            "material": mats,
        }
    )
# Raycast from the actual camera side, beyond every old skin. The earlier
# one-metre probes proved the new openings but could miss a more distant skin.
trees = []
for obj in objects:
    trees.append(
        (
            obj,
            BVHTree.FromPolygons(
                [obj.matrix_world @ v.co for v in obj.data.vertices],
                [tuple(p.vertices) for p in obj.data.polygons],
            ),
        )
    )
north = Vector((*plan["frontageNorthToSouth"][0], 0))
axis = Vector((*plan["axis"], 0))
inside = Vector((*plan["inwardNormal"], 0))
ox, oy = source["sourceOrigin"]
scale = source["metresPerPoint"]
ray_rows = []
for opening in source["openings"]:
    x0, y0, x1, y1 = opening["sourceBounds"]
    xy = north + axis * ((((x0 + x1) / 2) - ox) * scale * plan["horizontalFit"])
    z = (oy - (y0 + y1) / 2) * scale
    origin = Vector((xy.x, xy.y, z)) - inside * 50
    hits = []
    for obj, tree in trees:
        point, normal, face, distance = tree.ray_cast(origin, inside, 80)
        if point is not None:
            material = obj.data.materials[obj.data.polygons[face].material_index]
            hits.append(
                {
                    "name": obj.name,
                    "distance": distance,
                    "material": material.name,
                    "point": list(point),
                }
            )
    ray_rows.append(
        {
            "opening": opening["id"],
            "firstHits": sorted(hits, key=lambda row: row["distance"])[:6],
        }
    )
world = bpy.data.worlds.new("COL250 review daylight")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.65
scene = bpy.data.scenes.new("COL250 temporary comparison")
scene.world = world
for obj in objects:
    scene.collection.objects.link(obj)
bpy.context.window.scene = scene
light = bpy.data.lights.new("COL250 review key", "AREA")
light.energy = 1800
light.size = 12
lamp = bpy.data.objects.new(light.name, light)
scene.collection.objects.link(lamp)
lamp.location = (-25, -118, 40)
target = north + axis * (plan["nativeLengthM"] / 2) + Vector((0, 0, 17))
lamp.rotation_euler = (target - lamp.location).to_track_quat("-Z", "Y").to_euler()
data = bpy.data.cameras.new("COL250 review camera")
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.type = "ORTHO"
data.ortho_scale = 40
scene.render.engine = "CYCLES"
scene.cycles.samples = 12
scene.cycles.use_denoising = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1100
scene.render.resolution_percentage = 100
for label, offset in [
    ("front", -inside * 70),
    ("oblique", -inside * 65 + axis * 26 + Vector((0, 0, 12))),
]:
    camera.location = target + offset
    camera.rotation_euler = (
        (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    )
    scene.render.filepath = str(OUT / f"current-assembly-{label}.png")
    bpy.ops.render.render(write_still=True)
(OUT / "current-assembly-visibility.json").write_text(
    json.dumps(
        {
            "baselineSha256": BASE_SHA,
            "nativeMaterialOverrides": [
                {
                    "name": layer.name,
                    "material": layer.material_override.name
                    if layer.material_override
                    else None,
                }
                for layer in original_scene.view_layers
            ],
            "candidateCollectionHidden": collection.hide_render,
            "objects": rows,
            "rays": ray_rows,
        },
        indent=2,
    )
    + "\n"
)
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
print("COL250_ASSEMBLY_INSPECTED", len(objects), len(ray_rows), flush=True)
