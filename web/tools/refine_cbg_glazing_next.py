"""Refine CBG's existing glass tint from the facade contractor's neutral coating.

Run in Blender Text Editor. This is an appearance estimate, not a measured RGB
or a reconstruction of the still-unregistered office ventilation modules.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/cbg_glazing_next'
OUT.mkdir(parents=True, exist_ok=True)
BASE = ROOT / 'result/blender/LSE_campus_detailed_v127.blend'
if not BASE.exists():
    BASE = max((ROOT / 'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),
               key=lambda path: int(path.stem.rsplit('v', 1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
bpy.context.window.scene = scene
previous_path = OUT / 'audit.json'
if previous_path.exists():
    previous = json.loads(previous_path.read_text())
    for name in previous['ownedObjects']:
        obj = bpy.data.objects.get(name)
        if obj:
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            data.use_fake_user = False
            if not data.users:
                bpy.data.meshes.remove(data)
    for name in previous['archivedObjects']:
        obj = bpy.data.objects[name]
        obj.hide_render, obj.hide_viewport = previous['originalVisibility'][name][:2]
        obj.hide_set(previous['originalVisibility'][name][2])
    for mat in list(bpy.data.materials):
        if mat.name.startswith('CBG_NEXT_neutral_glazing') and mat.users == int(mat.use_fake_user):
            mat.use_fake_user = False
            bpy.data.materials.remove(mat)
for layer in scene.view_layers:
    layer.update()


def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for data, field, kind, count in ((obj.data.vertices, 'co', 'f', 3),
                                         (obj.data.loops, 'vertex_index', 'i', 1),
                                         (obj.data.polygons, 'material_index', 'i', 1)):
            values = array.array(kind, [0]) * (len(data) * count)
            data.foreach_get(field, values)
            digest.update(values.tobytes())
        for layer in obj.data.uv_layers:
            values = array.array('f', [0]) * (len(layer.data) * 2)
            layer.data.foreach_get('uv', values)
            digest.update(values.tobytes())
    digest.update(str([mat.name if mat else None for mat in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()


originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
sources = ['CBG_D_curtain_wall_glazing', 'CBG_D_end_wall_glazing', 'CBG_D_entry_glass_door_leaves']
original_mat = bpy.data.objects[sources[0]].data.materials[0]
assert all(list(bpy.data.objects[name].data.materials) == [original_mat] for name in sources)
old_color = list(original_mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value)
weights = (.2126, .7152, .0722)
luminance = sum(c * w for c, w in zip(old_color, weights))
neutral = (.285, .297, .308)
scale = luminance / sum(c * w for c, w in zip(neutral, weights))
new_color = tuple(c * scale for c in neutral) + (old_color[3],)
mat = original_mat.copy()
mat.name = 'CBG_NEXT_neutral_glazing'
mat.diffuse_color = new_color
mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = new_color
assert abs(sum(c * w for c, w in zip(new_color, weights)) - luminance) < 1e-8
owned = []
for name in sources:
    original = bpy.data.objects[name]
    obj = original.copy()
    obj.data = original.data.copy()
    obj.name = 'CBG_NEXT_neutral_' + name.removeprefix('CBG_D_')
    obj.data.name = obj.name
    obj.data.materials[0] = mat
    bpy.data.collections['CBG_EXTERIOR'].objects.link(obj)
    original.hide_render = True
    original.hide_set(True)
    owned.append(obj)
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
component = OUT / 'cbg-glazing-component.blend'
bpy.data.libraries.write(str(component), set(owned), fake_user=True)
audit = {
    'baselineSha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
    'ownedObjects': [obj.name for obj in owned], 'archivedObjects': sources,
    'originalVisibility': visibility, 'originalGeometryPreserved': True,
    'oldColorLinear': old_color, 'newColorLinear': new_color,
    'linearLuminance': luminance, 'webOpacity': mat.get('webOpacity'),
    'transmission': float(mat.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value),
    'source': {'url': 'https://www.dobler-metallbau.com/wp-content/uploads/2021/11/LSE_eng_web.pdf',
               'documentDate': '2023-02-20', 'page': 2, 'coating': 'SOLARWER neutral70/37',
               'sha256': hashlib.sha256((ROOT / 'data/collections/cbg_facade_contractor/dobler-lse-facade.pdf').read_bytes()).hexdigest()},
    'scope': 'Existing curtain panes, end panes and entry glass only. Red/orange shades, frame geometry, roughness and transparency retained.',
    'limitations': ['Neutral cool tint is a visual estimate without a color card; source lightness retained.',
                    'Physical68% light transmission is not equivalent to WebGL alpha.',
                    'Office solid opening panels and high-level vents remain unregistered and unbuilt.']
}
(OUT / 'audit.json').write_text(json.dumps(audit, indent=2) + '\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
with bpy.data.libraries.load(str(component), link=False) as (src, dst):
    dst.objects = list(audit['ownedObjects'])
for obj in dst.objects:
    bpy.data.collections['CBG_EXTERIOR'].objects.link(obj)
for name in sources:
    bpy.data.objects[name].hide_render = True
    bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:
    layer.update()
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
loaded = dst.objects[0].data.materials[0]
loaded_color = list(loaded.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value)
assert max(abs(a - b) for a, b in zip(loaded_color, new_color)) < 1e-7
assert abs(float(loaded.get('webOpacity')) - .56) < 1e-7
proof = {'componentSha256': hashlib.sha256(component.read_bytes()).hexdigest(),
         'savedComponentReopened': True, 'originalObjectCount': len(originals),
         'originalGeometryPreserved': True, 'fullModelSaved': False,
         'glassObjects': len(dst.objects), 'reloadedColorLinear': loaded_color,
         'sourceLuminanceRetained': True, 'sourceTransparencyRetained': True}
(OUT / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n')
print('CBG_NEUTRAL_GLAZING_RELOADED', len(originals), len(dst.objects), flush=True)
bpy.ops.wm.quit_blender()
