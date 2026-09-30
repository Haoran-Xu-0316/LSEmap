"""Correct photo-guided Lakatos sash divisions and facade finishes.
Run in Blender Text Editor; roof, bay positions and interiors remain unchanged.
"""
from pathlib import Path
import bpy,json,array,hashlib,sys
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage59';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v58.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];collection=bpy.data.collections['LAK_EXTERIOR']
def protected():
 h=hashlib.sha256();excluded=set(collection.all_objects)
 for obj in sorted(bpy.data.objects,key=lambda o:o.name):
  if obj in excluded:continue
  h.update(obj.name.encode());h.update(str([list(r)for r in obj.matrix_world]).encode())
  if obj.type=='MESH':
   h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
   h.update(str([m.name if m else None for m in obj.data.materials]).encode())
 return h.hexdigest()
before=protected();palette={};materials.clear()
for key,color in {'brick':(.46,.175,.078),'stone':(.67,.64,.565),'frame':(.74,.735,.70),'glass':(.105,.135,.13)}.items():
 source=bpy.data.materials['LAK13_'+key];mat=source.copy();mat.name='LAK_V59_'+key;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color
 if key=='brick':
  brick=next(n for n in mat.node_tree.nodes if n.type=='TEX_BRICK');brick.inputs['Color1'].default_value=(*color,1);brick.inputs['Color2'].default_value=(*(v*.83 for v in color),1);brick.inputs['Mortar'].default_value=(.30,.265,.20,1);mat['siteDetail']=True
 if key=='glass':shader.inputs['Roughness'].default_value=.19
 # Assign copies only to exterior slots, preserving any interior or other user of the source.
 owners=[]
 for obj in list(collection.all_objects):
  if obj.type!='MESH':continue
  for index,slot in enumerate(obj.data.materials):
   if slot==source:obj.data.materials[index]=mat;owners.append(obj.name)
 assert owners,key
 palette[key]={'material':mat.name,'color':list(color),'owners':owners};materials[key]=mat
old=bpy.data.objects['LAK_D5_fine_vertical_bar_frame'];old.hide_render=True;old.hide_set(True)
old_horizontal=bpy.data.objects['LAK_D5_fine_horizontal_bar_frame'];old_horizontal.hide_render=True;old_horizontal.hide_set(True)
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='LAK');groups={};centres=[]
for index,wall in enumerate(profile['walls'][:2]):
 facade=Facade(profile,wall,groups);bays=3 if index==0 else 7;pitch=facade.length/bays;width=1.55 if index==0 else 1.50
 for lo,hi in [(4.85,8.12),(9.12,11.20),(12.10,14.40)]:
  for j in range(bays):
   x=(j+.5)*pitch;centres.append({'wall':index,'x':x,'width':width,'low':lo,'high':hi,'rows':6 if lo==4.85 else 4})
   for fraction in [-1/6,1/6]:facade.box('sash59_vertical_bar','frame',x+width*fraction,(lo+hi)/2,.024,hi-lo,.07,.035)
   for fraction in ([1/6,2/6,4/6,5/6] if lo==4.85 else [.25,.75]):facade.box('sash59_horizontal_bar','frame',x,lo+(hi-lo)*fraction,width,.024,.07,.037)
for g in groups.values():
 obj=g.finish()
 # Joinery width is only 24mm. A 12mm bevel would consume the entire bar.
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
assert protected()==before,'Other buildings or interiors changed'
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage58'/filename).read_bytes())
audit={'version':59,'baseline':58,'protectedGeometryBefore':before,'protectedGeometryAfter':protected(),'hiddenOldMesh':old.name,'oldBars':len(old.data.vertices)//8,'newBars':60,'newHorizontalBars':80,'oldHorizontalMesh':old_horizontal.name,'sashWindows':centres,'columns':3,'rowsByStorey':[6,4,4],'palette':palette,'references':['data/建筑图片/LAK_Lakatos Building/01_建筑实拍/exteriors_lse_estate_010.jpg','data/建筑图片/LAK_Lakatos Building/01_建筑实拍/small_buildings_round3_small3_008.webp'],'limitations':['Photographs are undated and colors are estimated, not calibrated','Existing window positions and bay counts remain estimated','Roof, historical pediment position, unseen elevations and complete interiors remain unresolved']}
(OUT/'lakatos-sash-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v59.blend'));print('LAKATOS_SASH_SAVED',audit['oldBars'],audit['newBars'])
