"""Neutralise unsupported cyan glass on Columbia and Connaught House.

Open in Blender's Text Editor. Colour is a visual estimate from archived LSE
exterior photographs, not a measured or date-certified facade specification.
Only dedicated exterior material slots change; shared source materials survive.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/stage41'
OUT.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v40.blend'))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
TARGETS = ['COL_D4_recessed_glass', 'CON_EXTERIOR_Glazing_bays',
           'CON_D4_recessed_glass', 'CON_D4_vestibule_glass', 'CON_D4_fanlight_glass']
COLOUR = (.10, .115, .12, 1)

def fingerprint(obj):
    digest = hashlib.sha256(array.array('f', [c for v in obj.data.vertices for c in v.co]).tobytes())
    digest.update(array.array('i', [v.vertex_index for v in obj.data.loops]).tobytes())
    return digest.hexdigest()

before = {o.name: fingerprint(o) for o in bpy.data.objects if o.type == 'MESH'}
slots = {o.name: [m.name if m else None for m in o.data.materials] for o in bpy.data.objects if o.type == 'MESH'}

def export_review(code, phase):
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in bpy.data.collections[code + '_EXTERIOR'].all_objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT / f'{code.lower()}-{phase}.glb'),
        export_format='GLB', use_selection=True, use_active_scene=True,
        export_cameras=False, export_lights=False)

for code in ['COL', 'CON']:
    export_review(code, 'before')
changes = []
materials = {}
for name in TARGETS:
    obj = bpy.data.objects[name]
    assert len(obj.data.materials) == 1, name
    source = obj.data.materials[0]
    key = (name[:3], source.name)
    if key not in materials:
        material = source.copy()
        material.name = f'{name[:3]}_V41_neutral_glass_{len(materials)}'
        material.diffuse_color = COLOUR
        material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = COLOUR
        materials[key] = material
    obj.data.materials[0] = materials[key]
    changes.append({'object': name, 'oldColour': list(source.diffuse_color), 'newColour': list(COLOUR)})
assert all(fingerprint(o) == before[o.name] for o in bpy.data.objects if o.type == 'MESH')
assert all([m.name if m else None for m in o.data.materials] == slots[o.name]
           for o in bpy.data.objects if o.type == 'MESH' and o.name not in TARGETS)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'aldwych-glazing-candidate.blend'))
for code in ['COL', 'CON']:
    export_review(code, 'after')
(OUT / 'glazing-audit.json').write_text(json.dumps({
    'baseline': 'LSE_campus_detailed_v40.blend', 'changes': changes,
    'unchangedMeshGeometry': len(before), 'otherMaterialAssignmentsUnchanged': True,
    'references': ['data/建筑图片/COL_Columbia House/01_建筑实拍/exteriors_lse_estate_004.jpg',
      'data/建筑图片/COL_Columbia House/01_建筑实拍/small_round5_COL_handbook-000.png',
      'data/建筑图片/CON_Connaught House/01_建筑实拍/exteriors_lse_estate_005.jpg'],
    'limitations': ['Photo dates unverified; handbook edition 2025/26',
      'Colour is not a calibrated measurement; reflections depend on environment',
      'Upper repetition, roofs and complete interiors remain unresolved'],
    'publication': 'Candidate only'
}, ensure_ascii=False, indent=2)+'\n')
print('ALDWYCH_GLAZING_REFINED', len(TARGETS))
