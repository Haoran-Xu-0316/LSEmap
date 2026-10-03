"""Align the photographed OLD Student Services entrance upper transom.
Run in Blender Text Editor. Opening and material registration remain unchanged.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/old_glazing_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v127.blend'
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
collection=bpy.data.collections['OLD_EXTERIOR'];source=bpy.data.objects['OLD_D5_clare87_retained_blue'];assert not source.hide_render
ring=next(b for b in json.loads((ROOT/'result/blender/site_geometry.json').read_text())['buildings']if b['code']=='OLD')['rings'][0]
a,b=Vector((*ring[7],0)),Vector((*ring[8],0));origin=(a+b)/2;right=(a-b).normalized();normal=Vector((right.y,-right.x,0));length=(b-a).length
x=-length/2+length*.5/5;width=length/5-.92
# The retained 53 portal upper light spans its inscription-band top at 3.36m
# and frame at 5.15m. Its transom at 3.72m creates an unsupported narrow strip;
# the frontal photo shows two almost equal rows. Only this inner rail moves.
low,high=3.36,5.15;z=(low+high)/2;depth=-.10
def point(x,d,z):return origin+right*x+normal*d+Vector((0,0,z))
def probes(locations):
 vertices=[];faces=[];owners=[]
 for obj in collection.all_objects:
  if obj.type!='MESH'or obj.hide_render:continue
  k=len(vertices);vertices.extend(obj.matrix_world@v.co for v in obj.data.vertices);faces.extend(tuple(k+i for i in p.vertices)for p in obj.data.polygons);owners.extend([obj.name]*len(obj.data.polygons))
 tree=BVHTree.FromPolygons(vertices,faces);rows=[]
 for label,px,pz in locations:
  hit=tree.ray_cast(point(px,.85,pz),-normal,1.4);rows.append({'label':label,'local':[px,.85,pz],'direction':list(-normal),'firstSurface':owners[hit[2]]if hit[2]is not None else None})
 return rows
rail_locations=[('left-transom',x-width*.25,z),('right-transom',x+width*.25,z)]
glass_locations=[(str(col)+'-'+str(row),x+col*width*.25,low+(high-low)*row)for col in [-1,1]for row in [.25,.75]]
old_rail_locations=[('left-old-transom',x-width*.25,3.72),('right-old-transom',x+width*.25,3.72)]
before=probes(rail_locations);glass_before=probes(glass_locations);old_before=probes(old_rail_locations)
assert all(r['firstSurface']==source.name for r in old_before),old_before
assert all(r['firstSurface']=='OLD_V53_Clare_glass'for r in before+glass_before),before+glass_before
retained=source.copy();retained.data=source.data.copy();retained.name='OLD_GLAZING_NEXT_retained_blue';collection.objects.link(retained)
bm=bmesh.new();bm.from_mesh(retained.data);seen=set();delete=[];removed=0
for v in bm.verts:
 if v in seen:continue
 seen.add(v);stack=[v];part=[]
 while stack:
  a=stack.pop();part.append(a)
  for edge in a.link_edges:
   other=edge.other_vert(a)
   if other not in seen:seen.add(other);stack.append(other)
 coords=[]
 for vertex in part:
  d=retained.matrix_world@vertex.co-origin;coords.append(Vector((d.dot(right),d.dot(normal),d.z)))
 lo=[min(q[i]for q in coords)for i in range(3)];hi=[max(q[i]for q in coords)for i in range(3)]
 if abs((lo[0]+hi[0])/2-x)<.001 and abs((lo[2]+hi[2])/2-3.72)<.001 and hi[2]-lo[2]<.10:
  delete.extend(part);removed+=1
assert removed==1,removed
bmesh.ops.delete(bm,geom=delete,context='VERTS');bm.to_mesh(retained.data);bm.free();retained.data.update();source.hide_render=True;source.hide_set(True)
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();materials['blue']=source.data.materials[0]
g=Geometry('OLD','glazing_next_portal_transom','blue');g.box(point(x,depth,z),(width-.09,.15,.065),math.atan2(right.y,right.x));obj=g.finish();obj.name='OLD_GLAZING_NEXT_portal_upper_transom';obj.data.name=obj.name
for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();owned=[retained,obj]
after=probes(rail_locations);glass_after=probes(glass_locations);old_after=probes(old_rail_locations)
assert all(r['firstSurface']=='OLD_V53_Clare_glass'for r in old_after),old_after
assert all(r['firstSurface']==obj.name for r in after),after
assert all(r['firstSurface']=='OLD_V53_Clare_glass'for r in glass_after),glass_after
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
component=OUT/'old-glazing-component.blend';bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
reference=ROOT/'data/collections/public-realm-2026/user-references/reference-04.png';assert reference.exists()
audit={'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':[source.name],'removedOldTransomMembers':removed,'sources':[{'local':str(reference.relative_to(ROOT)),'sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'attribution':'User supplied frontal Clare Market Student Services entrance photograph','captureDate':'unknown','supports':'Upper entrance glazing has two columns and two rows with a horizontal blue transom'}],'scope':'Align the misplaced single horizontal blue transom in the Student Services entrance upper light; keep all glazing, external frames, portal inscription and roof casements','geometry':{'frame':{'origin':list(origin),'right':list(right),'outward':list(normal)},'retainedOpeningCenter':x,'retainedOpeningWidth':width,'retainedUpperLightBottom':low,'retainedUpperLightTop':high,'oldTransomHeight':3.72,'newTransomCentre':[x,depth,z],'newTransomDimensions':[width-.09,.15,.065],'columns':2,'rows':2},'beforeTargetTransomProbes':before,'beforeOldTransomProbes':old_before,'afterTransomProbes':after,'beforeFourGlassPaneProbes':glass_before,'afterFourGlassPaneProbes':glass_after,'afterOldTransomGlassProbes':old_after,'limitations':['Photograph establishes two rows and incorrect horizontal subdivision proportion; it does not establish millimetre dimensions or exact paint reflectance','Existing opening registration, heights, blue material and four-column regular windows retained as prior estimates','Private photograph is evidence only and is not published as an asset','No full facade, current refurbishment condition or complete OLD interior accuracy claimed']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for layer in scene.view_layers:layer.update()
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects']
collection=bpy.data.collections['OLD_EXTERIOR'];owned=dst.objects
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for obj in owned:
 collection.objects.link(obj)
 for i,mat in enumerate(list(obj.data.materials)):
  original=bpy.data.materials.get(mat.name.rsplit('.',1)[0])if mat.name[-4:-3]=='.'else mat
  if original:obj.data.materials[i]=original
assert all(fingerprint(bpy.data.objects[n])==v for n,v in originals.items())
after=probes(rail_locations);glass_after=probes(glass_locations);old_after=probes(old_rail_locations)
assert all(r['firstSurface']=='OLD_V53_Clare_glass'for r in old_after),old_after
assert all(r['firstSurface']=='OLD_GLAZING_NEXT_portal_upper_transom'for r in after),after
assert all(r['firstSurface']=='OLD_V53_Clare_glass'for r in glass_after),glass_after
names={o.name for o in collection.all_objects}
for obj in scene.objects:
 if obj.type=='MESH'and obj.name not in names:obj.hide_render=True
focus=point(x,0,3.65);camdata=bpy.data.cameras.new('OLD_GLAZING_NEXT_preview_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*15+right*.3+Vector((0,0,.3));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=6.0;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=950;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-portal-glazing.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==audit['baselineSha256'],'savedComponentReopened':True,'originalGeometryPreserved':True,'visibleElevationNewBlueTransomFirstHits':len(after),'visibleElevationRetainedGlassFirstHits':len(glass_after),'actualReopenedTransomProbes':after,'actualReopenedGlassProbes':glass_after,'actualReopenedOldTransomGlassProbes':old_after,'nativeRender':'reloaded-portal-glazing.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('OLD_GLAZING_COMPONENT_RELOADED_VERIFIED',flush=True)
