"""Register PAN's photographed lower frontage as five individually framed windows.
Constant Blender configuration. Saves a component library, never a full campus.
"""
from pathlib import Path
import array,hashlib,json
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/pankhurst_envelope_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v141.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
PREFIX='PAN_NEXT_ENVELOPE_';OLD=['PAN_D3_recessed_window_bands','PAN_D3_slender_window_mullions','PAN_D3_window_heads_and_sills','PAN_D3_precast_panel_vertical_joints']
FRAME=json.loads((ROOT/'result/blender/stage88/tower-entry-audit.json').read_text())['frame'];O,U,N=[Vector(FRAME[k])for k in ['origin','right','outward']]
L=11.878583169542;LO=.23;HI=L-.23;PITCH=(HI-LO)/5;ROWS=[(5.66+f*3.3,7.65+f*3.3)for f in range(5)]
def point(x,d,z):return O+U*x+N*d+Vector((0,0,z))
def local(p):q=p-O;return q.dot(U),q.dot(N),p.z
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   v=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,v);h.update(v.tobytes())
  for layer in o.data.uv_layers:
   v=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',v);h.update(v.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
def open_base():
 bpy.ops.wm.open_mainfile(filepath=str(BASE));bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
 previous=json.loads((OUT/'audit.json').read_text())if (OUT/'audit.json').exists()else None
 for o in list(bpy.data.objects):
  if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
 if previous:
  for name in previous['archivedObjects']:
   state=previous['originalVisibility'][name];o=bpy.data.objects[name];o.hide_render,o.hide_viewport=state[:2];o.hide_set(state[2])
 return bpy.context.scene,bpy.data.collections['PAN_EXTERIOR']
scene,col=open_base();originals={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects};owned=[];removed={};changes=[]
for source,depth,expected in zip(OLD,[-.20,-.10,-.055,.064],[5,45,10,15]):
 old=bpy.data.objects[source];assert not old.hide_render;new=old.copy();new.data=old.data.copy();new.name=PREFIX+'retained_'+source.removeprefix('PAN_D3_');col.objects.link(new)
 for m in list(new.modifiers):
  if m.type=='BEVEL':new.modifiers.remove(m)
 bm=bmesh.new();bm.from_mesh(new.data);seen=set();selected=[];count=0
 for seed in bm.verts:
  if seed in seen:continue
  stack=[seed];part=[];seen.add(seed)
  while stack:
   v=stack.pop();part.append(v)
   for e in v.link_edges:
    q=e.other_vert(v)
    if q not in seen:seen.add(q);stack.append(q)
  coords=[local(new.matrix_world@v.co)for v in part];center=[sum(p[k]for p in coords)/len(coords)for k in range(3)]
  if abs(center[1]-depth)<.002 and -.01<center[0]<L+.01 and 4.5<center[2]<21.01:
   assert len(part)==8,(source,center,len(part));selected.extend(part);count+=1
 assert count==expected,(source,count,expected)
 bmesh.ops.delete(bm,geom=selected,context='VERTS');bm.to_mesh(new.data);bm.free();new.data.update();owned.append(new);removed[source]=count;old.hide_render=True;old.hide_set(True);changes.append({'source':source,'owned':new.name,'action':'Retain all other elevations and upper rows; remove only registered lower-five-row frontage parts.'})
materials={}
for key,source in [('glass','PAN_D3_glass'),('frame','PAN_D3_frame'),('joint','PAN_D3_joint')]:
 m=bpy.data.materials[source].copy();m.name=PREFIX+key;materials[key]=m
# Preserve original finish and optical values; the primary correction is window rhythm.
def geometry(name,material,boxes):
 vs=[];fs=[]
 for x,d,z,w,t,h in boxes:
  start=len(vs);vs.extend(point(x+sx*w/2,d+sy*t/2,z+sz*h/2)for sx,sy,sz in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]);fs.extend(tuple(start+k for k in f)for f in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)])
 me=bpy.data.meshes.new(PREFIX+name);me.from_pydata(vs,[],fs);me.materials.append(material);me.update();uv=me.uv_layers.new(name='SurfaceUV')
 for f in me.polygons:
  p=[me.vertices[k].co for k in f.vertices];u=(p[1]-p[0]).normalized();v=f.normal.cross(u)
  for i,c in zip(f.loop_indices,p):uv.data[i].uv=((c-p[0]).dot(u),(c-p[0]).dot(v))
 o=bpy.data.objects.new(PREFIX+name,me);col.objects.link(o);owned.append(o);changes.append({'source':None,'owned':o.name,'action':name.replace('_',' ')})
glass=[];frames=[];joints=[]
for row,(low,high)in enumerate(ROWS):
 for k in range(5):
  a,b=LO+k*PITCH,LO+(k+1)*PITCH;mid=(a+b)/2;z=(low+high)/2;h=high-low
  glass.append((mid,-.20,z,PITCH-.10,.03,h-.10))
  for x in [a+.025,b-.025]:frames.append((x,-.10,z,.05,.13,h))
  for zz in [low+.025,high-.025]:frames.append((mid,-.10,zz,PITCH,.13,.05))
 for k in range(1,5):joints.append((LO+PITCH*k,.064,4.4+row*3.3+.61,.013,.01,1.18))
geometry('five_module_glass',materials['glass'],glass);geometry('individual_perimeter_frames',materials['frame'],frames);geometry('aligned_spandrel_joints',materials['joint'],joints)
OWNED=[o.name for o in owned]
def probes():
 trees=[(o,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons],all_triangles=False))for o in col.all_objects if o.type=='MESH'and not o.hide_render and len(o.data.polygons)]
 result=[]
 for row,(low,high)in enumerate(ROWS):
  z=(low+high)/2
  samples=[]
  for k in range(5):
   a=LO+k*PITCH;b=a+PITCH
   samples += [('glass',a+PITCH*f,z+(high-low)*v,PREFIX+'five_module_glass')for f,v in [(.3,.25),(.7,-.25)]]
   samples += [('individual-jamb',a+.025,z,PREFIX+'individual_perimeter_frames'),('individual-head',(a+b)/2,high-.045,PREFIX+'individual_perimeter_frames'),('retained-head-flashing',(a+b)/2,high+.002,'PAN_D5_V17_flashing_downstand')]
  samples += [('old-eight-light-bar',LO+(HI-LO)*k/8,z+.2,PREFIX+'five_module_glass')for k in [1,2,3,5,6,7]]
  for kind,x,pz,expected in samples:
   start=point(x,1,pz);best=None
   for o,tree in trees:
    hit=tree.ray_cast(start,-N,3)
    if hit[0]is not None and(best is None or hit[3]<best[0]):best=(hit[3],o.name)
   assert best and best[1]==expected,(row,kind,x,pz,best,expected)
   result.append({'row':row,'kind':kind,'localPoint':[x,1,pz],'firstSurface':best[1]})
 return result
checks=probes();assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'pankhurst-envelope-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True)
photos=['data/建筑图片/PAN_Pankhurst House/01_建筑实拍/exteriors_lse_estate_007.jpg','data/建筑图片/PAN_Pankhurst House/01_建筑实拍/tower_photos_round4_tower_round4_tour_p16_0.png','data/建筑图片/PAN_Pankhurst House/01_建筑实拍/tower_photos_round4_tower_round4_realm_p47_0.jpg']
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':OLD,'changes':changes,'removedConnectedBoxes':removed,'references':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),'captureDate':'unknown'}for p in photos],'sourceUrls':['https://info.lse.ac.uk/staff/divisions/estates-division/lse-estate/LSE-Estate','https://info.lse.ac.uk/current-students/your-first-weeks/assets/documents/self-guided-campus-tour.pdf','https://info.lse.ac.uk/staff/divisions/estates-division/Assets/Documents/2022-LSE-Public-Realm-Strategy.pdf'],'registration':{'frame':FRAME,'facadeOriginGIS':[69.5857533,-60.0455239],'facadeEndGIS':[71.6129574,-71.7498479],'length':L,'openingBounds':[LO,HI],'fiveModulePitch':PITCH,'rows':ROWS,'photoAnchor':'Native automatic doorx1.95 is photo right, revolving doorsx5.15/8.30 center, yellow revealx11.63 photo left. Five complete broad windows lie between the yellow-side corner and automatic-door-side turn. Rightmost narrow projected strip beyond main face is not treated as a sixth physical narrow module.','sideTurn':'Adjacent GIS edge to(61.08184,-54.46048) changes direction about46degrees; that angled face, any narrow projected edge panes and all its geometry remain unchanged.','dimensionStatus':'GIS inherited whole-face dimensions and photograph-guided repeated bay count; not surveyed pane widths, elevations or current2026 condition.'},'wholeEnvelopeAssessment':{'changed':'Lower-five-row main frontage rhythm changes from8 narrow lights per row to5 individually perimeter-framed windows;25 independent glazing panes and aligned spandrel panel joints. Same outer band apertures are kept, so no opaque wall overlay or invented wall-hole width.','preserved':'Aggregate finish, glass optics, ground entrance and accessibility corrections, side façades, original blinds, roof and unphotographed upper7 rows unchanged.','limitations':['Official estate photograph shows the lower repeated rows but clips the top of fifth row; inherited fifth-row height is not newly measured.','Precise bay widths/frame profiles are proportional estimates, not pixel-scaled24px narrow-window widths.','Roof height44m, upper-storey count and unphotographed upper-window cadence remain inherited estimates.','Existing interior/curtain placements remain schematic; no new glass transparency or room geometry inferred.']},'firstSurfaceChecks':checks}
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
scene,col=open_base()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=src.objects
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  m=slot.material
  if m and'.'in m.name and m.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(m.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for name in OLD:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
reloaded=probes();assert reloaded==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in OLD)
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'originalObjectCount':len(originals),'unrelatedVisibilityPreserved':True,'fullModelSaved':False,'windowCount':25,'checkCount':len(reloaded),'firstSurfaceChecks':reloaded,'materialOpticsChanged':False}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type=='MESH'and o.name not in visible:o.hide_render=True
focus=point(L/2,-2,22);cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cam.location=focus+N*75-U*20+Vector((0,0,8));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();cd.type='ORTHO';cd.ortho_scale=56;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1100;scene.render.resolution_y=1500;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-envelope.png');bpy.ops.render.render(write_still=True)
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('PAN_ENVELOPE_VERIFIED',len(originals),len(reloaded));bpy.ops.wm.quit_blender()
