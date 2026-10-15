"""Verify saved native footway borders, then independently compare coverage.

Run this file in Blender for native extraction, followed by MachineLearning for
planar coverage checks. It never modifies either accepted campus model.
"""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/streets215'
def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def native():
 import bpy
 from mathutils import Vector
 sys.path.insert(0,str(ROOT/'web/tools'))
 from refine_portsmouth_exterior207 import material_fingerprint
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v214.blend'))
 originals={m.name:material_fingerprint(m) for m in bpy.data.materials}
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v215.blend'))
 bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for name,digest in originals.items():assert material_fingerprint(bpy.data.materials[name])==digest,name
 audit=json.loads((OUT/'audit.json').read_text());rows=[]
 for name in audit['archivedObjects']:assert bpy.data.objects[name].hide_render
 for name in audit['addedObjects']:
  obj=bpy.data.objects[name];assert not obj.hide_render
  assert [m.name for m in obj.data.materials]==audit['replacementMaterialBindings'][name]
  points=[obj.matrix_world@p.co for p in obj.data.vertices]
  assert all(abs(p.z-.024)<1e-6 for p in points)
  assert all(p.normal.z>.99 for p in obj.data.polygons)
  assert obj.data.uv_layers.active.name=='MetricUV'
  rows.append(dict(name=name,faces=[[list(points[i]) for i in f.vertices] for f in obj.data.polygons]))
 baseline_rows=[]
 for name in audit['archivedObjects']:
  obj=bpy.data.objects[name];points=[obj.matrix_world@v.co for v in obj.data.vertices];baseline_rows.append(dict(name=name,faces=[[list(points[i]) for i in f.vertices] for f in obj.data.polygons]))
 save(OUT/'saved-native.json',dict(baselineObjects=baseline_rows,sourceModelSha256=hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v215.blend').read_bytes()).hexdigest(),originalMaterialNodesVerified=len(originals),heightNormalsAndBindingsVerified=True,objects=rows))
 print('STREETS215_NATIVE',len(originals),sum(len(o['faces']) for o in rows),flush=True)
def coverage():
 from shapely.geometry import Polygon,shape
 from shapely.ops import unary_union
 old=json.loads((ROOT/'result/blender/streets213/plan.json').read_text());plan=json.loads((OUT/'plan.json').read_text());saved=json.loads((OUT/'saved-native.json').read_text())
 # Compare the two actual accepted Blender meshes. The ideal plan also
 # contains microscopic triangles that already collapsed in the213export.
 expected=unary_union([Polygon([p[:2] for p in f]) for o in saved['baselineObjects'] for f in o['faces']])
 actual=unary_union([Polygon([p[:2] for p in f]) for o in saved['objects'] for f in o['faces']])
 assert actual.difference(expected.buffer(.0001)).area<.00001
 assert expected.difference(actual.buffer(.0001)).area<.00001
 error=expected.symmetric_difference(actual).area
 assert error<expected.length*.0001,error
 total=sum(Polygon([p[:2] for p in f]).area for o in saved['objects'] for f in o['faces'])
 assert total-actual.area<expected.length*.00005
 edge=unary_union([Polygon([p[:2] for p in f]) for o in saved['objects'] if o['name'].endswith('_edge') for f in o['faces']])
 # The design outline is frozen before triangulation. Verify the saved
 # native border against that contract, not a reordered GEOS union whose
 # sub-grid topology can differ at numerical cracks.
 outline_record=json.loads((OUT/'edge-outline.json').read_text())
 assert outline_record['sourcePlanSha256']==hashlib.sha256((ROOT/'result/blender/streets213/plan.json').read_bytes()).hexdigest()
 outline=shape(outline_record['geometry'])
 assert edge.difference(outline.difference(outline.buffer(-.14,join_style='mitre')).buffer(.0001)).area<.0001
 record=dict(version=215,nativeCoverageVerified=True,expectedAreaM2=expected.area,savedAreaM2=actual.area,symmetricDifferenceM2=error,duplicateAreaM2=total-actual.area,boundaryToleranceMetres=.0001,removedInternalBandAreaM2=plan['removedInternalBandAreaM2'],sourceWays=plan['sourceWays'],sourceModelSha256=saved['sourceModelSha256'],originalMaterialNodesVerified=saved['originalMaterialNodesVerified'])
 save(OUT/'verification.json',record);print('STREETS215_COVERAGE',record)
if __name__=='__main__':
 try:import bpy
 except ImportError:coverage()
 else:native()
