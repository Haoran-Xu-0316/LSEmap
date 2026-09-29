"""Separate CON's photographed lower granite from upper limestone.

The 3.12 m material transition is estimated against the existing door/transom,
not a survey. Work is restricted to the modelled street facade and portal.
"""
from pathlib import Path
import array,hashlib,json,shutil
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage30';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v29.blend'))
def geometry(o):
 v=array.array('f',[0])*(3*len(o.data.vertices));o.data.vertices.foreach_get('co',v)
 i=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',i)
 return hashlib.sha256(v.tobytes()+i.tobytes()).hexdigest()
before={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
granite=bpy.data.materials.new('CON_V30_fine_grey_granite');granite.use_nodes=True;granite.diffuse_color=(.40,.415,.425,1)
n=granite.node_tree.nodes;l=granite.node_tree.links;p=n.get('Principled BSDF');p.inputs['Base Color'].default_value=granite.diffuse_color;p.inputs['Roughness'].default_value=.76
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=90
ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.32,.335,.35,1);ramp.color_ramp.elements[1].color=(.48,.495,.51,1)
l.new(noise.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],p.inputs['Base Color'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.0015;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
parts=['stone_wall_piers','stone_spandrels','window_reveals','portal_piers','projecting_sills','sill_drip_edges','rustication_recesses']
changes=[];height=3.12
for part in parts:
 o=bpy.data.objects['CON_D4_'+part];bm=bmesh.new();bm.from_mesh(o.data)
 local=o.matrix_world.inverted()@Vector((0,0,height));normal=o.matrix_world.to_3x3().transposed()@Vector((0,0,1))
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=local,plane_no=normal,dist=1e-6)
 lower=[f for f in bm.faces if (o.matrix_world@f.calc_center_median()).z<height-1e-6]
 if part=='rustication_recesses':
  bmesh.ops.delete(bm,geom=lower,context='FACES')
 else:
  o.data.materials.append(granite);index=len(o.data.materials)-1
  if part=='portal_piers':
   o.data.materials.append(bpy.data.materials['STREET_D4_limestone'])
   for f in bm.faces:f.material_index=len(o.data.materials)-1
  for f in lower:f.material_index=index
 bm.to_mesh(o.data);bm.free();o.data.update()
 changes.append({'object':o.name,'lowerFaces':len(lower),'action':'remove lower ashlar grooves' if part=='rustication_recesses' else 'separate granite and limestone'})
after={o.name:geometry(o) for o in bpy.data.objects if o.type=='MESH'}
changed=[name for name in before if before[name]!=after[name]]
assert set(changed)<=set('CON_D4_'+p for p in parts)
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage29'/name,OUT/name)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v30.blend'))
(OUT/'connaught-base-audit.json').write_text(json.dumps({'evidence':'data/collections/exteriors/images/lse_estate_005.jpg','transitionHeightEstimate':height,'changes':changes,'geometryChanged':changed,'unchangedMeshes':len(before)-len(changed),'scope':'Street facade only; material transition estimated. Other elevations and full interior not verified.'},indent=2)+'\n')
print('CON_BASE_COMPLETE',len(changes),'objects')
