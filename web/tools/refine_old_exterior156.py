"""Finite OLD facade registration against the engineer's completed-project photograph.
Run in Blender's Text Editor. Private production exports; no publication writes.
"""
from pathlib import Path
import bpy, bmesh, hashlib, json, array, ast
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/old_exterior156'; WEB=ROOT/'result/web/old_exterior156'
BASE=ROOT/'result/blender/LSE_campus_detailed_v155.blend'
EXPECTED='eea3d3c6b8fa7ce6696c60fa0258f8603109fdf56ec04bfe85e79e0b9d93da31'
assert hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED
bpy.ops.wm.open_mainfile(filepath=str(BASE)); scene=bpy.data.scenes['00_CAMPUS_COMPLETE']; bpy.context.window.scene=scene
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
frame=json.loads((ROOT/'result/blender/stage52/old-houghton-audit.json').read_text())
p,u,n=map(Vector,[frame[k]for k in ('origin','right','outward')])
def local(q):
 q=Vector(q)-p;return Vector((q.dot(u),q.dot(n),q.z))
def components(o):
 adj=[[]for v in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;adj[a].append(b);adj[b].append(a)
 unseen=set(range(len(adj)))
 while unseen:
  seed=unseen.pop();group=[seed];stack=[seed]
  while stack:
   for v in adj[stack.pop()]:
    if v in unseen:unseen.remove(v);group.append(v);stack.append(v)
  yield group
records=[]
for o in bpy.data.collections['OLD_EXTERIOR'].all_objects:
 if o.hide_render or 'houghton112' not in o.name or not any(w in o.name for w in ['pediment','mansard']):continue
 parts=[]
 for g in components(o):
  pts=[local(o.matrix_world@o.data.vertices[i].co)for i in g]
  lo=[min(v[i]for v in pts)for i in range(3)];hi=[max(v[i]for v in pts)for i in range(3)]
  parts.append({'lo':lo,'hi':hi,'vertices':len(g)})
 records.append({'name':o.name,'materials':[m.name for m in o.data.materials],'components':parts})
(OUT/'registration.json').write_text(json.dumps(records,indent=2))
print('OLD_REGISTRATION_DONE',flush=True)

def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,count in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*count);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
originals={o.name:fingerprint(o)for o in bpy.data.objects}
visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
assert len(originals)==5915
collection=bpy.data.collections['OLD_EXTERIOR']
module=ast.parse((ROOT/'web/tools/export_scene.py').read_text())
namespace={'bpy':bpy,'bmesh':bmesh,'Vector':Vector,'full_detail':True,'material_cache':{},'OUTPUT':WEB,'depsgraph':bpy.context.evaluated_depsgraph_get()}
exec(compile(ast.Module(body=[node for node in module.body if isinstance(node,ast.FunctionDef)],type_ignores=[]),str(ROOT/'web/tools/export_scene.py'),'exec'),namespace)
def export(label):
 bpy.context.window.scene=scene;bpy.context.view_layer.update();namespace['depsgraph']=bpy.context.evaluated_depsgraph_get();namespace['material_cache']={}
 temporary=bpy.data.scenes.new('OLD_PRIVATE156_'+label)
 namespace['clone_group'](list(collection.all_objects),'OLD',temporary)
 namespace['export_scene'](temporary,label+'.glb')
 for o in list(temporary.objects):bpy.data.objects.remove(o,do_unlink=True)
 bpy.data.scenes.remove(temporary);bpy.context.window.scene=scene
export('before')
PREFIX='OLD_NEXT_EXTERIOR156_'
source=bpy.data.objects['OLD_D5_houghton112_pediments_stone'];glass=bpy.data.objects['OLD_D5_houghton112_mansard_glass']
assert not source.hide_render
windows=[]
for index,g in enumerate(components(glass)):
 pts=[local(glass.matrix_world@glass.data.vertices[i].co)for i in g];lo=[min(v[i]for v in pts)for i in range(3)];hi=[max(v[i]for v in pts)for i in range(3)]
 if hi[2]<24 and lo[0]>-33:
  windows.append({'index':index,'x':(lo[0]+hi[0])/2,'d':(lo[1]+hi[1])/2,'windowTop':hi[2],'width':hi[0]-lo[0]})
assert len(windows)==5
retained=source.copy();retained.data=source.data.copy();retained.name=PREFIX+'retained_unregistered_left_pediment';collection.objects.link(retained)
remove=[]
for g in components(source):
 pts=[local(source.matrix_world@source.data.vertices[i].co)for i in g];x=(min(v.x for v in pts)+max(v.x for v in pts))/2
 if any(abs(x-w['x'])<.001 for w in windows):remove.extend(g)
assert len(remove)==30
bm=bmesh.new();bm.from_mesh(retained.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[i]for i in remove],context='VERTS');bm.to_mesh(retained.data);bm.free()
assert len(retained.data.vertices)==6
verts=[];faces=[]
def point(x,d,z):return p+u*x+n*d+Vector((0,0,z))
def box(x,d,z,width,depth,height):
 start=len(verts);verts.extend(point(x+sx*width/2,d+sy*depth/2,z+sz*height/2)for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)])
 faces.extend(tuple(start+i for i in face)for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
for w in windows:
 # Registered opening is retained; cap width follows the photographed 1.48x ratio.
 box(w['x'],w['d']+.07,w['windowTop']+.13,1.88,.43,.16)
 for side in [-1,1]:
  box(w['x']+side*(w['width']/2+.10),w['d']+.06,w['windowTop']-.14,.10,.31,.38)
mesh=bpy.data.meshes.new(PREFIX+'horizontal_blue_caps');mesh.from_pydata(verts,[],faces);mesh.update()
caps=bpy.data.objects.new(mesh.name,mesh);collection.objects.link(caps)
blue=bpy.data.objects['OLD_NEXT_mansard_four_column_blue'].data.materials[0];caps.data.materials.append(blue)
bevel=caps.modifiers.new('Physical_edge_radius','BEVEL');bevel.width=.008;bevel.segments=2
source.hide_render=True;source.hide_set(True)
owned=[retained,caps];component=OUT/'old-exterior156-component.blend'
bpy.data.libraries.write(str(component),set(owned),fake_user=True,compress=True)
photo=ROOT/'data/建筑图片/OLD_Old Building/01_建筑实拍/campus_photos_round2_OLD_old_webbyates_06.jpg'
audit={'baseline':str(BASE.relative_to(ROOT)),'baselineSha256':EXPECTED,'originalObjectCount':5915,'originalFingerprints':originals,'originalVisibility':visibility,'ownedObjects':[o.name for o in owned],'archivedObjects':[source.name],'destinationCollection':'OLD_EXTERIOR','retainNewMaterials':False,'changes':[{'source':source.name,'owned':retained.name,'collection':'OLD_EXTERIOR','retainNewMaterials':False},{'source':None,'owned':caps.name,'collection':'OLD_EXTERIOR','retainNewMaterials':False}], 'sourceReferences':[{'path':str(photo.relative_to(ROOT)),'sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'url':'https://webbyates.com/projects/the-old-building/','publicationBasis':'Engineer project completion2024; photography by Damian Griffiths; exact capture date unknown'}],'registration':{'origin':list(p),'right':list(u),'outward':list(n),'windows':windows,'photographedWindowIndexes':[w['index']for w in windows],'capWidth':1.88,'capDepth':.43,'capHeight':.16,'bracketHeight':.38,'fiveTriangularPedimentsRemovedFromOwnedCopy':True,'unregisteredLeftPedimentRetained':True},'improvement':'Five Houghton lower mansard triangular stone crowns from proposed elevation replaced with photographed horizontal blue projecting caps and paired supports.','limitations':['Photo06 covers five lower dormers; the leftmost lower dormer is occluded and retained.','Cap dimensions and profiles are photographic estimates; original openings, glass, sash divisions, stone casings, mansard surface and roof levels are preserved.','Source proposal is LSEOLD-HBA-V1-XX-DR-A-080251 P2,12July2024; completed-project photography wins for these visible five caps.','No colour calibration, unseen facade or entire roof/interior completion claim.']}
(OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;collection=bpy.data.collections['OLD_EXTERIOR']
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=audit['ownedObjects'].copy()
for o in dst.objects:
 collection.objects.link(o)
 for i,m in enumerate(list(o.data.materials)):
  if m.name.endswith('.001') and bpy.data.materials.get(m.name[:-4]):o.data.materials[i]=bpy.data.materials[m.name[:-4]]
for name in audit['archivedObjects']:bpy.data.objects[name].hide_render=True;bpy.data.objects[name].hide_set(True)
for sc in bpy.data.scenes:
 for layer in sc.view_layers:layer.update()
assert all(fingerprint(bpy.data.objects[name])==h for name,h in originals.items())
assert all([bpy.data.objects[name].hide_render,bpy.data.objects[name].hide_viewport,bpy.data.objects[name].hide_get()]==v for name,v in visibility.items()if name not in audit['archivedObjects'])
assert len(bpy.data.objects[audit['ownedObjects'][0]].data.vertices)==6
export('after')
proof={'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':5915,'baselineUnchanged':hashlib.sha256(BASE.read_bytes()).hexdigest()==EXPECTED,'wholeCampusSaved':False,'retainedLeftPedimentVertices':6,'correctedPhotographedCaps':5,'candidateVisualAcceptance':'pending production whole and close review'}
(OUT/'verification.json').write_text(json.dumps(proof,indent=2)+'\n');print('OLD_EXTERIOR156_VERIFIED',proof['componentSha256'],flush=True);bpy.ops.wm.quit_blender()
