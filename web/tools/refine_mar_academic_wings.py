"""Rebuild five MAR academic-wing facades and lighten exterior precast concrete.
Run in Blender Text Editor after prepare_mar_fenestration.py. Photo estimates.
"""
from pathlib import Path
import array,hashlib,json,math,sys
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage75'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v74.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
D=json.loads((OUT/'mar-fenestration.json').read_text());col=bpy.data.collections['MAR_EXTERIOR']
def digest(o):
 h=hashlib.sha256(str([list(row) for row in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:digest(o) for o in bpy.data.objects};owned={o.name for o in col.all_objects}
materials.clear()
for key,color,rough,metal in [('concrete',(.69,.67,.625),.85,0),('glass',(.17,.235,.265),.20,.12),('joinery',(.29,.275,.235),.4,.45),('joint',(.33,.32,.29),.8,0)]:
 m=bpy.data.materials.new('MAR_V75_'+key);m.use_nodes=True;m.diffuse_color=(*color,1);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
# Isolate material slots: interior floor and structural concrete retain their own finish.
recolored=[]
for o in list(col.all_objects):
 if o.type!='MESH' or o.hide_render:continue
 touched=False
 for i,m in enumerate(o.data.materials):
  if m and 'concrete_palette26_MAR' in m.name:
   o.data.materials[i]=materials['concrete'];touched=True
 if touched:recolored.append(o.name)
frames=[]
for s in D['surfaces']:
 p,q=Vector((*s['p'],0)),Vector((*s['q'],0));axis=(q-p).normalized();normal=Vector((axis.y,-axis.x,0));mid=(p+q)/2;centre=Vector((*D['mar_center'],0))
 if (mid-centre).dot(normal)<0:normal=-normal
 frames.append((s,p,axis,normal))
def belongs(points):
 for s,p,u,n in frames:
  local=[((v-p).dot(u),(v-p).dot(n),v.z) for v in points]
  if not all(-.65<d<.35 for x,d,z in local):continue
  for a,b,c,d in s['oldOpenings']:
   if all(a-.18<x<c+.18 and b-.18<z<d+.18 for x,depth,z in local):return True
 return False
removed={}
for o in list(col.all_objects):
 if o.type!='MESH' or o.hide_render or not any(k in o.name.lower() for k in ['window','sill','gasket']):continue
 mesh=bmesh.new();mesh.from_mesh(o.data);seen=set();delete=[];count=0
 for v in list(mesh.verts):
  if v in seen:continue
  stack=[v];seen.add(v);component=[]
  while stack:
   a=stack.pop();component.append(a)
   for e in a.link_edges:
    b=e.other_vert(a)
    if b not in seen:seen.add(b);stack.append(b)
  if belongs([o.matrix_world@v.co for v in component]):delete.extend(component);count+=1
 if delete:
  bmesh.ops.delete(mesh,geom=delete,context='VERTS');mesh.to_mesh(o.data);o.data.update();removed[o.name]=count
 mesh.free()
assert removed.get('MAR_recessed_window_glass',0)>200,removed
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('MAR','wings75_'+key,key)
 return batches[key]
window_count=0;hidden=[]
for s,p,u,n in frames:
 old=bpy.data.objects['MAR_'+s['name']+'_pierced_wall'];old.hide_render=True;old.hide_set(True);hidden.append(old.name)
 def point(x,z,d=0):return p+u*x+n*d+Vector((0,0,z))
 for tri in s['triangles']:
  vs=[point(x,z) for x,z in tri]
  if (vs[1]-vs[0]).cross(vs[-1]-vs[0]).dot(n)<0:vs.reverse()
  batch('concrete').add(vs,[(0,1,2)])
 for ring in s['rings']:
  for a,b in zip(ring,ring[1:]+ring[:1]):batch('concrete').add([point(*a),point(*b),point(*b,-.40),point(*a,-.40)],[(0,1,2,3)])
 angle=math.atan2(u.y,u.x)
 def box(key,x,z,w,h,d,t):batch(key).box(point(x,z,d),(w,t,h),angle)
 for a,b,c,d in s['openings']:
  x,z=(a+c)/2,(b+d)/2;w,h=c-a,d-b
  box('glass',x,z,w-.06,h-.06,-.42,.025)
  for xx in [a,c]:box('joinery',xx,z,.05,h,-.39,.08)
  for zz in [b,d,d-.72]:box('joinery',x,zz,w,.05,-.39,.08)
  box('joinery',x,z,.042,h,-.39,.08)
  box('concrete',x,b-.075,w+.20,.15,-.02,.55)
  # Projected slender concrete sides and horizontal floor edges form the photographed grid.
  for xx in [a-.11,c+.11]:box('concrete',xx,z,.16,h+.30,.15,.38)
  box('concrete',x,d+.10,w+.38,.20,.15,.38)
  window_count+=1
added=[]
for key,g in batches.items():
 o=g.finish();added.append(o.name)
 for mod in list(o.modifiers):o.modifiers.remove(mod)
changed=[n for n,v in before.items() if digest(bpy.data.objects[n])!=v]
assert all(n in owned for n in changed),changed
for filename in ['room-studies.json','room-spaces.json','building-review.json']:(OUT/filename).write_bytes((ROOT/'result/blender/stage74'/filename).read_bytes())
audit={'version':75,'baseline':74,'windowCount':window_count,'surfaceCount':len(frames),'addedObjects':added,'hiddenPreviousObjects':hidden,'removedWindowComponents':removed,'recoloredObjects':recolored,'changedExistingObjects':changed,'reference':'Nick Kane MAR photographs 05 and 07, photographer project portfolio; 2022 upload paths, capture date unknown','referenceUrl':'https://nickkane.co.uk/portfolio_page/marshall-building-lse-london-grafton-architects/','limitations':['GIS footprint, previous floor heights and window centre positions retained; aperture dimensions and projecting profiles photo-estimated','Five academic-wing faces inferred from photographed courtyard and end elevations; hidden elevations and rear massing require further review','Interior structure and recent fire-safety works unchanged']}
(OUT/'mar-academic-wings-audit.json').write_text(json.dumps(audit,indent=2)+'\n');bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v75.blend'));print('MAR_ACADEMIC_WINGS_SAVED',window_count,removed)
