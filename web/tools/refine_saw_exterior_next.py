"""Localize SAW's sloping entrance canopy from published photographs.
Run in Blender Text Editor; geometric dimensions remain bounded estimates.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/saw_exterior_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v124.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
previous=json.loads((OUT/'audit.json').read_text()) if (OUT/'audit.json').exists() else None
if previous:
 for name in previous['ownedObjects']:
  obj=bpy.data.objects.get(name)
  if obj:
   mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);mesh.use_fake_user=False
   if not mesh.users:bpy.data.meshes.remove(mesh)
 for name in previous['archivedObjects']:
  if name in bpy.data.objects:
   obj=bpy.data.objects[name];state=previous['originalVisibility'][name];obj.hide_render,obj.hide_viewport=state[:2];obj.hide_set(state[2])
for layer in scene.view_layers:layer.update()
def fingerprint(obj):
 digest=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);digest.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);digest.update(values.tobytes())
 digest.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return digest.hexdigest()
originals={obj.name:fingerprint(obj) for obj in bpy.data.objects};visibility={obj.name:[obj.hide_render,obj.hide_viewport,obj.hide_get()] for obj in bpy.data.objects}
collection=bpy.data.collections['SAW_EXTERIOR']
archived=['SAW_canopy_glass','SAW_canopy_steel_rafters','SAW_canopy_raking_supports']
head=bpy.data.objects['SAW_D5_curtain82_central_return_head'];points=[head.matrix_world@v.co for v in head.data.vertices]
a,b=sum(points[:4],Vector())/4,sum(points[4:],Vector())/4
if a.z>b.z:a,b=b,a
# Native timber head sets the correct architectural recess, not the old
# unregistered canopy line extending across the entire south folded elevation.
start=a+(b-a)*.28;end=b;direction=(end-start).normalized()
u=Vector((direction.x,direction.y,0)).normalized();normal=Vector((u.y,-u.x,0))
allpoints=[o.matrix_world@v.co for o in collection.all_objects if o.type=='MESH' and not o.hide_render for v in o.data.vertices]
center=Vector([(min(p[i]for p in allpoints)+max(p[i]for p in allpoints))/2 for i in range(3)])
if (((start+end)*.5)-center).dot(normal)<0:normal=-normal
projection=2.15;drop=.28
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['glass']=bpy.data.materials['D2_glass_palette26_SAW'];materials['steel']=bpy.data.materials['D2_steel_red']
groups={key:Geometry('SAW','localized_canopy_'+key,key)for key in materials}
def beam(left,right,width=.065):
 axis=(right-left).normalized();side=axis.cross(Vector((0,0,1)))
 if side.length<.01:side=axis.cross(Vector((0,1,0)))
 side.normalize();edge=axis.cross(side).normalized();side*=width/2;edge*=width/2
 vertices=[p+x*side+y*edge for p in (left,right)for x,y in [(-1,-1),(-1,1),(1,1),(1,-1)]]
 groups['steel'].add(vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
wall=bpy.data.objects['SAW_SAW_central_return_pierced_wall']
wall_front=max((wall.matrix_world@v.co).dot(normal)for v in wall.data.vertices)
header_depth=((start+end)*.5).dot(normal)
registration_offset=wall_front-header_depth+.025
assert 0<registration_offset<.6,registration_offset
def back(t):return start+(end-start)*t+normal*registration_offset
def forward(t):return normal*projection*(1-t)+Vector((0,0,-drop*(1-t)))
for i in range(9):
 left,right=back(i/9),back((i+1)/9)
 groups['glass'].add([left,right,right+forward((i+1)/9),left+forward(i/9)],[(0,1,3)] if i==8 else [(0,1,2,3)])
for i in range(10):beam(back(i/9),back(i/9)+forward(i/9)) if i<9 else None
beam(back(0),back(1));beam(back(0)+forward(0),back(1)+forward(1))
# Two simple inclined red supports are photograph-established; exact joint
# angles and member sections remain estimates, with no invented V lattice.
for t in [.25,.72]:
 tip=back(t)+forward(t);base=Vector((tip.x,tip.y,0.10))-u*1.05
 beam(base,tip,.105)
owned=[]
for key,g in groups.items():
 obj=g.finish();obj.name='SAW_NEXT_central_canopy_'+key;obj.data.name=obj.name
 for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();owned.append(obj)
def tree(objects):
 vertices=[];faces=[];owners=[]
 for obj in objects:
  k=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(k+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 return BVHTree.FromPolygons(vertices,faces),owners
def probes(objects,locations):
 t,names=tree(objects);rows=[]
 for point in locations:
  hit=t.ray_cast(point+Vector((0,0,1)) ,Vector((0,0,-1)),2)
  rows.append({'point':list(point),'firstSurface':names[hit[2]]if hit[2]is not None else None})
 return rows
old=bpy.data.objects['SAW_canopy_glass'];oldpoints=[]
for polygon in old.data.polygons:
 p=sum((old.matrix_world@old.data.vertices[i].co for i in polygon.vertices),Vector())/len(polygon.vertices)
 if p.y<3:oldpoints.append(p)
before=probes([bpy.data.objects[n]for n in archived],oldpoints)
assert all(r['firstSurface']=='SAW_canopy_glass'for r in before)
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
centralpoints=[back((i+.5)/9)+forward((i+.5)/9)*.5 for i in range(9)]
after=probes(owned,oldpoints);central=probes(owned,centralpoints)
assert all(r['firstSurface']is None for r in after)
assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in central)
visible=[o for o in collection.all_objects if o.type=='MESH'and not o.hide_render]
whole_after=probes(visible,oldpoints);whole_central=probes(visible,centralpoints)
assert all(r['firstSurface']not in archived and not str(r['firstSurface']).startswith('SAW_NEXT_central_canopy')for r in whole_after)
assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in whole_central),whole_central
# Verify exposure along the actual inclined sheet normal,
# from 8cm off its surface, without deleting or ignoring any visible masonry.
normal_to_sheet=(end-start).cross(forward(0)).normalized()
if normal_to_sheet.z<0:normal_to_sheet=-normal_to_sheet
t,owners=tree(visible);surface_probes=[]
for point in centralpoints:
 hit=t.ray_cast(point+normal_to_sheet*.08,-normal_to_sheet,.16)
 surface_probes.append({'point':list(point),'originOffset':.08,'maxRayDistance':.16,'direction':list(-normal_to_sheet),'firstSurface':owners[hit[2]]if hit[2]is not None else None})
assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in surface_probes),surface_probes
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'saw-exterior-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
index=json.loads((ROOT/'data/建筑图片/SAW_Saw Swee Hock Student Centre/图片索引.json').read_text());sources=[]
for suffix in ['architecture_round5_SAW_saw_909_01.jpg','materials_saw_ehsmith_image_02.jpg','materials_saw_ehsmith_image_04.jpg']:
 record=next(r for r in index['images']if r['file'].endswith(suffix));path=ROOT/'data/建筑图片/SAW_Saw Swee Hock Student Centre'/record['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'];sources.append({'local':str(path.relative_to(ROOT)),'sha256':record['sha256'],'sources':record['sources']})
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':archived,'sources':sources,'scope':'Replace misregistered continuous glass canopy crossing the south fold with a localized sloping canopy at the photographed central recess; existing roof, timber curtain walls and perforated brick screens preserved','geometry':{'outwardNormal':list(normal),'boundingBoxCenter':list(center),'retainedWallFrontDepth':wall_front,'retainedTimberHeaderDepth':header_depth,'canopyBackRegistrationOffset':registration_offset,'headStart':list(a),'headEnd':list(b),'retainedStartFraction':.28,'projectionEstimate':projection,'triangularProjectionTapersTo':0,'crossSlopeDropEstimate':drop,'glassPanels':9,'steelSupports':2},'beforeUnsupportedCanopyProbes':before,'afterUnsupportedCanopyProbes':after,'centralCanopyProbes':central,'visibleElevationUnsupportedCanopyProbes':whole_after,'visibleElevationCentralCanopyProbes':whole_central,'visibleElevationSheetNormalProbes':surface_probes,'limitations':['909 gallery upload path is 2017; exact capture dates and current condition unverified','Central canopy existence and absence of continuous south/front canopy established by multiple photos; dimensions, pane count, support placement and roof pitch are photo-based estimates','Native central timber header registration retained; existing whole-building proportions and brick-screen opening bands are not validated by this correction','Perforated-brick gaps were checked and already expose recessed glass; no incorrect opaque-wall correction made','No claim of full facade or complete interior accuracy']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['SAW_EXTERIOR'];owned=dst.objects
for obj in owned:
 collection.objects.link(obj)
 for i,mat in enumerate(list(obj.data.materials)):
  original=bpy.data.materials.get(mat.name.rsplit('.',1)[0])if mat.name[-4:-3]=='.'else mat
  if original:obj.data.materials[i]=original
for name in archived:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
after=probes(owned,oldpoints);central=probes(owned,centralpoints)
assert all(r['firstSurface']is None for r in after);assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in central)
visible=[o for o in collection.all_objects if o.type=='MESH'and not o.hide_render]
whole_after=probes(visible,oldpoints);whole_central=probes(visible,centralpoints)
assert all(r['firstSurface']not in archived and not str(r['firstSurface']).startswith('SAW_NEXT_central_canopy')for r in whole_after)
assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in whole_central),whole_central
# Verify exposure along the actual inclined sheet normal,
# from 8cm off its surface, without deleting or ignoring any visible masonry.
normal_to_sheet=(end-start).cross(forward(0)).normalized()
if normal_to_sheet.z<0:normal_to_sheet=-normal_to_sheet
t,owners=tree(visible);surface_probes=[]
for point in centralpoints:
 hit=t.ray_cast(point+normal_to_sheet*.08,-normal_to_sheet,.16)
 surface_probes.append({'point':list(point),'originOffset':.08,'maxRayDistance':.16,'direction':list(-normal_to_sheet),'firstSurface':owners[hit[2]]if hit[2]is not None else None})
assert all(r['firstSurface']=='SAW_NEXT_central_canopy_glass'for r in surface_probes),surface_probes
names={o.name for o in collection.all_objects}
for obj in scene.objects:
 if obj.type=='MESH'and obj.name not in names:obj.hide_render=True
focus=(start+end)*.5+Vector((0,0,4));camdata=bpy.data.cameras.new('SAW_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*45-u*10+Vector((0,0,17));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=63;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1350;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-central-canopy.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'unsupportedCanopyProbes':len(after),'centralCanopyProbes':len(central),'visibleElevationUnsupportedCanopyProbes':len(whole_after),'visibleElevationCentralCanopyProbes':len(whole_central),'visibleElevationNormalGlassProbes':len(surface_probes),'verticalGlassFirstHits':9,'verticalLipFirstHits':0,'nativeRender':'reloaded-central-canopy.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('SAW_COMPONENT_RELOADED_VERIFIED',flush=True)
