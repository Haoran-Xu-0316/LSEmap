"""Photo-proportion correction of SAW's north-fold pierced brick-screen banks.
Run in Blender Text Editor. No native survey dimensions are inferred.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, array, math, ast, struct
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/saw_exterior155';WEB=ROOT/'result/web/saw_exterior155'
BASE=ROOT/'result/blender/LSE_campus_detailed_v154.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
rec=next(r for r in json.loads((ROOT/'result/blender/stage82/saw-curtain-audit.json').read_text())['facades']if r['family']=='north_fold')
p,u,n=map(Vector,[rec['p'],rec['u'],rec['n']]);L=rec['length']
def local(q):
 q=Vector(q)-p;return Vector((q.dot(u),q.dot(n),q.z))
def components(o):
 adj=[[]for v in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;adj[a].append(b);adj[b].append(a)
 unseen=set(range(len(adj)))
 while unseen:
  seed=unseen.pop();group=[seed];stack=[seed]
  while stack:
   for v in adj[stack.pop()]:
    if v in unseen:unseen.remove(v);group.append(v);stack.append(v)
  yield group
sources=['SAW_SAW_north_fold_pierced_wall','SAW_recessed_window_glass','SAW_window_frames','SAW_screen_support_posts']+['SAW_openwork_bricks_'+str(i)for i in range(8)]

PREFIX='SAW_NEXT_EXTERIOR155_'
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,count in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
collection=bpy.data.collections['SAW_EXTERIOR'];owned=[];changes=[];removed=[]
def P(x,z,d=0):return p+u*x+n*d+Vector((0,0,z))
# Production exporter functions are parsed without running its publication loop.
source=(ROOT/'web/tools/export_scene.py').read_text();module=ast.parse(source)
namespace={'bpy':bpy,'bmesh':bmesh,'Vector':Vector,'full_detail':True,'material_cache':{},'OUTPUT':WEB,'depsgraph':bpy.context.evaluated_depsgraph_get()}
exec(compile(ast.Module(body=[node for node in module.body if isinstance(node,ast.FunctionDef)],type_ignores=[]),str(ROOT/'web/tools/export_scene.py'),'exec'),namespace)
bpy.context.view_layer.update()
def export(label):
 bpy.context.window.scene=scene;bpy.context.view_layer.update();namespace['depsgraph']=bpy.context.evaluated_depsgraph_get();namespace['material_cache']={}
 exportscene=bpy.data.scenes.new('SAW_PRIVATE_'+label)
 exterior=list(collection.all_objects)+list(bpy.data.collections['SAW_PUBLIC_INTERIOR_study'].all_objects)
 namespace['clone_group'](exterior,'SAW',exportscene)
 namespace['export_scene'](exportscene,label+'.glb')
 for o in list(exportscene.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(exportscene);bpy.context.window.scene=scene
export('before')
for name in sources[1:]:
 original=bpy.data.objects[name];obj=original.copy();obj.data=original.data.copy();obj.name=PREFIX+'retained_'+name.removeprefix('SAW_');collection.objects.link(obj)
 selected=[];counts=0
 for indices in components(original):
  c=local(sum((original.matrix_world@original.data.vertices[i].co for i in indices),Vector())/len(indices))
  if .6<c.x<L-1.1 and -.52<c.y<.03 and c.z>8.7:selected.extend(indices);counts+=1
 assert counts>0,name
 bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in selected],context='VERTS');bm.to_mesh(obj.data);bm.free()
 owned.append(obj);changes.append({'source':name,'owned':obj.name,'collection':'SAW_EXTERIOR','retainNewMaterials':False});removed.append({'source':name,'northFoldComponentsRemoved':counts,'otherFacesRetainedInOwnedCopy':True})
class Mesh:
 def __init__(self,name,mats):self.name=PREFIX+name;self.mats=mats;self.v=[];self.f=[];self.mi=[];self.uv=[]
 def add(self,vertices,faces,slot=0,uvs=None):
  off=len(self.v);self.v.extend(vertices)
  for face in faces:
   self.f.append(tuple(off+i for i in face));self.mi.append(slot);self.uv.append([tuple(local(vertices[i])[j]for j in [0,2])for i in face]if uvs is None else [uvs[i]for i in face])
 def box(self,x,z,d,w,h,t,slot=0):
  v=[P(x+a*w/2,z+c*h/2,d+b*t/2)for a,b,c in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]
  self.add(v,[(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)],slot)
 def finish(self,source=None):
  mesh=bpy.data.meshes.new(self.name);mesh.from_pydata(self.v,[],self.f);mesh.update()
  for mat in self.mats:mesh.materials.append(mat)
  layer=mesh.uv_layers.new(name='MetricUV')
  for face,slot,coords in zip(mesh.polygons,self.mi,self.uv):
   face.material_index=slot
   for index,xy in zip(face.loop_indices,coords):layer.data[index].uv=xy
  bm=bmesh.new();bm.from_mesh(mesh)
  if self.name.endswith('north_fold_pierced_wall'):bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
  bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
  obj=bpy.data.objects.new(self.name,mesh);collection.objects.link(obj);owned.append(obj);changes.append({'source':source,'owned':obj.name,'action':'replace'if source else 'add','collection':'SAW_EXTERIOR','retainNewMaterials':False});return obj
wall=Mesh('north_fold_pierced_wall',[bpy.data.objects[sources[0]].data.materials[0]])
brick=Mesh('north_fold_openwork_bricks',[bpy.data.objects['SAW_openwork_bricks_'+str(i)].data.materials[0]for i in range(8)])
glass=Mesh('north_fold_recessed_glass',[bpy.data.objects['SAW_recessed_window_glass'].data.materials[0]])
frames=Mesh('north_fold_window_frames',[bpy.data.objects['SAW_window_frames'].data.materials[0]])
posts=Mesh('north_fold_screen_support',[bpy.data.objects['SAW_screen_support_posts'].data.materials[0]])
oldholes=[(.8,9,9.3,12),(.8,12.8,8.3,15.8),(.8,16.7,7.1,19.7),(L*.65,23.4,L-1.2,25.1)]
holes=[(.8,9,11.7,11.9),(.8,12.2,10.7,15.7),(.8,16,9.7,21.2),oldholes[-1]]
outline=[(0,7.8),(L*.61,7.8),(L,0),(L,27.9),(0,23)]
def clip(poly,a,b,c):
 result=[]
 for q,r in zip(poly,poly[1:]+poly[:1]):
  dq=a*q[0]+b*q[1]+c;dr=a*r[0]+b*r[1]+c
  if dq>=-1e-8:result.append(q)
  if (dq>=0)!=(dr>=0):
   t=dq/(dq-dr);result.append((q[0]+t*(r[0]-q[0]),q[1]+t*(r[1]-q[1])))
 return result
xs=sorted(set([0,L,L*.61]+[h[i]for h in holes for i in [0,2]]));zs=sorted(set([0,7.8,23,27.9]+[h[i]for h in holes for i in [1,3]]))
for x0,x1 in zip(xs,xs[1:]):
 for z0,z1 in zip(zs,zs[1:]):
  x=(x0+x1)/2;z=(z0+z1)/2
  if any(a<x<c and b<z<d for a,b,c,d in holes):continue
  poly=[(x0,z0),(x1,z0),(x1,z1),(x0,z1)]
  poly=clip(poly,4.9/L,-1,23)
  if x<=L*.61:poly=clip(poly,0,1,-7.8)
  else:
   slope=-7.8/(L-L*.61);poly=clip(poly,-slope,1,slope*L)
  if len(poly)<3:continue
  for depth,rev in [(0,False),(-.23,True)]:
   coords=list(reversed(poly))if rev else poly
   wall.add([P(x,z,depth)for x,z in coords],[tuple(range(len(coords)))],uvs=coords)
for ring in [outline]+[[(a,b),(a,d),(c,d),(c,b)]for a,b,c,d in holes]:
 for a,b in zip(ring,ring[1:]+ring[:1]):wall.add([P(*a),P(*b),P(*b,-.23),P(*a,-.23)],[(0,1,2,3)])
brickcounts=[]
for bank,(x0,z0,x1,z1)in enumerate(holes):
 w,h=x1-x0,z1-z0;glass.add([P(x0,z0,-.46),P(x1,z0,-.46),P(x1,z1,-.46),P(x0,z1,-.46)],[(0,1,2,3)])
 divisions=max(1,round(w/1.2))
 for j in range(divisions+1):frames.box(x0+j*w/divisions,(z0+z1)/2,-.43,.052,h,.09)
 for z in [z0,z1]+([z0+h*.5]if h>4 else []):frames.box((x0+x1)/2,z,-.43,w+.1,.065,.1)
 count=0
 for row in range(math.ceil(h/.078)):
  zz=z0+.038+row*.078
  for k in range(math.ceil(w/.325)+1):
   x=x0+k*.325+(row%2)*.1625
   if x+.215>x1 or zz+.0325>z1:continue
   brick.box(x+.1075,zz,-.018,.215,.065,.215,(row*3+k)%8);count+=1
 for k in range(max(1,int(w/2))):posts.box(x0+(k+.5)*w/max(1,int(w/2)),(z0+z1)/2,-.28,.035,h,.035)
 brickcounts.append(count)
wallobj=wall.finish(sources[0]);brickobj=brick.finish();glass.finish();frameobj=frames.finish();posts.finish()
for obj,width in [(wallobj,.006),(brickobj,.003),(frameobj,.008)]:
 mod=obj.modifiers.new('Physical_edge_radius','BEVEL');mod.width=width;mod.segments=2
for name in sources:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[name])==h for name,h in originals.items()),[name for name,h in originals.items()if fingerprint(bpy.data.objects[name])!=h]
assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()]==v for name,v in visibility.items()if name not in sources)
component=OUT/'saw-exterior155-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
photos=[ROOT/'data/collections/architecture_round5/images/SAW'/('SAW_saw_909_'+s+'.jpg')for s in ['01','02']]
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'baseline':str(BASE.relative_to(ROOT)),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':sources,'changes':changes,'sourceCollection':'SAW_EXTERIOR','destinationCollection':'SAW_EXTERIOR','retainNewMaterials':False,'improvement':'Three north-fold pierced screen banks change from sparse narrow ribbon openings to broader, taller photograph-supported banks. True masonry apertures, physical individual bricks, recessed glass, bronze frames and concealed support posts corrected together.','sourceReferences':[{'local':str(f.relative_to(ROOT)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'url':'https://www.photography909.co.uk/saw-swee-hocklse-gallery','captureDate':'unknown','publicationBasis':'2017 upload path; built photographs, not 2026 Estates future render'}for f in photos],'registration':{'p':list(p),'u':list(u),'n':list(n),'length':L,'outlineRetained':outline,'originalOpenings':oldholes,'estimatedCorrectedOpenings':holes,'originalThreeBankArea':sum((c-a)*(d-b)for a,b,c,d in oldholes[:3]),'correctedThreeBankArea':sum((c-a)*(d-b)for a,b,c,d in holes[:3]),'brickWidth':.215,'brickHeight':.065,'rowPitch':.078,'brickCounts':brickcounts},'sourceMeshRetention':removed,'limitations':['Opening widths, absolute levels and 0.30m masonry separators are photographic estimates. Camera perspective has not been surveyed.','Existing complete footprint, folded outer silhouette, absolute building height, roof, canopy, timber curtain glass, shading fins and all interiors preserved. Whole-building roof and unseen elevations remain unresolved.','Existing glass and brick material parameters retained; no claim of measured color or optical finish.','Other parts of mixed original batches are transferred unchanged in owned copies; full original objects remain archived intact.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
# Reload the independent library in the untouched baseline and validate all sources.
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects'].copy()
for obj in dst.objects:
 bpy.data.collections['SAW_EXTERIOR'].objects.link(obj)
 for i,mat in enumerate(list(obj.data.materials)):
  base=bpy.data.materials.get(mat.name.rsplit('.',1)[0])if mat and mat.name[-4:-3]=='.'else mat
  if base:obj.data.materials[i]=base
for name in sources:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==h for name,h in originals.items()),[name for name,h in originals.items()if fingerprint(bpy.data.objects[name])!=h]
assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()]==v for name,v in visibility.items()if name not in sources)
from mathutils.bvhtree import BVHTree
wallobject=bpy.data.objects[PREFIX+'north_fold_pierced_wall'];tree=BVHTree.FromPolygons([wallobject.matrix_world@v.co for v in wallobject.data.vertices],[tuple(face.vertices)for face in wallobject.data.polygons]);probe=[]
for a,b,c,d in holes:
 for x,z in [(a+.25,b+.2),((a+c)/2,(b+d)/2),(c-.25,d-.2)]:
  hit=tree.ray_cast(P(x,z,1),-n,2);assert hit[0]is None;probe.append({'x':x,'z':z,'masonryFirstHit':None})
# Private derivatives use the production detail exporter and original bevels.
collection=bpy.data.collections['SAW_EXTERIOR'];export('after')
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'allOriginalFingerprintsPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(originals),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'wholeCampusSaved':False,'trueApertureChecks':probe,'privateBeforeGlb':str(WEB/'before.glb'),'privateAfterGlb':str(WEB/'after.glb'),'candidateVisualAcceptance':'pending production CampusViewer complete-building comparison'}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('SAW_EXTERIOR155_VERIFIED',proof['componentSha256']);bpy.ops.wm.quit_blender()
