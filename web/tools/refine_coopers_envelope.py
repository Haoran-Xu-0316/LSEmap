"""Review Coopers' registered street envelope against bounded primary evidence.
Blender constant configuration; no command-line parameters or full-campus save.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh,numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/coopers_envelope_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v145.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
PREFIX='49L_NEXT_';previous=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
for o in list(bpy.data.objects):
 if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
if previous:
 for name in previous['archivedObjects']:
  o=bpy.data.objects[name];o.hide_render,o.hide_viewport=previous['originalVisibility'][name][:2];o.hide_set(previous['originalVisibility'][name][2])
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());shop=next(x for x in site['buildings']if x.get('code')=='OCS')['rings'][0]
source=np.array([[477.387,637.5],[577.406,597.48],[607.828,675.719],[597.867,706.199],[500.066,681.422]])
transform=np.linalg.lstsq(np.c_[source,np.ones(5)],np.array([shop[i]for i in [0,1,3,4,5]]),rcond=None)[0]
outline=np.array([[379.588,364.62],[470.308,332.04],[534.388,490.86],[484.227,504.48],[477.148,518.64],[423.628,533.46],[359.789,409.32]])
ring=(np.c_[outline,np.ones(7)]@transform).tolist();centre=sum((Vector((*p,0))for p in ring),Vector())/len(ring)
frames={}
for i in [0,5,6]:
 o=Vector((*ring[i],0));q=Vector((*ring[(i+1)%7],0));u=(q-o).normalized();n=Vector((u.y,-u.x,0))
 if n.dot((o+q)/2-centre)<0:n=-n
 frames[i]=(o,u,n,(q-o).length)
col=bpy.data.collections['49L_EXTERIOR'];records=[]
for o in col.all_objects:
 if o.type!='MESH':continue
 parts=[];adj={v.index:set()for v in o.data.vertices}
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 seen=set()
 for seed in adj:
  if seed in seen:continue
  stack=[seed];seen.add(seed);part=[]
  while stack:
   k=stack.pop();part.append(k)
   for k2 in adj[k]:
    if k2 not in seen:seen.add(k2);stack.append(k2)
  pts=[o.matrix_world@o.data.vertices[k].co for k in part];c=sum(pts,Vector())/len(pts)
  edge=min(frames,key=lambda i:abs((c-frames[i][0]).dot(frames[i][2])));a,u,n,l=frames[edge]
  parts.append({'edge':edge,'x':c.dot(u)-a.dot(u),'depth':(c-a).dot(n),'z':c.z,'bounds':[[min((p-a).dot(u)for p in pts),max((p-a).dot(u)for p in pts)],[min((p-a).dot(n)for p in pts),max((p-a).dot(n)for p in pts)],[min(p.z for p in pts),max(p.z for p in pts)]],'vertexCount':len(part)})
 records.append({'name':o.name,'visible':not o.hide_render,'parts':parts,'materials':[m.name if m else None for m in o.data.materials]})
(OUT/'native-inventory.json').write_text(json.dumps({'ring':ring,'frames':{str(i):{'origin':list(o),'right':list(u),'outward':list(n),'length':l}for i,(o,u,n,l)in frames.items()},'objects':records},indent=2))

def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v145'):assert sha=='84e45149527c586960d8c8a9f3cf94d0a29a68e92fe5d17e251f45158fad00b3'
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v145'):assert len(original)==5754
O,U,N,L=frames[5];BAY=L/3

def point(x,d,z):return O+U*x+N*d+Vector((0,0,z))
def local(p):q=p-O;return q.dot(U),q.dot(N),p.z
owned=[];archives=[];changes=[];removed={}
# Replace only the first ground-storey bay adjacent to the registered No.50 boundary.
for rec in records:
 if not rec['visible']:continue
 old=bpy.data.objects[rec['name']]
 if not old.name.startswith('49L_D5_'):continue
 new=old.copy();new.data=old.data.copy();new.name=PREFIX+'retained_'+old.name.removeprefix('49L_D5_');col.objects.link(new)
 bm=bmesh.new();bm.from_mesh(new.data);seen=set();delete=[];trim=[]
 for seed in bm.verts:
  if seed in seen:continue
  stack=[seed];seen.add(seed);part=[]
  while stack:
   v=stack.pop();part.append(v)
   for e in v.link_edges:
    q=e.other_vert(v)
    if q not in seen:seen.add(q);stack.append(q)
  pts=[local(new.matrix_world@v.co)for v in part];a,b=min(p[0]for p in pts),max(p[0]for p in pts);c=sum(p[1]for p in pts)/len(pts)
  if abs(c)>.4 or min(p[2]for p in pts)<-.01 or max(p[2]for p in pts)>3.8001 or a<-.005 or a>=BAY-.001:continue
  if b<=BAY+.005:delete.extend(part)
  else:
   assert len(part)==8,(old.name,len(part))
   for v,p in zip(part,pts):
    if p[0]<BAY:v.co=new.matrix_world.inverted()@point(BAY,p[1],p[2])
   trim.extend(part)
 if not delete and not trim:
  bm.free();bpy.data.objects.remove(new,do_unlink=True);continue
 bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(new.data);bm.free();new.data.update()
 for mod in list(new.modifiers):
  if mod.type=='BEVEL':new.modifiers.remove(mod)
 owned.append(new);archives.append(old.name);old.hide_render=True;old.hide_set(True);removed[old.name]={'deletedVertices':len(delete),'trimmedVertices':len(trim)};changes.append({'source':old.name,'owned':new.name,'action':'Remove or trim only first Portsmouth ground bay; all other window bays, upper rows and corner retained.'})
assert '49L_D5_window_glass'in archives
materials={}
for key,source in [('glass','COOPERS_glass'),('black','COOPERS_black'),('white','COOPERS_white'),('blue','COOPERS_blue')]:materials[key]=bpy.data.materials[source]
grey=bpy.data.materials['COOPERS_white'].copy();grey.name=PREFIX+'fireexit_lightgrey';grey.diffuse_color=(.67,.68,.66,1);grey.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=grey.diffuse_color;materials['grey']=grey
# Historic circular window uses retained real glass optics; it is not the neighbour's external lamp.
glass=materials['glass'].copy();glass.name=PREFIX+'circular_window_glass_material';glass['webOpacity']=float(glass.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value);materials['glass']=glass

def make(name,mat,boxes=None,vertices=None,faces=None):
 vs=[]if vertices is None else vertices;fs=[]if faces is None else faces
 for x,d,z,w,t,h in boxes or []:
  start=len(vs);vs.extend(point(x+sx*w/2,d+sy*t/2,z+sz*h/2)for sx,sy,sz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]);fs.extend(tuple(start+k for k in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
 me=bpy.data.meshes.new(PREFIX+name);me.from_pydata(vs,[],fs);me.materials.append(mat);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();uv=me.uv_layers.new(name='SurfaceUV')
 for f in me.polygons:
  pts=[me.vertices[k].co for k in f.vertices];u=(pts[1]-pts[0]).normalized();v=f.normal.cross(u)
  for k,p in zip(f.loop_indices,pts):uv.data[k].uv=((p-pts[0]).dot(u),(p-pts[0]).dot(v))
 o=bpy.data.objects.new(PREFIX+name,me);col.objects.link(o);owned.append(o);changes.append({'source':None,'owned':o.name,'action':name.replace('_',' ')});return o
CX=.94;R=.30;CZ=3.11;A=CX-.50;B=CX+.50;DLO=.08;DHI=2.55;STRIP=1.78
# Full wall geometry with a door opening and a genuine circular aperture.
wall=[(A/2,-.12,1.9,A,.25,3.8),((STRIP+B)/2,-.12,1.9,STRIP-B,.25,3.8), (CX,-.12,DLO/2,B-A,.25,DLO),(CX,-.12,(DHI+CZ-R)/2,B-A,.25,CZ-R-DHI),(CX,-.12,(CZ+R+3.8)/2,B-A,.25,3.8-CZ-R),((A+CX-R)/2,-.12,CZ,CX-R-A,.25,2*R),((B+CX+R)/2,-.12,CZ,B-CX-R,.25,2*R)]
make('fireexit_wall_surround',materials['grey'],wall);make('retained_blue_bay_infill',materials['blue'],[((STRIP+BAY)/2,-.12,1.9,BAY-STRIP,.25,3.8)])
vs=[];fs=[]
for i in range(48):
 a,b=2*math.pi*i/48,2*math.pi*(i+1)/48
 corners=[]
 for d in [-.245,.005]:
  for t,outer in [(a,False),(b,False),(b,True),(a,True)]:
   rr=R/max(abs(math.cos(t)),abs(math.sin(t)))if outer else R;corners.append(point(CX+rr*math.cos(t),d,CZ+rr*math.sin(t)))
 s=len(vs);vs.extend(corners);fs.extend(tuple(s+k for k in f)for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
make('circular_aperture_surround',materials['grey'],vertices=vs,faces=fs)
make('fireexit_black_door',materials['black'],[(CX,-.16,(DLO+DHI)/2,B-A-.08,.05,DHI-DLO-.04)])
make('fireexit_stone_jambs_and_lintel',materials['grey'],[(A+.02,.045,(DLO+DHI)/2,.12,.16,DHI-DLO),(B-.02,.045,(DLO+DHI)/2,.12,.16,DHI-DLO),(CX,.045,DHI+.07,B-A+.15,.16,.14)])
# Flat dark door panels are shallow relief estimated from the 2022 photo, not new glazing.
make('fireexit_door_panels',materials['black'],[(x,-.115,z,.32,.045,h)for x in [CX-.22,CX+.22]for z,h in [(.65,.72),(1.68,.90)]])
vs=[point(CX,-.17,CZ)]+[point(CX+(R-.035)*math.cos(2*math.pi*i/48),-.17,CZ+(R-.035)*math.sin(2*math.pi*i/48))for i in range(48)];fs=[(0,1+i,1+(i+1)%48)for i in range(48)]
make('fireexit_circular_window_glass',materials['glass'],vertices=vs,faces=fs)
vs=[];fs=[]
for i in range(48):
 a,b=2*math.pi*i/48,2*math.pi*(i+1)/48;s=len(vs)
 vs.extend(point(CX+r*math.cos(t),d,CZ+r*math.sin(t))for d in [-.09,.055]for r,t in [(R-.035,a),(R-.035,b),(R+.045,b),(R+.045,a)]);fs.extend(tuple(s+k for k in f)for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
make('fireexit_circular_stone_frame',materials['white'],vertices=vs,faces=fs)
OWNED=[o.name for o in owned]
def check():
 trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons]))for o in bpy.data.objects if o.type=='MESH'and not o.hide_render and len(o.data.polygons)]
 result=[]
 samples=[('fireexit-door',point(CX,1,1.16),N,PREFIX+'fireexit_black_door'),('round-glass',point(CX,1,CZ),N,PREFIX+'fireexit_circular_window_glass'),('round-glass-left',point(CX-.14,1,CZ+.03),N,PREFIX+'fireexit_circular_window_glass'),('circle-frame',point(CX+R,1,CZ),N,PREFIX+'fireexit_circular_stone_frame'),('grey-wall',point(.21,1,2),N,PREFIX+'fireexit_wall_surround'),('blue-infill',point(2.5,1,2),N,PREFIX+'retained_blue_bay_infill')]
 for rec in records:
  if rec['visible']and rec['name']in ['49L_D5_window_glass','49L_D5_round_corner_window_glass']:
   for p in rec['parts']:
    if rec['name'].endswith('round_corner_window_glass'):continue
    edge=p['edge'];origin,u,n,length=frames[edge]
    if edge==5 and p['z']<4 and p['x']<BAY:continue
    pos=origin+u*(p['x']+.25)+n*1+Vector((0,0,p['z']+.21));expected=PREFIX+'retained_window_glass';samples.append(('retained-window',pos,n,expected))
 for kind,start,n,expected in samples:
  hits=[]
  for o,t in trees:
   hit=t.ray_cast(start,-n,1.7)
   if hit[0]is not None:hits.append((hit[3],o.name))
  actual=min(hits)[1]if hits else None;assert actual==expected,(kind,list(start),actual,expected)
  result.append({'kind':kind,'origin':list(start),'outward':list(n),'firstSurface':actual,'expected':expected})
 return result
checks=check();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'coopers-envelope-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True)
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':changes,'removedOrTrimmedParts':removed,'registration':{'ring':ring,'edge5':{'origin':list(O),'right':list(U),'outward':list(N),'length':L},'bayIndices':'Portsmouth bay0 nearNo50 x0..3.238741; bay1 x3.238741..6.477483 and bay2 x6.477483..9.716224 retain original restaurant windows. LincolnInnFields edge0 has2upperwindowbays×2rows; corneredge6 originaldoorandoculus unchanged.','planAnchor':'2022 blockplan red location dot on edge5 close to vertex5 shared49/50boundary; labelled circularwindowtobereplaced. Actual planning photo has blackdoor directlyleftofNo50 goldenarch and circularglass above it; No50A round external lamp is farther right and excluded.','dimensionsEstimated':{'fireexitCentreFromNo50Boundary':CX,'doorWidth':B-A,'doorBottom':DLO,'doorTop':DHI,'circleCentreHeight':CZ,'circleRadius':R,'lightgreyStripWidth':STRIP},'dimensionStatus':'Plan-derived building outline is inherited affine registration, not survey. Local door/circle/strip sizes are photo proportions estimated against retained3.8m groundstorey; not measured facade dimensions.'},'references':[{'path':'data/documents/coopers_block_plan_2022.pdf','documentDate':'2022-06-22','drawing':'RT22055-RTA-XX-XX-DR-A-00002PL01','url':'https://docs.planning.org.uk/20220826/115/RELXRTRPFZ800/nev73t6wc2rk72nq.pdf'},{'path':'data/documents/coopers_planning_2022.pdf','documentDate':'2022-06-30','photoCaption':'Existing Elevation to Portsmouth St','captureDate':'unknown; reproduced in2022planningstatement'},{'path':'data/建筑图片/49L_Coopers Restaurant/01_建筑实拍/exteriors_lse_estate_042.jpg','captureDate':'unknown','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate'}],'wholeEnvelopeAssessment':{'accepted':'Preserve2×2upperLincolnsInnFieldswindows, shutteredcreamupperstoreys, bluegroundwindows and cornerblackcanopy/upperoculus. Rectify missing nearNo50 fireexit and circular aperture instead of repeated restaurant glass.','unresolved':['UpperPortsmouth terminalstrip may physicallyoverlapredbrick49/50 sharedbuilding; plan definesrestaurantboundarybutphotodoesnotregister alluppertenancies. Retainnativeuppergeometry pendingcompleteelevation.','Roof/parapetornament and unseenrear remainestimated; photographs donotestablishflatdeckheight10.9m.','2022proposedcircularlouvreinstallationnotconfirmed; thiscomponentmodels2022existingroundglass only.','CurrentlightgreyversusolderbluePortsmouthpaintsequence unknown; localgreyfireexitstrip follows2022photo withoutrepaintingothergroundwalls.']},'glazingOpticsChanged':False,'glassWebOpacity':float(materials['glass'].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value),'firstSurfaceChecks':checks}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['49L_EXTERIOR']
for o in list(bpy.data.objects):
 if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
for name in archives:
 o=bpy.data.objects[name];o.hide_render,o.hide_viewport=visibility[name][:2];o.hide_set(visibility[name][2])
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  m=slot.material
  if m and'.'in m.name and m.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(m.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for name in archives:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
reloaded=check();assert reloaded==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in archives)
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(original),'unrelatedVisibilityPreserved':True,'fullModelSaved':False,'firstSurfaceChecks':reloaded,'checkCount':len(reloaded),'neighbour50GeometryAndVisibilityPreserved':all(fingerprint(bpy.data.objects[n])==v and[bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==visibility[n]for n,v in original.items()if n.startswith('50L')),'originalCornerOculusPreserved':fingerprint(bpy.data.objects['49L_D5_round_corner_window_glass'])==original['49L_D5_round_corner_window_glass']}
visible={o.name for o in col.all_objects}|{o.name for o in bpy.data.collections['50L_EXTERIOR'].all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=point(L/2,-1,5.3);camera=focus+N*29-U*17+Vector((0,0,7));cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=camera;cam.rotation_euler=(focus-camera).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=21;scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-envelope.png')
if not(OUT/'reloaded-envelope.png').exists():bpy.ops.render.render(write_still=True)
proof['camera']={'position':list(camera),'target':list(focus),'orthoScale':21};proof['nativePreview']=str(OUT/'reloaded-envelope.png');(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('COOPERS_VERIFIED',len(original),len(owned),len(archives),len(checks));bpy.ops.wm.quit_blender()
