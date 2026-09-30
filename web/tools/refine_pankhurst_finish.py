"""Photo-guided PAN/FAW facade finishes. Run in Blender Text Editor.
Close tiny head/sill air gaps and preserve other buildings; unseen faces remain estimates.
"""
from pathlib import Path
import bpy,json,hashlib,array
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage58';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v57.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def geometry_digest(exclude_towers=False):
 h=hashlib.sha256()
 for obj in sorted(bpy.data.objects,key=lambda o:o.name):
  if exclude_towers and obj.name.startswith(('PAN_D3_', 'FAW_D3_')):continue
  h.update(obj.name.encode());h.update(str([list(r)for r in obj.matrix_world]).encode())
  if obj.type=='MESH':
   h.update(array.array('f',[x for v in obj.data.vertices for x in v.co]).tobytes())
   h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 return h.hexdigest()
before=geometry_digest();outside_before=geometry_digest(True);changes=[];closed_heads=[]
for code in ['PAN','FAW']:
 collection=bpy.data.collections[code+'_EXTERIOR']
 # Original 65mm heads left 7.5mm/17.5mm air gaps to the aggregate bands.
 # Increase only their vertical extent; centres, widths and facade layout stay fixed.
 head=bpy.data.objects[code+'_D3_window_heads_and_sills']
 assert len(head.data.vertices)%8==0
 for start in range(0,len(head.data.vertices),8):
  vertices=list(head.data.vertices)[start:start+8];center=sum(v.co.z for v in vertices)/8
  for vertex in vertices:vertex.co.z=center+(vertex.co.z-center)*(.11/.065)
 head.data.update();closed_heads.append(head.name)
 used={m for obj in collection.all_objects if obj.type=='MESH' for m in obj.data.materials if m}
 for key,color,rough,metal,opacity in [
  ('aggregate',(.49,.465,.405),.84,0,None),
  ('frame',(.58,.57,.52),.36,.32,None),
  ('glass',(.31,.36,.36),.18,0,.76),
  ('clear_glass',(.43,.48,.46),.16,0,.56),
 ]:
  mat=bpy.data.materials.get(code+'_D3_'+key);assert mat in used,(code,key)
  # The exterior owns these materials; do not recolor an interior through a shared slot.
  owners=[obj.name for obj in bpy.data.objects if obj.type=='MESH' and mat in obj.data.materials[:]]
  assert all(name.startswith(code+'_D3_') for name in owners),owners
  mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF']
  shader.inputs['Base Color'].default_value=mat.diffuse_color
  shader.inputs['Roughness'].default_value=rough;shader.inputs['Metallic'].default_value=metal
  if opacity is not None:mat['webOpacity']=opacity
  if key=='aggregate':
   ramp=next(n for n in mat.node_tree.nodes if n.type=='VALTORGB')
   ramp.color_ramp.elements[0].color=(.40,.375,.32,1)
   ramp.color_ramp.elements[-1].color=(.58,.555,.49,1)
   bump=next(n for n in mat.node_tree.nodes if n.type=='BUMP')
   bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.006
   mat['siteDetail']=True
  changes.append({'material':mat.name,'color':list(color),'roughness':rough,'metallic':metal,'webOpacity':opacity,'owners':owners})
 # Curtains are not aluminium sheets. Give only the blind mesh an independent finish.
 blind=bpy.data.objects[code+'_D3_selected_internal_blinds']
 curtain=bpy.data.materials.new(code+'_V58_curtain');curtain.use_nodes=True;curtain.diffuse_color=(.58,.56,.50,1)
 shader=curtain.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=curtain.diffuse_color;shader.inputs['Roughness'].default_value=.94
 blind.data.materials.clear();blind.data.materials.append(curtain)
 changes.append({'material':curtain.name,'color':list(curtain.diffuse_color[:3]),'roughness':.94,'metallic':0,'webOpacity':None,'owners':[blind.name]})
after=geometry_digest();outside_after=geometry_digest(True);assert outside_before==outside_after,'Non-tower geometry changed'
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage57'/filename).read_bytes())
audit={'version':58,'baseline':57,'geometryBefore':before,'geometryAfter':after,'outsideGeometryBefore':outside_before,'outsideGeometryAfter':outside_after,'closedHeadMeshes':closed_heads,'headHeightBefore':.065,'headHeightAfter':.11,'changes':changes,'reference':'data/建筑图片/PAN_Pankhurst House/01_建筑实拍/exteriors_lse_estate_007.jpg','limitations':['Undated entrance photograph; warm aggregate and pale metal finish photo guided, not calibrated colors','FAW shares the facade finish family; independent elevations are not verified','Existing roof, upper massing and interiors are unchanged and remain incomplete']}
(OUT/'pankhurst-finish-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v58.blend'))
print('PANKHURST_FINISH_SAVED',len(changes))
