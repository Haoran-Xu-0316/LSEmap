"""Correct the three fully photographed SHF dormers to six lights.
Run in Blender. Private component output, no complete-campus save or CLI options.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/shf_exterior148';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v147.blend';PREFIX='SHF_NEXT_148_';SOURCE='SHF_V50_dormer_mullion_frame'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
def open_source():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 old=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if old:
  for name in old['archivedObjects']:
   o=bpy.data.objects[name];o.hide_render,o.hide_viewport=old['originalVisibility'][name][:2];o.hide_set(old['originalVisibility'][name][2])
 return bpy.context.scene,bpy.data.collections['SHF_EXTERIOR']
scene,col=open_source();sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   v=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,v);h.update(v.tobytes())
  for uv in o.data.uv_layers:
   v=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',v);h.update(v.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());ring=next(x for x in site['buildings']if x['code']=='SHF')['rings'][0];O=Vector((*ring[0],0));END=Vector((*ring[6],0));U=(END-O).normalized();N=Vector((-U.y,U.x,0));centre=sum((Vector((*r,0))for r in ring),Vector())/len(ring)
if N.dot((O+END)/2-centre)<0:N=-N
L=(END-O).length;PITCH=L/4;CENTRES=[PITCH*(i+.5)for i in range(4)];WIDTH=2.25;Z=17.65;HEIGHT=1.14

def point(x,d,z):return O+U*x+N*d+Vector((0,0,z))
def local(p):q=p-O;return q.dot(U),q.dot(N),p.z
source=bpy.data.objects[SOURCE];assert not source.hide_render;copy=source.copy();copy.data=source.data.copy();copy.name=PREFIX+'retained_unknown_left_dormer';copy.data.name=copy.name;col.objects.link(copy)
bm=bmesh.new();bm.from_mesh(copy.data);seen=set();delete=[];removed=[];preserved=[]
for seed in bm.verts:
 if seed in seen:continue
 stack=[seed];seen.add(seed);part=[]
 while stack:
  v=stack.pop();part.append(v)
  for e in v.link_edges:
   q=e.other_vert(v)
   if q not in seen:seen.add(q);stack.append(q)
 pts=[local(copy.matrix_world@v.co)for v in part];c=[sum(p[k]for p in pts)/len(pts)for k in range(3)];bay=min(range(4),key=lambda i:abs(CENTRES[i]-c[0]));assert abs(c[1]+.025)<.002 and abs(c[2]-Z)<.002,(c,bay)
 if bay in [1,2,3]:
  assert len(part)==8;delete.extend(part);removed.append({'bay':bay,'centre':c})
 else:preserved.append(c)
assert len(removed)==9 and len(preserved)==3,(removed,preserved)
bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(copy.data);bm.free();copy.data.update()
for mod in list(copy.modifiers):
 if mod.type=='BEVEL':copy.modifiers.remove(mod)
vs=[];fs=[]
for bay in [1,2,3]:
 for j in range(1,6):
  x=CENTRES[bay]-WIDTH/2+WIDTH*j/6;w=.072 if j==3 else .030;s=len(vs)
  vs.extend(point(x+sx*w/2,-.025+sy*.12/2,Z+sz*HEIGHT/2)for sx,sy,sz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]);fs.extend(tuple(s+k for k in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
me=bpy.data.meshes.new(PREFIX+'six_light_dormer_mullions');me.from_pydata(vs,[],fs);me.materials.append(source.data.materials[0]);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();uv=me.uv_layers.new(name='SurfaceUV')
for f in me.polygons:
 p=[me.vertices[k].co for k in f.vertices];u=(p[1]-p[0]).normalized();v=f.normal.cross(u)
 for loop,q in zip(f.loop_indices,p):uv.data[loop].uv=((q-p[0]).dot(u),(q-p[0]).dot(v))
obj=bpy.data.objects.new(me.name,me);col.objects.link(obj);source.hide_render=True;source.hide_set(True);owned=[copy,obj];OWNED=[o.name for o in owned];ARCHIVED=[SOURCE]
glass=bpy.data.objects['SHF_V50_dormer_glass_glass'];original_glass=fingerprint(glass)
shader=glass.data.materials[0].node_tree.nodes['Principled BSDF'];glass_optics={'material':glass.data.materials[0].name,'baseColor':list(shader.inputs['Base Color'].default_value),'alpha':float(shader.inputs['Alpha'].default_value),'transmission':float(shader.inputs['Transmission Weight'].default_value),'roughness':float(shader.inputs['Roughness'].default_value),'webOpacity':glass.data.materials[0].get('webOpacity')}
def check():
 vertices=[];faces=[];owners=[]
 for o in col.all_objects:
  if o.type!='MESH'or o.hide_render:continue
  offset=len(vertices);vertices.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(offset+i for i in f.vertices)for f in o.data.polygons);owners.extend([o.name]*len(o.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);locations=[]
 for bay in [1,2,3]:
  x=CENTRES[bay]
  for light in range(6):
   for row in [-1,1]:locations.append(('glass',bay,light,point(x-WIDTH/2+WIDTH*(light+.5)/6,1,Z+row*.27),'SHF_V50_dormer_glass_glass'))
  for j in range(1,6):
   for row in [-1,1]:locations.append(('new-mullion',bay,j,point(x-WIDTH/2+WIDTH*j/6,1,Z+row*.27),PREFIX+'six_light_dormer_mullions'))
  locations.append(('retained-horizontal-transom',bay,None,point(x-WIDTH/2+WIDTH*.5/6,1,Z),'SHF_V50_dormer_transom_frame'))
 for j in range(1,4):locations.append(('unseen-left-mullion-preserved',0,j,point(CENTRES[0]-WIDTH/2+WIDTH*j/4,1,Z+.27),PREFIX+'retained_unknown_left_dormer'))
 result=[]
 for kind,bay,light,start,expected in locations:
  hit=tree.ray_cast(start,-N,1.5);actual=owners[hit[2]]if hit[2]is not None else None;assert actual==expected,(kind,bay,light,actual,expected)
  result.append({'kind':kind,'bay':bay,'light':light,'origin':list(start),'firstSurface':actual,'firstObject':actual,'expected':expected})
 return result
checks=check();assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
component=OUT/'sheffield-dormer-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':sha,'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':ARCHIVED,'changes':[{'source':SOURCE,'owned':OWNED[0],'action':'Retain exactly three old bars in obscured left dormer; remove9oldbars only from3fullypicturedright dormers.'},{'source':None,'owned':OWNED[1],'action':'15verticalbars form6lights per dormer, withwidecentralpostbetween2groups of3and thinner internalbars.'}],'registration':{'origin':list(O),'right':list(U),'outward':list(N),'frontLength':L,'centres':CENTRES,'changedBays':[1,2,3],'unchangedBay':0,'retainedWindowWidth':WIDTH,'retainedWindowCentreZ':Z,'retainedWindowHeight':HEIGHT,'newBarXFractions':[1/6,2/6,3/6,4/6,5/6],'centralBarWidthEstimated':.072,'fineBarWidthEstimated':.030,'depthAndHeightRetained':[-.025,.12,HEIGHT],'removedBars':removed,'unseenLeftBarsPreserved':preserved},'sources':[{'path':'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/exteriors_lse_estate_027.jpg','url':'https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','captureDate':'unknown','sha256':hashlib.sha256((ROOT/'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/exteriors_lse_estate_027.jpg').read_bytes()).hexdigest(),'supports':'Three rightmost dormers have 6lights and2rows, centralwidepostdividingtwo3lightcasements. Leftmostdormer partly scaffold-obscured. EXIForientation6 corrected for inspection only.'},{'path':'data/建筑图片/SHF_Sheffield Street/01_建筑实拍/small_round5_SHF_handbook-000.png','publicationEdition':'2025/26','captureDate':'unknown','supports':'Fourbaymainfrontage,whitebase/upperbrickandglazedentry;roofnotcovered. Thesealreadycorrectedpartsunchanged.'}],'wholeEnvelopeAssessment':{'matched':'4mainfrontagebays, white2levelbase, buffbrickupper, main6-lightpairedframes andglazedtimberentryalreadycorrected; not rebuilt thisround.','changed':'Wrong4-lightdormerpattern correctedto6lights in3completephoto-coveredwindows.','remaining':'Unknownleftdormerunder scaffold, roofdepth/backfaces, completeinteriorandexactcolour/height remainestimated.'},'glassOpticsRetained':glass_optics,'firstSurfaceChecks':checks,'limitations':['Photo capturedateunknown; not2026survey.','Windowwidth,height,roofplacementandmainwallgeometryare inheritedestimates.','Bar profiles andequal6-light spacing visuallyestimatedfromobliquephoto; notphotogrammetricsurvey.','Photo shows2groups of3lights separatedbywidecentralpost, not3groups of2 inferredfrommainwindow pattern.','Glass remains originalmaterial/optics; no addedtransparency or inventedinterior.']}
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
for n in ARCHIVED:bpy.data.objects[n].hide_render=True;bpy.data.objects[n].hide_set(True)
reopened=check();assert reopened==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in ARCHIVED);assert fingerprint(bpy.data.objects['SHF_V50_dormer_glass_glass'])==original_glass
node=bpy.data.objects['SHF_V50_dormer_glass_glass'].data.materials[0].node_tree.nodes['Principled BSDF'];assert float(node.inputs['Alpha'].default_value)==glass_optics['alpha']and float(node.inputs['Transmission Weight'].default_value)==glass_optics['transmission']
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(original),'unrelatedVisibilityPreserved':True,'fullModelSaved':False,'checkCount':len(reopened),'firstSurfaceChecks':reopened,'glassGeometryUVMaterialAndOpticsPreserved':True,'glassOptics':glass_optics,'unknownLeftDormerRetained':True}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in ['MESH','FONT','CURVE']and o.name not in visible:o.hide_render=True
focus=point(L/2,0,14);position=focus+N*37+U*2+Vector((0,0,5));cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=position;cam.rotation_euler=(focus-position).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=20;scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-dormer-envelope.png');bpy.ops.render.render(write_still=True)
proof['camera']={'position':list(position),'target':list(focus),'orthoScale':20};proof['nativePreview']=str(OUT/'reloaded-dormer-envelope.png');(OUT/'verification.json').write_text(json.dumps(proof,indent=2));print('SHF148_VERIFIED',len(original),len(OWNED),len(reopened));bpy.ops.wm.quit_blender()
