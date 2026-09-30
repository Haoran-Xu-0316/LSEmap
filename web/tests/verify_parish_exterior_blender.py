"""Measure saved PAR roof furniture, front joinery and outward-facing surfaces."""
from pathlib import Path
import json
import bpy
from mathutils import Vector
ROOT = Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'result/blender/LSE_campus_detailed_v66.blend'))
path = ROOT / 'result/blender/stage66/parish-exterior-audit.json'
a = json.loads(path.read_text())
w = a['front']
u = Vector(((w['q'][0] - w['p'][0]) / w['length'], (w['q'][1] - w['p'][1]) / w['length'], 0))
n = Vector((*w['outward'], 0))
origin = Vector((*w['p'], 0))
def points(name):
    obj = bpy.data.objects[name]
    return [obj.matrix_world @ v.co for v in obj.data.vertices]
heads = points('PAR_D5_photo66_pointed_window_head_archbrick')
assert len(heads) == 1536
peaks = []
for i in range(4):
    pts = heads[i * 384:(i + 1) * 384]
    peak = max(p.z for p in pts)
    assert 6.79 < peak < 6.81
    assert abs(sum((p - origin).dot(u) for p in pts) / len(pts) - (i + .5) * a['split'] / 4) < .0001
    peaks.append(peak)
central = points('PAR_D5_photo66_central_mullion_frame')
assert len(central) == 64
lower_bars = points('PAR_D5_photo66_lower_sash_bar_frame')
assert len(lower_bars) == 32
for start in range(0, 32, 8):
    pts = lower_bars[start:start + 8]
    assert abs(sum(p.z for p in pts) / 8 - (2.8 + 2.35 * .34)) < .0001
cap = bpy.data.objects['PAR_D5_photo66_cowl_cap_lead']
assert cap['component_count'] == 2
pots = bpy.data.objects['PAR_D5_photo66_round_chimney_pot_tile']
assert pots['component_count'] == 4
for name in ['PAR_D5_tiled_roof', 'PAR_D5_dormer_pitched_roof_tile']:
    assert all(poly.normal.z > 0 for poly in bpy.data.objects[name].data.polygons), name
assert all(poly.normal.dot(n) > .99 for poly in bpy.data.objects['PAR_D5_entrance_gable_brick'].data.polygons)
for name in a['hiddenPreviousObjects']:
    assert bpy.data.objects[name].hide_render
assert not a['changedOtherObjects']
a['savedMeasurements'] = {'pointedHeadPeaks': peaks, 'centralMullions': 8,
                          'lowerSashBars': 4, 'roofCowls': 2, 'roundPots': 4,
                          'outwardEntranceGable': True, 'upwardRoofFaces': True}
path.write_text(json.dumps(a, indent=2) + '\n')
print('SAVED_PARISH_EXTERIOR_VERIFIED')
