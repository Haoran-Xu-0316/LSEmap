"""Verify saved native street meshes and preserved source material nodes."""
from pathlib import Path
import json,sys,hashlib
import bpy
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'web/tools'))
from refine_portsmouth_exterior207 import material_fingerprint
OUT=ROOT/'result/blender/stage213'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v212.blend'))
materials={m.name:material_fingerprint(m) for m in bpy.data.materials}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v213.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
for name,value in materials.items():assert material_fingerprint(bpy.data.materials[name])==value,name
plan=json.loads((ROOT/'result/blender/streets213/plan.json').read_text());audit=json.loads((ROOT/'result/blender/streets213/audit.json').read_text())
for name in audit['archivedObjects']:assert bpy.data.objects[name].hide_render,name
rows=[]
for name in audit['addedObjects']:
 o=bpy.data.objects[name];assert not o.hide_render
 vertices=[o.matrix_world@v.co for v in o.data.vertices]
 assert all(abs(v.z-.024)<1e-6 for v in vertices)
 assert all(f.normal.z>.99 for f in o.data.polygons)
 faces=[dict(points=[list(vertices[i]) for i in f.vertices],material=o.data.materials[f.material_index].name) for f in o.data.polygons]
 rows.append(dict(name=name,faces=faces))
lrb=json.loads((ROOT/'result/blender/library-circulation213/audit.json').read_text())
for name,bindings in lrb['replacementMaterialBindings'].items():
 o=bpy.data.objects[name];assert [m.name for m in o.data.materials]==bindings
 assert o.name in bpy.data.collections['LRB_PUBLIC_INTERIOR168_study'].all_objects
for name in lrb['archivedObjects']:assert bpy.data.objects[name].hide_render
record=dict(version=213,completeModelReopened=True,sourceModelSha256=hashlib.sha256((ROOT/'result/blender/LSE_campus_detailed_v213.blend').read_bytes()).hexdigest(),originalMaterialNodesVerified=len(materials),allStreetNormalsUpward=True,originalStreetHeightPreserved=True,libraryMaterialBindingsPreserved=True,objects=rows)
(OUT/'saved-streets.json').write_text(json.dumps(record,indent=2)+'\n');print('STREETS213_NATIVE_VERIFIED',sum(len(r['faces']) for r in rows),len(materials),flush=True)
