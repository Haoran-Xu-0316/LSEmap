"""Add photographed MAR narrow-opening guards to two courtyard window rows.

Run in Blender Text Editor. Geometry follows retained apertures; metric sizes
and alignment are estimates. No shared glass material or original mesh changes.
"""
from pathlib import Path
import array, hashlib, json, math, sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/mar_exterior_next';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v125.blend'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for obj in list(bpy.data.objects):
 if obj.name.startswith('MAR_NEXT_'):bpy.data.objects.remove(obj,do_unlink=True)
def fingerprint(obj):
 h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
 if obj.type=='MESH':
  for data,field,kind,count in ((obj.data.vertices,'co','f',3),(obj.data.loops,'vertex_index','i',1),(obj.data.polygons,'material_index','i',1)):
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in obj.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o) for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()] for o in bpy.data.objects}
col=bpy.data.collections['MAR_EXTERIOR'];D=json.loads((ROOT/'result/blender/stage75/mar-fenestration.json').read_text());surface=next(s for s in D['surfaces'] if s['name']=='MAR_rear_way/1376078546_0')
p,q=Vector((*surface['p'],0)),Vector((*surface['q'],0));axis=(q-p).normalized();normal=Vector((axis.y,-axis.x,0));centre=Vector((*D['mar_center'],0))
if ((p+q)/2-centre).dot(normal)<0:normal=-normal
angle=math.atan2(axis.y,axis.x)
def point(x,z,d):return p+axis*x+normal*d+Vector((0,0,z))
sys.path.insert(0,str(Path(__file__).resolve().parent));from facade_geometry import Geometry,materials
materials.clear();material=bpy.data.objects['MAR_V115_retained_D5_wings75_joinery'].data.materials[0].copy();material.name='MAR_NEXT_opening_guard_bronze';materials['guard']=material
batch=Geometry('MAR','opening_guards','guard');windows=[]
# Photograph 07 shows two complete upper window rows and an access level below.
# Restrict additions to the first two window rows above the retained access row.
selected=[r for r in surface['openings'] if any(abs(r[1]-z)<.01 for z in [17.83,22.13])];assert len(selected)==10
for a,b,c,d in selected:
 # Photo 07's narrow right opening is approximately one third of total width.
 low=b+.055;top=b+.98;x0=a+(c-a)*.68+.035;x1=c-.035;depth=-.28
 batch.box(point((x0+x1)/2,top,depth),(x1-x0,.035,.035),angle)
 bars=[x0+(x1-x0)*i/7 for i in range(8)]
 for x in bars:batch.box(point(x,(low+top)/2,depth),(.018,.028,top-low),angle)
 windows.append({'aperture':[a,b,c,d],'guardExtent':[x0,low,x1,top],'barX':bars,'depth':depth})
# Move only the ten corresponding existing centre mullions, retaining every
# other joinery vertex and all original material slots/UV in an owned copy.
source=bpy.data.objects['MAR_V115_retained_D5_wings75_joinery'];joinery=source.copy();joinery.data=source.data.copy();joinery.name='MAR_NEXT_guarded_window_joinery';joinery.data.name=joinery.name
for owner in source.users_collection:owner.objects.link(joinery)
joinery.hide_render=False;joinery.hide_set(False);moved=[]
for a,b,c,d in selected:
 ids=[]
 for vertex in joinery.data.vertices:
  world=joinery.matrix_world@vertex.co;relative=world-p;x=relative.dot(axis);depth=relative.dot(normal)
  if abs(x-(a+c)/2)<.022 and b-.005<=world.z<=d+.005 and -.435<=depth<=-.345:
   vertex.co=joinery.matrix_world.inverted()@(world+axis*((c-a)*.18));ids.append(vertex.index)
 assert len(ids)>=8,(a,b,len(ids))
 moved.append({'aperture':[a,b,c,d],'vertexCount':len(ids),'dividerWidthFraction':.68})
# Photograph 07 has no high transom across the two complete window rows.
# Remove the ten inherited transom boxes, retaining perimeter frames/UVs.
mesh=bmesh.new();mesh.from_mesh(joinery.data);transoms=[]
for face in mesh.faces:
 coords=[]
 for vertex in face.verts:
  world=joinery.matrix_world@vertex.co;relative=world-p;coords.append((relative.dot(axis),world.z,relative.dot(normal)))
 if any(all(a-.005<=x<=c+.005 and abs(z-(d-.72))<=.027 and -.435<=depth<=-.345 for x,z,depth in coords) for a,b,c,d in selected):transoms.append(face)
assert len(transoms)==60,len(transoms)
bmesh.ops.delete(mesh,geom=transoms,context='FACES');orphan=[v for v in mesh.verts if not v.link_faces]
if orphan:bmesh.ops.delete(mesh,geom=orphan,context='VERTS')
mesh.to_mesh(joinery.data);mesh.free();joinery.data.update();source.hide_render=True;source.hide_set(True)
# Legacy small window reveals predate the enlarged academic-wing apertures.
# Remove only their faces wholly inside these ten openings, keeping all other
# legacy faces and UV loops in independently owned replacement meshes.
legacy_copies=[];legacy_archives=[];legacy_removed={}
for legacy_name in ['MAR_V115_retained_D5_V16_reveal_bead','MAR_V115_retained_D5_V17_folded_jamb_return','MAR_V115_retained_D5_V16_glazing_seal','MAR_V115_retained_D5_V17_flashing_downstand','MAR_V115_retained_D5_V17_head_flashing','MAR_V115_retained_D5_V17_cap_shadow_joint']:
 legacy=bpy.data.objects[legacy_name];replacement=legacy.copy();replacement.data=legacy.data.copy();replacement.name='MAR_NEXT_retained_'+legacy_name.removeprefix('MAR_V115_retained_').removeprefix('D5_');replacement.data.name=replacement.name
 for owner in legacy.users_collection:owner.objects.link(replacement)
 mesh=bmesh.new();mesh.from_mesh(replacement.data);remove=[]
 for face in mesh.faces:
  coords=[]
  for vertex in face.verts:
   world=replacement.matrix_world@vertex.co;relative=world-p;coords.append((relative.dot(axis),world.z,relative.dot(normal)))
  if any(all(a-.035<=x<=c+.035 and b-.035<=z<=d+.035 and -.75<=depth<=.55 for x,z,depth in coords) for a,b,c,d in selected):remove.append(face)
 assert remove,legacy_name
 legacy_removed[legacy_name]=len(remove);bmesh.ops.delete(mesh,geom=remove,context='FACES');orphan=[v for v in mesh.verts if not v.link_faces]
 if orphan:bmesh.ops.delete(mesh,geom=orphan,context='VERTS')
 mesh.to_mesh(replacement.data);mesh.free();replacement.data.update();replacement.hide_render=False;replacement.hide_set(False);legacy.hide_render=True;legacy.hide_set(True);legacy_copies.append(replacement);legacy_archives.append(legacy_name)
obj=batch.finish();obj.name='MAR_NEXT_opening_guards';obj.data.name=obj.name;obj.modifiers.clear()
for owner in list(obj.users_collection):owner.objects.unlink(obj)
col.objects.link(obj)
for layer in scene.view_layers:layer.update()

trees=[]
def refresh_trees():
 trees.clear()
 for other in col.all_objects:
  if other.type!='MESH' or other.hide_render or not len(other.data.polygons):continue
  mesh=other.data;verts=[other.matrix_world@v.co for v in mesh.vertices];polys=[tuple(poly.vertices) for poly in mesh.polygons]
  trees.append((other.name,BVHTree.FromPolygons(verts,polys,all_triangles=False)))
def first_hit(origin,direction):
 best=None
 for name,tree in trees:
  hit=tree.ray_cast(origin,direction,2)
  if hit[0] is not None and (best is None or hit[3]<best[0]):best=(hit[3],name)
 return best[1] if best else None

def probes():
 refresh_trees()
 # Every probe uses the entire visible MAR facade, including retained walls/glass.
 result=[]
 for row in windows:
  a,b,c,d=row['aperture'];xs=row['barX'];z=b+.45
  tests=[('bar',xs[3],z),('gap',(xs[3]+xs[4])/2,z),('upper-glass',(a+c)/2+.2,b+1.6),('fixed-glass',a+.65,b+.45),('removed-transom',a+.65,d-.72),('removed-inset-frame',a+(c-a)*.5,b+.4),('removed-low-seal',(a+c)/2,b+.27),('removed-high-flashing',(a+c)/2,d-.27),('removed-head-flashing',(a+c)/2,d-.245),('removed-cap-joint',a+.27,(b+d)/2)]
  for kind,x,height in tests:
   hit=first_hit(point(x,height,.4),-normal)
   expected='MAR_NEXT_opening_guards' if kind=='bar' else 'MAR_V115_retained_D5_wings75_glass'
   assert hit==expected,(kind,row['aperture'],hit,expected)
   result.append({'kind':kind,'firstSurface':hit,'point':list(point(x,height,.4))})
 return result
before_probes=probes();diagnostics=[]
for a,b,c,d in selected[:1]:
 for x,z in [(a+.255,(b+d)/2),(c-.255,(b+d)/2),((a+c)/2,b+.27),((a+c)/2,d-.27)]:diagnostics.append({'x':x,'z':z,'firstSurface':first_hit(point(x,z,.4),-normal)})
for a,b,c,d in selected[:1]:
 for offset in [i*.005 for i in range(10,101)]:
  for x,z in [(a+offset,(b+d)/2),((a+c)/2,d-offset)]:
   hit=first_hit(point(x,z,.4),-normal)
   if hit!='MAR_V115_retained_D5_wings75_glass':diagnostics.append({'x':x,'z':z,'firstSurface':hit})
assert all(r['firstSurface']=='MAR_V115_retained_D5_wings75_glass' for r in diagnostics),diagnostics
print('MAR_BORDER_DIAGNOSTICS',diagnostics,flush=True)
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
component=OUT/'mar-exterior-component.blend';bpy.data.libraries.write(str(component),{obj,joinery,*legacy_copies},fake_user=True)
index=json.loads((ROOT/'data/建筑图片/MAR_Marshall Building/图片索引.json').read_text());record=next(r for r in index['images'] if r['file'].endswith('MAR_mar_kane_07.jpg'));photo=ROOT/'data/建筑图片/MAR_Marshall Building'/record['file'];assert hashlib.sha256(photo.read_bytes()).hexdigest()==record['sha256']
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'ownedObjects':[obj.name,joinery.name,*[o.name for o in legacy_copies]],'archivedObjects':[source.name,*legacy_archives],'legacyRevealFacesRemoved':legacy_removed,'mullionCorrections':moved,'removedTransomCount':10,'originalFingerprints':originals,'originalVisibility':visibility,'originalGeometryPreserved':True,'windowCount':10,'barCountPerWindow':8,'surface':surface['name'],'windows':windows,'probes':before_probes,'borderDiagnostics':diagnostics,'reference':{'file':str(photo.relative_to(ROOT)),'sha256':record['sha256'],'sources':record['sources']},'scope':'Metal opening guards and estimated two-thirds fixed/one-third opening sash division on two retained courtyard rows. Glazing, wall openings, access level and other elevations unchanged.','limitations':['Five-column courtyard face and row registration follows inherited GIS face and floor estimates, not survey.','Photograph supports narrow right opening-side metal bars; corrected 68 percent fixed/32 percent opening division is photo-estimated.','Guard height .98m and bar count/spacing/section estimated from photograph; no claim of measured safety specification.','Outdated nested reveal faces inside these ten openings removed in owned copies; all unselected legacy window reveals retained.', '2022 upload path, photograph capture date unknown; hidden faces and full terrace arrangement not validated.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['MAR_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False) as (src,dst):dst.objects=src.objects
for obj in dst.objects:col.objects.link(obj)
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for layer in scene.view_layers:layer.update()
after_probes=probes();assert before_probes==after_probes
assert all(fingerprint(bpy.data.objects[name])==value for name,value in originals.items())
# Render a close native view of the complete guarded face, with no saved full campus.
names={o.name for o in col.all_objects}
for other in scene.objects:
 if other.type=='MESH' and other.name not in names:other.hide_render=True
focus=point((q-p).length/2,22.4,0);camdata=bpy.data.cameras.new('MAR_NEXT_guard_review_camera');cam=bpy.data.objects.new(camdata.name,camdata);scene.collection.objects.link(cam);cam.location=focus+normal*2.2+axis*.15;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=15.8;scene.camera=cam;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1400;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.filepath=str(OUT/'reloaded-window-guards.png');bpy.ops.render.render(write_still=True)
verification={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalObjectCount':len(originals),'originalGeometryPreserved':True,'fullModelSaved':False,'windowCount':10,'wholeFacadeProbeCount':len(after_probes),'wholeFacadeFirstSurfaceChecks':after_probes,'nativeRender':'result/blender/mar_exterior_next/reloaded-window-guards.png'}
(OUT/'verification.json').write_text(json.dumps(verification,indent=2)+'\n');print('MAR_OPENING_GUARDS_RELOADED',len(originals),len(after_probes),flush=True);bpy.ops.wm.quit_blender()
