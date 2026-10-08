"""Save and reopen a private SAW component, retaining the accepted complete source."""
from pathlib import Path
import ast,hashlib,json,sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'web/tools'))
from refine_saw_brick_screens import apply_saw_brick_screens,connected_bricks,facade_frames,SOURCES
from refine_architectural_glass import shape_signature
from refine_old_lettering185 import font_signature
def material_values(material):
 values={'diffuse':list(material.diffuse_color),'surface':material.surface_render_method,'nodes':[],'links':[]}
 for node in material.node_tree.nodes:
  row={'type':node.bl_idname,'inputs':{}}
  for socket in node.inputs:
   if hasattr(socket,'default_value'):
    value=socket.default_value
    try:value=list(value)
    except TypeError:pass
    if isinstance(value,(list,float,int,bool,str)):row['inputs'][socket.identifier]=value
  values['nodes'].append(row)
 for link in material.node_tree.links:values['links'].append((link.from_node.name,link.from_socket.identifier,link.to_node.name,link.to_socket.identifier))
 return values

OUT=R/'result/blender/saw-screen-review';BASE=R/'result/blender/LSE_campus_detailed_v189.blend';COMPONENT=OUT/'saw-flush-screens.blend'
OUT.mkdir(parents=True,exist_ok=True);baseline_hash=hashlib.sha256(BASE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene
for s in bpy.data.scenes:
 for layer in s.view_layers:layer.update()
before={o.name:shape_signature(o) for o in bpy.data.objects if o.type=='MESH'}
fonts={o.name:font_signature(o) for o in bpy.data.objects if o.type=='FONT'}
visibility={o.name:o.hide_render for o in bpy.data.objects}
module=ast.parse((R/'web/tools/export_scene.py').read_text());ns={'bpy':bpy,'bmesh':bmesh,'Vector':Vector,'full_detail':True,'material_cache':{},'OUTPUT':OUT,'depsgraph':bpy.context.evaluated_depsgraph_get()}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(R/'web/tools/export_scene.py'),'exec'),ns)
def export(label):
 bpy.context.window.scene=scene;bpy.context.view_layer.update();ns['depsgraph']=bpy.context.evaluated_depsgraph_get();ns['material_cache']={}
 temp=bpy.data.scenes.new('SAW_PRIVATE_REVIEW')
 ns['clone_group'](list(bpy.data.collections['SAW_EXTERIOR'].all_objects)+list(bpy.data.collections['SAW_PUBLIC_INTERIOR_study'].all_objects),'SAW',temp)
 ns['export_scene'](temp,label+'.glb')
 for o in list(temp.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(temp);bpy.context.window.scene=scene
export('before');change=apply_saw_brick_screens()
assert all(shape_signature(bpy.data.objects[n])==v for n,v in before.items())
assert all(font_signature(bpy.data.objects[n])==v for n,v in fonts.items())
assert all(bpy.data.objects[n].hide_render==v for n,v in visibility.items() if n not in SOURCES)
owned=[bpy.data.objects[n] for n in change['addedObjects']]
bpy.data.libraries.write(str(COMPONENT),set(owned),fake_user=True,compress=True)
export('after')
for obj in owned:bpy.data.objects.remove(obj,do_unlink=True)
with bpy.data.libraries.load(str(COMPONENT),link=False)as(a,b):b.objects=list(change['addedObjects'])
for obj in b.objects:bpy.data.collections['SAW_EXTERIOR'].objects.link(obj)
bpy.context.view_layer.update()
frames=facade_frames();total=0;maximum=0;triangles=[0,0]
for record in change['records']:
 old=bpy.data.objects[record['source']];new=bpy.data.objects[record['target']]
 assert [material_values(m) for m in old.data.materials]==[material_values(m) for m in new.data.materials]
 assert [tuple(p.vertices)for p in old.data.polygons]==[tuple(p.vertices)for p in new.data.polygons]
 for uv in old.data.uv_layers:assert [tuple(v.uv)for v in uv.data]==[tuple(v.uv)for v in new.data.uv_layers[uv.name].data]
 matrix=new.matrix_world.copy()
 for indices in connected_bricks(new.data):
  points=[matrix@new.data.vertices[i].co for i in indices];centre=sum(points,Vector())/8
  family=min(frames,key=lambda f:abs((centre-frames[f][0]).dot(frames[f][1])+.1075))
  origin,normal=frames[family];depths=[(p-origin).dot(normal)for p in points]
  assert abs(max(depths))<.00005 and abs(min(depths)+.215)<.00005
  maximum=max(maximum,abs(max(depths)))
  # Translation only: every edge preserves its physical length and every brick its height.
  oldpoints=[old.matrix_world@old.data.vertices[i].co for i in indices]
  for i in range(1,8):assert abs((points[i]-points[0]).length-(oldpoints[i]-oldpoints[0]).length)<.00005
  total+=1
 for i,obj in enumerate([old,new]):triangles[i]+=sum(len(p.vertices)-2 for p in obj.data.polygons)
assert triangles[0]==triangles[1] and total==sum(change['brickCounts'].values())
# Independent rays prove each mortar pad physically meets an upper and lower brick.
brick_vertices=[];brick_faces=[]
for record in change['records']:
 obj=bpy.data.objects[record['target']];offset=len(brick_vertices);matrix=obj.matrix_world.copy()
 brick_vertices.extend(matrix@v.co for v in obj.data.vertices)
 brick_faces.extend(tuple(offset+i for i in p.vertices)for p in obj.data.polygons)
brick_tree=BVHTree.FromPolygons(brick_vertices,brick_faces)
mortar=bpy.data.objects['SAW_NEXT_SCREEN_mortar_beds'];contacts=0
assert len(mortar.data.polygons)==len(change['mortarPads'])*4
for i,pad in enumerate(change['mortarPads']):
 indices=range(i*8,i*8+8);points=[mortar.matrix_world@mortar.data.vertices[j].co for j in indices]
 centre=sum(points,Vector())/8
 height=pad['bounds'][3]-pad['bounds'][2]
 samples=[centre]+[Vector((points[j].x,points[j].y,centre.z)) for j in (0,2,4,6)]
 for sample in samples:
  for direction in [Vector((0,0,1)),Vector((0,0,-1))]:
   hit=brick_tree.ray_cast(sample,direction,.02)
   assert hit[2] is not None and abs(hit[3]-height/2)<.00003,(pad,hit)
   contacts+=1
 # Nonzero section and corner contact rule out flat or unsupported bedding.
 a,b,c=points[4]-points[0],points[2]-points[0],points[1]-points[0]
 assert abs(a.dot(b.cross(c)))>1e-7
assert apply_saw_brick_screens()['alreadyApplied']
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==baseline_hash
proof={'baselineSha256':baseline_hash,'sourceUnchanged':True,'savedComponentReopened':True,'sourceShapesUVFontsPreserved':True,'bricksVerified':total,'triangleCounts':triangles,'maxPlaneErrorMetres':maximum,'mortarPads':len(change['mortarPads']),'brickContactRays':contacts,'addedTriangles':change['addedTriangles'],'componentSha256':hashlib.sha256(COMPONENT.read_bytes()).hexdigest(),'change':change}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('SAW_SCREEN_VERIFIED',total,triangles,flush=True)
