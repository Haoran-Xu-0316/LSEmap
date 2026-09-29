"""Export one complete building for geometry review before a campus-wide build.

Run in Blender's Text Editor. Set the three review constants below. Include the
same public interior used by the production exterior so slab/facade collisions
are visible. This preview does not transfer custom browser procedural materials;
colour acceptance still uses the production export and renderer.
"""
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'result/blender/LSE_campus_detailed_v35.blend'
BUILDING = 'LRB'
DESTINATION = ROOT / 'result/blender/stage35/lrb-preview.glb'

bpy.ops.wm.open_mainfile(filepath=str(MODEL))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.ops.object.select_all(action='DESELECT')
objects = list(bpy.data.collections[BUILDING + '_EXTERIOR'].all_objects)
interior = bpy.data.collections.get(BUILDING + '_PUBLIC_INTERIOR_study')
if interior and not interior.get('roomSample'):
    objects += list(interior.all_objects)
for obj in dict.fromkeys(objects):
    obj.hide_set(False)
    obj.select_set(True)
DESTINATION.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=str(DESTINATION), export_format='GLB', use_selection=True,
    export_cameras=False, export_lights=False,
)
