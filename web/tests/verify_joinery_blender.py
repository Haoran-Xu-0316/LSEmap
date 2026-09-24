"""Reopen edition 17 and verify per-building joinery geometry without changing it."""
from pathlib import Path
import hashlib
import json
import math
import bpy
ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT/'result/blender/LSE_campus_detailed_v17.blend'
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
report = json.loads((ROOT/'result/blender/stage17/all-buildings-manifest.json').read_text())
records = report['buildings']
checks = {
    'all_31_records': len(records) == 31 and len({r['code'] for r in records}) == 31,
    'every_building_has_new_components': all(r['newComponents'] > 0 for r in records),
    'all_exterior_geometry_changed': all(r['originalGeometrySha256'] != r['afterGeometrySha256'] for r in records if r['code'] != '35L'),
    'finite_new_vertices': all(math.isfinite(x) for o in bpy.data.objects if '_V17_' in o.name and o.type == 'MESH' for v in o.data.vertices for x in v.co),
    'every_building_has_saved_joinery': all(any('_V17_' in o.name for o in (bpy.data.collections[r['code']+'_EXTERIOR'].all_objects if r['code'] != '35L' else next(c for c in bpy.data.collections if c.name.startswith('35L_CONSTRUCTION')).all_objects)) for r in records),
    'five_public_interiors_retained': all(bpy.data.collections.get(code+'_PUBLIC_INTERIOR_study') for code in ['MAR','SAW','CBG','CKK','LRB']),
}
result = {'checks':checks,'sourceModelSha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'components':sum(r['newComponents'] for r in records)}
(ROOT/'result/blender/stage17/native-audit.json').write_text(json.dumps(result,indent=2)+'\n')
assert all(checks.values()), checks
print('JOINERY_AUDIT_PASS',json.dumps(result),flush=True)
