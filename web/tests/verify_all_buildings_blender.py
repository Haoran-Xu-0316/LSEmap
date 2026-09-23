"""Independent reopen audit of the local edition-16 native model.
Run in Blender; writes a report, never modifies or saves the source model.
"""
from pathlib import Path
import hashlib
import json
import math
import bpy
ROOT=Path(__file__).resolve().parents[2]
MODEL=ROOT/'result/blender/LSE_campus_detailed_v16.blend'
bpy.ops.wm.open_mainfile(filepath=str(MODEL))
manifest=json.loads((ROOT/'result/blender/stage16/all-buildings-manifest.json').read_text())
records=manifest['buildings']
checks={
 'all_31_codes':len(records)==31 and len({r['code'] for r in records})==31,
 'all_31_geometry_digests_changed':all(r['originalGeometrySha256']!=r['afterGeometrySha256'] for r in records),
 'all_31_have_components':all(r['newComponents']>0 for r in records),
 'finite_mesh_coordinates':all(math.isfinite(v) for mesh in bpy.data.meshes for vertex in mesh.vertices for v in vertex.co),
 'all_30_exterior_collections':all(bpy.data.collections.get(r['code']+'_EXTERIOR') for r in records if r['code']!='35L'),
 'construction_collection_retained':any(c.name.startswith('35L_CONSTRUCTION') for c in bpy.data.collections),
 'five_public_interiors_retained':all(bpy.data.collections.get(code+'_PUBLIC_INTERIOR_study') for code in ['MAR','SAW','CBG','CKK','LRB']),
}
report={'checks':checks,'newFinishComponents':sum(r['newComponents'] for r in records),'sha256':hashlib.sha256(MODEL.read_bytes()).hexdigest(),'bytes':MODEL.stat().st_size}
(ROOT/'result/web/all-buildings/native-audit.json').write_text(json.dumps(report,indent=2)+'\n')
assert all(checks.values()),checks
print('NATIVE_EDITION16_AUDIT_PASS',json.dumps(report),flush=True)
