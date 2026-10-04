"""Audit the present FAW envelope against attributable exterior references.

Open in Blender Text Editor. Unsupported tower dimensions are retained explicitly;
this audit never changes or saves the production scene.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'result/blender/faw_exterior156'
BASE = max((ROOT / 'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'), key=lambda path: int(path.stem.rsplit('v',1)[1]))
BASE_SHA = hashlib.sha256(BASE.read_bytes()).hexdigest()

def fingerprint(obj):
    digest = hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type == 'MESH':
        for items, field, kind, width in [(obj.data.vertices, 'co', 'f', 3), (obj.data.loops, 'vertex_index', 'i', 1), (obj.data.polygons, 'material_index', 'i', 1)]:
            values = array.array(kind, [0]) * (len(items) * width)
            items.foreach_get(field, values)
            digest.update(values.tobytes())
    digest.update(str([material.name if material else None for material in getattr(obj.data, 'materials', [])]).encode())
    return digest.hexdigest()

assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
bpy.ops.wm.open_mainfile(filepath=str(BASE))
bpy.context.window.scene = bpy.data.scenes['00_CAMPUS_COMPLETE']
originals = {obj.name: fingerprint(obj) for obj in bpy.data.objects}
visibility = {obj.name: [obj.hide_render, obj.hide_viewport, obj.hide_get()] for obj in bpy.data.objects}
assert originals, "The saved campus must contain its original objects"
collection = bpy.data.collections['FAW_EXTERIOR']
geometry = []
for obj in collection.all_objects:
    if obj.type != 'MESH' or not obj.data.vertices or obj.hide_render:
        continue
    positions = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    geometry.append({'name': obj.name, 'fingerprint': originals[obj.name], 'vertices': len(positions), 'bounds': [[min(v[i] for v in positions) for i in range(3)], [max(v[i] for v in positions) for i in range(3)]], 'materials': [m.name if m else None for m in obj.data.materials]})
glass = bpy.data.objects['FAW_D3_recessed_window_bands']
levels = {}
for start in range(0, len(glass.data.vertices), 8):
    positions = [glass.matrix_world @ vertex.co for vertex in glass.data.vertices[start:start + 8]]
    height = round(sum(v.z for v in positions) / 8, 3)
    levels[str(height)] = levels.get(str(height), 0) + 1
sources = []
source_root = OUT / 'sources'
for path in sorted(source_root.glob('*.jpg')):
    sources.append({'local': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'primaryPage': 'https://www.architectureplb.com/sectors/universities-and-colleges/lse-towers', 'projectStatus': 'Completed August 2018; phase one is shared towers 1/2 reception; phase two is tower 3', 'photographDate': 'not individually specified', 'coverage': 'Shared PAN/FAW entrance or interior. No FAW crown, independent full height, or complete tower elevation.'})
register = [
    {'element': 'Whole tower massing and all upper elevations', 'production': '44.23m maximum height; 144 repeated window-band cells across 12 upper levels', 'source': 'Handbook page20 locates FAW east of PAN and records1971; AccessAble identifies twelfth-floor Media Studio. No full elevation in available primary photos.', 'discrepancy': 'Exact height, floor heights and per-face bay counts remain unverified', 'action': 'retain pending independent full-height photograph with identifiable PAN junction'},
    {'element': 'Warm aggregate horizontal spandrels and vertical facade subdivisions', 'production': 'FAW_D3_aggregate_spandrels and FAW_D3_precast_panel_vertical_joints', 'source': 'Handbook and LSE Estate photograph show warm aggregate on the PAN shared-entry block; ArchitecturePLB entrance photo shows the same block.', 'discrepancy': 'FAW-specific colour and subdivision cannot be registered', 'action': 'retain estimated shared material; do not claim calibrated FAW colour'},
    {'element': 'Pale metal frames and recessed glass bands', 'production': 'FAW_D3_recessed_window_bands with144 cells; pale metal frame elements', 'source': 'Available exterior photos show pale frames and reflective glass at shared PAN entrance; FAW teaching-room photos show internal blind/reveal fragments.', 'discrepancy': 'Per-face independent FAW pane count and frame dimensions unknown', 'action': 'retain; no repeated opacity/probe change'},
    {'element': 'Shared ground-floor entrance and forecourt', 'production': 'PAN shared-entry meshes, corrected5-wide module retained in separate PAN component', 'source': 'ArchitecturePLB confirms one shared entrance created from loading bay and two separate entrances; night exterior shows yellow soffit, transparent entrance and planters.', 'discrepancy': 'Source is registered to shared PAN doorway, not independent FAW facade', 'action': 'leave PAN original untouched; do not duplicate entrance on FAW'},
    {'element': 'Roof, parapet and equipment', 'production': 'Flat44m roof and inherited parapet/equipment', 'source': 'No identifiable roof or crown in four checked architect photos, handbook, public-realm photographs or tour photograph.', 'discrepancy': 'Largest reliable gap is absence of independent upper FAW elevation and crown evidence', 'action': 'no speculative geometry replacement'},
    {'element': 'Remaining tower faces', 'production': 'Repeated inherited envelope around footprint', 'source': 'No attributable north/east/south complete elevation in bounded source batch', 'discrepancy': 'Face-specific asymmetric bays and blank walls unresolved', 'action': 'retain explicitly unverified'}]
audit = {'baseline': str(BASE), 'baselineSha256': BASE_SHA, 'status': 'reviewed-no-component-independent-FAW-elevation-not-registered', 'destinationCollection': 'FAW_EXTERIOR', 'ownedObjects': [], 'archivedObjects': [], 'changes': [], 'originalObjectCount': len(originals), 'geometry': geometry, 'windowBandCount': len(glass.data.vertices)//8, 'windowLevelRegister': levels, 'sources': sources, 'wholeFacadeRegister': register, 'largestReliableGap': 'No independently attributable full-height FAW facade and roof/crown; entrance sources cannot establish tower-wide dimensions or colours.', 'boundedLookup': ['Current official LSE Estate page verified FAW formerly Tower Two,2Clements Inn,1971.', 'ArchitecturePLB LSE Towers primary completed-project page and four original images inspected; no independent FAW whole facade.', 'Geograph5380684 referenced in Commons category, direct page unavailable; not used as geometry evidence.']}
assert all(fingerprint(bpy.data.objects[name]) == value for name, value in originals.items())
assert all([bpy.data.objects[name].hide_render, bpy.data.objects[name].hide_viewport, bpy.data.objects[name].hide_get()] == value for name, value in visibility.items())
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
OUT.mkdir(parents=True, exist_ok=True)
(OUT/'audit.json').write_text(json.dumps(audit, indent=2)+'\n')
(OUT/'verification.json').write_text(json.dumps({'baselineSha256': BASE_SHA, 'originalObjectCount': len(originals), 'originalGeometryPreserved': True, 'unrelatedVisibilityPreserved': True, 'baselineUnchanged': True, 'componentCreated': False, 'componentSha256': None, 'savedComponentReopened': False, 'reason': 'Evidence does not establish a reliable independent FAW exterior discrepancy.'}, indent=2)+'\n')
print('FAW_EXTERIOR156_AUDITED', len(geometry), levels, flush=True)
bpy.ops.wm.quit_blender()
