"""Refine 51L's photographed corner pediment and first upper window.
Run in Blender Text Editor. Preserve native56, GIS chamfer and other buildings.
"""
from pathlib import Path
import bpy,bmesh,json,math,hashlib,array,sys
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage57';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v56.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
profile=next(p for p in json.loads((ROOT/'result/blender/stage05/infill-geometry.json').read_text())if p['code']=='51L');wall=profile['walls'][2]
a=Vector((*wall['p'],0));right=Vector(((wall['q'][0]-wall['p'][0])/wall['length'],(wall['q'][1]-wall['p'][1])/wall['length'],0));outward=Vector((*wall['outward'],0));center=wall['length']/2
floor=profile['height']/profile['floors'];lo=floor+.82;hi=2*floor-.62;width=wall['length']*.58
collection=bpy.data.collections['51L_EXTERIOR']
def digest(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 return h.hexdigest()
before={obj.name:digest(obj)for obj in bpy.data.objects}
def point(x,d,z):return a+right*x+outward*d+Vector((0,0,z))
def local(p):
 v=p-a;return Vector((v.dot(right),v.dot(outward),v.z))
hidden=[];removed={}
for obj in list(collection.all_objects):
 if any(key in obj.name for key in ['segmental_pediment','pediment_tympanum','pediment_keystone','portal_entablature']):
  obj.hide_render=True;obj.hide_set(True);hidden.append(obj.name);continue
 if obj.type!='MESH' or obj.hide_render:continue
 keys=['sash_verticals','sash_rails','corner_quoins','stone_lintels']
 if not any(key in obj.name for key in keys):continue
 bm=bmesh.new();bm.from_mesh(obj.data);faces=[]
 if 'corner_quoins' in obj.name:
  seen=set()
  for seed in list(bm.verts):
   if seed in seen:continue
   stack=[seed];component=[];seen.add(seed)
   while stack:
    v=stack.pop();component.append(v)
    for edge in v.link_edges:
     other=edge.other_vert(v)
     if other not in seen:seen.add(other);stack.append(other)
   pts=[local(obj.matrix_world@v.co)for v in component];mid=sum(pts,Vector())/len(pts)
   if -.85<mid.x<wall['length']+.85 and abs(mid.y)<.90 and floor+.03<mid.z<2*floor-.01:faces.extend({f for v in component for f in v.link_faces})
 for face in bm.faces:
  pts=[local(obj.matrix_world@v.co)for v in face.verts]
  if not all(-.15<p.x<wall['length']+.15 and -.30<p.y<.32 and floor+.03<p.z<2*floor-.01 for p in pts):continue
  if 'corner_quoins' in obj.name:continue
  if 'stone_lintels' in obj.name:faces.append(face)
  elif 'sash_verticals' in obj.name and all(abs(p.x-center)<.04 for p in pts):faces.append(face)
  elif 'sash_rails' in obj.name and all(abs(p.z-(lo+hi)/2)<.04 for p in pts):faces.append(face)
 if faces:removed[obj.name]=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data);obj.data.update()
 bm.free()
materials.clear()
for key,color in {'stone':(.64,.63,.59),'frame':(.73,.73,.69),'dark':(.032,.037,.034)}.items():
 mat=bpy.data.materials.new('51L_V57_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1);shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.77;materials[key]=mat
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('51L','corner57_'+key,key)
 return batches[key]
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(right.y,right.x))
box('stone',center,.065,3.13,wall['length']+.12,.48,.22)
# A filled shallow segmental pediment, with a projecting curved stone cornice.
half=1.03;spring=3.24;rise=.48
samples=[(-half+2*half*i/32,spring+rise*(1-((-half+2*half*i/32)/half)**2))for i in range(33)]
outline=[(-half,3.20),(half,3.20)]+list(reversed(samples));count=len(outline)
vertices=[point(center+x,d,z)for d in [-.08,.20]for x,z in outline]
batch('stone').add(vertices,[tuple(reversed(range(count))),tuple(range(count,2*count))]+[(i,(i+1)%count,(i+1)%count+count,i+count)for i in range(count)])
for (x0,z0),(x1,z1) in zip(samples,samples[1:]):
 vs=[point(center+x,d,z)for d in [.16,.28]for x,z in [(x0,z0),(x1,z1),(x1,z1+.055),(x0,z0+.055)]]
 batch('stone').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
# The photographed corner sash has three columns and a finer row grid.
for offset in [-width/6,width/6]:box('frame',center+offset,.015,(lo+hi)/2,.032,.10,hi-lo)
for i in [1,2]:box('frame',center,.015,lo+(hi-lo)*i/3,width,.10,.030)
for side in [-1,1]:
 for i in range(5):
  z=lo+(hi-lo)*(i+.5)/5;box('stone',center+side*(width/2+.145),.06,z,.30 if i%2 else .38,.21,(hi-lo)/5-.016)
box('stone',center,.075,hi+.10,width+.38,.31,.16)
# Shallow tapered centre key above the sash, visible in the estate photograph.
outline=[(-.11,hi+.02),(.11,hi+.02),(.19,hi+.43),(-.19,hi+.43)];count=len(outline)
vs=[point(center+x,d,z)for d in [.05,.21]for x,z in outline]
batch('stone').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
added=[]
for key,g in batches.items():
 obj=g.finish();added.append(obj.name)
 # Coplanar construction strips form one cornice, not separately bevelled tiles.
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
# Entrance name board is visually separate from the stone cornice.
box('dark',center,-.015,2.93,1.46,.08,.18)
curve=bpy.data.curves.new('51L_V57_Entry_name','FONT');curve.body="51 Lincoln's Inn Fields";curve.size=.075;curve.align_x='CENTER';curve.extrude=.001;curve.materials.append(materials['frame'])
label=bpy.data.objects.new(curve.name,curve);collection.objects.link(label);label.location=point(center,.03,2.91);label.rotation_euler=Matrix((Vector((0,0,1)).cross(outward),Vector((0,0,1)),outward)).transposed().to_euler()
# Finish the name-board batch created after the masonry batches.
obj=batches['dark'].finish()
for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
added.extend([obj.name,label.name])
changed=[name for name,prior in before.items()if digest(bpy.data.objects[name])!=prior]
assert all(name.startswith('51L_')for name in changed),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage56'/filename).read_bytes())
audit={'version':57,'baseline':56,'changedExistingObjects':changed,'changedOtherObjects':[name for name in changed if not name.startswith('51L_')],'hiddenPreviousObjects':hidden,'removedOldFaces':removed,'addedObjects':added,'pedimentSamples':samples,'windowColumns':3,'windowRows':3,'chamferEdge':2,'labelBasisDeterminant':Matrix((Vector((0,0,1)).cross(outward),Vector((0,0,1)),outward)).transposed().determinant(),'reference':'data/建筑图片/51L_51 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_015.jpg','limitations':['Undated estate photograph, tree obscures upper facade','Corner details are photo guided; dimensions estimated, not surveyed','Upper quoins, unseen elevations, roof and interior remain unverified']}
(OUT/'lincolns-corner-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v57.blend'));print('51L_CORNER_SAVED',len(changed),len(hidden))
