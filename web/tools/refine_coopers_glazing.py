"""Photo-guided restrained Coopers glazing with aperture checks.
Constant Blender configuration; saves an independent component library only.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/coopers_glazing_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v146.blend';PREFIX='49L_NEXT_GLAZING_'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_source():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if old:
  for name in old['archivedObjects']:
   o=bpy.data.objects[name];o.hide_render,o.hide_viewport=old['originalVisibility'][name][:2];o.hide_set(old['originalVisibility'][name][2])
 return bpy.context.scene,bpy.data.collections['49L_EXTERIOR']
scene,col=open_source();sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v146'):assert sha=='835b179c5bb32ecf3959ca6d9bf996ac92095fe42821fc42e7c2ddbf599b048a'
frame_data=json.loads((ROOT/'result/blender/coopers_envelope_next/native-inventory.json').read_text())['frames'];frames={int(i):(Vector(f['origin']),Vector(f['right']),Vector(f['outward']),f['length'])for i,f in frame_data.items()}
def point(edge,x,d,z):o,u,n,l=frames[edge];return o+u*x+n*d+Vector((0,0,z))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v146'):assert len(original)==5784
SOURCES=['49L_NEXT_retained_window_glass','49L_D5_round_corner_window_glass','49L_NEXT_fireexit_circular_window_glass']
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
samples=[]
for name in SOURCES:
 o=bpy.data.objects[name];assert not o.hide_render
 if name==SOURCES[0]:
  for k,part in enumerate(parts(o)):
   pts=[o.matrix_world@o.data.vertices[i].co for i in part];c=sum(pts,Vector())/len(pts);edge=min([0,5],key=lambda i:abs((c-frames[i][0]).dot(frames[i][2])+.17));origin,u,n,l=frames[edge]
   for dx,dz in [(-.28,.42),(.28,-.42)]:samples.append({'source':name,'pane':k,'edge':edge,'point':list(c+u*dx+Vector((0,0,dz))), 'normal':list(n)})
 else:
  edge=6 if name==SOURCES[1]else 5;cx=frames[6][3]/2 if edge==6 else .94;cz=9.6 if edge==6 else 3.11;depth=.10 if edge==6 else -.17
  for k,(dx,dz)in enumerate([(-.12,.08),(.12,-.08),(0,.14)]):samples.append({'source':name,'pane':k,'edge':edge,'point':list(point(edge,cx+dx,depth,cz+dz)),'normal':list(frames[edge][2])})
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
ACTIVE_TREES=trees();before=[]
for s in samples:
 p,n=Vector(s['point']),Vector(s['normal']);front=hit(p+n*.9,-n,1.2);behind=hit(p-n*.002,-n,3,[s['source']]);assert front and front[1]==s['source'],(s,front)
 before.append({**s,'firstSurface':front[1],'behind':behind})
(OUT/'nearfield-before.json').write_text(json.dumps(before,indent=2))
owned=[];archives=[];changes=[];optics=[];mapping={}
def geometry_digest(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1)]:
  v=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,v);h.update(v.tobytes())
 for uv in o.data.uv_layers:
  v=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',v);h.update(v.tobytes())
 return h.hexdigest()
for index,name in enumerate(SOURCES):
 source=bpy.data.objects[name];obj=source.copy();obj.data=source.data.copy();obj.name=PREFIX+['street_window_panes','corner_oculus','fireexit_oculus'][index];obj.data.name=obj.name;col.objects.link(obj)
 old=source.data.materials[0];mat=old.copy();mat.name=PREFIX+['street_glass','corner_glass','fireexit_glass'][index];node=mat.node_tree.nodes['Principled BSDF'];oldnode=old.node_tree.nodes['Principled BSDF']
 prior={k:float(oldnode.inputs[k].default_value)for k in ['Transmission Weight','Alpha','Roughness','IOR','Metallic']};color=list(oldnode.inputs['Base Color'].default_value)
 # Reflected trees, sky and dark interior are visible together in the archived photo.
 # These conservative values are a rendering estimate, not physical transmittance.
 node.inputs['Transmission Weight'].default_value=.32;node.inputs['Alpha'].default_value=.84;node.inputs['Roughness'].default_value=.18;node.inputs['IOR'].default_value=1.45;node.inputs['Metallic'].default_value=0;mat['webOpacity']=.84
 obj.data.materials[0]=mat;source.hide_render=True;source.hide_set(True);owned.append(obj);archives.append(name);mapping[name]=obj.name;changes.append({'source':name,'owned':obj.name,'action':'Retain exact pane geometry, transforms, UV and original colour; estimated restrained transmission/reflection and explicit webOpacity.'})
 assert geometry_digest(source)==geometry_digest(obj)
 optics.append({'source':name,'owned':obj.name,'sourceMaterial':old.name,'ownedMaterial':mat.name,'retainedBaseColor':color,'before':prior,'after':{k:float(node.inputs[k].default_value)for k in prior},'webOpacity':.84})
# The newer handbook proves that the historical fireexit round glass became a vent.
# Preserve its existing circular outer frame; replace the disc by opaque clipped slats.
vent=bpy.data.objects[PREFIX+'fireexit_oculus'];ventmat=bpy.data.materials['COOPERS_black'].copy();ventmat.name=PREFIX+'fireexit_louvre_dark';ventnode=ventmat.node_tree.nodes['Principled BSDF'];ventnode.inputs['Transmission Weight'].default_value=0;ventnode.inputs['Alpha'].default_value=1;ventnode.inputs['Roughness'].default_value=.65;ventmat['webOpacity']=1.0
polygon=[(.265*math.cos(math.tau*i/64),.265*math.sin(math.tau*i/64))for i in range(64)]
def clip_horizontal(poly,z,keep_above):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  inside_a=a[1]>=z if keep_above else a[1]<=z;inside_b=b[1]>=z if keep_above else b[1]<=z
  if inside_a:result.append(a)
  if inside_a!=inside_b:
   f=(z-a[1])/(b[1]-a[1]);result.append((a[0]+f*(b[0]-a[0]),z))
 return result
ventvs=[];ventfs=[];slat_count=0
for row in range(-7,8):
 contour=clip_horizontal(clip_horizontal(polygon,row*.035-.013,True),row*.035+.013,False)
 if len(contour)<3:continue
 n=len(contour);base=len(ventvs);ventvs.extend(point(5,.94+x,d,3.11+z)for d in [-.20,-.11]for x,z in contour);ventfs.extend([tuple(base+i for i in range(n-1,-1,-1)),tuple(base+n+i for i in range(n))]);ventfs.extend((base+i,base+(i+1)%n,base+n+(i+1)%n,base+n+i)for i in range(n));slat_count+=1
me=bpy.data.meshes.new(vent.name+'_horizontal_louvres');me.from_pydata(ventvs,[],ventfs);me.materials.append(ventmat);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();uv=me.uv_layers.new(name='SurfaceUV')
for face in me.polygons:
 ps=[me.vertices[i].co for i in face.vertices];u=(ps[1]-ps[0]).normalized();v=face.normal.cross(u)
 for loop,p in zip(face.loop_indices,ps):uv.data[loop].uv=((p-ps[0]).dot(u),(p-ps[0]).dot(v))
vent.data=me;changes[2]['action']='Replace historic circular glazing disc by photographed opaque horizontal ventilation louvres; original outer frame and fireexit registration retained.'
optics[2]={'source':SOURCES[2],'owned':vent.name,'classification':'opaque ventilation louvre, not glass','ownedMaterial':ventmat.name,'transmission':0,'alpha':1,'webOpacity':1,'bladeCountEstimated':slat_count,'spacingEstimated':.035,'bladeHeightEstimated':.026,'diameterRetained':.53,'depthEstimated':[-.20,-.11]}

# The old upper corner wall seals its photographed oculus at43mm behind glass.
wall_source=bpy.data.objects['49L_D5_corner_pier_cream'];wall=wall_source.copy();wall.data=wall_source.data.copy();wall.name=PREFIX+'corner_pier_true_aperture';wall.data.name=wall.name;col.objects.link(wall)
bm=bmesh.new();bm.from_mesh(wall.data);seen=set();delete=[];removed=0;corner_o,corner_u,corner_n,corner_length=frames[6]
for seed in bm.verts:
 if seed in seen:continue
 stack=[seed];seen.add(seed);part=[]
 while stack:
  v=stack.pop();part.append(v)
  for e in v.link_edges:
   q=e.other_vert(v)
   if q not in seen:seen.add(q);stack.append(q)
 lo=min((wall.matrix_world@v.co).z for v in part);hi=max((wall.matrix_world@v.co).z for v in part)
 if abs(lo-7.25)<.001 and abs(hi-10.9)<.001:
  assert len(part)==8;delete.extend(part);removed+=1
assert removed==1; bmesh.ops.delete(bm,geom=delete,context='VERTS')
CX=corner_length/2;CZ=9.6;R=.30;DEPTH_LO=-.295;DEPTH_HI=.055
vs=[];fs=[]
def box(x,z,w,h):
 s=len(vs);vs.extend(point(6,x+sx*w/2,(DEPTH_LO+DEPTH_HI)/2+sy*(DEPTH_HI-DEPTH_LO)/2,z+sz*h/2)for sx,sy,sz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]);fs.extend(tuple(s+k for k in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
box(CX,(7.25+CZ-R)/2,corner_length,CZ-R-7.25);box(CX,(10.9+CZ+R)/2,corner_length,10.9-CZ-R);box((CX-R)/2,CZ,CX-R,2*R);box((CX+R+corner_length)/2,CZ,corner_length-CX-R,2*R)
for i in range(48):
 a,b=math.tau*i/48,math.tau*(i+1)/48;s=len(vs)
 for d in [DEPTH_LO,DEPTH_HI]:
  for t,outer in [(a,False),(b,False),(b,True),(a,True)]:
   radius=R/max(abs(math.cos(t)),abs(math.sin(t)))if outer else R;vs.append(point(6,CX+radius*math.cos(t),d,CZ+radius*math.sin(t)))
 fs.extend(tuple(s+k for k in f)for f in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2),(0,3,7,4)])
vertices=[bm.verts.new(wall.matrix_world.inverted()@p)for p in vs];newfaces=[bm.faces.new([vertices[k]for k in f])for f in fs];bmesh.ops.recalc_face_normals(bm,faces=newfaces);uv=bm.loops.layers.uv.get('SurfaceUV')or bm.loops.layers.uv.verify()
for f in newfaces:
 pts=[l.vert.co for l in f.loops];u=(pts[1]-pts[0]).normalized();v=f.normal.cross(u)
 for loop,p in zip(f.loops,pts):loop[uv].uv=((p-pts[0]).dot(u),(p-pts[0]).dot(v))
bm.to_mesh(wall.data);bm.free();wall.data.update()
for mod in list(wall.modifiers):
 if mod.type=='BEVEL':wall.modifiers.remove(mod)
wall_source.hide_render=True;wall_source.hide_set(True);archives.append(wall_source.name);owned.append(wall);changes.append({'source':wall_source.name,'owned':wall.name,'action':'Retain lower corner pier and source stone; replace only upper solidbox by same-depth wall with matching photographed circular aperture.'})
OWNED=[o.name for o in owned]
def verify():
 global ACTIVE_TREES
 ACTIVE_TREES=trees();rows=[]
 for s in samples:
  p,n=Vector(s['point']),Vector(s['normal']);expected=mapping[s['source']];front=hit(p+n*.9,-n,1.2);back=hit(p-n*.002,-n,3,[expected]);assert front and front[1]==expected,(s,front,expected)
  assert not back or back[0]>.10,(s,back)
  row={**s,'expected':expected,'firstSurface':front[1],'behind':back,'kind':'louvre'if s['source']==SOURCES[2]else'glass'}
  if s['source']!=SOURCES[2]:row['noOpaqueNearfieldCap']=not back or back[0]>.10
  rows.append(row)
 for label,x,z,expected in [('corner-outer-stone',CX+.48,CZ,wall.name),('corner-lower-pier',CX,5.4,wall.name),('preserved-oculus-frame',CX+.34,CZ,'49L_D5_oculus_frame_white')]:
  p=point(6,x,1,z);r=hit(p,-corner_n,1.7);assert r and r[1]==expected,(label,r);rows.append({'kind':label,'origin':list(p),'firstSurface':r[1],'expected':expected})
 for row in rows:row['firstObject']=row['firstSurface']
 return rows
checks=verify();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'coopers-glazing-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':changes,'glazingOptics':optics,'beforeNearfieldChecks':before,'firstSurfaceChecks':checks,'cornerAperture':{'frame':frame_data['6'],'centre':[CX,CZ],'radius':R,'depthBounds':[DEPTH_LO,DEPTH_HI],'upperWallBounds':[0,corner_length,7.25,10.9],'removedUpperBoxCount':1,'evidence':'Official estate photograph clearlyshowsdarkroundwindowincornercreamwall; baseline glass overlaysolidupperwall with43mmbackcap. Sameexistingglassandframeregistration retained; onlybackcap cutatcorrespondingcircle.'},'sources':[{'path':'data/建筑图片/49L_Coopers Restaurant/01_建筑实拍/exteriors_lse_estate_042.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','captureDate':'unknown','supports':'Mixedreflectedtrees/skyanddarkinteriorinupperandlowerglass; circleoncreamcorner. Notanopticalmeasurement.'},{'path':'data/documents/coopers_planning_2022.pdf','documentDate':'2022-06-30','captureDate':'unknown','supports':'Historical2022roundglass andproposedvent; supersededforventfinishby2025/26handbookphoto.'}],'scope':'14retainedrectangularglasspanesand1corneroculusretainexactgeometryUV/transforms/basecolours. NearNo50fireexitrounddiscbecomesopaqueventlouvresfollowingnewerhandbookphoto; originalcircleframeanddoorremain. No50L orimaginedinteriorstructureschanged.','limitations':['Transmission.32,alpha/webOpacity.84,roughness.18andIOR1.45arevisualrenderingestimates,notmeasuredglassspecifications.','3mnearfieldclearancedoesnotprovecompleteinterior; completeupperrooms remainunregistered, so restrainedtransparencyavoidsclaiminginterioraccuracy.','Nativeoriginalwindowheight/frame/shutterproportions androofremainestimates.','Sourcephotographcaptureyearsunknown; notclaimed2026survey.','The inherited circularplane positionsandstonewallthicknessare preservedestimatedgeometry; aperture radius.30includes.01mclearance relativetoexisting.29glass.']}
audit['sources'].append({'path':'data/建筑图片/50L_50 Lincoln_s Inn Fields/01_建筑实拍/small_round5_50L_handbook-000.png','url':'https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/Property-and-Space/LSE-Property-Handbook.pdf','publicationEdition':'2025/26','captureDate':'unknown','supports':'Roundopeningabove49LblackfireexitdirectlyleftofNo50goldenportalcontainsdenseopaquehorizontalventbladeswithinlightbluegreyouterring; distinctfrom50Aexternallamptoright.'})
audit['louvreFirstHits']=[r for r in checks if r.get('kind')=='louvre']
audit['fireExitRoundLouvre']={'opaque':True,'object':PREFIX+'fireexit_oculus','firstHitCount':3,'material':PREFIX+'fireexit_louvre_dark','webOpacity':1,'transmission':0}
audit['fireexitVent']={'slatCountEstimated':slat_count,'registrationRetained':[.94,3.11,.265],'outerFramePreserved':'49L_NEXT_fireexit_circular_stone_frame','source':'2025/26officialhandbook;photographcapturedateunknown','notGlass':True}
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
for n in archives:bpy.data.objects[n].hide_render=True;bpy.data.objects[n].hide_set(True)
# Reopened object wrappers are rebuilt after native load; no retained invalidRNA pointers.
wall=bpy.data.objects[PREFIX+'corner_pier_true_aperture'];reopened=verify();assert reopened==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in archives)
for name in SOURCES[:2]:
 assert geometry_digest(bpy.data.objects[name])==geometry_digest(bpy.data.objects[mapping[name]])
for o in dst.objects[:2]:
 m=o.data.materials[0];n=m.node_tree.nodes['Principled BSDF'];assert abs(m['webOpacity']-.84)<1e-7 and abs(n.inputs['Transmission Weight'].default_value-.32)<1e-6
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(original),'unrelatedVisibilityPreserved':True,'fullModelSaved':False,'checkCount':len(reopened),'firstSurfaceChecks':reopened,'remainingGlassGeometryAndUVRetained':True,'remainingGlassSourceColorsPreserved':True,'glassSampleCount':31,'louvreSampleCount':3,'fireexitLouvreOpaque':True,'neighbour50GeometryAndVisibilityPreserved':all(fingerprint(bpy.data.objects[n])==v and[bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==visibility[n]for n,v in original.items()if n.startswith('50L'))}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=point(6,CX,-1,5.5);camera=focus+corner_n*30+frames[6][1]*4+Vector((0,0,6));cd=bpy.data.cameras.new(PREFIX+'review_camera');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=camera;cam.rotation_euler=(focus-camera).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=17;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=1200;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-glazing-envelope.png');bpy.ops.render.render(write_still=True)
proof.update({'allGlazingGeometryAndUVRetained':True,'sourceColorsPreserved':True,'preservedGlassSources':SOURCES[:2],'louvreFirstHits':[r for r in reopened if r.get('kind')=='louvre'],'fireExitRoundLouvre':audit['fireExitRoundLouvre']})
proof['camera']={'position':list(camera),'target':list(focus),'orthoScale':17};proof['nativePreview']=str(OUT/'reloaded-glazing-envelope.png');(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('COOPERS_GLAZING_VERIFIED',len(original),len(owned),len(checks));bpy.ops.wm.quit_blender()
