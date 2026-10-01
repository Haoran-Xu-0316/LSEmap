"""Calibrate restored OCS finishes from the restoration team's exterior photos.
Run in Blender Text Editor. No reference photographs are packaged with the model.
"""
from pathlib import Path
import array, hashlib, json, shutil
import bpy
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage81'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v80.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def geometry(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[x for v in o.data.vertices for x in v.co]).tobytes())
  h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 return h.hexdigest()
before={o.name:geometry(o)for o in bpy.data.objects}
other_slots={o.name:[m.name if m else None for m in getattr(o.data,'materials',[])] for o in bpy.data.objects if not o.name.startswith('OCS_')}
palette={'cream_render':(.59,.545,.455),'cream_cornice':(.49,.445,.355),
 'deep_green_timber':(.016,.027,.022),'ochre_surround':(.38,.21,.095),
 'red_brown_sash':(.095,.029,.023)}
owned={}
for key,color in palette.items():
 m=bpy.data.materials.new('OCS_V81_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 s=m.node_tree.nodes['Principled BSDF']
 s.inputs['Base Color'].default_value=(*color,1)
 s.inputs['Roughness'].default_value=.83 if key=='cream_render' else .57
 owned[key]=m
changes=[]
upper_faces=0
for o in bpy.data.collections['OCS_EXTERIOR'].all_objects:
 if o.type!='MESH':continue
 selected={}
 for i,m in enumerate(o.data.materials):
  if not m:continue
  name=m.name
  key=None
  if name=='OCS_D3_warm_lime_plaster':key='cream_render'
  elif name=='OCS_D3_cornice':key='cream_cornice'
  elif name=='OCS_D3_deep_green_joinery' or name in ['V16_OCS_finish','V17_OCS_finish']:key='deep_green_timber'
  elif name=='OCS_D3_ochre_window_moulding':key='ochre_surround'
  elif name=='OCS_D3_sash_red_brown':key='red_brown_sash'
  if key:
   o.data.materials[i]=owned[key];selected[i]=key
 if not selected:continue
 split=[]
 if any(key=='deep_green_timber' for key in selected.values()):
  # Historical generic timber details used green for both storeys.
  # Keep the shop green, assign the upper sash lining its photographed finish.
  upper_key='ochre_surround' if any(n in o.name for n in ['lining','weatherboard','head_lining','apron']) else 'red_brown_sash'
  o.data.materials.append(owned[upper_key]);slot=len(o.data.materials)-1
  for p in o.data.polygons:
   if selected.get(p.material_index)=='deep_green_timber' and min((o.matrix_world@o.data.vertices[i].co).z for i in p.vertices)>3:
    p.material_index=slot;split.append(p.index);upper_faces+=1
 changes.append({'name':o.name,'slots':selected,'upperFinish':upper_key if split else None,'upperFaces':split})
assert all(before[o.name]==geometry(o)for o in bpy.data.objects)
assert all(other_slots[o.name]==[m.name if m else None for m in getattr(o.data,'materials',[])]for o in bpy.data.objects if o.name in other_slots)
for filename in ['room-studies.json','room-spaces.json','building-review.json']:
 shutil.copyfile(ROOT/'result/blender/stage80'/filename,OUT/filename)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':81,'baseline':80,'palette':palette,'changedObjects':changes,'upperReassignedFaces':upper_faces,
 'referenceUrls':['https://www.ayesa.com/en/projects/the-old-curiosity-shop/','https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/development-projects'],
 'referenceFiles':['data/collections/exterior_photos_round4/images/OCS/OCS_ayesa_2.jpg','data/collections/exterior_photos_round4/images/OCS/OCS_ayesa_9.jpg'],
 'limitations':['2023 completed restoration, photographs published in 2023/2024; precise capture date and 2026 paint condition unverified','Photo-guided colour estimates, no measured colour standard','Existing roof tiles and all geometry retained; roof silhouette, unseen elevations and full current interior still require review'],
 'baselineGeometry':before,'otherMaterialSlots':other_slots}
(OUT/'ocs-finish-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v81.blend'))
print('OCS_RESTORED_FINISH_SAVED',len(changes),upper_faces,flush=True)
