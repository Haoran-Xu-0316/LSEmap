"""Verify actual exported CBG geometry against the preceding accepted bounds.

Load the exporter setup and actual clone_group implementation, then exercise the
61A-to-CBG order that previously collapsed1362CBG vertices to the origin.
The saved native remains read-only and no web model is overwritten.
"""
from pathlib import Path
import json,sys,hashlib
ROOT=Path.cwd();script=ROOT/'web/tools/export_scene.py'
source=script.read_text();namespace={'__file__':str(script),'__name__':'export_diagnostic'}
exec(compile(source.split("campus_scene = bpy.data.scenes.new('WEB_CAMPUS')")[0],str(script),'exec'),namespace)
bpy=namespace['bpy'];records=namespace['records'];source_scene=namespace['source_scene']
for record in records:
 if record['interior']:
  collection=bpy.data.collections[record.get('interiorCollection',record['code']+'_PUBLIC_INTERIOR_study')]
  if collection.name not in source_scene.collection.children:source_scene.collection.children.link(collection)
namespace['full_detail']=True
for modifier,viewport,render in namespace['modifier_states']:
 if modifier.type=='BEVEL'and namespace['source_geometry_name'](modifier.id_data).startswith('SAL_FRAME_NEXT_'):continue
 modifier.show_viewport,modifier.show_render=viewport,render
for curve,resolution in namespace['curve_resolutions']:curve.resolution_u=resolution
bpy.context.window.scene=source_scene;bpy.context.view_layer.update();namespace['depsgraph']=bpy.context.evaluated_depsgraph_get()
# The prefix already defines exterior_objects before creating the campus scene.
rows=[]
for code,kind in [('61A','exterior'),('61A','interior'),('CBG','exterior'),('CBG','exterior')]:
 record=next(r for r in records if r['code']==code);objects=namespace['exterior_objects'](record)if kind=='exterior'else namespace['public_interior_objects'](record)
 scene=bpy.data.scenes.new('ORDER_'+code+'_'+kind);obj,bounds=namespace['clone_group'](objects,code,scene)
 zeros=sum(v.co.length<1e-7 for v in obj.data.vertices)
 rows.append(dict(code=code,kind=kind,bounds=bounds,zeroVertices=zeros,vertices=len(obj.data.vertices)))
 for item in list(scene.objects):bpy.data.objects.remove(item,do_unlink=True)
 bpy.data.scenes.remove(scene);bpy.data.batch_remove(ids=[mesh for mesh in bpy.data.meshes if mesh.users==0])
 if code=='CBG':
  assert zeros==0,rows[-1]
  expected=next(r for r in json.loads((ROOT/'result/blender/stage216/catalogue-before.json').read_text())['buildings']if r['code']=='CBG')['detailedExterior']['bounds']
  assert all(abs(bounds[key][i]-expected[key][i])<.0001 for key in ['min','max']for i in range(3)),rows[-1]
 print('ORDER',rows[-1],flush=True)
(ROOT/'result/blender/stage216/export-geometry-verification.json').write_text(json.dumps(rows,indent=2)+'\n')
