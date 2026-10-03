"""Restore the photographed green ceramic attic and lead cupola seams.

Run in Blender's Text Editor. Original meshes and materials are retained.
Writes a small mergeable component, not another complete campus backup.
Photographic colours are estimates; this is not a surveyed full-building model.
"""
from pathlib import Path
import array
import hashlib
import json
import re
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/kgs_next'
OUT.mkdir(parents=True, exist_ok=True)
BASELINE = ROOT / 'result/blender/LSE_campus_detailed_v119.blend'
rebuilding_merged = not BASELINE.exists()
if rebuilding_merged:
    candidates = []
    for path in (ROOT / 'result/blender').glob('LSE_campus_detailed_v*.blend'):
        match = re.fullmatch(r'LSE_campus_detailed_v(\d+)\.blend', path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    assert candidates, 'No accepted full native model available'
    BASELINE = max(candidates)[1]
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
if rebuilding_merged:
    previous = json.loads((OUT / 'audit.json').read_text())
    for name in previous['ownedObjects']:
        obj = bpy.data.objects.get(name)
        if obj:
            assert name.startswith('KGS_NEXT_')
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
    for name in previous['archivedObjects']:
        assert name.startswith('KGS_')
        obj = bpy.data.objects[name]
        state = previous['originalVisibility'][name]
        obj.hide_render = state['hideRender']
        obj.hide_set(state['hideViewport'])
    for material in list(bpy.data.materials):
        if material.name.startswith('KGS_NEXT_') and material.users == 0:
            bpy.data.materials.remove(material)

for scene in bpy.data.scenes:
    for layer in scene.view_layers:
        layer.update()

def fingerprint(obj):
    coordinates = array.array('f', [0]) * (3 * len(obj.data.vertices))
    indices = array.array('i', [0]) * len(obj.data.loops)
    obj.data.vertices.foreach_get('co', coordinates)
    obj.data.loops.foreach_get('vertex_index', indices)
    return {'geometry': hashlib.sha256(coordinates.tobytes() + indices.tobytes()).hexdigest(),
            'matrix': [list(row) for row in obj.matrix_world],
            'materials': [material.name if material else None for material in obj.data.materials],
            'polygonMaterialsSha256': hashlib.sha256(array.array('i', [face.material_index for face in obj.data.polygons]).tobytes()).hexdigest()}

originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects if obj.type == 'MESH'}
visibility = {obj.name: {'hideRender': obj.hide_render, 'hideViewport': obj.hide_get()}
              for obj in bpy.data.objects}
collection = bpy.data.collections['KGS_EXTERIOR']
owned, archived, changes = [], [], []

# Both the LSE estate photograph and the official list entry identify this
# green ceramic attic. Reuse all original wall apertures and dimensional data.
material = bpy.data.materials.new('KGS_NEXT_green_ceramic')
material.diffuse_color = (.072, .145, .103, 1)
material.use_nodes = True
nodes, links = material.node_tree.nodes, material.node_tree.links
surface = nodes.get('Principled BSDF')
surface.inputs['Base Color'].default_value = material.diffuse_color
surface.inputs['Roughness'].default_value = .37
brick = nodes.new('ShaderNodeTexBrick')
brick.inputs['Color1'].default_value = (.078, .155, .111, 1)
brick.inputs['Color2'].default_value = (.053, .118, .082, 1)
brick.inputs['Mortar'].default_value = (.096, .118, .102, 1)
brick.inputs['Mortar Size'].default_value = .004
brick.inputs['Brick Width'].default_value = .23
brick.inputs['Row Height'].default_value = .075
brick.inputs['Scale'].default_value = 1
coordinate = nodes.new('ShaderNodeTexCoord')
links.new(coordinate.outputs['UV'], brick.inputs['Vector'])
links.new(brick.outputs['Color'], surface.inputs['Base Color'])
bump = nodes.new('ShaderNodeBump')
bump.inputs['Strength'].default_value = .08
bump.inputs['Distance'].default_value = .002
links.new(brick.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], surface.inputs['Normal'])

for part in ['window_piers_darkbrick', 'window_spandrel_darkbrick', 'window_head_darkbrick']:
    original = bpy.data.objects['KGS_D5_' + part]
    assert not original.hide_render and not original.hide_get()
    replacement = original.copy()
    replacement.data = original.data.copy()
    replacement.name = 'KGS_NEXT_' + part
    replacement.data.name = replacement.name
    collection.objects.link(replacement)
    replacement.data.materials.append(material)
    material_index = len(replacement.data.materials) - 1
    selected = []
    for face in replacement.data.polygons:
        heights = [(replacement.matrix_world @ replacement.data.vertices[index].co).z
                   for index in face.vertices]
        if min(heights) >= 12.899:
            face.material_index = material_index
            selected.append(face.index)
    assert selected, part
    # Existing box parts end exactly at the attic cornice; no face is cut and
    # no extra sheet is laid over an aperture.
    original.hide_render = True
    original.hide_set(True)
    replacement.hide_render = False
    replacement.hide_set(False)
    replacement['scope'] = 'Photo-guided green ceramic attic; original wall geometry retained'
    archived.append(original.name)
    owned.append(replacement)
    changes.append({'original': original.name, 'replacement': replacement.name,
                    'atticFaces': selected, 'atticDatum': 12.9})

original = bpy.data.objects['KGS_D5_dome_standing_seams_trim']
replacement = original.copy()
replacement.data = original.data.copy()
replacement.name = 'KGS_NEXT_lead_cupola_seams'
replacement.data.name = replacement.name
collection.objects.link(replacement)
lead = bpy.data.materials['HERITAGE09_lead'].copy()
lead.name = 'KGS_NEXT_lead_seams'
lead.diffuse_color = (.19, .22, .22, 1)
surface = lead.node_tree.nodes.get('Principled BSDF')
for link in list(surface.inputs['Base Color'].links):
    lead.node_tree.links.remove(link)
surface.inputs['Base Color'].default_value = lead.diffuse_color
surface.inputs['Roughness'].default_value = .63
replacement.data.materials.clear()
replacement.data.materials.append(lead)
original.hide_render = True
original.hide_set(True)
replacement.hide_render = False
replacement.hide_set(False)
archived.append(original.name)
owned.append(replacement)
changes.append({'original': original.name, 'replacement': replacement.name,
                'scope': 'Lead-coloured standing seams; cupola geometry unchanged'})

assert originals == {name: fingerprint(bpy.data.objects[name]) for name in originals}
component = OUT / 'kings-chambers-component.blend'
bpy.data.libraries.write(str(component), set(owned), fake_user=False, compress=True)
assert component.stat().st_size < 10 * 1024 * 1024

audit = {'baseline': str(BASELINE.relative_to(ROOT)),
         'baselineSha256': hashlib.sha256(BASELINE.read_bytes()).hexdigest(),
         'archivedObjects': archived, 'ownedObjects': [obj.name for obj in owned],
         'originalFingerprints': originals, 'originalVisibility': visibility,
         'changes': changes, 'componentBytes': component.stat().st_size,
         'componentSha256': hashlib.sha256(component.read_bytes()).hexdigest(),
         'sources': [{'url': 'https://historicengland.org.uk/listing/the-list/list-entry/1235528',
                      'date': '1987-12-01 listing; read 2026-10-03',
                      'supports': 'Green ceramic attic and lead cupola; historical description, not current survey'},
                     {'file': 'data/建筑图片/KGS_King_s Chambers/01_建筑实拍/exteriors_lse_estate_008.jpg',
                      'sha256': '8835a81eececb3844114b8a4bee78cca1ce0400e5187f02c46905b19d823ace7',
                      'url': 'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Images/LSE-Estate/Kings-Chambers-300x376.jpg',
                      'date': 'Capture date unknown; current published LSE estate source',
                      'supports': 'Green upper-storey panels, grey lead dome ribs'}],
         'limitations': ['Colour estimated from photography, not calibrated albedo',
                         'Roof pitch, ground-floor shops and full interior remain unverified',
                         'No new opening locations, roof geometry or interior changes']}
(OUT / 'audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
print('KGS_COMPONENT_COMPLETE', len(owned), component.stat().st_size)
