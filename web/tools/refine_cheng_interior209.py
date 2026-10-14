"""Complete CKK's photographed Sounding Board end of the public atrium.

Open in Blender's Text Editor. The opposite entrance and every existing mesh,
material and independent classroom stay intact. The absent return galleries
reuse the retained gallery datums as estimates, rather than inventing rooms.
Historic built photographs establish the timber fold and two gallery levels;
they do not establish current furniture or measured dimensions.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/ckk-interior209'
BASE=ROOT/'result/blender/LSE_campus_detailed_v208.blend'
BASE_SHA='da07d198617bd18bceaece14682b9d0995a288655b6c5aa0ac8d2765e883b92c'
COMPONENT=OUT/'cheng-interior209-component.blend'
DEST='CKK_PUBLIC_INTERIOR_study'
PREFIX='CKK209_'
CENTRE=Vector((-110.49102024587766,77.56014819690478,0))
a=math.radians(22);U=Vector((math.cos(a),math.sin(a),0));N=Vector((-math.sin(a),math.cos(a),0))
SCOPE='Historical built-photo-informed public atrium, not a measured current fitout. Added Sounding Board timber return and two return galleries; no unseen room layout.'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def world(x,y,z):return CENTRE+U*x+N*y+Vector((0,0,z))
def local(p):
 q=p-CENTRE;return Vector((q.dot(U),q.dot(N),p.z))
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   v=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,v);h.update(v.tobytes())
  for uv in o.data.uv_layers:
   v=array.array('f',[0])*(len(uv.data)*2);uv.data.foreach_get('uv',v);h.update(v.tobytes())
  h.update(str([m.name if m else None for m in o.data.materials]).encode())
 return h.hexdigest()

class Builder:
 def __init__(self,collection):self.collection=collection;self.groups={};self.materials={};self.owned=[]
 def material(self,source):
  if source.name not in self.materials:
   m=source.copy();m.name=PREFIX+source.name;self.materials[source.name]=m
  return self.materials[source.name]
 def mesh(self,name,material,vertices,faces):
  key=(name,material.name)
  if key not in self.groups:self.groups[key]=[[],[],material]
  v,f,_=self.groups[key];offset=len(v);v.extend(world(*p)for p in vertices);f.extend(tuple(offset+i for i in p)for p in faces)
 def box(self,name,mat,centre,size):
  x,y,z=centre;a,b,c=[v/2 for v in size]
  self.mesh(name,mat,[(x+dx,y+dy,z+dz)for dz in [-c,c]for dy in [-b,b]for dx in [-a,a]],[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)])
 def ribbon(self,name,mat,x0,x1,curve):
  # A real continuous curved sheet, no intersecting strip boxes or z-fighting.
  verts=[(x,y,z)for x in [x0,x1]for y,z in curve];n=len(curve)
  self.mesh(name,mat,verts,[(i,i+1,n+i+1,n+i)for i in range(n-1)])
 def finish(self):
  for (name,_),(vertices,faces,mat)in self.groups.items():
   mesh=bpy.data.meshes.new(PREFIX+name+'_mesh');mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(mat)
   bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
   uv=mesh.uv_layers.new(name='SurfaceUV')
   for p in mesh.polygons:
    for i in p.loop_indices:
     q=local(mesh.vertices[mesh.loops[i].vertex_index].co);uv.data[i].uv=(q.x,q.y if abs(p.normal.z)>.5 else q.z)
   o=bpy.data.objects.new(PREFIX+name,mesh);self.collection.objects.link(o);o['buildingCode']='CKK';o['scope']=SCOPE;o['dimensionsEstimated']=True;self.owned.append(o)
  return self.owned
 def mirrored_gallery(self,source):
  mesh=source.data;verts=[]
  for v in mesh.vertices:
   p=local(source.matrix_world@v.co);verts.append(world(p.x,-p.y,p.z))
  fresh=bpy.data.meshes.new(PREFIX+source.name+'_mesh');fresh.from_pydata(verts,[],[tuple(reversed(p.vertices))for p in mesh.polygons]);fresh.update()
  for m in mesh.materials:fresh.materials.append(self.material(m))
  for p,q in zip(fresh.polygons,mesh.polygons):p.material_index=q.material_index;p.use_smooth=q.use_smooth
  for layer in mesh.uv_layers:
   uv=fresh.uv_layers.new(name=layer.name)
   for p,q in zip(fresh.polygons,mesh.polygons):
    for i,j in zip(p.loop_indices,reversed(q.loop_indices)):uv.data[i].uv=layer.data[j].uv
  if not fresh.uv_layers:
   uv=fresh.uv_layers.new(name='SurfaceUV')
   for p in fresh.polygons:
    for i in p.loop_indices:
     q=local(fresh.vertices[fresh.loops[i].vertex_index].co);uv.data[i].uv=(q.x,q.y if abs(p.normal.z)>.5 else q.z)
  o=bpy.data.objects.new(PREFIX+'return_'+source.name.removeprefix('CKK_'),fresh);self.collection.objects.link(o);o['buildingCode']='CKK';o['webGeometrySource']=source.name;o['scope']=SCOPE;o['dimensionsEstimated']=True;self.owned.append(o)
  return o

def build(collection):
 b=Builder(collection)
 timber=[b.material(bpy.data.materials['ATRIA_oak'+str(i)])for i in range(5)]
 white=b.material(bpy.data.materials['ATRIA_white']);red=b.material(bpy.data.materials['ATRIA_red']);steel=b.material(bpy.data.materials['ATRIA_steel']);glass=b.material(bpy.data.materials['CKK_GLASS164_clear_atrium'])
 # Register to the retained width23.2m and existing deck top.23m. The floor
 # curves into the missing rear wall; side stair passages remain open.
 for i in range(116):
  x0=-11.6+i*.2;x1=x0+.2;m=timber[(i*7+i//5)%5]
  curve=[(-12.55-1.15*math.sin(t),.26+1.15*(1-math.cos(t)))for t in [math.pi/2*j/24 for j in range(25)]]
  b.ribbon('oak_floor_wall_cove_'+str((i*7+i//5)%5),m,x0,x1,curve)
  b.box('lower_oak_wall_'+str((i*7+i//5)%5),m,((x0+x1)/2,-13.78,(1.41+5.19)/2),(.2,.10,5.19-1.41))
  # Timber surrounds leave both photographed red glazed gallery apertures.
  for z0,z1 in [(5.55,9.19),(9.55,12.85)]:
   if abs((x0+x1)/2)>8.4:b.box('oak_gallery_surrounds_'+str((i*7+i//5)%5),m,((x0+x1)/2,-13.78,(z0+z1)/2),(.2,.10,z1-z0))
  # Shallow top sweep returns toward the roof, as visible in frontal built view.
  topcurve=[(-13.78+1.05*(1-math.cos(t)),12.85+.95*math.sin(t))for t in [math.pi/2*j/20 for j in range(21)]]
  b.ribbon('oak_upper_cove_'+str((i*7+i//5)%5),m,x0,x1,topcurve)
 # Red visible backing is an architectural finish only; no room enclosure or
 # furniture is inferred behind the original photographed glazed slots.
 for z0,z1 in [(5.95,8.85),(10.80,12.55)]:
  b.box('red_gallery_backing',red,(0,-13.94,(z0+z1)/2),(16.8,.06,z1-z0))
  b.mesh('clear_gallery_apertures',glass,[(-8.4,-13.70,z0),(8.4,-13.70,z0),(8.4,-13.70,z1),(-8.4,-13.70,z1)],[(0,3,2,1)])
 # Ventilation slots appear on the photographed lower Sounding Board wall.
 # Recessed dark strips sit above, clear of the curved floor and stairs.
 for x in [-9.8+i*1.4 for i in range(15)]:
  for j in range(9):b.box('lower_ventilation_slots',steel,(x,-13.719,4.05+j*.075),(1.0,.008,.024))
 for name in ['CKK_cross_gallery_slabs','CKK_cross_gallery_finish','CKK_cross_bridge_glass','CKK_cross_bridge_steel_posts','CKK_cross_bridge_glass_clamps','CKK_cross_bridge_continuous_handrail','CKK_cross_bridge_linear_lights']:
  b.mirrored_gallery(bpy.data.objects[name])
 return b,b.finish()

def render(objects,label):
 scene=bpy.data.scenes.new(PREFIX+'review_'+label)
 for o in objects:
  if o.type=='MESH':scene.collection.objects.link(o)
 scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
 scene.world=bpy.data.worlds.new(PREFIX+'world_'+label);scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.5,.56,.65,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.6
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.35
 for name,pos,power,size in [('roof',(0,0,20),7000,20),('fill',(0,5,10),1800,12)]:
  d=bpy.data.lights.new(PREFIX+name+label,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);o.location=world(*pos);o.rotation_euler=(world(0,-8,3)-o.location).to_track_quat('-Z','Y').to_euler()
 d=bpy.data.cameras.new(PREFIX+'camera'+label);o=bpy.data.objects.new(d.name,d);scene.collection.objects.link(o);scene.camera=o;d.lens=23
 bpy.context.window.scene=scene
 for view,pos,target in [('sounding-board',(0,3,3.6),(0,-12.8,6.6)),('side',(-6,1.5,4.8),(0,-11,6))]:
  o.location=world(*pos);o.rotation_euler=(world(*target)-o.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/f'{label}-{view}.png');bpy.ops.render.render(write_still=True)

def validate(objects,originals):
 assert all(fingerprint(bpy.data.objects[k])==v for k,v in originals.items())
 assert all(o.type=='MESH'and len(o.data.uv_layers)>0 and all(math.isfinite(v)for p in o.data.vertices for v in p.co)for o in objects)
 # Whole two-level return floor is physically supported by the retained side
 # galleries at both ends, while the middle atrium stays open to the glass roof.
 meshverts=[];faces=[]
 for o in objects:
  if 'gallery_slabs' not in o.name:continue
  off=len(meshverts);meshverts.extend(o.matrix_world@v.co for v in o.data.vertices);faces.extend(tuple(off+i for i in p.vertices)for p in o.data.polygons)
 tree=BVHTree.FromPolygons(meshverts,faces);rays=[]
 for z in [5.55,9.55]:
  for x in [-10,0,10]:
   hit=tree.ray_cast(world(x,-11.95,z+1),Vector((0,0,-1)),2);assert hit[2] is not None and abs(hit[0].z-z)<.002;rays.append([x,-11.95,z])
  assert tree.ray_cast(world(0,0,z+1),Vector((0,0,-1)),2)[2]is None
 side=bpy.data.objects['CKK_side_gallery_slabs'];side_tree=BVHTree.FromPolygons([side.matrix_world@v.co for v in side.data.vertices],[list(p.vertices)for p in side.data.polygons]);joints=[]
 for z in [5.55,9.55]:
  for sign in [-1,1]:
   for x,t in [(sign*11.59,tree),(sign*11.61,side_tree)]:
    hit=t.ray_cast(world(x,-11.95,z+1),Vector((0,0,-1)),2);assert hit[2]is not None and abs(hit[0].z-z)<.002;joints.append(dict(x=x,y=-11.95,level=z,topError=abs(hit[0].z-z)))
 assert all(m.name.startswith(PREFIX)for o in objects for m in o.data.materials if m)
 return dict(savedComponentReopened=True,privateMaterialBindings=True,flushReturnToSideGalleryRays=joints,originalGeometryUVTransformsMaterialsPreserved=True,baselineObjectCount=len(originals),addedObjects=len(objects),returnGalleryLevels=[5.55,9.55],gallerySupportRays=rays,centralVoidPreserved=True,finiteVertices=True,uvComplete=True,unseenRoomsInvented=False)

def main():
 OUT.mkdir(parents=True,exist_ok=True);assert sha(BASE)==BASE_SHA;bpy.ops.wm.open_mainfile(filepath=str(BASE))
 originals={o.name:fingerprint(o)for o in bpy.data.objects};source=bpy.data.collections[DEST];oldobjects=list(source.all_objects);campus=set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys());owners=[s.name for s in bpy.data.scenes if source.name in s.collection.children]
 collection=bpy.data.collections.new(PREFIX+'component');builder,objects=build(collection);names=sorted(o.name for o in objects)
 bpy.data.libraries.write(str(COMPONENT),set(objects),fake_user=True,compress=True)
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 with bpy.data.libraries.load(str(COMPONENT),link=False)as(available,loaded):loaded.objects=names.copy()
 objects=list(loaded.objects);review=bpy.data.collections.new(PREFIX+'reopened')
 for o in objects:review.objects.link(o)
 proof=validate(objects,originals);assert set(bpy.data.scenes['00_CAMPUS_COMPLETE'].objects.keys())==campus
 proof.update(componentSha256=sha(COMPONENT),baselineSha256=sha(BASE),originalPublicAtriumOwnerScenes=owners,archivedObjects=0)
 (OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
 refs=['data/collections/exteriors/images/ckk_grimshaw_022.jpg','data/collections/exteriors/images/ckk_grimshaw_014.jpg','data/collections/exteriors/images/ckk_grimshaw_009.jpg']
 audit=dict(baseline=str(BASE.relative_to(ROOT)),baselineSha256=BASE_SHA,component=str(COMPONENT.relative_to(ROOT)),componentSha256=sha(COMPONENT),targetCollection=DEST,destinationCollection=DEST,ownedObjects=names,addedObjects=names,archivedObjects=[],changes=[dict(owned=n,destinationCollection=DEST,retainNewMaterials=True)for n in names],scope=SCOPE,sourceURLs=['https://grimshaw.global/projects/education-and-science/london-school-of-economics-new-academic-building/','https://www.willebrand.com/en/projects/lse-london-school-of-economics-grimshaw-architects.398'],sources=[dict(local=p,sha256=sha(ROOT/p),captureDate='unknown; completed2008project historical photograph')for p in refs],sourceRecheck='2026-10-15: both official built-project pages accessible; no photograph dates or2026fitout confirmed',sourceFindings=['Triple-height atrium and two cantilevered gallery levels','Timber floor folds down, up the Sounding Board wall and returns toward glazed roof','Red glazed middle/upper apertures with oak side surrounds; entrance is opposite and stays intact'],limitations=['Retained native30mby28m atrium envelope, gallery elevations and depths are estimates','Curvature1.15m, top sweep1.05m and aperture widths16.8m are photo-informed estimates','No newly enclosed rooms, furnishings, evacuation route or current2026survey claimed','Independent public-interior study remains owned by its original scene; no changes to geographic exterior or independent classrooms'],interiorViewNative=dict(position=list(world(0,3,3.6)),target=list(world(0,-12.8,6.6)),fov=65),proof=proof)
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 oldobjects=list(bpy.data.collections[DEST].all_objects);render(oldobjects,'before');render(oldobjects+objects,'after');assert sha(BASE)==BASE_SHA
 print('CKK209_VERIFIED',len(names),sha(COMPONENT),flush=True);bpy.ops.wm.quit_blender()
if __name__=='__main__':main()
