"""Photo-guided OLD entrance fan stair candidate, without shared exports.
Run in Blender Text Editor. Latest retained native baseline is edition115.
Height registration stays unchanged; widths and corner cuts are estimates.
"""
from pathlib import Path
import array
import hashlib
import json
import bpy
import bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage116/old'
OUT.mkdir(parents=True,exist_ok=True)
BASELINE=ROOT/'result/blender/LSE_campus_detailed_v115.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASELINE))
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(obj):
    h=hashlib.sha256(str([list(row) for row in obj.matrix_world]).encode())
    if obj.type=='MESH':
        vertices=array.array('f',[0])*(len(obj.data.vertices)*3)
        indices=array.array('i',[0])*len(obj.data.loops)
        obj.data.vertices.foreach_get('co',vertices)
        obj.data.loops.foreach_get('vertex_index',indices)
        h.update(vertices.tobytes());h.update(indices.tobytes())
    h.update(str([m.name if m else None for m in getattr(obj.data,'materials',[])]).encode())
    return h.hexdigest()
originals={obj.name:fingerprint(obj) for obj in bpy.data.objects}
source=bpy.data.objects['OLD_D5_houghton112_steps_stone']
assert source.type=='MESH' and len(source.data.vertices)==56 and not source.hide_render
points=[source.matrix_world@v.co for v in source.data.vertices[:8]]
right=(points[4]-points[0]).normalized()
outward=Vector((right.y,-right.x,0))
origin=sum(points,Vector())/8-outward*2.90
origin.z=0
collection=bpy.data.collections['OLD_EXTERIOR']
archive=bpy.data.collections.new('OLD_ARCHIVE_PRE_FAN_STAIR')
bpy.context.scene.collection.children.link(archive)
archive.objects.link(source)
for owner in list(source.users_collection):
    if owner!=archive:owner.objects.unlink(source)
source.hide_render=True;source.hide_set(True)
# Six old tread boxes are replaced; keep the landing as an independent copy.
copy=source.copy();copy.data=source.data.copy();copy.name='OLD_V116_retained_entrance_landing'
copy.hide_render=False;collection.objects.link(copy);copy.hide_set(False)
mesh=bmesh.new();mesh.from_mesh(copy.data);mesh.verts.ensure_lookup_table()
bmesh.ops.delete(mesh,geom=list(mesh.verts[:48]),context='VERTS')
mesh.to_mesh(copy.data);mesh.free();copy.data.update()
material=source.data.materials[0].copy();material.name='OLD_V116_entrance_limestone'
copy.data.materials.clear();copy.data.materials.append(material)
vertices=[];faces=[];steps=[]
def world(x,d,z):return origin+right*x+outward*d+Vector((0,0,z))
landing=1.245
for index in range(6):
    # Preserve every AOD-derived riser height and the previous outward reach.
    top=landing*(index+1)/6
    front=3.05-index*.30
    width=8.80-index*.16
    chamfer=.80-index*.06
    half=width/2
    outline=[(-half,-.70),(half,-.70),(half,front-chamfer),(half-chamfer,front),(-half+chamfer,front),(-half,front-chamfer)]
    offset=len(vertices);count=len(outline)
    vertices.extend(world(x,d,z) for z in [0,top] for x,d in outline)
    faces.extend([tuple(offset+j for j in range(count-1,-1,-1)),tuple(offset+count+j for j in range(count))])
    faces.extend((offset+j,offset+(j+1)%count,offset+(j+1)%count+count,offset+j+count) for j in range(count))
    steps.append({'index':index,'top':top,'front':front,'width':width,'cornerCut':chamfer,'outline':outline})
mesh=bpy.data.meshes.new('OLD_V116_fan_stair_mesh');mesh.from_pydata(vertices,[],faces);mesh.materials.append(material)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(mesh);bm.free();mesh.update()
uv=mesh.uv_layers.new(name='SurfaceUV')
for poly in mesh.polygons:
    positions=[mesh.vertices[i].co for i in poly.vertices]
    anchor=positions[0];u=(positions[1]-anchor).normalized()
    n=(positions[1]-anchor).cross(positions[-1]-anchor).normalized();v=n.cross(u)
    for loop,p in zip(poly.loop_indices,positions):
        uv.data[loop].uv=((p-anchor).dot(u),(p-anchor).dot(v))
obj=bpy.data.objects.new('OLD_V116_chamfered_fan_stair',mesh);collection.objects.link(obj)
obj['scope']='Photograph-supported chamfered fan plan; riser heights preserved, width and corner cuts estimated'
for scene in bpy.data.scenes:
    for layer in scene.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==digest for name,digest in originals.items())
audit={'baseline':115,'candidateStage':116,'originalFingerprints':originals,'originalGeometryRetained':True,'otherBuildingsAndInteriorsRetained':True,'archivedObjects':[source.name],'addedObjects':[copy.name,obj.name],'retainedLandingObject':copy.name,'newStairObject':obj.name,'origin':list(origin),'right':list(right),'outward':list(outward),'landing':landing,'steps':steps,'sources':['data/collections/campus_photos_round2/images/OLD/OLD_old_webbyates_01.jpg','data/collections/old-user-reference/houghton-user-entrance-additional-20261002.png'],'scope':'Only the six Houghton approach treads, retaining the labelled GF elevation and landing','limitations':['Photographs show fan-shaped chamfered steps but are not a measured plan','Six riser heights follow retained edition112 registration; current actual step count is not newly surveyed','Plan width and corner cuts estimated from photographs','Complete OLD facade, sculpture fidelity and interiors remain outside this correction']}
(OUT/'old-candidate-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'OLD_fan_stair_candidate.blend'))
print('OLD_FAN_STAIR_CANDIDATE_SAVED',len(vertices),len(faces),flush=True)
