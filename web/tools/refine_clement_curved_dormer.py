"""Register the fifth curved Clement dormer against native glass and cheek geometry.
Constant Blender configuration; independent component output only.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/clm_curved_dormer152';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v151.blend';PREFIX='CLM_NEXT_CURVED152_'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_source():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if old:
  for name in old['archivedObjects']:
   o=bpy.data.objects[name];o.hide_render,o.hide_viewport=old['originalVisibility'][name][:2];o.hide_set(old['originalVisibility'][name][2])
 return bpy.context.scene,bpy.data.collections['CLM_EXTERIOR']
scene,col=open_source();sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v151'):assert sha=='39376c7060856dd05b42596414e74a47d18a60828aba92a45f78c3d6fd842e19'
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()

original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v151'):assert len(original)==5868
def parts(o):
 adj={v.index:set()for v in o.data.vertices}
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 seen=set();result=[]
 for seed in adj:
  if seed in seen:continue
  stack=[seed];seen.add(seed);group=[]
  while stack:
   k=stack.pop();group.append(k)
   for q in adj[k]:
    if q not in seen:seen.add(q);stack.append(q)
  result.append(group)
 return result


site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());rec=next(x for x in site['buildings']if x['code']=='CLM');centre=Vector(rec['center']);points=[Vector(rec['rings'][0][i])for i in [5,4,3,2,1]];segments=[];length=0
for a,b in zip(points,points[1:]):
 u=(b-a).normalized();n=Vector((u.y,-u.x))
 if n.dot((a+b)/2-centre)<0:n=-n
 l=(b-a).length;segments.append((length,length+l,a,u,n));length+=l
bay=length/7;sc=5.5*bay
sour=bpy.data.objects['CLM_NEXT_GLAZING151_registered_four_dormer_glass'];group=parts(sour)[4];pts=[sour.matrix_world@sour.data.vertices[i].co for i in group]
cheek=bpy.data.objects['CLM_D5_roof73_dormer_metal'];groups=parts(cheek);c=sum(pts,Vector())/len(pts);near=sorted(groups,key=lambda g:(sum((cheek.matrix_world@cheek.data.vertices[i].co for i in g),Vector())/len(g)-c).length)[:2]

def point(chainage,depth,z):
 st,en,a,u,n=next((q for q in segments if chainage<=q[1]),segments[-1]);v=a+u*(chainage-st)+n*depth;return Vector((*v,z))
# Actual native glass spans two different facade normals. Connect its back-face
# endpoints to the respective native cheek rear edges, keeping a10mm lateral
# margin inside each cheek and the inherited rear depth exactly1.92m.
quad=[point(sc-.60,-.9725,0),point(sc+.60,-.9725,0),point(sc+.60,-1.92,0),point(sc-.60,-1.92,0)]
for v in quad[:2]:assert min((Vector((p.x,p.y,0))-v).length for p in pts)<.00003
mid=sum(quad,Vector())/4;planes=[]
for a,b in zip(quad,quad[1:]+quad[:1]):
 edge=b-a;normal=Vector((-edge.y,edge.x,0)).normalized()
 if normal.dot(mid-a)<0:normal=-normal
 planes.append((normal,normal.dot(a)))
planes.extend([(Vector((0,0,1)),24.975),(Vector((0,0,-1)),-26.39)])
def inside(p):return all(n.dot(p)>=d-3e-5 for n,d in planes)
def clip(poly,n,d,keep):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  av=n.dot(a[0])-d;bv=n.dot(b[0])-d;ia=av>=-1e-9 if keep else av<=1e-9;ib=bv>=-1e-9 if keep else bv<=1e-9
  if ia:result.append(a)
  if ia!=ib:
   f=av/(av-bv);result.append((a[0].lerp(b[0],f),a[1].lerp(b[1],f)))
 return result
roof_source=bpy.data.objects['CLM_NEXT_GLAZING151_four_bounded_dormer_apertures'];roof=roof_source.copy();roof.name=PREFIX+'fifth_registered_roof_aperture';col.objects.link(roof);uv_source=roof_source.data.uv_layers.active;output=[];removed=[]
for face in roof_source.data.polygons:
 poly=[(roof_source.matrix_world@roof_source.data.vertices[roof_source.data.loops[k].vertex_index].co,Vector(uv_source.data[k].uv)if uv_source else Vector((0,0)))for k in face.loop_indices];inner=poly
 for n,d in planes:
  inner=clip(inner,n,d,True)
  if len(inner)<3:break
 if len(inner)<3:output.append((poly,face.material_index));continue
 current=poly
 for n,d in planes:
  outside=clip(current,n,d,False)
  if len(outside)>=3:output.append((outside,face.material_index))
  current=clip(current,n,d,True)
 assert all(inside(v[0])for v in current),[[n.dot(v[0])-d for n,d in planes]for v in current];removed.append({'sourcePolygon':face.index,'worldVertices':[list(v[0])for v in current]})
assert removed
verts=[];faces=[];uvs=[];slots=[]
for polygon,slot in output:
 start=len(verts);verts.extend(roof_source.matrix_world.inverted()@q[0]for q in polygon);faces.append(tuple(start+i for i in range(len(polygon))));uvs.append([q[1]for q in polygon]);slots.append(slot)
mesh=bpy.data.meshes.new(roof.name);mesh.from_pydata(verts,[],faces);mesh.update()
for mat in roof_source.data.materials:mesh.materials.append(mat)
uv=mesh.uv_layers.new(name=uv_source.name)if uv_source else None
for face,coords,slot in zip(mesh.polygons,uvs,slots):
 face.material_index=slot
 if uv:
  for k,v in zip(face.loop_indices,coords):uv.data[k].uv=v
roof.data=mesh
source=sour;glass=source.copy();glass.data=source.data.copy();glass.name=PREFIX+'fifth_translucent_dormer';col.objects.link(glass)
# Existing accepted slot1 applies to preceding four panes. Reuse precisely that
# material for fifth pane, retaining every source vertex, loop, UV and material.
assert abs(glass.data.materials[1]['webOpacity']-.82)<1e-6
for face in glass.data.polygons:face.material_index=1
owned=[glass,roof];OWNED=[o.name for o in owned];archives=[source.name,roof_source.name]
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
def trees():
 allowed=set()
 def walk(c,hidden=False):
  hidden=hidden or c.hide_render
  if not hidden:allowed.update(o.name for o in c.objects)
  for child in c.children:walk(child,hidden)
 walk(scene.collection)
 return[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons]))for o in scene.objects if o.type=='MESH'and not o.hide_render and o.name in allowed and len(o.data.polygons)]
def hit(start,direction,maximum,excluded=None):
 hits=[]
 for name,t in ACTIVE_TREES:
  if name in(excluded or []):continue
  r=t.ray_cast(start,direction,maximum)
  if r[0]is not None:hits.append((r[3],name,list(r[0])))
 return min(hits)if hits else None

# Sample the actual glass chord, not either adjacent facade segment tangent.
left,right=quad[:2];U=(right-left).normalized();N=Vector((U.y,-U.x,0));C=(left+right)/2;C.z=25.68
samples=[]
for dx in [-.43,-.13,.13,.43]:
 for dz in [-.53,-.23,.23,.53]:samples.append(C+U*dx+Vector((0,0,dz)))
def check():
 global ACTIVE_TREES
 ACTIVE_TREES=trees();rows=[]
 for k,p in enumerate(samples):
  first=hit(p+N*.9,-N,1.5);back=hit(p-N*.03,-N,2,[OWNED[0]]);assert first and first[1]==OWNED[0],(k,first)
  assert back is None or not inside(Vector(back[2])),(k,back)
  rows.append({'kind':'fifth-light','sample':k,'point':list(p),'firstObject':first[1],'expected':OWNED[0],'behind':back,'noOpaqueInsideRegisteredCheeks':True})
 # Preserve four previously corrected openings using151accepted samples.
 previous=json.loads((ROOT/'result/blender/clm_glazing151/verification.json').read_text())
 for r in previous['firstSurfaceChecks']:
  if r['kind']!='registered-dormer-glass':continue
  p=Vector(r['point']);n=Vector(r['normal']);first=hit(p+n*.9,-n,1.5);back=hit(p-n*.035,-n,.90,[OWNED[0]]);assert first and first[1]==OWNED[0];assert back is None
  rows.append({'kind':'previous-four-preserved','point':list(p),'firstObject':first[1],'expected':OWNED[0],'behindNearfield':back})
 # Confirm roof immediately outside both sides of the new aperture remains.
 for dx in [-.78,.78]:
  p=C+U*dx;first=hit(p+N*.8,-N,3);assert first and first[1]==OWNED[1],(dx,first)
  rows.append({'kind':'roof-outside-aperture','point':list(p),'firstObject':first[1],'expected':OWNED[1]})
 return rows
checks=check();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'clement-curved-dormer-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':[{'source':source.name,'owned':OWNED[0],'action':'Retain five-pane geometry, UV and existing two material slots; assign fifth pane to already accepted neutral glazing slot1.'},{'source':roof_source.name,'owned':OWNED[1],'action':'Retain prior four apertures; subtract fifth actual glass chord prism with rear edge spanning respective native cheek boundaries.'}],'registration':{'chainageCentre':sc,'segmentJunction':segments[2][1],'worldFootprint':[list(v)for v in quad],'zRange':[24.975,26.39],'planes':[{'normal':list(n),'distance':d}for n,d in planes],'actualGlassVertices':[list(v)for v in pts],'actualCheekVertices':[[list(cheek.matrix_world@cheek.data.vertices[i].co)for i in g]for g in near],'removedIntersections':removed,'dimensionsEstimated':True,'numericalToleranceMetres':.00003},'references':json.loads((ROOT/'result/blender/stage73/references.json').read_text()),'limitations':['Native window and cheek dimensions inherited photo estimates, not measured2026survey.','2018/2023photos establish real glazing, not complete room volumes.','Interior and deeper actual roof outside registered chamber retained; no fabricated backing geometry.','Bottom bound24.975preserves native cheek-floor top; pane bottom24.970 remains inherited.']}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
scene,col=open_source()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(OWNED)
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  m=slot.material
  if m and'.'in m.name and m.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(m.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
reopened=check();assert reopened==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in archives)
a=bpy.data.objects[archives[0]];b=bpy.data.objects[OWNED[0]];assert a.matrix_world==b.matrix_world;assert[list(v.co)for v in a.data.vertices]==[list(v.co)for v in b.data.vertices];assert[list(v.uv)for v in a.data.uv_layers.active.data]==[list(v.uv)for v in b.data.uv_layers.active.data];assert[m.name for m in a.data.materials]==[m.name for m in b.data.materials]
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(original),'firstSurfaceChecks':reopened,'checkCount':len(reopened),'glazingGeometryUVAndMaterialsPreserved':True,'priorFourAperturesPreserved':True,'fullModelSaved':False}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in ['MESH','FONT','CURVE']and o.name not in visible:o.hide_render=True
previous=json.loads((ROOT/'result/blender/clm_glazing151/verification.json').read_text());params=previous['wholeBuildingPreview'];cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);position=Vector(params['position']);target=Vector(params['target']);cam.location=position;cam.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=params['orthoScale'];scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-clement-complete-glazing.png');bpy.ops.render.render(write_still=True);proof['previewCamera']=params;proof['nativePreview']=scene.render.filepath;(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('CLM152_VERIFIED',len(original),len(owned),len(reopened));bpy.ops.wm.quit_blender()
