"""Replace Lincoln Chambers' opaque shop risers with observed basement lights.
Run in Blender's Text Editor. Produces a review candidate, not a release.
"""
from pathlib import Path
import array
import hashlib
import json
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'web/tools'))
from facade_geometry import Facade, materials

OUT = ROOT / 'result/blender/stage43'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v42.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        digest.update(array.array('f', [c for vertex in obj.data.vertices for c in vertex.co]).tobytes())
        digest.update(array.array('i', [loop.vertex_index for loop in obj.data.loops]).tobytes())
    return digest.hexdigest()

for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

riser = bpy.data.objects['LCH_D5_V42_shop_riser_frame']
protected = {obj.name: fingerprint(obj) for obj in bpy.data.objects if obj != riser}
bpy.data.objects.remove(riser, do_unlink=True)
profile = next(item for item in json.loads((ROOT / 'result/blender/stage05/infill-geometry.json').read_text()) if item['code'] == 'LCH')
ring = profile['building']['rings'][0]
p, q = Vector(ring[0]), Vector(ring[2])
u = (q-p).normalized()
groups = {}
front = Facade(profile, {'p': list(p), 'q': list(q), 'length': (q-p).length, 'outward': [-u.y, u.x]}, groups)
materials.clear()
for key in ['frame', 'glass']:
    materials[key] = bpy.data.materials['LCH_V42_' + key]
metal = bpy.data.materials.new('LCH_V43_basement_metal')
metal.use_nodes = True
metal.diffuse_color = (.04, .045, .045, 1)
metal.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = metal.diffuse_color
metal.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .65
materials['metal'] = metal
# Three dark lower lights on each side, pale splayed surround and metal grids.
# Widths follow the existing shopfront; recess and slope remain estimates.
for side in [-1, 1]:
    left, right = (.18, front.length/2-2.10) if side < 0 else (front.length/2+2.10, front.length-.18)
    centre = (left+right)/2
    width = right-left-.35
    bottom, top = .38, 1.02
    for index in range(3):
        x0 = centre-width/2+width*index/3
        x1 = x0+width/3
        opening_left, opening_right = x0+.075, x1-.075
        front.box('V43_basement_glass', 'glass', (x0+x1)/2, .70, x1-x0-.15, .49, .035, -.025)
        # Recessed dark glazing, framed by sloping pale jambs.
        surround = front.group('V43_basement_splayed_surround', 'frame')
        for edge, inner in [(x0, opening_left), (x1, opening_right)]:
            surround.add([front.point(edge,bottom,.12), front.point(inner,bottom+.07,-.005), front.point(inner,top-.07,-.005), front.point(edge,top,.04)], [(0,1,2,3)])
        for z in [bottom+.035, top-.035]:
            front.box('V43_basement_rails', 'frame', (x0+x1)/2, z, x1-x0, .07, .18, .045)
        for fraction in [0, .5, 1]:
            front.box('V43_basement_grid', 'metal', opening_left+(opening_right-opening_left)*fraction, .70, .025, .49, .04, .005)
        for z in [.47, .70, .93]:
            front.box('V43_basement_grid', 'metal', (x0+x1)/2, z, opening_right-opening_left, .028, .04, .005)
for geometry in groups.values():
    geometry.finish()
for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in protected.items())
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'lincoln-basement-candidate.blend'))
# Preview only: export procedural brick as its base colour. Native nodes stay saved.
brick = bpy.data.materials['LCH_V42_brick']
base = brick.node_tree.nodes['Principled BSDF'].inputs['Base Color']
for link in list(base.links):
    brick.node_tree.links.remove(link)
base.default_value = brick.diffuse_color
for obj in bpy.data.objects:
    obj.select_set(False)
for obj in bpy.data.collections['LCH_EXTERIOR'].all_objects:
    obj.hide_set(False)
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT / 'lch-preview.glb'), export_format='GLB', use_selection=True, use_active_scene=True, export_cameras=False, export_lights=False)
(OUT / 'basement-audit.json').write_text(json.dumps({
    'baseline': 42, 'protectedObjectsUnchanged': len(protected),
    'removed': 'LCH_D5_V42_shop_riser_frame', 'lowerLights': 6,
    'reference': 'https://www.flickr.com/photos/12608538@N03/52301305449',
    'photoDate': '2022-08-21',
    'limitations': ['Recess depth and dimensions estimated', 'No interior inferred', 'Left side partly occluded in photo'],
    'status': 'Candidate pending visual review'
}, indent=2)+'\n')
