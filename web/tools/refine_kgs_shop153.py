"""Pierce the two registered Kings Chambers entrance panes through their opaque caps.
Constant Blender configuration; independent component output only.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/kgs_shop153';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v152.blend';PREFIX='KGS_NEXT_SHOP153_'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_source():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if old:
  for name in old['archivedObjects']:
   o=bpy.data.objects[name];o.hide_render,o.hide_viewport=old['originalVisibility'][name][:2];o.hide_set(old['originalVisibility'][name][2])
 return bpy.context.scene,bpy.data.collections['KGS_EXTERIOR']
scene,col=open_source();sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v152'):assert sha=='639440608dd8f7db604c126141c45c4a55076cf33dcae4f57af5b649238544a3'
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()

original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v152'):assert len(original)==5871
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



wood=bpy.data.objects['KGS_D5_entrance_door_wood'];glass=bpy.data.objects['KGS_D5_door_glass_glass'];wp=[wood.matrix_world@v.co for v in wood.data.vertices];O=sum(wp,Vector())/len(wp);O.z=0;U=(wp[4]-wp[0]).normalized();N=Vector((U.y,-U.x,0));site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());centre=Vector((*next(q for q in site['buildings']if q['code']=='KGS')['center'],0))
if N.dot(O-centre)<0:N=-N
def local(p):return((p-O).dot(U),(p-O).dot(N),p.z)
helpers=0
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


inspection=json.loads((OUT/'native-inspection.json').read_text());holes=[]
for row in inspection['glassChecks']:
 vertices=row['localVertices'];holes.append({'x':[min(v[0]for v in vertices),max(v[0]for v in vertices)],'z':[min(v[2]for v in vertices),max(v[2]for v in vertices)]})
def point(x,d,z):return O+U*x+N*d+Vector((0,0,z))
def clip(poly,axis,value,greater):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  av=local(a[0])[axis];bv=local(b[0])[axis];ia=av>=value-1e-9 if greater else av<=value+1e-9;ib=bv>=value-1e-9 if greater else bv<=value+1e-9
  if ia:result.append(a)
  if ia!=ib:
   t=(value-av)/(bv-av);result.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t)))
 return result
def pierced(wood,name):
 dvalues=[local(wood.matrix_world@v.co)[1]for v in wood.data.vertices];dmin,dmax=min(dvalues),max(dvalues)
 wood_owned=wood.copy();wood_owned.name=name;col.objects.link(wood_owned);old_uv=wood.data.uv_layers.active;output=[]
 for face in wood.data.polygons:
  poly=[(wood.matrix_world@wood.data.vertices[wood.data.loops[k].vertex_index].co,Vector(old_uv.data[k].uv)if old_uv else Vector((0,0)))for k in face.loop_indices];pieces=[poly]
  for h in holes:
   planes=[(0,h['x'][0],True),(0,h['x'][1],False),(2,h['z'][0],True),(2,h['z'][1],False)];updated=[]
   for piece in pieces:
    inside=piece
    for axis,value,g in planes:
     inside=clip(inside,axis,value,g)
     if len(inside)<3:break
    if len(inside)<3:updated.append(piece);continue
    current=piece
    for axis,value,g in planes:
     outside=clip(current,axis,value,not g)
     if len(outside)>=3:updated.append(outside)
     current=clip(current,axis,value,g)
   pieces=updated
  output.extend((p,face.material_index)for p in pieces)
 # New cut reveals use the original timber slot. UV is a geometric estimate only
 # on these new faces; retained source faces interpolate their exact original UV.
 for h in holes:
  x0,x1=h['x'];z0,z1=h['z']
  for a,b in [((x0,z0),(x0,z1)),((x1,z1),(x1,z0)),((x1,z0),(x0,z0)),((x0,z1),(x1,z1))]:
   ps=[point(a[0],d,a[1])for d in [dmax,dmin]]+[point(b[0],d,b[1])for d in [dmin,dmax]];output.append(([(v,Vector((i%2,(i//2))))for i,v in enumerate(ps)],0))
 verts=[];faces=[];uvs=[];slots=[]
 for polygon,slot in output:
  start=len(verts);verts.extend(wood.matrix_world.inverted()@q[0]for q in polygon);faces.append(tuple(start+i for i in range(len(polygon))));uvs.append([q[1]for q in polygon]);slots.append(slot)
 mesh=bpy.data.meshes.new(wood_owned.name);mesh.from_pydata(verts,[],faces);mesh.update()
 for mat in wood.data.materials:mesh.materials.append(mat)
 uv=mesh.uv_layers.new(name=old_uv.name)if old_uv else None
 for face,coords,slot in zip(mesh.polygons,uvs,slots):
  face.material_index=slot
  if uv:
   for k,value in zip(face.loop_indices,coords):uv.data[k].uv=value
 wood_owned.data=mesh
 return wood_owned
wood_owned=pierced(wood,PREFIX+'pierced_timber_door');shadow=bpy.data.objects['KGS_D5_entrance_recess_shadow'];shadow_owned=pierced(shadow,PREFIX+'open_recess_perimeter');glass_owned=glass.copy();glass_owned.data=glass.data.copy();glass_owned.name=PREFIX+'entrance_real_glass';col.objects.link(glass_owned);mat=glass.data.materials[0].copy();mat.name=PREFIX+'neutral_reflective_glass';node=mat.node_tree.nodes['Principled BSDF'];original_colour=list(node.inputs['Base Color'].default_value);node.inputs['Alpha'].default_value=.84;node.inputs['Transmission Weight'].default_value=.24;node.inputs['Roughness'].default_value=.23;node.inputs['IOR'].default_value=1.45;mat['webOpacity']=.84;glass_owned.data.materials[0]=mat
owned=[wood_owned,glass_owned,shadow_owned];OWNED=[o.name for o in owned];archives=[wood.name,glass.name,shadow.name]
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
def check():
 global ACTIVE_TREES
 ACTIVE_TREES=trees();rows=[]
 for pane,h in enumerate(holes):
  for fx in [.1,.3,.7,.9]:
   for fz in [.1,.3,.7,.9]:
    p=point(h['x'][0]+fx*(h['x'][1]-h['x'][0]),.072,h['z'][0]+fz*(h['z'][1]-h['z'][0]));first=hit(p+N*.8,-N,1.5);back=hit(p-N*.023,-N,.6,[OWNED[1]]);assert first and first[1]==OWNED[1],(pane,fx,fz,first);assert back is None,(pane,fx,fz,back)
    rows.append({'kind':'registered-door-glass','pane':pane,'point':list(p),'firstObject':first[1],'expected':OWNED[1],'behindNearfield':back,'noOpaqueNearfieldCap':True})
 for x,z,expected in [(-1.55,1.8,OWNED[0]),(1.55,1.8,OWNED[0]),(-1.7,1.8,'KGS_D5_door_jamb_wood'),(1.7,1.8,'KGS_D5_door_jamb_wood'),(0,2.5,'KGS_D5_door_center_stile_wood'),(-.8,.85,OWNED[0]),(.8,.85,OWNED[0]),(-.8,2.65,OWNED[0]),(.8,2.65,OWNED[0])]:
  p=point(x,.05,z);first=hit(p+N*.25,-N,.4);assert first and first[1]==expected,(x,z,first);rows.append({'kind':'timber-border-retained','point':list(p),'firstObject':first[1],'expected':expected})
 return rows
checks=check();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'kings-chambers-shop-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':[{'source':wood.name,'owned':OWNED[0],'action':'Pierce actual two glass outlines through existing solid timber leaf; retain all outside source timber surfaces and add cut reveals.'},{'source':glass.name,'owned':OWNED[1],'action':'Retain exact original glass geometry, UV, source tint and positions; limited estimated transparency only on two real entrance panes.'}],'registration':{'origin':list(O),'right':list(U),'outward':list(N),'holes':holes,'shadowDepth':[min(local(shadow.matrix_world@v.co)[1]for v in shadow.data.vertices),max(local(shadow.matrix_world@v.co)[1]for v in shadow.data.vertices)],'woodDepth':[-.05,.05],'dimensionsInheritedEstimates':True},'beforeChecks':inspection['glassChecks'],'sources':[{'path':'data/建筑图片/KGS_King_s Chambers/01_建筑实拍/small_buildings_round3_small3_007.jpg','captureDate':'unknown','supports':'Common portal actual glazed timber entrance with interior visible; source does not establish current RAG storefront colour or extent.'},{'path':'result/blender/kgs_shop153/official-vintage-shop.jpg','url':'https://info.lse.ac.uk/current-students/estates-division/Assets/Images/LSESU-Vintage-clothing-shop-web.jpg','captureDate':'unknown','supports':'Shopglass transparent and reflective with green shop lettering; crop does not uniquely register left/right store bay; no new storefront subdivision based on this image.'},{'url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Cap-Dev/2026-April-CD-Newsletter-FINAL.pdf','publicationDate':'2026-04','supports':'Finaldesigns under stakeholder review; June construction/JulyAugust anticipatedcompletion. Future schedule not built proof.'},{'path':'data/documents/estates_projects_2026_07.pdf','publicationDate':'2026-07','pdfPage':4,'supports':'RAG reddishshopfront design render, anticipatedautumncompletion. No built colour proof.'},{'url':'https://www.lsesu.com/organisation/7206/','accessed':'2026-10-04','supports':'Current vintagecharityshop exists; retrieved body contains no photographed completed revamp.'}],'optics':{'alpha':.84,'webOpacity':.84,'transmission':.24,'roughness':.23,'ior':1.45,'sourceColour':original_colour,'estimated':True},'scope':'Registered common entrance two real glass holes only. Shopwindow proportions, cream historical shop colours, green attic ceramic, dome, sidewall and interior retained. No red proposal implementation, fake backing plate or invented room.','limitations':['No latest dated postrefurbishment frontage photo was found in bounded official query; current RAG complete storefront remainsunverified.','Common entrance glass/photos capturedateunknown, dimensionsinheritedauthoringestimates.','Sixdecimetre window-clearance tests establish no immediate artificial leafcap, not complete internal room geometry.','Only added timber reveal UV is estimated; retained timber/sourceglass UV preserved.']}
audit['changes'].append({'source':shadow.name,'owned':OWNED[2],'action':'Pierce the two same registered glass outlines through artificial full entrance-recess cap; retain all perimeter faces.'});
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));scene,col=open_source()
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
a=bpy.data.objects[archives[1]];b=bpy.data.objects[OWNED[1]];assert a.matrix_world==b.matrix_world;assert[list(v.co)for v in a.data.vertices]==[list(v.co)for v in b.data.vertices];assert[list(v.uv)for v in a.data.uv_layers.active.data]==[list(v.uv)for v in b.data.uv_layers.active.data];assert list(b.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)==original_colour;assert abs(b.data.materials[0]['webOpacity']-.84)<1e-6
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(original),'firstSurfaceChecks':reopened,'checkCount':len(reopened),'glassGeometryUVAndSourceColourPreserved':True,'designRenderNotBuiltClaim':True,'fullModelSaved':False}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in ['MESH','FONT','CURVE']and o.name not in visible:o.hide_render=True
target=centre+Vector((0,0,9));position=target+N*38+U*8+Vector((0,0,5));cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=position;cam.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=32;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-kings-chambers.png');bpy.ops.render.render(write_still=True);proof['camera']={'position':list(position),'target':list(target),'orthoScale':32};proof['nativePreview']=scene.render.filepath;(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('KGS153_VERIFIED',len(original),len(owned),len(reopened));bpy.ops.wm.quit_blender()
