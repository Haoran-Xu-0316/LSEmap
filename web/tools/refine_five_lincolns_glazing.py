"""Photo-registered 5LF glazing and visible right chimney pots. Blender Text Editor."""
from pathlib import Path
import array, hashlib, json
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/five_lincolns_glazing_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v146.blend'
EXPECTED='835b179c5bb32ecf3959ca6d9bf996ac92095fe42821fc42e7c2ddbf599b048a'
PREFIX='5LF_NEXT_GLAZING_'
ARCHIVE=['5LF_D5_glass_glass','5LF_D5_segmental_glass','5LF_D5_chimney_pot_clay','5LF_V19_REM_chimney_pot_opening_shadow']
NAMES=[PREFIX+s for s in ['upper_panes','ground_panes','registered_pots','pot_openings']]
COMPONENT=OUT/'five-lincolns-glazing-component.blend'
PREVIOUS=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else {}
if BASE.exists():assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED
else:BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
SHA=hashlib.sha256(BASE.read_bytes()).hexdigest()
def open_base():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 for name in NAMES:
  o=bpy.data.objects.get(name)
  if o:
   mesh=o.data;bpy.data.objects.remove(o,do_unlink=True);mesh.use_fake_user=False
   if not mesh.users:bpy.data.meshes.remove(mesh)
 for name in ARCHIVE:
  o=bpy.data.objects[name];state=PREVIOUS.get('originalVisibility',{}).get(name,[False,False,False]);o.hide_render,o.hide_viewport=state[:2];o.hide_set(state[2])
 for layer in bpy.context.scene.view_layers:layer.update()
open_base()
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,n in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   ar=array.array(kind,[0])*(len(data)*n);data.foreach_get(field,ar);h.update(ar.tobytes())
  for uv in o.data.uv_layers:
   ar=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',ar);h.update(ar.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
if BASE.stem.endswith('v146'):assert len(originals)==5784
prior=json.loads((ROOT/'result/blender/five_lincolns_envelope_next/audit.json').read_text());reg=prior['registration'];a,u,n=[Vector(reg[k]) for k in ['origin','axis','normal']];L=reg['length']
def world(x,d,z):return a+u*x+n*d+Vector((0,0,z))
def local(p):return Vector(((p-a).dot(u),(p-a).dot(n),p.z))
def pbr(m):
 p=m.node_tree.nodes['Principled BSDF'];return {'name':m.name,'baseColor':list(p.inputs['Base Color'].default_value),'alpha':p.inputs['Alpha'].default_value,'metallic':p.inputs['Metallic'].default_value,'roughness':p.inputs['Roughness'].default_value,'nativeTransmission':p.inputs['Transmission Weight'].default_value,'ior':p.inputs['IOR'].default_value,'webOpacity':m.get('webOpacity')}
collection=bpy.data.collections['5LF_EXTERIOR'];owned=[];changes=[];materials=[]
for index,(sourceName,newName) in enumerate(zip(ARCHIVE,NAMES)):
 source=bpy.data.objects[sourceName];o=source.copy();o.data=source.data.copy();o.name=newName;collection.objects.link(o)
 if index<2:
  old=o.data.materials[0];m=old.copy();m.name=PREFIX+('upper_optics' if index==0 else 'ground_optics');p=m.node_tree.nodes['Principled BSDF'];p.inputs['Transmission Weight'].default_value=.38;p.inputs['Alpha'].default_value=.78;p.inputs['Metallic'].default_value=.08;p.inputs['Roughness'].default_value=.22;p.inputs['IOR'].default_value=1.46;m['webOpacity']=.78;o.data.materials[0]=m;materials.append({'original':pbr(old),'new':pbr(m),'reason':'Official012 shows blue sky reflection and darker lower panes; restrained neutral glass. Optical parameters estimated, original tint preserved.'})
  action='Optical material replacement only; exact coordinates, topology and UV retained'
 else:
  # Local x near0 is street-right. Preserve unseen left pot exactly; split only right pot along registered frontage axis.
  vs=[];fs=[];mis=[];right={v.index for v in source.data.vertices if local(source.matrix_world@v.co).x<L/2};left=set(range(len(source.data.vertices)))-right
  for ids,shift in [(left,None),(right,-.115),(right,.115)]:
   mapping={}
   for i in sorted(ids):
    p=source.matrix_world@source.data.vertices[i].co
    if shift is not None:
     q=local(p);q.x=.3+(q.x-.3)*.65+shift;q.y=-2+(q.y+2)*.65;p=world(*q)
    mapping[i]=len(vs);vs.append(source.matrix_world.inverted()@p)
   for f in source.data.polygons:
    if set(f.vertices)<=ids:fs.append(tuple(mapping[i] for i in f.vertices));mis.append(f.material_index)
  mesh=bpy.data.meshes.new(newName+'_mesh');mesh.from_pydata(vs,[],fs);mesh.update()
  for m in source.data.materials:mesh.materials.append(m)
  for f,mi in zip(mesh.polygons,mis):f.material_index=mi
  # Preserve loop UVs by mapping each cloned face to its original face.
  for uv in source.data.uv_layers:
   dst=mesh.uv_layers.new(name=uv.name);at=0
   for ids in [left,right,right]:
    for f in source.data.polygons:
     if set(f.vertices)<=ids:
      for li in f.loop_indices:dst.data[at].uv=uv.data[li].uv;at+=1
  o.data=mesh;action='Replace visible right single pot with two estimated narrow pots across existing stack frontage; left pot unchanged'
 owned.append(o);changes.append({'source':sourceName,'owned':newName,'action':action})
for name in ARCHIVE:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
openings=[]
for opening in prior['openings']:
 opening=dict(opening);opening['object']=dict(zip(ARCHIVE,NAMES))[opening['object']];openings.append(opening)
def probes():
 # Actual scene neighbors are included in the building's bounding region, not just its glass family.
 verts=[];faces=[];owners=[];faceIndices=[]
 ring=next(b['rings'][0] for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings'] if b['id']=='way/1184094775')
 minX=min(p[0] for p in ring)-2;maxX=max(p[0] for p in ring)+2;minY=min(p[1] for p in ring)-2;maxY=max(p[1] for p in ring)+2
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or o.hide_render or not o.data.polygons:continue
  ps=[o.matrix_world@Vector(p) for p in o.bound_box]
  if max(p.x for p in ps)<minX or min(p.x for p in ps)>maxX or max(p.y for p in ps)<minY or min(p.y for p in ps)>maxY or min(p.z for p in ps)>20 or max(p.z for p in ps)<0:continue
  k=len(verts);verts.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(k+i for i in f.vertices) for f in o.data.polygons);owners.extend([o.name]*len(o.data.polygons));faceIndices.extend(f.index for f in o.data.polygons)
 tree=BVHTree.FromPolygons(verts,faces)
 def ray(origin,direction,distance):
  h=tree.ray_cast(origin,direction,distance);name=owners[h[2]] if h[2] is not None else None
  return {'object':name,'pointLocal':list(local(h[0])) if h[0] is not None else None,'distance':h[3] if h[2] is not None else None,'face':faceIndices[h[2]] if h[2] is not None else None}
 front=[];behind=[]
 for index,p in enumerate(openings):
  lo,hi=p['boundsLocal']
  for sx in [.25,.75]:
   for sz in [.25,.75]:
    x=lo[0]+(hi[0]-lo[0])*sx;z=lo[2]+(hi[2]-lo[2])*sz
    result=ray(world(x,.8,z),-n,1.4);front.append({'window':index,'expectedGlass':p['object'],'originLocal':[x,.8,z],'firstHit':result});assert result['object']==p['object'],front[-1]
    # Begin5mm behind measured back face, detecting a plate only24mm behind glass.
    d=lo[1]-.005;result=ray(world(x,d,z),-n,2.0);behind.append({'window':index,'originLocal':[x,d,z],'nearFieldLimit':2.0,'firstHit':result})
 return front,behind
front,behind=probes();assert len(front)==44 and len(behind)==44 and not any(p['firstHit']['object'] for p in behind)
def preserved():
 assert all(fingerprint(bpy.data.objects[name])==h for name,h in originals.items())
 assert all([o.hide_render,o.hide_viewport,o.hide_get()]==visibility[o.name] for o in bpy.data.objects if o.name in originals and o.name not in ARCHIVE)
preserved();bpy.data.libraries.write(str(COMPONENT),set(owned),fake_user=True,compress=True)
audit={'baseline':str(BASE),'baselineSha256':SHA,'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':list(NAMES),'archivedObjects':list(ARCHIVE),'archiveObjects':list(ARCHIVE),'changes':changes,'materials':materials,'registration':reg,'references':prior['references'][:1],'frontGlassProbes':front,'behindGlassProbes':behind,'limitations':['Glass transmission0.38,alpha/webOpacity0.78,roughness0.22,IOR1.46 estimated for restrained reflection/visibility; original tint retained.','Right pot spacing0.23m/radius scaled0.65 are estimated from undated official012; position uses inherited right stack localx0.30,depth-2m.','No unseen roof, left chimney count or rooms reconstructed; 2m near-field void is not full interiors.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
open_base();collection=bpy.data.collections['5LF_EXTERIOR']
with bpy.data.libraries.load(str(COMPONENT),link=False) as (src,dst):dst.objects=list(NAMES)
for o in dst.objects:collection.objects.link(o)
for name in ARCHIVE:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in bpy.context.scene.view_layers:layer.update()
rf,rb=probes();assert rf==front and rb==behind;preserved()
for name in NAMES[:2]:
 m=bpy.data.objects[name].data.materials[0];assert abs(m['webOpacity']-.78)<1e-6 and abs(m.node_tree.nodes['Principled BSDF'].inputs['Transmission Weight'].default_value-.38)<1e-6
v={'componentSha256':hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(originals),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==SHA,'reloadedFrontProbes':rf,'reloadedBehindProbes':rb,'webOpacityVerified':.78,'render':'reloaded-five-lincolns-glazing.png'}
scene=bpy.context.scene;members={o.name for o in collection.all_objects}
for o in scene.objects:
 if o.type not in {'LIGHT','CAMERA'} and o.name not in members:o.hide_render=True
focus=world(L/2,0,8.0);camdata=bpy.data.cameras.new('5LF_REVIEW');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+n*25+u*1+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=23;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/v['render']);bpy.ops.render.render(write_still=True)
v['camera']=list(cam.location);v['target']=list(focus);(OUT/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('5LF_GLAZING_VERIFIED',len(originals),len(front),len(behind),v['componentSha256']);bpy.ops.wm.quit_blender()
