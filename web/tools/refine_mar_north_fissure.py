"""Correct MAR's north fissure, screened roof terraces and window sequence.
Run in Blender Text Editor. Original geometry is retained in archived objects.
North heights, fissure depth and colour are photographic estimates, not a survey.
"""
from pathlib import Path
import array,hashlib,json,math,shutil,sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/stage115';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from facade_geometry import Geometry,materials
baseline=ROOT/'result/blender/LSE_campus_detailed_v114.blend'
if not baseline.exists():baseline=OUT/'mar/temporary-baseline.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(obj):
 h=hashlib.sha256(str([list(r)for r in obj.matrix_world]).encode())
 if obj.type=='MESH':
  v=array.array('f',[0])*(3*len(obj.data.vertices));i=array.array('i',[0])*len(obj.data.loops)
  obj.data.vertices.foreach_get('co',v);obj.data.loops.foreach_get('vertex_index',i);h.update(v.tobytes());h.update(i.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:o.hide_render for o in bpy.data.objects}
# Retained local basis is sufficient; stage02 is not needed to rebuild MAR.
cx,cy=-8.696325894899289,49.33154396120258;angle=math.radians(22)
u=Vector((math.cos(angle),math.sin(angle),0));n=Vector((-math.sin(angle),math.cos(angle),0));origin=Vector((cx,cy,0))
def local(p):return Vector(((p-origin).dot(u),(p-origin).dot(n),p.z))
def point(x,y,z):return origin+u*x+n*y+Vector((0,0,z))
# The measured fin dimensions are independent of the estimated terrace datum.
roof_level=32.85
fissure=[(-15.2,21.16),(-15.2,8.8),(-8.5,3.5),(-2,16),(-2,21.16)]
def prism(polygon,low,high):
 planes=[]
 for a,b in zip(polygon,polygon[1:]+polygon[:1]):
  normal=Vector((a[1]-b[1],b[0]-a[0],0));planes.append((normal,-normal.dot(Vector((*a,0)))))
 return planes+[(Vector((0,0,1)),-low),(Vector((0,0,-1)),high)]
def rectangle(a,b,c,d):return [(a,b),(c,b),(c,d),(a,d)]
# The source return wall can be exactly coplanar with the estimated fissure.
# A small cutting clearance removes that old boundary behind the new windows.
void=[(normal,offset+(.06*normal.length if normal.z==0 else 0))
      for normal,offset in prism(fissure,12.801,45)]
front=prism(rectangle(-30.01,18.20,24.01,20.71),23.399,35.51)
roof_cut=prism(rectangle(-30.61,8.799,24.21,21.14),roof_level+.001,45)
# Split retained faces on the cut planes, carrying loop UVs with intersections.
# This works for open floor planes as well as solid trim; no Boolean fallback.
def split(poly,plane,inside=True):
 normal,offset=plane;sign=1 if inside else -1;out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  da=sign*(normal.dot(a[0])+offset);db=sign*(normal.dot(b[0])+offset)
  if da>=-1e-7:out.append(a)
  if (da>1e-7 and db<-1e-7)or(da<-1e-7 and db>1e-7):
   t=da/(da-db);out.append((a[0].lerp(b[0],t),[x.lerp(y,t)for x,y in zip(a[1],b[1])]))
 return out if len(out)>=3 else []
def subtract(poly,planes):
 # A whole polygon outside one half-space cannot intersect this prism.
 # Coplanar boundary faces are retained once, avoiding duplicate fragments.
 for normal,offset in planes:
  if max(normal.dot(vertex[0])+offset for vertex in poly)<=1e-7:return [poly]
 retained=[];working=poly
 for plane in planes:
  if not working:break
  normal,offset=plane
  distances=[normal.dot(vertex[0])+offset for vertex in working]
  if min(distances)>=-1e-7:continue
  outside=split(working,plane,False)
  if outside:retained.append(outside)
  working=split(working,plane,True)
 return retained
materials.clear()
for key,color,rough,metal in [('panel',(.78,.765,.725),.83,0),('fin',(.70,.685,.645),.80,0),
 ('glass',(.15,.215,.25),.18,.12),('frame',(.26,.25,.225),.40,.45),('roof',(.54,.525,.485),.86,0)]:
 m=bpy.data.materials.new('MAR_V115_'+key);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=m.node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;materials[key]=m
col=bpy.data.collections['MAR_EXTERIOR'];root=next(c for c in bpy.data.collections['02_LSE_BUILDINGS'].children if c.name.startswith('MAR_'))
# Upper floor planes in the public-interior collection also crossed the court.
# Include only those slab families; retained rooms and hall furniture stay intact.
owned=list({o for c in root.children if 'UNRESOLVED'not in c.name for o in c.all_objects
            if 'INTERIOR'not in c.name or o.name.startswith('MAR_MAR_floor_way/')})
added=[];archived=[];replacements=[]
def archive(obj):
 if obj.name not in archived:obj.hide_render=True;obj.hide_set(True);archived.append(obj.name)
def link_copy(obj):
 copy=obj.copy();copy.data=obj.data.copy();copy.name='MAR_V115_retained_'+obj.name.removeprefix('MAR_')
 for owner in obj.users_collection:owner.objects.link(copy)
 copy.hide_render=False;copy.hide_set(False);added.append(copy.name);archive(obj);return copy
obsolete={'MAR_D5_tapered_middle_blade','MAR_D5_screen_return_sill','MAR_D5_upper_fin_joint','MAR_D5_screen_corner_cap'}
for name in obsolete:archive(bpy.data.objects[name])
# Keep the 38 upper units intact, but assign their own lighter outer finish.
for name in ['MAR_D5_NEXT_upper_screen_shafts','MAR_D5_NEXT_upper_screen_hammerheads']:
 copy=link_copy(bpy.data.objects[name]);copy.data.materials.clear();copy.data.materials.append(materials['fin'])
for obj in owned:
 if obj.type!='MESH' or visibility[obj.name] or obj.name in archived:continue
 if 'north_screen_horizontal_edges' in obj.name:continue
 # Garden fixtures move with the corrected terrace, preserving their topology.
 if 'V25_terrace_'in obj.name and 'terrace_pavers'not in obj.name:
  copy=link_copy(obj)
  inverse=copy.matrix_world.inverted()
  for v in copy.data.vertices:v.co=inverse@(copy.matrix_world@v.co-Vector((0,0,1.98)))
  copy.data.update()
  replacements.append({'source':obj.name,'copy':copy.name,'mode':'terrace-shift'});continue
 inverse=obj.matrix_world.inverted()
 shifted_pavers='V25_terrace_pavers'in obj.name
 displacement=Vector((0,0,1.98))if shifted_pavers else Vector((0,0,0))
 points=[local(obj.matrix_world@v.co-displacement)for v in obj.data.vertices]
 if not points:continue
 if max(p.z for p in points)<12.801 or max(p.y for p in points)<3.49:continue
 layers=list(obj.data.uv_layers);new_faces=[];new_vertices=[];new_indices=[];new_uvs=[[]for l in layers];changed=shifted_pavers
 for face in obj.data.polygons:
  poly=[(points[obj.data.loops[i].vertex_index],[Vector(layer.data[i].uv)for layer in layers])for i in face.loop_indices]
  original_area=face.area;pieces=[poly]
  regions=[void]if shifted_pavers else [void,front,roof_cut]
  for region in regions:pieces=[part for p in pieces for part in subtract(p,region)]
  if len(pieces)!=1 or len(pieces[0])!=len(poly)or any((a[0]-b[0]).length>1e-5 for a,b in zip(pieces[0],poly))if pieces else True:changed=True
  for piece in pieces:
   # Reject collapsed fragments from numerically coincident original edges.
   cleaned=[]
   for v in piece:
    if not cleaned or (v[0]-cleaned[-1][0]).length>1e-6:cleaned.append(v)
   if len(cleaned)>2 and (cleaned[0][0]-cleaned[-1][0]).length<1e-6:cleaned.pop()
   if len(cleaned)<3:continue
   area=sum(((cleaned[i][0]-cleaned[0][0]).cross(cleaned[i+1][0]-cleaned[0][0])).length for i in range(1,len(cleaned)-1))/2
   if area<1e-8:continue
   offset=len(new_vertices);new_vertices.extend(inverse@point(*v[0])for v in cleaned)
   new_faces.append(tuple(range(offset,offset+len(cleaned))));new_indices.append(face.material_index)
   for j in range(len(layers)):new_uvs[j].extend(v[1][j]for v in cleaned)
 if not changed:continue
 copy=obj.copy();mesh=bpy.data.meshes.new(obj.data.name+'_north115');mesh.from_pydata(new_vertices,[],new_faces)
 for material in obj.data.materials:mesh.materials.append(material)
 for f,index in zip(mesh.polygons,new_indices):f.material_index=index
 for source,values in zip(layers,new_uvs):
  layer=mesh.uv_layers.new(name=source.name)
  for loop,value in zip(layer.data,values):loop.uv=value
  layer.active_render=source.active_render
 mesh.update();copy.data=mesh;copy.name='MAR_V115_retained_'+obj.name.removeprefix('MAR_')
 for owner in obj.users_collection:owner.objects.link(copy)
 copy.hide_render=False;copy.hide_set(False);added.append(copy.name);archive(obj)
 replacements.append({'source':obj.name,'copy':copy.name,'mode':'terrace-shift-and-fissure-trim'if shifted_pavers else 'fissure-and-roof-trim','beforeFaces':len(obj.data.polygons),'afterFaces':len(mesh.polygons)})
# Rebuild the upper faces around genuine openings and leave their roof screen open.
batches={}
def batch(key):
 if key not in batches:batches[key]=Geometry('MAR','north115_'+key,key)
 return batches[key]
def face(key,coords):batch(key).add([point(*p)for p in coords],[tuple(range(len(coords)))])
def box(key,x,y,z,w,d,h):batch(key).box(point(x,y,z),(w,d,h),angle)
window_probes=[]
def wall(a,b,columns,low=23.4,high=32.65):
 a,b=Vector(a),Vector(b);axis=(b-a).normalized();length=(b-a).length
 # Normal faces the exterior court/sky. Opening edges remain explicit geometry.
 normal=Vector((axis.y,-axis.x));cuts=[]
 for i in range(columns):
  x=(i+.5)*length/columns;w=min(1.45,length/columns-.5)
  for bottom,top in [(24.0,27.55),(28.65,32.20)]:cuts.append((x-w/2,bottom,x+w/2,top))
 xs=sorted({0,length,*[v for r in cuts for v in [r[0],r[2]]]});zs=sorted({low,high,*[v for r in cuts for v in [r[1],r[3]]]})
 def p(x,z,depth=0):
  xy=a+axis*x+normal*depth;return (xy.x,xy.y,z)
 for x0,x1 in zip(xs,xs[1:]):
  for z0,z1 in zip(zs,zs[1:]):
   if any(r[0]<(x0+x1)/2<r[2]and r[1]<(z0+z1)/2<r[3]for r in cuts):continue
   face('panel',[p(x0,z0),p(x1,z0),p(x1,z1),p(x0,z1)])
 for x0,z0,x1,z1 in cuts:
  face('glass',[p(x0+.04,z0+.04,-.12),p(x1-.04,z0+.04,-.12),p(x1-.04,z1-.04,-.12),p(x0+.04,z1-.04,-.12)])
  for x in [x0,x1]:face('frame',[p(x-.025,z0,-.09),p(x+.025,z0,-.09),p(x+.025,z1,-.09),p(x-.025,z1,-.09)])
  for z in [z0,z1]:face('frame',[p(x0,z-.025,-.09),p(x1,z-.025,-.09),p(x1,z+.025,-.09),p(x0,z+.025,-.09)])
  for z in [z0+(z1-z0)*.52]:face('frame',[p(x0,z-.018,-.08),p(x1,z-.018,-.08),p(x1,z+.018,-.08),p(x0,z+.018,-.08)])
  window_probes.append({'point':list(point(*p((x0+x1)/2,(z0+z1)/2,-.12))),'normal':list(u*normal.x+n*normal.y)})
# Reverse the north street endpoints so the face and recess normal is +Y.
wall((-15.2,18.8),(-30,18.8),5)
wall((24,18.8),(-2,18.8),10)
wall((-15.2,8.8),(-15.2,18.8),3)
wall((-2,18.8),(-2,16),1)
wall((-2,16),(-8.5,3.5),4)
# Twenty slanting lower units; section and inclination are photographic estimates.
for i in range(20):
 x=-30+54*i/19;shape=[(x-.15,21.03),(x+.15,21.03),(x+.88,19.03),(x+.28,19.03)]
 vertices=[point(xx,yy,z)for z in [12.8,23.4]for xx,yy in shape]
 batch('fin').add(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
# A thin, actual roof plane closes each northern office wing beneath its garden.
for x0,x1 in [(-30,-15.2),(-2,24)]:
 box('roof',(x0+x1)/2,13.8,32.815,x1-x0,10.0,.07)
for g in batches.values():
 obj=g.finish();obj.modifiers.clear();added.append(obj.name)
for scene in bpy.data.scenes:
 for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==h for name,h in before.items())
assert all(bpy.data.objects[name].hide_render==(True if name in archived else state)for name,state in visibility.items())
for filename in ['room-studies.json','building-review.json']:
 source=ROOT/'result/blender/stage114'/filename
 if source.exists():shutil.copyfile(source,OUT/filename)
 else:assert (OUT/filename).exists(),filename
audit={'version':115,'baseline':114,'originalFingerprints':before,'originalVisibility':visibility,
 'archivedObjects':archived,'addedObjects':added,'replacements':replacements,'upperFinCount':38,'lowerFinCount':20,
 'sourceBoundaryClearance':.06,'windowProbes':window_probes,'upperNorthWindowRows':2,'northRoofEstimate':roof_level,'fissureEstimate':fissure,
 'scope':'Photo-supported north openings, roof-screen separation and lower-fin count; lower hall, room samples and other buildings retained',
 'references':['Nick Kane built photographs 02 and 03 (2022 upload paths, capture date unknown)','Techrete manufacturer interview in Concrete Quarterly 279 (summer 2022)','Grafton architect-authored project description published February 2022'],
 'limitations':['GIS placement, fissure depth, roof datum, window size, fin inclination and PBR reflectance estimated','Full roof, hidden elevations, internal circulation and exact floor levels remain unverified','2017 section is indicative preconstruction context, not the basis for as-built dimensions']}
(OUT/'mar-north-fissure-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v115.blend'))
print('MAR_NORTH_FISSURE_SAVED',len(replacements),len(window_probes),flush=True)
