"""Read-only5LFwhole frontage and near-field glazing review in Blender Text Editor.
No component is produced without a substantial supported envelope correction.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/five_lincolns_envelope_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v145.blend';EXPECTED='84e45149527c586960d8c8a9f3cf94d0a29a68e92fe5d17e251f45158fad00b3'
if BASE.exists():assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED
else:BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
SHA=hashlib.sha256(BASE.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,n in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   ar=array.array(kind,[0])*(len(data)*n);data.foreach_get(field,ar);h.update(ar.tobytes())
  for uv in o.data.uv_layers:
   ar=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',ar);h.update(ar.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
if BASE.stem.endswith('v145'):assert len(originals)==5754
reg=json.loads((OUT/'inspection.json').read_text())['registration'];a,u,n=[Vector(reg[k]) for k in ['origin','axis','normal']];L=reg['length']
def world(x,d,z):return a+u*x+n*d+Vector((0,0,z))
def local(p):return Vector(((p-a).dot(u),(p-a).dot(n),p.z))
collection=bpy.data.collections['5LF_EXTERIOR'];openings=[];mats={}
for name in ['5LF_D5_glass_glass','5LF_D5_segmental_glass']:
 o=bpy.data.objects[name];mesh=o.data;adj={v.index:set() for v in mesh.vertices}
 for e in mesh.edges:
  x,y=e.vertices;adj[x].add(y);adj[y].add(x)
 seen=set()
 for v in mesh.vertices:
  if v.index in seen:continue
  seen.add(v.index);todo=[v.index];group=[]
  while todo:
   i=todo.pop();group.append(i)
   for j in adj[i]:
    if j not in seen:seen.add(j);todo.append(j)
  ps=[local(o.matrix_world@mesh.vertices[i].co) for i in group];lo=[min(p[i] for p in ps) for i in range(3)];hi=[max(p[i] for p in ps) for i in range(3)]
  openings.append({'object':name,'boundsLocal':[lo,hi]})
 for m in mesh.materials:
  p=m.node_tree.nodes.get('Principled BSDF');t=p.inputs.get('Transmission Weight') or p.inputs.get('Transmission')
  mats[m.name]={'baseColor':list(p.inputs['Base Color'].default_value),'alpha':p.inputs['Alpha'].default_value,'metallic':p.inputs['Metallic'].default_value,'roughness':p.inputs['Roughness'].default_value,'nativeTransmission':t.default_value if t else None,'explicitWebOpacity':m.get('webOpacity'),'resolvedWebOpacity':m.get('webOpacity',p.inputs['Alpha'].default_value),'unchanged':True}
assert len(openings)==11
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
assert all(fingerprint(bpy.data.objects[name])==h for name,h in originals.items())
assert all([o.hide_render,o.hide_viewport,o.hide_get()]==visibility[o.name] for o in bpy.data.objects if o.name in originals)
refs=[]
for file,folder,date,evidence in [('exteriors_lse_estate_012.jpg','01_建筑实拍','Unknown capture date; official LSE Estates','Three columns and three upper brick storeys; left door and two right segmental windows; right-front chimney has two pots.'),('small_buildings_round3_small3_009.jpg','03_历史与施工参考','1975 London Picture Archive','Historical rear photograph is context only, not evidence of current rear roof arrangement.')]:
 p=ROOT/'data/建筑图片/5LF_5 Lincoln_s Inn Fields'/folder/file;refs.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'date':date,'evidence':evidence})
audit={'baseline':str(BASE),'baselineSha256':SHA,'readOnly':True,'ownedObjects':[],'archivedObjects':[],'archiveObjects':[],'changes':[],'originalFingerprints':originals,'originalVisibility':visibility,'registration':reg,'references':refs,'wholeFrontReview':{'upperColumns':3,'upperStoreys':3,'groundGlazedOpenings':2,'doorPosition':'Street-left; registered localx=2.5L/3','openingCount':len(openings),'materials':'Existing yellow stock brick,pale ground frontage,dark door,white sash frames match overall official photograph','arches':'Estimated shallow segmental heads retained from55','rainwater':'Existing91edge pipes and dark chimney finish retained'},'openings':openings,'glassFamilies':mats,'frontGlassProbes':front,'behindGlassProbes':behind,'remainingIssues':[{'issue':'Official right-front chimney has two pots; native stack only one','scope':'Supported count difference recorded; not adding a small decorative batch under present scope'},{'issue':'Native flat roof behind parapet, rear/party elevations and chimney depth unverified','scope':'1975rear image cannot establish current roof; no guessed reconstruction'},{'issue':'Exact facade,forecourt and stair dimensions remain inherited estimates','scope':'No measured drawing supplied'}],'limitations':['Native/derived glazing opacity recorded; no transparency or material change.','Two-meter behind-pane checks verify local obstructions,not complete apartment interiors or surveyed rooms.','No component or save/reopen acceptance claimed for this read-only stage.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
v={'baselineSha256':SHA,'originalObjectCount':len(originals),'readOnly':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'frontGlassProbeCount':len(front),'behindGlassProbeCount':len(behind),'behindGlassHits':[p for p in behind if p['firstHit']['object']],'savedComponentReopened':False,'fullModelSaved':False,'renderCount':1,'render':'native-five-lincolns-frontage.png'}
scene=bpy.context.scene;members={o.name for o in collection.all_objects}
for o in scene.objects:
 if o.type not in {'LIGHT','CAMERA'} and o.name not in members:o.hide_render=True
focus=world(L/2,0,8.0);camdata=bpy.data.cameras.new('5LF_REVIEW');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+n*25+u*1+Vector((0,0,1));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=23;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1200;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.filepath=str(OUT/v['render']);bpy.ops.render.render(write_still=True)
v['camera']=list(cam.location);v['target']=list(focus);(OUT/'verification.json').write_text(json.dumps(v,indent=2)+'\n');print('5LF_READONLY_VERIFIED',len(originals),len(front),len(behind),len(v['behindGlassHits']));bpy.ops.wm.quit_blender()
