"""Replace generic plaque lettering with the project's existing LSE vector mark.
Run in Blender Text Editor. Retains every plaque, facade and interior position.
"""
from pathlib import Path
import array,hashlib,json,shutil,xml.etree.ElementTree as ET
import bpy,bmesh
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'result/blender/stage100';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v99.blend'))
bpy.context.window.scene=bpy.data.scenes['00_CAMPUS_COMPLETE']
def fingerprint(o):
 h=hashlib.sha256(str([list(r) for r in o.matrix_world]).encode())
 if o.type=='MESH':
  h.update(array.array('f',[c for v in o.data.vertices for c in v.co]).tobytes());h.update(array.array('i',[l.vertex_index for l in o.data.loops]).tobytes())
 if o.type=='FONT':h.update(str((o.data.body,o.data.size,o.data.font.name,o.data.extrude)).encode())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()
before={o.name:fingerprint(o) for o in bpy.data.objects}
svg=ET.parse(ROOT/'web/public/logo-lse.svg').getroot()
white=next(p for p in svg.iter() if p.tag.endswith('path') and p.attrib.get('fill')=='#fff')
source=OUT/'lse-mark.svg'
source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><path fill="#ffffff" d="'+white.attrib['d']+'"/></svg>')
objects=set(bpy.data.objects)
bpy.ops.import_curve.svg(filepath=str(source))
imported=[o for o in bpy.data.objects if o not in objects]
assert len(imported)==1 and imported[0].type=='CURVE'
curve=imported[0];curve.data.dimensions='2D';curve.data.fill_mode='BOTH';curve.data.extrude=.000001;curve.data.resolution_u=16
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get();template=bpy.data.meshes.new_from_object(curve.evaluated_get(deps))
# SVG cap and side tessellation emits coincident seam vertices. Weld them in
# small local coordinates before positioning the closed lettering in the campus.
bm=bmesh.new();bm.from_mesh(template)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(template);bm.free()
coords=[v.co.copy() for v in template.vertices]
lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
assert all(hi[i]>lo[i] for i in range(3))
# Extract the two OLD plaque supports without changing their geometry.
board=bpy.data.objects['OLD_V97_LSE_entrance_signs'];bm=bmesh.new();bm.from_mesh(board.data);seen=set();supports=[]
for v in bm.verts:
 if v in seen:continue
 group=[];stack=[v];seen.add(v)
 while stack:
  p=stack.pop();group.append(board.matrix_world@p.co)
  for e in p.link_edges:
   q=e.other_vert(p)
   if q not in seen:seen.add(q);stack.append(q)
 supports.append(group)
bm.free();assert len(supports)==2
records=[]
for name,code in [('OLD_V97_LSE_entry_sign','OLD'),('OLD_V97_LSE_entry_sign.001','OLD'),('COL_V99_logo_lettering','COL')]:
 old=bpy.data.objects[name];basis=old.matrix_world.to_3x3();horizontal=(basis@Vector((1,0,0))).normalized();up=Vector((0,0,1));normal=(basis@Vector((0,0,1))).normalized()
 if code=='OLD':
  points=min(supports,key=lambda ps:((sum(ps,Vector())/len(ps))-old.matrix_world.translation).length)
 else:
  support=bpy.data.objects['COL_V99_logo_badge'];points=[support.matrix_world@v.co for v in support.data.vertices]
 xs=[p.dot(horizontal) for p in points];zs=[p.z for p in points];depth=max(p.dot(normal) for p in points)
 width=max(xs)-min(xs);height=max(zs)-min(zs)
 center=horizontal*((min(xs)+max(xs))/2)+up*((min(zs)+max(zs))/2)+normal*depth
 mesh=template.copy();mesh.name=code+'_V100_vector_logo_mesh'
 for v in mesh.vertices:
  t=(v.co-lo);t=Vector(tuple(t[i]/(hi[i]-lo[i]) for i in range(3)))
  v.co=center+horizontal*((t.x-.5)*width*49.56/79.223)+up*((t.y-.5)*height*49.11/79.706)+normal*(.002+t.z*.006)
 obj=bpy.data.objects.new(code+'_V100_vector_logo',mesh);bpy.data.collections[code+'_EXTERIOR'].objects.link(obj)
 mesh.materials.clear();mesh.materials.append(old.data.materials[0]);old.hide_render=True;old.hide_set(True)
 records.append({'source':name,'copy':obj.name,'code':code,'supportCenter':list(center),'horizontal':list(horizontal),'normal':list(normal),'width':width,'height':height,'frontDepth':depth})
bpy.data.objects.remove(curve,do_unlink=True);bpy.data.meshes.remove(template)
assert all(fingerprint(bpy.data.objects[n])==h for n,h in before.items())
for name in ['room-studies.json','room-spaces.json','building-review.json']:shutil.copyfile(ROOT/'result/blender/stage99'/name,OUT/name)
shutil.copyfile(ROOT/'web/public/models/catalogue.json',OUT/'catalogue-before.json')
audit={'version':100,'baseline':99,'originalFingerprints':before,'plaques':records,'vectorSource':'web/public/logo-lse.svg','vectorSha256':hashlib.sha256((ROOT/'web/public/logo-lse.svg').read_bytes()).hexdigest(),'scope':'Replace generic font letters on two OLD Houghton plaques and COL Garrick badge with existing vector mark; retain all supports, facade geometry and interior layouts','limits':['Plaque sizes and positions remain photo estimates','No new facade dimensions or full interior completion claimed']}
(OUT/'plaque-lettering-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'result/blender/LSE_campus_detailed_v100.blend'))
print('VECTOR_PLAQUES_SAVED',len(records))
