"""Photo guided 5LF ground segmental arches and yellow stock brick.
Run in Blender Text Editor. Native54 retained; dimensions remain estimates.
"""
from pathlib import Path
import bpy,bmesh,json,math,hashlib,array,sys
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage55';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v54.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def digest(obj):
 h=hashlib.sha256(str([list(row)for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  h.update(array.array('f',[c for v in obj.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in obj.data.loops]).tobytes())
 return h.hexdigest()
before={o.name:digest(o)for o in bpy.data.objects}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());building=next(b for b in site['buildings']if b['id']=='way/1184094775');ring=building['rings'][0]
a,b=Vector((*ring[1],0)),Vector((*ring[2],0));u=(b-a).normalized();n=Vector((u.y,-u.x,0));length=(b-a).length
if n.dot((a+b)/2-Vector((*building['center'],0)))<0:n=-n
collection=bpy.data.collections['5LF_EXTERIOR'];removed={}
# Remove the superseded rectangular opening members, retaining the forecourt.
for obj in list(collection.all_objects):
 if obj.type!='MESH' or obj.hide_render:continue
 if not any(obj.name.startswith('5LF_D5_'+key+'_')for key in ['pier','spandrel','head','glass','jamb','horizontal_rail','sash_vertical','sill','door','door_panel','door_handle','ground_rustication']):continue
 bm=bmesh.new();bm.from_mesh(obj.data)
 faces=[face for face in bm.faces if all((obj.matrix_world@v.co).z<4.31 for v in face.verts)]
 if faces:
  removed[obj.name]=len(faces);bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(obj.data);obj.data.update()
 bm.free()
# Retain the existing procedural brick UVs; adjust only 5LF material endpoints.
brick=bpy.data.materials['5LF_brick'];shader=brick.node_tree.nodes['Principled BSDF'];brick.diffuse_color=(.43,.335,.18,1);shader.inputs['Base Color'].default_value=brick.diffuse_color
for node in brick.node_tree.nodes:
 if node.type=='TEX_BRICK':
  node.inputs['Color1'].default_value=(.43,.335,.18,1);node.inputs['Color2'].default_value=(.32,.25,.14,1);node.inputs['Mortar'].default_value=(.26,.25,.21,1)
materials.clear()
for key,color in {'plaster':(.74,.74,.70),'frame':(.69,.71,.70),'glass':(.085,.14,.17),'door':(.018,.022,.020),'mortar':(.32,.34,.33),'brass':(.40,.29,.10)}.items():
 mat=bpy.data.materials.new('5LF_V55_'+key);mat.use_nodes=True;mat.diffuse_color=(*color,1)
 shader=mat.node_tree.nodes['Principled BSDF'];shader.inputs['Base Color'].default_value=mat.diffuse_color;shader.inputs['Roughness'].default_value=.30 if key=='glass'else .74
 if key=='glass':shader.inputs['Metallic'].default_value=.24
 materials[key]=mat
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('5LF','segmental_'+key,key)
 return batches[key]
def point(x,d,z):return a+u*x+n*d+Vector((0,0,z))
def box(key,x,d,z,w,t,h):batch(key).box(point(x,d,z),(w,t,h),math.atan2(u.y,u.x))
def profile(x):return 3.25+.25*(1-(x/.615)**2)
def wall_strip(x0,x1,z0,z1):
 vs=[point(x,d,z)for d in [-.26,.02]for x,z in [(x0,z0),(x1,z1),(x1,4.21),(x0,4.21)]]
 batch('plaster').add(vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
pitch=length/3;width=1.23;lo=.90;arch_samples=[]
for bay in range(3):
 x=(bay+.5)*pitch;left=x-width/2;right=x+width/2;door=bay==2
 box('plaster',x,-.12,.44,pitch,.28,.88)
 for side in [-1,1]:box('plaster',x+side*(pitch+width)/4,-.12,2.54,(pitch-width)/2,.28,3.33)
 # Shallow parabolic segment is a photo approximation, not a semicircle.
 outline=[(left,lo),(right,lo)]+[(right-width*j/24,profile(width/2-width*j/24))for j in range(25)]
 key='door'if door else'glass';vs=[point(px,d,pz)for d in [-.16,-.12]for px,pz in outline];count=len(outline)
 faces=[tuple(reversed(range(count))),tuple(range(count,2*count))]+[(j,(j+1)%count,(j+1)%count+count,j+count)for j in range(count)]
 batch(key).add(vs,faces)
 for j in range(24):
  x0=-width/2+width*j/24;x1=-width/2+width*(j+1)/24;z0,z1=profile(x0),profile(x1)
  wall_strip(x+x0,x+x1,z0,z1)
  # Construct the curved head frame independently from the wall infill.
  verts=[point(px,d,pz)for d in [-.025,.045]for px,pz in [(x+x0,z0),(x+x1,z1),(x+x1,z1+.055),(x+x0,z0+.055)]]
  batch('door'if door else'frame').add(verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
 for sx in [-1,1]:box('door'if door else'frame',x+sx*width/2,.005,2.075,.06,.10,2.35)
 if door:
  for z in [1.25,1.90,2.52]:box('door',x,-.065,z,.87,.055,.48)
  box('brass',x-.36,.04,1.82,.045,.07,.18)
  box('door',x,.015,3.08,width,.09,.07)
 else:
  for z in [lo,2.16]:box('frame',x,.015,z,width,.10,.06)
  box('frame',x,.015,2.20,.036,.08,2.60)
  box('plaster',x,.04,.835,width+.18,.37,.13)
 arch_samples.append({'bay':bay,'spring':profile(width/2),'crown':profile(0),'width':width,'segments':24})
# Plaster coursing terminates beside actual openings instead of crossing glass.
for z in [1.15,1.80,2.45,3.10,3.75]:
 spans=[(0,pitch*.5-width/2)]
 for bay in range(2):spans.append((pitch*(bay+.5)+width/2,pitch*(bay+1.5)-width/2))
 spans.append((pitch*2.5+width/2,length))
 if z>3.5:spans=[(0,length)]
 for left,right in spans:box('mortar',(left+right)/2,.024,z,right-left,.01,.011)
added=[]
for g in batches.values():
 obj=g.finish()
 # Construction strips form one continuous wall/head, not separate chamfered tiles.
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 added.append(obj.name)
observed={}
for key in ['glass','door']:
 obj=bpy.data.objects['5LF_D5_segmental_'+key]
 heights=sorted({round((obj.matrix_world@v.co).z,3)for v in obj.data.vertices if (obj.matrix_world@v.co).z>=3.249})
 assert len(heights)>=10 and max(heights)==(3.5 if key=='glass'else 3.555),(key,heights)
 observed[key]=heights
changed=[name for name,prior in before.items()if digest(bpy.data.objects[name])!=prior]
assert changed and all(name.startswith('5LF_')for name in changed),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage54'/filename).read_bytes())
result={'version':55,'baseline':54,'changedExistingObjects':changed,'changedOtherObjects':[name for name in changed if not name.startswith('5LF_')],'removedRectangularFaces':removed,'arches':arch_samples,'savedArchHeights':observed,'addedObjects':added,'brickColor1':[.43,.335,.18],'brickColor2':[.32,.25,.14],'source':'data/建筑图片/5LF_5 Lincoln_s Inn Fields/01_建筑实拍/exteriors_lse_estate_012.jpg','limitations':['Estate exterior photo is undated; facade dimensions estimated','Segmental crown approximated from the photographed frontage','Roof behind parapet and other elevations remain unverified; interiors unchanged']}
(OUT/'five-lincolns-frontage-audit.json').write_text(json.dumps(result,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v55.blend'));print('5LF_SAVED',len(changed),len(added))
