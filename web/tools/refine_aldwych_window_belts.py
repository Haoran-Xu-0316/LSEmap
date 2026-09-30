"""Restore continuous three-storey window belts seen in the built 61A photo.
Run in Blender Text Editor. Bay positions and overall dimensions remain estimated.
"""
from pathlib import Path
import bpy,bmesh,json,sys,hashlib,array
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage64';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,Facade,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v63.blend'));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];col=bpy.data.collections['61A_EXTERIOR']
def digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects};profile=json.loads((ROOT/'result/blender/stage07/aldwych-geometry.json').read_text());walls=[w for w in profile['walls']if w['street'] and w!=profile['front']];removed={}
def on_wall(c,axis):
 for w in walls:
  p=Vector((*w['p'],0));u=Vector(((w['q'][0]-w['p'][0])/w['length'],(w['q'][1]-w['p'][1])/w['length'],0));n=Vector((*w['outward'],0));d=c-p
  if abs(axis.dot(u))>.99999 and -.01<d.dot(u)<w['length']+.01 and -.5<d.dot(n)<.6:return True
 return False
names=['61A_D5_'+k for k in ['sill_wall_stone','head_wall_stone','window_piers_stone','projecting_sill_trim','giant_pilaster_trim']]
for name in names:
 o=bpy.data.objects[name];bm=bmesh.new();bm.from_mesh(o.data);seen=set();delete=[];count=0
 for v in list(bm.verts):
  if v in seen:continue
  stack=[v];component=[];seen.add(v)
  while stack:
   q=stack.pop();component.append(q)
   for e in q.link_edges:
    r=e.other_vert(q)
    if r not in seen:seen.add(r);stack.append(r)
  component=sorted(component,key=lambda q:q.index);points=[o.matrix_world@q.co for q in component];c=sum(points,Vector())/len(points);assert len(points)==8;axis=(points[4]-points[0]).normalized()
  if 7.75<c.z<18.61 and min(q.z for q in points)>7.69 and max(q.z for q in points)<18.71 and on_wall(c,axis):delete.extend(component);count+=1
 if delete:bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(o.data);o.data.update()
 bm.free();removed[name]=count
assert all(removed.values()),removed
materials.clear();materials['stone']=bpy.data.materials['61A_stone'];materials['trim']=bpy.data.materials['61A_trim']
m=bpy.data.materials.new('61A_V64_spandrel');m.use_nodes=True;m.diffuse_color=(.09,.10,.10,1);s=m.node_tree.nodes['Principled BSDF'];s.inputs['Base Color'].default_value=m.diffuse_color;s.inputs['Roughness'].default_value=.39;s.inputs['Metallic'].default_value=.45;materials['spandrel']=m;materials['shadow']=bpy.data.materials['61A_shadow'];groups={};belts=[]
for w in walls:
 f=Facade(profile,w,groups);count=max(1,round(w['length']/3.3));pitch=w['length']/count;width=pitch*.74
 for j in range(count):
  x=(j+.5)*pitch
  for side in [-1,1]:f.box('belt64_continuous_pier','stone',x+side*(pitch+width)/4,13.2,(pitch-width)/2,10.8,.46,-.15)
  # Fill only the recessed opening between retained glazing lights with metal.
  for lo,hi in [(7.8,8.45),(10.92,12.05),(14.52,15.65),(18.12,18.6)]:f.box('belt64_metal_spandrel','spandrel',x,(lo+hi)/2,width,hi-lo,.07,-.24)
  for z in [8.45,12.05,15.65]:f.box('belt64_metal_sill','spandrel',x,z-.04,width+.04,.07,.19,-.09)
  f.box('belt64_continuous_pilaster','trim',j*pitch,13.2,.40,10.8,.65,.08)
  belts.append({'wall':profile['walls'].index(w),'x':x,'pitch':pitch,'width':width,'bottom':7.8,'top':18.6})
# Stone joints belong to masonry; never draw them across a recessed window.
old_joint=bpy.data.objects['61A_D5_stone_joint_shadow'];old_joint.hide_render=True;old_joint.hide_set(True)
levels=[0,4.2,7.8,11.4,15,18.6,22.2,25.8,29.4];joint_segments=[]
for w in [w for w in profile['walls']if w['street']]:
 f=Facade(profile,w,groups);count=max(1,round(w['length']/3.3));pitch=w['length']/count
 for z in [5.7,7.6,19.5,20.4,21.3,23.2,24.2,28.4]:
  floor=next(i for i in range(8)if levels[i]<=z<levels[i+1]);lo,hi=levels[floor]+.65,levels[floor+1]-.48;width=pitch*(.74 if 1<floor<5 else .58)
  for j in range(count):
   x=(j+.5)*pitch;spans=[(j*pitch,x-width/2),(x+width/2,(j+1)*pitch)]if lo<z<hi else[(j*pitch,(j+1)*pitch)]
   for a,b in spans:
    f.box('belt64_clipped_stone_joint','shadow',(a+b)/2,z,b-a,.014,.018,.089);joint_segments.append({'wall':profile['walls'].index(w),'height':z,'start':a,'end':b,'windowLow':lo,'windowHigh':hi,'windowLeft':x-width/2,'windowRight':x+width/2})
for g in groups.values():
 o=g.finish()
 for modifier in list(o.modifiers):o.modifiers.remove(modifier)
changed=[o.name for o in bpy.data.objects if o.name in before and digest(o)!=before[o.name]];assert set(changed)==set(names),changed
for name in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/name).write_bytes((ROOT/'result/blender/stage63'/name).read_bytes())
a={'version':64,'baseline':63,'changedExistingGeometry':changed,'removedMembers':removed,'belts':belts,'clippedJointSegments':joint_segments,'hiddenOldJoint':old_joint.name,'reference':'data/建筑图片/61A_61 Aldwych/01_建筑实拍/campus_photos_round2_61A_aldwych_survey_01.jpg','limitations':['Undated built-project photo; current site and LSE conversion not independently confirmed','Existing street bay counts, heights and glass dimensions preserved estimates','Corner portal, pavilion location, dormers and unseen elevations remain unresolved; interiors unchanged']};(OUT/'aldwych-belts-audit.json').write_text(json.dumps(a,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v64.blend'));print('ALDWYCH_BELTS_SAVED',len(belts),removed)
