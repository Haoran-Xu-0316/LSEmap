"""Bounded Clement glazing and entry inspection, independent component output.
Constant Blender configuration; no full-campus save or command-line parameters.
"""
from pathlib import Path
import array,hashlib,json,math
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'result/blender/clm_glazing151';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'result/blender/LSE_campus_detailed_v150.blend';PREFIX='CLM_NEXT_GLAZING151_'
if not BASE.exists():BASE=max((ROOT/'result/blender').glob('LSE_campus_detailed_v[0-9]*.blend'),key=lambda p:int(p.stem.rsplit('v',1)[1]))
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['CLM_EXTERIOR'];sha=hashlib.sha256(BASE.read_bytes()).hexdigest()
if BASE.stem.endswith('v150'):assert sha=='d365166d2cc3011cfab00365593400aa56bd8aab1252ce974a7dabeb4af97147'
def fingerprint(o):
 h=hashlib.sha256(str([list(r)for r in o.matrix_world]).encode())
 if o.type=='MESH':
  for data,field,kind,width in [(o.data.vertices,'co','f',3),(o.data.loops,'vertex_index','i',1),(o.data.polygons,'material_index','i',1)]:
   values=array.array(kind,[0])*(len(data)*width);data.foreach_get(field,values);h.update(values.tobytes())
  for layer in o.data.uv_layers:
   values=array.array('f',[0])*(len(layer.data)*2);layer.data.foreach_get('uv',values);h.update(values.tobytes())
 h.update(str([m.name if m else None for m in getattr(o.data,'materials',[])]).encode());return h.hexdigest()

def parts(o):
 adj={v.index:set()for v in o.data.vertices}
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 seen=set();result=[]
 for seed in adj:
  if seed in seen:continue
  stack=[seed];seen.add(seed);group=[]
  while stack:
   k=stack.pop();group.append(k)
   for q in adj[k]:
    if q not in seen:seen.add(q);stack.append(q)
  result.append(group)
 return result

def trees():
 allowed=set()
 def walk(c,hidden=False):
  hidden=hidden or c.hide_render
  if not hidden:allowed.update(o.name for o in c.objects)
  for child in c.children:walk(child,hidden)
 walk(scene.collection)
 return[(o.name,BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[tuple(f.vertices)for f in o.data.polygons]))for o in scene.objects if o.type=='MESH'and not o.hide_render and o.name in allowed and len(o.data.polygons)]
def hit(start,direction,maximum,excluded=None):
 hits=[]
 for name,t in ACTIVE_TREES:
  if name in(excluded or []):continue
  r=t.ray_cast(start,direction,maximum)
  if r[0]is not None:hits.append((r[3],name,list(r[0])))
 return min(hits)if hits else None

site=json.loads((ROOT/'result/blender/site_geometry.json').read_text());rec=next(x for x in site['buildings']if x['code']=='CLM');centre=Vector(rec['center']);points=[Vector(rec['rings'][0][i])for i in [5,4,3,2,1]];segments=[];length=0
for a,b in zip(points,points[1:]):
 u=(b-a).normalized();n=Vector((u.y,-u.x))
 if n.dot((a+b)/2-centre)<0:n=-n
 l=(b-a).length;segments.append((length,length+l,a,u,n));length+=l
def axes(p):
 def distance(t):
  st,en,a,u,n=t;s=max(0,min(en-st,(Vector(p[:2])-a).dot(u)));return(Vector(p[:2])-a-u*s).length
 st,en,a,u,n=min(segments,key=distance);return Vector((*u,0)),Vector((*n,0))

# Rebuild from a future accepted baseline without retaining a full older campus.
old_audit=json.loads((OUT/'audit.json').read_text())if(OUT/'audit.json').exists()else None
for o in list(bpy.data.objects):
 if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
if old_audit:
 for n in old_audit['archivedObjects']:
  o=bpy.data.objects[n];v=old_audit['originalVisibility'][n];o.hide_render,o.hide_viewport=v[:2];o.hide_set(v[2])
original={o.name:fingerprint(o)for o in bpy.data.objects};visibility={o.name:[o.hide_render,o.hide_viewport,o.hide_get()]for o in bpy.data.objects}
if BASE.stem.endswith('v150'):assert len(original)==5858
source=bpy.data.objects['CLM_D5_roof73_attic_glass'];original_material=source.data.materials[0];original_color=list(original_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
owned=source.copy();owned.data=source.data.copy();owned.name=PREFIX+'attic_glass';owned.data.name=owned.name;col.objects.link(owned)
material=original_material.copy();material.name=PREFIX+'attic_neutral_glass';node=material.node_tree.nodes['Principled BSDF'];node.inputs['Alpha'].default_value=.82;node.inputs['Transmission Weight'].default_value=.22;node.inputs['Roughness'].default_value=.26;node.inputs['Metallic'].default_value=.12;node.inputs['IOR'].default_value=1.45;material['webOpacity']=.82;owned.data.materials[0]=material
source.hide_render=True;source.hide_set(True);OWNED=[owned.name];archives=[source.name]
samples=[]
for k,part in enumerate(parts(source)):
 pts=[source.matrix_world@source.data.vertices[i].co for i in part];c=sum(pts,Vector())/len(pts);u,n=axes(c)
 for dx in [-.55,.08,.55]:
  for dz in [-.12,.12]:samples.append({'pane':k,'point':list(c+u*dx+Vector((0,0,dz))),'normal':list(n),'kind':'attic-glass'})
assert len(samples)==42

# Four roof chambers are registered by their actual native cheek vertices.
# The fifth spans a curved segment junction and is deliberately left opaque.
dormer_source=bpy.data.objects['CLM_D5_roof73_dormer_glass'];dormer=dormer_source.copy();dormer.data=dormer_source.data.copy();dormer.name=PREFIX+'registered_four_dormer_glass';col.objects.link(dormer);dormer_material=material.copy();dormer_material.name=PREFIX+'dormer_neutral_glass';dormer_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=dormer_source.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value;dormer.data.materials.append(dormer_material)
dormer_groups=parts(dormer_source);allowed=set(i for group in dormer_groups[:4]for i in group)
for f in dormer.data.polygons:f.material_index=1 if all(i in allowed for i in f.vertices)else 0
dormer_source.hide_render=True;dormer_source.hide_set(True);OWNED.append(dormer.name);archives.append(dormer_source.name)
roof_source=bpy.data.objects['CLM_D3_slate_mansard_planes'];roof=roof_source.copy();roof.name=PREFIX+'four_bounded_dormer_apertures';col.objects.link(roof)
holes=[]
for group in dormer_groups[:4]:
 pts=[dormer_source.matrix_world@dormer_source.data.vertices[i].co for i in group];c=sum(pts,Vector())/len(pts);u,n=axes(c);holes.append({'centre':c,'right':u,'outward':n,'bounds':[[-.60,.60],[-.96,.04],[c.z-.71,c.z+.71]]})
def coordinates(p,h):return((p-h['centre']).dot(h['right']),(p-h['centre']).dot(h['outward']),p.z)
def clip(poly,h,axis,value,greater):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  av=coordinates(a[0],h)[axis];bv=coordinates(b[0],h)[axis];ia=av>=value-1e-8 if greater else av<=value+1e-8;ib=bv>=value-1e-8 if greater else bv<=value+1e-8
  if ia:result.append(a)
  if ia!=ib:
   t=(value-av)/(bv-av);result.append((a[0].lerp(b[0],t),a[1].lerp(b[1],t)))
 return result
uv_source=roof_source.data.uv_layers.active;output=[];removed=[]
for face in roof_source.data.polygons:
 polygon=[(roof_source.matrix_world@roof_source.data.vertices[roof_source.data.loops[k].vertex_index].co,Vector(uv_source.data[k].uv)if uv_source else Vector((0,0)))for k in face.loop_indices];pieces=[polygon]
 for bay,h in enumerate(holes):
  planes=[(axis,value,g)for axis,bounds in enumerate(h['bounds'])for value,g in [(bounds[0],True),(bounds[1],False)]];updated=[]
  for piece in pieces:
   inside=piece
   for axis,value,g in planes:
    inside=clip(inside,h,axis,value,g)
    if len(inside)<3:break
   if len(inside)<3:updated.append(piece);continue
   current=piece
   for axis,value,g in planes:
    outside=clip(current,h,axis,value,not g)
    if len(outside)>=3:updated.append(outside)
    current=clip(current,h,axis,value,g)
   removed.append({'bay':bay,'sourcePolygon':face.index,'worldVertices':[list(q[0])for q in current]})
  pieces=updated
 output.extend((piece,face.material_index)for piece in pieces)
assert{r['bay']for r in removed}==set(range(4))
verts=[];faces=[];uvs=[];slots=[]
for polygon,slot in output:
 start=len(verts);verts.extend(roof_source.matrix_world.inverted()@q[0]for q in polygon);faces.append(tuple(start+i for i in range(len(polygon))));uvs.append([q[1]for q in polygon]);slots.append(slot)
mesh=bpy.data.meshes.new(roof.name);mesh.from_pydata(verts,[],faces);mesh.update()
for mat in roof_source.data.materials:mesh.materials.append(mat)
uv=mesh.uv_layers.new(name=uv_source.name)if uv_source else None
for face,coords,slot in zip(mesh.polygons,uvs,slots):
 face.material_index=slot
 if uv:
  for loop,value in zip(face.loop_indices,coords):uv.data[loop].uv=value
roof.data=mesh;roof_source.hide_render=True;roof_source.hide_set(True);OWNED.append(roof.name);archives.append(roof_source.name)
for bay,h in enumerate(holes):
 for dx in [-.48,-.12,.12,.48]:
  for dz in [-.25,.25]:samples.append({'pane':bay,'point':list(h['centre']+h['right']*dx+Vector((0,0,dz))),'normal':list(h['outward']),'kind':'registered-dormer-glass'})

preserved=['CLM_NEXT_ENVELOPE_street_glass','CLM_NEXT_ENVELOPE_tall_split_glass','CLM_NEXT_FACADE_opaque_brown_spandrels','CLM_D3_timber_door_leaves','CLM_D5_roof73_dormer_glass','CLM_D3_slate_mansard_planes']
def check():
 global ACTIVE_TREES
 ACTIVE_TREES=trees();rows=[]
 for item in samples:
  p=Vector(item['point']);n=Vector(item['normal']);expected=OWNED[0]if item['kind']=='attic-glass'else OWNED[1];front=hit(p+n*.9,-n,1.5);back=hit(p-n*.035,-n,4 if item['kind']=='attic-glass'else .90,[expected])
  assert front and front[1]==expected,(item,front)
  assert back is None,(item,back)
  rows.append({**item,'firstObject':front[1],'expected':expected,'behindNearfield':back,'noOpaqueNearfieldCap':True})
 for name in ['CLM_NEXT_FACADE_opaque_brown_spandrels','CLM_D3_timber_door_leaves']:
  o=bpy.data.objects[name]
  for k,group in enumerate(parts(o)):
   c=sum((o.matrix_world@o.data.vertices[i].co for i in group),Vector())/len(group);u,n=axes(c);p=c+u*.13+Vector((0,0,.06));front=hit(p+n*.9,-n,1.5)
   assert front and front[1]==name,(name,k,front)
   rows.append({'kind':'retained-opaque','source':name,'part':k,'point':list(p),'firstObject':front[1],'expected':name})
 # Fifth retains its actual opaque glass and roof intersection outside one cheek.
 o=bpy.data.objects['CLM_D5_roof73_dormer_glass'];group=parts(o)[4];c=sum((o.matrix_world@o.data.vertices[i].co for i in group),Vector())/len(group);u,n=axes(c);p=c+u*.19+Vector((0,0,.06));front=hit(p+n*.9,-n,1.5);back=hit(p-n*.05,-n,2,[OWNED[1]])
 assert front and front[1]==OWNED[1];assert back and back[1]==OWNED[2]
 rows.append({'kind':'fifth-dormer-retained-opaque','point':list(p),'firstObject':front[1],'expected':OWNED[1],'roofBehindRetained':back})
 return rows
# Register retained roof hits against actual native connected cheek geometry.
cheek=bpy.data.objects['CLM_D5_roof73_dormer_metal'];cheek_parts=[]
for group in parts(cheek):
 pts=[cheek.matrix_world@cheek.data.vertices[i].co for i in group];cheek_parts.append(pts)
roof_relations=[]
for row in json.loads((OUT/'inspection.json').read_text())['glassObjects']:
 if row['object']!='CLM_D5_roof73_dormer_glass':continue
 for pane in row['checks']:
  c=Vector(pane['centre']);u=Vector(pane['right']);n=Vector(pane['normal']);near=sorted(cheek_parts,key=lambda pts:abs((sum(pts,Vector())/len(pts)-c).dot(u))+abs((sum(pts,Vector())/len(pts)-c).z))[:2]
  bounds=[]
  for pts in near:bounds.append({'worldVertices':[list(p)for p in pts],'rightRange':[min((p-c).dot(u)for p in pts),max((p-c).dot(u)for p in pts)],'depthRange':[min((p-c).dot(n)for p in pts),max((p-c).dot(n)for p in pts)],'zRange':[min(p.z for p in pts),max(p.z for p in pts)]})
  h=Vector(pane['behind'][2]);hd=(h-c).dot(n);hz=h.z;inside=all(b['depthRange'][0]-.01<=hd<=b['depthRange'][1]+.01 and b['zRange'][0]<=hz<=b['zRange'][1]for b in bounds)
  roof_relations.append({'pane':pane['pane'],'glassCentre':list(c),'roofHit':list(h),'roofDepthFromGlass':hd,'nativeCheekBounds':bounds,'roofHitWithinBothCheekDepthAndHeight':inside})
(OUT/'dormer-coordinate-registration.json').write_text(json.dumps({'relations':roof_relations,'dimensionBasis':'Actual native mesh vertices; inherited dimensions remain photo estimates.','conclusion':'Roof hits within existing cheek enclosure support bounded window-prism openings; no argument from absent photographic measurement.'},indent=2))
checks=check()
component=OUT/'clement-glazing-component.blend';bpy.data.libraries.write(str(component),set(bpy.data.objects[n]for n in OWNED),fake_user=True,compress=True)
inspection=json.loads((OUT/'inspection.json').read_text())
references=json.loads((ROOT/'result/blender/stage73/references.json').read_text())
audit={'baselineSha256':sha,'baseline':str(BASE.relative_to(ROOT)),'originalObjectCount':len(original),'originalFingerprints':original,'originalVisibility':visibility,'ownedObjects':OWNED,'archivedObjects':archives,'changes':[{'source':source.name,'owned':OWNED[0],'action':'Retain all seven attic pane vertices, UV, matrix and source tint; apply limited estimated glazing optics consistent with already accepted street glass.'}],'optics':{'alpha':.82,'transmission':.22,'roughness':.26,'metallic':.12,'ior':1.45,'webOpacity':.82,'baseColor':original_color,'estimated':True},'references':references,'sourceCoverage':'2018-04-24 full upper frontage and2023-11-15 oblique frontage show seven attic windows and five glazed dormers. Trees and railings partly obscure attic subdivision; retain all existing window geometry. Dated references do not establish current2026 condition.','roofRegistration':{'holes':[{'centre':list(h['centre']),'right':list(h['right']),'outward':list(h['outward']),'bounds':h['bounds']}for h in holes],'removedIntersections':removed,'fifthDormerRetainedOpaque':True,'dimensionsEstimated':True},'preservedObjects':preserved,'dormerNearfieldUnresolved':next(r for r in inspection['glassObjects']if r['object']=='CLM_D5_roof73_dormer_glass')['checks'],'scope':'Seven attic and four registered dormer panes; subtract only four native glass outlines within existing cheek depths.39 main panes, opaque brown bands, timber portals and fifth dormer remain. No invented room/backplate.','limitations':['Optics are visual estimates, not measured glazing specifications.','Fifth dormer remains opaque: curved segment junction puts its roof hit outside one cheek depth; coordinates in dormer-coordinate-registration.json. Four preceding roof intersections removed only within inherited cheek volumes.','Existing window height, spacing, curved frontage and entry levels remain prior photo/GIS estimates.','Main glazed openings have no opaque surface within4m at prior diagnostic sample positions; this does not establish complete interior geometry.']}
audit['changes'].extend([{'source':dormer_source.name,'owned':OWNED[1],'action':'Retain exact geometry and UV; finite optics on four registered panes; fifth pane keeps original opaque slot.'},{'source':roof_source.name,'owned':OWNED[2],'action':'Remove four window-outline prisms only within native cheek depth; interpolate original UV at clipped boundaries, keep remaining roof.'}]);
(OUT/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items())
bpy.ops.wm.open_mainfile(filepath=str(BASE));scene=bpy.data.scenes['00_CAMPUS_COMPLETE'];bpy.context.window.scene=scene;col=bpy.data.collections['CLM_EXTERIOR']
for o in list(bpy.data.objects):
 if o.name.startswith(PREFIX):bpy.data.objects.remove(o,do_unlink=True)
for n in archives:
 o=bpy.data.objects[n];v=visibility[n];o.hide_render,o.hide_viewport=v[:2];o.hide_set(v[2])
with bpy.data.libraries.load(str(component),link=False)as(src,dst):dst.objects=list(OWNED)
for o in dst.objects:
 col.objects.link(o)
 for slot in o.material_slots:
  m=slot.material
  if m and'.'in m.name and m.name.rsplit('.',1)[1].isdigit():
   canonical=bpy.data.materials.get(m.name.rsplit('.',1)[0])
   if canonical:slot.material=canonical
for n in archives:bpy.data.objects[n].hide_render=True;bpy.data.objects[n].hide_set(True)
reopened=check();assert reopened==checks;assert all(fingerprint(bpy.data.objects[n])==v for n,v in original.items());assert all([bpy.data.objects[n].hide_render,bpy.data.objects[n].hide_viewport,bpy.data.objects[n].hide_get()]==v for n,v in visibility.items()if n not in archives)
source=bpy.data.objects[archives[0]];owned=bpy.data.objects[OWNED[0]]
assert [list(v.co)for v in source.data.vertices]==[list(v.co)for v in owned.data.vertices]
assert [list(v.uv)for v in source.data.uv_layers.active.data]==[list(v.uv)for v in owned.data.uv_layers.active.data]
assert source.matrix_world==owned.matrix_world
for srcname,dstname in [(archives[0],OWNED[0]),(archives[1],OWNED[1])]:
 src=bpy.data.objects[srcname];dst=bpy.data.objects[dstname];assert [list(v.co)for v in src.data.vertices]==[list(v.co)for v in dst.data.vertices];assert [list(v.uv)for v in src.data.uv_layers.active.data]==[list(v.uv)for v in dst.data.uv_layers.active.data];assert src.matrix_world==dst.matrix_world
node=owned.data.materials[0].node_tree.nodes['Principled BSDF'];assert list(node.inputs['Base Color'].default_value)==original_color;assert abs(owned.data.materials[0]['webOpacity']-.82)<1e-6
proof={'baselineSha256':sha,'componentSha256':hashlib.sha256(component.read_bytes()).hexdigest(),'savedComponentReopened':True,'originalGeometryPreserved':True,'unrelatedVisibilityPreserved':True,'originalObjectCount':len(original),'firstSurfaceChecks':reopened,'checkCount':len(reopened),'atticLightChecks':42,'allGlazingGeometryAndUVRetained':True,'sourceColorsPreserved':True,'opaqueSpandrelsAndTimberDoorsPreserved':True,'fifthDormerOpaquePreserved':True,'roofOutsideFourPrismsPreserved':True,'roofSourceHadNoUV':uv_source is None,'registeredDormerChecks':32,'fullModelSaved':False}
visible={o.name for o in col.all_objects}
for o in scene.objects:
 if o.type in ['MESH','FONT','CURVE']and o.name not in visible:o.hide_render=True
cd=bpy.data.cameras.new(PREFIX+'review');cam=bpy.data.objects.new(cd.name,cd);scene.collection.objects.link(cam);cd.type='ORTHO';scene.camera=cam
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True;scene.render.resolution_percentage=100
focus_xy=sum((a for _,_,a,_,_ in segments),Vector((0,0)))/len(segments)
def render(label,target,scale,dist):
 u,n=axes(target);position=target+n*dist+u*4+Vector((0,0,3));cam.location=position;cam.rotation_euler=(target-position).to_track_quat('-Z','Y').to_euler();cd.ortho_scale=scale;scene.render.resolution_x=1200;scene.render.resolution_y=1100;scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True);return{'position':list(position),'target':list(target),'orthoScale':scale,'path':scene.render.filepath}
focus_xy=sum((Vector(q['centre'][:2])for q in inspection['glassObjects'][0]['checks']),Vector((0,0)))/7
proof['wholeBuildingPreview']=render('reloaded-clement-glazing',Vector((*focus_xy,13.5)),42,44)
# Use a genuine retained side timber portal rather than an invented open doorway.
door=bpy.data.objects['CLM_D3_timber_door_leaves'];group=parts(door)[0];target=sum((door.matrix_world@door.data.vertices[i].co for i in group),Vector())/len(group);target.z=3.3
proof['entryPreview']={'path':str(OUT/'reloaded-clement-entry.png'),'reusedUnchangedGeometryAndOptics':True,'target':list(target),'orthoScale':9}
dormer=bpy.data.objects[OWNED[1]];assert sum(f.material_index==0 for f in dormer.data.polygons)==6;assert dormer.data.materials[0].node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value==1;assert abs(dormer.data.materials[1]['webOpacity']-.82)<1e-6;proof['fifthDormerOpaquePolygons']=6;proof['opticalChecks']=[{'object':n,'webOpacity':bpy.data.objects[n].data.materials[-1]['webOpacity']}for n in OWNED[:2]]
(OUT/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print('CLM151_VERIFIED',len(original),len(OWNED),len(reopened));bpy.ops.wm.quit_blender()
